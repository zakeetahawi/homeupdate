"""
تسجيل النماذج في واجهة الإدارة
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Database, Backup, GoogleDriveConfig
from .google_sync import GoogleSyncConfig, GoogleSyncLog
from .google_sync_advanced import (
    GoogleSheetMapping, GoogleSyncTask, GoogleSyncConflict, GoogleSyncSchedule
)
from .google_sync_advanced import (
    GoogleSheetMapping, GoogleSyncTask, GoogleSyncConflict, GoogleSyncSchedule
)

@admin.register(Database)
class DatabaseAdmin(admin.ModelAdmin):
    """إدارة قواعد البيانات"""

    list_display = ('name', 'db_type', 'is_active', 'created_at')
    list_filter = ('db_type', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'db_type', 'is_active')
        }),
        (_('معلومات الاتصال'), {
            'fields': ('connection_info',),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """إدارة النسخ الاحتياطية"""

    list_display = ('name', 'database', 'size_display', 'created_at', 'created_by')
    list_filter = ('database', 'created_at')
    search_fields = ('name', 'database__name')
    readonly_fields = ('size', 'created_at', 'created_by')
    fieldsets = (
        (None, {
            'fields': ('name', 'database', 'file_path')
        }),
        (_('معلومات النظام'), {
            'fields': ('size', 'created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GoogleDriveConfig)
class GoogleDriveConfigAdmin(admin.ModelAdmin):
    """إدارة إعدادات Google Drive"""

    list_display = ('name', 'is_active', 'total_uploads', 'last_upload')
    list_filter = ('is_active', 'last_upload')
    search_fields = ('name',)
    readonly_fields = ('total_uploads', 'last_upload', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        (_('إعدادات مجلد المعاينات'), {
            'fields': ('inspections_folder_id', 'inspections_folder_name'),
            'classes': ('collapse',)
        }),
        (_('إعدادات مجلد العقود'), {
            'fields': ('contracts_folder_id', 'contracts_folder_name'),
            'classes': ('collapse',)
        }),
        (_('ملف الاعتماد'), {
            'fields': ('credentials_file',),
            'classes': ('collapse',)
        }),
        (_('إعدادات تسمية الملفات'), {
            'fields': ('filename_pattern',),
            'classes': ('collapse',)
        }),
        (_('الإحصائيات'), {
            'fields': ('total_uploads', 'last_upload'),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GoogleSyncConfig)
class GoogleSyncConfigAdmin(admin.ModelAdmin):
    """إدارة إعدادات مزامنة غوغل"""

    list_display = ('name', 'is_active', 'last_sync', 'sync_frequency', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('last_sync', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'spreadsheet_id', 'credentials_file', 'is_active', 'sync_frequency')
        }),
        (_('خيارات المزامنة'), {
            'fields': ('sync_databases', 'sync_users', 'sync_customers', 'sync_orders', 'sync_products', 'sync_settings'),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'fields': ('last_sync', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GoogleSheetMapping)
class GoogleSheetMappingAdmin(admin.ModelAdmin):
    """إدارة تعيينات أوراق جوجل"""
    list_display = ('name', 'spreadsheet_id', 'sheet_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'spreadsheet_id', 'sheet_name')
    readonly_fields = ('created_at', 'updated_at', 'last_sync')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('إعدادات جدول البيانات'), {
            'fields': ('spreadsheet_id', 'sheet_name', 'header_row', 'data_start_row')
        }),
        (_('خيارات المزامنة'), {
            'fields': ('update_existing', 'auto_create', 'sync_frequency', 'last_sync')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 20


@admin.register(GoogleSyncTask)
class GoogleSyncTaskAdmin(admin.ModelAdmin):
    """إدارة مهام المزامنة"""
    list_display = ('mapping', 'task_type', 'status', 'started_at', 'completed_at', 'created_by')
    list_filter = ('status', 'task_type', 'started_at', 'completed_at')
    search_fields = ('mapping__name', 'error_log')
    readonly_fields = ('started_at', 'completed_at', 'created_by', 'get_duration', 'get_success_rate')
    fieldsets = (
        (None, {
            'fields': ('mapping', 'task_type', 'status', 'error_log')
        }),
        (_('التوقيتات'), {
            'fields': ('started_at', 'completed_at', 'get_duration'),
            'classes': ('collapse',)
        }),
        (_('النتائج'), {
            'fields': ('rows_processed', 'rows_successful', 'rows_failed', 'get_success_rate'),
            'classes': ('collapse',)
        }),
        (_('معاملات إضافية'), {
            'fields': ('task_parameters', 'result'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 20

    def get_duration(self, obj):
        return obj.get_duration()
    get_duration.short_description = 'مدة التنفيذ'
    get_duration.admin_order_field = 'completed_at'

    def get_success_rate(self, obj):
        return f"{obj.get_success_rate()}%" if hasattr(obj, 'get_success_rate') else 'N/A'
    get_success_rate.short_description = 'معدل النجاح'
    get_success_rate.admin_order_field = 'rows_successful'

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by on first save
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GoogleSyncConflict)
class GoogleSyncConflictAdmin(admin.ModelAdmin):
    """إدارة تعارضات المزامنة"""
    list_display = ('task', 'conflict_type', 'row_number', 'resolution_status', 'created_at')
    list_filter = ('resolution_status', 'conflict_type', 'created_at')
    search_fields = ('task__mapping__name', 'row_number', 'resolution_notes')
    readonly_fields = ('created_at', 'resolved_at', 'get_conflict_description')
    fieldsets = (
        (None, {
            'fields': ('task', 'conflict_type', 'row_number', 'resolution_status')
        }),
        (_('تفاصيل التعارض'), {
            'fields': ('get_conflict_description', 'sheet_data', 'existing_data'),
        }),
        (_('حل التعارض'), {
            'fields': ('resolution_action', 'resolution_notes', 'resolved_at'),
        }),
    )
    list_per_page = 20
    actions = ['mark_as_resolved', 'mark_as_ignored']

    def get_conflict_description(self, obj):
        return obj.get_conflict_description() if hasattr(obj, 'get_conflict_description') else 'غير متوفر'
    get_conflict_description.short_description = 'وصف التعارض'

    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(resolution_status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'تم تحديد {updated} من التعارضات كمحلولة.')
    mark_as_resolved.short_description = 'تحديد كمحلول'

    def mark_as_ignored(self, request, queryset):
        updated = queryset.update(resolution_status='ignored', resolved_at=timezone.now())
        self.message_user(request, f'تم تجاهل {updated} من التعارضات.')
    mark_as_ignored.short_description = 'تجاهل التعارضات المحددة'


@admin.register(GoogleSyncSchedule)
class GoogleSyncScheduleAdmin(admin.ModelAdmin):
    """إدارة جدولة المزامنة"""
    list_display = ('name', 'mapping', 'is_active', 'frequency', 'next_run', 'last_run', 'get_success_rate')
    list_filter = ('is_active', 'frequency', 'task_type')
    search_fields = ('name', 'mapping__name')
    readonly_fields = ('last_run', 'next_run', 'created_at', 'get_success_rate')
    fieldsets = (
        (None, {
            'fields': ('name', 'mapping', 'is_active')
        }),
        (_('إعدادات الجدولة'), {
            'fields': ('frequency', 'scheduled_time', 'task_type')
        }),
        (_('سجل التشغيل'), {
            'fields': ('last_run', 'next_run', 'total_runs', 'successful_runs', 'failed_runs', 'get_success_rate'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 20
    actions = ['run_now']

    def get_success_rate(self, obj):
        if hasattr(obj, 'total_runs') and obj.total_runs > 0:
            return f"{(obj.successful_runs / obj.total_runs) * 100:.1f}%"
        return "N/A"
    get_success_rate.short_description = 'معدل النجاح'

    def run_now(self, request, queryset):
        for schedule in queryset:
            # هنا يمكنك إضافة الكود لتنفيذ الجدولة فوراً
            self.message_user(request, f'سيتم تشغيل الجدولة {schedule.name} قريباً')
    run_now.short_description = 'تشغيل الجدولة المحددة الآن'

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by on first save
            obj.created_by = request.user
            if hasattr(obj, 'calculate_next_run'):
                obj.calculate_next_run()
        super().save_model(request, obj, form, change)


@admin.register(GoogleSyncLog)
class GoogleSyncLogAdmin(admin.ModelAdmin):
    """إدارة سجلات مزامنة غوغل"""

    list_display = ('config', 'status', 'message', 'created_at')
    list_filter = ('status', 'created_at', 'config')
    search_fields = ('message',)
    readonly_fields = ('config', 'status', 'message', 'details', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('config', 'status', 'message')
        }),
        (_('التفاصيل'), {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
