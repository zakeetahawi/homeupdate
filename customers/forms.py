from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re
from .models import Customer, CustomerCategory, CustomerNote, DiscountType, CustomerResponsible
from accounts.models import Branch

class CustomerForm(forms.ModelForm):
    phone2 = forms.CharField(
        label=_('رقم الهاتف الثاني'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'dir': 'ltr',
            'placeholder': '01234567890 (اختياري)',
            'maxlength': '11',
            'pattern': '^01[0-9]{9}$',
            'title': 'يجب أن يكون الرقم 11 رقم ويبدأ بـ 01',
            'data-check-duplicate': 'true',
            'autocomplete': 'tel'
        })
    )

    class Meta:
        model = Customer
        fields = [
            'name', 'phone', 'phone2', 'email', 'birth_date', 'address',
            'customer_type', 'category', 'status', 'interests',
            'image', 'discount_type'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': '01234567890',
                'maxlength': '11',
                'pattern': '^01[0-9]{9}$',
                'title': 'يجب أن يكون الرقم 11 رقم ويبدأ بـ 01',
                'data-check-duplicate': 'true',
                'autocomplete': 'tel'
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'اختر تاريخ الميلاد',
                'title': 'أدخل الشهر واليوم فقط'
            }),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'interests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'اختر نوع الخصم (اختياري)'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'branch') and user.branch:
            if user.branch.is_main_branch:
                # If user is from main branch, add branch field
                Branch = type(user.branch)
                self.fields['branch'] = forms.ModelChoiceField(
                    queryset=Branch.objects.filter(is_active=True),
                    label=_('الفرع'),
                    required=True,
                    empty_label=_('اختر الفرع'),
                    widget=forms.Select(attrs={
                        'class': 'form-select',
                        'required': 'required'
                    })
                )
                if 'branch' not in self._meta.fields:
                    self._meta.fields.append('branch')
            else:
                # If user is not from main branch, their branch will be set in the view
                self.fields.pop('branch', None)

        # Update customer type choices dynamically
        customer_types = Customer.get_customer_types()
        if not customer_types:
            from .models import CustomerType
            types = [(t.code, t.name) 
                    for t in CustomerType.objects.filter(is_active=True).order_by('name')]
            self.fields['customer_type'].choices = types
        else:
            self.fields['customer_type'].choices = customer_types

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (limit to 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError(_('حجم الصورة يجب أن لا يتجاوز 5 ميجابايت'))
            
            # Check file extension
            allowed_extensions = ['jpg', 'jpeg', 'png']
            ext = image.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise ValidationError(_('يجب أن تكون الصورة بصيغة JPG أو PNG'))
            
        return image

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # تنظيف الرقم من المسافات والرموز
            phone = re.sub(r'[^\d]', '', phone)

            # فحص صيغة الرقم
            if not re.match(r'^01[0-9]{9}$', phone):
                raise ValidationError(
                    _('رقم الهاتف يجب أن يكون 11 رقم ويبدأ بـ 01 (مثال: 01234567890)'),
                    code='invalid_phone_format'
                )

            # فحص التكرار
            qs = Customer.objects.filter(phone=phone)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                existing = qs.first()
                # إضافة معلومات العميل الموجود للاستخدام في القالب
                self.existing_customer = existing
                raise ValidationError(
                    _('رقم الهاتف مستخدم بالفعل للعميل: %(name)s (الفرع: %(branch)s)'),
                    code='duplicate_phone',
                    params={
                        'name': existing.name,
                        'branch': existing.branch.name if existing.branch else '-',
                        'customer_id': existing.pk,
                        'customer_url': f'/customers/{existing.pk}/'
                    }
                )
        return phone

    def clean_phone2(self):
        phone2 = self.cleaned_data.get('phone2')
        if phone2:
            # تنظيف الرقم من المسافات والرموز
            phone2 = re.sub(r'[^\d]', '', phone2)

            # فحص صيغة الرقم
            if not re.match(r'^01[0-9]{9}$', phone2):
                raise ValidationError(
                    _('رقم الهاتف الثاني يجب أن يكون 11 رقم ويبدأ بـ 01 (مثال: 01234567890)'),
                    code='invalid_phone2_format'
                )

            # فحص التكرار
            qs = Customer.objects.filter(phone2=phone2)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                existing = qs.first()
                raise ValidationError(
                    _('رقم الهاتف الثاني مستخدم بالفعل للعميل: %(name)s (الفرع: %(branch)s)'),
                    code='duplicate_phone2',
                    params={
                        'name': existing.name,
                        'branch': existing.branch.name if existing.branch else '-',
                        'customer_id': existing.pk,
                        'customer_url': f'/customers/{existing.pk}/'
                    }
                )

            # فحص أن الرقم الثاني مختلف عن الرقم الأول
            phone = self.cleaned_data.get('phone')
            if phone and phone == phone2:
                raise ValidationError(
                    _('رقم الهاتف الثاني يجب أن يكون مختلف عن رقم الهاتف الأول'),
                    code='same_phone_numbers'
                )

        return phone2

class CustomerNoteForm(forms.ModelForm):
    note = forms.CharField(
        label=_('الملاحظة'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('أضف ملاحظتك هنا...'),
            'required': True
        }),
        required=True,
        error_messages={
            'required': _('يرجى كتابة الملاحظة قبل الإضافة'),
        }
    )

    class Meta:
        model = CustomerNote
        fields = ['note']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_note(self):
        note = self.cleaned_data.get('note')
        if not note or not note.strip():
            raise forms.ValidationError(_('يرجى كتابة الملاحظة قبل الإضافة'))
        return note.strip()

    def save(self, commit=True):
        note = super().save(commit=False)
        if self.user:
            note.created_by = self.user
        if commit:
            note.save()
        return note

class CustomerSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('بحث عن عميل...')
        })
    )
    category = forms.ModelChoiceField(
        queryset=CustomerCategory.objects.all(),
        required=False,
        empty_label=_('كل التصنيفات'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_active=True),
        required=False,
        empty_label=_('كل الفروع'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    customer_type = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', _('كل الحالات'))] + list(Customer.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update customer type choices dynamically
        self.fields['customer_type'].choices = (
            [('', _('كل الأنواع'))] + list(Customer.get_customer_types())
        )





class CustomerResponsibleForm(forms.ModelForm):
    """نموذج مسؤولي العملاء"""

    class Meta:
        model = CustomerResponsible
        fields = ['name', 'position', 'phone', 'email', 'is_primary']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم المسؤول',
                'required': True
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المنصب (اختياري)'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': '01234567890',
                'pattern': '^01[0-9]{9}$',
                'title': 'يجب أن يكون الرقم 11 رقم ويبدأ بـ 01'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': 'البريد الإلكتروني (اختياري)'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # تنظيف الرقم من المسافات والرموز
            phone = re.sub(r'[^\d]', '', phone)

            # فحص صيغة الرقم
            if not re.match(r'^01[0-9]{9}$', phone):
                raise ValidationError(
                    _('رقم الهاتف يجب أن يكون 11 رقم ويبدأ بـ 01 (مثال: 01234567890)')
                )
        return phone


# FormSet للمسؤولين
CustomerResponsibleFormSet = forms.inlineformset_factory(
    Customer,
    CustomerResponsible,
    form=CustomerResponsibleForm,
    extra=1,
    max_num=3,
    can_delete=True,
    fields=['name', 'position', 'phone', 'email', 'is_primary']
)
