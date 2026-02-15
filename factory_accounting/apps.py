"""
Factory Accounting App Configuration
حسابات المصنع - إدارة مستحقات الخياطين والقصاصين
"""

from django.apps import AppConfig


class FactoryAccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "factory_accounting"
    verbose_name = "حسابات المصنع"

    def ready(self):
        """Import signals when app is ready"""
        import factory_accounting.signals
