import logging

from django.apps import AppConfig

logger = logging.getLogger('accounting')


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
            logger.info("Accounting signals registered successfully")
        except Exception as e:
            logger.error(f"Error registering accounting signals: {e}", exc_info=True)
