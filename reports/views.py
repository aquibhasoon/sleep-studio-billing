from decimal import Decimal
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from products.models import Product
from sales.models import Invoice, Payment


@login_required
def dashboard(request):

    today = timezone.localdate()

    today_invoices = Invoice.objects.filter(
        date__date=today
    )

    today_sales = today_invoices.aggregate(
        total=Sum("grand_total")
    )["total"] or Decimal("0.00")

    today_bills = today_invoices.count()

    outstanding = Invoice.objects.filter(
        balance__gt=0
    ).aggregate(
        total=Sum("balance")
    )["total"] or Decimal("0.00")

    total_products = Product.objects.filter(
        is_active=True
    ).count()

    low_stock_products = Product.objects.filter(
        is_active=True,
        stock_quantity__lte=5
    ).select_related("manufacturer")

    low_stock_count = low_stock_products.count()

    recent_invoices = Invoice.objects.select_related(
        "customer"
    ).order_by("-date")[:5]

    return render(
        request,
        "reports/dashboard.html",
        {
            "today_sales": today_sales,
            "today_bills": today_bills,
            "outstanding": outstanding,
            "total_products": total_products,
            "low_stock_count": low_stock_count,
            "low_stock_products": low_stock_products,
            "recent_invoices": recent_invoices,
        }
    )


@login_required
def daily_sales(request):

    selected_date = request.GET.get("date")

    if selected_date:
        try:
            report_date = date.fromisoformat(selected_date)
        except ValueError:
            report_date = date.today()
    else:
        report_date = date.today()

    invoices = Invoice.objects.filter(
        date__date=report_date
    ).select_related(
        "customer"
    ).order_by("-date")

    total_sales = sum(
        invoice.grand_total
        for invoice in invoices
    )

    total_paid = sum(
        invoice.amount_paid
        for invoice in invoices
    )

    total_outstanding = sum(
        invoice.balance
        for invoice in invoices
    )

    total_bills = invoices.count()

    return render(
        request,
        "reports/daily_sales.html",
        {
            "invoices": invoices,
            "report_date": report_date,
            "total_sales": total_sales,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "total_bills": total_bills,
        }
    )


@login_required
def reports_page(request):

    report_type = request.GET.get("type", "daily")

    # -------------------------
    # DAILY SALES
    # -------------------------

    if report_type == "daily":

        selected_date = request.GET.get("date")

        if selected_date:
            try:
                report_date = date.fromisoformat(selected_date)
            except ValueError:
                report_date = date.today()
        else:
            report_date = date.today()

        invoices = Invoice.objects.filter(
            date__date=report_date
        ).select_related(
            "customer"
        ).order_by("-date")

        total_sales = sum(
            invoice.grand_total
            for invoice in invoices
        )

        total_paid = sum(
            invoice.amount_paid
            for invoice in invoices
        )

        total_outstanding = sum(
            invoice.balance
            for invoice in invoices
        )

        total_bills = invoices.count()

        context = {
            "report_type": report_type,
            "report_date": report_date,
            "invoices": invoices,
            "total_sales": total_sales,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "total_bills": total_bills,
        }

    # -------------------------
    # DATE RANGE SALES
    # -------------------------

    elif report_type == "range":

        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        if not from_date:
            from_date = date.today().isoformat()

        if not to_date:
            to_date = date.today().isoformat()

        try:
            start_date = date.fromisoformat(from_date)
        except ValueError:
            start_date = date.today()
            from_date = start_date.isoformat()

        try:
            end_date = date.fromisoformat(to_date)
        except ValueError:
            end_date = date.today()
            to_date = end_date.isoformat()

        invoices = Invoice.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date
        ).select_related(
            "customer"
        ).order_by("-date")

        total_sales = sum(
            invoice.grand_total
            for invoice in invoices
        )

        total_paid = sum(
            invoice.amount_paid
            for invoice in invoices
        )

        total_outstanding = sum(
            invoice.balance
            for invoice in invoices
        )

        total_bills = invoices.count()

        context = {
            "report_type": report_type,
            "from_date": from_date,
            "to_date": to_date,
            "invoices": invoices,
            "total_sales": total_sales,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "total_bills": total_bills,
        }

    # -------------------------
    # PAYMENT METHOD REPORT
    # -------------------------

    elif report_type == "payment":

        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        if not from_date:
            from_date = date.today().isoformat()

        if not to_date:
            to_date = date.today().isoformat()

        try:
            start_date = date.fromisoformat(from_date)
        except ValueError:
            start_date = date.today()
            from_date = start_date.isoformat()

        try:
            end_date = date.fromisoformat(to_date)
        except ValueError:
            end_date = date.today()
            to_date = end_date.isoformat()

        payments = Payment.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date
        )

        cash_total = sum(
            payment.amount
            for payment in payments
            if payment.method == "CASH"
        )

        upi_total = sum(
            payment.amount
            for payment in payments
            if payment.method == "UPI"
        )

        card_total = sum(
            payment.amount
            for payment in payments
            if payment.method == "CARD"
        )

        bank_total = sum(
            payment.amount
            for payment in payments
            if payment.method == "BANK"
        )

        total_collected = sum(
            payment.amount
            for payment in payments
        )

        total_transactions = payments.count()

        context = {
            "report_type": report_type,
            "from_date": from_date,
            "to_date": to_date,
            "cash_total": cash_total,
            "upi_total": upi_total,
            "card_total": card_total,
            "bank_total": bank_total,
            "total_collected": total_collected,
            "total_transactions": total_transactions,
        }

    # -------------------------
    # PROFIT REPORT
    # -------------------------

    elif report_type == "profit":

        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        if not from_date:
            from_date = date.today().isoformat()

        if not to_date:
            to_date = date.today().isoformat()

        try:
            start_date = date.fromisoformat(from_date)
        except ValueError:
            start_date = date.today()
            from_date = start_date.isoformat()

        try:
            end_date = date.fromisoformat(to_date)
        except ValueError:
            end_date = date.today()
            to_date = end_date.isoformat()

        invoices = Invoice.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date
        ).prefetch_related(
            "items"
        )

        total_sales = Decimal("0.00")
        total_cost = Decimal("0.00")
        total_profit = Decimal("0.00")

        for invoice in invoices:

            items = list(invoice.items.all())

            if not items:
                continue

            # -----------------------------------------
            # Calculate total gross value of all items
            # before invoice-level discount.
            # -----------------------------------------

            invoice_gross_total = sum(
                (
                    item.unit_price * item.quantity
                    for item in items
                ),
                Decimal("0.00")
            )

            # Invoice-level discount cannot exceed the
            # invoice gross amount.

            invoice_discount = min(
                max(invoice.discount, Decimal("0.00")),
                invoice_gross_total
            )

            for item in items:

                item_gross = (
                    item.unit_price * item.quantity
                )

                # -----------------------------------------
                # Allocate invoice discount proportionally
                # according to each item's gross value.
                # -----------------------------------------

                if invoice_gross_total > 0:
                    allocated_invoice_discount = (
                        invoice_discount
                        * item_gross
                        / invoice_gross_total
                    )
                else:
                    allocated_invoice_discount = Decimal("0.00")

                # Item.total already represents the item's
                # value after its own item-level discount.
                #
                # Therefore:
                #
                # final sales value
                # = item.total - allocated invoice discount
                #

                sales_value = (
                    item.total
                    - allocated_invoice_discount
                )

                # Prevent negative sales values because of
                # unusual or invalid historical data.

                sales_value = max(
                    sales_value,
                    Decimal("0.00")
                )

                cost_value = (
                    item.cost_price * item.quantity
                )

                total_sales += sales_value
                total_cost += cost_value

                total_profit += (
                    sales_value - cost_value
                )

        context = {
            "report_type": report_type,
            "from_date": from_date,
            "to_date": to_date,
            "total_sales": total_sales,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "total_bills": invoices.count(),
        }

    # -------------------------
    # OUTSTANDING AMOUNT REPORT
    # -------------------------

    elif report_type == "outstanding":

        invoices = Invoice.objects.filter(
            balance__gt=0
        ).select_related(
            "customer"
        ).order_by(
            "-date"
        )

        total_outstanding = sum(
            invoice.balance
            for invoice in invoices
        )

        total_bills = invoices.count()

        context = {
            "report_type": report_type,
            "invoices": invoices,
            "total_outstanding": total_outstanding,
            "total_bills": total_bills,
        }

    # -------------------------
    # DEFAULT
    # -------------------------

    else:

        context = {
            "report_type": "daily",
            "report_date": date.today(),
            "invoices": [],
            "total_sales": 0,
            "total_paid": 0,
            "total_outstanding": 0,
            "total_bills": 0,
        }

    return render(
        request,
        "reports/reports.html",
        context
    )