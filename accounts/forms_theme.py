"""
نماذج تخصيص الثيمات
Theme Customization Forms
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from .theme_customization import ThemeCustomization


class ThemeCustomizationForm(forms.ModelForm):
    """
    نموذج تخصيص الثيم
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل base_theme غير مطلوب لأنه مخفي
        self.fields['base_theme'].required = False
        # إذا لم يكن له قيمة، استخدم default
        if not self.instance.base_theme:
            self.instance.base_theme = 'default'
    
    class Meta:
        model = ThemeCustomization
        exclude = ['user', 'created_at', 'updated_at', 'advanced_customization']
        widgets = {
            'base_theme': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_base_theme'
            }),
            # الخلفيات
            'background_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الخلفية الرئيسية'
            }),
            'surface_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون السطح'
            }),
            'card_bg_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر خلفية البطاقات'
            }),
            'elevated_bg_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر خلفية مرتفعة'
            }),
            'table_bg_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر خلفية الجداول'
            }),
            'filter_bg_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر خلفية الفلاتر'
            }),
            'input_bg_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر خلفية الحقول'
            }),
            # Navbar & Footer
            'navbar_bg_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر خلفية Navbar'
            }),
            'navbar_text_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون نص Navbar'
            }),
            'footer_bg_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر خلفية Footer'
            }),
            'footer_text_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون نص Footer'
            }),
            # الألوان الأساسية
            'primary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر اللون الأساسي'
            }),
            'secondary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر اللون الثانوي'
            }),
            'accent_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الإبراز'
            }),
            # ألوان النصوص
            'text_primary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون النص الأساسي'
            }),
            'text_secondary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون النص الثانوي'
            }),
            'text_tertiary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون النص الثالثي'
            }),
            # ألوان الحالة
            'success_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون النجاح'
            }),
            'warning_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون التحذير'
            }),
            'error_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الخطأ'
            }),
            'info_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون المعلومات'
            }),
            # الحدود والفواصل
            'border_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الحدود'
            }),
            'separator_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الفواصل'
            }),
            # الأيقونات
            'icon_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الأيقونات'
            }),
            'icon_hover_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الأيقونات عند التمرير'
            }),
            # الروابط
            'link_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الروابط'
            }),
            'link_hover_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'title': 'اختر لون الروابط عند التمرير'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'base_theme': _('الثيم الأساسي'),
            'background_color': _('🎨 خلفية رئيسية'),
            'surface_color': _('📄 سطح'),
            'card_bg_color': _('🎴 خلفية البطاقات'),
            'elevated_bg_color': _('⬆️ خلفية مرتفعة'),
            'table_bg_color': _('📋 خلفية الجداول'),
            'filter_bg_color': _('🔍 خلفية الفلاتر'),
            'input_bg_color': _('📝 خلفية الحقول'),
            'navbar_bg_color': _('🎯 خلفية Navbar'),
            'navbar_text_color': _('📝 نص Navbar'),
            'footer_bg_color': _('📌 خلفية Footer'),
            'footer_text_color': _('📝 نص Footer'),
            'primary_color': _('🎨 لون أساسي'),
            'secondary_color': _('🎨 لون ثانوي'),
            'accent_color': _('✨ لون إبراز'),
            'text_primary_color': _('✍️ نص أساسي'),
            'text_secondary_color': _('✍️ نص ثانوي'),
            'text_tertiary_color': _('✍️ نص ثالثي'),
            'success_color': _('✅ نجاح'),
            'warning_color': _('⚠️ تحذير'),
            'error_color': _('❌ خطأ'),
            'info_color': _('ℹ️ معلومات'),
            'border_color': _('📐 حدود'),
            'separator_color': _('➖ فواصل'),
            'icon_color': _('🎭 أيقونات'),
            'icon_hover_color': _('🎭 أيقونات (تمرير)'),
            'link_color': _('🔗 روابط'),
            'link_hover_color': _('🔗 روابط (تمرير)'),
            'is_active': _('نشط'),
        }
