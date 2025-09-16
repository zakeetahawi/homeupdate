from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import json

from .models import Report, ReportSchedule


class ReportForm(forms.ModelForm):
    DAYS_CHOICES = [
        (7, '7'),
        (14, '14'),
        (30, '30'),
        (90, '90'),
    ]

    ACTIVITY_CHOICES = [
        ('customers', _('عملاء')),
        ('orders', _('طلبات')),
        ('inspections', _('معاينات')),
        ('all', _('الكل')),
    ]

    days = forms.ChoiceField(choices=DAYS_CHOICES, label=_('عدد الأيام'), initial=7, required=False)
    activity = forms.ChoiceField(choices=ACTIVITY_CHOICES, label=_('نوع النشاط'), initial='customers', required=False)
    from django.contrib.auth.models import Group
    seller_roles = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        label=_('أدوار المستخدمين (اختر واحدة أو أكثر)'),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Report
        fields = ['title', 'report_type', 'description', 'parameters']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'parameters': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

        # ensure report_type choices reflect model choices (including seller_activity)
        try:
            self.fields['report_type'].choices = Report.REPORT_TYPE_CHOICES
        except Exception:
            pass

        # populate helper fields from existing parameters if present
        if instance and getattr(instance, 'parameters', None):
            params = instance.parameters or {}
            if 'days' in params:
                self.fields['days'].initial = params.get('days')
            if 'activity' in params:
                self.fields['activity'].initial = params.get('activity')
            # support both legacy seller_group (bool) and new seller_roles (list of ids)
            if 'seller_roles' in params:
                try:
                    self.fields['seller_roles'].initial = params.get('seller_roles')
                except Exception:
                    pass
            elif 'seller_group' in params:
                # legacy: if true, leave seller_roles empty (user can select)
                self.fields['seller_roles'].initial = []

    def clean_parameters(self):
        parameters = self.cleaned_data.get('parameters')
        if parameters is None or parameters == '':
            return {}
        if isinstance(parameters, dict):
            return parameters
        # if it's a string, try parse JSON
        try:
            parsed = json.loads(parameters)
            if not isinstance(parsed, dict):
                raise ValidationError(_('المعلمات يجب أن تكون كائن JSON صحيح'))
            return parsed
        except json.JSONDecodeError:
            raise ValidationError(_('تنسيق JSON غير صحيح'))


class ReportScheduleForm(forms.ModelForm):
    class Meta:
        model = ReportSchedule
        fields = ['name', 'frequency', 'parameters', 'recipients']
        widgets = {
            'parameters': forms.Textarea(attrs={'rows': 4}),
            'recipients': forms.SelectMultiple(attrs={'class': 'select2'}),
        }

    def clean_parameters(self):
        parameters = self.cleaned_data.get('parameters')
        if parameters is None or parameters == '':
            return {}
        if isinstance(parameters, dict):
            return parameters
        try:
            parsed = json.loads(parameters)
            if not isinstance(parsed, dict):
                raise ValidationError(_('المعلمات يجب أن تكون كائن JSON صحيح'))
            return parsed
        except json.JSONDecodeError:
            raise ValidationError(_('تنسيق JSON غير صحيح'))
