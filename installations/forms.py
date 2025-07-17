from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    InstallationSchedule, InstallationTeam, Technician, Driver,
    ModificationRequest, ModificationImage, ManufacturingOrder,
    ModificationReport, ReceiptMemo, InstallationPayment, CustomerDebt,
    InstallationAnalytics, ModificationErrorAnalysis, InstallationSchedulingSettings
)


class InstallationStatusForm(forms.ModelForm):
    """نموذج تغيير حالة التركيب"""
    reason = forms.CharField(
        label=_('سبب التغيير'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'اكتب سبب تغيير الحالة...'
        }),
        required=False,
        help_text='مطلوب لبعض التغييرات مثل الإلغاء أو طلب التعديل'
    )
    
    class Meta:
        model = InstallationSchedule
        fields = ['status', 'completion_date', 'notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control',
                'id': 'installation-status'
            }),
            'completion_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'id': 'completion-date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية...'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تحديد الحالات المتاحة بناءً على الحالة الحالية
        if self.instance and self.instance.pk:
            possible_statuses = self.instance.get_next_possible_statuses()
            # إضافة الحالة الحالية للقائمة
            current_status = (self.instance.status, self.instance.get_status_display())
            if current_status not in possible_statuses:
                possible_statuses.insert(0, current_status)
            
            self.fields['status'].choices = possible_statuses
        
        # إخفاء حقل تاريخ الإكمال إذا لم تكن الحالة مكتمل
        if self.instance and self.instance.status != 'completed':
            self.fields['completion_date'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')
        reason = cleaned_data.get('reason')
        
        # التحقق من صحة تغيير الحالة
        if self.instance and self.instance.pk:
            if new_status != self.instance.status:
                if not self.instance.can_change_status_to(new_status):
                    raise forms.ValidationError(
                        f'لا يمكن تغيير الحالة من {self.instance.get_status_display()} إلى {dict(self.instance.STATUS_CHOICES)[new_status]}'
                    )
                
                # التحقق من وجود سبب للتغييرات المهمة
                if new_status in ['cancelled', 'modification_required'] and not reason:
                    raise forms.ValidationError('سبب التغيير مطلوب لهذا النوع من التغيير')
        
        return cleaned_data


class ModificationRequestForm(forms.ModelForm):
    """نموذج طلب التعديل"""
    class Meta:
        model = ModificationRequest
        fields = ['modification_type', 'description', 'priority', 'estimated_cost', 'customer_approval']
        widgets = {
            'modification_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نوع التعديل المطلوب'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'تفاصيل التعديل المطلوب...'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'customer_approval': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class ModificationImageForm(forms.ModelForm):
    """نموذج رفع صور التعديل"""
    class Meta:
        model = ModificationImage
        fields = ['image', 'description']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'وصف الصورة'
            })
        }


class ManufacturingOrderForm(forms.ModelForm):
    """نموذج أمر التصنيع للتعديلات"""
    class Meta:
        model = ManufacturingOrder
        fields = ['order_type', 'status', 'description', 'estimated_completion_date', 'assigned_to', 'manager_notes']
        widgets = {
            'order_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'تفاصيل أمر التصنيع...'
            }),
            'estimated_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control'
            }),
            'manager_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات المدير...'
            })
        }


class ModificationReportForm(forms.ModelForm):
    """نموذج تقرير التعديل"""
    class Meta:
        model = ModificationReport
        fields = ['report_file', 'description', 'completion_notes']
        widgets = {
            'report_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'وصف التعديل المنجز...'
            }),
            'completion_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات الإكمال...'
            })
        }


class CustomerDebtForm(forms.ModelForm):
    """نموذج إدارة مديونية العميل"""
    class Meta:
        model = CustomerDebt
        fields = ['debt_amount', 'notes', 'is_paid', 'payment_receipt_number', 'payment_receiver_name']
        widgets = {
            'debt_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات حول المديونية...'
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'payment_receipt_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم إذن استلام المبلغ'
            }),
            'payment_receiver_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم المستلم'
            })
        }


class CustomerDebtPaymentForm(forms.ModelForm):
    """نموذج دفع المديونية"""
    class Meta:
        model = CustomerDebt
        fields = ['payment_receipt_number', 'payment_receiver_name', 'notes']
        widgets = {
            'payment_receipt_number': forms.TextInput(attrs={
                'placeholder': 'رقم إذن استلام المبلغ'
            }),
            'payment_receiver_name': forms.TextInput(attrs={
                'placeholder': 'اسم المستلم'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'ملاحظات الدفع...'
            }),
        }

    def clean_payment_receipt_number(self):
        receipt_number = self.cleaned_data.get('payment_receipt_number')
        if not receipt_number:
            raise ValidationError(_('رقم إذن استلام المبلغ مطلوب'))
        return receipt_number

    def clean_payment_receiver_name(self):
        receiver_name = self.cleaned_data.get('payment_receiver_name')
        if not receiver_name:
            raise ValidationError(_('اسم المستلم مطلوب'))
        return receiver_name


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


class QuickScheduleForm(forms.ModelForm):
    """نموذج جدولة سريعة للتركيب"""
    scheduled_date = forms.DateField(
        label=_('تاريخ التركيب'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        help_text=_('اختر تاريخ التركيب')
    )
    scheduled_time = forms.TimeField(
        label=_('موعد التركيب'),
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=True,
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

        if not scheduled_date:
            raise ValidationError(_('تاريخ التركيب مطلوب'))

        if not scheduled_time:
            raise ValidationError(_('موعد التركيب مطلوب'))

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


class ModificationReportForm_new(forms.ModelForm):
    """نموذج تقرير التعديل الجديد"""
    class Meta:
        model = ModificationReport
        fields = ['report_file', 'description', 'completion_notes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'completion_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class InstallationAnalyticsForm(forms.ModelForm):
    """نموذج تحليل التركيبات"""
    class Meta:
        model = InstallationAnalytics
        fields = ['month', 'total_installations', 'completed_installations', 'pending_installations', 
                 'in_progress_installations', 'total_customers', 'new_customers', 'total_visits', 
                 'total_modifications']
        widgets = {
            'month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'total_installations': forms.NumberInput(attrs={'class': 'form-control'}),
            'completed_installations': forms.NumberInput(attrs={'class': 'form-control'}),
            'pending_installations': forms.NumberInput(attrs={'class': 'form-control'}),
            'in_progress_installations': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_customers': forms.NumberInput(attrs={'class': 'form-control'}),
            'new_customers': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_visits': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_modifications': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ModificationErrorAnalysisForm(forms.ModelForm):
    """نموذج تحليل خطأ التعديل"""
    class Meta:
        model = ModificationErrorAnalysis
        fields = ['error_type', 'error_description', 'root_cause', 'solution_applied', 
                 'prevention_measures', 'cost_impact', 'time_impact_hours']
        widgets = {
            'error_type': forms.Select(attrs={'class': 'form-control'}),
            'error_description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'root_cause': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'solution_applied': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'prevention_measures': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'cost_impact': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'time_impact_hours': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class InstallationSchedulingSettingsForm(forms.ModelForm):
    """نموذج إعدادات جدولة التركيب"""
    class Meta:
        model = InstallationSchedulingSettings
        fields = [
            'technician_name', 'driver_name', 'customer_address', 'customer_phone',
            'contract_number', 'invoice_number', 'salesperson_name', 'branch_name',
            'special_instructions'
        ]
        widgets = {
            'technician_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الفني'
            }),
            'driver_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم السائق'
            }),
            'customer_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'عنوان العميل'
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم هاتف العميل'
            }),
            'contract_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم العقد'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الفاتورة'
            }),
            'salesperson_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم البائع'
            }),
            'branch_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الفرع'
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'تعليمات خاصة للتركيب...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ملء البيانات تلقائياً من الطلب إذا لم تكن موجودة
        if self.instance and self.instance.pk and not any([
            self.instance.customer_phone,
            self.instance.contract_number,
            self.instance.salesperson_name
        ]):
            self.instance.populate_from_order()


class ScheduleEditForm(forms.ModelForm):
    """نموذج تعديل الجدولة مع سبب التغيير"""
    reason = forms.CharField(
        label=_('سبب تعديل الجدولة'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'اكتب سبب تعديل الجدولة...'
        }),
        required=True,
        help_text='مطلوب كتابة سبب تعديل الجدولة'
    )
    
    class Meta:
        model = InstallationSchedule
        fields = ['team', 'scheduled_date', 'scheduled_time', 'notes']
        widgets = {
            'team': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'scheduled_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات الجدولة...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')
        reason = cleaned_data.get('reason')

        if not reason:
            raise ValidationError(_('سبب تعديل الجدولة مطلوب'))

        if scheduled_date and scheduled_date < timezone.now().date():
            raise ValidationError(_('لا يمكن جدولة تركيب في تاريخ ماضي'))

        if scheduled_date and scheduled_time:
            scheduled_datetime = timezone.make_aware(
                timezone.datetime.combine(scheduled_date, scheduled_time)
            )
            if scheduled_datetime < timezone.now():
                raise ValidationError(_('لا يمكن جدولة تركيب في وقت ماضي'))

        return cleaned_data
