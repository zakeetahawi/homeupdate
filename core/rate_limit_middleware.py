"""
🔒 Rate Limiting Middleware
حماية من هجمات Brute Force على صفحات تسجيل الدخول

الاستخدام:
1. أضف 'core.security_middleware.RateLimitMiddleware' إلى MIDDLEWARE
2. تأكد من وجود Redis للتخزين
"""

import time
import logging
from functools import wraps
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.shortcuts import render

logger = logging.getLogger('django.security')


class RateLimitMiddleware:
    """
    Middleware للحد من عدد الطلبات (Rate Limiting)
    يحمي من هجمات Brute Force
    """
    
    # الصفحات المحمية بـ Rate Limiting
    PROTECTED_PATHS = [
        '/accounts/login/',
        '/admin/login/',
        '/api/auth/login/',
        '/api/token/',
        '/api/token/refresh/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        # إعدادات Rate Limit
        self.rate_config = getattr(settings, 'RATE_LIMIT_LOGIN', {
            'ATTEMPTS': 5,
            'TIMEOUT': 300,
            'BLOCK_IP': True,
        })
    
    def __call__(self, request):
        # فحص Rate Limit للصفحات المحمية فقط
        if request.method == 'POST' and self._is_protected_path(request.path):
            client_ip = self._get_client_ip(request)
            
            # فحص إذا كان IP محظور
            if self._is_blocked(client_ip):
                remaining = self._get_block_remaining(client_ip)
                logger.warning(
                    f"Rate limit exceeded - IP blocked: {client_ip} | "
                    f"Path: {request.path} | Remaining: {remaining}s"
                )
                return self._blocked_response(request, remaining)
            
            # تسجيل المحاولة
            attempts = self._record_attempt(client_ip)
            
            # حظر إذا تجاوز الحد
            if attempts >= self.rate_config['ATTEMPTS']:
                self._block_ip(client_ip)
                logger.warning(
                    f"IP blocked after {attempts} attempts: {client_ip} | "
                    f"Path: {request.path}"
                )
        
        response = self.get_response(request)
        
        # إعادة تعيين العداد بعد تسجيل دخول ناجح
        if request.method == 'POST' and self._is_protected_path(request.path):
            if response.status_code in [200, 302]:
                # تحقق من نجاح تسجيل الدخول
                if hasattr(request, 'user') and request.user.is_authenticated:
                    client_ip = self._get_client_ip(request)
                    self._reset_attempts(client_ip)
                    logger.info(f"Rate limit reset after successful login: {client_ip}")
        
        return response
    
    def _is_protected_path(self, path):
        """فحص إذا كان المسار محمياً"""
        return any(path.startswith(p) for p in self.PROTECTED_PATHS)
    
    def _get_client_ip(self, request):
        """الحصول على IP العميل الحقيقي"""
        # دعم Cloudflare و Proxies
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('HTTP_CF_CONNECTING_IP',
                   request.META.get('HTTP_X_REAL_IP',
                   request.META.get('REMOTE_ADDR', '0.0.0.0')))
        return ip
    
    def _get_cache_key(self, ip, key_type='attempts'):
        """إنشاء مفتاح Cache"""
        return f"rate_limit:{key_type}:{ip}"
    
    def _record_attempt(self, ip):
        """تسجيل محاولة تسجيل دخول"""
        key = self._get_cache_key(ip, 'attempts')
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, self.rate_config['TIMEOUT'])
        return attempts
    
    def _reset_attempts(self, ip):
        """إعادة تعيين عدد المحاولات"""
        key = self._get_cache_key(ip, 'attempts')
        cache.delete(key)
        # إزالة الحظر أيضاً
        block_key = self._get_cache_key(ip, 'blocked')
        cache.delete(block_key)
    
    def _block_ip(self, ip):
        """حظر IP"""
        if self.rate_config.get('BLOCK_IP', True):
            key = self._get_cache_key(ip, 'blocked')
            cache.set(key, time.time(), self.rate_config['TIMEOUT'])
    
    def _is_blocked(self, ip):
        """فحص إذا كان IP محظور"""
        key = self._get_cache_key(ip, 'blocked')
        return cache.get(key) is not None
    
    def _get_block_remaining(self, ip):
        """الحصول على الوقت المتبقي للحظر"""
        key = self._get_cache_key(ip, 'blocked')
        blocked_at = cache.get(key)
        if blocked_at:
            elapsed = time.time() - blocked_at
            remaining = max(0, self.rate_config['TIMEOUT'] - int(elapsed))
            return remaining
        return 0
    
    def _blocked_response(self, request, remaining):
        """إرجاع استجابة الحظر"""
        # للـ API
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Too many login attempts',
                'message': f'تم حظرك مؤقتاً. حاول مرة أخرى بعد {remaining} ثانية.',
                'retry_after': remaining,
            }, status=429)
        
        # للصفحات العادية
        return HttpResponseForbidden(
            f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>تم حظرك مؤقتاً</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 15px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 400px;
                    }}
                    h1 {{ color: #e74c3c; margin-bottom: 10px; }}
                    p {{ color: #666; line-height: 1.6; }}
                    .timer {{
                        font-size: 48px;
                        font-weight: bold;
                        color: #3498db;
                        margin: 20px 0;
                    }}
                    .icon {{ font-size: 64px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">🔒</div>
                    <h1>تم حظرك مؤقتاً</h1>
                    <p>لقد تجاوزت عدد محاولات تسجيل الدخول المسموحة.</p>
                    <p>يرجى الانتظار قبل المحاولة مرة أخرى.</p>
                    <div class="timer" id="timer">{remaining}</div>
                    <p>ثانية</p>
                </div>
                <script>
                    let time = {remaining};
                    const timer = document.getElementById('timer');
                    const interval = setInterval(() => {{
                        time--;
                        timer.textContent = time;
                        if (time <= 0) {{
                            clearInterval(interval);
                            location.reload();
                        }}
                    }}, 1000);
                </script>
            </body>
            </html>
            """
        )


def rate_limit(attempts=5, timeout=300):
    """
    Decorator للحد من عدد الطلبات على View معين
    
    @rate_limit(attempts=3, timeout=60)
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # الحصول على IP العميل
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
            
            # مفتاح Cache
            key = f"rate_limit:{view_func.__name__}:{ip}"
            
            # فحص عدد المحاولات
            current = cache.get(key, 0)
            
            if current >= attempts:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': timeout,
                }, status=429)
            
            # تسجيل المحاولة
            cache.set(key, current + 1, timeout)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class SecurityHeadersMiddleware:
    """
    Middleware لإضافة Security Headers إضافية
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # إضافة headers أمنية
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (بديل Feature-Policy)
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()'
        )
        
        # إزالة headers تكشف معلومات
        if 'X-Powered-By' in response:
            del response['X-Powered-By']
        
        return response


class SQLInjectionProtectionMiddleware:
    """
    Middleware للحماية من SQL Injection الأساسي
    يفحص المدخلات للأنماط الخطرة
    """
    
    DANGEROUS_PATTERNS = [
        "' OR '1'='1",
        "'; DROP TABLE",
        "'; DELETE FROM",
        "UNION SELECT",
        "1=1--",
        "' OR 1=1",
        "<script>",
        "javascript:",
        "onclick=",
        "onerror=",
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # فحص GET parameters
        for key, value in request.GET.items():
            if self._is_dangerous(value):
                logger.warning(
                    f"Potential SQL Injection detected in GET: {key}={value[:50]} | "
                    f"IP: {request.META.get('REMOTE_ADDR')} | Path: {request.path}"
                )
                return HttpResponseForbidden("Invalid request detected")
        
        # فحص POST parameters
        for key, value in request.POST.items():
            if isinstance(value, str) and self._is_dangerous(value):
                logger.warning(
                    f"Potential SQL Injection detected in POST: {key} | "
                    f"IP: {request.META.get('REMOTE_ADDR')} | Path: {request.path}"
                )
                return HttpResponseForbidden("Invalid request detected")
        
        return self.get_response(request)
    
    def _is_dangerous(self, value):
        """فحص إذا كانت القيمة تحتوي على أنماط خطرة"""
        if not isinstance(value, str):
            return False
        
        value_upper = value.upper()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.upper() in value_upper:
                return True
        return False
