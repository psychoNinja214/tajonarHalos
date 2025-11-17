from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from store.models import Product
from .models import Cart, CartItem

def get_or_create_cart(request):
    """Get or create cart for the current session"""
    cart_id = request.session.get('cart_id')

    if cart_id:
        try:
            cart = Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            cart = Cart.objects.create()
            request.session['cart_id'] = cart.id
    else:
        cart = Cart.objects.create()
        request.session['cart_id'] = cart.id

    return cart

def add_to_cart(request, product_id):
    """Add a product to the cart"""
    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request)

    # Check if product already in cart
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )

    if not created:
        # Product already in cart, increase quantity
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'Updated {product.name} quantity in cart.')
        else:
            messages.warning(request, f'Sorry, only {product.stock} items available.')
    else:
        messages.success(request, f'Added {product.name} to cart.')

    return redirect('cart:cart_detail')

def cart_detail(request):
    """Display cart contents"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()

    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'cart_items': cart_items,
    })

def update_cart(request, item_id):
    """Update cart item quantity"""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))

        if quantity > 0 and quantity <= cart_item.product.stock:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated successfully.')
        elif quantity > cart_item.product.stock:
            messages.warning(request, f'Only {cart_item.product.stock} items available.')
        else:
            cart_item.delete()
            messages.success(request, 'Item removed from cart.')

    return redirect('cart:cart_detail')

def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'Removed {product_name} from cart.')

    return redirect('cart:cart_detail')

def clear_cart(request):
    """Clear all items from cart"""
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    messages.success(request, 'Cart cleared.')

    return redirect('cart:cart_detail')
