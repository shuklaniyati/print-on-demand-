from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Custom User model."""
    def __str__(self):
        return self.username


class Category(models.Model):
    """Model for product categories."""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True, help_text="Optional description of the category")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    """Model for products listed on the website."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image = models.ImageField(upload_to='e_commerce/ProductImages')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="products"
    )
    added_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="products_added"
    )
    added_by_admin = models.BooleanField(default=False, help_text="True if product is added by the website admin")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_trending = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def added_by_display(self):
        """Display who added the product."""
        if self.added_by_admin:
            return "Website"
        return self.added_by.username if self.added_by else "Unknown"


class Cart(models.Model):
    """Model for a user's cart."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    products = models.ManyToManyField(
        Product, through='CartItem', related_name="carts"
    )

    def __str__(self):
        return f"{self.user.username}'s Cart"


class CartItem(models.Model):
    """Through model for the Cart and Products relationship."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class Order(models.Model):
    """Model for orders."""

    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Card / UPI / Netbanking (Razorpay)'),
        ('upi', 'UPI'),
        ('card', 'Debit / Credit Card'),
        ('cod', 'Cash on Delivery'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('Pending', 'Pending'),
            ('Processing', 'Processing'),
            ('Shipped', 'Shipped'),
            ('Delivered', 'Delivered'),
        ],
        default='Pending',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    razorpay_order_id = models.CharField(max_length=255, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    def computed_total(self):
        """Calculate total from line items (fallback if total_amount unset)."""
        return sum(item.price * item.quantity for item in self.order_items.all())


class OrderItem(models.Model):
    """Model for order items."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

    @property
    def line_total(self):
        return self.price * self.quantity