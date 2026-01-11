"""
Middleware لتتبع المستخدم الحالي في thread local storage
"""

import threading

from django.utils.deprecation import MiddlewareMixin

# Thread local storage لتخزين المستخدم الحالي
_thread_locals = threading.local()


def get_current_user():
    """الحصول على المستخدم الحالي من thread local storage"""
    return getattr(_thread_locals, "user", None)


def get_current_request():
    """الحصول على الطلب الحالي من thread local storage"""
    return getattr(_thread_locals, "request", None)


class CurrentUserMiddleware(MiddlewareMixin):
    """
    Middleware لتخزين المستخدم الحالي في thread local storage
    يساعد في تتبع المستخدم في الإشارات والعمليات التلقائية
    """

    def process_request(self, request):
        """تخزين المستخدم والطلب الحالي في thread local storage"""
        _thread_locals.user = getattr(request, "user", None)
        _thread_locals.request = request

    def process_response(self, request, response):
        """تنظيف thread local storage بعد انتهاء الطلب"""
        if hasattr(_thread_locals, "user"):
            delattr(_thread_locals, "user")
        if hasattr(_thread_locals, "request"):
            delattr(_thread_locals, "request")
        return response

    def process_exception(self, request, exception):
        """تنظيف thread local storage في حالة حدوث خطأ"""
        if hasattr(_thread_locals, "user"):
            delattr(_thread_locals, "user")
        if hasattr(_thread_locals, "request"):
            delattr(_thread_locals, "request")
        return None
