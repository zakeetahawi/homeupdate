from django.apps import AppConfig


class CuttingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cutting"
    verbose_name = "نظام التقطيع"

    def ready(self):
        import cutting.signals
