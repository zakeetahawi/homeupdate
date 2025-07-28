"""
نماذج نظام النسخ الاحتياطي والاستعادة
"""
from django import forms
from .models import BackupJob, RestoreJob


class BackupForm(forms.Form):
    """نموذج إنشاء نسخة احتياطية"""
    
    name = forms.CharField(
        label='اسم النسخة الاحتياطية',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل اسم النسخة الاحتياطية'
        })
    )
    
    description = forms.CharField(
        label='الوصف',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'وصف اختياري للنسخة الاحتياطية'
        })
    )
    
    backup_type = forms.ChoiceField(
        label='نوع النسخة الاحتياطية',
        choices=BackupJob.TYPE_CHOICES,
        initial='full',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class RestoreForm(forms.Form):
    """نموذج الاستعادة"""
    
    name = forms.CharField(
        label='اسم عملية الاستعادة',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل اسم عملية الاستعادة'
        })
    )
    
    description = forms.CharField(
        label='الوصف',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'وصف اختياري لعملية الاستعادة'
        })
    )
    
    clear_existing_data = forms.BooleanField(
        label='حذف البيانات الموجودة قبل الاستعادة',
        required=False,
        help_text='تحذير: سيتم حذف جميع البيانات الموجودة قبل استعادة النسخة الاحتياطية',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class UploadBackupForm(forms.Form):
    """نموذج رفع ملف نسخة احتياطية"""
    
    backup_file = forms.FileField(
        label='ملف الن��خة الاحتياطية',
        help_text='اختر ملف النسخة الاحتياطية (.json أو .json.gz)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.json,.gz'
        })
    )
    
    name = forms.CharField(
        label='اسم عملية الاستعادة',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل اسم عملية الاستعادة'
        })
    )
    
    description = forms.CharField(
        label='الوصف',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'وصف اختياري لعملية الاستعادة'
        })
    )
    
    clear_existing_data = forms.BooleanField(
        label='حذف البيانات الموجودة قبل الاستعادة',
        required=False,
        help_text='تحذير: سيتم حذف جميع البيانات الموجودة قبل استعادة النسخة الاحتياطية',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_backup_file(self):
        """التحقق من صحة ملف النسخة الاحتياطية"""
        file = self.cleaned_data['backup_file']
        
        # التحقق من امتداد الملف
        allowed_extensions = ['.json', '.gz']
        file_extension = None
        
        for ext in allowed_extensions:
            if file.name.lower().endswith(ext):
                file_extension = ext
                break
        
        if not file_extension:
            raise forms.ValidationError(
                'نوع الملف غير مدعوم. يرجى رفع ملف .json أو .json.gz'
            )
        
        # التحقق من حجم الملف (حد أقصى 100 MB)
        max_size = 100 * 1024 * 1024  # 100 MB
        if file.size > max_size:
            raise forms.ValidationError(
                f'حجم الملف كبير جداً. الحد الأقصى المسموح: {max_size // (1024*1024)} MB'
            )
        
        return file


class BackupScheduleForm(forms.Form):
    """نموذج جدولة النسخ الاحتياطية"""
    
    name = forms.CharField(
        label='اسم الجدولة',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'أدخل اسم الجدولة'
        })
    )
    
    description = forms.CharField(
        label='الوصف',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'وصف اختياري للجدولة'
        })
    )
    
    frequency = forms.ChoiceField(
        label='التكرار',
        choices=[
            ('daily', 'يومياً'),
            ('weekly', 'أسبوعياً'),
            ('monthly', 'شهرياً'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    hour = forms.IntegerField(
        label='الساعة',
        min_value=0,
        max_value=23,
        initial=2,
        help_text='الساعة بنظام 24 ساعة (0-23)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    
    minute = forms.IntegerField(
        label='الدقيقة',
        min_value=0,
        max_value=59,
        initial=0,
        help_text='الدقيقة (0-59)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    
    backup_type = forms.ChoiceField(
        label='نوع النسخة الاحتياطية',
        choices=BackupJob.TYPE_CHOICES,
        initial='full',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    max_backups_to_keep = forms.IntegerField(
        label='عدد النسخ المحفوظة',
        min_value=1,
        max_value=30,
        initial=7,
        help_text='عدد النسخ الاحتياطية التي سيتم الاحتفاظ بها',
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    
    is_active = forms.BooleanField(
        label='نشط',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )