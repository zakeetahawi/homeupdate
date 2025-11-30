"""
Middleware للأمان المتقدم
يوفر حماية إضافية من الهجمات المختلفة
"""

import hashlib
import time
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('security')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    إضافة Security Headers متقدمة لجميع الاستجابات
    """
    
    def process_response(self, request, response):
        # Content Security Policy
        if not settings.DEBUG:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net code.jquery.com static.cloudflareinsights.com unpkg.com; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' cdn.jsdelivr.net; "
                "connect-src 'self' cloudflareinsights.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
            response['Content-Security-Policy'] = csp_policy
        
        # Permissions Policy (Feature Policy) - السماح بالكاميرا للمستخدم
        # camera=(self) يسمح باستخدام الكاميرا في الصفحة نفسها فقط بناءً على إذن المستخدم
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(self), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=()'
        )
        
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options (إضافي للحماية)
        if not response.get('X-Frame-Options'):
            response['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Cross-Origin Policies (فقط في الإنتاج)
        if not settings.DEBUG:
            response['Cross-Origin-Opener-Policy'] = 'same-origin'
            response['Cross-Origin-Resource-Policy'] = 'same-origin'
            response['Cross-Origin-Embedder-Policy'] = 'require-corp'
        
        # إزالة معلومات الخادم
        if 'Server' in response:
            del response['Server']
        if 'X-Powered-By' in response:
            del response['X-Powered-By']
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    حماية من هجمات DDoS و Brute Force
    """
    
    def get_client_ip(self, request):
        """الحصول على IP العميل الحقيقي"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def process_request(self, request):
        # تخطي للطلبات الآمنة
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return None
        
        # تخطي إذا لم يكن المستخدم مصادقاً
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        ip = self.get_client_ip(request)
        path = request.path
        
        # مفتاح التخزين المؤقت
        cache_key = f'rate_limit:{ip}:{path}'
        
        # الحصول على عدد الطلبات
        requests_count = cache.get(cache_key, 0)
        
        # الحد الأقصى: 10 طلبات في الدقيقة للصفحات الحساسة
        max_requests = 10
        window = 60  # ثانية
        
        # صفحات حساسة تحتاج حماية أكثر
        sensitive_paths = ['/accounts/login/', '/accounts/password/', '/admin/']
        if any(path.startswith(sp) for sp in sensitive_paths):
            max_requests = 5
        
        if requests_count >= max_requests:
            logger.warning(f'Rate limit exceeded for IP {ip} on {path}')
            
            # حظر مؤقت
            block_key = f'blocked:{ip}'
            cache.set(block_key, True, 300)  # حظر لمدة 5 دقائق
            
            return JsonResponse({
                'error': 'تم تجاوز الحد المسموح من الطلبات. يرجى المحاولة بعد 5 دقائق.',
                'retry_after': 300
            }, status=429)
        
        # تحديث العداد
        cache.set(cache_key, requests_count + 1, window)
        
        return None


class BruteForceProtectionMiddleware(MiddlewareMixin):
    """
    حماية من هجمات Brute Force على تسجيل الدخول
    """
    
    def process_request(self, request):
        # فقط لصفحات تسجيل الدخول
        if request.path not in ['/accounts/login/', '/admin/login/']:
            return None
        
        if request.method != 'POST':
            return None
        
        ip = self.get_client_ip(request)
        
        # التحقق من الحظر
        block_key = f'login_blocked:{ip}'
        if cache.get(block_key):
            return HttpResponseForbidden(
                'تم حظر عنوان IP هذا مؤقتاً بسبب محاولات تسجيل دخول فاشلة متعددة. '
                'يرجى المحاولة بعد 30 دقيقة.'
            )
        
        return None
    
    def process_response(self, request, response):
        # تسجيل محاولات الفشل
        if request.path in ['/accounts/login/', '/admin/login/']:
            if request.method == 'POST' and response.status_code in [200, 302]:
                # تحقق من وجود أخطاء في النموذج
                if hasattr(response, 'context_data'):
                    form = response.context_data.get('form')
                    if form and form.errors:
                        self.record_failed_login(request)
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def record_failed_login(self, request):
        """تسجيل محاولة فاشلة"""
        ip = self.get_client_ip(request)
        cache_key = f'login_attempts:{ip}'
        
        attempts = cache.get(cache_key, 0) + 1
        cache.set(cache_key, attempts, 1800)  # 30 دقيقة
        
        # بعد 5 محاولات فاشلة، حظر لمدة 30 دقيقة
        if attempts >= 5:
            block_key = f'login_blocked:{ip}'
            cache.set(block_key, True, 1800)
            logger.warning(f'IP {ip} blocked due to {attempts} failed login attempts')


class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """
    فحص إضافي لحماية من SQL Injection
    """
    
    # أنماط SQL Injection الشائعة
    SQL_PATTERNS = [
        'union.*select', 'insert.*into', 'delete.*from', 
        'drop.*table', 'update.*set', '--', ';--',
        'xp_cmdshell', 'exec.*sp_', '0x[0-9a-f]+',
        '@@version', 'benchmark\\(', 'sleep\\(',
    ]
    
    def process_request(self, request):
        # فحص GET parameters
        for key, value in request.GET.items():
            if self.is_sql_injection_attempt(value):
                logger.error(f'SQL Injection attempt detected in GET: {key}={value}')
                return HttpResponseForbidden('طلب مشبوه تم رفضه')
        
        # فحص POST parameters
        if request.method == 'POST':
            for key, value in request.POST.items():
                if isinstance(value, str) and self.is_sql_injection_attempt(value):
                    logger.error(f'SQL Injection attempt detected in POST: {key}')
                    return HttpResponseForbidden('طلب مشبوه تم رفضه')
        
        return None
    
    def is_sql_injection_attempt(self, value):
        """التحقق من محاولة SQL Injection"""
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        
        import re
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, value_lower):
                return True
        
        return False


class XSSProtectionMiddleware(MiddlewareMixin):
    """
    فحص إضافي لحماية من XSS
    """
    
    XSS_PATTERNS = [
        '<script', 'javascript:', 'onerror=', 'onload=',
        'onclick=', 'onmouseover=', '<iframe', 'eval\\(',
        'expression\\(', 'vbscript:', 'data:text/html',
    ]
    
    def process_request(self, request):
        # فحص GET parameters
        for key, value in request.GET.items():
            if isinstance(value, str) and self.is_xss_attempt(value):
                logger.error(f'XSS attempt detected in GET: {key}={value[:50]}')
                return HttpResponseForbidden('طلب مشبوه تم رفضه')
        
        # فحص POST parameters (ما عدا الحقول المسموح بها بـ HTML)
        if request.method == 'POST':
            allowed_html_fields = ['content', 'description', 'body']  # حقول مسموح بها
            
            for key, value in request.POST.items():
                if key not in allowed_html_fields:
                    if isinstance(value, str) and self.is_xss_attempt(value):
                        logger.error(f'XSS attempt detected in POST: {key}')
                        return HttpResponseForbidden('طلب مشبوه تم رفضه')
        
        return None
    
    def is_xss_attempt(self, value):
        """التحقق من محاولة XSS"""
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        
        import re
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value_lower):
                return True
        
        return False


class SecureSessionMiddleware(MiddlewareMixin):
    """
    تعزيز أمان الجلسات
    ملاحظة: تم تعطيل جميع الفحوصات التي كانت تسبب تسجيل خروج متكرر
    """
    
    def process_request(self, request):
        # ⚠️ تم تعطيل تجديد مفتاح الجلسة لأنه كان يسبب مشاكل في تسجيل الخروج
        # cycle_key() يغير session_key مما يسبب فقدان الجلسة أحياناً
        # خاصة عند استخدام cached_db backend
        
        # الكود المعطل:
        # if request.user.is_authenticated and hasattr(request, 'session') and request.session.session_key:
        #     session_key = f'session_age:{request.session.session_key}'
        #     last_rotation = cache.get(session_key)
        #     rotation_interval = 6 * 60 * 60  # 6 ساعات
        #     if not last_rotation or time.time() - last_rotation > rotation_interval:
        #         try:
        #             request.session.cycle_key()
        #             cache.set(session_key, time.time(), rotation_interval)
        #         except Exception as e:
        #             logger.debug(f'Session key rotation skipped: {e}')
        
        # ⚠️ تم تعطيل التحقق من User-Agent أيضاً
        # لأنه كان يسبب تسجيل خروج عند تغير User-Agent
        
        return None
