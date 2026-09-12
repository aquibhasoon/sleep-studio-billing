from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("reports.urls")),
    path("sales/", include("sales.urls")),
    path("products/", include("products.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("customers/", include("customers.urls")),
    
]