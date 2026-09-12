from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from customers.models import Customer
from products.models import Product
from .models import Invoice, InvoiceItem, Payment
from .services import create_invoice


@login_required
def create_sale(request):

    if request.method == "POST":

        try:
            customer_id = request.POST.get("customer")
            customer = None

            if customer_id:
                customer = Customer.objects.get(id=customer_id)

            product_ids = request.POST.getlist("product_id")
            quantities = request.POST.getlist("quantity")
            item_discounts = request.POST.getlist("item_discount")

            if not product_ids:
                raise ValueError(
                    "Invoice must contain at least one item."
                )

            if len(product_ids) != len(quantities):
                raise ValueError(
                    "Invalid product or quantity data."
                )

            items = []

            for i in range(len(product_ids)):

                product = get_object_or_404(
                    Product,
                    id=product_ids[i],
                    is_active=True
                )

                try:
                    quantity = int(quantities[i])
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Invalid quantity for {product.name}."
                    )

                if quantity <= 0:
                    raise ValueError(
                        f"Quantity must be greater than zero for "
                        f"{product.name}."
                    )

                try:
                    item_discount = Decimal(
                        item_discounts[i]
                        if i < len(item_discounts)
                        else "0"
                    )
                except (InvalidOperation, ValueError):
                    raise ValueError(
                        f"Invalid discount for {product.name}."
                    )

                items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "unit_price": product.selling_price,
                        "discount": item_discount,
                    }
                )

            invoice = create_invoice(
                customer=customer,
                items=items,
                discount=request.POST.get(
                    "discount",
                    "0"
                ),
                tax_percentage=request.POST.get(
                    "tax",
                    "0"
                ),
                payment_amount=request.POST.get(
                    "amount_paid",
                    "0"
                ),
                payment_method=request.POST.get(
                    "payment_method"
                ),
                payment_reference=request.POST.get(
                    "payment_reference",
                    ""
                ),
            )

            amount_received = Decimal(
                request.POST.get(
                    "amount_paid",
                    "0"
                )
            )

            actual_payment = invoice.amount_paid

            change_amount = max(
                amount_received - invoice.grand_total,
                Decimal("0.00")
            )

            return render(
                request,
                "sales/invoice_success.html",
                {
                    "invoice": invoice,
                    "amount_received": amount_received,
                    "actual_payment": actual_payment,
                    "change_amount": change_amount,
                },
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    products = Product.objects.filter(
        is_active=True
    ).select_related(
        "manufacturer"
    )

    customers = Customer.objects.all().order_by(
        "name"
    )

    return render(
        request,
        "sales/create_sale.html",
        {
            "products": products,
            "customers": customers,
        },
    )


@login_required
def invoice_history(request):

    invoices = (
        Invoice.objects
        .select_related("customer")
        .order_by("-date")
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    )

    if search:
        invoices = invoices.filter(
            invoice_number__icontains=search
        )

    if status:
        invoices = invoices.filter(
            payment_status=status
        )

    return render(
        request,
        "sales/invoice_history.html",
        {
            "invoices": invoices,
            "search": search,
            "selected_status": status,
        },
    )


@login_required
def invoice_detail(request, invoice_id):

    invoice = get_object_or_404(
        Invoice.objects.select_related("customer"),
        id=invoice_id
    )

    payments = invoice.payments.order_by(
        "-date"
    )

    total_payments = sum(
        (
            payment.amount
            for payment in payments
        ),
        Decimal("0.00")
    )

    return render(
        request,
        "sales/invoice_success.html",
        {
            "invoice": invoice,
            "payments": payments,
            "total_payments": total_payments,
            "amount_received": invoice.amount_paid,
            "actual_payment": invoice.amount_paid,
            "change_amount": 0,
        },
    )


@login_required
def invoice_pdf(request, invoice_id):

    invoice = get_object_or_404(
        Invoice.objects
        .select_related("customer")
        .prefetch_related(
            "items__product",
            "payments",
        ),
        id=invoice_id
    )

    try:
        from pathlib import Path

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            ParagraphStyle,
            getSampleStyleSheet,
        )
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

    except ImportError:

        return HttpResponse(
            "ReportLab is not installed. "
            "Run: pip install reportlab",
            status=500
        )

    # --------------------------------------------------
    # FONT SETUP
    # --------------------------------------------------

    # DejaVu Sans supports the Indian Rupee symbol.
    # We check common Linux and Windows locations.
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    bold_font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]

    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"

    regular_font_path = None
    bold_font_path = None

    for path in font_paths:

        if Path(path).exists():
            regular_font_path = path
            break

    for path in bold_font_paths:

        if Path(path).exists():
            bold_font_path = path
            break

    if regular_font_path:

        try:
            pdfmetrics.registerFont(
                TTFont(
                    "SleepStudioFont",
                    regular_font_path
                )
            )

            regular_font = "SleepStudioFont"

        except Exception:
            pass

    if bold_font_path:

        try:
            pdfmetrics.registerFont(
                TTFont(
                    "SleepStudioFontBold",
                    bold_font_path
                )
            )

            bold_font = "SleepStudioFontBold"

        except Exception:
            pass

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; '
        f'filename="Invoice-{invoice.invoice_number}.pdf"'
    )

    # --------------------------------------------------
    # DOCUMENT
    # --------------------------------------------------

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
        title=f"Invoice {invoice.invoice_number}",
        author="SLEEP STUDIO",
    )

    styles = getSampleStyleSheet()

    # --------------------------------------------------
    # STYLES
    # --------------------------------------------------

    shop_name_style = ParagraphStyle(
        "ShopName",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=22,
        leading=25,
        textColor=colors.HexColor("#171717"),
        spaceAfter=2,
    )

    tagline_style = ParagraphStyle(
        "Tagline",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#777777"),
    )

    shop_details_style = ParagraphStyle(
        "ShopDetails",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#444444"),
    )

    invoice_title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=22,
        leading=25,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#171717"),
    )

    invoice_meta_style = ParagraphStyle(
        "InvoiceMeta",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=8.5,
        leading=13,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#555555"),
    )

    section_label_style = ParagraphStyle(
        "SectionLabel",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#777777"),
        letterSpacing=0.5,
    )

    customer_name_style = ParagraphStyle(
        "CustomerName",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#222222"),
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#444444"),
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#666666"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=7.5,
        leading=10,
        textColor=colors.white,
    )

    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#333333"),
    )

    table_body_bold_style = ParagraphStyle(
        "TableBodyBold",
        parent=table_body_style,
        fontName=bold_font,
    )

    right_body_style = ParagraphStyle(
        "RightBody",
        parent=table_body_style,
        alignment=TA_RIGHT,
    )

    right_small_style = ParagraphStyle(
        "RightSmall",
        parent=small_style,
        alignment=TA_RIGHT,
    )

    total_label_style = ParagraphStyle(
        "TotalLabel",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#171717"),
    )

    total_value_style = ParagraphStyle(
        "TotalValue",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=13,
        leading=16,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#171717"),
    )

    status_style = ParagraphStyle(
        "Status",
        parent=styles["Normal"],
        fontName=bold_font,
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#222222"),
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor("#666666"),
    )

    elements = []

    # --------------------------------------------------
    # HEADER
    # --------------------------------------------------

    shop_details = (
        "Thikkodi Panchayat,<br/>"
        "Thikkoti (P.O.) - 673529<br/>"
        "Phone: 7510800770"
    )

    invoice_details = (
        f"<b>Invoice No:</b> {invoice.invoice_number}<br/>"
        f"<b>Date:</b> {invoice.date.strftime('%d %b %Y')}<br/>"
        f"<b>Time:</b> {invoice.date.strftime('%I:%M %p')}"
    )

    header_left = [
        Paragraph(
            "SLEEP STUDIO",
            shop_name_style
        ),
        Paragraph(
            "Mattress &amp; Home Comfort",
            tagline_style
        ),
        Spacer(1, 5),
        Paragraph(
            shop_details,
            shop_details_style
        ),
    ]

    header_right = [
        Paragraph(
            "INVOICE",
            invoice_title_style
        ),
        Spacer(1, 3),
        Paragraph(
            invoice_details,
            invoice_meta_style
        ),
    ]

    header_table = Table(
        [[header_left, header_right]],
        colWidths=[
            105 * mm,
            65 * mm,
        ],
    )

    header_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, 0),
                    "RIGHT"
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    1.4,
                    colors.HexColor("#202020")
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    11
                ),
            ]
        )
    )

    elements.append(header_table)
    elements.append(Spacer(1, 11))

    # --------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------

    if invoice.customer:

        customer_content = [
            Paragraph(
                "BILL TO",
                section_label_style
            ),
            Spacer(1, 2),
            Paragraph(
                invoice.customer.name,
                customer_name_style
            ),
            Paragraph(
                f"Phone: {invoice.customer.phone}",
                body_style
            ),
        ]

        if invoice.customer.address:

            customer_content.append(
                Paragraph(
                    invoice.customer.address,
                    body_style
                )
            )

    else:

        customer_content = [
            Paragraph(
                "BILL TO",
                section_label_style
            ),
            Spacer(1, 2),
            Paragraph(
                "Walk-in Customer",
                customer_name_style
            ),
        ]

    customer_table = Table(
        [[customer_content]],
        colWidths=[170 * mm],
    )

    customer_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F7F7F7")
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#DDDDDD")
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
            ]
        )
    )

    elements.append(customer_table)
    elements.append(Spacer(1, 13))

    # --------------------------------------------------
    # ITEM TABLE
    # --------------------------------------------------

    item_rows = [
        [
            Paragraph("PRODUCT", table_header_style),
            Paragraph("QTY", table_header_style),
            Paragraph("UNIT PRICE", table_header_style),
            Paragraph("TOTAL", table_header_style),
        ]
    ]

    for item in invoice.items.all():

        product_content = [
            Paragraph(
                item.product.name,
                table_body_bold_style
            )
        ]

        product_details = []

        if item.product.size:

            product_details.append(
                f"Size: {item.product.size}"
            )

        if item.product.thickness:

            product_details.append(
                f"Thickness: {item.product.thickness}"
            )

        if product_details:

            product_content.append(
                Paragraph(
                    " | ".join(product_details),
                    small_style
                )
            )

        item_rows.append(
            [
                product_content,
                Paragraph(
                    str(item.quantity),
                    right_body_style
                ),
                Paragraph(
                    f"₹{item.unit_price:,.2f}",
                    right_body_style
                ),
                Paragraph(
                    f"₹{item.total:,.2f}",
                    right_body_style
                ),
            ]
        )

    items_table = Table(
        item_rows,
        colWidths=[
            86 * mm,
            18 * mm,
            33 * mm,
            33 * mm,
        ],
        repeatRows=1,
    )

    items_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#242424")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    colors.HexColor("#DCDCDC")
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
            ]
        )
    )

    elements.append(items_table)
    elements.append(Spacer(1, 11))

    # --------------------------------------------------
    # TOTALS
    # --------------------------------------------------

    totals_rows = [
        [
            Paragraph(
                "Subtotal",
                body_style
            ),
            Paragraph(
                f"₹{invoice.subtotal:,.2f}",
                right_body_style
            ),
        ],
        [
            Paragraph(
                "Discount",
                body_style
            ),
            Paragraph(
                f"₹{invoice.discount:,.2f}",
                right_body_style
            ),
        ],
        [
            Paragraph(
                f"Tax ({invoice.tax_percentage}%)",
                body_style
            ),
            Paragraph(
                f"₹{invoice.tax_amount:,.2f}",
                right_body_style
            ),
        ],
        [
            Paragraph(
                "GRAND TOTAL",
                total_label_style
            ),
            Paragraph(
                f"₹{invoice.grand_total:,.2f}",
                total_value_style
            ),
        ],
    ]

    totals_table = Table(
        totals_rows,
        colWidths=[
            125 * mm,
            45 * mm,
    ])

    totals_table.setStyle(
        TableStyle(
            [
                (
                    "ALIGN",
                    (1, 0),
                    (1, -1),
                    "RIGHT"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -2),
                    4
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -2),
                    4
                ),
                (
                    "LINEABOVE",
                    (0, -1),
                    (-1, -1),
                    1.5,
                    colors.HexColor("#202020")
                ),
                (
                    "TOPPADDING",
                    (0, -1),
                    (-1, -1),
                    8
                ),
                (
                    "BOTTOMPADDING",
                    (0, -1),
                    (-1, -1),
                    5
                ),
            ]
        )
    )

    elements.append(totals_table)
    elements.append(Spacer(1, 13))

    # --------------------------------------------------
    # PAYMENT DETAILS
    # --------------------------------------------------

    payment_rows = [
        [
            Paragraph(
                "PAYMENT DETAILS",
                section_label_style
            ),
            "",
        ],
        [
            Paragraph(
                "Amount Paid",
                body_style
            ),
            Paragraph(
                f"₹{invoice.amount_paid:,.2f}",
                right_body_style
            ),
        ],
        [
            Paragraph(
                "Balance",
                body_style
            ),
            Paragraph(
                f"₹{invoice.balance:,.2f}",
                right_body_style
            ),
        ],
        [
            Paragraph(
                "Payment Status",
                body_style
            ),
            Paragraph(
                invoice.get_payment_status_display().upper(),
                status_style
            ),
        ],
    ]

    payment_table = Table(
        payment_rows,
        colWidths=[
            125 * mm,
            45 * mm,
        ],
    )

    payment_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F7F7F7")
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#DDDDDD")
                ),
                (
                    "SPAN",
                    (0, 0),
                    (1, 0)
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    0.5,
                    colors.HexColor("#DDDDDD")
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
            ]
        )
    )

    elements.append(payment_table)

    # --------------------------------------------------
    # PAYMENT HISTORY
    # --------------------------------------------------

    payments = invoice.payments.all()

    if payments.exists():

        elements.append(Spacer(1, 13))

        elements.append(
            Paragraph(
                "PAYMENT HISTORY",
                section_label_style
            )
        )

        elements.append(Spacer(1, 5))

        payment_history_rows = [
            [
                Paragraph(
                    "DATE",
                    table_header_style
                ),
                Paragraph(
                    "METHOD",
                    table_header_style
                ),
                Paragraph(
                    "REFERENCE",
                    table_header_style
                ),
                Paragraph(
                    "AMOUNT",
                    table_header_style
                ),
            ]
        ]

        method_names = {
            "CASH": "Cash",
            "UPI": "UPI",
            "CARD": "Card",
            "BANK": "Bank Transfer",
        }

        for payment in payments:

            method = method_names.get(
                payment.method,
                payment.method
            )

            reference = (
                payment.reference
                if payment.reference
                else "—"
            )

            payment_history_rows.append(
                [
                    Paragraph(
                        payment.date.strftime(
                            "%d %b %Y, %I:%M %p"
                        ),
                        small_style
                    ),
                    Paragraph(
                        method,
                        small_style
                    ),
                    Paragraph(
                        reference,
                        small_style
                    ),
                    Paragraph(
                        f"₹{payment.amount:,.2f}",
                        right_small_style
                    ),
                ]
            )

        payment_history_table = Table(
            payment_history_rows,
            colWidths=[
                48 * mm,
                35 * mm,
                55 * mm,
                32 * mm,
            ],
            repeatRows=1,
        )

        payment_history_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#242424")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white
                    ),
                    (
                        "LINEBELOW",
                        (0, 0),
                        (-1, -1),
                        0.45,
                        colors.HexColor("#DDDDDD")
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),
                ]
            )
        )

        elements.append(
            payment_history_table
        )

    # --------------------------------------------------
    # FOOTER
    # --------------------------------------------------

    elements.append(Spacer(1, 20))

    footer_left = Paragraph(
        "<b>Thank you for choosing SLEEP STUDIO!</b><br/>"
        "We appreciate your business.<br/>"
        "Phone: 7510800770",
        footer_style
    )

    footer_right = Paragraph(
        "_________________________<br/>"
        "Authorized Signature",
        ParagraphStyle(
            "Signature",
            parent=footer_style,
            alignment=TA_RIGHT,
        )
    )

    footer_table = Table(
        [[
            footer_left,
            footer_right
        ]],
        colWidths=[
            105 * mm,
            65 * mm,
        ],
    )

    footer_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "BOTTOM"
                ),
                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    0.5,
                    colors.HexColor("#DDDDDD")
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    9
                ),
            ]
        )
    )

    elements.append(footer_table)

    # --------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------

    doc.build(elements)

    return response


@login_required
def outstanding_bills(request):

    invoices = (
        Invoice.objects
        .select_related("customer")
        .filter(balance__gt=0)
        .order_by("-date")
    )

    return render(
        request,
        "sales/outstanding_bills.html",
        {
            "invoices": invoices,
        },
    )


@login_required
def collect_payment(request, invoice_id):

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id
    )

    if request.method == "POST":

        amount = request.POST.get(
            "amount",
            ""
        ).strip()

        method = request.POST.get(
            "method",
            ""
        )

        reference = request.POST.get(
            "reference",
            ""
        ).strip()

        try:
            amount = Decimal(amount)

        except (InvalidOperation, ValueError):

            return render(
                request,
                "sales/collect_payment.html",
                {
                    "invoice": invoice,
                    "error": (
                        "Please enter a valid amount."
                    ),
                },
            )

        if amount <= 0:

            return render(
                request,
                "sales/collect_payment.html",
                {
                    "invoice": invoice,
                    "error": (
                        "Payment amount must be greater "
                        "than zero."
                    ),
                },
            )

        if amount > invoice.balance:

            return render(
                request,
                "sales/collect_payment.html",
                {
                    "invoice": invoice,
                    "error": (
                        f"Payment cannot exceed the outstanding "
                        f"balance of ₹{invoice.balance}."
                    ),
                },
            )

        if not method:

            return render(
                request,
                "sales/collect_payment.html",
                {
                    "invoice": invoice,
                    "error": (
                        "Payment method is required."
                    ),
                },
            )

        Payment.objects.create(
            invoice=invoice,
            amount=amount,
            method=method,
            reference=reference
        )

        invoice.amount_paid += amount

        invoice.balance = (
            invoice.grand_total
            - invoice.amount_paid
        )

        if invoice.balance <= 0:

            invoice.balance = Decimal("0.00")
            invoice.payment_status = "PAID"

        else:

            invoice.payment_status = "PARTIAL"

        invoice.save(
            update_fields=[
                "amount_paid",
                "balance",
                "payment_status"
            ]
        )

        return redirect(
            "invoice_detail",
            invoice_id=invoice.id
        )

    return render(
        request,
        "sales/collect_payment.html",
        {
            "invoice": invoice
        }
    )


@login_required
def payment_history(request):

    payments = (
        Payment.objects
        .select_related(
            "invoice",
            "invoice__customer"
        )
        .order_by("-date")
    )

    return render(
        request,
        "sales/payment_history.html",
        {
            "payments": payments,
        },
    )