"""
Cloudflare Settings & QR Design Admin
Manage Cloudflare Workers sync settings and QR page design from Django Admin
"""
from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.contrib import messages
from colorfield.fields import ColorField
import uuid
import json


class CloudflareSettings(models.Model):
    """
    Model to store Cloudflare sync settings
    Singleton pattern - only one instance should exist
    """
    
    worker_url = models.URLField(
        _('رابط Worker'),
        help_text=_('رابط Cloudflare Worker (مثال: https://qr.elkhawaga.uk)'),
        blank=True,
        default=''
    )
    
    sync_api_key = models.CharField(
        _('مفتاح API للمزامنة'),
        max_length=64,
        help_text=_('مفتاح سري للتحقق من طلبات المزامنة'),
        blank=True,
        default=''
    )
    
    is_enabled = models.BooleanField(
        _('تفعيل المزامنة'),
        default=False,
        help_text=_('تفعيل أو إيقاف المزامنة التلقائية مع Cloudflare')
    )
    
    auto_sync_on_save = models.BooleanField(
        _('مزامنة تلقائية عند الحفظ'),
        default=True,
        help_text=_('مزامنة المنتج تلقائياً عند حفظه')
    )
    
    last_full_sync = models.DateTimeField(
        _('آخر مزامنة كاملة'),
        null=True,
        blank=True
    )
    
    products_synced = models.PositiveIntegerField(
        _('عدد المنتجات المُزامَنة'),
        default=0
    )
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('إعدادات Cloudflare')
        verbose_name_plural = _('إعدادات Cloudflare')
    
    def __str__(self):
        status = "✅ مفعّل" if self.is_enabled else "❌ معطّل"
        return f"إعدادات Cloudflare Workers - {status}"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and CloudflareSettings.objects.exists():
            raise ValueError("يمكن إنشاء سجل واحد فقط لإعدادات Cloudflare")
        
        # Generate API key if empty
        if not self.sync_api_key:
            self.sync_api_key = f"cf_{uuid.uuid4().hex}"
        
        super().save(*args, **kwargs)
        
        # Clear cache
        cache.delete('cloudflare_settings')
    
    @classmethod
    def get_settings(cls):
        """Get or create singleton settings instance"""
        settings = cache.get('cloudflare_settings')
        if settings is None:
            settings, _ = cls.objects.get_or_create(pk=1)
            cache.set('cloudflare_settings', settings, 300)  # Cache for 5 minutes
        return settings
    
    def generate_new_api_key(self):
        """Generate a new API key"""
        self.sync_api_key = f"cf_{uuid.uuid4().hex}"
        self.save()
        return self.sync_api_key


@admin.register(CloudflareSettings)
class CloudflareSettingsAdmin(admin.ModelAdmin):
    """Admin interface for Cloudflare settings"""
    
    list_display = ['__str__', 'is_enabled', 'products_synced', 'last_full_sync']
    readonly_fields = ['sync_api_key', 'last_full_sync', 'products_synced', 'created_at', 'updated_at']
    
    fieldsets = (
        (_('إعدادات الاتصال'), {
            'fields': ('worker_url', 'sync_api_key'),
            'description': _('أدخل رابط Worker ونسخ مفتاح API لإعداده في Cloudflare')
        }),
        (_('خيارات المزامنة'), {
            'fields': ('is_enabled', 'auto_sync_on_save'),
        }),
        (_('الإحصائيات'), {
            'fields': ('products_synced', 'last_full_sync'),
            'classes': ('collapse',),
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['sync_all_products', 'generate_new_api_key', 'test_connection']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not CloudflareSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to change view if settings exist"""
        from django.shortcuts import redirect
        
        # If settings exist, redirect to change view
        if CloudflareSettings.objects.exists():
            obj = CloudflareSettings.objects.first()
            return redirect(f'/admin/public/cloudflaresettings/{obj.pk}/change/')
        
        # Otherwise show the list (which will be empty)
        return super().changelist_view(request, extra_context)
    
    def add_view(self, request, form_url='', extra_context=None):
        """Redirect to change view if settings already exist"""
        from django.shortcuts import redirect
        
        # If settings exist, redirect to change view
        if CloudflareSettings.objects.exists():
            obj = CloudflareSettings.objects.first()
            return redirect(f'/admin/public/cloudflaresettings/{obj.pk}/change/')
        
        return super().add_view(request, form_url, extra_context)
    
    def sync_all_products(self, request, queryset):
        """Sync all products to Cloudflare"""
        from .cloudflare_sync import get_cloudflare_sync
        from django.utils import timezone
        
        settings_obj = CloudflareSettings.get_settings()
        
        if not settings_obj.is_enabled:
            self.message_user(request, "المزامنة معطلة. قم بتفعيلها أولاً.", messages.WARNING)
            return
        
        sync = get_cloudflare_sync()
        if not sync.is_configured():
            self.message_user(request, "إعدادات Cloudflare غير مكتملة.", messages.ERROR)
            return
        
        try:
            count = sync.sync_all_products()
            settings_obj.products_synced = count
            settings_obj.last_full_sync = timezone.now()
            settings_obj.save()
            self.message_user(request, f"تم مزامنة {count} منتج بنجاح ✅", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"فشلت المزامنة: {e}", messages.ERROR)
    
    sync_all_products.short_description = "🔄 مزامنة جميع المنتجات"
    
    def generate_new_api_key(self, request, queryset):
        """Generate new API key"""
        for obj in queryset:
            new_key = obj.generate_new_api_key()
            self.message_user(
                request, 
                f"تم إنشاء مفتاح جديد. تأكد من تحديثه في Cloudflare: {new_key}", 
                messages.WARNING
            )
    
    generate_new_api_key.short_description = "🔑 إنشاء مفتاح API جديد"
    
    def test_connection(self, request, queryset):
        """Test connection to Cloudflare Worker"""
        import requests
        
        for obj in queryset:
            if not obj.worker_url:
                self.message_user(request, "لم يتم تحديد رابط Worker", messages.WARNING)
                continue
            
            try:
                response = requests.get(f"{obj.worker_url}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.message_user(
                        request, 
                        f"✅ الاتصال ناجح! المنتجات المخزنة: {data.get('products_cached', 0)}", 
                        messages.SUCCESS
                    )
                else:
                    self.message_user(
                        request, 
                        f"⚠️ استجابة غير متوقعة: {response.status_code}", 
                        messages.WARNING
                    )
            except requests.exceptions.RequestException as e:
                self.message_user(request, f"❌ فشل الاتصال: {e}", messages.ERROR)
    
    test_connection.short_description = "🧪 اختبار الاتصال"
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)


# ============================================
# QR Design Settings Model
# ============================================

class QRDesignSettings(models.Model):
    """
    إعدادات تصميم صفحات QR Scanner
    QR Scanner Pages Design Settings
    """
    
    class Meta:
        verbose_name = 'إعدادات تصميم QR'
        verbose_name_plural = 'إعدادات تصميم QR'
        db_table = 'public_qr_design_settings'
    
    # ====== الشعار / Logo ======
    logo = models.ImageField(
        'الشعار / Logo',
        upload_to='qr_design/logos/',
        blank=True,
        null=True,
        help_text='شعار الشركة (يظهر في صفحات المنتجات والبنوك)'
    )
    
    logo_text = models.CharField(
        'نص الشعار',
        max_length=100,
        default='الخواجة',
        help_text='نص بديل عند عدم وجود صورة'
    )
    
    logo_text_en = models.CharField(
        'نص الشعار (إنجليزي)',
        max_length=100,
        default='Elkhawaga',
        blank=True
    )
    
    show_logo = models.BooleanField(
        'إظهار الشعار',
        default=True
    )
    
    logo_size = models.IntegerField(
        'حجم الشعار',
        default=200,
        help_text='الحجم الأقصى للشعار بالبكسل (50-400)'
    )
    
    # ====== الألوان / Colors ======
    color_primary = ColorField(
        'اللون الأساسي',
        default='#d4af37',
        help_text='اللون الذهبي الرئيسي'
    )
    
    color_secondary = ColorField(
        'اللون الثانوي',
        default='#b8860b',
        help_text='لون ذهبي داكن'
    )
    
    color_background = ColorField(
        'لون الخلفية',
        default='#1a1a2e',
        help_text='لون خلفية الصفحة'
    )
    
    color_surface = ColorField(
        'لون السطح',
        default='#16213e',
        help_text='لون بطاقة المحتوى'
    )
    
    color_text = ColorField(
        'لون النص',
        default='#ffffff',
        help_text='لون النص الرئيسي'
    )
    
    color_text_secondary = ColorField(
        'لون النص الثانوي',
        default='#c0c0c0',
        help_text='لون النص الفرعي'
    )
    
    # ====== ألوان إضافية / Additional Colors ======
    color_card = ColorField(
        'لون البطاقة',
        default='#16213e',
        help_text='لون خلفية البطاقة الرئيسية'
    )
    
    color_button = ColorField(
        'لون الأزرار',
        default='#d4af37',
        help_text='لون خلفية الأزرار'
    )
    
    color_button_text = ColorField(
        'لون نص الأزرار',
        default='#1a1a2e',
        help_text='لون النص داخل الأزرار'
    )
    
    color_badge = ColorField(
        'لون البادجات',
        default='#d4af37',
        help_text='لون خلفية البادجات (الفئة، الوحدة، الكود)'
    )
    
    color_badge_text = ColorField(
        'لون نص البادجات',
        default='#1a1a2e',
        help_text='لون النص داخل البادجات'
    )
    
    color_price = ColorField(
        'لون السعر',
        default='#d4af37',
        help_text='لون رقم السعر (يدعم تدرج من primary إلى price)'
    )
    
    color_product_name = ColorField(
        'لون اسم المنتج',
        default='#d4af37',
        help_text='لون اسم المنتج الرئيسي'
    )
    
    color_label = ColorField(
        'لون العناوين',
        default='#888888',
        help_text='لون العناوين والتسميات (النوع، الوحدة، سعر المنتج الأساسي)'
    )
    
    background_image = models.ImageField(
        'صورة الخلفية',
        upload_to='qr_design/backgrounds/',
        blank=True,
        null=True,
        help_text='صورة خلفية للصفحة (اختياري - يظهر خلف اللون)'
    )
    
    # ====== الروابط / Links ======
    website_url = models.URLField(
        'رابط الموقع الرئيسي',
        default='https://elkhawaga.com',
        help_text='يظهر في زر "زيارة الموقع"'
    )
    
    show_website_button = models.BooleanField(
        'إظهار زر الموقع',
        default=True
    )
    
    # ====== التواصل الاجتماعي / Social Media ======
    facebook_url = models.URLField(
        'فيسبوك',
        blank=True,
        default='',
        help_text='رابط صفحة فيسبوك'
    )
    
    instagram_url = models.URLField(
        'إنستجرام',
        blank=True,
        default='',
        help_text='رابط حساب إنستجرام'
    )
    
    whatsapp_number = models.CharField(
        'واتساب',
        max_length=20,
        blank=True,
        default='',
        help_text='رقم واتساب (مثال: 201234567890)'
    )
    
    twitter_url = models.URLField(
        'تويتر / X',
        blank=True,
        default='',
        help_text='رابط حساب تويتر'
    )
    
    youtube_url = models.URLField(
        'يوتيوب',
        blank=True,
        default='',
        help_text='رابط قناة يوتيوب'
    )
    
    tiktok_url = models.URLField(
        'تيك توك',
        blank=True,
        default='',
        help_text='رابط حساب تيك توك'
    )
    
    phone_number = models.CharField(
        'رقم الهاتف',
        max_length=20,
        blank=True,
        default='',
        help_text='رقم هاتف للاتصال'
    )
    
    email = models.EmailField(
        'البريد الإلكتروني',
        blank=True,
        default='',
        help_text='بريد إلكتروني للتواصل'
    )
    
    show_social_media = models.BooleanField(
        'إظهار أزرار التواصل',
        default=True,
        help_text='إظهار/إخفاء جميع أزرار التواصل الاجتماعي'
    )
    
    # ====== الشكوى / Complaint ======
    complaint_url = models.URLField(
        'رابط الشكوى',
        blank=True,
        default='/complaints/create/',
        help_text='رابط صفحة إنشاء شكوى'
    )
    
    complaint_button_text = models.CharField(
        'نص زر الشكوى',
        max_length=50,
        default='إنشاء شكوى',
        help_text='النص الذي يظهر على زر الشكوى'
    )
    
    complaint_button_text_en = models.CharField(
        'نص زر الشكوى (إنجليزي)',
        max_length=50,
        default='Create Complaint',
        blank=True
    )
    
    show_complaint_button = models.BooleanField(
        'إظهار زر الشكوى',
        default=True
    )
    
    # ====== التخطيط / Layout ======
    layout_style = models.CharField(
        'نمط التخطيط',
        max_length=20,
        choices=[
            ('modern', 'حديث (Modern)'),
            ('classic', 'كلاسيكي (Classic)'),
            ('minimal', 'بسيط (Minimal)'),
            ('elegant', 'أنيق (Elegant)'),
        ],
        default='modern'
    )
    
    card_border_radius = models.IntegerField(
        'انحناء زوايا البطاقة',
        default=15,
        help_text='بالبكسل (0-50)'
    )
    
    enable_animations = models.BooleanField(
        'تفعيل التأثيرات الحركية',
        default=True
    )
    
    enable_glassmorphism = models.BooleanField(
        'تفعيل تأثير Glassmorphism',
        default=True,
        help_text='تأثير الزجاج الشفاف - يطبق لون البطاقة مع شفافية 80%'
    )
    
    # ====== الطباعة / Typography ======
    font_family = models.CharField(
        'نوع الخط',
        max_length=100,
        default='Cairo',
        help_text='مثل: Cairo, Tajawal, Almarai, Rubik'
    )
    
    font_size_base = models.IntegerField(
        'حجم الخط الأساسي',
        default=16,
        help_text='بالبكسل (12-24)'
    )
    
    FONT_WEIGHT_CHOICES = [
        ('400', 'عادي'),
        ('500', 'متوسط'),
        ('600', 'سميك'),
        ('700', 'سميك جداً'),
        ('800', 'أكثر سماكة'),
    ]
    
    font_weight_heading = models.CharField(
        'وزن خط العناوين',
        max_length=20,
        default='700',
        choices=FONT_WEIGHT_CHOICES
    )
    
    # ====== المسافات والأبعاد / Spacing & Sizing ======
    card_padding = models.IntegerField(
        'مسافة داخلية للبطاقة',
        default=30,
        help_text='بالبكسل (20-50)'
    )
    
    card_max_width = models.IntegerField(
        'أقصى عرض للبطاقة',
        default=450,
        help_text='بالبكسل (400-600)'
    )
    
    element_spacing = models.IntegerField(
        'المسافة بين العناصر',
        default=20,
        help_text='بالبكسل (10-40)'
    )
    
    # ====== الظلال والتأثيرات / Shadows & Effects ======
    SHADOW_CHOICES = [
        ('none', 'بدون ظل'),
        ('light', 'خفيف'),
        ('medium', 'متوسط'),
        ('strong', 'قوي'),
    ]
    
    card_shadow_intensity = models.CharField(
        'قوة ظل البطاقة',
        max_length=20,
        default='medium',
        choices=SHADOW_CHOICES
    )
    
    enable_gradient_bg = models.BooleanField(
        'تفعيل تدرج الخلفية',
        default=True,
        help_text='خلفية بتدرج جميل بدلاً من لون صامت'
    )
    
    enable_hover_effects = models.BooleanField(
        'تفعيل تأثيرات التمرير',
        default=True,
        help_text='حركات عند التمرير على الأزرار'
    )
    
    # ====== شكل الأزرار / Button Styles ======
    BUTTON_STYLE_CHOICES = [
        ('square', 'مربع'),
        ('rounded', 'زوايا منحنية'),
        ('pill', 'حبة دواء'),
    ]
    
    button_style = models.CharField(
        'شكل الأزرار',
        max_length=20,
        default='rounded',
        choices=BUTTON_STYLE_CHOICES
    )
    
    BUTTON_SIZE_CHOICES = [
        ('small', 'صغير'),
        ('medium', 'متوسط'),
        ('large', 'كبير'),
    ]
    
    button_size = models.CharField(
        'حجم الأزرار',
        max_length=20,
        default='medium',
        choices=BUTTON_SIZE_CHOICES
    )
    
    # ====== عرض السعر / Price Display ======
    price_font_size = models.IntegerField(
        'حجم خط السعر',
        default=48,
        help_text='بالبكسل (32-72)'
    )
    
    show_price_badge = models.BooleanField(
        'إظهار شارة السعر',
        default=True,
        help_text='خلفية مميزة لقسم السعر'
    )
    
    # ====== تحسينات بطاقة المنتج / Product Card ======
    show_product_icon = models.BooleanField(
        'إظهار أيقونة المنتج',
        default=True
    )
    
    show_category_badge = models.BooleanField(
        'إظهار شارة التصنيف',
        default=True
    )
    
    # ====== إعدادات متقدمة / Advanced ======
    custom_css = models.TextField(
        'CSS مخصص',
        blank=True,
        default='',
        help_text='كود CSS إضافي للتخصيص المتقدم'
    )
    
    custom_js = models.TextField(
        'JavaScript مخصص',
        blank=True,
        default='',
        help_text='كود JavaScript إضافي'
    )
    
    footer_text = models.CharField(
        'نص التذييل',
        max_length=200,
        default='© 2025 الخواجة - جميع الحقوق محفوظة',
        blank=True
    )
    
    show_footer = models.BooleanField(
        'إظهار التذييل',
        default=True
    )
    
    # ====== المزامنة / Sync ======
    last_synced_at = models.DateTimeField(
        'آخر مزامنة',
        auto_now=True
    )
    
    cloudflare_synced = models.BooleanField(
        'تمت المزامنة مع Cloudflare',
        default=False
    )
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    def __str__(self):
        return f"إعدادات تصميم QR - {self.logo_text}"
    
    def save(self, *args, **kwargs):
        # Singleton pattern - only one instance
        if not self.pk and QRDesignSettings.objects.exists():
            raise ValueError('يمكن إنشاء إعدادات واحدة فقط. قم بتعديل الإعدادات الموجودة.')
        super().save(*args, **kwargs)
        
        # Clear cache
        cache.delete('qr_design_settings')
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات (مع Cache)"""
        settings = cache.get('qr_design_settings')
        if not settings:
            settings = cls.objects.first()
            if not settings:
                settings = cls.objects.create()
            cache.set('qr_design_settings', settings, 3600)  # 1 hour
        return settings
    
    def to_dict(self):
        """تحويل الإعدادات إلى قاموس للمزامنة - مع تحويل الصور إلى Base64"""
        import base64
        import os
        from django.conf import settings
        
        def image_to_base64(image_field):
            """
            تحويل ImageField إلى Base64 data URL
            يُستخدم لرفع الصور مباشرة إلى Cloudflare بدون الحاجة للسيرفر الأصلي
            """
            if not image_field:
                return ''
            try:
                # فتح الملف وقراءته
                with image_field.open('rb') as img_file:
                    img_data = img_file.read()
                    # تحويل إلى base64
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    # تحديد نوع الملف
                    ext = os.path.splitext(image_field.name)[1].lower()
                    mime_types = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp',
                        '.svg': 'image/svg+xml'
                    }
                    mime_type = mime_types.get(ext, 'image/png')
                    # إرجاع data URL
                    return f'data:{mime_type};base64,{img_base64}'
            except Exception as e:
                print(f'خطأ في تحويل الصورة إلى Base64: {e}')
                return ''
        
        # تحويل اللوغو إلى Base64
        logo_url = image_to_base64(self.logo)
        
        # تحويل صورة الخلفية إلى Base64
        background_image_url = image_to_base64(self.background_image)
        
        return {
            'logo_url': logo_url,
            'logo_text': self.logo_text,
            'logo_text_en': self.logo_text_en,
            'show_logo': self.show_logo,
            'logo_size': self.logo_size,
            'background_image_url': background_image_url,
            'colors': {
                'primary': self.color_primary,
                'secondary': self.color_secondary,
                'background': self.color_background,
                'surface': self.color_surface,
                'text': self.color_text,
                'text_secondary': self.color_text_secondary,
                'card': self.color_card,
                'button': self.color_button,
                'button_text': self.color_button_text,
                'badge': self.color_badge,
                'badge_text': self.color_badge_text,
                'price': self.color_price,
                'product_name': self.color_product_name,
                'label': self.color_label,
            },
            'links': {
                'website': self.website_url,
                'facebook': self.facebook_url,
                'instagram': self.instagram_url,
                'twitter': self.twitter_url,
                'youtube': self.youtube_url,
                'tiktok': self.tiktok_url,
                'whatsapp': self.whatsapp_number,
                'phone': self.phone_number,
                'email': self.email,
            },
            'complaint': {
                'url': self.complaint_url,
                'text': self.complaint_button_text,
                'text_en': self.complaint_button_text_en,
                'show': self.show_complaint_button,
            },
            'layout': {
                'style': self.layout_style,
                'border_radius': self.card_border_radius,
                'animations': self.enable_animations,
                'glassmorphism': self.enable_glassmorphism,
            },
            'show_website_button': self.show_website_button,
            'show_social_media': self.show_social_media,
            'show_footer': self.show_footer,
            'footer_text': self.footer_text,
            'custom_css': self.custom_css,
            'custom_js': self.custom_js,
        }

