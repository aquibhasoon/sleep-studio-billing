from django.contrib import admin
from .models import Product, Manufacturer, StockMovement


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'manufacturer',
        'size',
        'selling_price',
        'stock_quantity',
        'is_active',
    )

    list_filter = (
        'category',
        'manufacturer',
        'is_active',
    )

    search_fields = (
        'name',
        'manufacturer__name',
    )
    

    
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "movement_type",
        "quantity",
        "note",
        "created_at",
    )

    list_filter = (
        "movement_type",
        "created_at",
    )

    search_fields = (
        "product__name",
        "note",
    )

    ordering = ("-created_at",)