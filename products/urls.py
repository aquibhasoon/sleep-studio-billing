from django.urls import path

from .views import (
    inventory,
    stock_in,
    stock_adjustment,
    stock_history,
    manage_products,
)

urlpatterns = [
    path("", inventory, name="inventory"),
    path("manage/", manage_products, name="manage_products"),
    path("stock-in/<int:product_id>/", stock_in, name="stock_in"),
    path(
        "stock-adjustment/<int:product_id>/", stock_adjustment, name="stock_adjustment"
    ),
    path("stock-history/", stock_history, name="stock_history"),
]
