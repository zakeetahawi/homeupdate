from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    verbose_name = "إدارة المخزون"

    def ready(self):
        try:
            import inventory.signals
        except ImportError:
            pass
