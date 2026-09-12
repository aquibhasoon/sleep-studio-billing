from django.contrib import admin
from .models import Invoice, InvoiceItem, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number',
        'customer',
        'date',
        'grand_total',
        'amount_paid',
        'balance',
        'payment_status',
    )

    list_filter = (
        'payment_status',
        'date',
    )

    search_fields = (
        'invoice_number',
        'customer__name',
        'customer__phone',
    )


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = (
        'invoice',
        'product',
        'quantity',
        'unit_price',
        'total',
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'invoice',
        'amount',
        'method',
        'date',
    )

    list_filter = (
        'method',
        'date',
    )