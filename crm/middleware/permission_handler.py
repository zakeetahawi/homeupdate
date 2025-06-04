"""
وسيط لمعالجة أخطاء الصلاحيات بشكل موحد في النظام
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.urls import reverse

class PermissionDeniedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            messages.error(request, 'عذراً، ليس لديك الصلاحيات الكافية للقيام بهذا الإجراء')
            # Get the previous URL from the session
            previous_url = request.META.get('HTTP_REFERER')
            if previous_url:
                return redirect(previous_url)
            return redirect('home')
        return None
