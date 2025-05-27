"""
نماذج إدارة قواعد البيانات على طراز أودو
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Database, Backup, BackupSchedule, GoogleDriveConfig


class DatabaseForm(forms.ModelForm):
    """نموذج إنشاء وتعديل قاعدة البيانات"""

    class Meta:
        model = Database
        fields = ['name', 'db_type', 'connection_info']
        widgets = {
            'connection_info': forms.Textarea(attrs={'rows': 5, 'dir': 'ltr'}),
        }


class BackupForm(forms.ModelForm):
    """نموذج إنشاء نسخة احتياطية"""

    database = forms.ModelChoiceField(
        queryset=Database.objects.all(),
        label=_('قاعدة البيانات'),
        empty_label=_('-- اختر قاعدة البيانات --'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Backup
        fields = ['database', 'name', 'backup_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'backup_type': forms.Select(attrs={'class': 'form-select'}),
        }


class BackupRestoreForm(forms.Form):
    """نموذج استعادة نسخة احتياطية"""

    clear_data = forms.BooleanField(
        label=_('حذف البيانات الحالية قبل الاستعادة'),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class BackupUploadForm(forms.Form):
    """نموذج تحميل ملف نسخة احتياطية"""

    database = forms.ModelChoiceField(
        queryset=Database.objects.all(),
        label=_('قاعدة البيانات'),
        empty_label=_('-- اختر قاعدة البيانات --'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    backup_file = forms.FileField(
        label=_('ملف النسخة الاحتياطية'),
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    backup_type = forms.ChoiceField(
        label=_('نوع النسخة الاحتياطية'),
        choices=Backup.BACKUP_TYPES,
        initial='full',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    clear_data = forms.BooleanField(
        label=_('حذف البيانات الحالية قبل الاستعادة'),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class BackupScheduleForm(forms.ModelForm):
    """نموذج جدولة النسخ الاحتياطية"""

    database = forms.ModelChoiceField(
        queryset=Database.objects.all(),
        label=_('قاعدة البيانات'),
        empty_label=_('-- اختر قاعدة البيانات --'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = BackupSchedule
        fields = [
            'database', 'name', 'backup_type', 'frequency',
            'hour', 'minute', 'day_of_week', 'day_of_month',
            'max_backups', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'backup_type': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'hour': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 23}),
            'minute': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 59}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'day_of_month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'max_backups': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 24}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['day_of_week'].required = False
        self.fields['day_of_month'].required = False

    def clean(self):
        cleaned_data = super().clean()
        frequency = cleaned_data.get('frequency')
        day_of_week = cleaned_data.get('day_of_week')
        day_of_month = cleaned_data.get('day_of_month')

        if frequency == 'weekly' and day_of_week is None:
            self.add_error('day_of_week', _('يجب تحديد يوم الأسبوع للتكرار الأسبوعي'))

        if frequency == 'monthly' and day_of_month is None:
            self.add_error('day_of_month', _('يجب تحديد يوم الشهر للتكرار الشهري'))

        return cleaned_data


class GoogleDriveConfigForm(forms.ModelForm):
    """نموذج إعدادات Google Drive"""

    class Meta:
        model = GoogleDriveConfig
        fields = [
            'name', 'inspections_folder_id', 'inspections_folder_name',
            'credentials_file', 'filename_pattern', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'inspections_folder_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
            }),
            'inspections_folder_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: ملفات المعاينات'
            }),
            'credentials_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.json'
            }),
            'filename_pattern': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إضافة نص المساعدة
        self.fields['inspections_folder_id'].help_text = _(
            'معرف المجلد في Google Drive. يمكن الحصول عليه من رابط المجلد'
        )
        self.fields['credentials_file'].help_text = _(
            'ملف JSON من Google Cloud Console (Service Account Key)'
        )
        self.fields['filename_pattern'].help_text = _(
            'نمط تسمية الملفات: اسم_العميل_الفرع_التاريخ_رقم_الطلب.pdf'
        )

    def clean_inspections_folder_id(self):
        folder_id = self.cleaned_data.get('inspections_folder_id')
        if folder_id:
            # إزالة أي مسافات أو رموز إضافية
            folder_id = folder_id.strip()
            # التحقق من صحة معرف المجلد (يجب أن يكون نص بدون مسافات)
            if ' ' in folder_id or len(folder_id) < 10:
                raise forms.ValidationError(_('معرف المجلد غير صحيح'))
        return folder_id

    def clean_credentials_file(self):
        file = self.cleaned_data.get('credentials_file')
        if file:
            # التحقق من أن الملف JSON
            if not file.name.endswith('.json'):
                raise forms.ValidationError(_('يجب أن يكون الملف من نوع JSON'))

            # التحقق من حجم الملف (أقل من 1MB)
            if file.size > 1024 * 1024:
                raise forms.ValidationError(_('حجم الملف كبير جداً (الحد الأقصى 1MB)'))

        return file
