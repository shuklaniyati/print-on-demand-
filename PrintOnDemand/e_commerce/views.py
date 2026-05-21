from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ProductForm, ProfileForm
from .models import Cart, CartItem, Category, Order, Product, User
from . import payments

CATEGORY_PREVIEW_IMAGES = {
    'clothing': 'images/z2.jpg',
    'mobilecovers': 'images/z3.jpg',
    'mugs': 'images/z5.jpg',
    'shoes': 'images/z6.jpg',
}

HERO_CATEGORY_SLUG = 'mobilecovers'


def home(request):
    category_id = request.GET.get('category_id')
    query = request.GET.get('q', '').strip()

    products = Product.objects.select_related('category').all()

    if category_id:
        products = products.filter(category_id=category_id)

    if query:
        products = products.filter(name__icontains=query)

    product_data = [
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "category": product.category.name if product.category else None,
            "added_by": product.added_by_display(),
            "product_image": product.product_image.url if product.product_image else None,
        }
        for product in products
    ]

    categories = []
    for category in Category.objects.order_by('name'):
        categories.append({
            'name': category.name,
            'slug': category.slug,
            'preview_image': CATEGORY_PREVIEW_IMAGES.get(category.slug),
        })

    gifts_category = Category.objects.filter(slug='gifts').first()
    gifts_url_name = 'products_by_category'
    gifts_url_args = [gifts_category.slug] if gifts_category else []
    if not gifts_category:
        gifts_url_name = 'home'
        gifts_url_args = []

    return render(request, 'index.html', {
        'product_data': product_data,
        'categories': categories,
        'search_query': query,
        'hero_category_slug': HERO_CATEGORY_SLUG,
        'gifts_url_name': gifts_url_name,
        'gifts_url_args': gifts_url_args,
    })

def product_detail_view(request, pk):
    """
    Display details of a specific product.
    """
    product = get_object_or_404(Product, pk=pk)
    product_data ={
        "id": pk,
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "category": product.category.name if product.category else None,
        "added_by": product.added_by_display(),
        "product_image": product.product_image.url if product.product_image else None , # Correct way to get the image URL
        "added_by_admin": product.added_by_admin
    }
    return render(request, 'product_detail.html', {
        'product': product_data,
        'payment_demo_mode': settings.PAYMENT_DEMO_MODE,
        'razorpay_enabled': payments.razorpay_enabled(),
    })

# Cart Views 
@login_required(login_url='signin')
def cart_view(request):
    """
    API to view the user's cart.
    """
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.cartitem_set.all()

    cart_data = {
        "id": cart.id,
        "user": cart.user.username,
        "items": [
            {
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": float(item.product.price),
                "total_price": item.quantity * float(item.product.price),  # Calculate total price for each item
                "product_id": item.product.id,
                "product_image": item.product.product_image.url if item.product.product_image else None ,
            }
            for item in cart_items
        ],
        "total_price": sum(item.quantity * float(item.product.price) for item in cart_items),
    }

    return render(request, 'cart.html', {
        'cart_data': cart_data,
        'has_items': bool(cart_items),
        'payment_demo_mode': settings.PAYMENT_DEMO_MODE,
        'razorpay_enabled': payments.razorpay_enabled(),
    })



@login_required(login_url='signin')
def add_to_cart(request, pk):
    """Add a product to the user's cart."""
    product = get_object_or_404(Product, pk=pk)
    cart, _created = Cart.objects.get_or_create(user=request.user)
    quantity = max(1, int(request.POST.get('quantity', 1)))

    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

    if item_created:
        cart_item.quantity = quantity
    else:
        cart_item.quantity += quantity
    cart_item.save()

    messages.success(request, f"Added '{product.name}' to your cart.")
    return redirect('product_detail', pk=pk)


@login_required(login_url='signin')
def remove_from_cart(request, product_id):
    """
    Remove a product from the user's cart.
    """
    cart, created = Cart.objects.get_or_create(user=request.user)  # Create the cart if it doesn't exist

    # Get the cart item associated with the product_id
    cart_item = CartItem.objects.filter(cart=cart, product_id=product_id).first()

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
        return redirect('view_cart')
    else:
        if cart_item:
            cart_item.delete()  # Remove the cart item from the cart
            messages.success(request, 'Product has been removed from your cart.')
        else:
            messages.warning(request, 'This product is not in your cart.')

        return redirect('view_cart')  # Ensure 'cart' is correctly configured in urls.py


def signup_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Basic validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('signup')

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Account created successfully! Please log in.")
        return redirect('signin')

    return render(request, 'signup.html')


# SignIn View
def signin_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password!")
            return redirect('signin')

    return render(request, 'signin.html')


# SignOut View
def signout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('signin')

@login_required(login_url='signin')
def add_product(request):
    """
    View to add a new product.
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)  # Handle form with image uploads
        if form.is_valid():
            product = form.save(commit=False)
            product.added_by = request.user  # Associate the product with the logged-in user
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('product_detail', pk=product.pk)  # Redirect to the product detail page
        else:
            messages.error(request, 'There was an error with your form.')
    else:
        form = ProductForm()

    return render(request, 'add_product.html', {'form': form})

@login_required(login_url='signin')
def update_cart_quantity(request, product_id):
    """Update the quantity of a product in the cart."""
    new_quantity = request.GET.get('quantity')

    if new_quantity:
        cart = Cart.objects.get(user=request.user)
        cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        cart_item.quantity = new_quantity
        cart_item.save()

        # Calculate the new total price
        new_total_price = cart_item.quantity * cart_item.product.price

        return JsonResponse({'new_total_price': new_total_price})

    return JsonResponse({'error': 'Invalid quantity'}, status=400)

def products_by_category_view(request, category_slug):
    """
    Display all products under a specific category using the slug.
    """
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category)
    
    product_data = [
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "category": product.category.name if product.category else None,
            "added_by": product.added_by_display(),
            "product_image": product.product_image.url if product.product_image else None
        }
        for product in products
    ]

    # Pass product data as context
    return render(request, 'products_by_category.html', {
        'category': category,
        'product_data': product_data,
    })

def trending_products_view(request):
    """
    Display all products having is_trending = True.
    """
    
    products = Product.objects.filter(is_trending=True)
    
    product_data = [
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "category": product.category.name if product.category else None,
            "added_by": product.added_by_display(),
            "product_image": product.product_image.url if product.product_image else None
        }
        for product in products
    ]

    # Pass product data as context
    return render(request, 'trending_view.html', {
        'product_data': product_data,
    })

def my_products_view(request):
    """
    Display all products added by the logged-in user.
    """
    if not request.user.is_authenticated:
        return redirect('signin')  # Redirect to sign-in page if user is not authenticated

    products = Product.objects.filter(added_by=request.user)
    
    product_data = [
        {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "category": product.category.name if product.category else None,
            "added_by": product.added_by.username,  # Ensure added_by_display works if a method
            "product_image": product.product_image.url if product.product_image else None
        }
        for product in products
    ]

    # Pass product data as context
    return render(request, 'my_product.html', {
        'product_data': product_data,
    })


def _checkout_context(request, line_items, source, product_id=None, quantity=1):
    total = payments.calculate_total(line_items)
    return {
        'line_items': payments.serialize_line_items(line_items),
        'total_amount': float(total),
        'source': source,
        'product_id': product_id,
        'quantity': quantity,
        'payment_demo_mode': settings.PAYMENT_DEMO_MODE,
        'razorpay_enabled': payments.razorpay_enabled(),
        'use_razorpay': payments.razorpay_enabled(),
    }


@login_required(login_url='signin')
def checkout_cart(request):
    line_items = payments.build_line_items_from_cart(request.user)
    if not line_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('view_cart')

    return render(request, 'checkout.html', _checkout_context(
        request, line_items, source='cart',
    ))


@login_required(login_url='signin')
def checkout_buy_now(request, pk):
    product = get_object_or_404(Product, pk=pk)
    quantity = request.GET.get('quantity', 1)
    line_items = payments.build_line_items_for_product(product, quantity)

    return render(request, 'checkout.html', _checkout_context(
        request,
        line_items,
        source='buy_now',
        product_id=product.id,
        quantity=line_items[0]['quantity'],
    ))


@login_required(login_url='signin')
@require_POST
def place_order(request):
    source = request.POST.get('source', 'cart')
    payment_method = request.POST.get('payment_method', 'razorpay')

    valid_methods = {choice[0] for choice in Order.PAYMENT_METHOD_CHOICES}
    if payment_method not in valid_methods:
        messages.error(request, 'Please select a valid payment method.')
        return redirect('view_cart')

    if source == 'buy_now':
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity', 1)
        product = get_object_or_404(Product, pk=product_id)
        line_items = payments.build_line_items_for_product(product, quantity)
        clear_cart_after = False
    else:
        line_items = payments.build_line_items_from_cart(request.user)
        clear_cart_after = True

    if not line_items:
        messages.warning(request, 'No items to checkout.')
        return redirect('view_cart')

    order = payments.create_order(request.user, line_items, payment_method)

    use_razorpay = (
        payment_method == 'razorpay'
        and payments.razorpay_enabled()
    )

    if use_razorpay:
        try:
            payments.create_razorpay_order(order)
        except Exception:
            order.payment_status = 'failed'
            order.save(update_fields=['payment_status'])
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(
                    {'error': 'Could not connect to payment gateway.'},
                    status=500,
                )
            messages.error(request, 'Could not connect to payment gateway.')
            return redirect('checkout_cart')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'razorpay': {
                    'key': settings.RAZORPAY_KEY_ID,
                    'amount': int(Decimal(order.total_amount) * 100),
                    'currency': 'INR',
                    'order_id': order.id,
                    'razorpay_order_id': order.razorpay_order_id,
                },
            })

        messages.info(request, 'Complete payment using Razorpay checkout.')
        return redirect('checkout_cart')

    payments.complete_order_payment(order)
    if clear_cart_after:
        payments.clear_cart(request.user)

    messages.success(request, f'Order #{order.id} placed successfully!')
    return redirect('order_success', order_id=order.id)


@login_required(login_url='signin')
@require_POST
def verify_payment(request):
    snazzy_order_id = request.POST.get('snazzy_order_id')
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')

    order = get_object_or_404(Order, pk=snazzy_order_id, user=request.user)

    try:
        payments.verify_razorpay_payment(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
        )
    except Exception:
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status'])
        messages.error(request, 'Payment verification failed.')
        return redirect('view_cart')

    payments.complete_order_payment(order, payment_id=razorpay_payment_id)
    payments.clear_cart(request.user)
    messages.success(request, f'Payment successful! Order #{order.id} confirmed.')
    return redirect('order_success', order_id=order.id)


@login_required(login_url='signin')
def order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('order_items__product'),
        pk=order_id,
        user=request.user,
    )
    return render(request, 'order_success.html', {'order': order})


@login_required(login_url='signin')
def profile_view(request):
    user = request.user
    orders = (
        Order.objects.filter(user=user)
        .prefetch_related('order_items__product')
        .order_by('-created_at')
    )

    cart = Cart.objects.filter(user=user).first()
    cart_item_count = cart.cartitem_set.count() if cart else 0
    products_listed = Product.objects.filter(added_by=user).count()
    orders_count = orders.count()
    paid_orders = orders.filter(payment_status='paid')
    total_spent = sum(order.total_amount for order in paid_orders)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=user)

    return render(request, 'profile.html', {
        'form': form,
        'orders': orders,
        'stats': {
            'orders_count': orders_count,
            'products_listed': products_listed,
            'cart_item_count': cart_item_count,
            'total_spent': total_spent,
        },
    })


@login_required(login_url='signin')
def order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('order_items__product'),
        pk=order_id,
        user=request.user,
    )
    return render(request, 'order_detail.html', {'order': order})



