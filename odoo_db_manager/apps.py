"""
تكوين تطبيق إدارة قواعد البيانات على طراز أودو
"""

import logging
import sys

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class OdooDbManagerConfig(AppConfig):
    """Configuration for the Odoo Database Manager application.

    Note: Database synchronization is now handled by the sync_databases management command
    instead of during app initialization to prevent database access during startup.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "odoo_db_manager"
    verbose_name = _("إدارة قواعد البيانات")

    def ready(self):
        """تهيئة التطبيق.

        يتم استدعاء هذه الدالة عند بدء تشغيل Django. نستخدمها لتسجيل الإشارات والتحقق
        مع تجنب أي عمليات على قاعدة البيانات خلال مرحلة التهيئة.
        """
        # استيراد وحدة الإشارات لتسجيلها
        # يتم إنشاء اتصالات الإشارات عند استيراد الوحدة
        try:
            # استيراد الإشارات - سيتم تسجيلها تلقائياً
            import odoo_db_manager.signals  # noqa: F401 (signals auto-register)

            # تأجيل بدء خدمة النسخ الاحتياطي حتى يكتمل تحميل التطبيق
            self._setup_backup_service()

        except ImportError as e:
            logger.warning(f"فشل في استيراد الإشارات: {e}")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء تهيئة التطبيق: {str(e)}", exc_info=True)

    def _setup_backup_service(self):
        """إعداد خدمة النسخ الاحتياطي.

        يتم تسجيل دالة فحص النظام التي ستبدأ الخدمة بعد اكتمال تحميل التطبيق.
        """
        from django.core.checks import register

        @register()
        def check_scheduled_backup_service(app_configs, **kwargs):
            """التحقق من وبدء خدمة النسخ الاحتياطي المجدولة.

            يتم تنفيذ هذا الفحص بعد اكتمال تحميل سجل التطبيق وهو آمن
            لعمليات قاعدة البيانات.
            """
            import os
            import sys

            from django.conf import settings

            # تخطي في وضع الاختبار أو أوامر إدارة معينة
            if (
                settings.TESTING
                or "test" in sys.argv
                or "migrate" in sys.argv
                or "makemigrations" in sys.argv
                or "collectstatic" in sys.argv
                or "createsuperuser" in sys.argv
            ):
                return []

            # التحقق مما إذا كنا في سياق runserver
            is_runserver = "runserver" in sys.argv
            is_main_process = os.environ.get("RUN_MAIN") == "true" or not is_runserver

            # المتابعة فقط في العملية الرئيسية (وليس في إعادة التحميل التلقائي)
            if is_main_process:
                # استيراد الخدمة هنا لتجنب استيرادها أثناء التهيئة
                from .services.scheduled_backup_service import scheduled_backup_service

                try:
                    if not scheduled_backup_service.scheduler.running:
                        scheduled_backup_service.start()
                        logger.info("تم بدء خدمة النسخ الاحتياطي المجدولة بنجاح")
                except Exception as e:
                    logger.error(f"فشل في بدء خدمة النسخ الاحتياطي: {str(e)}")

            return []  # لا توجد أخطاء أو تحذيرات
