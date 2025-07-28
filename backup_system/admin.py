"""
إدارة نظام النسخ الاحتياطي والاستعادة
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import BackupJob, RestoreJob, BackupSchedule


@admin.register(BackupJob)
class BackupJobAdmin(admin.ModelAdmin):
    """إدارة مهام النسخ الاحتياطي"""
    
    list_display = [
        'name', 'backup_type', 'status_badge', 'progress_bar', 
        'file_size_display', 'compressed_size_display', 'compression_ratio',
        'created_by', 'created_at'
    ]
    list_filter = ['status', 'backup_type', 'created_at', 'created_by']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = [
        'id', 'file_path', 'file_size', 'compressed_size', 'compression_ratio',
        'status', 'progress_percentage', 'current_step', 'total_records',
        'processed_records', 'error_message', 'started_at', 'completed_at'
    ]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'backup_type', 'created_by')
        }),
        ('حالة المهمة', {
            'fields': ('status', 'progress_percentage', 'current_step'),
            'classes': ('collapse',)
        }),
        ('معلومات الملف', {
            'fields': ('file_path', 'file_size', 'compressed_size', 'compression_ratio'),
            'classes': ('collapse',)
        }),
        ('إحصائيات', {
            'fields': ('total_records', 'processed_records'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('أخطاء', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """عرض حالة المهمة كشارة ملونة"""
        colors = {
            'pending': 'gray',
            'running': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'الحالة'
    
    def progress_bar(self, obj):
        """عرض شريط التقدم"""
        if obj.status == 'running':
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background-color: #007cba; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
                '{}%</div></div>',
                obj.progress_percentage, int(obj.progress_percentage)
            )
        elif obj.status == 'completed':
            return format_html('<span style="color: green; font-weight: bold;">100%</span>')
        else:
            return '-'
    progress_bar.short_description = 'التقدم'
    
    def has_add_permission(self, request):
        """منع إضافة مهام جديدة من الإدارة"""
        return False


@admin.register(RestoreJob)
class RestoreJobAdmin(admin.ModelAdmin):
    """إدارة مهام الاستعادة"""
    
    list_display = [
        'name', 'status_badge', 'progress_bar', 'success_rate_display',
        'file_size_display', 'clear_existing_data', 'created_by', 'created_at'
    ]
    list_filter = ['status', 'clear_existing_data', 'created_at', 'created_by']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = [
        'id', 'source_file', 'file_size', 'status', 'progress_percentage',
        'current_step', 'total_records', 'processed_records', 'success_records',
        'failed_records', 'error_message', 'started_at', 'completed_at'
    ]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('إعدادات الاستعادة', {
            'fields': ('source_file', 'file_size', 'clear_existing_data')
        }),
        ('حالة المهمة', {
            'fields': ('status', 'progress_percentage', 'current_step'),
            'classes': ('collapse',)
        }),
        ('إحصائيات', {
            'fields': ('total_records', 'processed_records', 'success_records', 'failed_records'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('أخطاء', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """عرض حالة المهمة كشارة ملونة"""
        colors = {
            'pending': 'gray',
            'running': 'orange',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'الحالة'
    
    def progress_bar(self, obj):
        """عرض شريط التقدم"""
        if obj.status == 'running':
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background-color: #007cba; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
                '{}%</div></div>',
                obj.progress_percentage, int(obj.progress_percentage)
            )
        elif obj.status == 'completed':
            return format_html('<span style="color: green; font-weight: bold;">100%</span>')
        else:
            return '-'
    progress_bar.short_description = 'التقدم'
    
    def success_rate_display(self, obj):
        """عرض نسبة النجاح"""
        if obj.status == 'completed' and obj.total_records > 0:
            rate = obj.success_rate
            color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, rate
            )
        return '-'
    success_rate_display.short_description = 'نسبة النجاح'
    
    def has_add_permission(self, request):
        """منع إضافة مهام جديدة من الإدارة"""
        return False


@admin.register(BackupSchedule)
class BackupScheduleAdmin(admin.ModelAdmin):
    """إدارة جدولة النسخ الاحتياطية"""
    
    list_display = [
        'name', 'frequency', 'backup_type', 'is_active_badge',
        'next_run', 'last_run', 'max_backups_to_keep', 'created_by'
    ]
    list_filter = ['frequency', 'backup_type', 'is_active', 'created_by']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('إعدادات الجدولة', {
            'fields': ('frequency', 'hour', 'minute', 'is_active')
        }),
        ('إعدادات النسخة الاحتياطية', {
            'fields': ('backup_type', 'max_backups_to_keep')
        }),
        ('معلومات التشغيل', {
            'fields': ('last_run', 'next_run'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_badge(self, obj):
        """عرض حالة التفعيل كشارة ملونة"""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">نشط</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">غير نشط</span>')
    is_active_badge.short_description = 'الحالة'
    
    def save_model(self, request, obj, form, change):
        """حفظ النموذج مع تحديد المستخدم المنشئ"""
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# تخصيص عنوان الإدارة
admin.site.site_header = "إدارة نظام النسخ الاحتياطي"
admin.site.site_title = "نظام النسخ الاحتياطي"
admin.site.index_title = "لوحة تحكم النسخ الاحتياطي"