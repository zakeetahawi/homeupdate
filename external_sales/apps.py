from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExternalSalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "external_sales"
    verbose_name = _("المبيعات الخارجية")

    def ready(self):
        import external_sales.signals  # noqa: F401
