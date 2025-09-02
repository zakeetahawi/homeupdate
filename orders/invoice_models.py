"""
نماذج إدارة الفواتير وقوالبها
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class InvoiceTemplate(models.Model):
    """نموذج قالب الفاتورة"""
    
    TEMPLATE_TYPES = [
        ('standard', 'قالب عادي'),
        ('detailed', 'قالب مفصل'),
        ('minimal', 'قالب مبسط'),
        ('custom', 'قالب مخصص'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='اسم القالب')
    template_type = models.CharField(
        max_length=20, 
        choices=TEMPLATE_TYPES, 
        default='standard',
        verbose_name='نوع القالب'
    )
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    is_default = models.BooleanField(default=False, verbose_name='افتراضي')
    
    # إعدادات الشركة
    company_name = models.CharField(max_length=200, verbose_name='اسم الشركة')
    company_logo = models.ImageField(
        upload_to='invoice_templates/logos/', 
        blank=True, 
        null=True,
        verbose_name='شعار الشركة'
    )
    company_address = models.TextField(verbose_name='عنوان الشركة')
    company_phone = models.CharField(max_length=100, blank=True, verbose_name='هاتف الشركة')
    company_email = models.EmailField(blank=True, verbose_name='بريد الشركة')
    company_website = models.URLField(blank=True, verbose_name='موقع الشركة')
    
    # إعدادات التصميم المتقدمة
    primary_color = models.CharField(
        max_length=7, 
        default='#0d6efd',
        verbose_name='اللون الأساسي',
        help_text='مثل: #0d6efd (أزرق)'
    )
    secondary_color = models.CharField(
        max_length=7, 
        default='#198754',
        verbose_name='اللون الثانوي',
        help_text='مثل: #198754 (أخضر)'
    )
    accent_color = models.CharField(
        max_length=7,
        default='#ffc107',
        verbose_name='لون التمييز',
        help_text='مثل: #ffc107 (أصفر)'
    )
    font_family = models.CharField(
        max_length=100,
        default='Cairo, Arial, sans-serif',
        verbose_name='نوع الخط',
        choices=[
            ('Cairo, Arial, sans-serif', 'Cairo'),
            ('Amiri, serif', 'Amiri'),
            ('Noto Sans Arabic, Arial, sans-serif', 'Noto Sans Arabic'),
            ('Tajawal, Arial, sans-serif', 'Tajawal'),
            ('IBM Plex Sans Arabic, Arial, sans-serif', 'IBM Plex Sans Arabic'),
        ],
        help_text='نوع الخط المستخدم في الفاتورة'
    )
    font_size = models.IntegerField(default=14, verbose_name='حجم الخط الأساسي')
    
    # إعدادات الصفحة
    page_size = models.CharField(
        max_length=20,
        default='A4',
        verbose_name='حجم الصفحة',
        choices=[
            ('A4', 'A4 (210x297mm)'),
            ('Letter', 'Letter (216x279mm)'),
            ('Legal', 'Legal (216x356mm)'),
        ]
    )
    
    page_margins = models.IntegerField(
        default=20,
        verbose_name='هوامش الصفحة (mm)',
        help_text='الهوامش حول محتوى الفاتورة'
    )
    
    # محتوى HTML مخصص للمحرر المتقدم
    html_content = models.TextField(
        blank=True,
        verbose_name='محتوى HTML مخصص',
        help_text='محتوى HTML مخصص للقالب (للمحرر المتقدم)'
    )
    
    css_styles = models.TextField(
        blank=True,
        verbose_name='أنماط CSS مخصصة',
        help_text='أنماط CSS إضافية للقالب'
    )
    
    # إعدادات متقدمة كـ JSON
    advanced_settings = models.JSONField(
        default=dict,
        verbose_name='إعدادات متقدمة',
        help_text='إعدادات متقدمة للقالب (JSON)'
    )
    
    # إحصائيات الاستخدام
    usage_count = models.IntegerField(
        default=0,
        verbose_name='عدد مرات الاستخدام'
    )
    
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخر استخدام'
    )
    
    # إعدادات المحتوى
    show_company_logo = models.BooleanField(default=True, verbose_name='إظهار شعار الشركة')
    show_order_details = models.BooleanField(default=True, verbose_name='إظهار تفاصيل الطلب')
    show_customer_details = models.BooleanField(default=True, verbose_name='إظهار بيانات العميل')
    show_payment_details = models.BooleanField(default=True, verbose_name='إظهار تفاصيل الدفع')
    show_notes = models.BooleanField(default=True, verbose_name='إظهار الملاحظات')
    show_terms = models.BooleanField(default=True, verbose_name='إظهار الشروط والأحكام')
    
    # نصوص مخصصة
    header_text = models.TextField(
        blank=True,
        verbose_name='نص الرأس',
        help_text='نص يظهر في أعلى الفاتورة'
    )
    footer_text = models.TextField(
        blank=True,
        verbose_name='نص التذييل', 
        help_text='نص يظهر في أسفل الفاتورة'
    )
    terms_text = models.TextField(
        blank=True,
        verbose_name='الشروط والأحكام',
        default='شكراً لتعاملكم معنا. جميع الأسعار شاملة ضريبة القيمة المضافة.'
    )
    
    # معلومات النظام
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='تم الإنشاء بواسطة'
    )
    
    class Meta:
        verbose_name = 'قالب فاتورة'
        verbose_name_plural = 'قوالب الفواتير'
        ordering = ['-is_default', '-is_active', 'name']
    
    def __str__(self):
        status = '(افتراضي)' if self.is_default else ''
        return f'{self.name} {status}'
    
    def save(self, *args, **kwargs):
        # التأكد من وجود قالب افتراضي واحد فقط
        if self.is_default:
            InvoiceTemplate.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_default_template(cls):
        """الحصول على القالب الافتراضي"""
        return cls.objects.filter(is_default=True, is_active=True).first() or \
               cls.objects.filter(is_active=True).first()
    
    def increment_usage(self):
        """زيادة عداد الاستخدام"""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
    
    def get_color_palette(self):
        """الحصول على لوحة الألوان"""
        return {
            'primary': self.primary_color,
            'secondary': self.secondary_color,
            'accent': self.accent_color,
        }
    
    def get_font_settings(self):
        """الحصول على إعدادات الخط"""
        return {
            'family': self.font_family,
            'size': self.font_size,
        }
    
    def get_page_settings(self):
        """الحصول على إعدادات الصفحة"""
        return {
            'size': self.page_size,
            'margins': self.page_margins,
        }
    
    def render_html_content(self, context):
        """عرض المحتوى HTML مع السياق"""
        if self.html_content:
            from django.template import Template, Context
            template = Template(self.html_content)
            return template.render(Context(context))
        return self.generate_default_html(context)
    
    def generate_default_html(self, context):
        """إنشاء HTML افتراضي بناءً على الإعدادات"""
        # هذه دالة مساعدة لإنشاء HTML افتراضي
        return f"""
        <div class="invoice-template" style="font-family: {self.font_family}; font-size: {self.font_size}px;">
            <!-- محتوى افتراضي للفاتورة -->
            <div class="header" style="color: {self.primary_color};">
                <h1>{self.company_name}</h1>
            </div>
            <!-- المزيد من المحتوى... -->
        </div>
        """
    
    def clone_template(self, new_name):
        """إنشاء نسخة من القالب"""
        clone = InvoiceTemplate.objects.create(
            name=new_name,
            template_type='custom',
            company_name=self.company_name,
            company_address=self.company_address,
            company_phone=self.company_phone,
            company_email=self.company_email,
            company_website=self.company_website,
            primary_color=self.primary_color,
            secondary_color=self.secondary_color,
            accent_color=self.accent_color,
            font_family=self.font_family,
            font_size=self.font_size,
            page_size=self.page_size,
            page_margins=self.page_margins,
            html_content=self.html_content,
            css_styles=self.css_styles,
            advanced_settings=self.advanced_settings.copy(),
            show_company_logo=self.show_company_logo,
            show_order_details=self.show_order_details,
            show_customer_details=self.show_customer_details,
            show_payment_details=self.show_payment_details,
            show_notes=self.show_notes,
            show_terms=self.show_terms,
            header_text=self.header_text,
            footer_text=self.footer_text,
            terms_text=self.terms_text,
        )
        return clone


class InvoicePrintLog(models.Model):
    """سجل طباعة الفواتير"""
    
    order = models.ForeignKey(
        'Order', 
        on_delete=models.CASCADE,
        related_name='invoice_prints',
        verbose_name='الطلب'
    )
    template = models.ForeignKey(
        InvoiceTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='القالب المستخدم'
    )
    printed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='تم الطباعة بواسطة'
    )
    printed_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الطباعة')
    print_type = models.CharField(
        max_length=20,
        choices=[
            ('auto', 'طباعة تلقائية'),
            ('manual', 'طباعة يدوية'),
        ],
        default='manual',
        verbose_name='نوع الطباعة'
    )
    
    class Meta:
        verbose_name = 'سجل طباعة فاتورة'
        verbose_name_plural = 'سجلات طباعة الفواتير'
        ordering = ['-printed_at']
    
    def __str__(self):
        return f'فاتورة {self.order.order_number} - {self.printed_at.strftime("%Y-%m-%d %H:%M")}'