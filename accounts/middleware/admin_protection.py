"""
حماية لوحة الإدارة: تقييد الوصول إلى /admin/ بناءً على قائمة IPs المسموح بها.
SEC-001: بوتات تحاول اختراق /admin/login/ عبر هجمات CSRF

إذا لم يتم تعريف ADMIN_ALLOWED_IPS في settings.py (أو كانت قائمة فارغة)،
تُسمح جميع الطلبات (لا تغيير في السلوك).

إضافة IPs مسموح بها في settings.py:
    ADMIN_ALLOWED_IPS = ["203.0.113.1", "198.51.100.0/24"]
"""

import ipaddress
import logging

from django.conf import settings
from django.http import Http404

logger = logging.getLogger(__name__)


def _get_real_ip(request):
    """
    الحصول على الـ IP الحقيقي للعميل من الـ headers.
    Cloudflare Tunnel يضع الـ IP الأصلي في CF-Connecting-IP أو X-Forwarded-For.
    """
    # Cloudflare Tunnel: CF-Connecting-IP هو الأموثق
    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
    if cf_ip:
        return cf_ip.strip()

    # بديل: X-Forwarded-For (أول IP في القائمة هو الأصلي)
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # احتياطي: REMOTE_ADDR
    return request.META.get("REMOTE_ADDR", "")


def _is_ip_allowed(ip_str, allowed_list):
    """
    التحقق مما إذا كان الـ IP في قائمة المسموح بهم.
    يدعم عناوين IP المنفردة وأنظمة CIDR (مثل 192.168.1.0/24).
    """
    try:
        client_ip = ipaddress.ip_address(ip_str)
    except ValueError:
        logger.warning(f"IP غير صالح: {ip_str}")
        return False

    for entry in allowed_list:
        entry = entry.strip()
        try:
            if "/" in entry:
                # نطاق CIDR
                if client_ip in ipaddress.ip_network(entry, strict=False):
                    return True
            else:
                # IP منفرد
                if client_ip == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            logger.warning(f"إدخال IP غير صالح في ADMIN_ALLOWED_IPS: {entry}")
            continue

    return False


class AdminIPRestrictionMiddleware:
    """
    Middleware لتقييد الوصول إلى /admin/ بناءً على قائمة IPs المسموح بها.
    إذا كانت ADMIN_ALLOWED_IPS فارغة أو غير موجودة: يُسمح بكل الطلبات.
    إذا كانت محددة: يُرفض الوصول من IPs غير واردة فيها بإرجاع 404.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # قراءة القائمة من الإعدادات مرة واحدة عند بدء التشغيل
        self.allowed_ips = getattr(settings, "ADMIN_ALLOWED_IPS", [])

    def __call__(self, request):
        # تطبيق الفحص فقط على مسارات /admin/
        if request.path.startswith("/admin/") and self.allowed_ips:
            client_ip = _get_real_ip(request)

            if not _is_ip_allowed(client_ip, self.allowed_ips):
                logger.warning(
                    f"SEC-001: محاولة وصول للوحة الإدارة من IP غير مصرح: {client_ip} "
                    f"| المسار: {request.path} | الطريقة: {request.method}"
                )
                # إرجاع 404 بدلاً من 403 لإخفاء وجود لوحة الإدارة
                raise Http404

        return self.get_response(request)
