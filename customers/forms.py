from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import Customer, CustomerCategory, CustomerNote

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'name', 'image', 'category', 'customer_type',
            'phone', 'email', 'address', 'status', 'notes', 'interests'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(
                attrs={'class': 'form-control', 'dir': 'ltr'}
            ),
            'email': forms.EmailInput(
                attrs={'class': 'form-control', 'dir': 'ltr'}
            ),
            'address': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'interests': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and not user.is_superuser:
            self.instance.branch = user.branch
            self.instance.created_by = user

        # تحديث خيارات نوع العميل بشكل ديناميكي
        customer_types = Customer.get_customer_types()
        if not customer_types:
            from .models import CustomerType
            # إذا كانت القائمة فارغة، نجلب البيانات مباشرة
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

class CustomerNoteForm(forms.ModelForm):
    class Meta:
        model = CustomerNote
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('أضف ملاحظتك هنا...')
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

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
