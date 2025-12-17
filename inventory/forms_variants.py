"""
Forms لنظام المتغيرات والتسعير
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    BaseProduct, ProductVariant, ColorAttribute, 
    VariantStock, PriceHistory, Category, Warehouse
)


class BaseProductForm(forms.ModelForm):
    """
    نموذج المنتج الأساسي
    """
    class Meta:
        model = BaseProduct
        fields = [
            'name', 'code', 'description', 'category',
            'base_price', 'unit', 'minimum_stock', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اسم المنتج الأساسي')
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('مثال: ORION, HARMONY')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'minimum_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')


class ProductVariantForm(forms.ModelForm):
    """
    نموذج متغير المنتج
    """
    class Meta:
        model = ProductVariant
        fields = [
            'base_product', 'variant_code', 'color', 'color_code',
            'price_override', 'barcode', 'description', 'is_active'
        ]
        widgets = {
            'base_product': forms.Select(attrs={'class': 'form-select'}),
            'variant_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('مثال: C 004, C1, OFF WHITE')
            }),
            'color': forms.Select(attrs={'class': 'form-select'}),
            'color_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('كود اللون إذا لم يكن في القائمة')
            }),
            'price_override': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': _('اتركه فارغاً لاستخدام السعر الأساسي')
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('الباركود (اختياري)')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        base_product = kwargs.pop('base_product', None)
        super().__init__(*args, **kwargs)
        
        self.fields['color'].queryset = ColorAttribute.objects.filter(is_active=True)
        self.fields['color'].required = False
        self.fields['price_override'].required = False
        
        if base_product:
            self.fields['base_product'].initial = base_product
            self.fields['base_product'].widget = forms.HiddenInput()


class ColorAttributeForm(forms.ModelForm):
    """
    نموذج سمة اللون
    """
    class Meta:
        model = ColorAttribute
        fields = ['name', 'code', 'hex_code', 'description', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('اسم اللون')
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('رمز اللون مثل: C1, RED')
            }),
            'hex_code': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'placeholder': '#FF5733'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
        }


class BulkPriceUpdateForm(forms.Form):
    """
    نموذج تحديث الأسعار بالجملة
    """
    UPDATE_TYPE_CHOICES = [
        ('percentage', _('نسبة مئوية (%)')),
        ('increase', _('زيادة مبلغ ثابت')),
        ('decrease', _('نقصان مبلغ ثابت')),
        ('fixed', _('تعيين سعر ثابت')),
        ('reset', _('إعادة للسعر الأساسي')),
    ]
    
    update_type = forms.ChoiceField(
        label=_('نوع التحديث'),
        choices=UPDATE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'update-type'})
    )
    
    value = forms.DecimalField(
        label=_('القيمة'),
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'id': 'update-value',
            'placeholder': _('القيمة أو النسبة')
        })
    )
    
    apply_to_all = forms.BooleanField(
        label=_('تطبيق على جميع المتغيرات'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    variant_ids = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'variant-ids'})
    )
    
    notes = forms.CharField(
        label=_('ملاحظات'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('سبب التحديث (اختياري)')
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        update_type = cleaned_data.get('update_type')
        value = cleaned_data.get('value')
        
        if update_type != 'reset' and value is None:
            raise forms.ValidationError(_('يجب إدخال قيمة'))
        
        if update_type == 'percentage' and value and abs(value) > 1000:
            raise forms.ValidationError(_('النسبة يجب أن تكون بين -1000% و 1000%'))
        
        return cleaned_data


class VariantStockUpdateForm(forms.Form):
    """
    نموذج تحديث مخزون المتغير
    """
    TRANSACTION_TYPES = [
        ('in', _('وارد')),
        ('out', _('صادر')),
        ('adjustment', _('تسوية')),
    ]
    
    REASON_CHOICES = [
        ('purchase', _('شراء')),
        ('sale', _('بيع')),
        ('return', _('مرتجع')),
        ('inventory_check', _('جرد')),
        ('damage', _('تلف')),
        ('production', _('إنتاج')),
        ('other', _('أخرى')),
    ]
    
    warehouse = forms.ModelChoiceField(
        label=_('المستودع'),
        queryset=Warehouse.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    transaction_type = forms.ChoiceField(
        label=_('نوع الحركة'),
        choices=TRANSACTION_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    quantity = forms.DecimalField(
        label=_('الكمية'),
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
    )
    
    reason = forms.ChoiceField(
        label=_('السبب'),
        choices=REASON_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        label=_('ملاحظات'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2
        })
    )


class VariantStockTransferForm(forms.Form):
    """
    نموذج نقل مخزون المتغير
    """
    from_warehouse = forms.ModelChoiceField(
        label=_('من مستودع'),
        queryset=Warehouse.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    to_warehouse = forms.ModelChoiceField(
        label=_('إلى مستودع'),
        queryset=Warehouse.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    quantity = forms.DecimalField(
        label=_('الكمية'),
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
    )
    
    notes = forms.CharField(
        label=_('ملاحظات'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        from_wh = cleaned_data.get('from_warehouse')
        to_wh = cleaned_data.get('to_warehouse')
        
        if from_wh and to_wh and from_wh == to_wh:
            raise forms.ValidationError(_('لا يمكن النقل من وإلى نفس المستودع'))
        
        return cleaned_data


class QuickVariantCreateForm(forms.Form):
    """
    نموذج إنشاء سريع لمتغيرات متعددة
    """
    variant_codes = forms.CharField(
        label=_('أكواد المتغيرات'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': _('أدخل كود واحد في كل سطر\nمثال:\nC1\nC2\nC3\nOFF WHITE')
        }),
        help_text=_('أدخل كل كود متغير في سطر منفصل')
    )
    
    copy_price_from_base = forms.BooleanField(
        label=_('استخدام السعر الأساسي'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    initial_stock = forms.DecimalField(
        label=_('المخزون الابتدائي'),
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1',
            'min': '0',
            'placeholder': '0'
        })
    )
    
    warehouse = forms.ModelChoiceField(
        label=_('المستودع'),
        queryset=Warehouse.objects.filter(is_active=True),
        required=False,
        empty_label=_('-- بدون مخزون --'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def get_variant_codes_list(self):
        """تحويل النص إلى قائمة أكواد"""
        codes_text = self.cleaned_data.get('variant_codes', '')
        codes = [c.strip() for c in codes_text.split('\n') if c.strip()]
        return codes


class MigrateProductsForm(forms.Form):
    """
    نموذج ترحيل المنتجات القديمة
    """
    confirm = forms.BooleanField(
        label=_('تأكيد الترحيل'),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    dry_run = forms.BooleanField(
        label=_('تجربة فقط (بدون حفظ)'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
