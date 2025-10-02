"""
تكوين تطبيق CRM
"""

from django.apps import AppConfig


class CrmConfig(AppConfig):
    """تكوين تطبيق CRM"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
    verbose_name = "نظام إدارة علاقات العملاء"

    def ready(self):
        """تنفيذ الإعدادات عند بدء التطبيق"""
        import crm.signals  # noqa
