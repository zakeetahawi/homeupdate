"""
تحسينات الأداء لصفحات إدارة الشكاوى
"""
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.core.cache import cache
from functools import wraps


def cache_admin_method(timeout=300):
    """Decorator لتخزين نتائج دوال الإدارة مؤقتاً"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, obj):
            if not obj or not obj.pk:
                return func(self, obj)
            
            cache_key = f"admin_{self.__class__.__name__}_{func.__name__}_{obj.pk}"
            result = cache.get(cache_key)
            
            if result is None:
                result = func(self, obj)
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


class OptimizedComplaintAdminMixin:
    """Mixin لتحسين أداء إدارة الشكاوى"""
    
    def get_queryset(self, request):
        """تحسين الاستعلامات الأساسية"""
        queryset = super().get_queryset(request)
        
        # تحسين العلاقات الأساسية
        if hasattr(self.model, 'customer'):
            queryset = queryset.select_related('customer')
        if hasattr(self.model, 'complaint_type'):
            queryset = queryset.select_related('complaint_type')
        if hasattr(self.model, 'assigned_to'):
            queryset = queryset.select_related('assigned_to')
        if hasattr(self.model, 'created_by'):
            queryset = queryset.select_related('created_by')
        
        return queryset
    
    def get_list_display(self, request):
        """تحسين عرض القائمة بناءً على الصلاحيات"""
        list_display = super().get_list_display(request)
        
        # إخفاء بعض الأعمدة للمستخدمين العاديين لتحسين الأداء
        user = request.user
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Complaints_Managers', 'Complaints_Supervisors']).exists()):
            # إزالة الأعمدة المعقدة للمستخدمين العاديين
            simplified_display = []
            for field in list_display:
                if field not in ['is_overdue_display', 'time_remaining_display', 'resolution_time_display']:
                    simplified_display.append(field)
            return simplified_display
        
        return list_display
    
    def get_list_filter(self, request):
        """تحسين الفلاتر بناءً على الصلاحيات"""
        list_filter = super().get_list_filter(request)
        
        user = request.user
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Complaints_Managers', 'Complaints_Supervisors']).exists()):
            # فلاتر مبسطة للمستخدمين العاديين
            return ['status', 'priority', 'created_at']
        
        return list_filter


class OptimizedInlineMixin:
    """Mixin لتحسين أداء الـ Inlines"""
    
    def get_queryset(self, request):
        """تحسين استعلامات الـ Inline"""
        queryset = super().get_queryset(request)
        
        # تحديد عدد السجلات المعروضة
        if hasattr(self, 'max_display_count'):
            queryset = queryset[:self.max_display_count]
        
        # تحسين العلاقات
        if hasattr(self.model, 'created_by'):
            queryset = queryset.select_related('created_by')
        if hasattr(self.model, 'uploaded_by'):
            queryset = queryset.select_related('uploaded_by')
        
        return queryset.order_by('-id')  # أحدث السجلات أولاً


def optimize_complaint_admin():
    """تطبيق تحسينات الأداء على إدارة الشكاوى"""
    from .admin import ComplaintAdmin, ComplaintUpdateInline, ComplaintAttachmentInline
    
    # إضافة Mixins للتحسين
    class OptimizedComplaintAdmin(OptimizedComplaintAdminMixin, ComplaintAdmin):
        pass
    
    class OptimizedComplaintUpdateInline(OptimizedInlineMixin, ComplaintUpdateInline):
        max_display_count = 5  # عرض آخر 5 تحديثات فقط
    
    class OptimizedComplaintAttachmentInline(OptimizedInlineMixin, ComplaintAttachmentInline):
        max_display_count = 3  # عرض آخر 3 مرفقات فقط
    
    # استبدال الـ inlines
    OptimizedComplaintAdmin.inlines = [
        OptimizedComplaintUpdateInline,
        OptimizedComplaintAttachmentInline
    ]
    
    return OptimizedComplaintAdmin


# تحسينات إضافية للعرض
def get_cached_customer_name(complaint):
    """جلب اسم العميل مع التخزين المؤقت"""
    cache_key = f"customer_name_{complaint.customer_id}"
    name = cache.get(cache_key)
    
    if name is None:
        name = complaint.customer.name
        cache.set(cache_key, name, 3600)  # ساعة واحدة
    
    return name


def get_cached_status_display(complaint):
    """عرض الحالة مع التخزين المؤقت"""
    cache_key = f"status_display_{complaint.status}"
    display = cache.get(cache_key)
    
    if display is None:
        display = format_html(
            '<span class="badge {}">{}</span>',
            complaint.get_status_badge_class().replace('bg-', 'badge-'),
            complaint.get_status_display()
        )
        cache.set(cache_key, display, 1800)  # 30 دقيقة
    
    return display


def get_cached_priority_display(complaint):
    """عرض الأولوية مع التخزين المؤقت"""
    cache_key = f"priority_display_{complaint.priority}"
    display = cache.get(cache_key)
    
    if display is None:
        display = format_html(
            '<span class="badge {}">{}</span>',
            complaint.get_priority_badge_class().replace('bg-', 'badge-'),
            complaint.get_priority_display()
        )
        cache.set(cache_key, display, 1800)  # 30 دقيقة
    
    return display


# إعدادات التخزين المؤقت للإدارة
ADMIN_CACHE_SETTINGS = {
    'complaint_list_timeout': 300,  # 5 دقائق
    'complaint_detail_timeout': 600,  # 10 دقائق
    'user_permissions_timeout': 1800,  # 30 دقيقة
    'status_choices_timeout': 3600,  # ساعة واحدة
}


def clear_complaint_cache(complaint_id=None):
    """مسح التخزين المؤقت للشكاوى"""
    if complaint_id:
        # مسح cache لشكوى محددة
        cache_keys = [
            f"customer_name_{complaint_id}",
            f"status_display_{complaint_id}",
            f"priority_display_{complaint_id}",
        ]
        cache.delete_many(cache_keys)
    else:
        # مسح جميع cache الشكاوى
        cache.clear()


def get_user_complaint_permissions(user):
    """جلب صلاحيات المستخدم مع التخزين المؤقت"""
    cache_key = f"user_permissions_{user.id}"
    permissions = cache.get(cache_key)
    
    if permissions is None:
        try:
            perm_obj = user.complaint_permissions
            permissions = {
                'can_edit_all': perm_obj.can_edit_all_complaints,
                'can_view_all': perm_obj.can_view_all_complaints,
                'can_assign': perm_obj.can_assign_complaints,
                'can_escalate': perm_obj.can_escalate_complaints,
                'can_resolve': perm_obj.can_resolve_complaints,
                'can_close': perm_obj.can_close_complaints,
                'can_delete': perm_obj.can_delete_complaints,
                'is_active': perm_obj.is_active,
            }
        except:
            permissions = {
                'can_edit_all': False,
                'can_view_all': False,
                'can_assign': False,
                'can_escalate': False,
                'can_resolve': False,
                'can_close': False,
                'can_delete': False,
                'is_active': False,
            }
        
        cache.set(cache_key, permissions, ADMIN_CACHE_SETTINGS['user_permissions_timeout'])
    
    return permissions


def is_user_admin(user):
    """فحص ما إذا كان المستخدم مدير مع التخزين المؤقت"""
    cache_key = f"user_is_admin_{user.id}"
    is_admin = cache.get(cache_key)
    
    if is_admin is None:
        is_admin = (
            user.is_superuser or
            user.groups.filter(name__in=[
                'Complaints_Managers', 
                'Complaints_Supervisors', 
                'Managers'
            ]).exists()
        )
        cache.set(cache_key, is_admin, ADMIN_CACHE_SETTINGS['user_permissions_timeout'])
    
    return is_admin


# تطبيق التحسينات تلقائياً عند استيراد الملف
def apply_performance_optimizations():
    """تطبيق جميع تحسينات الأداء"""
    try:
        # يمكن إضافة المزيد من التحسينات هنا
        pass
    except Exception as e:
        print(f"خطأ في تطبيق تحسينات الأداء: {e}")


# تطبيق التحسينات عند استيراد الملف
apply_performance_optimizations()
