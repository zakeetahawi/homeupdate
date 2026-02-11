"""
أدوات مساعدة لتتبع نشاط المستخدمين
"""


def get_client_ip_from_request(request):
    """
    الحصول على IP الحقيقي للمستخدم
    يدعم Cloudflare Tunnel و Proxy العادي

    الترتيب:
    1. CF-Connecting-IP (Cloudflare Tunnel - IP الحقيقي)
    2. X-Forwarded-For (Proxy عادي - أول IP)
    3. X-Real-IP (Nginx proxy)
    4. REMOTE_ADDR (اتصال مباشر)

    يُستخدم من django-axes لتسجيل IP الحقيقي في سجلات المحاولات الفاشلة
    """
    # Cloudflare Tunnel - الأدق
    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
    if cf_ip:
        return cf_ip.strip()

    # Proxy عادي
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    # Nginx proxy
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()

    # اتصال مباشر
    return request.META.get("REMOTE_ADDR", "0.0.0.0")
