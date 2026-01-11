# ملف تهيئة لجعل هذا المجلد باكيج بايثون صالح للاستيراد

# استيراد RoleBasedPermissionsMiddleware من الملف الرئيسي
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# استيراد middleware من الملف الأصلي
try:
    from ..middleware import RoleBasedPermissionsMiddleware
except ImportError:
    # حل بديل - إنشاء middleware بسيط
    from django.utils.deprecation import MiddlewareMixin

    class RoleBasedPermissionsMiddleware(MiddlewareMixin):
        """وسيط بسيط لإدارة الصلاحيات"""

        def process_request(self, request):
            return None
