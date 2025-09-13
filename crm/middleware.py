import json
import traceback
import time
import logging
import re
from django.http import HttpResponse, HttpResponseGone
from django.conf import settings
from django.db import connection
from django.middleware.gzip import GZipMiddleware
from django.utils.functional import SimpleLazyObject
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.middleware import get_user
from rest_framework_simplejwt.tokens import AccessToken

# إعداد السجل الخاص بالاستعلامات البطيئة
slow_queries_logger = logging.getLogger('slow_queries')
query_logger = logging.getLogger('django.db.backends')
websocket_logger = logging.getLogger('websocket_blocker')


class BlockWebSocketMiddleware(MiddlewareMixin):
    """
    Middleware لحظر جميع طلبات WebSocket والدردشة
    """

    def process_request(self, request):
        """
        فحص الطلبات وحظر طلبات WebSocket
        """
        path = request.path.lower()

        # قائمة المسارات المحظورة
        blocked_paths = [
            '/ws/',
            '/websocket/',
            '/chat/',
            '/socket.io/',
            '/ws/chat/',
            '/chat/general/',
            '/ws/chat/general/',
        ]

        # فحص إذا كان المسار محظور
        for blocked_path in blocked_paths:
            if blocked_path in path:
                # تسجيل معلومات الطلب
                user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
                referer = request.META.get('HTTP_REFERER', 'No referer')
                remote_addr = request.META.get('REMOTE_ADDR', 'Unknown IP')

                websocket_logger.warning(
                    f"🚫 Blocked WebSocket request: {path} - "
                    f"IP: {remote_addr}, "
                    f"User-Agent: {user_agent[:50]}..., "
                    f"Referer: {referer}"
                )

                # إرجاع 410 Gone مع headers قوية
                response = HttpResponseGone(
                    "WebSocket and chat services have been permanently removed. "
                    "Please clear your browser cache and disable any chat-related extensions."
                )
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                response['Retry-After'] = '86400'  # 24 ساعة
                response['X-Chat-Status'] = 'PERMANENTLY_REMOVED'
                response['X-WebSocket-Status'] = 'DISABLED'
                response['Connection'] = 'close'

                return response

        # فحص headers للطلبات WebSocket
        upgrade_header = request.META.get('HTTP_UPGRADE', '').lower()
        connection_header = request.META.get('HTTP_CONNECTION', '').lower()

        if upgrade_header == 'websocket' or 'upgrade' in connection_header:
            websocket_logger.warning(
                f"🚫 Blocked WebSocket upgrade request: {path} - "
                f"Upgrade: {upgrade_header}, Connection: {connection_header}"
            )

            response = HttpResponseGone("WebSocket connections are not supported")
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Connection'] = 'close'
            return response

        return None


class QueryAnalysisMiddleware(MiddlewareMixin):
    """Middleware لتحليل وتسجيل الاستعلامات البطيئة"""
    
    def process_request(self, request):
        """بداية تتبع الاستعلامات"""
        self.start_time = time.time()
        self.start_queries = len(connection.queries)
        return None
    
    def process_response(self, request, response):
        """تحليل الاستعلامات في نهاية الطلب"""
        if not settings.DEBUG:
            return response
            
        total_time = time.time() - self.start_time
        total_queries = len(connection.queries) - self.start_queries
        
        # تسجيل المعلومات الأساسية
        if total_time > getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1.0):
            query_logger.warning(
                f"بطء في الطلب: {request.path} - "
                f"الوقت: {total_time:.3f}s، "
                f"الاستعلامات: {total_queries}"
            )
        
        # تحليل الاستعلامات البطيئة
        slow_queries = []
        for query in connection.queries[-total_queries:]:
            query_time = float(query['time'])
            if query_time > getattr(settings, 'SLOW_QUERY_THRESHOLD', 0.1):
                slow_queries.append({
                    'sql': query['sql'][:200] + '...' if len(query['sql']) > 200 else query['sql'],
                    'time': query_time
                })
        
        if slow_queries:
            query_logger.warning(
                f"استعلامات بطيئة في {request.path}:\n" +
                "\n".join([f"  - {q['time']:.3f}s: {q['sql']}" for q in slow_queries])
            )
        
        # إضافة headers للمطورين
        if settings.DEBUG:
            response['X-DB-Queries'] = str(total_queries)
            response['X-DB-Time'] = f"{total_time:.3f}s"
            response['X-Slow-Queries'] = str(len(slow_queries))
        
        return response

class DebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if settings.DEBUG:
            # Print the exception details
            print("\n\n=== EXCEPTION DETAILS ===")
            print(f"Exception Type: {type(exception).__name__}")
            print(f"Exception Message: {str(exception)}")
            print(f"Request Path: {request.path}")
            print(f"Request Method: {request.method}")
            
            # Print request data
            print("\n=== REQUEST DATA ===")
            print(f"GET Parameters: {request.GET}")
            
            if request.method == 'POST':
                print("\n=== POST DATA ===")
                for key, value in request.POST.items():
                    # Limit the output length for large values
                    if isinstance(value, str) and len(value) > 1000:
                        print(f"{key}: {value[:1000]}... (truncated)")
                    else:
                        print(f"{key}: {value}")
            
            # Print traceback
            print("\n=== TRACEBACK ===")
            traceback.print_exc()
            print("=====================\n\n")
            
            # Return a detailed error response in development
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse(
                    json.dumps({
                        'error': str(exception),
                        'type': type(exception).__name__,
                        'traceback': traceback.format_exc()
                    }),
                    content_type='application/json',
                    status=500
                )
        
        # Let Django handle the exception
        return None

class QueryPerformanceMiddleware:
    """
    وسيط لمراقبة أداء استعلامات قاعدة البيانات وتسجيل الاستعلامات البطيئة
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # حد العتبة للاستعلامات البطيئة بالثواني (50 مللي ثانية = 0.05 ثانية)
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 0.05)
    
    def __call__(self, request):
        # تنفيذ أي كود قبل معالجة الطلب
        
        # قياس وقت تنفيذ الطلب
        start_time = time.time()
        start_queries = len(connection.queries)
        
        # معالجة الطلب
        response = self.get_response(request)
        
        # قياس الوقت بعد انتهاء الطلب
        duration = time.time() - start_time
        end_queries = len(connection.queries)
        
        # تسجيل الاستعلامات البطيئة إذا كان التصحيح مفعَّلاً
        if settings.DEBUG:
            queries_executed = end_queries - start_queries
            if queries_executed > 0:
                slow_queries = []
                for query in connection.queries[start_queries:end_queries]:
                    query_time = float(query.get('time', 0))
                    if query_time > self.slow_query_threshold:
                        slow_queries.append({
                            'sql': query.get('sql'),
                            'time': query_time,
                        })
                
                if slow_queries:
                    # Using ASCII-only text for log messages to avoid encoding issues
                    slow_queries_logger.warning(
                        f"Found {len(slow_queries)} slow queries in request {request.path}:\n" +
                        "\n".join([f"Time: {q['time']:.4f}s: {q['sql']}" for q in slow_queries])
                    )
            
            # تسجيل إجمالي الاستعلامات والوقت المستغرق
            if queries_executed > 10:
                # Using ASCII-only text for log messages
                slow_queries_logger.info(
                    f"Executed {queries_executed} queries in request {request.path} in {duration:.4f} seconds"
                )
        
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
        if settings.DEBUG and hasattr(request, 'user') and request.user.is_superuser:
            duration = time.time() - start_time
            queries_executed = len(connection.queries) - start_queries
            
            # استخدام نص ASCII فقط لتجنب مشاكل الترميز
            response.set_cookie(
                'performance_info',
                f"Time: {duration:.4f}s | Queries: {queries_executed}",
                max_age=30,  # 30 seconds
                httponly=False,
                samesite='Lax'
            )
            
        return response

class CustomGZipMiddleware(GZipMiddleware):
    """
    وسيط مخصص لضغط المحتوى مع تحسينات إضافية
    """
    def process_response(self, request, response):
        # تجاهل FileResponse لأنه يستخدم streaming_content
        if hasattr(response, 'streaming_content'):
            return response
            
        # تجاهل الملفات المضغوطة بالفعل
        if response.has_header('Content-Encoding'):
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
        response['X-Frame-Options'] = 'DENY'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # تعيين Cache-Control للمحتوى الثابت
        if request.path.startswith(settings.STATIC_URL):
            response['Cache-Control'] = 'public, max-age=31536000'
        elif request.path.startswith(settings.MEDIA_URL):
            response['Cache-Control'] = 'public, max-age=2592000'
        else:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'

        # تسجيل الطلبات البطيئة
        if duration > 1.0:  # أكثر من ثانية
            print(f'Slow request: {request.path} took {duration:.2f}s')

        return response

class LazyLoadMiddleware:
    """
    وسيط لتطبيق التحميل الكسول للصور
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.img_pattern = re.compile(r'<img([^>]+)>')

    def __call__(self, request):
        response = self.get_response(request)
        
        # تجاهل FileResponse و StreamingResponse
        if hasattr(response, 'streaming_content'):
            return response
        
        if 'text/html' not in response.get('Content-Type', ''):
            return response
            
        # تطبيق loading="lazy" على الصور
        try:
            if isinstance(response.content, bytes):
                content = response.content.decode('utf-8')
            else:
                content = response.content
                
            def add_lazy_loading(match):
                if 'loading=' not in match.group(1):
                    return f'<img{match.group(1)} loading="lazy">'
                return match.group(0)
                
            modified_content = self.img_pattern.sub(add_lazy_loading, content)
            response.content = modified_content.encode('utf-8')
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
            validated_token = jwt_auth.get_validated_token(request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE']))
            user = jwt_auth.get_user(validated_token)
            return user
        except:
            return user

class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # إضافة التوكن للكوكيز عند تسجيل الدخول
        if request.path == '/api/token/' and response.status_code == 200:
            data = response.data
            if 'access' in data:
                response.set_cookie(
                    settings.SIMPLE_JWT['AUTH_COOKIE'],
                    data['access'],
                    max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
                    httponly=settings.SIMPLE_JWT['AUTH_COOKIE_HTTP_ONLY'],
                    samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
                )
        return response
