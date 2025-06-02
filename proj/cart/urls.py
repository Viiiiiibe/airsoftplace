from django.urls import path
from . import views
from .webhooks import yookassa_webhook

app_name = 'cart'

urlpatterns = [
    path('', views.cart_view, name='cart-view'),
    path('add/', views.cart_add, name='add-to-cart'),
    path('delete/', views.cart_delete, name='delete-to-cart'),
    path('update/', views.cart_update, name='update-to-cart'),
    path('order/<slug:shop_slug>/', views.order_view, name='order-view'),
    path('payment-success/', views.payment_success, name='payment-success'),
    path('payment-error/', views.payment_error, name='payment-error'),
    path('webhook-yookassa/', yookassa_webhook, name='webhook-yookassa'),

]
