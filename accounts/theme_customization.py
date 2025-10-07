"""
نموذج تخصيص الثيمات
Theme Customization Model
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
import json

User = get_user_model()


class ThemeCustomization(models.Model):
    """
    نموذج لحفظ تخصيصات الثيم لكل مستخدم
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='theme_customization',
        verbose_name=_('المستخدم')
    )
    
    # الثيم الأساسي المستخدم
    base_theme = models.CharField(
        max_length=50,
        default='default',
        verbose_name=_('الثيم الأساسي')
    )
    
    # الخلفيات
    background_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الخلفية الرئيسية'))
    surface_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون السطح'))
    card_bg_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('خلفية البطاقات'))
    elevated_bg_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('خلفية مرتفعة'))
    table_bg_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('خلفية الجداول'))
    filter_bg_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('خلفية الفلاتر'))
    input_bg_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('خلفية الحقول'))
    
    # Header & Footer
    navbar_bg_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('خلفية Navbar'))
    navbar_text_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('نص Navbar'))
    footer_bg_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('خلفية Footer'))
    footer_text_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('نص Footer'))
    
    # الألوان الأساسية
    primary_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('اللون الأساسي'))
    secondary_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('اللون الثانوي'))
    accent_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الإبراز'))
    
    # ألوان النصوص
    text_primary_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('النص الأساسي'))
    text_secondary_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('النص الثانوي'))
    text_tertiary_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('النص الثالثي'))
    
    # ألوان الحالة
    success_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون النجاح'))
    warning_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون التحذير'))
    error_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الخطأ'))
    info_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون المعلومات'))
    
    # الحدود والفواصل
    border_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الحدود'))
    separator_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الفواصل'))
    
    # الأيقونات
    icon_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الأيقونات'))
    icon_hover_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الأيقونات عند التمرير'))
    
    # الروابط
    link_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الروابط'))
    link_hover_color = models.CharField(max_length=7, blank=True, null=True, verbose_name=_('لون الروابط عند التمرير'))
    
    # تخصيصات متقدمة (JSON)
    advanced_customization = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('تخصيصات متقدمة'),
        help_text=_('تخصيصات إضافية بصيغة JSON')
    )
    
    # التواريخ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))
    
    # نشط
    is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
    
    class Meta:
        verbose_name = _('تخصيص الثيم')
        verbose_name_plural = _('تخصيصات الثيمات')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"تخصيص {self.user.username} - {self.base_theme}"
    
    def get_css_variables(self):
        """
        إرجاع متغيرات CSS كقاموس
        """
        variables = {}
        
        if self.background_color:
            variables['--background'] = self.background_color
        if self.surface_color:
            variables['--surface'] = self.surface_color
        if self.card_bg_color:
            variables['--card-bg'] = self.card_bg_color
        if self.elevated_bg_color:
            variables['--elevated-bg'] = self.elevated_bg_color
        if self.table_bg_color:
            variables['--table-bg'] = self.table_bg_color
        if self.filter_bg_color:
            variables['--filter-bg'] = self.filter_bg_color
        if self.input_bg_color:
            variables['--input-bg'] = self.input_bg_color
        
        if self.primary_color:
            variables['--primary'] = self.primary_color
        if self.secondary_color:
            variables['--secondary'] = self.secondary_color
        if self.accent_color:
            variables['--accent'] = self.accent_color
        
        if self.text_primary_color:
            variables['--text-primary'] = self.text_primary_color
        if self.text_secondary_color:
            variables['--text-secondary'] = self.text_secondary_color
        if self.text_tertiary_color:
            variables['--text-tertiary'] = self.text_tertiary_color
        
        if self.success_color:
            variables['--success'] = self.success_color
        if self.warning_color:
            variables['--warning'] = self.warning_color
        if self.error_color:
            variables['--error'] = self.error_color
        if self.info_color:
            variables['--info'] = self.info_color
        
        if self.border_color:
            variables['--border'] = self.border_color
        if self.separator_color:
            variables['--separator'] = self.separator_color
        
        if self.link_color:
            variables['--link-color'] = self.link_color
        if self.link_hover_color:
            variables['--link-hover-color'] = self.link_hover_color
        
        if self.icon_color:
            variables['--icon-color'] = self.icon_color
        if self.icon_hover_color:
            variables['--icon-hover-color'] = self.icon_hover_color
        
        return variables
    
    def to_json(self):
        """
        تصدير التخصيصات كـ JSON
        """
        data = {
            'base_theme': self.base_theme,
            'colors': {
                'background': self.background_color,
                'surface': self.surface_color,
                'card_bg': self.card_bg_color,
                'elevated_bg': self.elevated_bg_color,
                'table_bg': self.table_bg_color,
                'filter_bg': self.filter_bg_color,
                'input_bg': self.input_bg_color,
                'primary': self.primary_color,
                'secondary': self.secondary_color,
                'accent': self.accent_color,
                'text_primary': self.text_primary_color,
                'text_secondary': self.text_secondary_color,
                'text_tertiary': self.text_tertiary_color,
                'success': self.success_color,
                'warning': self.warning_color,
                'error': self.error_color,
                'info': self.info_color,
                'border': self.border_color,
                'separator': self.separator_color,
                'link': self.link_color,
                'link_hover': self.link_hover_color,
                'icon': self.icon_color,
                'icon_hover': self.icon_hover_color,
                'navbar_bg': self.navbar_bg_color,
                'navbar_text': self.navbar_text_color,
                'footer_bg': self.footer_bg_color,
                'footer_text': self.footer_text_color,
            }
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def reset_to_defaults(self):
        """
        إعادة تعيين جميع التخصيصات للقيم الافتراضية
        """
        self.background_color = None
        self.surface_color = None
        self.card_bg_color = None
        self.elevated_bg_color = None
        self.table_bg_color = None
        self.filter_bg_color = None
        self.input_bg_color = None
        self.primary_color = None
        self.secondary_color = None
        self.accent_color = None
        self.text_primary_color = None
        self.text_secondary_color = None
        self.text_tertiary_color = None
        self.success_color = None
        self.warning_color = None
        self.error_color = None
        self.info_color = None
        self.border_color = None
        self.separator_color = None
        self.link_color = None
        self.link_hover_color = None
        self.icon_color = None
        self.icon_hover_color = None
        self.navbar_bg_color = None
        self.navbar_text_color = None
        self.footer_bg_color = None
        self.footer_text_color = None
        self.advanced_customization = None
        self.save()
