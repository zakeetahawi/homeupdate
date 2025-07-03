from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Installation, InstallationTeam, InstallationStep, InstallationQualityCheckOld, InstallationIssue, InstallationNotification
from .models_new import InstallationNew, InstallationTeamNew, InstallationTechnician, InstallationAlert

@admin.register(InstallationTeam)
class InstallationTeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader', 'branch', 'is_active')
    list_filter = ('is_active', 'branch')
    search_fields = ('name', 'leader__username')
    filter_horizontal = ('members',)

@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):
    list_display = ('order', 'team', 'status', 'scheduled_date', 'quality_rating')
    list_filter = ('status', 'team', 'scheduled_date')
    search_fields = ('order__order_number', 'notes')
    date_hierarchy = 'scheduled_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('order', 'inspection', 'team', 'scheduled_date')
        }),
        (_('حالة التركيب'), {
            'fields': ('status', 'actual_start_date', 'actual_end_date', 'quality_rating')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(InstallationStep)
class InstallationStepAdmin(admin.ModelAdmin):
    list_display = ('name', 'installation', 'order', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'completed_at')
    search_fields = ('name', 'description', 'installation__order__order_number')

@admin.register(InstallationQualityCheckOld)
class InstallationQualityCheckAdmin(admin.ModelAdmin):
    list_display = ('installation', 'criteria', 'rating', 'checked_by', 'created_at')
    list_filter = ('criteria', 'rating', 'created_at')
    search_fields = ('installation__order__order_number', 'notes')

@admin.register(InstallationIssue)
class InstallationIssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'installation', 'priority', 'status', 'reported_by')
    list_filter = ('priority', 'status')
    search_fields = ('title', 'description', 'installation__order__order_number')

@admin.register(InstallationNotification)
class InstallationNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'installation', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'installation__order__order_number')


# النماذج الجديدة
@admin.register(InstallationNew)
class InstallationNewAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'customer_phone', 'windows_count', 'status', 'priority', 'scheduled_date', 'created_at')
    list_filter = ('status', 'priority', 'location_type', 'scheduled_date', 'created_at')
    search_fields = ('customer_name', 'customer_phone', 'customer_address', 'salesperson_name', 'branch_name')
    date_hierarchy = 'scheduled_date'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('معلومات العميل'), {
            'fields': ('customer_name', 'customer_phone', 'customer_address')
        }),
        (_('تفاصيل التركيب'), {
            'fields': ('windows_count', 'location_type', 'priority', 'scheduled_date', 'team')
        }),
        (_('معلومات الطلب'), {
            'fields': ('order', 'salesperson_name', 'branch_name')
        }),
        (_('حالة التركيب'), {
            'fields': ('status', 'order_date', 'actual_start_date', 'actual_end_date')
        }),
        (_('ملاحظات'), {
            'fields': ('notes', 'installation_notes')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'team', 'created_by')

    actions = ['mark_as_completed', 'mark_as_pending', 'delete_selected']

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'تم تحديث {updated} تركيب إلى مكتمل')
    mark_as_completed.short_description = 'تحديد كمكتمل'

    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'تم تحديث {updated} تركيب إلى قيد الانتظار')
    mark_as_pending.short_description = 'تحديد كقيد الانتظار'


@admin.register(InstallationTeamNew)
class InstallationTeamNewAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader', 'max_daily_installations', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('معلومات الفريق'), {
            'fields': ('name', 'leader', 'members', 'branch')
        }),
        (_('إعدادات العمل'), {
            'fields': ('max_daily_installations', 'is_active', 'specializations')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InstallationTechnician)
class InstallationTechnicianAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'experience_years', 'is_active', 'branch')
    list_filter = ('is_active', 'experience_years', 'branch')
    search_fields = ('user__first_name', 'user__last_name', 'employee_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(InstallationAlert)
class InstallationAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'installation', 'alert_type', 'severity', 'is_resolved', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_resolved', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('installation')
