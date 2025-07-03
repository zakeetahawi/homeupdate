"""
نماذج Django للتركيبات الجديدة
"""
from django import forms
from django.utils import timezone
from datetime import date, timedelta
from .models_new import InstallationNew, InstallationTeamNew


class InstallationForm(forms.ModelForm):
    """نموذج إنشاء وتعديل التركيبات"""

    # حقل اختيار الطلب
    order = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="اختر طلب موجود (اختياري)",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'order_select'
        }),
        label='رقم الطلب'
    )

    class Meta:
        model = InstallationNew
        fields = [
            'order',
            'customer_name',
            'customer_phone',
            'customer_address',
            'windows_count',
            'location_type',
            'priority',
            'scheduled_date',
            'team',
            'salesperson_name',
            'branch_name',
            'notes'
        ]
        
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم العميل',
                'required': True
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الهاتف',
                'required': True
            }),
            'customer_address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان العميل',
                'rows': 3,
                'required': True
            }),
            'windows_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'عدد الشبابيك',
                'required': True
            }),
            'location_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': date.today().strftime('%Y-%m-%d')
            }),
            'team': forms.Select(attrs={
                'class': 'form-select'
            }),
            'salesperson_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم مندوب المبيعات'
            }),
            'branch_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الفرع'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'ملاحظات إضافية',
                'rows': 3
            })
        }
        
        labels = {
            'customer_name': 'اسم العميل',
            'customer_phone': 'رقم الهاتف',
            'customer_address': 'عنوان العميل',
            'windows_count': 'عدد الشبابيك',
            'location_type': 'نوع الموقع',
            'priority': 'الأولوية',
            'scheduled_date': 'تاريخ التركيب المجدول',
            'team': 'فريق التركيب',
            'salesperson_name': 'اسم مندوب المبيعات',
            'branch_name': 'اسم الفرع',
            'notes': 'ملاحظات'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # استيراد الطلبات
        from orders.models import Order

        # تحديد الطلبات المتاحة (طلبات التركيب فقط)
        self.fields['order'].queryset = Order.objects.filter(
            selected_types__contains=['installation']
        ).select_related('customer').order_by('-created_at')

        # تحديد الفرق النشطة فقط
        team_field = self.fields['team']
        if hasattr(team_field, 'queryset'):
            team_field.queryset = InstallationTeamNew.objects.filter(is_active=True)

        # تحديد القيم الافتراضية للتركيبات الجديدة
        if not self.instance.pk:
            self.fields['scheduled_date'].initial = date.today() + timedelta(days=7)
            self.fields['priority'].initial = 'normal'
            self.fields['location_type'].initial = 'residential'
    
    def clean_scheduled_date(self):
        """التحقق من صحة تاريخ التركيب"""
        scheduled_date = self.cleaned_data.get('scheduled_date')
        
        if scheduled_date and scheduled_date < date.today():
            raise forms.ValidationError('لا يمكن جدولة التركيب في تاريخ سابق')
            
        return scheduled_date
    
    def clean_windows_count(self):
        """التحقق من صحة عدد الشبابيك"""
        windows_count = self.cleaned_data.get('windows_count')
        
        if windows_count and windows_count < 1:
            raise forms.ValidationError('عدد الشبابيك يجب أن يكون أكبر من صفر')
            
        if windows_count and windows_count > 50:
            raise forms.ValidationError('عدد الشبابيك كبير جداً (الحد الأقصى 50)')
            
        return windows_count
    
    def clean_customer_phone(self):
        """التحقق من صحة رقم الهاتف"""
        phone = self.cleaned_data.get('customer_phone')
        
        if phone:
            # إزالة المسافات والرموز
            phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            # التحقق من أن الرقم يحتوي على أرقام فقط
            if not phone.isdigit():
                raise forms.ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')
                
            # التحقق من طول الرقم
            if len(phone) < 10 or len(phone) > 15:
                raise forms.ValidationError('رقم الهاتف غير صحيح')
                
        return phone
    
    def save(self, commit=True):
        """حفظ التركيب مع إعداد القيم الافتراضية"""
        installation = super().save(commit=False)
        
        # تحديد تاريخ الطلب إذا لم يكن محدداً
        if not installation.order_date:
            installation.order_date = date.today()
            
        # تحديد الحالة الافتراضية
        if not installation.status:
            installation.status = 'pending'
            
        if commit:
            installation.save()
            
        return installation


class InstallationSearchForm(forms.Form):
    """نموذج البحث في التركيبات"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث في التركيبات...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'جميع الحالات')] + InstallationNew.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'جميع الأولويات')] + InstallationNew.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    team = forms.ModelChoiceField(
        required=False,
        queryset=InstallationTeamNew.objects.filter(is_active=True),
        empty_label="جميع الفرق",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
