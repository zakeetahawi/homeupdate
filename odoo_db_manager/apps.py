"""
تكوين تطبيق إدارة قواعد البيانات على طراز أودو
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OdooDbManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "odoo_db_manager"
    verbose_name = _("إدارة قواعد البيانات")

    def ready(self):
        """تهيئة التطبيق"""
        # استيراد الإشارات
        try:
            import odoo_db_manager.signals

            # مزامنة قواعد البيانات من ملف الإعدادات
            from .services.database_service import DatabaseService
            database_service = DatabaseService()
            database_service.sync_databases_from_settings()

            # اكتشاف ومزامنة قواعد البيانات الموجودة في PostgreSQL
            database_service.sync_discovered_databases()

            # بدء تشغيل خدمة النسخ الاحتياطية المجدولة
            import os
            if os.environ.get('RUN_MAIN', None) != 'true':
                # تجنب التشغيل المزدوج في وضع التطوير
                from .services.scheduled_backup_service import scheduled_backup_service
                scheduled_backup_service.start()
                print("تم بدء تشغيل خدمة النسخ الاحتياطية المجدولة")
        except ImportError:
            pass
        except Exception as e:
            print(f"حدث خطأ أثناء تهيئة التطبيق: {str(e)}")
