from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "customers"
    verbose_name = "إدارة العملاء"

    def ready(self):
        import customers.signals  # استيراد ملف الإشارات
