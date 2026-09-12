from django.urls import path

from .views import (
    customer_list,
    create_customer,
    customer_edit,
    customer_detail,
)

urlpatterns = [
    path("", customer_list, name="customer_list"),
    path("create/", create_customer, name="create_customer"),
    path("<int:customer_id>/", customer_detail, name="customer_detail"),
    path("<int:customer_id>/edit/", customer_edit, name="customer_edit"),
]
