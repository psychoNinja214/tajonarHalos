from .views import get_or_create_cart

def cart_count(request):
    """Make cart item count available in all templates"""
    cart = get_or_create_cart(request)
    count = sum(item.quantity for item in cart.items.all())
    return {'cart_count': count}

