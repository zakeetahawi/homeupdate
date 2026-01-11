"""
Middleware لتتبع المستخدم الحالي في التطبيق
"""

import threading

# متغير thread-local لحفظ المستخدم الحالي
_user = threading.local()


class CurrentUserMiddleware:
    """
    Middleware لحفظ المستخدم الحالي في thread-local storage
    بحيث يمكن الوصول إليه من أي مكان في التطبيق
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # حفظ المستخدم الحالي
        _user.value = getattr(request, "user", None)

        response = self.get_response(request)

        # تنظيف المستخدم بعد انتهاء الطلب
        if hasattr(_user, "value"):
            del _user.value

        return response


def get_current_user():
    """
    الحصول على المستخدم الحالي من thread-local storage

    Returns:
        User: المستخدم الحالي أو None
    """
    return getattr(_user, "value", None)


def set_current_user(user):
    """
    تعيين المستخدم الحالي في thread-local storage

    Args:
        user: المستخدم المراد تعيينه
    """
    _user.value = user
