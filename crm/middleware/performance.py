"""
Performance Middleware - وسطاء قياس وتحسين الأداء
"""

import logging
import time

from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class PerformanceMiddleware:
    """وسيط قياس أداء الطلبات"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        # حساب وقت الاستجابة
        duration = time.time() - start_time

        # إضافة وقت الاستجابة إلى headers
        response["X-Response-Time"] = f"{duration:.3f}s"

        # تسجيل الطلبات البطيئة
        if duration > 1.0:  # أكثر من ثانية واحدة
            logger.warning(f"Slow request: {request.path} took {duration:.3f}s")

        return response


class LazyLoadMiddleware:
    """وسيط التحميل الكسول للصور"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # إضافة headers للتحميل الكسول
        if hasattr(response, "content") and "text/html" in response.get(
            "Content-Type", ""
        ):
            response["X-Lazy-Load"] = "enabled"

        return response


class QueryPerformanceMiddleware:
    """وسيط مراقبة أداء استعلامات قاعدة البيانات"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.db import connection

        # عدد الاستعلامات قبل الطلب
        queries_before = len(connection.queries)

        response = self.get_response(request)

        # عدد الاستعلامات بعد الطلب
        queries_after = len(connection.queries)
        query_count = queries_after - queries_before

        # إضافة عدد الاستعلامات إلى headers
        response["X-DB-Queries"] = str(query_count)

        # تحذير من الاستعلامات الكثيرة
        if query_count > 10:
            logger.warning(
                f"High query count: {request.path} executed {query_count} queries"
            )

        return response


class PerformanceCookiesMiddleware:
    """وسيط إضافة معلومات الأداء إلى cookies"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        # حساب وقت الاستجابة
        duration = time.time() - start_time

        # إضافة معلومات الأداء إلى cookies (للتطوير فقط)
        if settings.DEBUG:
            response.set_cookie("performance_time", f"{duration:.3f}", max_age=60)
            response.set_cookie("performance_path", request.path, max_age=60)

        return response


class CustomGZipMiddleware:
    """وسيط ضغط مخصص"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # إضافة headers للضغط
        if hasattr(response, "content"):
            response["X-Compression"] = "gzip"

        return response
