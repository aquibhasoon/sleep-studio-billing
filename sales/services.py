from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import Invoice, InvoiceItem, Payment
from products.models import Product, StockMovement


@transaction.atomic
def create_invoice(
    customer,
    items,
    discount=Decimal("0.00"),
    tax_percentage=Decimal("0.00"),
    payment_amount=Decimal("0.00"),
    payment_method=None,
    payment_reference="",
):
    """
    Create an invoice, invoice items, payment and update stock
    as one atomic database transaction.

    items should be a list of dictionaries:

    {
        "product": Product object,
        "quantity": 2,
        "unit_price": Decimal("15000.00"),
        "discount": Decimal("0.00")
    }
    """

    # --------------------------------------------------
    # 1. Validate basic values
    # --------------------------------------------------

    try:
        discount = Decimal(discount)
        tax_percentage = Decimal(tax_percentage)
        payment_amount = Decimal(payment_amount)

    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(
            "Invalid invoice amount."
        )

    if discount < 0:
        raise ValueError(
            "Discount cannot be negative."
        )

    if tax_percentage < 0:
        raise ValueError(
            "Tax percentage cannot be negative."
        )

    if payment_amount < 0:
        raise ValueError(
            "Payment amount cannot be negative."
        )

    if not items:
        raise ValueError(
            "Invoice must contain at least one item."
        )

    # --------------------------------------------------
    # 2. Generate invoice number
    # --------------------------------------------------

    last_invoice = (
        Invoice.objects
        .select_for_update()
        .order_by("-id")
        .first()
    )

    if last_invoice:

        try:
            last_number = int(
                last_invoice.invoice_number.replace(
                    "INV-",
                    ""
                )
            )

        except (ValueError, AttributeError):
            raise ValueError(
                "Invalid invoice number format."
            )

        next_number = last_number + 1

    else:

        next_number = 1

    invoice_number = (
        f"INV-{next_number:06d}"
    )

    # --------------------------------------------------
    # 3. Create invoice
    # --------------------------------------------------

    invoice = Invoice.objects.create(
        invoice_number=invoice_number,
        customer=customer,
        subtotal=Decimal("0.00"),
        discount=discount,
        tax_percentage=tax_percentage,
        tax_amount=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        amount_paid=Decimal("0.00"),
        balance=Decimal("0.00"),
        payment_status="UNPAID",
    )

    subtotal = Decimal("0.00")

    # --------------------------------------------------
    # 4. Create invoice items + update stock
    # --------------------------------------------------

    for item in items:

        product = item["product"]

        try:
            quantity = int(
                item["quantity"]
            )

        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid quantity for {product.name}."
            )

        if quantity <= 0:
            raise ValueError(
                f"Invalid quantity for {product.name}."
            )

        # Lock the product row so two simultaneous sales
        # cannot oversell the same stock.
        product = (
            Product.objects
            .select_for_update()
            .get(
                id=product.id,
                is_active=True
            )
        )

        if product.stock_quantity < quantity:

            raise ValueError(
                f"Insufficient stock for {product.name}. "
                f"Available: {product.stock_quantity}"
            )

        # Always use the current database selling price.
        # The browser-submitted price is intentionally ignored.
        unit_price = product.selling_price

        try:
            item_discount = Decimal(
                item.get(
                    "discount",
                    "0.00"
                )
            )

        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(
                f"Invalid discount for {product.name}."
            )

        if unit_price < 0:
            raise ValueError(
                "Unit price cannot be negative."
            )

        if item_discount < 0:
            raise ValueError(
                "Item discount cannot be negative."
            )

        item_total = (
            unit_price * quantity
        ) - item_discount

        if item_total < 0:

            raise ValueError(
                f"Discount cannot exceed item price "
                f"for {product.name}."
            )

        InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            cost_price=product.cost_price,
            discount=item_discount,
            total=item_total,
        )

        subtotal += item_total

        # --------------------------------------------------
        # Reduce stock
        # --------------------------------------------------

        product.stock_quantity -= quantity

        product.save(
            update_fields=[
                "stock_quantity"
            ]
        )

        # --------------------------------------------------
        # Record stock movement
        # --------------------------------------------------

        StockMovement.objects.create(
            product=product,
            movement_type="OUT",
            quantity=quantity,
            note=(
                f"Sold in invoice "
                f"{invoice.invoice_number}"
            )
        )

    # --------------------------------------------------
    # 5. Calculate totals
    # --------------------------------------------------

    taxable_amount = (
        subtotal - discount
    )

    if taxable_amount < 0:
        raise ValueError(
            "Invoice discount cannot exceed subtotal."
        )

    tax_amount = (
        taxable_amount
        * tax_percentage
        / Decimal("100")
    )

    grand_total = (
        taxable_amount
        + tax_amount
    )

    # --------------------------------------------------
    # 6. Validate payment
    # --------------------------------------------------

    if payment_amount > grand_total:

        actual_payment = grand_total

    else:

        actual_payment = payment_amount

    balance = (
        grand_total
        - actual_payment
    )

    if actual_payment == 0:

        payment_status = "UNPAID"

    elif actual_payment < grand_total:

        payment_status = "PARTIAL"

    else:

        payment_status = "PAID"

    # --------------------------------------------------
    # 7. Update invoice
    # --------------------------------------------------

    invoice.subtotal = subtotal
    invoice.tax_amount = tax_amount
    invoice.grand_total = grand_total
    invoice.amount_paid = actual_payment
    invoice.balance = balance
    invoice.payment_status = payment_status

    invoice.save()

    # --------------------------------------------------
    # 8. Create payment record
    # --------------------------------------------------

    if actual_payment > 0:

        if not payment_method:
            raise ValueError(
                "Payment method is required."
            )

        Payment.objects.create(
            invoice=invoice,
            amount=actual_payment,
            method=payment_method,
            reference=payment_reference,
        )

    return invoice