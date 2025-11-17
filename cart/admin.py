from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'get_total']
    inlines = [CartItemInline]

    def get_total(self, obj):
        return f"${obj.get_total()}"
    get_total.short_description = 'Total'
