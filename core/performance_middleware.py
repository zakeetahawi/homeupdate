"""
🛡️ Performance Middleware - ميدلوير تحسين الأداء
يقوم بـ:
1. Smart Caching للصفحات
2. Query Monitoring & Logging
3. Response Time Tracking
4. Automatic N+1 Detection
"""

import hashlib
import logging
import re
import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.db import connection, reset_queries
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("performance")


class PerformanceCacheMiddleware:
    """
    ميدلوير الكاش الذكي للأداء

    المميزات:
    - كاش تلقائي للصفحات GET
    - تجاهل صفحات معينة (admin, login, etc.)
    - vary by user/branch
    - ETag support
    """

    # صفحات لا يتم كاشها أبداً
    NEVER_CACHE_PATHS = [
        r"^/admin/",
        r"^/accounts/login/",
        r"^/accounts/logout/",
        r"^/api/.*",  # API يتم كاشه بشكل منفصل
        r".*\?.*no_cache=",
    ]

    # صفحات يتم كاشها لفترة قصيرة (1 دقيقة)
    SHORT_CACHE_PATHS = [
        (r"^/orders/wizard/", 60),
        (r"^/notifications/", 30),
    ]

    # صفحات يتم كاشها لفترة متوسطة (5 دقائق)
    MEDIUM_CACHE_PATHS = [
        (r"^/installations/installation-list/", 300),
        (r"^/orders/order-list/", 300),
        (r"^/manufacturing/", 300),
    ]

    # صفحات يتم كاشها لفترة طويلة (30 دقيقة)
    LONG_CACHE_PATHS = [
        (r"^/reports/", 1800),
        (r"^/statistics/", 1800),
    ]

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # تجاهل غير GET
        if request.method != "GET":
            return self.get_response(request)

        # تجاهل AJAX requests للـ polling
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            if "poll" in request.path or "status" in request.path:
                return self.get_response(request)

        # فحص إذا كان المسار في قائمة عدم الكاش
        for pattern in self.NEVER_CACHE_PATHS:
            if re.match(pattern, request.path):
                return self.get_response(request)

        # تحديد مدة الكاش
        cache_timeout = self._get_cache_timeout(request.path)
        if cache_timeout == 0:
            return self.get_response(request)

        # بناء مفتاح الكاش
        cache_key = self._build_cache_key(request)

        # محاولة جلب من الكاش
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            # إضافة header للتوضيح
            response = cached_response
            response["X-Cache"] = "HIT"
            return response

        # تنفيذ الطلب
        response = self.get_response(request)

        # تخزين فقط للاستجابات الناجحة
        if response.status_code == 200 and not response.streaming:
            try:
                cache.set(cache_key, response, cache_timeout)
                response["X-Cache"] = "MISS"
            except Exception as e:
                logger.warning(f"Failed to cache response: {e}")

        return response

    def _get_cache_timeout(self, path: str) -> int:
        """تحديد مدة الكاش بناءً على المسار"""
        for pattern, timeout in self.SHORT_CACHE_PATHS:
            if re.match(pattern, path):
                return timeout

        for pattern, timeout in self.MEDIUM_CACHE_PATHS:
            if re.match(pattern, path):
                return timeout

        for pattern, timeout in self.LONG_CACHE_PATHS:
            if re.match(pattern, path):
                return timeout

        # افتراضي: 2 دقيقة
        return 120

    def _build_cache_key(self, request: HttpRequest) -> str:
        """بناء مفتاح الكاش"""
        parts = [
            "page",
            request.path,
        ]

        # إضافة query string
        if request.GET:
            qs_hash = hashlib.md5(request.GET.urlencode().encode()).hexdigest()[:8]
            parts.append(qs_hash)

        # vary by user
        if hasattr(request, "user") and request.user.is_authenticated:
            parts.append(f"u:{request.user.id}")
            # vary by branch if available
            if hasattr(request.user, "branch_id") and request.user.branch_id:
                parts.append(f"b:{request.user.branch_id}")

        return ":".join(parts)


class QueryMonitorMiddleware:
    """
    ميدلوير مراقبة الاستعلامات

    المميزات:
    - تسجيل عدد الاستعلامات لكل طلب
    - تحذير عند تجاوز الحد المسموح
    - اكتشاف N+1 queries
    - تسجيل الاستعلامات البطيئة
    """

    # عتبات التحذير
    QUERY_COUNT_WARNING = 50
    QUERY_COUNT_CRITICAL = 100
    QUERY_TIME_WARNING_MS = 100
    TOTAL_TIME_WARNING_MS = 2000

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # تجاهل static files
        if self._is_static_request(request):
            return self.get_response(request)

        # بدء المراقبة
        start_time = time.time()
        reset_queries()

        # تفعيل debug cursor لتسجيل الاستعلامات
        was_debug = settings.DEBUG
        if not was_debug:
            connection.force_debug_cursor = True

        try:
            response = self.get_response(request)
        finally:
            # إعادة الضبط
            if not was_debug:
                connection.force_debug_cursor = False

        # حساب الإحصائيات
        total_time = (time.time() - start_time) * 1000
        queries = connection.queries
        query_count = len(queries)

        # إضافة headers للتوضيح
        response["X-Query-Count"] = str(query_count)
        response["X-Response-Time"] = f"{total_time:.0f}ms"

        # تحليل وتسجيل
        self._analyze_and_log(request, queries, query_count, total_time)

        return response

    def _is_static_request(self, request: HttpRequest) -> bool:
        """فحص إذا كان الطلب لملف ثابت"""
        static_patterns = ["/static/", "/media/", "/favicon.ico"]
        return any(request.path.startswith(p) for p in static_patterns)

    def _analyze_and_log(
        self, request: HttpRequest, queries: list, query_count: int, total_time: float
    ):
        """تحليل وتسجيل الاستعلامات"""
        log_data = {
            "path": request.path,
            "method": request.method,
            "query_count": query_count,
            "total_time_ms": round(total_time, 2),
        }

        # تحذير عند تجاوز عدد الاستعلامات
        if query_count >= self.QUERY_COUNT_CRITICAL:
            log_data["level"] = "CRITICAL"
            logger.error(f"CRITICAL_QUERY_COUNT: {log_data}")
        elif query_count >= self.QUERY_COUNT_WARNING:
            log_data["level"] = "WARNING"
            logger.warning(f"HIGH_QUERY_COUNT: {log_data}")

        # تحذير عند بطء الاستجابة
        if total_time >= self.TOTAL_TIME_WARNING_MS:
            logger.warning(f"SLOW_RESPONSE: {log_data}")

        # البحث عن N+1 queries
        duplicate_queries = self._find_duplicate_queries(queries)
        if duplicate_queries:
            log_data["duplicates"] = duplicate_queries
            logger.warning(f"N+1_DETECTED: {log_data}")

        # تسجيل الاستعلامات البطيئة
        slow_queries = [
            q
            for q in queries
            if float(q.get("time", 0)) * 1000 > self.QUERY_TIME_WARNING_MS
        ]
        if slow_queries:
            for sq in slow_queries[:5]:  # أول 5 فقط
                logger.warning(
                    f"SLOW_QUERY: {sq['sql'][:200]}... ({float(sq['time'])*1000:.0f}ms)"
                )

    def _find_duplicate_queries(self, queries: list) -> dict:
        """البحث عن الاستعلامات المكررة (N+1 pattern)"""
        # نستخدم pattern matching للتعرف على استعلامات متشابهة
        query_patterns = {}

        for q in queries:
            sql = q.get("sql", "")
            # تبسيط الاستعلام للمقارنة
            simplified = re.sub(r"\d+", "N", sql)
            simplified = re.sub(r"'[^']*'", "'X'", simplified)

            if simplified not in query_patterns:
                query_patterns[simplified] = 0
            query_patterns[simplified] += 1

        # إرجاع فقط المكرر أكثر من 3 مرات
        return {k: v for k, v in query_patterns.items() if v > 3}


class CompressionMiddleware:
    """
    ميدلوير ضغط الاستجابات

    يضغط الاستجابات الكبيرة باستخدام gzip
    """

    MIN_SIZE_TO_COMPRESS = 1024  # 1KB
    COMPRESSIBLE_CONTENT_TYPES = [
        "text/html",
        "text/css",
        "text/javascript",
        "application/javascript",
        "application/json",
        "application/xml",
    ]

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # فحص إذا كان العميل يدعم gzip
        if "gzip" not in request.META.get("HTTP_ACCEPT_ENCODING", ""):
            return response

        # فحص نوع المحتوى
        content_type = response.get("Content-Type", "").split(";")[0]
        if content_type not in self.COMPRESSIBLE_CONTENT_TYPES:
            return response

        # فحص الحجم
        if len(response.content) < self.MIN_SIZE_TO_COMPRESS:
            return response

        # الضغط
        try:
            import gzip

            compressed = gzip.compress(response.content)

            # استخدام المضغوط فقط إذا كان أصغر
            if len(compressed) < len(response.content):
                response.content = compressed
                response["Content-Encoding"] = "gzip"
                response["Content-Length"] = len(compressed)
        except Exception:
            pass  # تجاهل أخطاء الضغط

        return response


class SecurityHeadersMiddleware:
    """
    ميدلوير إضافة headers الأمان
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # إضافة headers الأمان
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
