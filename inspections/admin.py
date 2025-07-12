from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Inspection,
    InspectionEvaluation,
    InspectionReport,
    InspectionNotification
)

@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = [
        'contract_number',
        'customer',
        'request_date',
        'scheduled_date',
        'status',
        'result',
        'expected_delivery_date',
        'created_by'
    ]
    list_filter = ['status', 'result', 'request_date', 'scheduled_date', 'branch']
    search_fields = [
        'contract_number',
        'customer__name',
        'notes',
        'created_by__username'
    ]
    date_hierarchy = 'request_date'
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'expected_delivery_date']

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('contract_number', 'customer', 'branch', 'request_date', 'scheduled_date')
        }),
        (_('حالة المعاينة'), {
            'fields': ('status', 'result', 'notes')
        }),
        (_('موعد التسليم'), {
            'fields': ('expected_delivery_date',)
        }),
        (_('معلومات النظام'), {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
            if not obj.branch:
                obj.branch = request.user.branch
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'branch', 'created_by')

@admin.register(InspectionEvaluation)
class InspectionEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        'inspection',
        'criteria',
        'rating',
        'created_by',
        'created_at'
    ]
    list_filter = ['criteria', 'rating', 'created_at']
    search_fields = [
        'inspection__contract_number',
        'notes',
        'created_by__username'
    ]
    readonly_fields = ['created_at', 'created_by']

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(InspectionReport)
class InspectionReportAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'report_type',
        'branch',
        'date_from',
        'date_to',
        'total_inspections',
        'created_by'
    ]
    list_filter = ['report_type', 'branch', 'date_from', 'date_to']
    search_fields = ['title', 'notes']
    readonly_fields = [
        'total_inspections',
        'successful_inspections',
        'pending_inspections',
        'cancelled_inspections',
        'created_at',
        'created_by'
    ]

    fieldsets = (
        (_('معلومات التقرير'), {
            'fields': ('title', 'report_type', 'branch', 'date_from', 'date_to', 'notes')
        }),
        (_('إحصائيات'), {
            'fields': (
                'total_inspections',
                'successful_inspections',
                'pending_inspections',
                'cancelled_inspections'
            )
        }),
        (_('معلومات النظام'), {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        obj.calculate_statistics()
        super().save_model(request, obj, form, change)

@admin.register(InspectionNotification)
class InspectionNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'inspection',
        'type',
        'is_read',
        'scheduled_for',
        'created_at'
    ]
    list_filter = ['type', 'is_read', 'created_at', 'scheduled_for']
    search_fields = [
        'inspection__contract_number',
        'message'
    ]
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, _(f'تم تحديث {updated} تنبيهات كمقروءة.'))
    mark_as_read.short_description = _('تحديد كمقروء')
