from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from .models import (
    Inspection,
    InspectionEvaluation,
    InspectionReport,
    InspectionNotification
)

@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = [
        'inspection_code',
        'customer',
        'inspector_display',
        'responsible_employee',
        'status_display',
        'result_display',
        'request_date',
        'scheduled_date', 
        'windows_count',
        'branch',
        'created_at'
    ]
    list_filter = [
        'status', 
        'result', 
        'branch',
        'is_from_orders',
        'request_date', 
        'scheduled_date',
        'inspector',
        'responsible_employee'
    ]
    search_fields = [
        'order__order_number',
        'customer__name',
        'customer__phone',
        'inspector__first_name',
        'inspector__last_name',
        'responsible_employee__name',
        'notes',
    ]
    date_hierarchy = 'request_date'
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'completed_at',
        'expected_delivery_date',
        'is_uploaded_to_drive',
        'google_drive_file_url'
    ]
    
    actions = ['mark_as_completed', 'mark_as_passed', 'mark_as_failed', 'export_inspections']

    fieldsets = (
        (_('معلومات العميل والطلب'), {
            'fields': ('order', 'customer', 'branch', 'responsible_employee'),
            'description': 'يجب ربط المعاينة بطلب من قسم الطلبات'
        }),
        (_('معلومات المعاينة'), {
            'fields': ('inspector', 'windows_count', 'request_date', 'scheduled_date', 'scheduled_time')
        }),
        (_('حالة المعاينة'), {
            'fields': ('status', 'result', 'expected_delivery_date')
        }),
        (_('ملاحظات'), {
            'fields': ('notes', 'order_notes')
        }),
        (_('ملفات المعاينة'), {
            'fields': ('inspection_file', 'google_drive_file_url', 'is_uploaded_to_drive'),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at', 'updated_at', 'completed_at', 'is_from_orders')
        }),
    )

    def inspector_display(self, obj):
        """عرض اسم المعاين"""
        if obj.inspector:
            return obj.inspector.get_full_name() or obj.inspector.username
        return '-'
    inspector_display.short_description = 'المعاين'

    def status_display(self, obj):
        """عرض حالة المعاينة بألوان"""
        colors = {
            'pending': '#ffc107',      # أصفر
            'scheduled': '#17a2b8',    # أزرق فاتح
            'completed': '#28a745',    # أخضر
            'cancelled': '#dc3545',    # أحمر
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'

    def result_display(self, obj):
        """عرض نتيجة المعاينة بألوان"""
        if not obj.result:
            return '-'
        
        colors = {
            'passed': '#28a745',    # أخضر
            'failed': '#dc3545',    # أحمر
        }
        color = colors.get(obj.result, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_result_display()
        )
    result_display.short_description = 'النتيجة'

    def mark_as_completed(self, request, queryset):
        """تحديد المعاينات كمكتملة"""
        updated = queryset.filter(status__in=['pending', 'scheduled']).update(status='completed')
        self.message_user(
            request,
            f'تم تحديث {updated} معاينة كمكتملة.',
            level='SUCCESS' if updated > 0 else 'WARNING'
        )
    mark_as_completed.short_description = 'تحديد كمكتملة'

    def mark_as_passed(self, request, queryset):
        """تحديد المعاينات كناجحة"""
        updated = queryset.update(result='passed', status='completed')
        self.message_user(
            request,
            f'تم تحديث {updated} معاينة كناجحة.',
            level='SUCCESS' if updated > 0 else 'WARNING'
        )
    mark_as_passed.short_description = 'تحديد كناجحة'

    def mark_as_failed(self, request, queryset):
        """تحديد المعاينات كغير مجدية"""
        updated = queryset.update(result='failed', status='completed')
        self.message_user(
            request,
            f'تم تحديث {updated} معاينة كغير مجدية.',
            level='SUCCESS' if updated > 0 else 'WARNING'
        )
    mark_as_failed.short_description = 'تحديد كغير مجدية'

    def export_inspections(self, request, queryset):
        """تصدير المعاينات المحددة"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inspections.csv"'
        response.write('\ufeff')  # BOM for Excel
        
        writer = csv.writer(response)
        writer.writerow([
            'رقم المعاينة', 'العميل', 'المعاين', 'البائع المسؤول', 
            'الحالة', 'النتيجة', 'عدد الشبابيك', 'تاريخ الطلب', 
            'تاريخ التنفيذ', 'الفرع', 'تاريخ الإنشاء'
        ])
        
        for inspection in queryset:
            writer.writerow([
                inspection.id,
                inspection.customer.name if inspection.customer else '',
                inspection.inspector.get_full_name() if inspection.inspector else '',
                inspection.responsible_employee.name if inspection.responsible_employee else '',
                inspection.get_status_display(),
                inspection.get_result_display() if inspection.result else '',
                inspection.windows_count or '',
                inspection.request_date.strftime('%Y-%m-%d') if inspection.request_date else '',
                inspection.scheduled_date.strftime('%Y-%m-%d') if inspection.scheduled_date else '',
                inspection.branch.name if inspection.branch else '',
                inspection.created_at.strftime('%Y-%m-%d') if inspection.created_at else ''
            ])
        
        return response
    export_inspections.short_description = 'تصدير إلى CSV'

    def get_urls(self):
        """إضافة URLs مخصصة للوصول للمعاينات باستخدام الكود"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'by-code/<str:inspection_code>/',
                self.admin_site.admin_view(self.inspection_by_code_view),
                name='inspections_inspection_by_code',
            ),
        ]
        return custom_urls + urls

    def inspection_by_code_view(self, request, inspection_code):
        """عرض المعاينة باستخدام الكود وإعادة التوجيه لصفحة التحرير"""
        try:
            # البحث باستخدام order_number إذا كان يحتوي على رقم الطلب
            if inspection_code.endswith('-I'):
                base_code = inspection_code[:-2]  # إزالة '-I'
                if base_code.startswith('#'):
                    # البحث باستخدام ID مباشرة
                    inspection_id = base_code[1:]  # إزالة '#'
                    inspection = Inspection.objects.get(id=inspection_id)
                else:
                    # البحث باستخدام order_number
                    inspection = Inspection.objects.get(order__order_number=base_code)
            else:
                # محاولة البحث المباشر بالكود
                inspection = Inspection.objects.get(id=inspection_code)
                
            return HttpResponseRedirect(
                reverse('admin:inspections_inspection_change', args=[inspection.pk])
            )
        except (Inspection.DoesNotExist, ValueError):
            self.message_user(request, f'المعاينة بكود {inspection_code} غير موجودة', level='error')
            return HttpResponseRedirect(reverse('admin:inspections_inspection_changelist'))

    def inspection_code(self, obj):
        """عرض رقم طلب المعاينة الموحد مع روابط محسنة - تحديث للاستخدام الكود في admin"""
        code = obj.inspection_code
        
        try:
            # رابط عرض المعاينة في الواجهة
            view_url = reverse('inspections:inspection_detail_by_code', args=[code])
            # رابط تحرير المعاينة في لوحة التحكم باستخدام الكود
            admin_url = reverse('admin:inspections_inspection_by_code', kwargs={'inspection_code': code})
            
            return format_html(
                '<strong>{}</strong><br/>'
                '<a href="{}" target="_blank" title="عرض في الواجهة">'
                '<span style="color: #0073aa;">👁️ عرض</span></a> | '
                '<a href="{}" title="تحرير في لوحة التحكم">'
                '<span style="color: #d63638;">✏️ تحرير</span></a>',
                code,
                view_url,
                admin_url
            )
        except Exception:
            return code
    inspection_code.short_description = 'رقم طلب المعاينة'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'branch', 'created_by', 'inspector', 'order'
        ).prefetch_related(
            'evaluations', 'notifications'
        )

    def get_form(self, request, obj=None, **kwargs):
        """تخصيص النموذج حسب المستخدم"""
        form = super().get_form(request, obj, **kwargs)
        
        # تقييد المعاينين والبائعين حسب فرع المستخدم
        if not request.user.is_superuser and hasattr(request.user, 'branch') and request.user.branch:
            if hasattr(form.base_fields, 'inspector'):
                form.base_fields['inspector'].queryset = form.base_fields['inspector'].queryset.filter(
                    branch=request.user.branch,
                    is_active=True
                )
            
            if hasattr(form.base_fields, 'responsible_employee'):
                form.base_fields['responsible_employee'].queryset = form.base_fields['responsible_employee'].queryset.filter(
                    branch=request.user.branch,
                    is_active=True
                )
            
            if hasattr(form.base_fields, 'customer'):
                form.base_fields['customer'].queryset = form.base_fields['customer'].queryset.filter(
                    branch=request.user.branch,
                    status='active'
                )
        
        return form

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
            if not obj.branch:
                obj.branch = request.user.branch
        super().save_model(request, obj, form, change)

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
        'inspection__id',
        'inspection__customer__name',
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
        'inspection__id',
        'inspection__customer__name',
        'message'
    ]
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, _(f'تم تحديث {updated} تنبيهات كمقروءة.'))
    mark_as_read.short_description = _('تحديد كمقروء')
