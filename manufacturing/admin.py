from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

from .models import (
    ManufacturingOrder, ManufacturingOrderItem
)


class ManufacturingOrderItemInline(admin.TabularInline):
    model = ManufacturingOrderItem
    extra = 1
    fields = ('product_name', 'quantity', 'specifications', 'status')
    readonly_fields = ('status',)


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_max_show_all = 100  # السماح بعرض حتى 100 صف عند اختيار "عرض الكل"
    show_full_result_count = False  # تعطيل عدد النتائج لتحسين الأداء
    
    # إعادة جميع الأعمدة المهمة كما كانت
    list_display = [
        'manufacturing_code',
        'contract_number',
        'order_type_display',
        'customer_name',
        'status_display',
        'rejection_reply_status',
        'order_date',
        'expected_delivery_date',
        'exit_permit_display',
        'delivery_info',
        'created_at',
    ]
    
    # تمكين الترتيب الديناميكي لجميع الأعمدة
    def get_sortable_by(self, request):
        """تمكين الترتيب لجميع الأعمدة المعروضة"""
        return self.list_display
    
    # تحديد الحقول القابلة للترتيب بوضوح
    sortable_by = [
        'id',  # للترتيب حسب manufacturing_code
        'contract_number',
        'order_type',
        'order__customer__name',  # للترتيب حسب اسم العميل
        'status',  # تمكين ترتيب الحالة
        'has_rejection_reply',
        'order_date',
        'expected_delivery_date',
        'delivery_permit_number',
        'delivery_date',
        'created_at',
    ]
    
    # تحديد أولوية الترتيب الافتراضي
    ordering = ['-id']  # استخدام id بدلاً من created_at
    
    # تخصيص الحقول القابلة للنقر للانتقال لصفحة التحرير
    list_display_links = ['manufacturing_code']
    
    # إعادة البحث الشامل
    search_fields = [
        'order__order_number',
        'order__customer__name',  # إضافة البحث باسم العميل
        'contract_number',
        'invoice_number',
        'exit_permit_number',
        'delivery_permit_number',
        'delivery_recipient_name',
    ]
    
    # إعادة الفلاتر الأصلية
    list_filter = [
        'status',
        'order_type',
        'order_date',
        'expected_delivery_date',
        'delivery_date',
        'has_rejection_reply',
    ]
    
    # إعادة date_hierarchy
    date_hierarchy = 'created_at'
    
    # ترتيب محسن
    ordering = ['-id']  # استخدام id بدلاً من created_at

    # تم تبسيط الفلاتر
    # list_filter = (
    #     'status',
    #     'order_type',
    #     'order_date',
    #     'expected_delivery_date',
    #     'delivery_date',
    #     'has_rejection_reply',
    # )

    # تم تبسيط البحث
    # search_fields = (
    #     'order__order_number',
    #     'order__customer__name',  # إضافة البحث باسم العميل
    #     'contract_number',
    #     'invoice_number',
    #     'exit_permit_number',
    #     'delivery_permit_number',
    #     'delivery_recipient_name',
    # )

    readonly_fields = (
        'created_at', 'updated_at', 'completion_date', 'delivery_date',
        'rejection_reply_date', 'has_rejection_reply'
    )
    inlines = [ManufacturingOrderItemInline]
    date_hierarchy = 'created_at'

    actions = ['bulk_update_status']

    def bulk_update_status(self, request, queryset):
        from django import forms
        from django.shortcuts import render, redirect
        class StatusForm(forms.Form):
            status = forms.ChoiceField(choices=queryset.model.STATUS_CHOICES, label='الحالة الجديدة')

        if 'apply' in request.POST:
            form = StatusForm(request.POST)
            if form.is_valid():
                new_status = form.cleaned_data['status']
                count = queryset.update(status=new_status)
                self.message_user(request, f'تم تحديث حالة {count} أمر تصنيع إلى {dict(queryset.model.STATUS_CHOICES)[new_status]} بنجاح.')
                return None
        else:
            form = StatusForm()
        return render(request, 'admin/bulk_update_status.html', {
            'orders': queryset,
            'form': form,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })
    bulk_update_status.short_description = 'تبديل حالة الأوامر المحددة جماعياً'

    fieldsets = (
        ('معلومات الطلب الأساسية', {
            'fields': (
                'order',
                'contract_number',
                'invoice_number',
                'order_type',
                'order_date',
                'expected_delivery_date',
            )
        }),
        ('حالة التصنيع', {
            'fields': (
                'status',
                'exit_permit_number',
                'notes',
            )
        }),
        ('معلومات الرفض (إن وجدت)', {
            'fields': (
                'rejection_reason',
                'rejection_reply',
                'rejection_reply_date',
                'has_rejection_reply',
            ),
            'classes': ('collapse',),
        }),
        ('معلومات التسليم', {
            'fields': (
                'delivery_permit_number',
                'delivery_recipient_name',
                'delivery_date',
            ),
            'classes': ('collapse',),
        }),
        ('الملفات', {
            'fields': (
                'contract_file',
                'inspection_file',
            ),
            'classes': ('collapse',),
        }),
        ('التواريخ', {
            'fields': (
                'completion_date',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def customer_name(self, obj):
        """عرض اسم العميل بطريقة محسنة"""
        # استخدام البيانات المحملة مسبقاً أولاً
        if hasattr(obj, '_customer_name') and obj._customer_name:
            return obj._customer_name
        
        # الطريقة التقليدية كـ fallback
        if obj.order and obj.order.customer:
            return obj.order.customer.name
        
        return "-"
    customer_name.short_description = 'العميل'
    customer_name.admin_order_field = 'order__customer__name'  # تمكين الترتيب

    def contract_number(self, obj):
        """عرض رقم العقد"""
        if hasattr(obj, '_contract_number') and obj._contract_number:
            return obj._contract_number
        return obj.contract_number or '-'
    contract_number.short_description = 'رقم العقد'
    contract_number.admin_order_field = 'contract_number'  # تمكين الترتيب

    def exit_permit_display(self, obj):
        """عرض رقم إذن التسليم (رقم إذن الخروج)"""
        return obj.delivery_permit_number or '-'
    exit_permit_display.short_description = 'رقم إذن الخروج'
    exit_permit_display.admin_order_field = 'delivery_permit_number'  # تمكين الترتيب

    def order_type_display(self, obj):
        """عرض نوع الطلب محسن"""
        # استخدام البيانات المحملة مسبقاً إذا كانت متوفرة
        if hasattr(obj, '_order_type') and obj._order_type:
            type_map = {
                'installation': '🔧 تركيب',
                'detail': '✂️ تفصيل', 
                'accessory': '💎 إكسسوار',
                'inspection': '👁️ معاينة'
            }
            return type_map.get(obj._order_type, obj._order_type)
        
        # الطريقة التقليدية كـ fallback
        if obj.order:
            selected_types = obj.order.get_selected_types_list()
            if selected_types:
                type_map = {
                    'installation': '🔧 تركيب',
                    'tailoring': '✂️ تفصيل', 
                    'accessory': '💎 إكسسوار',
                    'inspection': '👁️ معاينة'
                }
                type_names = [type_map.get(t, t) for t in selected_types]
                return ', '.join(type_names)
        return obj.get_order_type_display()
    order_type_display.short_description = 'نوع الطلب'
    order_type_display.admin_order_field = 'order_type'  # تمكين الترتيب

    def order_date(self, obj):
        """عرض تاريخ الطلب"""
        if hasattr(obj, '_order_date') and obj._order_date:
            return obj._order_date.strftime('%Y-%m-%d') if obj._order_date else '-'
        return obj.order_date.strftime('%Y-%m-%d') if obj.order_date else '-'
    order_date.short_description = 'تاريخ الطلب'
    order_date.admin_order_field = 'order_date'  # تمكين الترتيب

    def expected_delivery_date(self, obj):
        """عرض تاريخ التسليم المتوقع"""
        if hasattr(obj, '_expected_delivery_date') and obj._expected_delivery_date:
            return obj._expected_delivery_date.strftime('%Y-%m-%d') if obj._expected_delivery_date else '-'
        return obj.expected_delivery_date.strftime('%Y-%m-%d') if obj.expected_delivery_date else '-'
    expected_delivery_date.short_description = 'التسليم المتوقع'
    expected_delivery_date.admin_order_field = 'expected_delivery_date'  # تمكين الترتيب

    def status_display(self, obj):
        """عرض حالة الطلب بألوان واضحة"""
        colors = {
            'pending_approval': '#0056b3',  # أزرق غامق
            'pending': '#e6a700',          # أصفر
            'in_progress': '#138496',       # أزرق فاتح
            'ready_install': '#6f42c1',     # بنفسجي
            'completed': '#1e7e34',         # أخضر
            'delivered': '#20c997',         # أخضر فاتح
            'rejected': '#c82333',          # أحمر
            'cancelled': '#545b62',         # رمادي
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 12px; white-space: nowrap;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'
    status_display.admin_order_field = 'status'  # تمكين الترتيب

    def delivery_info(self, obj):
        """عرض معلومات التسليم - اسم المستلم والتاريخ"""
        if obj.status == 'delivered':
            # استخدام البيانات المحملة مسبقاً
            recipient = (hasattr(obj, '_delivery_recipient_name') and obj._delivery_recipient_name) or obj.delivery_recipient_name or '-'
            date_obj = (hasattr(obj, '_delivery_date') and obj._delivery_date) or obj.delivery_date
            date = date_obj.strftime('%Y-%m-%d') if date_obj else '-'
            
            return format_html(
                '<div style="text-align: right;">'
                '<strong>المستلم:</strong> {}<br>'
                '<strong>التاريخ:</strong> {}'
                '</div>',
                recipient,
                date
            )
        return "-"
    delivery_info.short_description = 'معلومات التسليم'
    delivery_info.admin_order_field = 'delivery_date'  # تمكين الترتيب

    def rejection_reply_status(self, obj):
        """عرض حالة الرد على الرفض"""
        if obj.status == 'rejected':
            # استخدام البيانات المحملة مسبقاً
            has_reply = (hasattr(obj, '_has_rejection_reply') and obj._has_rejection_reply) or obj.has_rejection_reply
            
            if has_reply:
                return format_html(
                    '<span style="background-color: #007bff; color: white; padding: 2px 6px; '
                    'border-radius: 8px; font-size: 11px;">✅ تم الرد</span>'
                )
            else:
                return format_html(
                    '<span style="background-color: #dc3545; color: white; padding: 2px 6px; '
                    'border-radius: 8px; font-size: 11px;">❌ لم يتم الرد</span>'
                )
        return "-"
    rejection_reply_status.short_description = 'حالة الرد'
    rejection_reply_status.admin_order_field = 'has_rejection_reply'  # تمكين الترتيب

    def created_at(self, obj):
        """عرض تاريخ الإنشاء"""
        created_date = (hasattr(obj, '_created_at') and obj._created_at) or obj.created_at
        return created_date.strftime('%Y-%m-%d %H:%M') if created_date else '-'
    created_at.short_description = 'تاريخ الإنشاء'
    created_at.admin_order_field = 'created_at'  # تمكين الترتيب

    def get_urls(self):
        """إضافة URLs مخصصة للوصول لأوامر التصنيع باستخدام الكود"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'by-code/<str:manufacturing_code>/',
                self.admin_site.admin_view(self.manufacturing_order_by_code_view),
                name='manufacturing_manufacturingorder_by_code',
            ),
        ]
        return custom_urls + urls

    def manufacturing_order_by_code_view(self, request, manufacturing_code):
        """عرض أمر التصنيع باستخدام الكود وإعادة التوجيه لصفحة التحرير"""
        try:
            # البحث باستخدام order_number إذا كان يحتوي على رقم الطلب
            if manufacturing_code.endswith('-M'):
                base_code = manufacturing_code[:-2]  # إزالة '-M'
                if base_code.startswith('#'):
                    # البحث باستخدام ID مباشرة
                    manufacturing_id = base_code[1:]  # إزالة '#'
                    manufacturing_order = self.model.objects.get(id=manufacturing_id)
                else:
                    # البحث باستخدام order_number
                    manufacturing_order = self.model.objects.get(order__order_number=base_code)
            else:
                # محاولة البحث المباشر بالكود
                manufacturing_order = self.model.objects.get(id=manufacturing_code)
                
            return HttpResponseRedirect(
                reverse('admin:manufacturing_manufacturingorder_change', args=[manufacturing_order.pk])
            )
        except (self.model.DoesNotExist, ValueError):
            self.message_user(request, f'أمر التصنيع بكود {manufacturing_code} غير موجود', level='error')
            return HttpResponseRedirect(reverse('admin:manufacturing_manufacturingorder_changelist'))

    def manufacturing_code(self, obj):
        """عرض رقم طلب التصنيع الموحد مع روابط محسنة - تحديث للاستخدام الكود في admin"""
        code = obj.manufacturing_code
        
        try:
            # رابط عرض أمر التصنيع في الواجهة
            view_url = reverse('manufacturing:order_detail_by_code', args=[code])
            # رابط تحرير أمر التصنيع في لوحة التحكم باستخدام الكود
            admin_url = reverse('admin:manufacturing_manufacturingorder_by_code', kwargs={'manufacturing_code': code})
            
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
    manufacturing_code.short_description = 'رقم طلب التصنيع'
    manufacturing_code.admin_order_field = 'id'  # تمكين الترتيب حسب ID

    def get_queryset(self, request):
        """استعلام محسن للحصول على جميع البيانات المطلوبة"""
        # بدلاً من SQL مخصص، نستخدم Django ORM محسن
        qs = super().get_queryset(request).select_related(
            'order', 'order__customer', 'created_by'
        ).prefetch_related(
            'items'
        )
        
        # إضافة البيانات المحملة مسبقاً لتحسين الأداء
        for obj in qs:
            if obj.order:
                obj._order_number = obj.order.order_number
                obj._customer_name = obj.order.customer.name if obj.order.customer else None
            obj._contract_number = obj.contract_number
            obj._order_type = obj.order_type
            obj._order_date = obj.order_date
            obj._expected_delivery_date = obj.expected_delivery_date
            obj._created_at = obj.created_at
            obj._delivery_permit_number = obj.delivery_permit_number
            obj._delivery_recipient_name = obj.delivery_recipient_name
            obj._delivery_date = obj.delivery_date
            obj._has_rejection_reply = obj.has_rejection_reply
        
        return qs

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'pending_approval':
            # Only users with approval permission can change pending_approval
            return (request.user.has_perm('manufacturing.can_approve_orders')
                    or request.user.is_superuser)
        return super().has_change_permission(request, obj)


@admin.register(ManufacturingOrderItem)
class ManufacturingOrderItemAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ('manufacturing_order', 'product_name', 'quantity', 'status')
    list_filter = ('status',)
    search_fields = ('manufacturing_order__id', 'product_name')

# The user management code has been moved to accounts/admin.py
