from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from accounts.models import Department
from .models import (
    ComplaintType, Complaint, ComplaintUpdate, ComplaintAttachment,
    ComplaintEscalation, ComplaintSLA, ComplaintTemplate, ResolutionMethod,
    ComplaintUserPermissions
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
                'responsible_department', 'default_assignee', 'responsible_staff'
            )
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ('responsible_staff',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ComplaintUserPermissions)
class ComplaintUserPermissionsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'can_be_assigned_complaints', 'can_receive_escalations',
        'current_assigned_count', 'max_assigned_complaints', 'is_active'
    ]
    list_filter = [
        'can_be_assigned_complaints', 'can_receive_escalations',
        'can_view_all_complaints', 'can_edit_all_complaints', 'is_active'
    ]
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email']
    filter_horizontal = ['departments', 'complaint_types']

    fieldsets = (
        ('المستخدم', {
            'fields': ('user',)
        }),
        ('صلاحيات الإسناد والتصعيد', {
            'fields': (
                'can_be_assigned_complaints', 'can_receive_escalations',
                'max_assigned_complaints'
            )
        }),
        ('صلاحيات العرض والتعديل', {
            'fields': ('can_view_all_complaints', 'can_edit_all_complaints')
        }),
        ('التخصص', {
            'fields': ('departments', 'complaint_types'),
            'description': 'تحديد الأقسام وأنواع الشكاوى التي يمكن للمستخدم التعامل معها'
        }),
        ('الحالة', {
            'fields': ('is_active',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def current_assigned_count(self, obj):
        """عدد الشكاوى المسندة حالياً"""
        count = obj.current_assigned_complaints_count
        if obj.max_assigned_complaints > 0:
            percentage = (count / obj.max_assigned_complaints) * 100
            if percentage >= 90:
                color = 'red'
            elif percentage >= 70:
                color = 'orange'
            else:
                color = 'green'
            return format_html(
                '<span style="color: {};">{}/{}</span>',
                color, count, obj.max_assigned_complaints
            )
        return count
    current_assigned_count.short_description = 'الشكاوى المسندة'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    actions = ['enable_assignment', 'disable_assignment', 'enable_escalation', 'disable_escalation']

    def enable_assignment(self, request, queryset):
        """تفعيل إمكانية الإسناد"""
        updated = queryset.update(can_be_assigned_complaints=True)
        self.message_user(request, f'تم تفعيل إمكانية الإسناد لـ {updated} مستخدم')
    enable_assignment.short_description = 'تفعيل إمكانية الإسناد'

    def disable_assignment(self, request, queryset):
        """إلغاء إمكانية الإسناد"""
        updated = queryset.update(can_be_assigned_complaints=False)
        self.message_user(request, f'تم إلغاء إمكانية الإسناد لـ {updated} مستخدم')
    disable_assignment.short_description = 'إلغاء إمكانية الإسناد'

    def enable_escalation(self, request, queryset):
        """تفعيل إمكانية التصعيد"""
        updated = queryset.update(can_receive_escalations=True)
        self.message_user(request, f'تم تفعيل إمكانية التصعيد لـ {updated} مستخدم')
    enable_escalation.short_description = 'تفعيل إمكانية التصعيد'

    def disable_escalation(self, request, queryset):
        """إلغاء إمكانية التصعيد"""
        updated = queryset.update(can_receive_escalations=False)
        self.message_user(request, f'تم إلغاء إمكانية التصعيد لـ {updated} مستخدم')
    disable_escalation.short_description = 'إلغاء إمكانية التصعيد'


class ComplaintUpdateInline(admin.TabularInline):
    model = ComplaintUpdate
    extra = 0
    readonly_fields = ('created_at', 'created_by')
    fields = (
        'update_type', 'title', 'description', 'is_visible_to_customer',
        'old_status', 'new_status', 'old_assignee', 'new_assignee',
        'resolution_method', 'created_by', 'created_at'
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by', 'old_assignee', 'new_assignee'
        )
    
    def has_delete_permission(self, request, obj=None):
        return False  # منع حذف التحديثات للحفاظ على سجل التغييرات


class ComplaintAttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0
    readonly_fields = ('uploaded_at', 'file_size', 'uploaded_by', 'filename')
    fields = ('file', 'filename', 'description', 'uploaded_by', 'uploaded_at', 'file_size_display')
    
    def file_size_display(self, obj):
        """عرض حجم الملف بتنسيق مناسب"""
        if not obj.file_size:
            return '-'
        
        if obj.file_size < 1024:
            return f'{obj.file_size} بايت'
        elif obj.file_size < 1024 * 1024:
            return f'{obj.file_size / 1024:.1f} كيلوبايت'
        else:
            return f'{obj.file_size / (1024 * 1024):.1f} ميجابايت'
    file_size_display.short_description = 'حجم الملف'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('uploaded_by')





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
    
    actions = ['mark_as_resolved', 'escalate_complaints', 'export_as_csv', 'export_as_excel']
    
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
    
    def export_as_csv(self, request, queryset):
        """تصدير الشكاوى المحددة إلى ملف CSV"""
        from .utils.export import export_complaints_to_csv
        return export_complaints_to_csv(queryset=queryset)
    export_as_csv.short_description = 'تصدير إلى CSV'
    
    def export_as_excel(self, request, queryset):
        """تصدير الشكاوى المحددة إلى ملف Excel"""
        from .utils.export import export_complaints_to_excel
        return export_complaints_to_excel(queryset=queryset)
    export_as_excel.short_description = 'تصدير إلى Excel'


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'complaint', 'update_type', 'title', 'created_by',
        'created_at', 'is_visible_to_customer', 'status_change_display', 'resolution_method'
    ]
    list_filter = [
        'update_type', 'is_visible_to_customer', 'created_at',
        ('complaint__status', admin.RelatedOnlyFieldListFilter),
        ('created_by', admin.RelatedOnlyFieldListFilter)
    ]
    search_fields = [
        'complaint__complaint_number', 'title', 'description',
        'created_by__username', 'created_by__first_name',
        'created_by__last_name'
    ]
    readonly_fields = [
        'created_at', 'created_by', 'old_status', 'new_status',
        'old_assignee', 'new_assignee'
    ]

    fieldsets = (
        ('معلومات التحديث', {
            'fields': ('complaint', 'update_type', 'title', 'description', 'is_visible_to_customer')
        }),
        ('تغيير الحالة', {
            'fields': ('old_status', 'new_status', 'resolution_method'),
            'classes': ('collapse',)
        }),
        ('تغيير التعيين', {
            'fields': ('old_assignee', 'new_assignee'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_change_display(self, obj):
        """عرض تغيير الحالة"""
        if obj.update_type == 'status_change' and obj.old_status and obj.new_status:
            return f'{obj.old_status} → {obj.new_status}'
        return '-'
    status_change_display.short_description = 'تغيير الحالة'
    
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


# ملاحظة: Department admin موجود بالفعل في accounts.admin


@admin.register(ResolutionMethod)
class ResolutionMethodAdmin(admin.ModelAdmin):
    """إدارة طرق حل الشكاوى"""
    list_display = ['name', 'description', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'is_active', 'order')
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ComplaintTemplate)
class ComplaintTemplateAdmin(admin.ModelAdmin):
    """إدارة قوالب الشكاوى"""
    list_display = ['name', 'complaint_type', 'priority', 'is_active', 'created_at']
    list_filter = ['complaint_type', 'priority', 'is_active', 'created_at']
    search_fields = ['name', 'title_template', 'description_template']
    list_editable = ['is_active']
    ordering = ['complaint_type', 'name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'complaint_type', 'priority', 'is_active')
        }),
        ('قوالب النصوص', {
            'fields': ('title_template', 'description_template'),
            'description': 'يمكن استخدام {customer}، {order}، {date} كمتغيرات'
        }),
        ('إعدادات المهلة', {
            'fields': ('default_deadline_hours',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )