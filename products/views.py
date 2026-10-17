from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Product, Manufacturer, StockMovement


@login_required
def inventory(request):
    products = Product.objects.filter(
        is_active=True
    ).select_related("manufacturer")

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    manufacturer = request.GET.get("manufacturer", "")

    if search:
        products = products.filter(name__icontains=search)

    if category:
        products = products.filter(category=category)

    if manufacturer:
        products = products.filter(manufacturer_id=manufacturer)

    manufacturers = Manufacturer.objects.filter(is_active=True)

    return render(
        request,
        "products/inventory.html",
        {
            "products": products,
            "manufacturers": manufacturers,
            "selected_category": category,
            "selected_manufacturer": manufacturer,
            "search": search,
        },
    )


@login_required
def stock_in(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
    )

    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 0))
        except (ValueError, TypeError):
            quantity = 0

        if quantity > 0:
            product.stock_quantity += quantity
            product.save(update_fields=["stock_quantity"])

            StockMovement.objects.create(
                product=product,
                movement_type="IN",
                quantity=quantity,
                note="Stock added",
            )

        return redirect("inventory")

    return render(
        request,
        "products/stock_in.html",
        {"product": product},
    )


@login_required
def stock_adjustment(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
    )

    if request.method == "POST":
        try:
            new_quantity = int(request.POST.get("new_quantity", 0))
        except (ValueError, TypeError):
            return render(
                request,
                "products/stock_adjustment.html",
                {
                    "product": product,
                    "error": "Please enter a valid stock quantity.",
                },
            )

        if new_quantity < 0:
            return render(
                request,
                "products/stock_adjustment.html",
                {
                    "product": product,
                    "error": "Stock quantity cannot be negative.",
                },
            )

        old_quantity = product.stock_quantity
        difference = new_quantity - old_quantity

        if difference == 0:
            return redirect("inventory")

        product.stock_quantity = new_quantity
        product.save(update_fields=["stock_quantity"])

        StockMovement.objects.create(
            product=product,
            movement_type="ADJUSTMENT",
            quantity=abs(difference),
            note=f"Stock adjusted from {old_quantity} to {new_quantity}",
        )

        return redirect("inventory")

    return render(
        request,
        "products/stock_adjustment.html",
        {"product": product},
    )


@login_required
def stock_history(request):
    movements = StockMovement.objects.select_related(
        "product"
    ).order_by("-created_at")

    search = request.GET.get("search", "").strip()
    movement_type = request.GET.get("movement_type", "")

    if search:
        movements = movements.filter(product__name__icontains=search)

    if movement_type:
        movements = movements.filter(movement_type=movement_type)

    return render(
        request,
        "products/stock_history.html",
        {
            "movements": movements,
            "search": search,
            "selected_movement_type": movement_type,
        },
    )


@login_required
def manage_products(request):
    tab = request.GET.get("tab", "products")

    if request.method == "POST":
        action = request.POST.get("action")

        # Add manufacturer
        if action == "add_manufacturer":
            name = request.POST.get("name", "").strip()

            if name:
                Manufacturer.objects.create(name=name)
                messages.success(request, "Manufacturer added.")
            else:
                messages.error(request, "Enter a manufacturer name.")

            return redirect("/products/manage/?tab=manufacturers")

        # Add one product
        elif action == "add_product":
            try:
                name = request.POST.get("name", "").strip()
                manufacturer_id = request.POST.get("manufacturer")

                cost_price = float(request.POST.get("cost_price", 0))
                selling_price = float(request.POST.get("selling_price", 0))
                stock_quantity = int(request.POST.get("stock_quantity", 0))
                threshold = int(request.POST.get("low_stock_threshold", 5))

                if not name:
                    raise ValueError

                if cost_price < 0 or selling_price < 0:
                    raise ValueError

                if stock_quantity < 0 or threshold < 0:
                    raise ValueError

                manufacturer = get_object_or_404(
                    Manufacturer,
                    id=manufacturer_id,
                    is_active=True,
                )

                Product.objects.create(
                    name=name,
                    category=request.POST.get("category"),
                    manufacturer=manufacturer,
                    size=request.POST.get("size", "").strip(),
                    thickness=request.POST.get("thickness", "").strip(),
                    cost_price=cost_price,
                    selling_price=selling_price,
                    stock_quantity=stock_quantity,
                    low_stock_threshold=threshold,
                )

                messages.success(request, "Product added successfully.")

            except (ValueError, TypeError):
                messages.error(
                    request,
                    "Please check the product details, prices, and stock quantity.",
                )

            return redirect("/products/manage/?tab=products")

        # Add multiple sizes for a new product
        elif action == "add_product_variants":
            name = request.POST.get("variant_product_name", "").strip()
            category = request.POST.get("variant_category", "")
            manufacturer_id = request.POST.get("variant_manufacturer", "")

            sizes = request.POST.getlist("variant_size")
            thicknesses = request.POST.getlist("variant_thickness")
            costs = request.POST.getlist("variant_cost_price")
            prices = request.POST.getlist("variant_selling_price")
            stocks = request.POST.getlist("variant_stock_quantity")

            threshold = request.POST.get(
                "variant_low_stock_threshold", "5"
            )

            if not name or not category or not manufacturer_id:
                messages.error(
                    request,
                    "Enter the product name, category, and manufacturer.",
                )
                return redirect("/products/manage/?tab=add")

            if not sizes or not any(size.strip() for size in sizes):
                messages.error(request, "Add at least one product size.")
                return redirect("/products/manage/?tab=add")

            try:
                threshold_value = int(threshold)

                if threshold_value < 0:
                    raise ValueError

                manufacturer = get_object_or_404(
                    Manufacturer,
                    id=manufacturer_id,
                    is_active=True,
                )

                variants_to_create = []

                for index, raw_size in enumerate(sizes):
                    size = raw_size.strip()

                    if not size:
                        continue

                    thickness = (
                        thicknesses[index].strip()
                        if index < len(thicknesses)
                        else ""
                    )

                    cost = float(costs[index])
                    price = float(prices[index])
                    stock = int(stocks[index])

                    if cost < 0 or price < 0 or stock < 0:
                        raise ValueError

                    variants_to_create.append(
                        Product(
                            name=name,
                            category=category,
                            manufacturer=manufacturer,
                            size=size,
                            thickness=thickness,
                            cost_price=cost,
                            selling_price=price,
                            stock_quantity=stock,
                            low_stock_threshold=threshold_value,
                        )
                    )

                if not variants_to_create:
                    raise ValueError

                Product.objects.bulk_create(variants_to_create)

            except (ValueError, TypeError, IndexError):
                messages.error(
                    request,
                    "Check each size, thickness, price, and stock value. "
                    "Prices and stock must be valid non-negative numbers.",
                )
                return redirect("/products/manage/?tab=add")

            messages.success(
                request,
                f"Added {len(variants_to_create)} sizes for {name}.",
            )
            return redirect("/products/manage/?tab=products")

        # Add more sizes to an existing product
        elif action == "add_existing_product_variants":
            base_product_id = request.POST.get(
                "existing_product_id", ""
            )

            sizes = request.POST.getlist("existing_variant_size")
            thicknesses = request.POST.getlist(
                "existing_variant_thickness"
            )
            costs = request.POST.getlist(
                "existing_variant_cost_price"
            )
            prices = request.POST.getlist(
                "existing_variant_selling_price"
            )
            stocks = request.POST.getlist(
                "existing_variant_stock_quantity"
            )

            if not base_product_id:
                messages.error(
                    request,
                    "Select an existing product first.",
                )
                return redirect("/products/manage/?tab=add")

            base_product = get_object_or_404(
                Product.objects.select_related("manufacturer"),
                id=base_product_id,
                is_active=True,
            )

            if not sizes or not any(size.strip() for size in sizes):
                messages.error(request, "Add at least one size.")
                return redirect("/products/manage/?tab=add")

            try:
                variants_to_create = []
                seen_variants = set()

                for index, raw_size in enumerate(sizes):
                    size = raw_size.strip()

                    if not size:
                        continue

                    thickness = (
                        thicknesses[index].strip()
                        if index < len(thicknesses)
                        else ""
                    )

                    cost = float(costs[index])
                    price = float(prices[index])
                    stock = int(stocks[index])

                    if cost < 0 or price < 0 or stock < 0:
                        raise ValueError

                    variant_key = (
                        size.casefold(),
                        thickness.casefold(),
                    )

                    if variant_key in seen_variants:
                        raise ValueError

                    seen_variants.add(variant_key)

                    duplicate_exists = Product.objects.filter(
                        name__iexact=base_product.name,
                        manufacturer=base_product.manufacturer,
                        size__iexact=size,
                        thickness__iexact=thickness,
                        is_active=True,
                    ).exists()

                    if duplicate_exists:
                        messages.error(
                            request,
                            f"The size {size} "
                            f"({thickness or 'no thickness'}) "
                            "already exists for this product.",
                        )
                        return redirect("/products/manage/?tab=add")

                    variants_to_create.append(
                        Product(
                            name=base_product.name,
                            category=base_product.category,
                            manufacturer=base_product.manufacturer,
                            size=size,
                            thickness=thickness,
                            cost_price=cost,
                            selling_price=price,
                            stock_quantity=stock,
                            low_stock_threshold=(
                                base_product.low_stock_threshold
                            ),
                        )
                    )

                if not variants_to_create:
                    raise ValueError

                Product.objects.bulk_create(variants_to_create)

            except (ValueError, TypeError, IndexError):
                messages.error(
                    request,
                    "Check each size, thickness, price, and stock value. "
                    "Prices and stock must be valid non-negative numbers.",
                )
                return redirect("/products/manage/?tab=add")

            messages.success(
                request,
                f"Added {len(variants_to_create)} new sizes "
                f"for {base_product.name}.",
            )
            return redirect("/products/manage/?tab=products")

        # Edit product
        elif action == "edit_product":
            product = get_object_or_404(
                Product,
                id=request.POST.get("product_id"),
            )

            try:
                cost_price = float(request.POST.get("cost_price", 0))
                selling_price = float(request.POST.get("selling_price", 0))
                threshold = int(
                    request.POST.get("low_stock_threshold", 5)
                )

                if (
                    cost_price < 0
                    or selling_price < 0
                    or threshold < 0
                ):
                    raise ValueError

                product.name = request.POST.get("name", "").strip()
                product.category = request.POST.get("category")
                product.manufacturer_id = request.POST.get("manufacturer")
                product.size = request.POST.get("size", "").strip()
                product.thickness = request.POST.get(
                    "thickness", ""
                ).strip()
                product.cost_price = cost_price
                product.selling_price = selling_price
                product.low_stock_threshold = threshold

                product.save()
                messages.success(request, "Product updated.")

            except (ValueError, TypeError):
                messages.error(
                    request,
                    "Please check the product details and price values.",
                )

            return redirect("/products/manage/?tab=products")

        # Activate/deactivate product
        elif action == "toggle_product":
            product = get_object_or_404(
                Product,
                id=request.POST.get("product_id"),
            )

            product.is_active = not product.is_active
            product.save(update_fields=["is_active"])

            return redirect("/products/manage/?tab=products")

        # Edit manufacturer
        elif action == "edit_manufacturer":
            manufacturer = get_object_or_404(
                Manufacturer,
                id=request.POST.get("manufacturer_id"),
            )

            name = request.POST.get("name", "").strip()

            if name:
                manufacturer.name = name
                manufacturer.save()
                messages.success(request, "Manufacturer updated.")
            else:
                messages.error(request, "Enter a manufacturer name.")

            return redirect("/products/manage/?tab=manufacturers")

        # Activate/deactivate manufacturer
        elif action == "toggle_manufacturer":
            manufacturer = get_object_or_404(
                Manufacturer,
                id=request.POST.get("manufacturer_id"),
            )

            manufacturer.is_active = not manufacturer.is_active
            manufacturer.save(update_fields=["is_active"])

            return redirect("/products/manage/?tab=manufacturers")

    products = Product.objects.all().select_related(
        "manufacturer"
    ).order_by("-created_at")

    manufacturers = Manufacturer.objects.all().order_by("name")

    existing_variant_products = Product.objects.filter(
        is_active=True
    ).select_related(
        "manufacturer"
    ).order_by("name", "size", "thickness")

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    manufacturer = request.GET.get("manufacturer", "")

    if search:
        products = products.filter(name__icontains=search)

    if category:
        products = products.filter(category=category)

    if manufacturer:
        products = products.filter(manufacturer_id=manufacturer)

    edit_product = None
    edit_id = request.GET.get("edit")

    if edit_id and tab == "edit":
        edit_product = get_object_or_404(Product, id=edit_id)

    edit_manufacturer = None
    manufacturer_edit_id = request.GET.get("manufacturer_edit")

    if manufacturer_edit_id:
        edit_manufacturer = get_object_or_404(
            Manufacturer,
            id=manufacturer_edit_id,
        )

    context = {
        "tab": tab,
        "products": products,
        "manufacturers": manufacturers,
        "existing_variant_products": existing_variant_products,
        "selected_category": category,
        "selected_manufacturer": manufacturer,
        "search": search,
        "edit_product": edit_product,
        "edit_manufacturer": edit_manufacturer,
    }

    return render(
        request,
        "products/manage_products.html",
        context,
    )