from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounting"
    verbose_name = "النظام المحاسبي"
    
    def ready(self):
        """
        تسجيل الإشارات عند تحميل التطبيق
        """
        try:
            from . import signals
            signals.register_accounting_signals()
            signals.register_order_signals()
            signals.register_customer_signals()
        except Exception as e:
            print(f"Error registering accounting signals: {e}")
