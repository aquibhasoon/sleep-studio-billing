from django.db import models
from customers.models import Customer
from products.models import Product


class Invoice(models.Model):

    PAYMENT_STATUS = [
        ("UNPAID", "Unpaid"),
        ("PARTIAL", "Partial"),
        ("PAID", "Paid"),
    ]

    invoice_number = models.CharField(max_length=30, unique=True)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="invoices",
        null=True,
        blank=True,
    )

    date = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS, default="UNPAID"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")

    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


class Payment(models.Model):

    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("UPI", "UPI"),
        ("CARD", "Card"),
        ("BANK", "Bank Transfer"),
    ]

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    reference = models.CharField(max_length=100, blank=True)

    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice.invoice_number} - ₹{self.amount}"
