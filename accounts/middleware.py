from django.contrib.auth.models import Permission
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.conf import settings

class RoleBasedPermissionsMiddleware(MiddlewareMixin):
    """
    وسيط للتحقق من صلاحيات المستخدمين بناءً على أدوارهم
    يقوم بتحديث الصلاحيات المخزنة مؤقتاً للمستخدمين الذين تم تسجيل دخولهم
    """
    
    def process_request(self, request):
        if not hasattr(request, 'user') or isinstance(request.user, AnonymousUser):
            return None
            
        user = request.user
        
        # تخزين مؤقت للصلاحيات لتحسين أداء النظام
        cache_key = f"user_permissions_{user.id}"
        cached_permissions = cache.get(cache_key)
        
        if not cached_permissions:
            # الحصول على الصلاحيات المباشرة للمستخدم
            user_permissions = set(user.user_permissions.values_list('codename', flat=True))
            
            # إضافة الصلاحيات من الأدوار المسندة للمستخدم
            try:
                # استخدام حقل user_roles المضاف في نموذج المستخدم
                if hasattr(user, 'user_roles'):
                    # تجميع الصلاحيات من كل الأدوار المسندة للمستخدم
                    for user_role in user.user_roles.select_related('role').all():
                        role_permissions = user_role.role.permissions.values_list('codename', flat=True)
                        user_permissions.update(set(role_permissions))
            except Exception:
                pass
            
            # حفظ الصلاحيات في التخزين المؤقت
            cache_timeout = getattr(settings, 'PERMISSIONS_CACHE_TIMEOUT', 3600)  # ساعة واحدة افتراضياً
            cache.set(cache_key, user_permissions, cache_timeout)
            
            # تعيين الصلاحيات للمستخدم في الطلب الحالي
            setattr(request, '_cached_user_permissions', user_permissions)
        else:
            # استخدام الصلاحيات المخزنة مسبقاً
            setattr(request, '_cached_user_permissions', cached_permissions)
        
        return None
    
    @staticmethod
    def clear_user_permissions_cache(user_id):
        """مسح التخزين المؤقت لصلاحيات المستخدم"""
        cache_key = f"user_permissions_{user_id}"
        cache.delete(cache_key)