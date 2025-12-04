from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django import forms
from core.admin_mixins import OptimizedAdminMixin
from .models import (
    Customer, CustomerCategory, CustomerNote, CustomerType,
    DiscountType, CustomerResponsible, get_customer_types
)



class CustomerAdminForm(forms.ModelForm):
    """نموذج مخصص لإدارة العملاء مع قائمة منسدلة ديناميكية لأنواع العملاء"""
    
    customer_type = forms.ChoiceField(
        label=_('نوع العميل'),
        choices=[],
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحديث خيارات نوع العميل ديناميكياً
        customer_types = get_customer_types()
        self.fields['customer_type'].choices = customer_types
        
        # إذا كان هناك instance موجود، تعيين القيمة الحالية
        if self.instance and self.instance.pk:
            self.fields['customer_type'].initial = self.instance.customer_type
    
    def clean_customer_type(self):
        """التحقق من صحة نوع العميل"""
        customer_type = self.cleaned_data.get('customer_type')
        valid_choices = [choice[0] for choice in get_customer_types()]
        
        if customer_type not in valid_choices:
            raise forms.ValidationError(
                f'نوع العميل "{customer_type}" غير صحيح. الخيارات المتاحة: {valid_choices}'
            )
        
        return customer_type
        
    class Meta:
        model = Customer
        fields = '__all__'


@admin.register(CustomerCategory)
class CustomerCategoryAdmin(OptimizedAdminMixin, admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']


@admin.register(CustomerNote)
class CustomerNoteAdmin(OptimizedAdminMixin, admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['customer', 'note_preview', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['customer__name', 'note', 'created_by__username']
    readonly_fields = ['created_by', 'created_at']

    def note_preview(self, obj):
        return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
    note_preview.short_description = _('الملاحظة')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CustomerType)
class CustomerTypeAdmin(OptimizedAdminMixin, admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['code', 'name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at']
    ordering = ['name']


class CustomerResponsibleInline(admin.TabularInline):
    """إدارة مسؤولي العملاء كـ inline"""
    model = CustomerResponsible
    extra = 1
    max_num = 3
    fields = ['name', 'position', 'phone', 'email', 'is_primary', 'order']
    ordering = ['order', 'name']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        # إضافة validation للتأكد من وجود مسؤول رئيسي واحد فقط
        class CustomFormSet(formset):
            def clean(self):
                super().clean()
                if any(self.errors):
                    return

                primary_count = 0
                for form in self.forms:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        if form.cleaned_data.get('is_primary', False):
                            primary_count += 1

                if primary_count > 1:
                    raise forms.ValidationError(_('يمكن أن يكون هناك مسؤول رئيسي واحد فقط'))
                elif primary_count == 0 and obj and obj.requires_responsibles():
                    raise forms.ValidationError(_('يجب تحديد مسؤول رئيسي واحد على الأقل'))

        return CustomFormSet


@admin.register(Customer)
class CustomerAdmin(OptimizedAdminMixin, admin.ModelAdmin):
    form = CustomerAdminForm
    list_per_page = 20  # تقليل من 50 إلى 20 لتحسين الأداء
    list_max_show_all = 50  # تقليل من 100 إلى 50
    show_full_result_count = False  # تعطيل عدد النتائج لتحسين الأداء

    list_display = [
        'customer_code_display', 'customer_image', 'name', 'customer_type_display',
        'branch', 'phone', 'phone2', 'birth_date_display', 'status', 'category'
    ]

    # إضافة إمكانية الترتيب لجميع الأعمدة
    sortable_by = [
        'code', 'name', 'customer_type', 'branch__name',
        'phone', 'phone2', 'birth_date', 'status', 'category__name',
        'created_at'
    ]

    list_filter = [
        'status', 'customer_type', 'category',
        'branch', 'birth_date', 'created_at'
    ]

    search_fields = [
        'code', 'name', 'phone', 'phone2', 'email',
        'birth_date', 'notes', 'category__name'
    ]

    readonly_fields = ['created_by', 'created_at', 'updated_at']
    inlines = [CustomerResponsibleInline]

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': (
                'code', 'name', 'image', 'customer_type',
                'category', 'status'
            )
        }),
        (_('معلومات الاتصال'), {
            'fields': ('phone', 'phone2', 'email', 'birth_date', 'address')
        }),
        (_('معلومات إضافية'), {
            'fields': ('branch', 'interests', 'notes', 'discount_type')
        }),
        (_('معلومات النظام'), {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def customer_type_display(self, obj):
        """عرض نوع العميل بالاسم المقروء"""
        if not obj or not obj.customer_type:
            return 'غير محدد'
        
        # الحصول على قاموس أنواع العملاء
        customer_types_dict = dict(get_customer_types())
        return customer_types_dict.get(obj.customer_type, obj.customer_type)
    
    customer_type_display.short_description = _('نوع العميل')
    customer_type_display.admin_order_field = 'customer_type'

    def customer_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="border-radius: 50%;" />',
                obj.image.url
            )
        return '-'
    customer_image.short_description = _('الصورة')

    def birth_date_display(self, obj):
        """عرض تاريخ الميلاد بالشكل المطلوب"""
        if obj.birth_date:
            return obj.birth_date.strftime('%d/%m')
        return '-'
    
    birth_date_display.short_description = _('تاريخ الميلاد')
    birth_date_display.admin_order_field = 'birth_date'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related(
            'category', 'branch', 'created_by'
        ).only(
            'id', 'code', 'name', 'customer_type', 'phone', 'phone2', 'birth_date', 'status',
            'category__id', 'category__name',
            'branch__id', 'branch__name',
            'created_by__id', 'created_by__username'
        )
        
        if request.user.is_superuser:
            return qs
        # فلترة العملاء حسب فرع المستخدم
        if request.user.branch:
            return qs.filter(branch=request.user.branch)
        return qs.none()

    def get_urls(self):
        """إضافة URLs مخصصة للوصول للعملاء باستخدام الكود"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'by-code/<str:customer_code>/',
                self.admin_site.admin_view(self.customer_by_code_view),
                name='customers_customer_by_code',
            ),
        ]
        return custom_urls + urls

    def customer_by_code_view(self, request, customer_code):
        """عرض العميل باستخدام الكود وإعادة التوجيه لصفحة التحرير"""
        try:
            customer = Customer.objects.get(code=customer_code)
            return HttpResponseRedirect(
                reverse('admin:customers_customer_change', args=[customer.pk])
            )
        except Customer.DoesNotExist:
            self.message_user(request, f'العميل بكود {customer_code} غير موجود', level='error')
            return HttpResponseRedirect(reverse('admin:customers_customer_changelist'))

    def customer_code_display(self, obj):
        """عرض كود العميل مع روابط للعرض والتحرير - تحديث للاستخدام الكود في admin"""
        if not obj or not obj.code:
            return '-'
        
        try:
            # رابط عرض العميل في الواجهة
            view_url = reverse('customers:customer_detail_by_code', kwargs={'customer_code': obj.code})
            # رابط تحرير العميل في لوحة التحكم باستخدام الكود
            admin_url = reverse('admin:customers_customer_by_code', kwargs={'customer_code': obj.code})
            
            return format_html(
                '<strong>{}</strong><br/>'
                '<a href="{}" target="_blank" title="عرض في الواجهة">'
                '<span style="color: #0073aa;">👁️ عرض</span></a> | '
                '<a href="{}" title="تحرير في لوحة التحكم">'
                '<span style="color: #d63638;">✏️ تحرير</span></a>',
                obj.code,
                view_url,
                admin_url
            )
        except Exception:
            return obj.code
    
    customer_code_display.short_description = _('كود العميل')
    customer_code_display.admin_order_field = 'code'

    def has_change_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        # السماح بالتعديل فقط للعملاء في نفس فرع المستخدم
        return obj.branch == request.user.branch

    def has_delete_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        # السماح بالحذف فقط للعملاء في نفس فرع المستخدم
        return obj.branch == request.user.branch

    def delete_model(self, request, obj):
        """حذف عميل واحد مع حذف السجلات المرتبطة بشكل آمن"""
        from django.db import connection, transaction
        from django.db.models.signals import post_delete
        from orders import signals as order_signals
        from orders.models import OrderItem

        # تعطيل signal حذف عناصر الطلب مؤقتاً
        post_delete.disconnect(order_signals.log_order_item_deletion, sender=OrderItem)

        try:
            with transaction.atomic():
                # حذف سجلات OrderStatusLog لجميع طلبات العميل
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM orders_orderstatuslog
                        WHERE order_id IN (
                            SELECT id FROM orders_order WHERE customer_id = %s
                        )
                    """, [obj.pk])

                # حذف العميل (سيتم حذف الطلبات تلقائياً بسبب CASCADE)
                obj.delete()
        finally:
            # إعادة تفعيل signal حذف عناصر الطلب
            post_delete.connect(order_signals.log_order_item_deletion, sender=OrderItem)

    def delete_queryset(self, request, queryset):
        """حذف عدة عملاء مع حذف السجلات المرتبطة بشكل آمن"""
        from django.db import connection, transaction
        from django.db.models.signals import post_delete
        from orders import signals as order_signals
        from orders.models import OrderItem

        # تعطيل signal حذف عناصر الطلب مؤقتاً
        post_delete.disconnect(order_signals.log_order_item_deletion, sender=OrderItem)

        try:
            with transaction.atomic():
                # حذف سجلات OrderStatusLog لجميع طلبات العملاء
                customer_ids = list(queryset.values_list('id', flat=True))
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM orders_orderstatuslog
                        WHERE order_id IN (
                            SELECT id FROM orders_order WHERE customer_id = ANY(%s)
                        )
                    """, [customer_ids])

                # حذف العملاء (سيتم حذف الطلبات تلقائياً بسبب CASCADE)
                queryset.delete()
        finally:
            # إعادة تفعيل signal حذف عناصر الطلب
            post_delete.connect(order_signals.log_order_item_deletion, sender=OrderItem)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not request.user.is_superuser and not obj.branch:
                obj.branch = request.user.branch
        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('css/admin-extra.css',)
        }


@admin.register(DiscountType)
class DiscountTypeAdmin(OptimizedAdminMixin, admin.ModelAdmin):
    """إدارة أنواع الخصومات"""
    list_display = ['name', 'percentage', 'is_active', 'is_default', 'customers_count', 'created_at']
    list_filter = ['is_active', 'is_default', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-is_default', 'percentage', 'name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('name', 'percentage', 'description')
        }),
        (_('الإعدادات'), {
            'fields': ('is_active', 'is_default')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def customers_count(self, obj):
        """عدد العملاء الذين يستخدمون هذا النوع من الخصم"""
        count = obj.customers.count()
        if count > 0:
            return format_html(
                '<a href="{}?discount_type__id__exact={}">{} عميل</a>',
                reverse('admin:customers_customer_changelist'),
                obj.id,
                count
            )
        return '0 عميل'
    customers_count.short_description = _('عدد العملاء')

    def save_model(self, request, obj, form, change):
        # التأكد من وجود نوع خصم افتراضي واحد فقط
        if obj.is_default:
            DiscountType.objects.filter(is_default=True).exclude(pk=obj.pk).update(is_default=False)
        super().save_model(request, obj, form, change)





@admin.register(CustomerResponsible)
class CustomerResponsibleAdmin(OptimizedAdminMixin, admin.ModelAdmin):
    """إدارة مسؤولي العملاء"""
    list_display = ['name', 'customer', 'position', 'phone', 'is_primary', 'order']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['name', 'customer__name', 'position', 'phone', 'email']
    ordering = ['customer__name', 'order', 'name']
    autocomplete_fields = ['customer']

    fieldsets = (
        (_('معلومات المسؤول'), {
            'fields': ('customer', 'name', 'position')
        }),
        (_('معلومات الاتصال'), {
            'fields': ('phone', 'email')
        }),
        (_('الإعدادات'), {
            'fields': ('is_primary', 'order')
        }),
    )
