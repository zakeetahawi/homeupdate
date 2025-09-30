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
from accounts.models import Salesperson, Branch


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
        
        # تعيين قيمة افتراضية لتاريخ الإكمال
        if not self.instance.completion_date:
            from django.utils import timezone
            self.fields['completion_date'].initial = timezone.now()

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')
        reason = cleaned_data.get('reason')
        completion_date = cleaned_data.get('completion_date')

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

        # التحقق من تاريخ الإكمال عند تغيير الحالة إلى مكتمل
        if new_status == 'completed':
            if not completion_date:
                from django.utils import timezone
                cleaned_data['completion_date'] = timezone.now()

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
        help_text=_('اختر تاريخ التركيب'),
        required=False
    )
    scheduled_time = forms.TimeField(
        label=_('موعد التركيب'),
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text=_('اختر موعد التركيب'),
        required=False
    )
    windows_count = forms.IntegerField(
        label=_('عدد الشبابيك'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'placeholder': 'أدخل عدد الشبابيك'
        }),
        required=False,
        help_text=_('عدد الشبابيك المطلوبة للتركيب')
    )

    class Meta:
        model = InstallationSchedule
        fields = ['team', 'scheduled_date', 'scheduled_time', 'location_type', 'windows_count', 'notes']
        widgets = {
            'location_type': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'اختر نوع المكان'
            }),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'أضف ملاحظات هنا...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')

        # التحقق من أن التاريخ والوقت مطلوبان عند الجدولة
        if self.instance and self.instance.status in ['scheduled', 'in_installation']:
            if not scheduled_date:
                raise ValidationError(_('تاريخ التركيب مطلوب للحالة المجدولة'))
            if not scheduled_time:
                raise ValidationError(_('موعد التركيب مطلوب للحالة المجدولة'))

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
    location_address = forms.CharField(
        label=_('عنوان التركيب'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'سيتم جلب العنوان من معلومات العميل'
        }),
        required=False,
        help_text=_('عنوان التركيب (سيتم جلبه من معلومات العميل)')
    )
    
    # إضافة حقل تحديث عنوان العميل
    update_customer_address = forms.CharField(
        label=_('تحديث عنوان العميل الرئيسي'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('اتركه فارغاً إذا لم تريد تحديث عنوان العميل الرئيسي')
        }),
        help_text=_('إذا تم ملء هذا الحقل، سيتم تحديث العنوان الرئيسي للعميل في جميع أنحاء النظام')
    )
    
    def __init__(self, *args, **kwargs):
        order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        
        if order and order.customer:
            # تعيين العنوان الافتراضي من معلومات العميل
            customer_address = order.customer.address or ''
            customer_location_type = getattr(order.customer, 'location_type', '') or ''
            
            # إضافة نوع المكان إلى العنوان إذا كان متوفراً
            if customer_location_type:
                location_type_display = dict(order.customer._meta.get_field('location_type').choices).get(customer_location_type, '')
                if location_type_display:
                    customer_address = f"{customer_address}\nنوع المكان: {location_type_display}"
            
            self.fields['location_address'].initial = customer_address
            self.fields['location_type'].initial = customer_location_type

    class Meta:
        model = InstallationSchedule
        fields = ['team', 'scheduled_date', 'scheduled_time', 'location_type', 'location_address', 'notes']
        widgets = {
            'location_type': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'اختر نوع المكان'
            }),
            'location_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'أدخل عنوان التركيب بالتفصيل'
            }),
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
            'name': forms.TextInput(attrs={
                'placeholder': 'اسم الفريق',
                'class': 'form-control'
            }),
            'technicians': forms.CheckboxSelectMultiple(),
            'driver': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية الفنيين لعرض فنيي التركيبات فقط
        self.fields['technicians'].queryset = Technician.objects.filter(
            department='installation',
            is_active=True
        )
        # تصفية السائقين لعرض النشطين فقط
        self.fields['driver'].queryset = Driver.objects.filter(is_active=True)
        self.fields['driver'].empty_label = "اختر سائق (اختياري)"

    def clean(self):
        cleaned_data = super().clean()
        technicians = cleaned_data.get('technicians')
        
        if not technicians:
            raise ValidationError('يجب اختيار فني واحد على الأقل')

        return cleaned_data


class TechnicianForm(forms.ModelForm):
    """نموذج الفني"""
    class Meta:
        model = Technician
        fields = ['name', 'phone', 'specialization', 'is_active']  # إزالة department من الحقول المعروضة
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'اسم الفني',
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'رقم الهاتف',
                'class': 'form-control'
            }),
            'specialization': forms.TextInput(attrs={
                'placeholder': 'التخصص',
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TechnicianEditForm(forms.ModelForm):
    """نموذج تعديل الفني - يتضمن حقل القسم"""
    class Meta:
        model = Technician
        fields = ['name', 'phone', 'specialization', 'department', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'اسم الفني',
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'رقم الهاتف',
                'class': 'form-control'
            }),
            'specialization': forms.TextInput(attrs={
                'placeholder': 'التخصص',
                'class': 'form-control'
            }),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DriverForm(forms.ModelForm):
    """نموذج السائق"""
    class Meta:
        model = Driver
        fields = ['name', 'phone', 'license_number', 'vehicle_number', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'اسم السائق',
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'رقم الهاتف',
                'class': 'form-control'
            }),
            'license_number': forms.TextInput(attrs={
                'placeholder': 'رقم الرخصة',
                'class': 'form-control'
            }),
            'vehicle_number': forms.TextInput(attrs={
                'placeholder': 'رقم المركبة',
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
    """نموذج فلترة التركيبات - محسّن للأداء"""
    STATUS_CHOICES = [
        ('', _('جميع الحالات')),
        ('needs_scheduling', _('بحاجة جدولة')),
        ('under_manufacturing', _('تحت التصنيع')),
        ('scheduled', _('مجدول')),
        ('in_installation', _('قيد التركيب')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
        ('modification_required', _('يحتاج تعديل')),
        ('modification_in_progress', _('التعديل قيد التنفيذ')),
        ('modification_completed', _('التعديل مكتمل')),
    ]

    # فلاتر أساسية
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label=_('حالة التركيب'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    team = forms.ModelChoiceField(
        queryset=InstallationTeam.objects.filter(is_active=True),
        required=False,
        label=_('الفريق'),
        empty_label=_('جميع الفرق'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    # فلاتر التاريخ
    date_from = forms.DateField(
        required=False,
        label=_('من تاريخ'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label=_('إلى تاريخ'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    # بحث ذكي
    search = forms.CharField(
        required=False,
        label=_('بحث سريع'),
        widget=forms.TextInput(attrs={
            'placeholder': 'رقم الطلب، اسم العميل، رقم الهاتف...',
            'class': 'form-control',
            'autocomplete': 'off'
        })
    )
    
    # فلاتر إضافية
    location_type = forms.ChoiceField(
        choices=[
            ('', _('جميع الأماكن')),
            ('open', _('مفتوح')),
            ('compound', _('كومبوند')),
        ],
        required=False,
        label=_('نوع المكان'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    order_status = forms.ChoiceField(
        choices=[
            ('', _('جميع حالات الطلب')),
            ('ready_install', _('جاهز للتركيب')),
            ('completed', _('مكتمل')),
            ('delivered', _('تم التسليم')),
        ],
        required=False,
        label=_('حالة الطلب'),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تحسين خيارات الفرق بناءً على البيانات الموجودة
        active_teams = InstallationTeam.objects.filter(
            is_active=True,
            installationschedule__isnull=False
        ).distinct()
        self.fields['team'].queryset = active_teams
        
        # إضافة CSS classes للتحسين البصري
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('class'):
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'


class DailyScheduleForm(forms.Form):
    """نموذج الجدول اليومي المحسن"""
    date = forms.DateField(
        label=_('التاريخ'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date()
    )
    
    team = forms.ModelChoiceField(
        queryset=InstallationTeam.objects.filter(is_active=True),
        required=False,
        label=_('الفريق'),
        empty_label=_('جميع الفرق'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', _('جميع الحالات')),
            ('scheduled', _('مجدول')),
            ('in_installation', _('قيد التركيب')),
            ('in_progress', _('قيد التنفيذ')),
            ('completed', _('مكتمل')),
            ('cancelled', _('ملغي')),
            ('modification_required', _('يحتاج تعديل')),
            ('modification_in_progress', _('التعديل قيد التنفيذ')),
            ('modification_completed', _('التعديل مكتمل')),
        ],
        required=False,
        label=_('حالة التركيب'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    salesperson = forms.ModelChoiceField(
        queryset=Salesperson.objects.filter(is_active=True),
        required=False,
        label=_('البائع'),
        empty_label=_('جميع البائعين'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_active=True),
        required=False,
        label=_('الفرع'),
        empty_label=_('جميع الفروع'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        label=_('بحث'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'بحث في أرقام الطلبات أو أسماء العملاء...'
        })
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
        fields = ['error_type', 'severity', 'error_description', 'root_cause', 'solution_applied', 
                 'prevention_measures', 'cost_impact', 'time_impact_hours']
        widgets = {
            'error_type': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
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
        fields = ['team', 'scheduled_date', 'scheduled_time', 'location_type', 'notes']
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
            'location_type': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'اختر نوع المكان'
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


class DailyScheduleForm(forms.Form):
    """نموذج فلترة الجدول اليومي للتركيبات"""
    date = forms.DateField(
        label='التاريخ',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'date-filter'
        }),
        initial=timezone.now().date()
    )
    
    status = forms.ChoiceField(
        label='الحالة',
        choices=[
            ('', 'جميع الحالات'),
            ('scheduled', 'مجدول'),
            ('in_installation', 'قيد التركيب'),
            ('completed', 'مكتمل'),
            ('cancelled', 'ملغي'),
            ('modification_required', 'يحتاج تعديل'),
            ('modification_in_progress', 'تعديل قيد التنفيذ'),
            ('modification_completed', 'تعديل مكتمل'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'status-filter'
        }),
        required=False
    )
    
    team = forms.ModelChoiceField(
        label='الفريق',
        queryset=InstallationTeam.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'team-filter'
        }),
        required=False,
        empty_label='جميع الفرق'
    )
    
    salesperson = forms.ModelChoiceField(
        label='البائع',
        queryset=Salesperson.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'salesperson-filter'
        }),
        required=False,
        empty_label='جميع البائعين'
    )
    
    branch = forms.ModelChoiceField(
        label='الفرع',
        queryset=Branch.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'branch-filter'
        }),
        required=False,
        empty_label='جميع الفروع'
    )
    
    search = forms.CharField(
        label='البحث',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم الطلب، اسم العميل، رقم الهاتف...',
            'id': 'search-filter'
        }),
        required=False
    )
