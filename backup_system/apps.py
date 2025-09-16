"""
إعدادات تطبيق نظام النسخ الاحتياطي
"""
from django.apps import AppConfig


class BackupSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backup_system'
    verbose_name = 'نظام النسخ الاحتياطي والاستعادة'
    
    def ready(self):
        """تنفيذ عند تحميل التطبيق"""
        pass