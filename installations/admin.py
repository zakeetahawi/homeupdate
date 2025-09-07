from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from accounts.models import SystemSettings

from .models import (
    InstallationSchedule, InstallationTeam, Technician, Driver,
    ModificationRequest, ModificationImage, ManufacturingOrder as InstallationManufacturingOrder,
    ModificationReport, ReceiptMemo, InstallationPayment, InstallationArchive, CustomerDebt,
    InstallationAnalytics, ModificationErrorAnalysis, ModificationErrorType
)
from manufacturing.models import ManufacturingOrder


# فلتر مخصص لنوع الطلب - للاستخدام مع ManufacturingOrder
class OrderTypeFilter(admin.SimpleListFilter):
    title = 'نوع الطلب'
    parameter_name = 'order_type'

    def lookups(self, request, model_admin):
        return [
            ('installation', 'تركيب'),
            ('custom', 'تفصيل'),
            ('accessory', 'اكسسوار'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(order_type=self.value())
        return queryset


# فلتر مخصص لنوع الطلب - للاستخدام مع InstallationSchedule (من Order)
class InstallationOrderTypeFilter(admin.SimpleListFilter):
    title = 'نوع الطلب'
    parameter_name = 'order_type'

    def lookups(self, request, model_admin):
        return [
            ('installation', 'تركيب'),
            ('custom', 'تفصيل'),
            ('accessory', 'اكسسوار'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            # فلترة حسب نوع الطلب من Order
            if self.value() == 'installation':
                return queryset.filter(order__selected_types__icontains='installation')
            elif self.value() == 'custom':
                return queryset.filter(order__selected_types__icontains='custom')
            elif self.value() == 'accessory':
                return queryset.filter(order__selected_types__icontains='accessory')
        return queryset


# فلتر مخصص لحالة التركيب
class InstallationStatusFilter(admin.SimpleListFilter):
    title = 'حالة التركيب'
    parameter_name = 'installation_status'

    def lookups(self, request, model_admin):
        return [
            ('needs_scheduling', 'يحتاج جدولة'),
            ('scheduled', 'مجدول'),
            ('in_installation', 'قيد التركيب'),
            ('completed', 'مكتمل'),
            ('cancelled', 'ملغي'),
            ('modification_required', 'يحتاج تعديل'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(order__installation_status=self.value())
        return queryset


# فلتر مخصص لحالة المصنع
class ManufacturingStatusFilter(admin.SimpleListFilter):
    title = 'حالة المصنع'
    parameter_name = 'manufacturing_status'

    def lookups(self, request, model_admin):
        return [
            ('pending_approval', 'قيد الموافقة'),
            ('pending', 'قيد الانتظار'),
            ('in_progress', 'قيد التصنيع'),
            ('ready_install', 'جاهز للتركيب'),
            ('completed', 'مكتمل'),
            ('delivered', 'تم التسليم'),
            ('rejected', 'مرفوض'),
            ('cancelled', 'ملغي'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


def currency_format(amount):
    """تنسيق المبلغ مع عملة النظام"""
    try:
        settings = SystemSettings.get_settings()
        symbol = settings.currency_symbol
        formatted_amount = f"{amount:,.2f}"
        return f"{formatted_amount} {symbol}"
    except Exception:
        return f"{amount:,.2f} ر.س"


@admin.register(CustomerDebt)
class CustomerDebtAdmin(admin.ModelAdmin):
    list_per_page = 50  # زيادة العدد إلى 50
    list_display = ['customer', 'order', 'debt_amount_formatted', 'is_paid', 'payment_date', 'created_at']
    list_filter = ['is_paid', 'created_at', 'payment_date']
    search_fields = ['customer__name', 'order__order_number']
    list_editable = ['is_paid']
    ordering = ['-created_at']
    
    # إضافة إمكانية الترتيب لجميع الأعمدة
    sortable_by = [
        'customer__name', 'order__order_number', 'debt_amount',
        'is_paid', 'payment_date', 'created_at'
    ]

    def debt_amount_formatted(self, obj):
        return currency_format(obj.debt_amount)
    debt_amount_formatted.short_description = 'مبلغ المديونية'
    debt_amount_formatted.admin_order_field = 'debt_amount'  # تمكين الترتيب


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'phone', 'specialization', 'is_active', 'created_at']
    list_filter = ['is_active', 'specialization', 'created_at']
    search_fields = ['name', 'phone', 'specialization']
    list_editable = ['is_active']
    ordering = ['name']


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'phone', 'license_number', 'vehicle_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'phone', 'license_number', 'vehicle_number']
    list_editable = ['is_active']
    ordering = ['name']


@admin.register(InstallationTeam)
class InstallationTeamAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'driver', 'technicians_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']
    filter_horizontal = ['technicians']
    ordering = ['name']

    def technicians_count(self, obj):
        return obj.technicians.count()
    technicians_count.short_description = 'عدد الفنيين'


@admin.register(InstallationSchedule)
class InstallationScheduleAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'installation_code', 'customer_name', 'scheduled_date', 'scheduled_time',
        'team', 'status_display', 'created_at'
    ]
    list_filter = [
        'status',
        InstallationOrderTypeFilter,  # فلتر مخصص لنوع الطلب (من Order)
        'scheduled_date',
        'team',
        'created_at'
    ]
    search_fields = ['order__order_number', 'order__customer__name']
    list_editable = ['team']
    date_hierarchy = 'scheduled_date'
    ordering = ['-scheduled_date', '-scheduled_time']

    # إضافة إجراءات مجمعة لتغيير حالة التركيب
    actions = [
        'mark_status_scheduled', 'mark_status_in_installation', 'mark_status_completed',
        'mark_status_cancelled', 'mark_status_modification_required'
    ]
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('order', 'status')
        }),
        ('جدولة التركيب', {
            'fields': ('team', 'scheduled_date', 'scheduled_time')
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        """عرض حالة التركيب بألوان"""
        colors = {
            'needs_scheduling': '#ffc107',         # أصفر
            'scheduled': '#17a2b8',               # أزرق فاتح
            'in_installation': '#007bff',         # أزرق
            'completed': '#28a745',               # أخضر
            'cancelled': '#dc3545',               # أحمر
            'modification_required': '#fd7e14',   # برتقالي
            'modification_in_progress': '#6f42c1', # بنفسجي
            'modification_completed': '#20c997',   # أخضر فاتح
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'

    def customer_name(self, obj):
        if obj.order and obj.order.customer:
            return obj.order.customer.name
        return '-'
    customer_name.short_description = 'اسم العميل'

    def get_urls(self):
        """إضافة URLs مخصصة للوصول للتركيبات باستخدام الكود"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'by-code/<str:installation_code>/',
                self.admin_site.admin_view(self.installation_by_code_view),
                name='installations_installationschedule_by_code',
            ),
        ]
        return custom_urls + urls

    def installation_by_code_view(self, request, installation_code):
        """عرض التركيب باستخدام الكود وإعادة التوجيه لصفحة التحرير"""
        try:
            # البحث باستخدام order_number إذا كان يحتوي على رقم الطلب
            if installation_code.endswith('-T'):
                base_code = installation_code[:-2]  # إزالة '-T'
                if base_code.startswith('#'):
                    # البحث باستخدام ID مباشرة
                    installation_id = base_code[1:]  # إزالة '#'
                    installation = InstallationSchedule.objects.get(id=installation_id)
                else:
                    # البحث باستخدام order_number
                    installation = InstallationSchedule.objects.get(order__order_number=base_code)
            else:
                # محاولة البحث المباشر بالكود
                installation = InstallationSchedule.objects.get(id=installation_code)
                
            return HttpResponseRedirect(
                reverse('admin:installations_installationschedule_change', args=[installation.pk])
            )
        except (InstallationSchedule.DoesNotExist, ValueError):
            self.message_user(request, f'التركيب بكود {installation_code} غير موجود', level='error')
            return HttpResponseRedirect(reverse('admin:installations_installationschedule_changelist'))

    def installation_code(self, obj):
        """عرض رقم طلب التركيب الموحد مع روابط محسنة - تحديث للاستخدام الكود في admin"""
        code = obj.installation_code
        
        try:
            # رابط عرض التركيب في الواجهة
            view_url = reverse('installations:installation_detail_by_code', args=[code])
            # رابط تحرير التركيب في لوحة التحكم باستخدام الكود
            admin_url = reverse('admin:installations_installationschedule_by_code', kwargs={'installation_code': code})
            
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
    installation_code.short_description = 'رقم طلب التركيب'

    # إجراءات التحديث المجمع لحالة التركيب
    def mark_status_scheduled(self, request, queryset):
        """تغيير حالة التركيب إلى مجدول"""
        updated = queryset.update(status='scheduled')
        self.message_user(request, f'✅ تم تغيير حالة {updated} تركيب إلى "مجدول"')
    mark_status_scheduled.short_description = "تغيير الحالة إلى مجدول"

    def mark_status_in_installation(self, request, queryset):
        """تغيير حالة التركيب إلى قيد التركيب"""
        updated = queryset.update(status='in_installation')
        self.message_user(request, f'✅ تم تغيير حالة {updated} تركيب إلى "قيد التركيب"')
    mark_status_in_installation.short_description = "تغيير الحالة إلى قيد التركيب"

    def mark_status_completed(self, request, queryset):
        """تغيير حالة التركيب إلى مكتمل"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'✅ تم تغيير حالة {updated} تركيب إلى "مكتمل"')
    mark_status_completed.short_description = "تغيير الحالة إلى مكتمل"

    def mark_status_cancelled(self, request, queryset):
        """تغيير حالة التركيب إلى ملغي"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'✅ تم تغيير حالة {updated} تركيب إلى "ملغي"')
    mark_status_cancelled.short_description = "تغيير الحالة إلى ملغي"

    def mark_status_modification_required(self, request, queryset):
        """تغيير حالة التركيب إلى يحتاج تعديل"""
        updated = queryset.update(status='modification_required')
        self.message_user(request, f'✅ تم تغيير حالة {updated} تركيب إلى "يحتاج تعديل"')
    mark_status_modification_required.short_description = "تغيير الحالة إلى يحتاج تعديل"

    def get_queryset(self, request):
        """تحسين الاستعلامات لتحسين الأداء"""
        return super().get_queryset(request).select_related(
            'order', 'order__customer', 'order__branch', 'team'
        )


@admin.register(ModificationRequest)
class ModificationRequestAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'customer', 'modification_type', 'priority', 'estimated_cost_formatted', 'customer_approval', 'created_at']
    list_filter = ['priority', 'customer_approval', 'created_at']
    search_fields = ['installation__order__order_number', 'customer__name', 'modification_type']
    list_editable = ['priority', 'customer_approval']
    ordering = ['-created_at']

    def estimated_cost_formatted(self, obj):
        return currency_format(obj.estimated_cost)
    estimated_cost_formatted.short_description = 'التكلفة المتوقعة'


@admin.register(ModificationImage)
class ModificationImageAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['modification', 'image_preview', 'description', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['modification__installation__order__order_number', 'description']
    ordering = ['-uploaded_at']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'معاينة الصورة'


# إنشاء admin مخصص لأوامر التصنيع في قسم التركيبات
# سيتم تسجيله يدوياً في نهاية الملف لتجنب التكرار
class InstallationManufacturingOrderAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = [
        'manufacturing_code', 'order_number', 'customer_name', 'order_type_display', 
        'status', 'installation_status_display', 'order_date', 'expected_delivery_date', 'production_line'
    ]
    list_filter = [
        ManufacturingStatusFilter,  # فلتر مخصص لحالة المصنع
        OrderTypeFilter,  # فلتر مخصص لنوع الطلب (من ManufacturingOrder)
        InstallationStatusFilter,  # فلتر مخصص لحالة التركيب
        'order_date',
        'expected_delivery_date',
        ('order__branch', admin.RelatedFieldListFilter),
        ('order__salesperson', admin.RelatedFieldListFilter),
        ('production_line', admin.RelatedFieldListFilter),
    ]

    # إضافة روابط سريعة للفلترة
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        # إضافة روابط سريعة للحالات المختلفة
        extra_context['quick_filters'] = [
            {
                'name': 'يحتاج جدولة',
                'url': '?order__installation_status__exact=needs_scheduling',
                'count': self.get_queryset(request).filter(order__installation_status='needs_scheduling').count()
            },
            {
                'name': 'مجدول',
                'url': '?order__installation_status__exact=scheduled',
                'count': self.get_queryset(request).filter(order__installation_status='scheduled').count()
            },
            {
                'name': 'قيد التركيب',
                'url': '?order__installation_status__exact=in_installation',
                'count': self.get_queryset(request).filter(order__installation_status='in_installation').count()
            },
            {
                'name': 'مكتمل',
                'url': '?order__installation_status__exact=completed',
                'count': self.get_queryset(request).filter(order__installation_status='completed').count()
            },
            {
                'name': 'ملغي',
                'url': '?order__installation_status__exact=cancelled',
                'count': self.get_queryset(request).filter(order__installation_status='cancelled').count()
            },
            {
                'name': 'يحتاج تعديل',
                'url': '?order__installation_status__exact=modification_required',
                'count': self.get_queryset(request).filter(order__installation_status='modification_required').count()
            },
        ]

        # مسح cache إذا كان هناك تحديث
        if request.GET.get('updated') or request.GET.get('_refresh') or request.GET.get('_nocache'):
            from django.core.cache import cache
            cache.clear()

            # مسح cache الـ ORM أيضاً
            from django.db import connection
            if hasattr(connection, 'queries_log'):
                connection.queries_log.clear()

        # إضافة header لمنع caching في المتصفح دائماً
        response = super().changelist_view(request, extra_context)
        if request.GET.get('updated') or request.GET.get('_refresh') or request.GET.get('_nocache'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Last-Modified'] = ''
            response['ETag'] = ''

        return response
    search_fields = [
        'manufacturing_code', 'contract_number', 'invoice_number',
        'order__order_number', 'order__customer__name', 'order__customer__phone'
    ]
    list_editable = ['status', 'production_line']
    ordering = ['-order_date']
    date_hierarchy = 'order_date'
    
    # إضافة إجراءات مجمعة لتغيير الحالة
    actions = [
        # إجراءات حالة أوامر التصنيع
        'mark_manufacturing_pending_approval', 'mark_manufacturing_pending', 'mark_manufacturing_in_progress',
        'mark_manufacturing_ready_install', 'mark_manufacturing_completed', 'mark_manufacturing_delivered',
        'mark_manufacturing_rejected', 'mark_manufacturing_cancelled',
        # إجراءات حالة التركيب
        'mark_installation_needs_scheduling', 'mark_installation_scheduled', 'mark_installation_in_progress',
        'mark_installation_completed', 'mark_installation_cancelled', 'mark_installation_modification_required'
    ]
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('order', 'order_type', 'contract_number', 'invoice_number')
        }),
        ('حالة التصنيع', {
            'fields': ('status', 'production_line', 'order_date', 'expected_delivery_date')
        }),
        ('ملفات', {
            'fields': ('contract_file', 'inspection_file'),
            'classes': ('collapse',)
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def changelist_view(self, request, extra_context=None):
        """تخصيص عرض قائمة التغييرات لضمان إعادة التحميل الصحيح"""
        if extra_context is None:
            extra_context = {}

        # مسح cache إذا كان هناك تحديث
        if request.GET.get('updated') or request.GET.get('_refresh') or request.GET.get('_nocache'):
            from django.core.cache import cache
            cache.clear()

            # مسح cache الـ ORM أيضاً
            from django.db import connection
            if hasattr(connection, 'queries_log'):
                connection.queries_log.clear()

        # إضافة header لمنع caching في المتصفح دائماً
        response = super().changelist_view(request, extra_context)
        if request.GET.get('updated') or request.GET.get('_refresh') or request.GET.get('_nocache'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Last-Modified'] = ''
            response['ETag'] = ''

        return response

    def get_queryset(self, request):
        """تخصيص الـ queryset لضمان الحصول على أحدث البيانات"""
        queryset = super().get_queryset(request)

        # إذا كان هناك تحديث، تجنب الـ cache
        if request.GET.get('updated') or request.GET.get('_refresh') or request.GET.get('_nocache'):
            # إعادة تقييم الـ queryset لضمان الحصول على أحدث البيانات
            queryset = queryset.all()

        return queryset

    def order_number(self, obj):
        """عرض رقم الطلب مع رابط"""
        if obj.order:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                reverse('admin:orders_order_change', args=[obj.order.pk]),
                obj.order.order_number
            )
        return '-'
    order_number.short_description = 'رقم الطلب'
    order_number.admin_order_field = 'order__order_number'

    def customer_name(self, obj):
        """عرض اسم العميل"""
        if obj.order and obj.order.customer:
            return obj.order.customer.name
        return '-'
    customer_name.short_description = 'اسم العميل'
    customer_name.admin_order_field = 'order__customer__name'

    def order_type_display(self, obj):
        """عرض نوع الطلب بألوان"""
        colors = {
            'installation': '#007bff',     # أزرق
            'custom': '#28a745',          # أخضر
            'accessory': '#ffc107',       # أصفر
        }
        color = colors.get(obj.order_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_order_type_display()
        )
    order_type_display.short_description = 'نوع الطلب'

    def status(self, obj):
        """عرض حالة التصنيع بألوان"""
        colors = {
            'pending_approval': '#ffc107',  # أصفر
            'pending': '#6c757d',          # رمادي
            'in_progress': '#007bff',      # أزرق
            'ready_install': '#17a2b8',    # أزرق فاتح
            'completed': '#28a745',        # أخضر
            'delivered': '#20c997',        # أخضر فاتح
            'rejected': '#dc3545',         # أحمر
            'cancelled': '#6c757d',        # رمادي
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_status_display()
        )
    status.short_description = 'الحالة'

    def installation_status_display(self, obj):
        """عرض حالة التركيب بألوان"""
        if not obj.order:
            return '-'
            
        colors = {
            'needs_scheduling': '#fd7e14',           # برتقالي
            'scheduled': '#17a2b8',                  # أزرق فاتح
            'in_installation': '#007bff',            # أزرق
            'completed': '#28a745',                  # أخضر
            'cancelled': '#6c757d',                  # رمادي
            'modification_required': '#ffc107',      # أصفر
            'modification_in_progress': '#e83e8c',   # وردي
            'modification_completed': '#20c997',     # أخضر فاتح
        }
        color = colors.get(obj.order.installation_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.order.get_installation_status_display()
        )
    installation_status_display.short_description = 'حالة التركيب'
    installation_status_display.admin_order_field = 'order__installation_status'

    # إجراءات مجمعة لتغيير الحالة
    def mark_as_pending(self, request, queryset):
        """تغيير الحالة إلى في الانتظار"""
        updated = queryset.update(status='pending')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "في الانتظار"')
    mark_as_pending.short_description = "تغيير الحالة إلى في الانتظار"

    def mark_as_in_progress(self, request, queryset):
        """تغيير الحالة إلى قيد التصنيع"""
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "قيد التصنيع"')
    mark_as_in_progress.short_description = "تغيير الحالة إلى قيد التصنيع"

    def mark_as_ready_install(self, request, queryset):
        """تغيير الحالة إلى جاهز للتركيب"""
        updated = queryset.update(status='ready_install')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "جاهز للتركيب"')
    mark_as_ready_install.short_description = "تغيير الحالة إلى جاهز للتركيب"

    def mark_as_completed(self, request, queryset):
        """تغيير الحالة إلى مكتمل"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "مكتمل"')
    mark_as_completed.short_description = "تغيير الحالة إلى مكتمل"

    def mark_as_delivered(self, request, queryset):
        """تغيير الحالة إلى تم التسليم"""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "تم التسليم"')
    mark_as_delivered.short_description = "تغيير الحالة إلى تم التسليم"

    def get_queryset(self, request):
        """تحسين الاستعلامات لتحسين الأداء - عرض جميع أوامر التصنيع"""
        return super().get_queryset(request).select_related(
            'order', 'order__customer', 'order__branch', 'production_line'
        )



    # دالة مساعدة لتحديث حالة التركيب
    def _update_installation_status(self, request, queryset, new_status, status_display):
        """دالة مساعدة لتحديث حالة التركيب"""
        from installations.models import InstallationSchedule
        from django.db import transaction

        with transaction.atomic():
            # الحصول على الطلبات
            orders = [order.order for order in queryset if order.order]
            order_ids = [order.id for order in orders]

            if order_ids:
                # تحديث حالة التركيب في الطلبات مباشرة
                from orders.models import Order
                Order.objects.filter(id__in=order_ids).update(installation_status=new_status)

                # تحديث أو إنشاء InstallationSchedule
                existing_installations = InstallationSchedule.objects.filter(order_id__in=order_ids)
                existing_order_ids = set(existing_installations.values_list('order_id', flat=True))

                # إنشاء InstallationSchedule للطلبات التي لا تملكها
                new_installations = []
                for order in orders:
                    if order.id not in existing_order_ids:
                        new_installations.append(InstallationSchedule(
                            order=order,
                            status=new_status
                        ))

                if new_installations:
                    InstallationSchedule.objects.bulk_create(new_installations)

                # تحديث الحالات الموجودة
                updated_count = existing_installations.update(status=new_status)
                total_updated = len(new_installations) + updated_count

                # مسح cache
                from django.core.cache import cache
                cache.clear()
            else:
                total_updated = 0

        self.message_user(request, f'✅ تم تغيير حالة التركيب لـ {total_updated} طلب إلى "{status_display}"')
        return total_updated

    # إجراءات تغيير حالة التركيب - محسنة للأداء
    def mark_installation_needs_scheduling(self, request, queryset):
        """تغيير حالة التركيب إلى بحاجة جدولة"""
        self._update_installation_status(request, queryset, 'needs_scheduling', 'بحاجة جدولة')
    mark_installation_needs_scheduling.short_description = "تغيير حالة التركيب إلى بحاجة جدولة"

    def mark_installation_scheduled(self, request, queryset):
        """تغيير حالة التركيب إلى مجدول"""
        self._update_installation_status(request, queryset, 'scheduled', 'مجدول')
    mark_installation_scheduled.short_description = "تغيير حالة التركيب إلى مجدول"

    def mark_installation_in_progress(self, request, queryset):
        """تغيير حالة التركيب إلى قيد التركيب"""
        self._update_installation_status(request, queryset, 'in_installation', 'قيد التركيب')
    mark_installation_in_progress.short_description = "تغيير حالة التركيب إلى قيد التركيب"

    def mark_installation_completed(self, request, queryset):
        """تغيير حالة التركيب إلى مكتمل"""
        self._update_installation_status(request, queryset, 'completed', 'مكتمل')
    mark_installation_completed.short_description = "تغيير حالة التركيب إلى مكتمل"

    def mark_installation_cancelled(self, request, queryset):
        """تغيير حالة التركيب إلى ملغي"""
        self._update_installation_status(request, queryset, 'cancelled', 'ملغي')
    mark_installation_cancelled.short_description = "تغيير حالة التركيب إلى ملغي"

    def mark_installation_modification_required(self, request, queryset):
        """تغيير حالة التركيب إلى يحتاج تعديل"""
        self._update_installation_status(request, queryset, 'modification_required', 'يحتاج تعديل')
    mark_installation_modification_required.short_description = "تغيير حالة التركيب إلى يحتاج تعديل"

    # إجراءات تحديث حالات أوامر التصنيع
    def mark_manufacturing_pending_approval(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى قيد الموافقة"""
        updated = queryset.update(status='pending_approval')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "قيد الموافقة"')
    mark_manufacturing_pending_approval.short_description = "تغيير حالة التصنيع إلى قيد الموافقة"

    def mark_manufacturing_pending(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى قيد الانتظار"""
        updated = queryset.update(status='pending')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "قيد الانتظار"')
    mark_manufacturing_pending.short_description = "تغيير حالة التصنيع إلى قيد الانتظار"

    def mark_manufacturing_in_progress(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى قيد التصنيع"""
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "قيد التصنيع"')
    mark_manufacturing_in_progress.short_description = "تغيير حالة التصنيع إلى قيد التصنيع"

    def mark_manufacturing_ready_install(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى جاهز للتركيب"""
        updated = queryset.update(status='ready_install')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "جاهز للتركيب"')
    mark_manufacturing_ready_install.short_description = "تغيير حالة التصنيع إلى جاهز للتركيب"

    def mark_manufacturing_completed(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى مكتمل"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "مكتمل"')
    mark_manufacturing_completed.short_description = "تغيير حالة التصنيع إلى مكتمل"

    def mark_manufacturing_delivered(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى تم التسليم"""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "تم التسليم"')
    mark_manufacturing_delivered.short_description = "تغيير حالة التصنيع إلى تم التسليم"

    def mark_manufacturing_rejected(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى مرفوض"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "مرفوض"')
    mark_manufacturing_rejected.short_description = "تغيير حالة التصنيع إلى مرفوض"

    def mark_manufacturing_cancelled(self, request, queryset):
        """تغيير حالة أمر التصنيع إلى ملغي"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'✅ تم تغيير حالة {updated} أمر تصنيع إلى "ملغي"')
    mark_manufacturing_cancelled.short_description = "تغيير حالة التصنيع إلى ملغي"


# إزالة تسجيل نموذج أوامر التعديل - سنستخدم admin مخصص لـ manufacturing.models.ManufacturingOrder
# @admin.register(InstallationManufacturingOrder)
class ModificationManufacturingOrderAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'order_number', 'customer_name', 'order_type', 'status', 
        'assigned_to', 'estimated_completion', 'created_at'
    ]
    list_filter = [
        'order_type', 'status', 'assigned_to', 'created_at',
        ('modification_request__installation__order__order_date', admin.DateFieldListFilter),
        ('modification_request__installation__order__branch', admin.RelatedFieldListFilter),
    ]
    search_fields = [
        'modification_request__installation__order__order_number', 
        'modification_request__installation__order__customer__name', 
        'modification_request__installation__order__customer__phone',
        'modification_request__installation__order__order_number'
    ]
    list_editable = ['status', 'assigned_to']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    # إضافة إجراءات مجمعة لتغيير الحالة
    actions = ['mark_as_pending', 'mark_as_in_progress', 'mark_as_completed', 'mark_as_delivered']
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('modification_request', 'order_type')
        }),
        ('حالة التصنيع', {
            'fields': ('status', 'assigned_to', 'estimated_completion_date')
        }),
        ('ملاحظات', {
            'fields': ('description', 'manager_notes'),
            'classes': ('collapse',)
        }),
    )

    def order_number(self, obj):
        """عرض رقم الطلب مع رابط"""
        if obj.modification_request and obj.modification_request.installation and obj.modification_request.installation.order:
            order = obj.modification_request.installation.order
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                reverse('admin:orders_order_change', args=[order.pk]),
                order.order_number
            )
        return '-'
    order_number.short_description = 'رقم الطلب'
    order_number.admin_order_field = 'modification_request__installation__order__order_number'

    def customer_name(self, obj):
        """عرض اسم العميل"""
        if obj.modification_request and obj.modification_request.installation and obj.modification_request.installation.order and obj.modification_request.installation.order.customer:
            return obj.modification_request.installation.order.customer.name
        return '-'
    customer_name.short_description = 'اسم العميل'
    customer_name.admin_order_field = 'modification_request__installation__order__customer__name'

    def status(self, obj):
        """عرض حالة التصنيع بألوان"""
        colors = {
            'pending': '#ffc107',         # أصفر
            'in_progress': '#007bff',     # أزرق
            'completed': '#28a745',       # أخضر
            'delivered': '#20c997',       # أخضر فاتح
            'cancelled': '#dc3545',       # أحمر
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_status_display()
        )
    status.short_description = 'الحالة'

    def estimated_completion(self, obj):
        """عرض تاريخ الإكمال المتوقع"""
        if obj.estimated_completion_date:
            return obj.estimated_completion_date.strftime('%Y-%m-%d')
        return '-'
    estimated_completion.short_description = 'تاريخ الإكمال المتوقع'
    estimated_completion.admin_order_field = 'estimated_completion_date'

    # إجراءات مجمعة لتغيير الحالة
    def mark_as_pending(self, request, queryset):
        """تغيير الحالة إلى في الانتظار"""
        updated = queryset.update(status='pending')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "في الانتظار"')
    mark_as_pending.short_description = "تغيير الحالة إلى في الانتظار"

    def mark_as_in_progress(self, request, queryset):
        """تغيير الحالة إلى قيد التنفيذ"""
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "قيد التنفيذ"')
    mark_as_in_progress.short_description = "تغيير الحالة إلى قيد التنفيذ"

    def mark_as_completed(self, request, queryset):
        """تغيير الحالة إلى مكتمل"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "مكتمل"')
    mark_as_completed.short_description = "تغيير الحالة إلى مكتمل"

    def mark_as_delivered(self, request, queryset):
        """تغيير الحالة إلى تم التسليم"""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'تم تغيير حالة {updated} أمر تصنيع إلى "تم التسليم"')
    mark_as_delivered.short_description = "تغيير الحالة إلى تم التسليم"

    def get_queryset(self, request):
        """تحسين الاستعلامات لتحسين الأداء"""
        return super().get_queryset(request).select_related(
            'modification_request__installation__order__customer',
            'modification_request__installation__order__branch',
            'assigned_to'
        ).prefetch_related('modification_request__installation')


@admin.register(ModificationReport)
class ModificationReportAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['modification_request', 'manufacturing_order', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['modification_request__installation__order__order_number', 'description']
    ordering = ['-created_at']


@admin.register(ReceiptMemo)
class ReceiptMemoAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'receipt_image_preview', 'customer_signature', 'amount_received_formatted', 'created_at']
    list_filter = ['customer_signature', 'created_at']
    search_fields = ['installation__order__order_number']
    ordering = ['-created_at']

    def receipt_image_preview(self, obj):
        if obj.receipt_image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.receipt_image.url
            )
        return '-'
    receipt_image_preview.short_description = 'صورة المذكرة'

    def amount_received_formatted(self, obj):
        return currency_format(obj.amount_received)
    amount_received_formatted.short_description = 'المبلغ المستلم'


@admin.register(InstallationPayment)
class InstallationPaymentAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'payment_type', 'amount_formatted', 'payment_method', 'created_at']
    list_filter = ['payment_type', 'payment_method', 'created_at']
    search_fields = ['installation__order__order_number', 'receipt_number']
    ordering = ['-created_at']

    def amount_formatted(self, obj):
        return currency_format(obj.amount)
    amount_formatted.short_description = 'المبلغ'


@admin.register(InstallationArchive)
class InstallationArchiveAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'completion_date', 'archived_by']
    list_filter = ['completion_date', 'archived_by']
    search_fields = ['installation__order__order_number']
    ordering = ['-completion_date']
    readonly_fields = ['completion_date', 'archived_by']


@admin.register(InstallationAnalytics)
class InstallationAnalyticsAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['month', 'total_installations', 'completed_installations', 'total_customers', 
                   'total_modifications', 'completion_rate', 'modification_rate']
    list_filter = ['month']
    search_fields = ['month']
    readonly_fields = ['completion_rate', 'modification_rate']
    
    def save_model(self, request, obj, form, change):
        obj.calculate_rates()
        super().save_model(request, obj, form, change)


@admin.register(ModificationErrorAnalysis)
class ModificationErrorAnalysisAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['modification_request', 'error_type', 'cost_impact_formatted', 'time_impact_hours', 'created_at']
    list_filter = ['error_type', 'created_at']
    search_fields = ['modification_request__installation__order__order_number', 'error_description']
    readonly_fields = ['created_at', 'updated_at']

    def cost_impact_formatted(self, obj):
        return currency_format(obj.cost_impact)
    cost_impact_formatted.short_description = 'التأثير المالي'


@admin.register(ModificationErrorType)
class ModificationErrorTypeAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']


# تسجيل admin مخصص لأوامر التصنيع في قسم التركيبات
# إزالة admin الأصلي من manufacturing
try:
    admin.site.unregister(ManufacturingOrder)
except admin.sites.NotRegistered:
    pass

# تسجيل admin مخصص في قسم التركيبات
admin.site.register(ManufacturingOrder, InstallationManufacturingOrderAdmin)

# تخصيص عنوان لوحة الإدارة
admin.site.site_header = "إدارة التركيبات - نظام الخواجه"
admin.site.site_title = "إدارة التركيبات"
admin.site.index_title = "مرحباً بك في إدارة التركيبات"
