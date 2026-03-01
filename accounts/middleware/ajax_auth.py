"""
معترض AJAX للمصادقة
عند انتهاء الجلسة، يُعيد JSON 401 لطلبات AJAX بدل توجيه HTML
"""
import json

from django.http import JsonResponse


class AjaxAuthMiddleware:
    """
    يعترض طلبات AJAX للمستخدمين غير المصادق عليهم
    ويُعيد JSON 401 بدل الـ redirect لصفحة HTML لتسجيل الدخول.

    يُكتشف طلب AJAX إذا توفر أحد:
      - X-Requested-With: XMLHttpRequest
      - X-CSRFToken header
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # نتحقق بعد المعالجة: إذا كان الرد redirect (302) إلى صفحة login
        # وكان الطلب AJAX → نُعيد JSON 401
        if (
            response.status_code == 302
            and self._is_ajax_request(request)
            and self._is_login_redirect(response)
        ):
            return JsonResponse(
                {
                    "success": False,
                    "session_expired": True,
                    "message": "انتهت الجلسة. يرجى تسجيل الدخول مجدداً.",
                    "login_url": "/accounts/login/?next="
                    + request.path,
                },
                status=401,
            )

        return response

    @staticmethod
    def _is_ajax_request(request):
        return bool(
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.headers.get("X-CSRFToken")
        )

    @staticmethod
    def _is_login_redirect(response):
        location = response.get("Location", "")
        return "login" in location or "accounts/login" in location
