from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django import forms
from .models import (
    Customer, CustomerCategory, CustomerNote, CustomerType, get_customer_types
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
class CustomerCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
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
class CustomerTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at']
    ordering = ['name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = CustomerAdminForm
    
    list_display = [
        'code', 'customer_image', 'name', 'customer_type_display',
        'branch', 'phone', 'phone2', 'birth_date_display', 'status', 'category'
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
            'fields': ('branch', 'interests', 'notes')
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
        if request.user.is_superuser:
            return qs
        # فلترة العملاء حسب فرع المستخدم
        if request.user.branch:
            return qs.filter(branch=request.user.branch)
        return qs.none()

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
