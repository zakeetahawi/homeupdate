from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from .models import (
    ComplaintType, Complaint, ComplaintUpdate, ComplaintAttachment,
    ComplaintEscalation, ComplaintSLA
)




@admin.register(ComplaintType)
class ComplaintTypeAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'name', 'default_priority', 'default_deadline_hours',
        'responsible_department', 'default_assignee', 'is_active', 'order'
    ]
    list_filter = ['default_priority', 'is_active', 'responsible_department']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'is_active', 'order')
        }),
        ('الإعدادات الافتراضية', {
            'fields': (
                'default_priority', 'default_deadline_hours',
                'responsible_department', 'default_assignee'
            )
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


class ComplaintUpdateInline(admin.TabularInline):
    model = ComplaintUpdate
    extra = 0
    readonly_fields = ('created_at', 'created_by')
    fields = (
        'update_type', 'title', 'description', 'is_visible_to_customer',
        'created_by', 'created_at'
    )


class ComplaintAttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0
    readonly_fields = ('uploaded_at', 'file_size', 'uploaded_by')
    fields = ('file', 'description', 'uploaded_by', 'uploaded_at', 'file_size')





@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'complaint_number', 'customer_name', 'complaint_type',
        'status_display', 'priority_display', 'assigned_to',
        'deadline', 'is_overdue_display', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'complaint_type', 'assigned_department',
        'created_at', 'deadline'
    ]
    search_fields = [
        'complaint_number', 'customer__name', 'title', 'description'
    ]
    readonly_fields = [
        'complaint_number', 'created_at', 'updated_at', 'resolved_at',
        'closed_at', 'last_activity_at', 'is_overdue_display',
        'time_remaining_display', 'resolution_time_display'
    ]
    
    fieldsets = (
        ('معلومات الشكوى', {
            'fields': (
                'complaint_number', 'customer', 'complaint_type',
                'title', 'description'
            )
        }),
        ('الطلب والأنظمة المرتبطة', {
            'fields': ('related_order', 'content_type', 'object_id')
        }),
        ('الحالة والأولوية', {
            'fields': (
                'status', 'priority', 'assigned_to', 'assigned_department'
            )
        }),
        ('التوقيتات', {
            'fields': (
                'created_at', 'deadline', 'resolved_at', 'closed_at',
                'is_overdue_display', 'time_remaining_display',
                'resolution_time_display'
            )
        }),
        ('تقييم العميل', {
            'fields': ('customer_rating', 'customer_feedback'),
            'classes': ('collapse',)
        }),
        ('ملاحظات', {
            'fields': ('internal_notes',),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'branch', 'updated_at', 'last_activity_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [
        ComplaintUpdateInline, ComplaintAttachmentInline
    ]
    
    def customer_name(self, obj):
        return obj.customer.name
    customer_name.short_description = 'العميل'
    
    def status_display(self, obj):
        return format_html(
            '<span class="badge {}">{}</span>',
            obj.get_status_badge_class().replace('bg-', 'badge-'),
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'
    
    def priority_display(self, obj):
        return format_html(
            '<span class="badge {}">{}</span>',
            obj.get_priority_badge_class().replace('bg-', 'badge-'),
            obj.get_priority_display()
        )
    priority_display.short_description = 'الأولوية'
    
    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: red;">✗ متأخرة</span>'
            )
        return format_html(
            '<span style="color: green;">✓ في الوقت</span>'
        )
    is_overdue_display.short_description = 'متأخرة؟'
    
    def time_remaining_display(self, obj):
        remaining = obj.time_remaining
        if remaining is None:
            return 'منتهية'
        
        if remaining.total_seconds() <= 0:
            return format_html('<span style="color: red;">انتهت المهلة</span>')
        
        days = remaining.days
        hours = remaining.seconds // 3600
        
        if days > 0:
            return f'{days} يوم و {hours} ساعة'
        return f'{hours} ساعة'
    time_remaining_display.short_description = 'الوقت المتبقي'
    
    def resolution_time_display(self, obj):
        resolution_time = obj.resolution_time
        if resolution_time is None:
            return 'لم تحل بعد'
        
        days = resolution_time.days
        hours = resolution_time.seconds // 3600
        
        if days > 0:
            return f'{days} يوم و {hours} ساعة'
        return f'{hours} ساعة'
    resolution_time_display.short_description = 'وقت الحل'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'complaint_type', 'assigned_to',
            'assigned_department', 'created_by'
        )
    
    actions = ['mark_as_resolved', 'escalate_complaints']
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.filter(
            status__in=['new', 'in_progress', 'overdue']
        ).update(
            status='resolved',
            resolved_at=timezone.now()
        )
        self.message_user(
            request,
            f'تم تحديد {updated} شكاوى كمحلولة.'
        )
    mark_as_resolved.short_description = 'تحديد كمحلولة'
    
    def escalate_complaints(self, request, queryset):
        # هذا سيتطلب منطق أكثر تعقيداً
        self.message_user(
            request,
            'يرجى استخدام نموذج التصعيد الفردي لكل شكوى.'
        )
    escalate_complaints.short_description = 'تصعيد الشكاوى'


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'complaint', 'update_type', 'title', 'created_by',
        'created_at', 'is_visible_to_customer'
    ]
    list_filter = [
        'update_type', 'is_visible_to_customer', 'created_at'
    ]
    search_fields = ['complaint__complaint_number', 'title', 'description']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'complaint', 'created_by'
        )


@admin.register(ComplaintAttachment)
class ComplaintAttachmentAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'complaint', 'filename', 'file_size_display',
        'uploaded_by', 'uploaded_at'
    ]
    list_filter = ['uploaded_at']
    search_fields = ['complaint__complaint_number', 'filename', 'description']
    readonly_fields = ['uploaded_at', 'file_size']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f'{obj.file_size} بايت'
            elif obj.file_size < 1024 * 1024:
                return f'{obj.file_size / 1024:.1f} كيلوبايت'
            else:
                return f'{obj.file_size / (1024 * 1024):.1f} ميجابايت'
        return 'غير محدد'
    file_size_display.short_description = 'حجم الملف'





@admin.register(ComplaintEscalation)
class ComplaintEscalationAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'complaint', 'reason', 'escalated_from', 'escalated_to',
        'escalated_by', 'escalated_at', 'resolved_at'
    ]
    list_filter = ['reason', 'escalated_at', 'resolved_at']
    search_fields = ['complaint__complaint_number', 'description']
    readonly_fields = ['escalated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'complaint', 'escalated_from', 'escalated_to', 'escalated_by'
        )


@admin.register(ComplaintSLA)
class ComplaintSLAAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'complaint_type', 'response_time_hours', 'resolution_time_hours',
        'escalation_time_hours', 'target_satisfaction_rate', 'is_active'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['complaint_type__name']
    readonly_fields = ['created_at', 'updated_at']