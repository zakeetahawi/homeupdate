"""
Middleware لتتبع جلسات المستخدمين
"""

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from .models import OnlineUser, UserSession


class UserSessionTrackingMiddleware(MiddlewareMixin):
    """
    Middleware لتتبع وتحديث جلسات المستخدمين النشطين
    """

    def process_request(self, request):
        """معالجة الطلب وتحديث معلومات الجلسة"""
        if request.user and request.user.is_authenticated:
            session_key = request.session.session_key

            if session_key:
                # تحديث أو إنشاء UserSession
                user_session, created = UserSession.objects.update_or_create(
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

        return None

    @staticmethod
    def get_client_ip(request):
        """الحصول على IP الحقيقي للمستخدم"""
        # دعم Cloudflare
        x_forwarded_for = request.META.get("HTTP_CF_CONNECTING_IP")
        if x_forwarded_for:
            return x_forwarded_for

        # دعم Proxy عادي
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "0.0.0.0")

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
