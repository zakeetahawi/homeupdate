"""
Decorators مخصصة للمشروع
"""

from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def ajax_login_required(view_func):
    """
    Decorator للـ AJAX requests التي تتطلب authentication
    يرجع JSON error بدلاً من redirect للـ AJAX requests
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # إذا كان الطلب AJAX، أرجع JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required',
                    'message': 'يجب تسجيل الدخول للوصول إلى هذه الخدمة',
                    'redirect': '/accounts/login/'
                }, status=401)
            else:
                # للطلبات العادية، استخدم السلوك الافتراضي
                return redirect('accounts:login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def api_login_required(view_func):
    """
    Decorator للـ API endpoints
    يرجع JSON error دائماً
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required',
                'message': 'يجب تسجيل الدخول للوصول إلى هذه الخدمة'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
