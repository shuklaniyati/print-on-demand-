from decimal import Decimal

from django.conf import settings

from .models import Cart, CartItem, Order, OrderItem, Product


PAYMENT_METHODS = [
    ('razorpay', 'Card / UPI / Netbanking'),
    ('upi', 'UPI'),
    ('card', 'Debit / Credit Card'),
    ('cod', 'Cash on Delivery'),
]


def razorpay_enabled():
    if not getattr(settings, 'RAZORPAY_KEY_ID', '') or not getattr(settings, 'RAZORPAY_KEY_SECRET', ''):
        return False
    try:
        import razorpay  # noqa: F401
    except ImportError:
        return False
    return True


def get_razorpay_client():
    if not razorpay_enabled():
        return None
    try:
        import razorpay
    except ImportError:
        return None

    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def build_line_items_from_cart(user):
    cart = Cart.objects.filter(user=user).first()
    if not cart:
        return []

    items = []
    for cart_item in cart.cartitem_set.select_related('product'):
        items.append({
            'product': cart_item.product,
            'quantity': cart_item.quantity,
            'unit_price': cart_item.product.price,
            'line_total': cart_item.product.price * cart_item.quantity,
        })
    return items


def build_line_items_for_product(product, quantity):
    quantity = max(1, int(quantity))
    return [{
        'product': product,
        'quantity': quantity,
        'unit_price': product.price,
        'line_total': product.price * quantity,
    }]


def calculate_total(line_items):
    return sum(item['line_total'] for item in line_items)


def serialize_line_items(line_items):
    return [
        {
            'product_id': item['product'].id,
            'product_name': item['product'].name,
            'product_image': (
                item['product'].product_image.url
                if item['product'].product_image else None
            ),
            'quantity': item['quantity'],
            'unit_price': float(item['unit_price']),
            'line_total': float(item['line_total']),
        }
        for item in line_items
    ]


def create_order(user, line_items, payment_method):
    total = calculate_total(line_items)
    order = Order.objects.create(
        user=user,
        payment_method=payment_method,
        payment_status='pending',
        total_amount=total,
        status='Pending',
    )

    for item in line_items:
        OrderItem.objects.create(
            order=order,
            product=item['product'],
            quantity=item['quantity'],
            price=item['unit_price'],
        )

    return order


def clear_cart(user):
    cart = Cart.objects.filter(user=user).first()
    if cart:
        CartItem.objects.filter(cart=cart).delete()


def create_razorpay_order(order):
    client = get_razorpay_client()
    if not client:
        return None

    amount_paise = int(Decimal(order.total_amount) * 100)
    razorpay_order = client.order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'payment_capture': 1,
        'notes': {
            'snazzy_order_id': str(order.id),
        },
    })
    order.razorpay_order_id = razorpay_order['id']
    order.save(update_fields=['razorpay_order_id'])
    return razorpay_order


def verify_razorpay_payment(order_id, payment_id, signature):
    client = get_razorpay_client()
    if not client:
        return False

    client.utility.verify_payment_signature({
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature,
    })
    return True


def complete_order_payment(order, payment_id=''):
    if order.payment_method == 'cod':
        order.payment_status = 'pending'
        order.status = 'Pending'
    else:
        order.payment_status = 'paid'
        order.status = 'Processing'
    if payment_id:
        order.razorpay_payment_id = payment_id
    order.save(update_fields=['payment_status', 'status', 'razorpay_payment_id'])
