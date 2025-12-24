"""
QR Design Settings Admin
لوحة تحكم متقدمة لإعدادات تصميم صفحات QR
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
import requests
import json
from .models import QRDesignSettings


@admin.register(QRDesignSettings)
class QRDesignSettingsAdmin(admin.ModelAdmin):
    """
    لوحة تحكم إعدادات تصميم QR
    """
    
    fieldsets = [
        ('🎨 الشعار / Logo', {
            'fields': [
                'logo',
                'logo_preview',
                ('logo_text', 'logo_text_en'),
                'show_logo',
            ],
            'classes': ['collapse'],
        }),
        
        ('🎨 الألوان / Colors', {
            'fields': [
                ('color_primary', 'color_secondary'),
                ('color_background', 'color_surface'),
                ('color_text', 'color_text_secondary'),
                'live_preview',
            ],
            'description': '💡 نصيحة: بعد تعديل الألوان، احفظ الإعدادات ثم أعد تحميل الصفحة (F5) لرؤية المعاينة المحدثة',
        }),
        
        ('✍️ الطباعة / Typography', {
            'fields': [
                'font_family',
                ('font_size_base', 'font_weight_heading'),
                'price_font_size',
            ],
            'classes': ['collapse'],
        }),
        
        ('📐 المسافات والأبعاد / Spacing & Sizing', {
            'fields': [
                'card_max_width',
                ('card_padding', 'element_spacing'),
                'card_border_radius',
            ],
            'classes': ['collapse'],
        }),
        
        ('🌟 الظلال والتأثيرات / Effects', {
            'fields': [
                'card_shadow_intensity',
                'enable_gradient_bg',
                'enable_animations',
                'enable_glassmorphism',
                'enable_hover_effects',
            ],
            'classes': ['collapse'],
        }),
        
        ('🔘 الأزرار / Buttons', {
            'fields': [
                ('button_style', 'button_size'),
            ],
            'classes': ['collapse'],
        }),
        
        ('💰 عرض السعر / Price Display', {
            'fields': [
                'show_price_badge',
                ('show_product_icon', 'show_category_badge'),
            ],
            'classes': ['collapse'],
        }),
        
        ('🔗 الروابط / Links', {
            'fields': [
                'website_url',
                'show_website_button',
            ],
            'classes': ['collapse'],
        }),
        
        ('📱 التواصل الاجتماعي / Social Media', {
            'fields': [
                'show_social_media',
                ('facebook_url', 'instagram_url'),
                ('twitter_url', 'youtube_url'),
                ('tiktok_url', 'whatsapp_number'),
                ('phone_number', 'email'),
            ],
            'classes': ['collapse'],
        }),
        
        ('📝 الشكوى / Complaint', {
            'fields': [
                'show_complaint_button',
                'complaint_url',
                ('complaint_button_text', 'complaint_button_text_en'),
            ],
            'classes': ['collapse'],
        }),
        
        ('⚙️ متقدم / Advanced', {
            'fields': [
                'custom_css',
                'custom_js',
                'show_footer',
                'footer_text',
            ],
            'classes': ['collapse'],
        }),
        
        (' معلومات المزامنة / Sync Info', {
            'fields': [
                'cloudflare_synced',
                'last_synced_at',
                'sync_status_display',
            ],
            'classes': ['collapse'],
        }),
    ]
    
    readonly_fields = [
        'logo_preview',
        'color_preview',
        'last_synced_at',
        'cloudflare_synced',
        'sync_status_display',
        'live_preview',
    ]
    
    list_display = [
        'settings_name',
        'logo_display',
        'colors_display',
        'sync_status',
        'actions_display',
    ]
    
    actions = [
        'sync_to_cloudflare',
        'test_preview',
    ]
    
    def has_add_permission(self, request):
        """منع إنشاء أكثر من إعدادات واحدة"""
        return not QRDesignSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """منع الحذف"""
        return False
    
    def save_model(self, request, obj, form, change):
        """حفظ النموذج ومسح Cache"""
        super().save_model(request, obj, form, change)
        # مسح cache لضمان تحديث فوري
        from django.core.cache import cache
        cache.delete('qr_design_settings')
        messages.success(request, '✅ تم حفظ الإعدادات بنجاح وتحديث المعاينة')
    
    # ====== Display Methods ======
    
    def settings_name(self, obj):
        """اسم الإعدادات"""
        return format_html(
            '<strong style="font-size:14px;">🎨 {}</strong>',
            obj.logo_text
        )
    settings_name.short_description = 'الإعدادات'
    
    def logo_display(self, obj):
        """عرض الشعار"""
        from django.utils.safestring import mark_safe
        if obj.logo:
            return format_html(
                '<img src="{0}" style="height:40px; border-radius:5px;">',
                obj.logo.url
            )
        return mark_safe(
            '<span style="color:#999;">📷 لا يوجد</span>'
        )
    logo_display.short_description = 'الشعار'
    
    def colors_display(self, obj):
        """عرض الألوان"""
        return format_html(
            '<div style="display:flex; gap:5px;"><div style="width:30px; height:30px; background:{0}; border-radius:5px; border:1px solid #ddd;" title="Primary"></div><div style="width:30px; height:30px; background:{1}; border-radius:5px; border:1px solid #ddd;" title="Secondary"></div><div style="width:30px; height:30px; background:{2}; border-radius:5px; border:1px solid #ddd;" title="Background"></div></div>',
            obj.color_primary,
            obj.color_secondary,
            obj.color_background
        )
    colors_display.short_description = 'الألوان'
    
    def sync_status(self, obj):
        """حالة المزامنة"""
        from django.utils.safestring import mark_safe
        if obj.cloudflare_synced:
            return mark_safe(
                '<span style="color:#28a745; font-weight:bold;">✓ متزامن</span>'
            )
        return mark_safe(
            '<span style="color:#dc3545; font-weight:bold;">✗ غير متزامن</span>'
        )
    sync_status.short_description = 'المزامنة'
    
    def actions_display(self, obj):
        """أزرار الإجراءات"""
        return format_html(
            '<a href="{0}" class="button" style="padding:5px 10px; background:#007bff; color:white; text-decoration:none; border-radius:3px; margin:2px;">🔄 مزامنة</a><a href="{1}" class="button" target="_blank" style="padding:5px 10px; background:#28a745; color:white; text-decoration:none; border-radius:3px; margin:2px;">👁️ معاينة</a>',
            reverse('admin:sync_qr_design'),
            reverse('public:qr_design_preview')
        )
    actions_display.short_description = 'الإجراءات'
    
    # ====== Readonly Field Methods ======
    
    def logo_preview(self, obj):
        """معاينة الشعار"""
        from django.utils.safestring import mark_safe
        if obj and obj.logo:
            return mark_safe(
                f'<div style="margin:10px 0;">'
                f'<img src="{obj.logo.url}" style="max-width:200px; max-height:200px; border:2px solid #ddd; padding:10px; background:white; border-radius:10px;">'
                f'<p style="margin-top:10px; color:#666;">الحجم الموصى به: 500x500 بكسل</p>'
                f'</div>'
            )
        return mark_safe(
            '<p style="color:#999;">لم يتم رفع شعار بعد</p>'
        )
    logo_preview.short_description = 'معاينة الشعار'
    
    def color_preview(self, obj):
        """معاينة الألوان"""
        from django.utils.safestring import mark_safe
        if not obj:
            return ''
        
        return mark_safe(f'''
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:15px; margin:20px 0;">
                <div style="text-align:center;">
                    <div style="width:100%; height:80px; background:{obj.color_primary}; border-radius:10px; margin-bottom:5px;"></div>
                    <small>Primary</small>
                </div>
                <div style="text-align:center;">
                    <div style="width:100%; height:80px; background:{obj.color_secondary}; border-radius:10px; margin-bottom:5px;"></div>
                    <small>Secondary</small>
                </div>
                <div style="text-align:center;">
                    <div style="width:100%; height:80px; background:{obj.color_background}; border-radius:10px; margin-bottom:5px;"></div>
                    <small>Background</small>
                </div>
                <div style="text-align:center;">
                    <div style="width:100%; height:80px; background:{obj.color_surface}; border-radius:10px; margin-bottom:5px;"></div>
                    <small>Surface</small>
                </div>
                <div style="text-align:center;">
                    <div style="width:100%; height:80px; background:{obj.color_text}; border-radius:10px; margin-bottom:5px; border:1px solid #ddd;"></div>
                    <small>Text</small>
                </div>
                <div style="text-align:center;">
                    <div style="width:100%; height:80px; background:{obj.color_text_secondary}; border-radius:10px; margin-bottom:5px; border:1px solid #ddd;"></div>
                    <small>Text Secondary</small>
                </div>
            </div>
            <div style="background:{obj.color_background}; padding:20px; border-radius:10px; margin-top:20px;">
                <div style="background:{obj.color_surface}; padding:15px; border-radius:8px;">
                    <h3 style="color:{obj.color_primary}; margin:0 0 10px 0;">عنوان تجريبي</h3>
                    <p style="color:{obj.color_text}; margin:0 0 5px 0;">نص تجريبي بلون النص الأساسي</p>
                    <p style="color:{obj.color_text_secondary}; margin:0; font-size:12px;">نص فرعي تجريبي</p>
                </div>
            </div>
        ''')
    color_preview.short_description = 'معاينة الألوان'
    
    def sync_status_display(self, obj):
        """عرض حالة المزامنة التفصيلية"""
        from django.utils.safestring import mark_safe
        if not obj:
            return ''
        
        status_color = '#28a745' if obj.cloudflare_synced else '#dc3545'
        status_text = 'متزامن ✓' if obj.cloudflare_synced else 'غير متزامن ✗'
        
        return mark_safe(f'''
            <div style="padding:15px; background:#f8f9fa; border-radius:8px; border-left:4px solid {status_color};">
                <p style="margin:0 0 5px 0; font-weight:bold; color:{status_color};">
                    {status_text}
                </p>
                <p style="margin:0; font-size:12px; color:#666;">
                    آخر تحديث: {obj.last_synced_at.strftime('%Y-%m-%d %H:%M:%S') if obj.last_synced_at else 'لم يتم'}
                </p>
            </div>
        ''')
    sync_status_display.short_description = 'حالة المزامنة'
    
    def live_preview(self, obj):
        """معاينة فورية مع JavaScript"""
        from django.utils.safestring import mark_safe
        if not obj:
            return ''
        
        # حساب قيم الأزرار
        button_border_radius = {
            'square': '4px',
            'rounded': '14px',
            'pill': '50px'
        }.get(obj.button_style, '14px')
        
        button_padding = {
            'small': '10px 20px',
            'medium': '16px 32px',
            'large': '20px 40px'
        }.get(obj.button_size, '16px 32px')
        
        # حساب الظل
        box_shadow = {
            'none': 'none',
            'light': '0 4px 15px rgba(0,0,0,0.1)',
            'medium': '0 8px 32px rgba(0,0,0,0.3)',
            'strong': '0 12px 48px rgba(0,0,0,0.5)'
        }.get(obj.card_shadow_intensity, '0 8px 32px rgba(0,0,0,0.3)')
        
        return mark_safe(f'''
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
        
        <div id="qr-live-preview-container" style="background:#f5f5f5;padding:20px;border-radius:10px;margin:20px 0;">
            <div id="qr-preview-bg" style="
                background: linear-gradient(135deg, {obj.color_background} 0%, #0f1419 100%);
                padding: 40px 20px;
                border-radius: 16px;
                font-family: 'Cairo', sans-serif;
                font-size: {obj.font_size_base}px;
            ">
                <div id="qr-preview-card" style="
                    max-width: {obj.card_max_width}px;
                    margin: 0 auto;
                    background: {obj.color_surface}{'cc' if obj.enable_glassmorphism else ''};
                    {'backdrop-filter: blur(10px);' if obj.enable_glassmorphism else ''}
                    border-radius: {obj.card_border_radius}px;
                    padding: {obj.card_padding}px;
                    box-shadow: {box_shadow};
                    border: 1px solid {obj.color_primary}33;
                    position: relative;
                ">
                    <div style="position:absolute;top:10px;left:10px;background:#28a745;color:white;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                        <i class="fas fa-eye"></i> معاينة فورية ⚡
                    </div>
                    
                    {'<div style="text-align:center;margin-bottom:' + str(obj.element_spacing) + 'px;"><i class="fas fa-box-open" id="product-icon" style="font-size:48px;color:' + obj.color_primary + ';"></i></div>' if obj.show_product_icon else ''}
                    
                    {'<div style="text-align:center;margin-bottom:' + str(obj.element_spacing) + 'px;"><h2 id="logo-text" style="font-size:28px;font-weight:' + obj.font_weight_heading + ';background:linear-gradient(135deg,' + obj.color_primary + ',' + obj.color_secondary + ');-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0;">' + obj.logo_text + '</h2></div>' if obj.show_logo else ''}
                    
                    <div style="text-align:center;margin-bottom:{obj.element_spacing}px;">
                        <span id="product-code" style="display:inline-block;background:{obj.color_primary}22;color:{obj.color_primary};padding:6px 14px;border-radius:8px;font-size:13px;font-weight:600;font-family:'Courier New',monospace;border:1px solid {obj.color_primary}44;">
                            <i class="fas fa-barcode"></i> DEMO001
                        </span>
                    </div>
                    
                    <h1 id="product-name" style="font-size:24px;font-weight:{obj.font_weight_heading};color:{obj.color_text};text-align:center;margin:0 0 {obj.element_spacing}px 0;">
                        منتج تجريبي للمعاينة
                    </h1>
                    
                    {'<div style="text-align:center;margin-bottom:' + str(obj.element_spacing) + 'px;"><span id="category-badge" style="display:inline-block;background:linear-gradient(135deg,' + obj.color_primary + ',' + obj.color_secondary + ');color:' + obj.color_background + ';padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600;">قماش</span></div>' if obj.show_category_badge else ''}
                    
                    <div id="price-section" style="
                        background: {'linear-gradient(135deg,' + obj.color_primary + '22,' + obj.color_primary + '11)' if obj.show_price_badge else 'transparent'};
                        border: {'1px solid ' + obj.color_primary + '33' if obj.show_price_badge else 'none'};
                        border-radius: 16px;
                        padding: {obj.element_spacing}px;
                        text-align: center;
                        margin-bottom: {obj.element_spacing}px;
                    ">
                        <div id="price-label" style="color:{obj.color_text_secondary};font-size:13px;margin-bottom:8px;">السعر</div>
                        <div id="price-value" style="
                            font-size:{obj.price_font_size}px;
                            font-weight:800;
                            background:linear-gradient(135deg,{obj.color_primary},{obj.color_secondary});
                            -webkit-background-clip:text;
                            -webkit-text-fill-color:transparent;
                            font-family:'Courier New',monospace;
                            line-height:1;
                        ">
                            1,500 <span id="price-currency" style="font-size:18px;color:{obj.color_text_secondary};">ج.م</span>
                        </div>
                        <div id="unit-badge" style="
                            display:inline-block;
                            background:linear-gradient(135deg,{obj.color_primary},{obj.color_secondary});
                            color:{obj.color_background};
                            padding:6px 14px;
                            border-radius:12px;
                            font-size:13px;
                            font-weight:600;
                            margin-top:10px;
                        ">
                            <i class="fas fa-ruler"></i> لكل متر
                        </div>
                    </div>
                    
                    <div style="text-align:center;margin-top:{obj.element_spacing}px;">
                        <a href="#" id="website-btn" style="
                            display:inline-flex;
                            align-items:center;
                            gap:10px;
                            background:linear-gradient(135deg,{obj.color_primary},{obj.color_secondary});
                            color:{obj.color_background};
                            padding:{button_padding};
                            border-radius:{button_border_radius};
                            text-decoration:none;
                            font-weight:700;
                            box-shadow:0 4px 20px {obj.color_primary}55;
                        ">
                            <i class="fas fa-globe"></i><span>زيارة الموقع</span>
                        </a>
                    </div>
                    
                    <div id="update-time" style="text-align:center;color:{obj.color_text_secondary};font-size:12px;margin-top:{obj.element_spacing}px;">
                        <i class="far fa-clock"></i> تحديث تلقائي فوري
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        (function() {{
            function updatePreviewColors() {{
                const primary = document.getElementById('id_color_primary')?.value || '{obj.color_primary}';
                const secondary = document.getElementById('id_color_secondary')?.value || '{obj.color_secondary}';
                const background = document.getElementById('id_color_background')?.value || '{obj.color_background}';
                const surface = document.getElementById('id_color_surface')?.value || '{obj.color_surface}';
                const text = document.getElementById('id_color_text')?.value || '{obj.color_text}';
                const textSecondary = document.getElementById('id_color_text_secondary')?.value || '{obj.color_text_secondary}';
                
                const bg = document.getElementById('qr-preview-bg');
                if (bg) bg.style.background = `linear-gradient(135deg, ${{background}} 0%, #0f1419 100%)`;
                
                const card = document.getElementById('qr-preview-card');
                if (card) {{
                    card.style.background = surface + '{'cc' if obj.enable_glassmorphism else ''}';
                    card.style.borderColor = `${{primary}}33`;
                }}
                
                const icon = document.getElementById('product-icon');
                if (icon) icon.style.color = primary;
                
                const logo = document.getElementById('logo-text');
                if (logo) {{
                    logo.style.background = `linear-gradient(135deg, ${{primary}}, ${{secondary}})`;
                    logo.style.webkitBackgroundClip = 'text';
                    logo.style.webkitTextFillColor = 'transparent';
                }}
                
                const code = document.getElementById('product-code');
                if (code) {{
                    code.style.background = `${{primary}}22`;
                    code.style.color = primary;
                    code.style.borderColor = `${{primary}}44`;
                }}
                
                const name = document.getElementById('product-name');
                if (name) name.style.color = text;
                
                const badge = document.getElementById('category-badge');
                if (badge) {{
                    badge.style.background = `linear-gradient(135deg, ${{primary}}, ${{secondary}})`;
                    badge.style.color = background;
                }}
                
                const priceSection = document.getElementById('price-section');
                if (priceSection) {{
                    priceSection.style.background = `linear-gradient(135deg, ${{primary}}22, ${{primary}}11)`;
                    priceSection.style.borderColor = `${{primary}}33`;
                }}
                
                const priceLabel = document.getElementById('price-label');
                if (priceLabel) priceLabel.style.color = textSecondary;
                
                const priceCurrency = document.getElementById('price-currency');
                if (priceCurrency) priceCurrency.style.color = textSecondary;
                
                const priceValue = document.getElementById('price-value');
                if (priceValue) {{
                    priceValue.style.background = `linear-gradient(135deg, ${{primary}}, ${{secondary}})`;
                    priceValue.style.webkitBackgroundClip = 'text';
                    priceValue.style.webkitTextFillColor = 'transparent';
                }}
                
                const unitBadge = document.getElementById('unit-badge');
                if (unitBadge) {{
                    unitBadge.style.background = `linear-gradient(135deg, ${{primary}}, ${{secondary}})`;
                    unitBadge.style.color = background;
                }}
                
                const btn = document.getElementById('website-btn');
                if (btn) {{
                    btn.style.background = `linear-gradient(135deg, ${{primary}}, ${{secondary}})`;
                    btn.style.color = background;
                    btn.style.boxShadow = `0 4px 20px ${{primary}}55`;
                }}
                
                const time = document.getElementById('update-time');
                if (time) time.style.color = textSecondary;
            }}
            
            setTimeout(function() {{
                const colorInputs = ['id_color_primary', 'id_color_secondary', 'id_color_background', 'id_color_surface', 'id_color_text', 'id_color_text_secondary'];
                colorInputs.forEach(function(id) {{
                    const input = document.getElementById(id);
                    if (input) {{
                        input.addEventListener('input', updatePreviewColors);
                        input.addEventListener('change', updatePreviewColors);
                    }}
                }});
                updatePreviewColors();
            }}, 500);
        }})();
        </script>
        ''')
    live_preview.short_description = '👁️ معاينة فورية'

    def sync_to_cloudflare(self, request, queryset):
        """مزامنة الإعدادات مع Cloudflare"""
        for obj in queryset:
            try:
                from accounting.cloudflare_sync import sync_qr_design_to_cloudflare
                result = sync_qr_design_to_cloudflare(obj)
                
                if result.get('success'):
                    obj.cloudflare_synced = True
                    obj.save()
                    messages.success(
                        request,
                        f'✅ تمت المزامنة بنجاح مع Cloudflare'
                    )
                else:
                    messages.error(
                        request,
                        f'❌ فشلت المزامنة: {result.get("error")}'
                    )
            except Exception as e:
                messages.error(request, f'❌ خطأ: {str(e)}')
    
    sync_to_cloudflare.short_description = '🔄 مزامنة مع Cloudflare'
    
    def test_preview(self, request, queryset):
        """معاينة التصميم"""
        messages.info(
            request,
            'افتح رابط المعاينة في تبويب جديد'
        )
    test_preview.short_description = '👁️ معاينة التصميم'
    
    # ====== Custom URLs ======
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'sync/',
                self.admin_site.admin_view(self.sync_view),
                name='sync_qr_design'
            ),
        ]
        return custom_urls + urls
    
    def sync_view(self, request):
        """صفحة المزامنة"""
        obj = QRDesignSettings.objects.first()
        if not obj:
            messages.error(request, 'لا توجد إعدادات. قم بإنشاء إعدادات أولاً.')
            return redirect('admin:public_qrdesignsettings_changelist')
        
        try:
            from accounting.cloudflare_sync import sync_qr_design_to_cloudflare
            result = sync_qr_design_to_cloudflare(obj)
            
            if result.get('success'):
                obj.cloudflare_synced = True
                obj.save()
                messages.success(request, '✅ تمت المزامنة بنجاح!')
            else:
                messages.error(request, f'❌ فشلت المزامنة: {result.get("error")}')
        except Exception as e:
            messages.error(request, f'❌ خطأ: {str(e)}')
        
        return redirect('admin:public_qrdesignsettings_changelist')
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        
        # إضافة رابط المعاينة
        if object_id:
            extra_context['preview_url'] = reverse('public:qr_design_preview')
            extra_context['sync_url'] = reverse('admin:sync_qr_design')
        
        return super().changeform_view(request, object_id, form_url, extra_context)


# إلغاء تسجيل CloudflareSettings القديم إذا كان موجود
try:
    admin.site.unregister(CloudflareSettings)
except:
    pass
