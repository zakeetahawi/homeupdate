"""
Middleware لتتبع جلسات المستخدمين
"""

from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from .models import OnlineUser, UserSession

# Throttle interval in seconds — only write to DB once per this interval per session
SESSION_TRACKING_THROTTLE = 60


class UserSessionTrackingMiddleware(MiddlewareMixin):
    """
    Middleware لتتبع وتحديث جلسات المستخدمين النشطين
    محسّن: يكتب في قاعدة البيانات مرة واحدة كل 60 ثانية بدلاً من كل request
    """

    # المسارات التي لا تحتاج تتبع (AJAX, API, static)
    SKIP_PATHS = ('/api/', '/static/', '/media/', '/favicon.ico', '/__debug__/')

    def process_request(self, request):
        """معالجة الطلب وتحديث معلومات الجلسة"""
        if not (request.user and request.user.is_authenticated):
            return None

        # تخطي مسارات AJAX و API و static
        path = request.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return None

        session_key = request.session.session_key
        if not session_key:
            return None

        # Throttle: فقط كتابة في DB مرة كل 60 ثانية لكل جلسة
        cache_key = f"session_track_{session_key}"
        if cache.get(cache_key):
            return None

        # تحديث أو إنشاء UserSession
        UserSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                "user": request.user,
                "ip_address": self.get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
                "last_activity": timezone.now(),
                "is_active": True,
                "device_type": self.get_device_type(request),
                "browser": self.get_browser(request),
                "operating_system": self.get_os(request),
            },
        )

        # تحديث OnlineUser
        OnlineUser.update_user_activity(request.user, request)

        # تعيين الـ throttle cache
        cache.set(cache_key, True, timeout=SESSION_TRACKING_THROTTLE)

        return None

    @staticmethod
    def get_client_ip(request):
        """الحصول على IP الحقيقي للمستخدم — يستخدم الدالة المركزية"""
        from user_activity.utils import get_client_ip_from_request
        return get_client_ip_from_request(request)

    @staticmethod
    def get_device_type(request):
        """تحديد نوع الجهاز"""
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
            return "mobile"
        elif "tablet" in user_agent or "ipad" in user_agent:
            return "tablet"
        elif "windows" in user_agent or "mac" in user_agent or "linux" in user_agent:
            return "desktop"

        return "unknown"

    @staticmethod
    def get_browser(request):
        """تحديد نوع المتصفح"""
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        if "edg" in user_agent or "edge" in user_agent:
            return "Edge"
        elif "chrome" in user_agent:
            return "Chrome"
        elif "firefox" in user_agent:
            return "Firefox"
        elif "safari" in user_agent:
            return "Safari"
        elif "opera" in user_agent or "opr" in user_agent:
            return "Opera"

        return "Unknown"

    @staticmethod
    def get_os(request):
        """تحديد نظام التشغيل"""
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

        if "windows" in user_agent:
            return "Windows"
        elif "mac" in user_agent:
            return "macOS"
        elif "linux" in user_agent:
            return "Linux"
        elif "android" in user_agent:
            return "Android"
        elif "iphone" in user_agent or "ipad" in user_agent:
            return "iOS"

        return "Unknown"
