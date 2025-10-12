"""
نماذج تقارير الإنتاج
Production Reports Forms
"""

from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import ManufacturingOrder, ProductionLine, ProductionForecast
from orders.models import Order


class ProductionReportFilterForm(forms.Form):
    """
    نموذج فلترة تقارير الإنتاج
    Production Report Filter Form
    """
    date_from = forms.DateField(
        required=False,
        label='من تاريخ',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label='إلى تاريخ',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    from_status = forms.MultipleChoiceField(
        required=False,
        label='من حالة',
        choices=ManufacturingOrder.STATUS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    to_status = forms.MultipleChoiceField(
        required=False,
        label='إلى حالة',
        choices=ManufacturingOrder.STATUS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    production_line = forms.MultipleChoiceField(
        required=False,
        label='خط الإنتاج',
        choices=[],  # سيتم ملؤها في __init__
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    order_type = forms.MultipleChoiceField(
        required=False,
        label='نوع الطلب',
        choices=ManufacturingOrder.ORDER_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    order_status = forms.MultipleChoiceField(
        required=False,
        label='وضع الطلب',
        choices=Order.STATUS_CHOICES,  # عادي أو VIP
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تعيين القيم الافتراضية
        if not self.data:
            self.fields['date_to'].initial = timezone.now().date()
            self.fields['date_from'].initial = timezone.now().date() - timedelta(days=30)

        # ملء خيارات خطوط الإنتاج
        production_lines = ProductionLine.objects.all()
        self.fields['production_line'].choices = [
            (str(line.id), line.name) for line in production_lines
        ]


class ProductionForecastForm(forms.ModelForm):
    """
    نموذج إنشاء/تعديل توقعات الإنتاج
    Production Forecast Form
    """
    class Meta:
        model = ProductionForecast
        fields = [
            'forecast_date',
            'period_type',
            'forecasted_orders_count',
            'forecasted_meters',
            'production_line',
            'order_type',
            'confidence_level',
            'notes'
        ]
        widgets = {
            'forecast_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'period_type': forms.Select(attrs={'class': 'form-select'}),
            'forecasted_orders_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'forecasted_meters': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'production_line': forms.Select(attrs={'class': 'form-select'}),
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'confidence_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل بعض الحقول اختيارية
        self.fields['production_line'].required = False
        self.fields['order_type'].required = False
        self.fields['notes'].required = False


class ExportColumnsForm(forms.Form):
    """
    نموذج اختيار الأعمدة للتصدير
    Export Columns Selection Form
    """
    COLUMN_CHOICES = [
        ('manufacturing_code', 'رقم أمر التصنيع'),
        ('order_number', 'رقم الطلب'),
        ('contract_number', 'رقم العقد'),
        ('customer_name', 'اسم العميل'),
        ('customer_phone', 'رقم الهاتف'),
        ('customer_address', 'عنوان العميل'),
        ('branch', 'الفرع'),
        ('from_status', 'من حالة'),
        ('to_status', 'إلى حالة'),
        ('order_type', 'نوع الطلب'),
        ('production_line', 'خط الإنتاج'),
        ('changed_by', 'تم التغيير بواسطة'),
        ('changed_at', 'تاريخ التغيير'),
        ('notes', 'ملاحظات'),
        ('order_date', 'تاريخ الطلب'),
        ('expected_delivery_date', 'تاريخ التسليم المتوقع'),
        ('completion_date', 'تاريخ الإكمال'),
    ]
    
    columns = forms.MultipleChoiceField(
        required=False,
        label='الأعمدة المطلوبة',
        choices=COLUMN_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        initial=[choice[0] for choice in COLUMN_CHOICES[:13]]  # الأعمدة الأساسية
    )
    
    export_format = forms.ChoiceField(
        required=True,
        label='صيغة التصدير',
        choices=[
            ('excel', 'Excel'),
            ('pdf', 'PDF'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='excel'
    )


class DateRangeForm(forms.Form):
    """
    نموذج بسيط لاختيار نطاق التاريخ
    Simple Date Range Form
    """
    date_from = forms.DateField(
        required=True,
        label='من تاريخ',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=True,
        label='إلى تاريخ',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to:
            if date_from > date_to:
                raise forms.ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
            
            # التحقق من أن الفترة ليست طويلة جداً (مثلاً سنة واحدة)
            if (date_to - date_from).days > 365:
                raise forms.ValidationError('الفترة الزمنية يجب ألا تتجاوز سنة واحدة')
        
        return cleaned_data

