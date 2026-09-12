from django.db import models


class Manufacturer(models.Model):
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):

    CATEGORY_CHOICES = [
        ('MATTRESS', 'Mattress'),
        ('PILLOW', 'Pillow'),
        ('PROTECTOR', 'Protector'),
        ('COMFORTER', 'Comforter'),
    ]

    name = models.CharField(max_length=200)

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name='products'
    )

    size = models.CharField(
        max_length=50,
        blank=True
    )

    thickness = models.CharField(
        max_length=50,
        blank=True
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    stock_quantity = models.PositiveIntegerField(
        default=0
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return (
            self.stock_quantity <= self.low_stock_threshold
        )


class StockMovement(models.Model):

    MOVEMENT_TYPES = [
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("ADJUSTMENT", "Adjustment"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_movements"
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES
    )

    quantity = models.PositiveIntegerField()

    note = models.CharField(
        max_length=255,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.movement_type} - "
            f"{self.quantity}"
        )