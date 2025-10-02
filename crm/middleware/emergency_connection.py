"""
Emergency Connection Management Middleware
يدير الاتصالات في الحالات الطارئة ويمنع استنزاف connection pool
"""

import logging
import time

from django.core.cache import cache
from django.db import connections, transaction
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class EmergencyConnectionMiddleware:
    """
    Middleware لإدارة اتصالات قاعدة البيانات في الحالات الطارئة
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_connections_threshold = 180  # تحذير عند 180 اتصال
        self.critical_threshold = 190  # حالة طوارئ عند 190 اتصال

    def __call__(self, request):
        # فحص حالة الاتصالات قبل معالجة الطلب
        connection_status = self.check_connection_health()

        if connection_status["status"] == "critical":
            # في حالة الطوارئ، ارجع استجابة سريعة
            return JsonResponse(
                {
                    "error": "System temporarily overloaded. Please try again in a moment.",
                    "status": "service_unavailable",
                    "retry_after": 30,
                },
                status=503,
            )

        # معالجة الطلب العادي
        response = self.get_response(request)

        # تنظيف الاتصالات بعد كل طلب
        self.cleanup_connections()

        return response

    def check_connection_health(self):
        """
        فحص صحة اتصالات قاعدة البيانات
        """
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE datname = %s AND state = 'active'
                """,
                    [connection.settings_dict["NAME"]],
                )

                active_count = cursor.fetchone()[0]

                # تحديد حالة النظام
                if active_count >= self.critical_threshold:
                    status = "critical"
                    logger.critical(
                        f"Critical: {active_count} active database connections"
                    )
                elif active_count >= self.max_connections_threshold:
                    status = "warning"
                    logger.warning(
                        f"Warning: {active_count} active database connections"
                    )
                else:
                    status = "healthy"

                # حفظ الإحصائيات في cache
                cache.set("db_connection_count", active_count, 60)
                cache.set("db_connection_status", status, 60)

                return {
                    "status": status,
                    "active_connections": active_count,
                    "timestamp": time.time(),
                }

        except Exception as e:
            logger.error(f"Error checking connection health: {e}")
            return {"status": "unknown", "error": str(e), "timestamp": time.time()}

    def cleanup_connections(self):
        """
        تنظيف اتصالات قاعدة البيانات
        """
        try:
            # إغلاق جميع الاتصالات الخاملة
            for alias in connections:
                connection = connections[alias]
                if connection.connection is not None:
                    # إغلاق الاتصال إذا كان خاملاً
                    if hasattr(connection, "close_if_unusable_or_obsolete"):
                        connection.close_if_unusable_or_obsolete()

        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")

    def process_exception(self, request, exception):
        """
        معالجة الأخطاء المتعلقة بقاعدة البيانات
        """
        if "too many clients already" in str(exception):
            logger.critical("Database connection pool exhausted!")

            # محاولة تنظيف الاتصالات
            self.cleanup_connections()

            return JsonResponse(
                {
                    "error": "Database temporarily unavailable. Please try again.",
                    "status": "database_overload",
                    "retry_after": 60,
                },
                status=503,
            )

        return None
