from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from cart.views import get_or_create_cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
import stripe
import json

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

def checkout(request):
    """Checkout page with order form"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()

    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('cart:cart_detail')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            # Create order (but don't process payment yet)
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.total = cart.get_total()
            order.status = 'pending'  # Keep as pending until payment
            order.save()

            # Create order items from cart
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    price=cart_item.product.price,
                    quantity=cart_item.quantity
                )

            # Store order ID in session
            request.session['order_id'] = order.id

            # Redirect to payment page
            return redirect('orders:payment', order_id=order.id)
    else:
        # Pre-fill form if user is authenticated
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            }
        form = OrderCreateForm(initial=initial_data)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'cart_items': cart_items,
        'form': form,
    })

def payment(request, order_id):
    """Payment page with Stripe integration"""
    order = get_object_or_404(Order, id=order_id)

    # Security check
    if request.user.is_authenticated:
        if order.user and order.user != request.user:
            messages.error(request, 'Access denied.')
            return redirect('store:product_list')
    else:
        session_order_id = request.session.get('order_id')
        if session_order_id != order_id:
            messages.error(request, 'Access denied.')
            return redirect('store:product_list')

    # Check if already paid
    if order.status != 'pending':
        messages.info(request, 'This order has already been processed.')
        return redirect('orders:order_confirmation', order_id=order.id)

    # Create Stripe PaymentIntent
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(order.total * 100),  # Stripe uses cents
            currency='usd',
            metadata={
                'order_id': order.id,
                'customer_email': order.email
            }
        )

        return render(request, 'orders/payment.html', {
            'order': order,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
            'client_secret': intent.client_secret,
        })
    except Exception as e:
        messages.error(request, f'Payment error: {str(e)}')
        return redirect('orders:checkout')

def payment_success(request, order_id):
    """Handle successful payment"""
    order = get_object_or_404(Order, id=order_id)

    # Verify payment intent
    payment_intent_id = request.GET.get('payment_intent')

    if payment_intent_id:
        try:
            # Retrieve the payment intent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            if intent.status == 'succeeded' and order.status == 'pending':
                # Update order status
                order.status = 'processing'
                order.save()

                # Reduce stock for each item
                for item in order.items.all():
                    product = item.product
                    product.stock -= item.quantity
                    product.save()

                # Clear cart
                cart = get_or_create_cart(request)
                cart.items.all().delete()

                messages.success(request, f'Payment successful! Order #{order.id} confirmed.')
                return redirect('orders:order_confirmation', order_id=order.id)

        except stripe.error.StripeError as e:
            messages.error(request, f'Payment verification failed: {str(e)}')
            return redirect('orders:payment', order_id=order.id)

    messages.error(request, 'Invalid payment.')
    return redirect('orders:payment', order_id=order.id)

def payment_cancelled(request, order_id):
    """Handle cancelled payment"""
    order = get_object_or_404(Order, id=order_id)
    messages.warning(request, 'Payment was cancelled. You can try again.')
    return redirect('orders:payment', order_id=order.id)

def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)

    # Security: only show if it's the user's order or just created
    if request.user.is_authenticated:
        if order.user and order.user != request.user:
            messages.error(request, 'Access denied.')
            return redirect('store:product_list')
    else:
        session_order_id = request.session.get('order_id')
        if session_order_id != order_id:
            messages.error(request, 'Access denied.')
            return redirect('store:product_list')

    return render(request, 'orders/order_confirmation.html', {
        'order': order,
    })

@login_required
def order_history(request):
    """View all orders for logged in user"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {
        'orders': orders,
    })

@login_required
def order_detail(request, order_id):
    """View single order detail"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {
        'order': order,
    })

# Webhook handler (optional but recommended for production)
@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata'].get('order_id')

        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                if order.status == 'pending':
                    order.status = 'processing'
                    order.save()

                    # Reduce stock
                    for item in order.items.all():
                        product = item.product
                        product.stock -= item.quantity
                        product.save()
            except Order.DoesNotExist:
                pass

    return HttpResponse(status=200)

