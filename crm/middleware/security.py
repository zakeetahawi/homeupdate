"""
Security Middleware - وسطاء الأمان المتقدمة
"""

import re
import logging
import hashlib
import time
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware أساسي للأمان
    """
    
    def process_request(self, request):
        # فحص headers الأمان
        if not self._check_security_headers(request):
            return HttpResponseForbidden("طلب غير آمن")
        
        # فحص rate limiting
        if not self._check_rate_limit(request):
            return HttpResponseForbidden("تجاوز حد الطلبات")
        
        # فحص CSRF
        if not self._check_csrf(request):
            return HttpResponseForbidden("خطأ في CSRF")
        
        # فحص SQL Injection
        if self._detect_sql_injection(request):
            logger.warning(f"محاولة SQL Injection من {request.META.get('REMOTE_ADDR')}")
            return HttpResponseForbidden("طلب غير آمن")
        
        # فحص XSS
        if self._detect_xss(request):
            logger.warning(f"محاولة XSS من {request.META.get('REMOTE_ADDR')}")
            return HttpResponseForbidden("طلب غير آمن")
        
        return None
    
    def _check_security_headers(self, request):
        """فحص headers الأمان"""
        # فحص Origin header
        origin = request.META.get('HTTP_ORIGIN')
        if origin and not self._is_allowed_origin(origin):
            return False
        
        # فحص Referer header
        referer = request.META.get('HTTP_REFERER')
        if referer and not self._is_allowed_referer(referer):
            return False
        
        return True
    
    def _is_allowed_origin(self, origin):
        """فحص إذا كان Origin مسموح"""
        allowed_origins = getattr(settings, 'ALLOWED_ORIGINS', [])
        return origin in allowed_origins
    
    def _is_allowed_referer(self, referer):
        """فحص إذا كان Referer مسموح"""
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        for host in allowed_hosts:
            if host in referer:
                return True
        return False
    
    def _check_rate_limit(self, request):
        """فحص حد الطلبات"""
        client_ip = self._get_client_ip(request)
        rate_limit_key = f"rate_limit:{client_ip}"
        
        # الحصول على عدد الطلبات الحالي
        request_count = cache.get(rate_limit_key, 0)
        
        # فحص الحد (100 طلب في الدقيقة)
        if request_count > 100:
            return False
        
        # زيادة العداد
        cache.set(rate_limit_key, request_count + 1, 60)
        return True
    
    def _get_client_ip(self, request):
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _check_csrf(self, request):
        """فحص CSRF"""
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # فحص CSRF token
        csrf_token = request.META.get('CSRF_COOKIE')
        if not csrf_token:
            return False
        
        return True
    
    def _detect_sql_injection(self, request):
        """كشف SQL Injection"""
        sql_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(or|and)\b\s+\d+\s*=\s*\d+)',
            r'(\b(union|select)\b.*\bfrom\b)',
            r'(\b(union|select)\b.*\bwhere\b)',
            r'(\b(union|select)\b.*\border\b\s+by)',
            r'(\b(union|select)\b.*\bgroup\b\s+by)',
            r'(\b(union|select)\b.*\bhaving\b)',
            r'(\b(union|select)\b.*\blimit\b)',
            r'(\b(union|select)\b.*\boffset\b)',
            r'(\b(union|select)\b.*\btop\b)',
            r'(\b(union|select)\b.*\bdistinct\b)',
            r'(\b(union|select)\b.*\bcount\b)',
            r'(\b(union|select)\b.*\bsum\b)',
            r'(\b(union|select)\b.*\bavg\b)',
            r'(\b(union|select)\b.*\bmax\b)',
            r'(\b(union|select)\b.*\bmin\b)',
            r'(\b(union|select)\b.*\bcase\b)',
            r'(\b(union|select)\b.*\bwhen\b)',
            r'(\b(union|select)\b.*\bthen\b)',
            r'(\b(union|select)\b.*\belse\b)',
            r'(\b(union|select)\b.*\bend\b)',
            r'(\b(union|select)\b.*\bas\b)',
            r'(\b(union|select)\b.*\bin\b)',
            r'(\b(union|select)\b.*\bbetween\b)',
            r'(\b(union|select)\b.*\blike\b)',
            r'(\b(union|select)\b.*\bis\s+null\b)',
            r'(\b(union|select)\b.*\bis\s+not\s+null\b)',
            r'(\b(union|select)\b.*\bexists\b)',
            r'(\b(union|select)\b.*\bnot\s+exists\b)',
            r'(\b(union|select)\b.*\bany\b)',
            r'(\b(union|select)\b.*\ball\b)',
            r'(\b(union|select)\b.*\bsome\b)',
            r'(\b(union|select)\b.*\bwith\b)',
            r'(\b(union|select)\b.*\bcte\b)',
            r'(\b(union|select)\b.*\bwindow\b)',
            r'(\b(union|select)\b.*\bover\b)',
            r'(\b(union|select)\b.*\bpartition\b\s+by)',
            r'(\b(union|select)\b.*\border\b\s+by)',
            r'(\b(union|select)\b.*\brows\b)',
            r'(\b(union|select)\b.*\brange\b)',
            r'(\b(union|select)\b.*\bpreceding\b)',
            r'(\b(union|select)\b.*\bfollowing\b)',
            r'(\b(union|select)\b.*\bunbounded\b)',
            r'(\b(union|select)\b.*\bcurrent\b\s+row)',
            r'(\b(union|select)\b.*\blag\b)',
            r'(\b(union|select)\b.*\blead\b)',
            r'(\b(union|select)\b.*\bfirst_value\b)',
            r'(\b(union|select)\b.*\blast_value\b)',
            r'(\b(union|select)\b.*\bnth_value\b)',
            r'(\b(union|select)\b.*\bntile\b)',
            r'(\b(union|select)\b.*\bpercent_rank\b)',
            r'(\b(union|select)\b.*\bcume_dist\b)',
            r'(\b(union|select)\b.*\brow_number\b)',
            r'(\b(union|select)\b.*\brank\b)',
            r'(\b(union|select)\b.*\bdense_rank\b)',
        ]
        
        # فحص GET parameters
        for key, value in request.GET.items():
            if self._check_patterns(value, sql_patterns):
                return True
        
        # فحص POST data
        if request.method == 'POST':
            for key, value in request.POST.items():
                if self._check_patterns(value, sql_patterns):
                    return True
        
        return False
    
    def _detect_xss(self, request):
        """كشف XSS"""
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<applet[^>]*>',
            r'<form[^>]*>',
            r'<input[^>]*>',
            r'<textarea[^>]*>',
            r'<select[^>]*>',
            r'<button[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>',
            r'<link[^>]*>',
            r'<base[^>]*>',
            r'<bgsound[^>]*>',
            r'<marquee[^>]*>',
            r'<xmp[^>]*>',
            r'<plaintext[^>]*>',
            r'<listing[^>]*>',
            r'<nobr[^>]*>',
            r'<noframes[^>]*>',
            r'<noscript[^>]*>',
            r'<noembed[^>]*>',
            r'<noframes[^>]*>',
            r'<nolayer[^>]*>',
            r'<ilayer[^>]*>',
            r'<layer[^>]*>',
            r'<keygen[^>]*>',
            r'<isindex[^>]*>',
            r'<dir[^>]*>',
            r'<menu[^>]*>',
            r'<menuitem[^>]*>',
            r'<command[^>]*>',
            r'<details[^>]*>',
            r'<summary[^>]*>',
            r'<dialog[^>]*>',
            r'<datagrid[^>]*>',
            r'<datalist[^>]*>',
            r'<output[^>]*>',
            r'<progress[^>]*>',
            r'<meter[^>]*>',
            r'<time[^>]*>',
            r'<mark[^>]*>',
            r'<ruby[^>]*>',
            r'<rt[^>]*>',
            r'<rp[^>]*>',
            r'<bdi[^>]*>',
            r'<bdo[^>]*>',
            r'<wbr[^>]*>',
            r'<canvas[^>]*>',
            r'<svg[^>]*>',
            r'<math[^>]*>',
            r'<video[^>]*>',
            r'<audio[^>]*>',
            r'<source[^>]*>',
            r'<track[^>]*>',
            r'<map[^>]*>',
            r'<area[^>]*>',
            r'<col[^>]*>',
            r'<colgroup[^>]*>',
            r'<thead[^>]*>',
            r'<tbody[^>]*>',
            r'<tfoot[^>]*>',
            r'<tr[^>]*>',
            r'<td[^>]*>',
            r'<th[^>]*>',
            r'<caption[^>]*>',
            r'<fieldset[^>]*>',
            r'<legend[^>]*>',
            r'<optgroup[^>]*>',
            r'<option[^>]*>',
            r'<datalist[^>]*>',
            r'<output[^>]*>',
            r'<progress[^>]*>',
            r'<meter[^>]*>',
            r'<time[^>]*>',
            r'<mark[^>]*>',
            r'<ruby[^>]*>',
            r'<rt[^>]*>',
            r'<rp[^>]*>',
            r'<bdi[^>]*>',
            r'<bdo[^>]*>',
            r'<wbr[^>]*>',
            r'<canvas[^>]*>',
            r'<svg[^>]*>',
            r'<math[^>]*>',
            r'<video[^>]*>',
            r'<audio[^>]*>',
            r'<source[^>]*>',
            r'<track[^>]*>',
            r'<map[^>]*>',
            r'<area[^>]*>',
            r'<col[^>]*>',
            r'<colgroup[^>]*>',
            r'<thead[^>]*>',
            r'<tbody[^>]*>',
            r'<tfoot[^>]*>',
            r'<tr[^>]*>',
            r'<td[^>]*>',
            r'<th[^>]*>',
            r'<caption[^>]*>',
            r'<fieldset[^>]*>',
            r'<legend[^>]*>',
            r'<optgroup[^>]*>',
            r'<option[^>]*>',
        ]
        
        # فحص GET parameters
        for key, value in request.GET.items():
            if self._check_patterns(value, xss_patterns):
                return True
        
        # فحص POST data
        if request.method == 'POST':
            for key, value in request.POST.items():
                if self._check_patterns(value, xss_patterns):
                    return True
        
        return False
    
    def _check_patterns(self, value, patterns):
        """فحص القيمة ضد الأنماط"""
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        for pattern in patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False


class AuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware للمصادقة المتقدمة
    """
    
    def process_request(self, request):
        # فحص session
        if not self._check_session(request):
            return HttpResponseForbidden("جلسة غير صالحة")
        
        # فحص permissions
        if not self._check_permissions(request):
            return HttpResponseForbidden("ليس لديك صلاحية")
        
        # فحص IP whitelist
        if not self._check_ip_whitelist(request):
            return HttpResponseForbidden("IP غير مسموح")
        
        return None
    
    def _check_session(self, request):
        """فحص صحة الجلسة"""
        if request.user.is_authenticated:
            # فحص آخر نشاط
            last_activity = request.session.get('last_activity')
            if last_activity:
                # فحص إذا انتهت الجلسة (30 دقيقة)
                if time.time() - last_activity > 1800:
                    return False
            
            # تحديث آخر نشاط
            request.session['last_activity'] = time.time()
        
        return True
    
    def _check_permissions(self, request):
        """فحص الصلاحيات"""
        # فحص الصفحات المحمية
        protected_paths = [
            '/admin/',
            '/api/',
            '/settings/',
            '/reports/',
        ]
        
        for path in protected_paths:
            if request.path.startswith(path):
                if not request.user.is_authenticated:
                    return False
                
                # فحص صلاحيات خاصة
                if path == '/admin/' and not request.user.is_staff:
                    return False
        
        return True
    
    def _check_ip_whitelist(self, request):
        """فحص IP whitelist"""
        client_ip = self._get_client_ip(request)
        whitelist = getattr(settings, 'IP_WHITELIST', [])
        
        if whitelist and client_ip not in whitelist:
            return False
        
        return True
    
    def _get_client_ip(self, request):
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LoggingMiddleware(MiddlewareMixin):
    """
    Middleware لتسجيل الأحداث الأمنية
    """
    
    def process_request(self, request):
        # تسجيل الطلب
        self._log_request(request)
        return None
    
    def process_response(self, request, response):
        # تسجيل الاستجابة
        self._log_response(request, response)
        return response
    
    def process_exception(self, request, exception):
        # تسجيل الأخطاء
        self._log_exception(request, exception)
        return None
    
    def _log_request(self, request):
        """تسجيل الطلب"""
        log_data = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'ip': self._get_client_ip(request),
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
        }
        
        logger.info(f"طلب: {log_data}")
    
    def _log_response(self, request, response):
        """تسجيل الاستجابة"""
        log_data = {
            'timestamp': time.time(),
            'status_code': response.status_code,
            'path': request.path,
            'ip': self._get_client_ip(request),
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
        }
        
        logger.info(f"استجابة: {log_data}")
    
    def _log_exception(self, request, exception):
        """تسجيل الأخطاء"""
        log_data = {
            'timestamp': time.time(),
            'exception': str(exception),
            'path': request.path,
            'ip': self._get_client_ip(request),
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
        }
        
        logger.error(f"خطأ: {log_data}")
    
    def _get_client_ip(self, request):
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 