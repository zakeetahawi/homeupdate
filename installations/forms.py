from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    InstallationSchedule, InstallationTeam, Technician, Driver,
    ModificationReport, ReceiptMemo, InstallationPayment
)


class InstallationScheduleForm(forms.ModelForm):
    """نموذج جدولة التركيب"""
    scheduled_date = forms.DateField(
        label=_('تاريخ التركيب'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text=_('اختر تاريخ التركيب')
    )
    scheduled_time = forms.TimeField(
        label=_('موعد التركيب'),
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text=_('اختر موعد التركيب')
    )

    class Meta:
        model = InstallationSchedule
        fields = ['team', 'scheduled_date', 'scheduled_time', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'أضف ملاحظات هنا...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')

        if scheduled_date and scheduled_date < timezone.now().date():
            raise ValidationError(_('لا يمكن جدولة تركيب في تاريخ ماضي'))

        if scheduled_date and scheduled_time:
            scheduled_datetime = timezone.make_aware(
                timezone.datetime.combine(scheduled_date, scheduled_time)
            )
            if scheduled_datetime < timezone.now():
                raise ValidationError(_('لا يمكن جدولة تركيب في وقت ماضي'))

        return cleaned_data


class InstallationTeamForm(forms.ModelForm):
    """نموذج فريق التركيب"""
    class Meta:
        model = InstallationTeam
        fields = ['name', 'technicians', 'driver']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'اسم الفريق'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        technicians = cleaned_data.get('technicians')
        
        if not technicians:
            raise ValidationError(_('يجب اختيار فني واحد على الأقل'))

        return cleaned_data


class TechnicianForm(forms.ModelForm):
    """نموذج الفني"""
    class Meta:
        model = Technician
        fields = ['name', 'phone', 'specialization', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'اسم الفني'}),
            'phone': forms.TextInput(attrs={'placeholder': 'رقم الهاتف'}),
            'specialization': forms.TextInput(attrs={'placeholder': 'التخصص'}),
        }


class DriverForm(forms.ModelForm):
    """نموذج السائق"""
    class Meta:
        model = Driver
        fields = ['name', 'phone', 'license_number', 'vehicle_number', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'اسم السائق'}),
            'phone': forms.TextInput(attrs={'placeholder': 'رقم الهاتف'}),
            'license_number': forms.TextInput(attrs={'placeholder': 'رقم الرخصة'}),
            'vehicle_number': forms.TextInput(attrs={'placeholder': 'رقم المركبة'}),
        }


class ModificationReportForm(forms.ModelForm):
    """نموذج تقرير التعديل"""
    class Meta:
        model = ModificationReport
        fields = ['report_file', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'وصف التعديل المطلوب...'
            }),
        }

    def clean_report_file(self):
        file = self.cleaned_data.get('report_file')
        if file:
            # التحقق من نوع الملف
            allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
            if file.content_type not in allowed_types:
                raise ValidationError(_('يجب أن يكون الملف من نوع PDF أو صورة'))
            
            # التحقق من حجم الملف (5MB كحد أقصى)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError(_('حجم الملف يجب أن يكون أقل من 5 ميجابايت'))

        return file


class ReceiptMemoForm(forms.ModelForm):
    """نموذج مذكرة الاستلام"""
    class Meta:
        model = ReceiptMemo
        fields = ['receipt_image', 'customer_signature', 'amount_received', 'notes']
        widgets = {
            'amount_received': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'ملاحظات إضافية...'
            }),
        }

    def clean_receipt_image(self):
        image = self.cleaned_data.get('receipt_image')
        if image:
            # التحقق من نوع الصورة
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
            if image.content_type not in allowed_types:
                raise ValidationError(_('يجب أن تكون الصورة من نوع JPG أو PNG'))
            
            # التحقق من حجم الصورة (2MB كحد أقصى)
            if image.size > 2 * 1024 * 1024:
                raise ValidationError(_('حجم الصورة يجب أن يكون أقل من 2 ميجابايت'))

        return image


class InstallationPaymentForm(forms.ModelForm):
    """نموذج دفعة التركيب"""
    class Meta:
        model = InstallationPayment
        fields = ['payment_type', 'amount', 'payment_method', 'receipt_number', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'payment_method': forms.TextInput(attrs={'placeholder': 'طريقة الدفع'}),
            'receipt_number': forms.TextInput(attrs={'placeholder': 'رقم الإيصال'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'ملاحظات الدفع...'
            }),
        }


class InstallationFilterForm(forms.Form):
    """نموذج فلترة التركيبات"""
    STATUS_CHOICES = [
        ('', _('جميع الحالات')),
        ('pending', _('في الانتظار')),
        ('scheduled', _('مجدول')),
        ('in_progress', _('قيد التنفيذ')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
        ('rescheduled', _('إعادة جدولة')),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label=_('حالة التركيب')
    )
    
    team = forms.ModelChoiceField(
        queryset=InstallationTeam.objects.filter(is_active=True),
        required=False,
        label=_('الفريق'),
        empty_label=_('جميع الفرق')
    )
    
    date_from = forms.DateField(
        required=False,
        label=_('من تاريخ'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        label=_('إلى تاريخ'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    search = forms.CharField(
        required=False,
        label=_('بحث'),
        widget=forms.TextInput(attrs={'placeholder': 'بحث في أرقام الطلبات أو أسماء العملاء...'})
    )


class DailyScheduleForm(forms.Form):
    """نموذج الجدول اليومي"""
    date = forms.DateField(
        label=_('التاريخ'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date()
    )
    
    team = forms.ModelChoiceField(
        queryset=InstallationTeam.objects.filter(is_active=True),
        required=False,
        label=_('الفريق'),
        empty_label=_('جميع الفرق')
    )
