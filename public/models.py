"""
Cloudflare Settings Admin
Manage Cloudflare Workers sync settings from Django Admin
"""
from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.contrib import messages
import uuid


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

