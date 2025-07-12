"""
Performance Middleware - وسطاء قياس وتحسين الأداء
"""

import time
import logging
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class PerformanceMiddleware(MiddlewareMixin):
    """
    Middleware لمراقبة وتحسين الأداء
    """
    
    def process_request(self, request):
        # تسجيل وقت بداية الطلب
        request.start_time = time.time()
        
        # إضافة cache headers
        if not request.path.startswith('/admin/'):
            request.cache_key = f"page:{request.path}:{request.user.id if request.user.is_authenticated else 'anonymous'}"
            
            # محاولة استرجاع من cache
            cached_response = cache.get(request.cache_key)
            if cached_response:
                return cached_response
        
        return None
    
    def process_response(self, request, response):
        # حساب وقت الاستجابة
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # تسجيل الأداء البطيء
            if duration > 1.0:  # أكثر من ثانية واحدة
                logger.warning(f"بطيء: {request.path} استغرق {duration:.2f} ثانية")
            
            # إضافة headers للأداء
            response['X-Response-Time'] = f"{duration:.3f}s"
            
            # cache للصفحات العامة
            if (hasattr(request, 'cache_key') and 
                response.status_code == 200 and 
                not request.path.startswith('/admin/')):
                
                # cache لمدة 5 دقائق للصفحات العامة
                cache.set(request.cache_key, response, 300)
        
        return response
    
    def process_exception(self, request, exception):
        # تسجيل الأخطاء
        logger.error(f"خطأ في {request.path}: {str(exception)}")
        return None


class LazyLoadMiddleware:
    """وسيط التحميل الكسول للصور"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # إضافة headers للتحميل الكسول
        if hasattr(response, 'content') and 'text/html' in response.get('Content-Type', ''):
            response['X-Lazy-Load'] = 'enabled'
        
        return response


class QueryOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware لتحسين الاستعلامات
    """
    
    def process_request(self, request):
        # إعادة تعيين عداد الاستعلامات
        request.query_count = 0
        return None
    
    def process_response(self, request, response):
        # مراقبة عدد الاستعلامات
        if hasattr(request, 'query_count'):
            query_count = len(connection.queries)
            
            # تحذير من الاستعلامات الكثيرة
            if query_count > 20:
                logger.warning(f"كثير من الاستعلامات في {request.path}: {query_count} استعلام")
            
            response['X-Query-Count'] = str(query_count)
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware لإضافة headers الأمان
    """
    
    def process_response(self, request, response):
        # إضافة security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # إضافة CSP header
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self';"
        )
        response['Content-Security-Policy'] = csp_policy
        
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
            response.set_cookie('performance_time', f"{duration:.3f}", max_age=60)
            response.set_cookie('performance_path', request.path, max_age=60)
        
        return response


class CustomGZipMiddleware:
    """وسيط ضغط مخصص"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # إضافة headers للضغط
        if hasattr(response, 'content'):
            response['X-Compression'] = 'gzip'
        
        return response


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware لمراقبة أداء الطلبات والاستعلامات
    """
    
    def process_request(self, request):
        # تسجيل وقت بداية الطلب
        request.start_time = time.time()
        
        # تسجيل عدد الاستعلامات في بداية الطلب
        request.initial_queries = len(connection.queries)
        
        return None
    
    def process_response(self, request, response):
        # حساب وقت الاستجابة
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            
            # حساب عدد الاستعلامات
            final_queries = len(connection.queries)
            queries_count = final_queries - getattr(request, 'initial_queries', 0)
            
            # تسجيل الأداء إذا كان بطيئاً
            if response_time > 1.0:  # أكثر من ثانية واحدة
                logger.warning(
                    f'Slow request: {request.path} took {response_time:.2f}s '
                    f'with {queries_count} queries'
                )
            
            # إضافة headers للأداء
            response['X-Response-Time'] = f'{response_time:.3f}s'
            response['X-Query-Count'] = str(queries_count)
            
            # تسجيل إحصائيات الأداء
            self.log_performance(request, response_time, queries_count)
        
        return response
    
    def process_exception(self, request, exception):
        # تسجيل الأخطاء مع معلومات الأداء
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            logger.error(
                f'Exception in {request.path}: {exception} '
                f'(took {response_time:.2f}s)'
            )
        return None
    
    def log_performance(self, request, response_time, queries_count):
        """تسجيل إحصائيات الأداء"""
        path = request.path
        method = request.method
        
        # تصنيف الطلبات حسب الأداء
        if response_time < 0.1:
            performance_level = 'excellent'
        elif response_time < 0.5:
            performance_level = 'good'
        elif response_time < 1.0:
            performance_level = 'acceptable'
        else:
            performance_level = 'slow'
        
        # تسجيل الإحصائيات
        logger.info(
            f'Performance: {method} {path} - '
            f'{response_time:.3f}s, {queries_count} queries, '
            f'{performance_level}'
        )

class DatabaseQueryMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware لمراقبة استعلامات قاعدة البيانات
    """
    
    def process_request(self, request):
        # إعادة تعيين عداد الاستعلامات
        connection.queries_log = []
        return None
    
    def process_response(self, request, response):
        # تحليل الاستعلامات البطيئة
        slow_queries = []
        for query in connection.queries:
            if float(query['time']) > 0.1:  # أكثر من 100ms
                slow_queries.append({
                    'sql': query['sql'][:200] + '...' if len(query['sql']) > 200 else query['sql'],
                    'time': query['time']
                })
        
        # تسجيل الاستعلامات البطيئة
        if slow_queries:
            logger.warning(
                f'Slow queries in {request.path}: '
                f'{len(slow_queries)} queries > 100ms'
            )
            for query in slow_queries:
                logger.warning(f'Slow query: {query["time"]}ms - {query["sql"]}')
        
        return response

class CacheMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware لمراقبة استخدام الذاكرة المؤقتة
    """
    
    def process_request(self, request):
        # إضافة معلومات الذاكرة المؤقتة للطلب
        request.cache_hits = 0
        request.cache_misses = 0
        return None
    
    def process_response(self, request, response):
        # تسجيل إحصائيات الذاكرة المؤقتة
        if hasattr(request, 'cache_hits') and hasattr(request, 'cache_misses'):
            total_requests = request.cache_hits + request.cache_misses
            if total_requests > 0:
                hit_rate = (request.cache_hits / total_requests) * 100
                logger.info(
                    f'Cache stats for {request.path}: '
                    f'{request.cache_hits} hits, {request.cache_misses} misses '
                    f'({hit_rate:.1f}% hit rate)'
                )
        
        return response
