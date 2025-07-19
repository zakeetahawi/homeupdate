from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import ManufacturingOrder


@admin.register(ManufacturingOrder)
class FactoryManufacturingOrderAdmin(admin.ModelAdmin):
    """إدارة طلبات التصنيع في المصنع"""
    
    list_display = [
        'order_number', 
        'status_display', 
        'start_date', 
        'completion_date', 
        'duration_display',
        'is_completed'
    ]
    
    list_filter = [
        'status', 
        'start_date', 
        'completion_date'
    ]
    
    search_fields = [
        'order_number', 
        'description'
    ]
    
    readonly_fields = [
        'start_date', 
        'completion_date', 
        'duration_display'
    ]
    
    date_hierarchy = 'start_date'
    
    fieldsets = (
        (_('معلومات الطلب'), {
            'fields': ('order_number', 'description', 'status')
        }),
        (_('التواريخ'), {
            'fields': ('start_date', 'completion_date', 'duration_display')
        }),
    )
    
    actions = [
        'mark_as_completed',
        'mark_as_in_progress',
        'mark_as_pending',
        'mark_as_cancelled'
    ]
    
    def status_display(self, obj):
        """عرض الحالة مع الألوان"""
        colors = {
            'pending': '#ffc107',      # أصفر
            'in_progress': '#007bff',  # أزرق
            'completed': '#28a745',    # أخضر
            'cancelled': '#dc3545',    # أحمر
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = _('الحالة')
    status_display.admin_order_field = 'status'
    
    def duration_display(self, obj):
        """عرض مدة التنفيذ"""
        if obj.completion_date and obj.start_date:
            duration = obj.completion_date - obj.start_date
            days = duration.days
            hours = duration.seconds // 3600
            if days > 0:
                return f"{days} يوم"
            elif hours > 0:
                return f"{hours} ساعة"
            else:
                return "أقل من ساعة"
        return "لم ينته بعد"
    duration_display.short_description = _('مدة التنفيذ')
    
    def is_completed(self, obj):
        """عرض ما إذا كان الطلب مكتملاً"""
        return obj.status == 'completed'
    is_completed.boolean = True
    is_completed.short_description = _('مكتمل')
    
    def mark_as_completed(self, request, queryset):
        """تحديد الطلبات كمكتملة"""
        from django.utils import timezone
        updated = queryset.update(
            status='completed',
            completion_date=timezone.now()
        )
        self.message_user(
            request, 
            f'تم تحديث {updated} طلب كمكتمل بنجاح'
        )
    mark_as_completed.short_description = _('تحديد كمكتمل')
    
    def mark_as_in_progress(self, request, queryset):
        """تحديد الطلبات قيد التنفيذ"""
        updated = queryset.update(status='in_progress')
        self.message_user(
            request, 
            f'تم تحديث {updated} طلب قيد التنفيذ بنجاح'
        )
    mark_as_in_progress.short_description = _('تحديد قيد التنفيذ')
    
    def mark_as_pending(self, request, queryset):
        """تحديد الطلبات قيد الانتظار"""
        updated = queryset.update(status='pending')
        self.message_user(
            request, 
            f'تم تحديث {updated} طلب قيد الانتظار بنجاح'
        )
    mark_as_pending.short_description = _('تحديد قيد الانتظار')
    
    def mark_as_cancelled(self, request, queryset):
        """تحديد الطلبات كملغية"""
        updated = queryset.update(status='cancelled')
        self.message_user(
            request, 
            f'تم تحديث {updated} طلب كملغي بنجاح'
        )
    mark_as_cancelled.short_description = _('تحديد كملغي')
    
    def has_add_permission(self, request):
        """السماح بإضافة طلبات جديدة"""
        return request.user.is_staff
    
    def has_change_permission(self, request, obj=None):
        """السماح بتعديل الطلبات"""
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """السماح بحذف الطلبات"""
        return request.user.is_staff
    
    def has_view_permission(self, request, obj=None):
        """السماح بعرض الطلبات"""
        return request.user.is_staff
