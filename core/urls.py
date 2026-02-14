"""
مسارات سجل التدقيق — Audit Log URLs
"""

from django.urls import path

from . import audit_views

app_name = "audit"

urlpatterns = [
    path("", audit_views.audit_log_list, name="audit_log_list"),
    path("<int:pk>/", audit_views.audit_log_detail, name="audit_log_detail"),
    path("export/", audit_views.audit_log_export, name="audit_log_export"),
    path("stats/", audit_views.audit_log_stats, name="audit_log_stats"),
]
