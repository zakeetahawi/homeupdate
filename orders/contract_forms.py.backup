"""
نماذج إدخال بيانات العقود
"""
from django import forms
from .contract_models import ContractTemplate, ContractCurtain
from .models import Order, OrderItem


class ContractCurtainForm(forms.ModelForm):
    """نموذج إدخال بيانات الستارة"""
    
    class Meta:
        model = ContractCurtain
        fields = [
            'sequence', 'room_name', 'width', 'height', 'curtain_image',
            # القماش الخفيف
            'light_fabric', 'light_fabric_meters', 'light_fabric_tailoring', 'light_fabric_tailoring_size',
            # القماش الثقيل
            'heavy_fabric', 'heavy_fabric_meters', 'heavy_fabric_tailoring', 'heavy_fabric_tailoring_size',
            # البلاك أوت
            'blackout_fabric', 'blackout_fabric_meters', 'blackout_fabric_tailoring', 'blackout_fabric_tailoring_size',
            # الإكسسوارات
            'wood_quantity', 'wood_type',
            'track_type', 'track_quantity',
            'pipe', 'pipe_quantity',
            'bracket', 'bracket_quantity',
            'finial', 'finial_quantity',
            'ring', 'ring_quantity',
            'hanger', 'hanger_quantity',
            'valance', 'valance_quantity',
            'tassel', 'tassel_quantity',
            'tieback_fabric', 'tieback_quantity',
            'belt', 'belt_quantity',
            'notes'
        ]
        widgets = {
            'sequence': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'room_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الغرفة'}),
            'width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'العرض بالمتر'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'الطول بالمتر'}),
            'curtain_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            
            # القماش الخفيف
            'light_fabric': forms.Select(attrs={'class': 'form-control select2'}),
            'light_fabric_meters': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'light_fabric_tailoring': forms.Select(attrs={'class': 'form-control'}),
            'light_fabric_tailoring_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مقاس الشريط'}),
            
            # القماش الثقيل
            'heavy_fabric': forms.Select(attrs={'class': 'form-control select2'}),
            'heavy_fabric_meters': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'heavy_fabric_tailoring': forms.Select(attrs={'class': 'form-control'}),
            'heavy_fabric_tailoring_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مقاس الشريط'}),
            
            # البلاك أوت
            'blackout_fabric': forms.Select(attrs={'class': 'form-control select2'}),
            'blackout_fabric_meters': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'blackout_fabric_tailoring': forms.Select(attrs={'class': 'form-control'}),
            'blackout_fabric_tailoring_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مقاس الشريط'}),
            
            # الإكسسوارات
            'wood_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'wood_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نوع الخشب'}),
            'track_type': forms.Select(attrs={'class': 'form-control select2'}),
            'track_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'pipe': forms.Select(attrs={'class': 'form-control select2'}),
            'pipe_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'bracket': forms.Select(attrs={'class': 'form-control select2'}),
            'bracket_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'finial': forms.Select(attrs={'class': 'form-control select2'}),
            'finial_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'ring': forms.Select(attrs={'class': 'form-control select2'}),
            'ring_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'hanger': forms.Select(attrs={'class': 'form-control select2'}),
            'hanger_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'valance': forms.Select(attrs={'class': 'form-control select2'}),
            'valance_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'tassel': forms.Select(attrs={'class': 'form-control select2'}),
            'tassel_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'tieback_fabric': forms.Select(attrs={'class': 'form-control select2'}),
            'tieback_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'belt': forms.Select(attrs={'class': 'form-control select2'}),
            'belt_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '3', 'placeholder': 'ملاحظات وشرح'}),
        }
    
    def __init__(self, *args, **kwargs):
        order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        
        # تحديد خيارات القوائم المنسدلة من عناصر الفاتورة
        if order:
            order_items = OrderItem.objects.filter(order=order)
            
            # تحديث خيارات جميع حقول الإكسسوارات
            fabric_fields = [
                'light_fabric', 'heavy_fabric', 'blackout_fabric',
                'track_type', 'pipe', 'bracket', 'finial', 'ring',
                'hanger', 'valance', 'tassel', 'tieback_fabric', 'belt'
            ]
            
            for field_name in fabric_fields:
                if field_name in self.fields:
                    self.fields[field_name].queryset = order_items
                    self.fields[field_name].required = False
                    # إضافة خيار فارغ
                    self.fields[field_name].empty_label = '--- اختر ---'


class ContractTemplateForm(forms.ModelForm):
    """نموذج إنشاء وتحرير قالب العقد"""
    
    class Meta:
        model = ContractTemplate
        fields = [
            'name', 'template_type', 'is_active', 'is_default',
            'company_name', 'company_logo', 'company_address', 'company_phone',
            'company_email', 'company_website', 'company_tax_number', 'company_commercial_register',
            'primary_color', 'secondary_color', 'accent_color',
            'font_family', 'font_size', 'page_size', 'page_margins',
            'show_company_logo', 'show_order_details', 'show_customer_details',
            'show_items_table', 'show_payment_details', 'show_terms', 'show_signatures',
            'header_text', 'footer_text', 'terms_text'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'template_type': forms.Select(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_address': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
            'company_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'company_website': forms.URLInput(attrs={'class': 'form-control'}),
            'company_tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'company_commercial_register': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'font_family': forms.TextInput(attrs={'class': 'form-control'}),
            'font_size': forms.NumberInput(attrs={'class': 'form-control', 'min': '8', 'max': '24'}),
            'page_size': forms.Select(attrs={'class': 'form-control'}),
            'page_margins': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '50'}),
            'header_text': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'footer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'terms_text': forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}),
        }

