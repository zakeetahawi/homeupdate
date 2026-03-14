
import time
import logging
from django.conf import settings
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("performance")
slow_queries_logger = logging.getLogger("websocket_blocker")

class QueryPerformanceLoggingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        request._start_time = time.time()
        # تفعيل queries logging فقط في DEBUG
        if settings.DEBUG:
            from django.db import reset_queries
            # تفعيل queries logging فقط في التطوير
            connection.force_debug_cursor = True
            reset_queries()
            request._queries_before = len(connection.queries)

    def process_response(self, request, response):
        # حساب الوقت المستغرق
        start_time = getattr(request, "_start_time", time.time())
        total_time = (time.time() - start_time) * 1000

        # تسجيل الصفحات البطيئة (أكثر من ثانية)
        if total_time > 1000:
            logger.warning(
                f"SLOW_PAGE: {request.path} | {int(total_time)}ms | user={getattr(request, 'user', None)}"
            )

        # تسجيل الاستعلامات البطيئة فقط في DEBUG
        if settings.DEBUG and hasattr(request, '_queries_before'):
            queries_count = len(connection.queries) - request._queries_before
            
            # تسجيل الاستعلامات البطيئة (أكثر من 100ms)
            if hasattr(connection, "queries") and connection.queries:
                for query in connection.queries[request._queries_before:]:
                    if "time" in query and float(query["time"]) > 0.1:  # 100ms
                        slow_queries_logger.warning(
                            f"SLOW_QUERY: {query['time']}s | {query['sql'][:200]}..."
                        )
            
            # إعادة ضبط force_debug_cursor
            connection.force_debug_cursor = False

        return response


class PerformanceCookiesMiddleware:
    """
    وسيط لإضافة معلومات الأداء إلى ملفات تعريف الارتباط للمستخدمين المسؤولين
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # معالجة الطلب
        start_time = time.time()
        start_queries = len(connection.queries)

        response = self.get_response(request)

        # إضافة معلومات الأداء للمسؤولين
        if settings.DEBUG and hasattr(request, "user") and request.user.is_superuser:
            duration = time.time() - start_time
            queries_executed = len(connection.queries) - start_queries

            # استخدام نص ASCII فقط لتجنب مشاكل الترميز
            response.set_cookie(
                "performance_info",
                f"Time: {duration:.4f}s | Queries: {queries_executed}",
                max_age=30,  # 30 seconds
                httponly=False,
                samesite="Lax",
            )

        return response


class CustomGZipMiddleware(GZipMiddleware):
    """
    وسيط مخصص لضغط المحتوى مع تحسينات إضافية
    """

    def process_response(self, request, response):
        # تجاهل FileResponse لأنه يستخدم streaming_content
        if hasattr(response, "streaming_content"):
            return response

        # تجاهل الملفات المضغوطة بالفعل
        if response.has_header("Content-Encoding"):
            return response

        # تجاهل الملفات الصغيرة
        try:
            if len(response.content) < 200:
                return response
        except (AttributeError, ValueError):
            return response

        return super().process_response(request, response)


class PerformanceMiddleware:
    """
    وسيط لقياس وتحسين الأداء
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # قياس وقت الاستجابة
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        # إضافة رؤوس HTTP لتحسين الأداء
        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # تعيين Cache-Control للمحتوى الثابت
        if request.path.startswith(settings.STATIC_URL):
            response["Cache-Control"] = "public, max-age=31536000"
        elif request.path.startswith(settings.MEDIA_URL):
            response["Cache-Control"] = "public, max-age=2592000"
        else:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"

        # تسجيل الطلبات البطيئة
        if duration > 1.0:  # أكثر من ثانية
            print(f"Slow request: {request.path} took {duration:.2f}s")

        return response


class LazyLoadMiddleware:
    """
    وسيط لتطبيق التحميل الكسول للصور
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.img_pattern = re.compile(r"<img([^>]+)>")

    def __call__(self, request):
        response = self.get_response(request)

        # تجاهل FileResponse و StreamingResponse
        if hasattr(response, "streaming_content"):
            return response

        if "text/html" not in response.get("Content-Type", ""):
            return response

        # تطبيق loading="lazy" على الصور
        try:
            if isinstance(response.content, bytes):
                content = response.content.decode("utf-8")
            else:
                content = response.content

            def add_lazy_loading(match):
                if "loading=" not in match.group(1):
                    return f'<img{match.group(1)} loading="lazy">'
                return match.group(0)

            modified_content = self.img_pattern.sub(add_lazy_loading, content)
            response.content = modified_content.encode("utf-8")
        except (AttributeError, ValueError):
            return response

        return response


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user = SimpleLazyObject(lambda: self._get_user(request))
        return self.get_response(request)

    def _get_user(self, request):
        user = get_user(request)
        if user.is_authenticated:
            return user

        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(
                request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
            )
            user = jwt_auth.get_user(validated_token)
            return user
        except Exception:
            return user


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # إضافة التوكن للكوكيز عند تسجيل الدخول
        if request.path == "/api/token/" and response.status_code == 200:
            data = response.data
            if "access" in data:
                response.set_cookie(
                    settings.SIMPLE_JWT["AUTH_COOKIE"],
                    data["access"],
                    max_age=settings.SIMPLE_JWT[
                        "ACCESS_TOKEN_LIFETIME"
                    ].total_seconds(),
                    httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                    samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
                )
        return response
