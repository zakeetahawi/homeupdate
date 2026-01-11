"""
Middleware لإدارة اتصالات قاعدة البيانات بكفاءة
يهدف إلى حل مشكلة "too many clients already" في PostgreSQL
"""

import logging
import time

from django.conf import settings
from django.db import connection, connections
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("connection_manager")


class DatabaseConnectionMiddleware:
    """
    Middleware لإدارة اتصالات قاعدة البيانات بكفاءة
    يغلق الاتصالات بعد كل طلب لتجنب تراكمها
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.connection_count = 0

    def __call__(self, request):
        # تسجيل بداية الطلب
        start_time = time.time()

        # معالجة الطلب
        response = self.get_response(request)

        # إغلاق جميع اتصالات قاعدة البيانات بعد كل طلب
        self.cleanup_connections()

        # تسجيل معلومات الأداء
        duration = time.time() - start_time
        if duration > 1.0:  # تسجيل الطلبات البطيئة
            logger.warning(f"Slow request: {request.path} took {duration:.2f}s")

        return response

    def cleanup_connections(self):
        """تنظيف جميع اتصالات قاعدة البيانات"""
        try:
            closed_count = 0

            # إغلاق جميع الاتصالات
            for alias in connections:
                conn = connections[alias]
                if conn.connection is not None:
                    conn.close()
                    closed_count += 1

            if closed_count > 0:
                logger.debug(f"Closed {closed_count} database connections")

        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


class ConnectionMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware لمراقبة استخدام اتصالات قاعدة البيانات
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.request_count = 0

    def process_request(self, request):
        """بداية معالجة الطلب"""
        self.request_count += 1
        request._connection_start_time = time.time()

        # مراقبة عدد الطلبات
        if self.request_count % 100 == 0:
            logger.info(f"Processed {self.request_count} requests")

        return None

    def process_response(self, request, response):
        """نهاية معالجة الطلب"""
        if hasattr(request, "_connection_start_time"):
            duration = time.time() - request._connection_start_time

            # تسجيل الطلبات البطيئة
            if duration > 2.0:
                logger.warning(
                    f"Very slow request: {request.path} took {duration:.2f}s"
                )

        return response


class ConnectionPoolMiddleware:
    """
    Middleware لإدارة pool الاتصالات
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_connections_warning = 50

    def __call__(self, request):
        # فحص عدد الاتصالات قبل معالجة الطلب
        self.check_connection_count()

        response = self.get_response(request)

        # تنظيف الاتصالات الخاملة
        self.cleanup_idle_connections()

        return response

    def check_connection_count(self):
        """فحص عدد الاتصالات الحالية"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """
                )
                total_connections = cursor.fetchone()[0]

                if total_connections > self.max_connections_warning:
                    logger.warning(
                        f"High connection count: {total_connections} connections"
                    )

        except Exception as e:
            logger.error(f"Error checking connection count: {e}")

    def cleanup_idle_connections(self):
        """تنظيف الاتصالات الخاملة"""
        try:
            with connection.cursor() as cursor:
                # قتل الاتصالات الخاملة لأكثر من 5 دقائق
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    AND state = 'idle'
                    AND state_change < now() - interval '5 minutes'
                    AND pid != pg_backend_pid()
                """
                )

        except Exception as e:
            logger.error(f"Error cleaning idle connections: {e}")


class EmergencyConnectionMiddleware:
    """
    Middleware طوارئ لحالات تراكم الاتصالات الحرجة
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.emergency_threshold = 80

    def __call__(self, request):
        # فحص حالة الطوارئ
        if self.is_emergency_state():
            logger.critical("Emergency: Too many database connections!")
            self.emergency_cleanup()

        response = self.get_response(request)

        # إغلاق فوري للاتصال في حالة الطوارئ
        if hasattr(connection, "connection") and connection.connection:
            connection.close()

        return response

    def is_emergency_state(self):
        """فحص ما إذا كنا في حالة طوارئ"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """
                )
                total_connections = cursor.fetchone()[0]
                return total_connections > self.emergency_threshold

        except Exception:
            return True  # في حالة الخطأ، اعتبرها حالة طوارئ

    def emergency_cleanup(self):
        """تنظيف طوارئ للاتصالات"""
        try:
            with connection.cursor() as cursor:
                # قتل جميع الاتصالات الخاملة فوراً
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    AND state IN ('idle', 'idle in transaction')
                    AND pid != pg_backend_pid()
                """
                )

                logger.info("Emergency cleanup completed")

        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")
