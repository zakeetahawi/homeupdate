"""
نموذج إعدادات النظام - للتحكم في سلوك الويزارد والنظام القديم
System Settings Model - Control Wizard and Legacy System Behavior
"""
from django.db import models
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _


class SystemSettings(models.Model):
    """
    إعدادات النظام العامة - Singleton Model
    """
    # اسم فريد للإعدادات (دائماً 'default')
    name = models.CharField(
        max_length=20,
        default='default',
        unique=True,
        verbose_name='اسم الإعدادات'
    )
    
    # === إعدادات نظام الطلبات ===
    ORDER_SYSTEM_CHOICES = [
        ('wizard', 'نظام الويزارد فقط'),
        ('legacy', 'النظام القديم فقط'),
        ('both', 'كلا النظامين'),
    ]
    
    order_system = models.CharField(
        max_length=10,
        choices=ORDER_SYSTEM_CHOICES,
        default='both',
        verbose_name='نظام إنشاء الطلبات',
        help_text='اختر النظام المستخدم لإنشاء الطلبات'
    )
    
    # الأولوية عند فتح طلب للتعديل
    EDIT_PRIORITY_CHOICES = [
        ('source', 'حسب طريقة الإنشاء'),
        ('wizard', 'الويزارد دائماً'),
        ('legacy', 'النظام القديم دائماً'),
    ]
    
    edit_priority = models.CharField(
        max_length=10,
        choices=EDIT_PRIORITY_CHOICES,
        default='source',
        verbose_name='أولوية التعديل',
        help_text='كيف يتم فتح الطلبات للتعديل'
    )
    
    # إخفاء النظام القديم تماماً من الواجهة
    hide_legacy_system = models.BooleanField(
        default=False,
        verbose_name='إخفاء النظام القديم',
        help_text='إخفاء جميع أزرار ووظائف النظام القديم من الواجهة'
    )
    
    # إخفاء نظام الويزارد من الواجهة
    hide_wizard_system = models.BooleanField(
        default=False,
        verbose_name='إخفاء نظام الويزارد',
        help_text='إخفاء جميع أزرار ووظائف نظام الويزارد من الواجهة'
    )
    
    # السماح بتحويل الطلبات القديمة إلى ويزارد
    allow_legacy_to_wizard_conversion = models.BooleanField(
        default=True,
        verbose_name='السماح بتحويل الطلبات القديمة',
        help_text='السماح بتحويل الطلبات المنشأة بالنظام القديم إلى نظام الويزارد'
    )
    
    # === إعدادات الحقول الديناميكية ===
    
    # أنواع التفصيل المتاحة
    tailoring_types = models.JSONField(
        default=list,
        verbose_name='أنواع التفصيل المتاحة',
        help_text='قائمة بأنواع التفصيل التي يمكن اختيارها',
        blank=True
    )
    
    # أنواع الأقمشة المتاحة
    fabric_types = models.JSONField(
        default=list,
        verbose_name='أنواع الأقمشة المتاحة',
        help_text='قائمة بأنواع الأقمشة التي يمكن اختيارها',
        blank=True
    )
    
    # أنواع التركيب المتاحة
    installation_types = models.JSONField(
        default=list,
        verbose_name='أنواع التركيب المتاحة',
        help_text='قائمة بأنواع التركيب التي يمكن اختيارها',
        blank=True
    )
    
    # طرق الدفع المتاحة
    payment_methods = models.JSONField(
        default=list,
        verbose_name='طرق الدفع المتاحة',
        help_text='قائمة بطرق الدفع التي يمكن اختيارها',
        blank=True
    )
    
    # === إعدادات العقود ===
    
    # طلب رقم العقد إلزامياً
    require_contract_number = models.BooleanField(
        default=True,
        verbose_name='رقم العقد إلزامي',
        help_text='جعل رقم العقد حقل إلزامي في طلبات التركيب والتسليم'
    )
    
    # طلب ملف العقد إلزامياً
    require_contract_file = models.BooleanField(
        default=False,
        verbose_name='ملف العقد إلزامي',
        help_text='جعل رفع ملف العقد إلزامي'
    )
    
    # === إعدادات الإشعارات ===
    
    # إرسال إشعارات للويزارد
    enable_wizard_notifications = models.BooleanField(
        default=True,
        verbose_name='تفعيل إشعارات الويزارد',
        help_text='إرسال إشعارات عند إكمال خطوات الويزارد'
    )
    
    # === معلومات النظام ===
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    
    class Meta:
        verbose_name = 'إعدادات النظام'
        verbose_name_plural = 'إعدادات النظام'
    
    def __str__(self):
        return 'إعدادات النظام'
    
    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات النظام (Singleton)"""
        # التحقق من الكاش أولاً
        settings = cache.get('orders_system_settings')
        if settings is None:
            settings, _ = cls.objects.get_or_create(
                name='default',
                defaults=cls._get_default_settings()
            )
            cache.set('orders_system_settings', settings, 3600)  # Cache for 1 hour
        return settings
    
    @classmethod
    def _get_default_settings(cls):
        """الإعدادات الافتراضية"""
        return {
            'tailoring_types': [
                {'value': 'regular', 'label': 'عادي'},
                {'value': 'pleated', 'label': 'كسرات'},
                {'value': 'eyelet', 'label': 'حلقات'},
                {'value': 'rod_pocket', 'label': 'جيب'},
                {'value': 'tab_top', 'label': 'ألسنة'},
            ],
            'fabric_types': [
                {'value': 'light', 'label': 'خفيف'},
                {'value': 'heavy', 'label': 'ثقيل'},
                {'value': 'blackout', 'label': 'بلاك أوت'},
                {'value': 'extra', 'label': 'إضافي'},
            ],
            'installation_types': [
                {'value': 'wall', 'label': 'حائط'},
                {'value': 'ceiling', 'label': 'سقف'},
                {'value': 'box', 'label': 'بيت ستارة'},
            ],
            'payment_methods': [
                {'value': 'cash', 'label': 'نقدي'},
                {'value': 'card', 'label': 'بطاقة'},
                {'value': 'bank_transfer', 'label': 'تحويل بنكي'},
                {'value': 'installment', 'label': 'تقسيط'},
            ]
        }
    
    def save(self, *args, **kwargs):
        """حفظ الإعدادات وتحديث الكاش"""
        super().save(*args, **kwargs)
        # مسح الكاش عند التحديث
        cache.delete('orders_system_settings')
        # تحديث الكاش
        cache.set('orders_system_settings', self, 3600)
    
    @classmethod
    def invalidate_cache(cls):
        """مسح الكاش"""
        cache.delete('orders_system_settings')
    
    # === دوال مساعدة للحصول على القيم ===
    
    @classmethod
    def get_order_system(cls):
        """الحصول على نظام الطلبات المفعّل"""
        return cls.get_settings().order_system
    
    @classmethod
    def is_wizard_enabled(cls):
        """التحقق من تفعيل نظام الويزارد"""
        settings = cls.get_settings()
        return settings.order_system in ['wizard', 'both'] and not settings.hide_wizard_system
    
    @classmethod
    def is_legacy_enabled(cls):
        """التحقق من تفعيل النظام القديم"""
        settings = cls.get_settings()
        return settings.order_system in ['legacy', 'both'] and not settings.hide_legacy_system
    
    @classmethod
    def get_tailoring_types(cls):
        """الحصول على أنواع التفصيل"""
        settings = cls.get_settings()
        return settings.tailoring_types or cls._get_default_settings()['tailoring_types']
    
    @classmethod
    def get_fabric_types(cls):
        """الحصول على أنواع الأقمشة"""
        settings = cls.get_settings()
        return settings.fabric_types or cls._get_default_settings()['fabric_types']
    
    @classmethod
    def get_installation_types(cls):
        """الحصول على أنواع التركيب"""
        settings = cls.get_settings()
        return settings.installation_types or cls._get_default_settings()['installation_types']
    
    @classmethod
    def get_payment_methods(cls):
        """الحصول على طرق الدفع"""
        settings = cls.get_settings()
        return settings.payment_methods or cls._get_default_settings()['payment_methods']
