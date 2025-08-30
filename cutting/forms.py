from django import forms
from django.core.exceptions import ValidationError
from .models import CuttingOrder, CuttingOrderItem, CuttingReport
from inventory.models import Warehouse
from accounts.models import User


class CuttingOrderForm(forms.ModelForm):
    """نموذج أمر التقطيع"""
    
    class Meta:
        model = CuttingOrder
        fields = ['order', 'warehouse', 'status', 'assigned_to', 'notes']
        widgets = {
            'order': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'اختر الطلب'
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'اختر المستودع'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'اختر المسؤول'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # فلترة المستودعات النشطة فقط
        self.fields['warehouse'].queryset = Warehouse.objects.filter(is_active=True)
        
        # فلترة المستخدمين النشطين فقط
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)


class CuttingItemForm(forms.ModelForm):
    """نموذج عنصر التقطيع"""
    
    class Meta:
        model = CuttingOrderItem
        fields = [
            'status', 'cutter_name', 'permit_number', 'receiver_name',
            'bag_number', 'additional_quantity', 'notes', 'rejection_reason'
        ]
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'cutter_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم القصاص'
            }),
            'permit_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الإذن'
            }),
            'receiver_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم المستلم'
            }),
            'bag_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الشنطة'
            }),
            'additional_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0',
                'placeholder': '0.000'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'ملاحظات...'
            }),
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'سبب الرفض...'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        cutter_name = cleaned_data.get('cutter_name')
        permit_number = cleaned_data.get('permit_number')
        receiver_name = cleaned_data.get('receiver_name')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        # التحقق من البيانات المطلوبة للإكمال
        if status == 'completed':
            if not all([cutter_name, permit_number, receiver_name]):
                raise ValidationError(
                    'يجب ملء اسم القصاص ورقم الإذن واسم المستلم لإكمال العنصر'
                )
        
        # التحقق من سبب الرفض
        if status == 'rejected' and not rejection_reason:
            raise ValidationError('يجب كتابة سبب الرفض')
        
        return cleaned_data


class BulkUpdateForm(forms.Form):
    """نموذج التحديث المجمع"""
    
    cutter_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم القصاص'
        }),
        label='اسم القصاص'
    )
    
    permit_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم الإذن'
        }),
        label='رقم الإذن'
    )
    
    receiver_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستلم'
        }),
        label='اسم المستلم'
    )
    
    bag_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم الشنطة (اختياري)'
        }),
        label='رقم الشنطة'
    )
    
    complete_items = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='إكمال العناصر تلقائياً'
    )


class CuttingReportForm(forms.ModelForm):
    """نموذج تقرير التقطيع"""
    
    class Meta:
        model = CuttingReport
        fields = ['report_type', 'warehouse', 'start_date', 'end_date']
        widgets = {
            'report_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'warehouse': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'اختر المستودع'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['warehouse'].queryset = Warehouse.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
        
        return cleaned_data


class CuttingFilterForm(forms.Form):
    """نموذج فلترة أوامر التقطيع"""
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        required=False,
        empty_label='جميع المستودعات',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='المستودع'
    )
    
    status = forms.ChoiceField(
        choices=[('', 'جميع الحالات')] + CuttingOrder.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='الحالة'
    )
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث بكود التقطيع أو اسم العميل...'
        }),
        label='البحث'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='من تاريخ'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='إلى تاريخ'
    )


class QuickCompleteForm(forms.Form):
    """نموذج الإكمال السريع"""
    
    cutter_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم القصاص',
            'required': True
        }),
        label='اسم القصاص'
    )
    
    permit_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم الإذن',
            'required': True
        }),
        label='رقم الإذن'
    )
    
    receiver_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستلم',
            'required': True
        }),
        label='اسم المستلم'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'ملاحظات إضافية...'
        }),
        label='ملاحظات'
    )
