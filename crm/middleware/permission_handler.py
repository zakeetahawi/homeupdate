"""
وسيط لمعالجة أخطاء الصلاحيات بشكل موحد في النظام
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse


class PermissionDeniedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):

            # معالجة طلبات AJAX بشكل خاص
            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                'application/json' in request.headers.get('Accept', '') or
                request.path.startswith('/api/') or
                'status' in request.path or 'progress' in request.path
            )

            if is_ajax:
                message = (
                    'عذراً، ليس لديك الصلاحيات '
                    'الكافية للقيام بهذا الإجراء'
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Permission Denied',
                    'message': message
                }, status=403)

            error_message = (
                'عذراً، ليس لديك الصلاحيات '
                'الكافية للقيام بهذا الإجراء'
            )
            messages.error(request, error_message)
            # Get the previous URL from the session
            previous_url = request.META.get('HTTP_REFERER')
            if previous_url:
                return redirect(previous_url)
            return redirect('home')
        return None
