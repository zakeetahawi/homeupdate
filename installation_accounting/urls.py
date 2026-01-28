from django.urls import path

from . import views

app_name = "installation_accounting"

urlpatterns = [
    path("reports/", views.installation_reports, name="reports"),
    path("api/bulk-pay/", views.api_bulk_pay_installations, name="bulk_pay"),
]
