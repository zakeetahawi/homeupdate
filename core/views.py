"""
Views للأمان
"""

from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token


@requires_csrf_token
def csrf_failure(request, reason=""):
    """
    صفحة خطأ CSRF مخصصة
    """
    context = {
        'reason': reason,
        'no_referer': reason == "Referer checking failed - no Referer.",
        'no_csrf_cookie': reason == "CSRF cookie not set.",
        'bad_token': "CSRF token" in reason,
    }
    
    return render(request, 'core/csrf_error.html', context, status=403)


def security_error(request):
    """
    صفحة خطأ أمني عامة
    """
    return render(request, 'core/security_error.html', status=403)
