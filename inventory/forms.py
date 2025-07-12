from django import forms
from django.utils.translation import gettext_lazy as _
from .models import PurchaseOrder, PurchaseOrderItem, Product, Supplier, Warehouse


class PurchaseOrderForm(forms.ModelForm):
    """نموذج طلب الشراء"""
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'warehouse', 'status', 'expected_date', 
            'total_amount', 'notes'
        ]
        widgets = {
            'supplier': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'اختر المورد'
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'اختر المستودع'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'expected_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية...'
            })
        }
        labels = {
            'supplier': _('المورد'),
            'warehouse': _('المستودع'),
            'status': _('الحالة'),
            'expected_date': _('تاريخ التسليم المتوقع'),
            'total_amount': _('إجمالي المبلغ'),
            'notes': _('ملاحظات')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحسين عرض الموردين والمستودعات
        self.fields['supplier'].queryset = Supplier.objects.all().order_by('name')
        self.fields['warehouse'].queryset = Warehouse.objects.filter(is_active=True).order_by('name')


class PurchaseOrderItemForm(forms.ModelForm):
    """نموذج عنصر طلب الشراء"""
    
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'unit_price', 'received_quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control product-select',
                'placeholder': 'اختر المنتج'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control quantity-input',
                'min': '1',
                'placeholder': 'الكمية'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control price-input',
                'step': '0.01',
                'placeholder': 'سعر الوحدة'
            }),
            'received_quantity': forms.NumberInput(attrs={
                'class': 'form-control received-input',
                'min': '0',
                'placeholder': 'الكمية المستلمة'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ملاحظات إضافية'
            })
        }
        labels = {
            'product': _('المنتج'),
            'quantity': _('الكمية'),
            'unit_price': _('سعر الوحدة'),
            'received_quantity': _('الكمية المستلمة'),
            'notes': _('ملاحظات')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحسين عرض المنتجات
        self.fields['product'].queryset = Product.objects.all().order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        received_quantity = cleaned_data.get('received_quantity')
        
        if quantity and received_quantity and received_quantity > quantity:
            raise forms.ValidationError(
                _('الكمية المستلمة لا يمكن أن تكون أكبر من الكمية المطلوبة')
            )
        
        return cleaned_data


class PurchaseOrderItemFormSet(forms.BaseModelFormSet):
    """FormSet لعناصر طلب الشراء"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = PurchaseOrderItem.objects.none()
    
    def clean(self):
        super().clean()
        if not self.forms:
            raise forms.ValidationError(_('يجب إضافة منتج واحد على الأقل'))
        
        for form in self.forms:
            if form.is_valid():
                quantity = form.cleaned_data.get('quantity')
                if quantity and quantity <= 0:
                    raise forms.ValidationError(_('يجب أن تكون الكمية أكبر من صفر'))


# إنشاء FormSet
PurchaseOrderItemFormSet = forms.modelformset_factory(
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    formset=PurchaseOrderItemFormSet,
    extra=1,
    can_delete=True
) 