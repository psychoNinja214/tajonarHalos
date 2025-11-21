from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<int:order_id>/', views.payment, name='payment'),
    path('payment-success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('payment-cancelled/<int:order_id>/', views.payment_cancelled, name='payment_cancelled'),
    path('confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('history/', views.order_history, name='order_history'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),  # For Stripe webhooks
]

