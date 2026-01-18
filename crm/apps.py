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

        # نسخ جميع التسجيلات من admin.site إلى custom_admin_site
        self._migrate_admin_registrations()

    def _migrate_admin_registrations(self):
        """نقل جميع التسجيلات من admin.site إلى custom_admin_site تلقائياً"""
        try:
            from django.contrib import admin

            from crm.custom_admin import custom_admin_site

            # نسخ جميع النماذج المسجلة
            for model, model_admin in admin.site._registry.items():
                try:
                    if model not in custom_admin_site._registry:
                        custom_admin_site.register(model, model_admin.__class__)
                except admin.sites.AlreadyRegistered:
                    pass
        except Exception as e:
            # في حالة حدوث خطأ، لا نريد أن يتعطل Django
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to migrate admin registrations: {e}")
