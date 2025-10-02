"""
Middleware لإضافة دعم تلقائي لروابط Cloudflare إلى ALLOWED_HOSTS
"""

import re

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseBadRequest


class CloudflareHostsMiddleware:
    """
    Middleware يضيف تلقائياً أي رابط Cloudflare إلى ALLOWED_HOSTS
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # قائمة بالنطاقات المسموحة تلقائياً
        self.auto_allowed_patterns = [
            r".*\.trycloudflare\.com$",
            r".*\.cloudflare\.com$",
            r".*\.cfargotunnel\.com$",
            r".*\.ngrok\.io$",
            r".*\.ngrok-free\.app$",
            r".*\.railway\.app$",
            r".*\.up\.railway\.app$",
            r".*\.vercel\.app$",
            r".*\.herokuapp\.com$",
            r".*\.onrender\.com$",
            r".*\.pythonanywhere\.com$",
        ]

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except DisallowedHost as e:
            # استخراج اسم المضيف من الخطأ
            host = self._extract_host_from_error(str(e))

            if host and self._is_auto_allowed_host(host):
                # إضافة المضيف إلى ALLOWED_HOSTS
                if host not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(host)
                    print(f"✅ تم إضافة المضيف تلقائياً: {host}")

                # إعادة معالجة الطلب
                try:
                    response = self.get_response(request)
                    return response
                except Exception as retry_error:
                    print(f"❌ فشل في إعادة المعالجة: {retry_error}")
                    return HttpResponseBadRequest(f"خطأ في معالجة الطلب: {retry_error}")
            else:
                # المضيف غير مسموح
                print(f"❌ مضيف غير مسموح: {host}")
                return HttpResponseBadRequest(f"مضيف غير مسموح: {host}")

    def _extract_host_from_error(self, error_message):
        """استخراج اسم المضيف من رسالة الخطأ"""
        try:
            # البحث عن النمط: 'host_name'
            match = re.search(r"'([^']+)'", error_message)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None

    def _is_auto_allowed_host(self, host):
        """فحص ما إذا كان المضيف مسموحاً تلقائياً"""
        for pattern in self.auto_allowed_patterns:
            if re.match(pattern, host, re.IGNORECASE):
                return True
        return False


class DynamicAllowedHostsMiddleware:
    """
    Middleware بديل يسمح بجميع المضيفين في وضع التطوير
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # في وضع التطوير، السماح لجميع المضيفين
        if settings.DEBUG:
            original_allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
            if "*" not in original_allowed_hosts:
                # إضافة مؤقتة للمضيف الحالي
                host = request.get_host()
                if host and host not in original_allowed_hosts:
                    settings.ALLOWED_HOSTS = original_allowed_hosts + [host]
                    print(f"🔧 إضافة مؤقتة للمضيف: {host}")

        response = self.get_response(request)
        return response
