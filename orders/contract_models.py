"""
نماذج قوالب العقود
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class ContractTemplate(models.Model):
    """نموذج قالب العقد"""
    
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
        upload_to='contract_templates/logos/', 
        blank=True, 
        null=True,
        verbose_name='شعار الشركة'
    )
    company_address = models.TextField(blank=True, verbose_name='عنوان الشركة')
    company_phone = models.CharField(max_length=100, blank=True, verbose_name='هاتف الشركة')
    company_email = models.EmailField(blank=True, verbose_name='بريد الشركة')
    company_website = models.URLField(blank=True, verbose_name='موقع الشركة')
    company_tax_number = models.CharField(max_length=100, blank=True, verbose_name='الرقم الضريبي')
    company_commercial_register = models.CharField(max_length=100, blank=True, verbose_name='السجل التجاري')
    
    # إعدادات الألوان والخطوط
    primary_color = models.CharField(
        max_length=7, 
        default='#007bff',
        verbose_name='اللون الأساسي',
        help_text='اللون الأساسي للعقد (مثل: #007bff)'
    )
    secondary_color = models.CharField(
        max_length=7, 
        default='#6c757d',
        verbose_name='اللون الثانوي'
    )
    accent_color = models.CharField(
        max_length=7, 
        default='#ffc107',
        verbose_name='لون التمييز'
    )
    font_family = models.CharField(
        max_length=100, 
        default='Arial, sans-serif',
        verbose_name='نوع الخط'
    )
    font_size = models.IntegerField(
        default=14,
        verbose_name='حجم الخط (px)'
    )
    
    # إعدادات الصفحة
    page_size = models.CharField(
        max_length=10,
        default='A4',
        choices=[('A4', 'A4'), ('Letter', 'Letter')],
        verbose_name='حجم الصفحة'
    )
    page_margins = models.IntegerField(
        default=20,
        verbose_name='هوامش الصفحة (mm)',
        help_text='الهوامش حول محتوى العقد'
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
    
    # إعدادات المحتوى - ما يتم عرضه في العقد
    show_company_logo = models.BooleanField(default=True, verbose_name='عرض شعار الشركة')
    show_order_details = models.BooleanField(default=True, verbose_name='عرض تفاصيل الطلب')
    show_customer_details = models.BooleanField(default=True, verbose_name='عرض بيانات العميل')
    show_items_table = models.BooleanField(default=True, verbose_name='عرض جدول العناصر')
    show_payment_details = models.BooleanField(default=True, verbose_name='عرض تفاصيل الدفع')
    show_terms = models.BooleanField(default=True, verbose_name='عرض الشروط والأحكام')
    show_signatures = models.BooleanField(default=True, verbose_name='عرض التوقيعات')
    
    # نصوص مخصصة
    header_text = models.TextField(
        blank=True,
        verbose_name='نص الرأس',
        help_text='نص يظهر في أعلى العقد'
    )
    footer_text = models.TextField(
        blank=True,
        verbose_name='نص التذييل', 
        help_text='نص يظهر في أسفل العقد'
    )
    terms_text = models.TextField(
        blank=True,
        verbose_name='الشروط والأحكام',
        default='شروط وأحكام العقد...'
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
        verbose_name = 'قالب عقد'
        verbose_name_plural = 'قوالب العقود'
        ordering = ['-is_default', '-is_active', 'name']

    def __str__(self):
        status = '(افتراضي)' if self.is_default else ''
        return f'{self.name} {status}'

    def save(self, *args, **kwargs):
        # التأكد من وجود قالب افتراضي واحد فقط
        if self.is_default:
            ContractTemplate.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default_template(cls):
        """الحصول على القالب الافتراضي"""
        return cls.objects.filter(is_default=True, is_active=True).first() or \
               cls.objects.filter(is_active=True).first()

    def increment_usage(self):
        """زيادة عداد الاستخدام"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])

    def clone_template(self, new_name):
        """إنشاء نسخة من القالب"""
        clone = ContractTemplate.objects.create(
            name=new_name,
            template_type='custom',
            company_name=self.company_name,
            company_address=self.company_address,
            company_phone=self.company_phone,
            company_email=self.company_email,
            company_website=self.company_website,
            company_tax_number=self.company_tax_number,
            company_commercial_register=self.company_commercial_register,
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
            show_items_table=self.show_items_table,
            show_payment_details=self.show_payment_details,
            show_terms=self.show_terms,
            show_signatures=self.show_signatures,
            header_text=self.header_text,
            footer_text=self.footer_text,
            terms_text=self.terms_text,
            is_active=True,
            is_default=False
        )
        return clone


class ContractCurtain(models.Model):
    """نموذج تفاصيل الستارة في العقد"""

    TAILORING_TYPE_CHOICES = [
        ('rings', 'حلقات'),
        ('tape', 'شريط'),
        ('snap', 'كبس'),
        ('double_fold', 'كسرة مزدوجة'),
        ('triple_fold', 'كسرة ثلاثية'),
        ('pencil_pleat', 'كسرة قلم'),
        ('eyelet', 'عراوي'),
        ('tab_top', 'عروة علوية'),
    ]
    
    INSTALLATION_TYPE_CHOICES = [
        ('wall_gypsum', 'حائط - جبس'),
        ('wall_concrete', 'حائط - مسلح'),
        ('ceiling_gypsum', 'سقف - جبس'),
        ('ceiling_concrete', 'سقف - مسلح'),
        ('curtain_box_concrete', 'بيت ستارة مسلح'),
        ('curtain_box_gypsum', 'بيت ستارة جبس'),
    ]

    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='contract_curtains',
        verbose_name='الطلب',
        null=True,
        blank=True
    )
    
    # دعم المسودات - للويزارد
    draft_order = models.ForeignKey(
        'DraftOrder',
        on_delete=models.CASCADE,
        related_name='contract_curtains',
        verbose_name='مسودة الطلب',
        null=True,
        blank=True
    )

    # ترتيب الستارة في العقد
    sequence = models.IntegerField(default=1, verbose_name='الترتيب')

    # معلومات الغرفة والمقاسات
    room_name = models.CharField(max_length=100, verbose_name='اسم الغرفة')
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='العرض',
        help_text='بالمتر'
    )
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الطول',
        help_text='بالمتر'
    )
    
    # نوع التركيب
    installation_type = models.CharField(
        max_length=30,
        choices=INSTALLATION_TYPE_CHOICES,
        blank=True,
        verbose_name='نوع التركيب'
    )
    
    # مقاسات بيت الستارة (بالسنتيمتر - تظهر فقط عند اختيار بيت ستارة)
    curtain_box_width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='عرض بيت الستارة (سم)',
        help_text='بالسنتيمتر - يُملأ عند اختيار بيت ستارة مسلح أو جبس'
    )
    curtain_box_depth = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='عمق بيت الستارة (سم)',
        help_text='بالسنتيمتر - يُملأ عند اختيار بيت ستارة مسلح أو جبس'
    )

    # صورة موديل الستارة
    curtain_image = models.ImageField(
        upload_to='contract_curtains/',
        blank=True,
        null=True,
        verbose_name='صورة موديل الستارة'
    )

    # القماش الخفيف
    light_fabric = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_light',
        verbose_name='قماش خفيف'
    )
    light_fabric_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='عدد أمتار القماش الخفيف'
    )
    light_fabric_tailoring = models.CharField(
        max_length=20,
        choices=TAILORING_TYPE_CHOICES,
        blank=True,
        verbose_name='نوع تفصيل القماش الخفيف'
    )
    light_fabric_tailoring_size = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='مقاس التفصيل (للشريط)',
        help_text='يُملأ في حالة اختيار شريط'
    )

    # القماش الثقيل
    heavy_fabric = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_heavy',
        verbose_name='قماش ثقيل'
    )
    heavy_fabric_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='عدد أمتار القماش الثقيل'
    )
    heavy_fabric_tailoring = models.CharField(
        max_length=20,
        choices=TAILORING_TYPE_CHOICES,
        blank=True,
        verbose_name='نوع تفصيل القماش الثقيل'
    )
    heavy_fabric_tailoring_size = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='مقاس التفصيل (للشريط)',
        help_text='يُملأ في حالة اختيار شريط'
    )

    # قماش البلاك أوت
    blackout_fabric = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_blackout',
        verbose_name='قماش بلاك أوت'
    )
    blackout_fabric_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='عدد أمتار البلاك أوت'
    )
    blackout_fabric_tailoring = models.CharField(
        max_length=20,
        choices=TAILORING_TYPE_CHOICES,
        blank=True,
        verbose_name='نوع تفصيل البلاك أوت'
    )
    blackout_fabric_tailoring_size = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='مقاس التفصيل (للشريط)',
        help_text='يُملأ في حالة اختيار شريط'
    )

    # الإكسسوارات
    # خشب
    wood_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد الخشب'
    )
    wood_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='نوع الخشب',
        help_text='يُكتب يدوياً'
    )

    # نوع المجرى
    track_type = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_track',
        verbose_name='نوع المجرى'
    )
    track_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد المجرى'
    )

    # مواسير
    pipe = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_pipe',
        verbose_name='نوع المواسير'
    )
    pipe_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد المواسير'
    )

    # كوابيل
    bracket = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_bracket',
        verbose_name='نوع الكوابيل'
    )
    bracket_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد الكوابيل'
    )

    # نهايات
    finial = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_finial',
        verbose_name='نوع النهايات'
    )
    finial_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد النهايات'
    )

    # طبة
    ring = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_ring',
        verbose_name='نوع الطبة'
    )
    ring_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد الطبة'
    )

    # شماعات
    hanger = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_hanger',
        verbose_name='نوع الشماعات'
    )
    hanger_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد الشماعات'
    )

    # فرانشة
    valance = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_valance',
        verbose_name='نوع الفرانشة'
    )
    valance_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد الفرانشة'
    )

    # شرابة
    tassel = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_tassel',
        verbose_name='نوع الشرابة'
    )
    tassel_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد الشرابة'
    )

    # مرابط يدوي
    tieback_fabric = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_tieback',
        verbose_name='نوع قماش المرابط'
    )
    tieback_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد المرابط'
    )

    # حزام وسط
    belt = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_curtains_belt',
        verbose_name='نوع حزام الوسط'
    )
    belt_quantity = models.IntegerField(
        default=0,
        verbose_name='عدد حزام الوسط'
    )

    # ملاحظات
    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات وشرح'
    )

    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'ستارة في العقد'
        verbose_name_plural = 'ستائر في العقد'
        ordering = ['order', 'sequence']
        unique_together = ['order', 'sequence']

    def __str__(self):
        return f'{self.room_name} - {self.order.order_number}'

    def clean(self):
        """التحقق من صحة البيانات"""
        from django.core.exceptions import ValidationError
        errors = {}

        # التحقق من أن الكميات لا تتجاوز الكميات في الفاتورة
        if self.light_fabric and self.light_fabric_meters:
            if self.light_fabric_meters > self.light_fabric.quantity:
                errors['light_fabric_meters'] = f'الكمية المطلوبة ({self.light_fabric_meters}) أكبر من الكمية المتاحة ({self.light_fabric.quantity})'

        if self.heavy_fabric and self.heavy_fabric_meters:
            if self.heavy_fabric_meters > self.heavy_fabric.quantity:
                errors['heavy_fabric_meters'] = f'الكمية المطلوبة ({self.heavy_fabric_meters}) أكبر من الكمية المتاحة ({self.heavy_fabric.quantity})'

        if self.blackout_fabric and self.blackout_fabric_meters:
            if self.blackout_fabric_meters > self.blackout_fabric.quantity:
                errors['blackout_fabric_meters'] = f'الكمية المطلوبة ({self.blackout_fabric_meters}) أكبر من الكمية المتاحة ({self.blackout_fabric.quantity})'

        if errors:
            raise ValidationError(errors)


class ContractPrintLog(models.Model):
    """سجل طباعة العقود"""

    PRINT_TYPE_CHOICES = [
        ('auto', 'طباعة تلقائية'),
        ('manual', 'طباعة يدوية'),
    ]

    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='contract_print_logs',
        verbose_name='الطلب'
    )
    template = models.ForeignKey(
        ContractTemplate,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='القالب المستخدم'
    )
    printed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='تمت الطباعة بواسطة'
    )
    print_type = models.CharField(
        max_length=10,
        choices=PRINT_TYPE_CHOICES,
        default='manual',
        verbose_name='نوع الطباعة'
    )
    printed_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الطباعة')

    class Meta:
        verbose_name = 'سجل طباعة عقد'
        verbose_name_plural = 'سجلات طباعة العقود'
        ordering = ['-printed_at']

    def __str__(self):
        return f'طباعة عقد {self.order.order_number} - {self.printed_at.strftime("%Y-%m-%d %H:%M")}'


class CurtainFabric(models.Model):
    """
    نموذج مبسط للأقمشة المرتبطة بالستارة
    يدعم كلاً من الطلبات النهائية والمسودات
    """
    FABRIC_TYPES = [
        ('light', 'خفيف'),
        ('heavy', 'ثقيل'),
        ('blackout', 'بلاك أوت'),
        ('additional', 'إضافي'),
    ]
    
    TAILORING_TYPES = [
        ('rings', 'حلقات'),
        ('tape', 'شريط'),
        ('snap', 'كبس'),
        ('double_fold', 'كسرة مزدوجة'),
        ('triple_fold', 'كسرة ثلاثية'),
        ('pencil_pleat', 'كسرة قلم'),
        ('eyelet', 'عراوي'),
        ('tab_top', 'عروة علوية'),
    ]
    
    curtain = models.ForeignKey(
        ContractCurtain,
        on_delete=models.CASCADE,
        related_name='fabrics',
        verbose_name='الستارة'
    )
    
    # ربط بعنصر الفاتورة (يدعم OrderItem و DraftOrderItem)
    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curtain_fabrics',
        verbose_name='عنصر الفاتورة (النهائي)',
        help_text='القماش من عناصر الفاتورة النهائية'
    )
    
    # ربط بعنصر المسودة
    draft_order_item = models.ForeignKey(
        'DraftOrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curtain_fabrics',
        verbose_name='عنصر المسودة',
        help_text='القماش من عناصر مسودة الطلب'
    )
    
    fabric_type = models.CharField(
        max_length=20,
        choices=FABRIC_TYPES,
        verbose_name='نوع القماش'
    )
    fabric_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='اسم القماش'
    )
    pieces = models.IntegerField(
        default=1,
        verbose_name='عدد القطع'
    )
    meters = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='عدد الأمتار'
    )
    tailoring_type = models.CharField(
        max_length=20,
        choices=TAILORING_TYPES,
        blank=True,
        verbose_name='نوع التفصيل'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات القماش',
        help_text='ملاحظات خاصة بهذا القماش'
    )
    sequence = models.IntegerField(
        default=0,
        verbose_name='الترتيب'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'قماش الستارة'
        verbose_name_plural = 'أقمشة الستائر'
        ordering = ['curtain', 'sequence']
    
    def __str__(self):
        if self.order_item:
            return f"{self.get_fabric_type_display()} - {self.order_item.product.name} ({self.meters}م)"
        elif self.draft_order_item:
            return f"{self.get_fabric_type_display()} - {self.draft_order_item.product.name} ({self.meters}م)"
        return f"{self.get_fabric_type_display()} - {self.fabric_name} ({self.meters}م)"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # التحقق من عدم تجاوز الكمية المتاحة للطلبات النهائية
        if self.order_item and self.meters:
            # حساب إجمالي ما تم استخدامه من هذا العنصر
            used_total = CurtainFabric.objects.filter(
                order_item=self.order_item
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('meters')
            )['total'] or 0
            
            available = self.order_item.quantity - used_total
            
            if self.meters > available:
                errors['meters'] = f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح ({available}م من {self.order_item.quantity}م)'
        
        # التحقق من عدم تجاوز الكمية المتاحة للمسودات
        if self.draft_order_item and self.meters:
            # حساب إجمالي ما تم استخدامه من هذا العنصر في المسودات
            used_total = CurtainFabric.objects.filter(
                draft_order_item=self.draft_order_item
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('meters')
            )['total'] or 0
            
            available = self.draft_order_item.quantity - used_total
            
            if self.meters > available:
                errors['meters'] = f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح ({available}م من {self.draft_order_item.quantity}م)'
        
        if errors:
            raise ValidationError(errors)


class CurtainAccessory(models.Model):
    """
    نموذج مبسط للإكسسوارات المرتبطة بالستارة
    """
    curtain = models.ForeignKey(
        ContractCurtain,
        on_delete=models.CASCADE,
        related_name='accessories',
        verbose_name='الستارة'
    )
    
    # ربط بعنصر الفاتورة (يدعم OrderItem و DraftOrderItem)
    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curtain_accessories',
        verbose_name='عنصر الفاتورة (النهائي)',
        help_text='الإكسسوار من عناصر الفاتورة النهائية'
    )
    
    # ربط بعنصر المسودة
    draft_order_item = models.ForeignKey(
        'DraftOrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curtain_accessories',
        verbose_name='عنصر المسودة',
        help_text='الإكسسوار من عناصر مسودة الطلب'
    )
    
    accessory_name = models.CharField(
        max_length=200,
        verbose_name='اسم الإكسسوار'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=1,
        verbose_name='الكمية الإجمالية',
        help_text='الكمية الإجمالية = العدد × المقاس'
    )
    count = models.IntegerField(
        default=1,
        verbose_name='العدد',
        help_text='عدد القطع'
    )
    size = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=1,
        verbose_name='المقاس',
        help_text='المقاس لكل قطعة'
    )
    color = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='اللون'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'إكسسوار الستارة'
        verbose_name_plural = 'إكسسوارات الستائر'
    
    def __str__(self):
        parts = [self.accessory_name]
        if self.count and self.size:
            parts.append(f"({self.count} × {self.size} = {self.quantity})")
        elif self.quantity:
            parts.append(f"({self.quantity})")
        if self.color:
            parts.append(self.color)
        return " - ".join(parts)
    
    def save(self, *args, **kwargs):
        """حساب الكمية الإجمالية تلقائياً"""
        # Calculate quantity = count × size
        if self.count and self.size:
            self.quantity = self.count * self.size
        super().save(*args, **kwargs)
    
    def clean(self):
        """التحقق من صحة البيانات"""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # التحقق من عدم تجاوز الكمية المتاحة للطلبات النهائية
        if self.order_item and self.quantity:
            # حساب إجمالي ما تم استخدامه من هذا العنصر
            used_total = CurtainAccessory.objects.filter(
                order_item=self.order_item
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
            
            available = self.order_item.quantity - used_total
            
            if self.quantity > available:
                errors['quantity'] = f'الكمية المطلوبة ({self.quantity}) أكبر من المتاح ({available} من {self.order_item.quantity})'
        
        # التحقق من عدم تجاوز الكمية المتاحة للمسودات
        if self.draft_order_item and self.quantity:
            # حساب إجمالي ما تم استخدامه من هذا العنصر في المسودات
            used_total = CurtainAccessory.objects.filter(
                draft_order_item=self.draft_order_item
            ).exclude(pk=self.pk).aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
            
            available = self.draft_order_item.quantity - used_total
            
            if self.quantity > available:
                errors['quantity'] = f'الكمية المطلوبة ({self.quantity}) أكبر من المتاح ({available} من {self.draft_order_item.quantity})'
        
        if errors:
            raise ValidationError(errors)



