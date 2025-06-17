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
            import odoo_db_manager.signals            # التحقق من وجود الجداول قبل المزامنة
            from django.db import connection
            from django.db.utils import OperationalError
            
            try:
                # محاولة التحقق من وجود جدول Database
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM odoo_db_manager_database LIMIT 1")
                
                # إذا وصلنا هنا، فالجداول موجودة ويمكننا المزامنة
                from .services.database_service import DatabaseService
                database_service = DatabaseService()
                database_service.sync_databases_from_settings()
                database_service.sync_discovered_databases()
                
            except OperationalError:
                # الجداول غير موجودة بعد، تخطي المزامنة
                print("تخطي مزامنة قواعد البيانات - الجداول غير موجودة بعد")

            # بدء تشغيل خدمة النسخ الاحتياطية المجدولة
            import os
            if os.environ.get('RUN_MAIN', None) != 'true':
                # تجنب التشغيل المزدوج في وضع التطوير
                try:
                    from .services.scheduled_backup_service import scheduled_backup_service
                    scheduled_backup_service.start()
                    print("تم بدء تشغيل خدمة النسخ الاحتياطية المجدولة")
                except Exception as scheduler_error:
                    print(f"فشل بدء تشغيل المجدول: {str(scheduler_error)}")
                    # في بيئة الإنتاج، قد نحتاج لحل بديل
                    print("سيتم استخدام النسخ الاحتياطية اليدوية في بيئة الإنتاج")
        except ImportError:
            pass
        except Exception as e:
            print(f"حدث خطأ أثناء تهيئة التطبيق: {str(e)}")
