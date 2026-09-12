from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Customer


@login_required
def customer_list(request):
    customers = Customer.objects.all().order_by("name")

    search = request.GET.get("search", "").strip()

    if search:
        customers = customers.filter(
            Q(name__icontains=search)
            | Q(phone__icontains=search)
        )

    return render(
        request,
        "customers/customer_list.html",
        {
            "customers": customers,
            "search": search,
        },
    )


@login_required
def create_customer(request):
    """
    Creates a customer from the New Bill page.

    This is an AJAX endpoint.
    It does not render a separate customer page.
    """

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request method."
            },
            status=405
        )

    name = request.POST.get("name", "").strip()
    phone = request.POST.get("phone", "").strip()
    address = request.POST.get("address", "").strip()

    if not name:
        return JsonResponse(
            {
                "success": False,
                "error": "Customer name is required."
            },
            status=400
        )

    if not phone:
        return JsonResponse(
            {
                "success": False,
                "error": "Phone number is required."
            },
            status=400
        )

    customer = Customer.objects.create(
        name=name,
        phone=phone,
        address=address,
    )

    return JsonResponse(
        {
            "success": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "address": customer.address,
            }
        }
    )


@login_required
def customer_edit(request, customer_id):
    customer = get_object_or_404(
        Customer,
        id=customer_id
    )

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        if not name:
            return render(
                request,
                "customers/edit_customer.html",
                {
                    "customer": customer,
                    "error": "Customer name is required.",
                },
            )

        if not phone:
            return render(
                request,
                "customers/edit_customer.html",
                {
                    "customer": customer,
                    "error": "Phone number is required.",
                },
            )

        customer.name = name
        customer.phone = phone
        customer.address = address
        customer.save()

        return redirect(
            "customer_detail",
            customer_id=customer.id
        )

    return render(
        request,
        "customers/edit_customer.html",
        {
            "customer": customer,
        },
    )


@login_required
def customer_detail(request, customer_id):
    customer = get_object_or_404(
        Customer,
        id=customer_id
    )

    invoices = (
        customer.invoices
        .all()
        .order_by("-date")
    )

    total_bills = invoices.count()

    total_purchases = (
        invoices.aggregate(
            total=Sum("grand_total")
        )["total"]
        or 0
    )

    total_paid = (
        invoices.aggregate(
            total=Sum("amount_paid")
        )["total"]
        or 0
    )

    outstanding = (
        invoices.aggregate(
            total=Sum("balance")
        )["total"]
        or 0
    )

    return render(
        request,
        "customers/customer_detail.html",
        {
            "customer": customer,
            "invoices": invoices,
            "total_bills": total_bills,
            "total_purchases": total_purchases,
            "total_paid": total_paid,
            "outstanding": outstanding,
        },
    )