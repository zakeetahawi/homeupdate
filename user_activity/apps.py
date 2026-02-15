from django.apps import AppConfig


class UserActivityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user_activity"
    verbose_name = "نشاط المستخدمين"

    def ready(self):
        """تشغيل الإعدادات عند بدء التطبيق"""
        import user_activity.signals  # استيراد الإشارات
