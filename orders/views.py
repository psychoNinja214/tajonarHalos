from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cart.views import get_or_create_cart
from .models import Order, OrderItem
from .forms import OrderCreateForm

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
            # Create order
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.total = cart.get_total()
            order.save()

            # Create order items from cart
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    price=cart_item.product.price,
                    quantity=cart_item.quantity
                )

                # Reduce stock
                product = cart_item.product
                product.stock -= cart_item.quantity
                product.save()

            # Clear cart
            cart.items.all().delete()

            # Store order ID in session
            request.session['order_id'] = order.id

            messages.success(request, f'Order #{order.id} created successfully!')
            return redirect('orders:order_confirmation', order_id=order.id)
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

def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)

    # Security: only show if it's the user's order or just created
    if request.user.is_authenticated:
        if order.user != request.user:
            messages.error(request, 'Access denied.')
            return redirect('store:product_list')
    else:
        # Check if this order was just created in this session
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


