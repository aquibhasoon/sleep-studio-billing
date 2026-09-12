from django.urls import path
from .views import dashboard, reports_page

urlpatterns = [
    path("", dashboard, name="dashboard"),

    path(
        "reports/",
        reports_page,
        name="reports_page"
    ),

   
]