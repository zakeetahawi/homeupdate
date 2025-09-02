"""
معالجات خاصة لأخطاء CSRF
"""

from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token
from django.http import HttpResponseForbidden
import logging

logger = logging.getLogger(__name__)


@requires_csrf_token
def csrf_failure(request, reason=""):
    """
    معالج مخصص لأخطاء CSRF
    """
    
    # تسجيل الخطأ للمراقبة
    logger.warning(f"CSRF failure for user {request.user} from IP {request.META.get('REMOTE_ADDR')}: {reason}")
    
    # معلومات إضافية للتشخيص
    context = {
        'reason': reason,
        'user_agent': request.META.get('HTTP_USER_AGENT', 'غير معروف'),
        'referer': request.META.get('HTTP_REFERER', 'غير معروف'),
        'method': request.method,
        'path': request.path,
        'is_ajax': request.headers.get('X-Requested-With') == 'XMLHttpRequest',
        'has_csrf_cookie': 'csrftoken' in request.COOKIES,
        'csrf_cookie_value': request.COOKIES.get('csrftoken', 'غير موجود')[:10] + '...' if 'csrftoken' in request.COOKIES else 'غير موجود',
    }
    
    # إذا كان طلب AJAX، إرجاع JSON
    if context['is_ajax']:
        from django.http import JsonResponse
        return JsonResponse({
            'error': 'CSRF verification failed',
            'message': 'انتهت صلاحية رمز الحماية. يرجى إعادة تحميل الصفحة.',
            'code': 'CSRF_FAILURE',
            'reload_required': True
        }, status=403)
    
    # إرجاع صفحة HTML مخصصة
    return HttpResponseForbidden(
        render(request, '403_csrf.html', context).content
    )


def get_csrf_token_view(request):
    """
    API endpoint لجلب CSRF token جديد
    """
    from django.middleware.csrf import get_token
    from django.http import JsonResponse
    
    token = get_token(request)
    
    return JsonResponse({
        'csrf_token': token,
        'status': 'success',
        'message': 'تم إنشاء رمز حماية جديد'
    })


def csrf_debug_view(request):
    """
    صفحة تشخيص مشاكل CSRF (للتطوير فقط)
    """
    from django.conf import settings
    from django.http import JsonResponse
    
    if not settings.DEBUG:
        return JsonResponse({'error': 'هذه الصفحة متاحة في وضع التطوير فقط'}, status=404)
    
    debug_info = {
        'csrf_settings': {
            'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', None),
            'CSRF_COOKIE_HTTPONLY': getattr(settings, 'CSRF_COOKIE_HTTPONLY', None),
            'CSRF_COOKIE_SAMESITE': getattr(settings, 'CSRF_COOKIE_SAMESITE', None),
            'CSRF_TRUSTED_ORIGINS': getattr(settings, 'CSRF_TRUSTED_ORIGINS', []),
            'CSRF_USE_SESSIONS': getattr(settings, 'CSRF_USE_SESSIONS', None),
        },
        'request_info': {
            'method': request.method,
            'path': request.path,
            'is_secure': request.is_secure(),
            'host': request.get_host(),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'remote_addr': request.META.get('REMOTE_ADDR', ''),
        },
        'csrf_info': {
            'has_csrf_cookie': 'csrftoken' in request.COOKIES,
            'csrf_cookie_value': request.COOKIES.get('csrftoken', 'غير موجود')[:20] + '...' if 'csrftoken' in request.COOKIES else 'غير موجود',
            'csrf_header': request.META.get('HTTP_X_CSRFTOKEN', 'غير موجود')[:20] + '...' if request.META.get('HTTP_X_CSRFTOKEN') else 'غير موجود',
        },
        'session_info': {
            'session_key': request.session.session_key,
            'session_exists': request.session.exists(request.session.session_key) if request.session.session_key else False,
            'is_authenticated': request.user.is_authenticated,
            'user': str(request.user) if request.user.is_authenticated else 'غير مسجل دخول',
        }
    }
    
    return JsonResponse(debug_info, json_dumps_params={'ensure_ascii': False, 'indent': 2})


def test_csrf_view(request):
    """
    صفحة اختبار CSRF (للتطوير فقط)
    """
    from django.conf import settings
    
    if not settings.DEBUG:
        from django.http import Http404
        raise Http404("هذه الصفحة متاحة في وضع التطوير فقط")
    
    if request.method == 'POST':
        from django.http import JsonResponse
        return JsonResponse({
            'status': 'success',
            'message': 'تم إرسال النموذج بنجاح! CSRF يعمل بشكل صحيح.',
            'data': dict(request.POST)
        })
    
    # إرجاع نموذج اختبار
    from django.template.response import TemplateResponse
    
    test_form_html = """
    {% load static %}
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>اختبار CSRF</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h4>اختبار CSRF Token</h4>
                        </div>
                        <div class="card-body">
                            <form method="post" id="csrf-test-form">
                                {% csrf_token %}
                                <div class="mb-3">
                                    <label class="form-label">رسالة اختبار:</label>
                                    <input type="text" name="test_message" class="form-control" value="اختبار CSRF" required>
                                </div>
                                <button type="submit" class="btn btn-primary">إرسال الاختبار</button>
                            </form>
                            
                            <hr>
                            
                            <div class="mt-3">
                                <h6>معلومات CSRF:</h6>
                                <p><strong>CSRF Token:</strong> <code>{{ csrf_token }}</code></p>
                                <p><strong>Cookie موجود:</strong> <span id="csrf-cookie-status"></span></p>
                            </div>
                            
                            <div class="mt-3">
                                <a href="/csrf-debug/" class="btn btn-info btn-sm">معلومات التشخيص</a>
                                <a href="/" class="btn btn-secondary btn-sm">العودة للرئيسية</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // فحص وجود CSRF cookie
            document.addEventListener('DOMContentLoaded', function() {
                const hasCsrfCookie = document.cookie.includes('csrftoken');
                document.getElementById('csrf-cookie-status').textContent = hasCsrfCookie ? 'نعم ✅' : 'لا ❌';
                
                // معالج النموذج
                document.getElementById('csrf-test-form').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    
                    fetch(window.location.href, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        alert('النتيجة: ' + data.message);
                    })
                    .catch(error => {
                        alert('خطأ: ' + error.message);
                    });
                });
            });
        </script>
    </body>
    </html>
    """
    
    return TemplateResponse(request, 'string:' + test_form_html, {})
