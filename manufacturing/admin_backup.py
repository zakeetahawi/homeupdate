from django import forms
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    ManufacturingDisplaySettings,
    ManufacturingOrder,
    ManufacturingOrderItem,
    ProductionLine,
)


class ProductionLineForm(forms.ModelForm):
    """نموذج مخصص لخط الإنتاج مع widget لأنواع الطلبات"""

    supported_order_types = forms.MultipleChoiceField(
        choices=ProductionLine.ORDER_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='أنواع الطلبات المدعومة',
        help_text='حدد أنواع الطلبات التي يمكن لهذا الخط التعامل معها (اتركه فارغاً لدعم جميع الأنواع)'
    )

    class Meta:
        model = ProductionLine
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.supported_order_types:
            self.fields['supported_order_types'].initial = self.instance.supported_order_types

    def save(self, commit=True):
        instance = super().save(commit=False)
        # تحويل القائمة إلى JSON
        instance.supported_order_types = self.cleaned_data.get('supported_order_types', [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ManufacturingOrderItemInline(admin.TabularInline):
    model = ManufacturingOrderItem
    extra = 0
    fields = ('product_name', 'quantity', 'status')
    readonly_fields = ('status',)


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_per_page = 25  # عرض 50 صف كافتراضي
    list_max_show_all = 100  # السماح بعرض حتى 100 صف عند اختيار "عرض الكل"
    show_full_result_count = False  # تعطيل عدد النتائج لتحسين الأداء
    list_display = [
        'manufacturing_code',
        'contract_number',
        'order_type_display',
        'customer_name',
        'status_display',
        'order_date',
        'expected_delivery_date',
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
        'production_line__name',  # للترتيب حسب خط الإنتاج
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
    # inlines = [ManufacturingOrderItemInline]  # معطل مؤقتاً لتحسين الأداء
    date_hierarchy = 'created_at'

    actions = ['bulk_update_status']

    def bulk_update_status(self, request, queryset):
        from django import forms
        from django.shortcuts import redirect, render
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
                'order_type',
                'status',
            )
        }),
    )

    def customer_name(self, obj):
        """عرض اسم العميل"""
        # استخدام البيانات المحملة مسبقاً أولاً
        if hasattr(obj, '_customer_name') and obj._customer_name:
            return obj._customer_name

        # الطريقة التقليدية كـ fallback
        if obj.order and obj.order.customer:
            return obj.order.customer.name

        return "-"
    customer_name.short_description = 'العميل'
    customer_name.admin_order_field = 'order__customer__name'

    def production_line_display(self, obj):
        """عرض خط الإنتاج"""
        if obj.production_line:
            return format_html(
                '<span style="background: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 12px; font-size: 0.85em;">'
                '<i class="fas fa-industry me-1"></i>{}</span>',
                obj.production_line.name
            )
        return format_html(
            '<span style="color: #999; font-style: italic;">غير محدد</span>'
        )
    production_line_display.short_description = 'خط الإنتاج'
    production_line_display.admin_order_field = 'production_line__name'  # تمكين الترتيب

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
                    manufacturing_order = self.model.objects.select_related('order').get(id=manufacturing_id)
                else:
                    # البحث باستخدام order_number
                    manufacturing_order = self.model.objects.select_related('order', 'order__customer').get(order__order_number=base_code)
            else:
                # محاولة البحث المباشر بالكود
                manufacturing_order = self.model.objects.select_related('order').get(id=manufacturing_code)
                
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
        """استعلام محسن للغاية - تحديد الحقول المطلوبة فقط"""
        return super().get_queryset(request).select_related(
            'order', 
            'order__customer', 
            'production_line',
            'created_by'
        ).defer(
            'notes', 'rejection_reason', 'rejection_reply'
        )

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


@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    """إدارة خطوط الإنتاج"""

    form = ProductionLineForm
    list_per_page = 20

    list_display = [
        'name',
        'is_active',
        'priority',
        'get_branches_display',
        'get_supported_order_types_display',
        'orders_count',
        'active_orders_count',
        'capacity_per_day',
        'created_by',
        'created_at'
    ]

    list_filter = [
        'is_active',
        'priority',
        'branches',
        'created_at',
        'created_by'
    ]

    search_fields = [
        'name',
        'description',
        'branches__name'
    ]

    ordering = ['-priority', 'name']

    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'is_active', 'priority')
        }),
        ('الفروع المرتبطة', {
            'fields': ('branches',),
            'description': 'حدد الفروع التي يخدمها هذا الخط'
        }),
        ('أنواع الطلبات المدعومة', {
            'fields': ('supported_order_types',),
            'description': 'حدد أنواع الطلبات التي يمكن لهذا الخط التعامل معها (اتركه فارغاً لدعم جميع الأنواع)'
        }),
        ('إعدادات الإنتاج', {
            'fields': ('capacity_per_day',),
            'description': 'إعدادات الطاقة الإنتاجية (اختياري)'
        }),
    )

    filter_horizontal = ['branches']

    def save_model(self, request, obj, form, change):
        """حفظ النموذج مع تسجيل المستخدم المنشئ"""
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_branches_display(self, obj):
        """عرض الفروع المرتبطة"""
        return obj.get_branches_display()
    get_branches_display.short_description = 'الفروع المرتبطة'

    def get_supported_order_types_display(self, obj):
        """عرض أنواع الطلبات المدعومة"""
        return obj.get_supported_order_types_display()
    get_supported_order_types_display.short_description = 'أنواع الطلبات المدعومة'


class ManufacturingDisplaySettingsForm(forms.ModelForm):
    """نموذج مخصص لإعدادات عرض التصنيع"""

    class Meta:
        model = ManufacturingDisplaySettings
        fields = '__all__'
        widgets = {
            'allowed_statuses': forms.CheckboxSelectMultiple(
                choices=ManufacturingOrder.STATUS_CHOICES
            ),
            'allowed_order_types': forms.CheckboxSelectMultiple(
                choices=ManufacturingOrder.ORDER_TYPE_CHOICES
            ),
            'target_users': forms.CheckboxSelectMultiple(),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تخصيص عرض الحقول
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})
        self.fields['priority'].widget.attrs.update({'class': 'form-control'})

        # إضافة تلميحات مفيدة
        self.fields['allowed_statuses'].help_text = 'اختر الحالات التي تريد عرضها. إذا لم تختر أي حالة، ستُعرض جميع الحالات.'
        self.fields['allowed_order_types'].help_text = 'اختر أنواع الطلبات التي تريد عرضها. إذا لم تختر أي نوع، ستُعرض جميع الأنواع.'
        self.fields['target_users'].help_text = 'اختر المستخدمين الذين ينطبق عليهم هذا الإعداد. يمكنك أيضاً اختيار "تطبيق على جميع المستخدمين".'

        # تحديد المستخدمين النشطين فقط
        from accounts.models import User
        self.fields['target_users'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')

        # التأكد من أن القوائم ليست None
        if self.instance and self.instance.pk:
            if self.instance.allowed_statuses is None:
                self.instance.allowed_statuses = []
            if self.instance.allowed_order_types is None:
                self.instance.allowed_order_types = []

    def clean(self):
        cleaned_data = super().clean()
        apply_to_all = cleaned_data.get('apply_to_all_users')
        target_users = cleaned_data.get('target_users')

        # التحقق من أن المستخدم اختار إما "جميع المستخدمين" أو مستخدمين محددين
        if not apply_to_all and not target_users:
            raise forms.ValidationError(
                'يجب اختيار إما "تطبيق على جميع المستخدمين" أو تحديد مستخدمين محددين.'
            )

        # التأكد من أن القوائم ليست None
        if cleaned_data.get('allowed_statuses') is None:
            cleaned_data['allowed_statuses'] = []

        if cleaned_data.get('allowed_order_types') is None:
            cleaned_data['allowed_order_types'] = []

        return cleaned_data


@admin.register(ManufacturingDisplaySettings)
class ManufacturingDisplaySettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات عرض طلبات التصنيع"""

    form = ManufacturingDisplaySettingsForm
    list_per_page = 20

    list_display = [
        'name',
        'is_active',
        'priority',
        'get_allowed_statuses_display',
        'get_allowed_order_types_display',
        'get_target_users_display',
        'created_by',
        'created_at'
    ]

    list_filter = [
        'is_active',
        'apply_to_all_users',
        'priority',
        'created_at',
        'created_by'
    ]

    search_fields = [
        'name',
        'description',
        'target_users__username',
        'target_users__first_name',
        'target_users__last_name'
    ]

    ordering = ['-priority', '-created_at']

    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'description', 'is_active', 'priority')
        }),
        ('إعدادات الفلترة', {
            'fields': ('allowed_statuses', 'allowed_order_types'),
            'description': 'حدد الحالات وأنواع الطلبات التي تريد عرضها. إذا تركت الحقل فارغاً، ستُعرض جميع الخيارات.'
        }),
        ('المستخدمون المستهدفون', {
            'fields': ('apply_to_all_users', 'target_users'),
            'description': 'حدد المستخدمين الذين ينطبق عليهم هذا الإعداد.'
        }),
    )

    filter_horizontal = ['target_users']

    def has_module_permission(self, request):
        """التحقق من صلاحية الوصول للوحدة - للمديرين فقط"""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """التحقق من صلاحية العرض - للمديرين فقط"""
        return request.user.is_superuser

    def has_add_permission(self, request):
        """التحقق من صلاحية الإضافة - للمديرين فقط"""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """التحقق من صلاحية التعديل - للمديرين فقط"""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """التحقق من صلاحية الحذف - للمديرين فقط"""
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        """حفظ النموذج مع تسجيل المستخدم المنشئ"""
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_allowed_statuses_display(self, obj):
        """عرض الحالات المسموحة"""
        return obj.get_allowed_statuses_display()
    get_allowed_statuses_display.short_description = 'الحالات المسموحة'

    def get_allowed_order_types_display(self, obj):
        """عرض أنواع الطلبات المسموحة"""
        return obj.get_allowed_order_types_display()
    get_allowed_order_types_display.short_description = 'أنواع الطلبات المسموحة'

    def get_target_users_display(self, obj):
        """عرض المستخدمين المستهدفين"""
        return obj.get_target_users_display()
    get_target_users_display.short_description = 'المستخدمون المستهدفون'

    def orders_count(self, obj):
        """عرض عدد الطلبات الإجمالي"""
        return obj.orders_count
    orders_count.short_description = 'إجمالي الطلبات'

    def active_orders_count(self, obj):
        """عرض عدد الطلبات النشطة"""
        return obj.active_orders_count
    active_orders_count.short_description = 'الطلبات النشطة'
