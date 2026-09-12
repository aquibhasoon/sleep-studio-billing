from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Product, Manufacturer, StockMovement


@login_required
def inventory(request):

    products = Product.objects.filter(
        is_active=True
    ).select_related("manufacturer")

    search = request.GET.get(
        "search",
        ""
    ).strip()

    category = request.GET.get(
        "category",
        ""
    )

    manufacturer = request.GET.get(
        "manufacturer",
        ""
    )

    if search:
        products = products.filter(
            name__icontains=search
        )

    if category:
        products = products.filter(
            category=category
        )

    if manufacturer:
        products = products.filter(
            manufacturer_id=manufacturer
        )

    manufacturers = Manufacturer.objects.filter(
        is_active=True
    )

    return render(
        request,
        "products/inventory.html",
        {
            "products": products,
            "manufacturers": manufacturers,
            "selected_category": category,
            "selected_manufacturer": manufacturer,
            "search": search,
        }
    )


@login_required
def stock_in(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    if request.method == "POST":

        quantity = int(
            request.POST.get(
                "quantity",
                0
            )
        )

        if quantity > 0:

            product.stock_quantity += quantity

            product.save(
                update_fields=[
                    "stock_quantity"
                ]
            )

            StockMovement.objects.create(
                product=product,
                movement_type="IN",
                quantity=quantity,
                note="Stock added"
            )

        return redirect("inventory")

    return render(
        request,
        "products/stock_in.html",
        {
            "product": product,
        }
    )


@login_required
def stock_adjustment(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    if request.method == "POST":

        try:
            new_quantity = int(
                request.POST.get(
                    "new_quantity",
                    0
                )
            )
        except (ValueError, TypeError):

            return render(
                request,
                "products/stock_adjustment.html",
                {
                    "product": product,
                    "error": "Please enter a valid stock quantity.",
                }
            )

        if new_quantity < 0:

            return render(
                request,
                "products/stock_adjustment.html",
                {
                    "product": product,
                    "error": "Stock quantity cannot be negative.",
                }
            )

        old_quantity = product.stock_quantity

        difference = new_quantity - old_quantity

        if difference == 0:

            return redirect("inventory")

        product.stock_quantity = new_quantity

        product.save(
            update_fields=[
                "stock_quantity"
            ]
        )

        StockMovement.objects.create(
            product=product,
            movement_type="ADJUSTMENT",
            quantity=abs(difference),
            note=(
                f"Stock adjusted from "
                f"{old_quantity} to "
                f"{new_quantity}"
            )
        )

        return redirect("inventory")

    return render(
        request,
        "products/stock_adjustment.html",
        {
            "product": product,
        }
    )


@login_required
def stock_history(request):

    movements = StockMovement.objects.select_related(
        "product"
    ).order_by(
        "-created_at"
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    movement_type = request.GET.get(
        "movement_type",
        ""
    )

    if search:

        movements = movements.filter(
            product__name__icontains=search
        )

    if movement_type:

        movements = movements.filter(
            movement_type=movement_type
        )

    return render(
        request,
        "products/stock_history.html",
        {
            "movements": movements,
            "search": search,
            "selected_movement_type": movement_type,
        }
    )


@login_required
def manage_products(request):

    tab = request.GET.get(
        "tab",
        "products"
    )

    if request.method == "POST":

        action = request.POST.get(
            "action"
        )

        # ==================================================
        # ADD MANUFACTURER
        # ==================================================

        if action == "add_manufacturer":

            name = request.POST.get(
                "name",
                ""
            ).strip()

            if name:

                Manufacturer.objects.create(
                    name=name
                )

            return redirect(
                "/products/manage/?tab=manufacturers"
            )

        # ==================================================
        # ADD PRODUCT
        # ==================================================

        elif action == "add_product":

            low_stock_threshold = request.POST.get(
                "low_stock_threshold",
                5
            )

            Product.objects.create(

                name=request.POST.get(
                    "name",
                    ""
                ).strip(),

                category=request.POST.get(
                    "category"
                ),

                manufacturer_id=request.POST.get(
                    "manufacturer"
                ),

                size=request.POST.get(
                    "size",
                    ""
                ).strip(),

                thickness=request.POST.get(
                    "thickness",
                    ""
                ).strip(),

                cost_price=request.POST.get(
                    "cost_price"
                ),

                selling_price=request.POST.get(
                    "selling_price"
                ),

                stock_quantity=request.POST.get(
                    "stock_quantity",
                    0
                ),

                low_stock_threshold=low_stock_threshold,
            )

            return redirect(
                "/products/manage/?tab=products"
            )

        # ==================================================
        # EDIT PRODUCT
        # ==================================================

        elif action == "edit_product":

            product_id = request.POST.get(
                "product_id"
            )

            product = get_object_or_404(
                Product,
                id=product_id
            )

            product.name = request.POST.get(
                "name",
                ""
            ).strip()

            product.category = request.POST.get(
                "category"
            )

            product.manufacturer_id = request.POST.get(
                "manufacturer"
            )

            product.size = request.POST.get(
                "size",
                ""
            ).strip()

            product.thickness = request.POST.get(
                "thickness",
                ""
            ).strip()

            product.cost_price = request.POST.get(
                "cost_price"
            )

            product.selling_price = request.POST.get(
                "selling_price"
            )

            product.low_stock_threshold = request.POST.get(
                "low_stock_threshold",
                5
            )

            product.save()

            return redirect(
                "/products/manage/?tab=products"
            )

        # ==================================================
        # TOGGLE PRODUCT
        # ==================================================

        elif action == "toggle_product":

            product_id = request.POST.get(
                "product_id"
            )

            product = get_object_or_404(
                Product,
                id=product_id
            )

            product.is_active = not product.is_active

            product.save(
                update_fields=[
                    "is_active"
                ]
            )

            return redirect(
                "/products/manage/?tab=products"
            )

        # ==================================================
        # EDIT MANUFACTURER
        # ==================================================

        elif action == "edit_manufacturer":

            manufacturer_id = request.POST.get(
                "manufacturer_id"
            )

            manufacturer = get_object_or_404(
                Manufacturer,
                id=manufacturer_id
            )

            name = request.POST.get(
                "name",
                ""
            ).strip()

            if name:

                manufacturer.name = name

                manufacturer.save()

            return redirect(
                "/products/manage/?tab=manufacturers"
            )

        # ==================================================
        # TOGGLE MANUFACTURER
        # ==================================================

        elif action == "toggle_manufacturer":

            manufacturer_id = request.POST.get(
                "manufacturer_id"
            )

            manufacturer = get_object_or_404(
                Manufacturer,
                id=manufacturer_id
            )

            manufacturer.is_active = not manufacturer.is_active

            manufacturer.save(
                update_fields=[
                    "is_active"
                ]
            )

            return redirect(
                "/products/manage/?tab=manufacturers"
            )

    products = Product.objects.all().select_related(
        "manufacturer"
    ).order_by(
        "-created_at"
    )

    manufacturers = Manufacturer.objects.all().order_by(
        "name"
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    category = request.GET.get(
        "category",
        ""
    )

    manufacturer = request.GET.get(
        "manufacturer",
        ""
    )

    if search:

        products = products.filter(
            name__icontains=search
        )

    if category:

        products = products.filter(
            category=category
        )

    if manufacturer:

        products = products.filter(
            manufacturer_id=manufacturer
        )

    edit_product = None

    edit_id = request.GET.get(
        "edit"
    )

    if edit_id and tab == "edit":

        edit_product = get_object_or_404(
            Product,
            id=edit_id
        )

    edit_manufacturer = None

    manufacturer_edit_id = request.GET.get(
        "manufacturer_edit"
    )

    if manufacturer_edit_id:

        edit_manufacturer = get_object_or_404(
            Manufacturer,
            id=manufacturer_edit_id
        )

    context = {
        "tab": tab,
        "products": products,
        "manufacturers": manufacturers,
        "selected_category": category,
        "selected_manufacturer": manufacturer,
        "search": search,
        "edit_product": edit_product,
        "edit_manufacturer": edit_manufacturer,
    }

    return render(
        request,
        "products/manage_products.html",
        context
    )