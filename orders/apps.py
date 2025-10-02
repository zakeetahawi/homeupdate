from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"
    verbose_name = _("الطلبات")

    def ready(self):
        import orders.cache_utils  # تحميل إشارات التخزين المؤقت
        import orders.signals
        import orders.tracking  # تحميل نظام التتبع الموحد
