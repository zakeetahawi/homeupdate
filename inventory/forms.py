from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Product, Category, Warehouse
import pandas as pd
import openpyxl
from io import BytesIO
from django.core.files.uploadedfile import UploadedFile


class ProductExcelUploadForm(forms.Form):
    """
    نموذج لرفع المنتجات من ملف إكسل
    """
    excel_file = forms.FileField(
        label=_('ملف الإكسل'),
        help_text=_('يجب أن يكون الملف بصيغة .xlsx أو .xls'),
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label=_('المستودع'),
        required=True,
        empty_label=_('اختر المستودع'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    overwrite_existing = forms.BooleanField(
        label=_('استبدال المنتجات الموجودة'),
        required=False,
        initial=False,
        help_text=_('في حالة وجود منتج بنفس الكود، سيتم تحديث بياناته'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_excel_file(self):
        file = self.cleaned_data.get('excel_file')
        if not file:
            raise forms.ValidationError(_('يجب رفع ملف إكسل'))
        
        # التحقق من نوع الملف
        if not file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError(_('نوع الملف غير مدعوم. يرجى رفع ملف .xlsx أو .xls'))
        
        # التحقق من حجم الملف (حد أقصى 10 ميجابايت)
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('حجم الملف كبير جداً. الحد الأقصى 10 ميجابايت'))
        
        try:
            # محاولة قراءة الملف للتأكد من صحته
            file_data = file.read()
            
            # محاولة قراءة الملف بطريقة آمنة
            try:
                df = pd.read_excel(BytesIO(file_data), engine='openpyxl', keep_default_na=False)
            except Exception as e1:
                try:
                    df = pd.read_excel(BytesIO(file_data), engine='xlrd')
                except Exception as e2:
                    try:
                        df = pd.read_excel(BytesIO(file_data))
                    except Exception as e3:
                        # محاولة أخيرة مع openpyxl مع إعدادات خاصة
                        try:
                            from openpyxl import load_workbook
                            workbook = load_workbook(BytesIO(file_data), data_only=True, read_only=True)
                            sheet = workbook.active
                            data = []
                            for row in sheet.iter_rows(values_only=True):
                                if any(cell is not None for cell in row):
                                    data.append(row)
                            
                            if data:
                                headers = data[0]
                                rows = data[1:]
                                df = pd.DataFrame(rows, columns=headers)
                            else:
                                raise Exception("الملف فارغ")
                        except Exception as e4:
                            raise Exception(f"فشل في قراءة الملف: {str(e1)} | {str(e2)} | {str(e3)} | {str(e4)}")
            
            file.seek(0)  # إعادة تعيين مؤشر الملف
            
            # التحقق من وجود الأعمدة المطلوبة
            required_columns = ['اسم المنتج', 'السعر']
            missing_columns = []
            
            for col in required_columns:
                if col not in df.columns:
                    missing_columns.append(col)
            
            if missing_columns:
                raise forms.ValidationError(
                    _('الأعمدة التالية مفقودة في الملف: {}').format(', '.join(missing_columns))
                )
            
            # التحقق من وجود بيانات
            if df.empty:
                raise forms.ValidationError(_('الملف فارغ أو لا يحتوي على بيانات'))
            
            # التحقق من وجود بيانات في الأعمدة المطلوبة
            df_filtered = df.dropna(subset=['اسم المنتج', 'السعر'])
            if df_filtered.empty:
                raise forms.ValidationError(_('لا توجد بيانات صحيحة في الأعمدة المطلوبة'))
                
        except Exception as e:
            if isinstance(e, forms.ValidationError):
                raise e
            raise forms.ValidationError(_('خطأ في قراءة الملف: {}').format(str(e)))
        
        return file


class BulkStockUpdateForm(forms.Form):
    """
    نموذج لتحديث المخزون بالجملة
    """
    excel_file = forms.FileField(
        label=_('ملف تحديث المخزون'),
        help_text=_('ملف إكسل يحتوي على أكواد المنتجات والكميات الجديدة'),
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )
    
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label=_('المستودع'),
        required=True,
        empty_label=_('اختر المستودع'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    update_type = forms.ChoiceField(
        label=_('نوع التحديث'),
        choices=[
            ('replace', _('استبدال الكمية الحالية')),
            ('add', _('إضافة للكمية الحالية')),
            ('subtract', _('خصم من الكمية الحالية')),
        ],
        initial='replace',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    reason = forms.CharField(
        label=_('سبب التحديث'),
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('مثال: جرد، تصحيح، إلخ')
        })
    )

    def clean_excel_file(self):
        file = self.cleaned_data.get('excel_file')
        if not file:
            raise forms.ValidationError(_('يجب رفع ملف إكسل'))
        
        # التحقق من نوع الملف
        if not file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError(_('نوع الملف غير مدعوم. يرجى رفع ملف .xlsx أو .xls'))
        
        # التحقق من حجم الملف (حد أقصى 10 ميجابايت)
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('حجم الملف كبير جداً. الحد الأقصى 10 ميجابايت'))
        
        try:
            # محاولة قراءة الملف للتأكد من صحته
            file_data = file.read()
            
            # محاولة قراءة الملف بطريقة آمنة
            try:
                df = pd.read_excel(BytesIO(file_data), engine='openpyxl', keep_default_na=False)
            except Exception as e1:
                try:
                    df = pd.read_excel(BytesIO(file_data), engine='xlrd')
                except Exception as e2:
                    try:
                        df = pd.read_excel(BytesIO(file_data))
                    except Exception as e3:
                        # محاولة أخيرة مع openpyxl مع إعدادات خاصة
                        try:
                            from openpyxl import load_workbook
                            workbook = load_workbook(BytesIO(file_data), data_only=True, read_only=True)
                            sheet = workbook.active
                            data = []
                            for row in sheet.iter_rows(values_only=True):
                                if any(cell is not None for cell in row):
                                    data.append(row)
                            
                            if data:
                                headers = data[0]
                                rows = data[1:]
                                df = pd.DataFrame(rows, columns=headers)
                            else:
                                raise Exception("الملف فارغ")
                        except Exception as e4:
                            raise Exception(f"فشل في قراءة الملف: {str(e1)} | {str(e2)} | {str(e3)} | {str(e4)}")
            
            file.seek(0)  # إعادة تعيين مؤشر الملف
            
            # التحقق من وجود الأعمدة المطلوبة
            required_columns = ['كود المنتج', 'الكمية']
            missing_columns = []
            
            for col in required_columns:
                if col not in df.columns:
                    missing_columns.append(col)
            
            if missing_columns:
                raise forms.ValidationError(
                    _('الأعمدة التالية مفقودة في الملف: {}').format(', '.join(missing_columns))
                )
            
            # التحقق من وجود بيانات
            if df.empty:
                raise forms.ValidationError(_('الملف فارغ أو لا يحتوي على بيانات'))
            
            # التحقق من وجود بيانات في الأعمدة المطلوبة
            df_filtered = df.dropna(subset=['كود المنتج', 'الكمية'])
            if df_filtered.empty:
                raise forms.ValidationError(_('لا توجد بيانات صحيحة في الأعمدة المطلوبة'))
                
        except Exception as e:
            if isinstance(e, forms.ValidationError):
                raise e
            raise forms.ValidationError(_('خطأ في قراءة الملف: {}').format(str(e)))
        
        return file


class ProductForm(forms.ModelForm):
    """
    نموذج لإضافة/تعديل منتج واحد
    """
    class Meta:
        model = Product
        fields = ['name', 'code', 'category', 'description', 'price', 'currency', 'unit', 'minimum_stock']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].empty_label = _('اختر الفئة')
        
        # إضافة خيارات العملة
        self.fields['currency'].choices = [
            ('EGP', _('جنيه مصري')),
            ('USD', _('دولار أمريكي')),
            ('EUR', _('يورو')),
        ]
