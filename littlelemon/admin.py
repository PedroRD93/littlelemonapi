from django.contrib import admin
from .models import *


class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'price', 'featured', 'category']


class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total', 'date']


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'menuitem', 'quantity', 'unit_price', 'price']


admin.site.register(Category)
admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(Cart)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)