"""
⚠️  تحذير أمني: هذا الملف معطّل ولا يجب استخدامه في الإنتاج!
Middleware للتحقق من وجود مستخدم افتراضي — محذوف لأسباب أمنية
استخدم بدلاً من ذلك: python manage.py createsuperuser
"""

import warnings


class DefaultUserMiddleware:
    """
    ⛔ هذا الـ Middleware معطّل لأسباب أمنية.
    كان يُنشئ مستخدم admin/admin123 تلقائياً — وهو خطر أمني كبير.
    استخدم بدلاً من ذلك: python manage.py createsuperuser
    """

    def __init__(self, get_response):
        warnings.warn(
            "⛔ DefaultUserMiddleware is DISABLED for security. "
            "Use 'python manage.py createsuperuser' instead.",
            SecurityWarning,
            stacklevel=2,
        )
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
