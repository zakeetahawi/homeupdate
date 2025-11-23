"""
نماذج الويزارد لإنشاء الطلبات
Forms for Multi-Step Order Creation Wizard
"""
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .wizard_models import DraftOrder, DraftOrderItem
from .contract_models import ContractCurtain, CurtainFabric, CurtainAccessory
from customers.models import Customer
from accounts.models import Branch, Salesperson
from inventory.models import Product
from inspections.models import Inspection


class Step1BasicInfoForm(forms.ModelForm):
    """
    الخطوة 1: البيانات الأساسية
    """
    class Meta:
        model = DraftOrder
        fields = ['customer', 'branch', 'salesperson', 'status', 'notes']
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-select select2-customer',
                'required': True
            }),
            'branch': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'salesperson': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'ملاحظات حول الطلب (اختياري)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # تعيين الفرع الافتراضي من المستخدم
        if user and hasattr(user, 'branch') and user.branch:
            self.fields['branch'].initial = user.branch
        
        # تحميل البائعين النشطين فقط
        self.fields['salesperson'].queryset = Salesperson.objects.filter(is_active=True)


class Step2OrderTypeForm(forms.ModelForm):
    """
    الخطوة 2: نوع الطلب
    """
    class Meta:
        model = DraftOrder
        fields = ['selected_type', 'related_inspection', 'related_inspection_type']
        widgets = {
            'selected_type': forms.RadioSelect(attrs={
                'class': 'form-check-input',
                'required': True
            }),
            'related_inspection': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)
        
        # تحميل المعاينات المرتبطة بالعميل
        if customer:
            self.fields['related_inspection'].queryset = Inspection.objects.filter(
                customer=customer
            ).order_by('-created_at')
        else:
            self.fields['related_inspection'].queryset = Inspection.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        selected_type = cleaned_data.get('selected_type')
        
        # التحقق من اختيار نوع الطلب
        if not selected_type:
            raise ValidationError('يجب اختيار نوع الطلب')
        
        return cleaned_data


class Step3OrderItemForm(forms.ModelForm):
    """
    نموذج إضافة عنصر طلب
    """
    class Meta:
        model = DraftOrderItem
        fields = ['product', 'quantity', 'unit_price', 'discount_percentage', 'item_type', 'notes']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-select product-select',
                'required': True
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.001',
                'step': '0.001',
                'required': True
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'required': True
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01',
                'value': '0'
            }),
            'item_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            raise ValidationError('الكمية يجب أن تكون أكبر من صفر')
        return quantity
    
    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price and unit_price < 0:
            raise ValidationError('السعر لا يمكن أن يكون سالباً')
        return unit_price


class Step4InvoicePaymentForm(forms.ModelForm):
    """
    الخطوة 4: تفاصيل الفاتورة والدفع
    """
    class Meta:
        model = DraftOrder
        fields = [
            'invoice_number', 'invoice_number_2', 'invoice_number_3',
            'contract_number', 'contract_number_2', 'contract_number_3',
            'payment_method', 'paid_amount', 'payment_notes'
        ]
        widgets = {
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الفاتورة الرئيسي'
            }),
            'invoice_number_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم فاتورة إضافي (اختياري)'
            }),
            'invoice_number_3': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم فاتورة إضافي (اختياري)'
            }),
            'contract_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم العقد الرئيسي'
            }),
            'contract_number_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم عقد إضافي (اختياري)'
            }),
            'contract_number_3': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم عقد إضافي (اختياري)'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'paid_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'value': '0'
            }),
            'payment_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات الدفع (اختياري)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.draft_order = kwargs.pop('draft_order', None)
        super().__init__(*args, **kwargs)
    
    def clean_paid_amount(self):
        paid_amount = self.cleaned_data.get('paid_amount')
        
        # التحقق من أن المبلغ المدفوع لا يتجاوز الإجمالي
        if self.draft_order and paid_amount:
            if paid_amount > self.draft_order.final_total:
                raise ValidationError(
                    f'المبلغ المدفوع ({paid_amount}) لا يمكن أن يتجاوز الإجمالي ({self.draft_order.final_total})'
                )
        
        return paid_amount


# Note: Forms for curtains, fabrics, and accessories are now handled via AJAX
# and use the contract_models directly

