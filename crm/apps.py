from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    verbose_name = 'إدارة النظام'
    
    def ready(self):
        """تهيئة التطبيق عند بدء التشغيل"""
        try:
            # استيراد الإشارات
            from . import signals  # noqa: F401
        except ImportError:
            pass
