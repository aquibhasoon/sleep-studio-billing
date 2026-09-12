from django.urls import path

from .views import (
    create_sale,
    invoice_history,
    invoice_detail,
    invoice_pdf,
    outstanding_bills,
    collect_payment,
    payment_history,
)

urlpatterns = [
    path("new/", create_sale, name="create_sale"),
    path("history/", invoice_history, name="invoice_history"),
    path("invoice/<int:invoice_id>/", invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/pdf/", invoice_pdf, name="invoice_pdf"),
    path("outstanding/", outstanding_bills, name="outstanding_bills"),
    path("invoice/<int:invoice_id>/payment/", collect_payment, name="collect_payment"),
    path("payments/", payment_history, name="payment_history"),
]
