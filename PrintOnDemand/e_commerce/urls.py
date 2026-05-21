from django.urls import path
from .views import (
    add_product,
    add_to_cart,
    cart_view,
    checkout_buy_now,
    checkout_cart,
    home,
    my_products_view,
    order_detail_view,
    order_success,
    profile_view,
    place_order,
    product_detail_view,
    products_by_category_view,
    remove_from_cart,
    signin_view,
    signout_view,
    signup_view,
    trending_products_view,
    update_cart_quantity,
    verify_payment,
)
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', home, name='home'),

    # Product URLs
    path('product/<int:pk>/', product_detail_view, name='product_detail'),  # View product details
    path('add-product/', add_product, name='add_product'),  # Add a new product
    path('category/<slug:category_slug>/', products_by_category_view, name='products_by_category'),
    path('trending/', trending_products_view, name='trending_view'),
    path('my-stuff/', my_products_view, name='my_product'),
    path('profile/', profile_view, name='profile'),
    path('profile/orders/<int:order_id>/', order_detail_view, name='order_detail'),

    # Cart URLs
    path('cart/', cart_view, name='view_cart'),  # View cart
    path('product/<int:pk>/add-to-cart/', add_to_cart, name='add_to_cart'),  # Add product to cart
    path('remove_from_cart/<int:product_id>/', remove_from_cart, name='remove_from_cart'),  # Remove product from cart
    path('update_cart_quantity/<int:product_id>/', update_cart_quantity, name='update_cart_quantity'),

    # Checkout & payment
    path('checkout/', checkout_cart, name='checkout_cart'),
    path('checkout/buy-now/<int:pk>/', checkout_buy_now, name='checkout_buy_now'),
    path('payment/place-order/', place_order, name='place_order'),
    path('payment/verify/', verify_payment, name='verify_payment'),
    path('order/success/<int:order_id>/', order_success, name='order_success'),

    # Authentication URLs
    path('signup/', signup_view, name='signup'),  # Signup page
    path('signin/', signin_view, name='signin'),  # Signin page
    path('signout/', signout_view, name='signout'),  # Signout page
]

if settings.DEBUG:  # Only for development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)