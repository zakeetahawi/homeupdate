
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
