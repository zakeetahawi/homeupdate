"""
QR Design Settings Admin
لوحة تحكم متقدمة لإعدادات تصميم صفحات QR
"""

import json

import requests
from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import QRDesignSettings


@admin.register(QRDesignSettings)
class QRDesignSettingsAdmin(admin.ModelAdmin):
    """
    لوحة تحكم إعدادات تصميم QR

    📌 ملاحظات التصميم الحالي:
    - اسم المنتج: #1a1a1a (أسود ثابت)
    - العملة: #542804 (بني ثابت)
    - قيم المعلومات: #1a1a1a (أسود ثابت)
    - صفحة البنك: لا تظهر أسماء - فقط شعارات
    - حجم لوغو البنك: 350px ثابت
    """

    fieldsets = [
        (
            "🎨 الشعار / Logo",
            {
                "fields": [
                    "logo",
                    "logo_preview",
                    ("logo_text", "logo_text_en"),
                    ("show_logo", "logo_size"),
                ],
                "description": """
                <div style="background:#d1ecf1; border:1px solid #bee5eb; padding:12px; border-radius:6px; margin:10px 0;">
                    <strong>ℹ️ معلومات مهمة:</strong>
                    <ul style="margin:5px 0; line-height:1.8;">
                        <li><strong>صفحة المنتج:</strong> حجم اللوغو حسب إعداد "logo_size" أدناه</li>
                        <li><strong>صفحة البنك:</strong> حجم اللوغو ثابت 350px (لا يتأثر بـ logo_size)</li>
                        <li><strong>الأسماء:</strong> لا تظهر أسماء الشركة أو البنك في صفحة البنك - فقط الشعارات</li>
                    </ul>
                </div>
            """,
                "classes": ["collapse"],
            },
        ),
        (
            "🎨 الألوان / Colors",
            {
                "fields": [
                    ("color_primary", "color_secondary"),
                    ("color_background", "color_surface"),
                    ("color_text", "color_text_secondary"),
                    "background_image",
                    ("color_card", "color_price"),
                    ("color_button", "color_button_text"),
                    ("color_badge", "color_badge_text"),
                    ("color_product_name", "color_label"),
                    "live_preview",
                ],
                "description": """
                <div style="background:#fff3cd; border:1px solid #ffc107; padding:15px; border-radius:8px; margin:10px 0;">
                    <h4 style="margin:0 0 10px 0; color:#856404;">⚠️ ملاحظات مهمة:</h4>
                    <ul style="margin:5px 0; color:#856404; line-height:1.8;">
                        <li><strong>الألوان الثابتة (غير قابلة للتغيير):</strong>
                            <br>• اسم المنتج: <code>#1a1a1a</code> (أسود داكن)
                            <br>• العملة: <code>#542804</code> (بني داكن - نفس لون الأزرار)
                            <br>• قيم المعلومات (العملة/الوحدة): <code>#1a1a1a</code> (أسود)
                        </li>
                        <li><strong>صفحة البنك:</strong> لا تظهر أسماء (الشركة أو البنك) - فقط شعارات</li>
                        <li><strong>حجم اللوغو في صفحة البنك:</strong> 350px</li>
                    </ul>
                </div>
                💡 نصيحة: بعد تعديل الألوان، احفظ الإعدات ثم أعد تحميل الصفحة (F5) لرؤية المعاينة المحدثة
            """,
            },
        ),
        (
            "✍️ الطباعة / Typography",
            {
                "fields": [
                    "font_family",
                    ("font_size_base", "font_weight_heading"),
                    "price_font_size",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "📐 المسافات والأبعاد / Spacing & Sizing",
            {
                "fields": [
                    "card_max_width",
                    ("card_padding", "element_spacing"),
                    "card_border_radius",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "🌟 الظلال والتأثيرات / Effects",
            {
                "fields": [
                    "card_shadow_intensity",
                    "enable_gradient_bg",
                    "enable_animations",
                    "enable_glassmorphism",
                    "enable_hover_effects",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "🔘 الأزرار / Buttons",
            {
                "fields": [
                    ("button_style", "button_size"),
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "💰 عرض السعر / Price Display",
            {
                "fields": [
                    "show_price_badge",
                    ("show_product_icon", "show_category_badge"),
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "🔗 الروابط / Links",
            {
                "fields": [
                    "website_url",
                    "show_website_button",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "📱 التواصل الاجتماعي / Social Media",
            {
                "fields": [
                    "show_social_media",
                    ("facebook_url", "instagram_url"),
                    ("twitter_url", "youtube_url"),
                    ("tiktok_url", "whatsapp_number"),
                    ("phone_number", "email"),
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "📝 الشكوى / Complaint",
            {
                "fields": [
                    "show_complaint_button",
                    "complaint_url",
                    ("complaint_button_text", "complaint_button_text_en"),
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "⚙️ متقدم / Advanced",
            {
                "fields": [
                    "custom_css",
                    "custom_js",
                    "show_footer",
                    "footer_text",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            " معلومات المزامنة / Sync Info",
            {
                "fields": [
                    "cloudflare_synced",
                    "last_synced_at",
                    "sync_status_display",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    readonly_fields = [
        "logo_preview",
        "color_preview",
        "last_synced_at",
        "cloudflare_synced",
        "sync_status_display",
        "live_preview",
    ]

    list_display = [
        "settings_name",
        "logo_display",
        "colors_display",
        "sync_status",
        "actions_display",
    ]

    actions = [
        "sync_to_cloudflare",
        "test_preview",
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

        cache.delete("qr_design_settings")
        messages.success(request, "✅ تم حفظ الإعدادات بنجاح وتحديث المعاينة")
        messages.info(
            request,
            "💡 لا تنسى مزامنة التصميم مع Cloudflare لتطبيق التغييرات",
            extra_tags="safe",
        )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """إضافة معلومات إضافية في أعلى النموذج"""
        extra_context = extra_context or {}
        extra_context["design_info"] = mark_safe(
            """
            <div style="background:#e7f3ff; border:2px solid #2196f3; padding:15px; border-radius:8px; margin:15px 0;">
                <h3 style="margin:0 0 10px 0; color:#0d47a1;">📋 معلومات التصميم الحالي</h3>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px;">
                    <div>
                        <h4 style="color:#1976d2; margin:10px 0 5px 0;">🎨 الألوان الثابتة (غير قابلة للتغيير):</h4>
                        <ul style="margin:5px 0; line-height:1.8;">
                            <li><strong>اسم المنتج:</strong> <code style="background:#1a1a1a; color:#fff; padding:2px 8px; border-radius:3px;">#1a1a1a</code> (أسود داكن)</li>
                            <li><strong>رمز العملة:</strong> <code style="background:#542804; color:#fff; padding:2px 8px; border-radius:3px;">#542804</code> (بني داكن)</li>
                            <li><strong>قيم المعلومات:</strong> <code style="background:#1a1a1a; color:#fff; padding:2px 8px; border-radius:3px;">#1a1a1a</code> (أسود)</li>
                        </ul>
                    </div>
                    <div>
                        <h4 style="color:#1976d2; margin:10px 0 5px 0;">🏦 صفحة البنك:</h4>
                        <ul style="margin:5px 0; line-height:1.8;">
                            <li><strong>حجم اللوغو:</strong> 350px (ثابت - لا يتأثر بإعداد logo_size)</li>
                            <li><strong>العرض:</strong> لا تظهر أسماء الشركة أو البنك</li>
                            <li><strong>الشعارات فقط:</strong> لوغو الشركة + شعار البنك</li>
                        </ul>
                    </div>
                </div>
            </div>
        """
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    # ====== Display Methods ======

    def settings_name(self, obj):
        """اسم الإعدادات"""
        return format_html(
            '<strong style="font-size:14px;">🎨 {}</strong>', obj.logo_text
        )

    settings_name.short_description = "الإعدادات"

    def logo_display(self, obj):
        """عرض الشعار"""
        from django.utils.safestring import mark_safe

        if obj.logo:
            return format_html(
                '<img src="{0}" style="height:40px; border-radius:5px;">', obj.logo.url
            )
        return mark_safe('<span style="color:#999;">📷 لا يوجد</span>')

    logo_display.short_description = "الشعار"

    def colors_display(self, obj):
        """عرض الألوان"""
        return format_html(
            '<div style="display:flex; gap:5px;"><div style="width:30px; height:30px; background:{0}; border-radius:5px; border:1px solid #ddd;" title="Primary"></div><div style="width:30px; height:30px; background:{1}; border-radius:5px; border:1px solid #ddd;" title="Secondary"></div><div style="width:30px; height:30px; background:{2}; border-radius:5px; border:1px solid #ddd;" title="Background"></div></div>',
            obj.color_primary,
            obj.color_secondary,
            obj.color_background,
        )

    colors_display.short_description = "الألوان"

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

    sync_status.short_description = "المزامنة"

    def actions_display(self, obj):
        """أزرار الإجراءات"""
        return format_html(
            '<a href="{0}" class="button" style="padding:5px 10px; background:#007bff; color:white; text-decoration:none; border-radius:3px; margin:2px;">🔄 مزامنة</a><a href="{1}" class="button" target="_blank" style="padding:5px 10px; background:#28a745; color:white; text-decoration:none; border-radius:3px; margin:2px;">👁️ معاينة</a>',
            reverse("admin:sync_qr_design"),
            reverse("public:qr_design_preview"),
        )

    actions_display.short_description = "الإجراءات"

    # ====== Readonly Field Methods ======

    def logo_preview(self, obj):
        """معاينة الشعار"""
        from django.utils.safestring import mark_safe

        if obj and obj.logo:
            return mark_safe(
                f'<div style="margin:10px 0;">'
                f'<img src="{obj.logo.url}" style="max-width:200px; max-height:200px; border:2px solid #ddd; padding:10px; background:white; border-radius:10px;">'
                f'<p style="margin-top:10px; color:#666;">الحجم الموصى به: 500x500 بكسل</p>'
                f"</div>"
            )
        return mark_safe('<p style="color:#999;">لم يتم رفع شعار بعد</p>')

    logo_preview.short_description = "معاينة الشعار"

    def color_preview(self, obj):
        """معاينة الألوان"""
        from django.utils.safestring import mark_safe

        if not obj:
            return ""

        return mark_safe(
            f"""
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
        """
        )

    color_preview.short_description = "معاينة الألوان"

    def sync_status_display(self, obj):
        """عرض حالة المزامنة التفصيلية"""
        from django.utils.safestring import mark_safe

        if not obj:
            return ""

        status_color = "#28a745" if obj.cloudflare_synced else "#dc3545"
        status_text = "متزامن ✓" if obj.cloudflare_synced else "غير متزامن ✗"

        return mark_safe(
            f"""
            <div style="padding:15px; background:#f8f9fa; border-radius:8px; border-left:4px solid {status_color};">
                <p style="margin:0 0 5px 0; font-weight:bold; color:{status_color};">
                    {status_text}
                </p>
                <p style="margin:0; font-size:12px; color:#666;">
                    آخر تحديث: {obj.last_synced_at.strftime('%Y-%m-%d %H:%M:%S') if obj.last_synced_at else 'لم يتم'}
                </p>
            </div>
        """
        )

    sync_status_display.short_description = "حالة المزامنة"

    def live_preview(self, obj):
        """معاينة فورية - نسخة مطابقة 100% لقالب Cloudflare Worker"""
        if not obj:
            return mark_safe('<p style="color:#999;">لا توجد إعدادات</p>')

        # Background image style
        bg_image_style = ""
        if obj.background_image:
            bg_image_style = f"background-image: url({obj.background_image.url});background-size: cover;background-position: center;background-blend-mode: overlay;"

        return mark_safe(
            f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&amp;display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
        
        <style>
            #qr-preview-wrapper {{
                --gold: {obj.color_primary};
                --gold-light: {obj.color_secondary};
                --gold-dark: {obj.color_primary};
                --dark: {obj.color_background};
                --dark-light: {obj.color_surface};
                --dark-surface: {obj.color_surface};
                --card-bg: {obj.color_card};
                --button-bg: {obj.color_button};
                --button-text: {obj.color_button_text};
                --badge-bg: {obj.color_badge};
                --badge-text: {obj.color_badge_text};
                --price-color: {obj.color_price};
            }}
            
            #qr-preview-wrapper * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            #qr-preview-wrapper {{
                font-family: 'Cairo', sans-serif;
                background: linear-gradient(135deg, var(--dark) 0%, var(--dark-light) 50%, var(--dark-surface) 100%);
                {bg_image_style}
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
                overflow-x: hidden;
                border-radius: 12px;
                margin: 20px 0;
            }}
            
            #qr-preview-wrapper::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image:
                    radial-gradient(circle at 20% 80%, rgba(212, 175, 55, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 20%, rgba(212, 175, 55, 0.08) 0%, transparent 50%);
                pointer-events: none;
                z-index: 0;
            }}
            
            #qr-preview-wrapper .container {{
                max-width: 450px;
                width: 100%;
                position: relative;
                z-index: 1;
            }}
            
            #qr-preview-wrapper .card {{
                background: var(--card-bg);
                opacity: 0.95;
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(212, 175, 55, 0.2);
                border-radius: 24px;
                overflow: hidden;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
                animation: fadeInUp 0.6s ease-out;
            }}
            
            @keyframes fadeInDown {{
                from {{ opacity: 0; transform: translateY(-20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            @keyframes fadeInUp {{
                from {{ opacity: 0; transform: translateY(30px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            #qr-preview-wrapper .product-visual {{
                height: 180px;
                background: linear-gradient(135deg, var(--dark-surface) 0%, var(--dark-light) 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
            }}
            
            #qr-preview-wrapper .product-visual::before {{
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: conic-gradient(from 0deg,
                    transparent 0deg 90deg,
                    rgba(212, 175, 55, 0.1) 90deg 180deg,
                    transparent 180deg 270deg,
                    rgba(212, 175, 55, 0.05) 270deg 360deg);
                animation: rotate 20s linear infinite;
            }}
            
            @keyframes rotate {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            
            #qr-preview-wrapper .product-logo {{
                max-width: {obj.logo_size}px;
                max-height: {int(obj.logo_size * 0.7)}px;
                object-fit: contain;
                position: relative;
                z-index: 1;
                filter: drop-shadow(0 4px 20px rgba(0, 0, 0, 0.3));
            }}
            
            #qr-preview-wrapper .category-badge {{
                position: absolute;
                top: 16px;
                right: 16px;
                background: var(--badge-bg);
                color: var(--badge-text);
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
                z-index: 2;
                box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4);
            }}
            
            #qr-preview-wrapper .content {{
                padding: 28px 24px;
            }}
            
            #qr-preview-wrapper .product-code {{
                display: inline-block;
                background: var(--badge-bg);
                color: var(--badge-text);
                padding: 6px 14px;
                border-radius: 8px;
                font-size: 0.85rem;
                font-weight: 600;
                margin-bottom: 12px;
                font-family: 'Courier New', monospace;
                letter-spacing: 1px;
                border: 1px solid rgba(212, 175, 55, 0.3);
            }}
            
            #qr-preview-wrapper .product-name {{
                font-size: 1.6rem;
                font-weight: 700;
                color: #1a1a1a;
                margin-bottom: 20px;
                line-height: 1.4;
            }}
            
            #qr-preview-wrapper .price-section {{
                background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(212, 175, 55, 0.05) 100%);
                border: 1px solid rgba(212, 175, 55, 0.3);
                border-radius: 16px;
                padding: 24px;
                text-align: center;
                margin-bottom: 24px;
                position: relative;
                overflow: hidden;
            }}
            
            #qr-preview-wrapper .price-section::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg, transparent, var(--gold), transparent);
            }}
            
            #qr-preview-wrapper .price-label {{
                color: #a0a0a0;
                font-size: 0.85rem;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            #qr-preview-wrapper .price {{
                font-size: 2.8rem;
                font-weight: 800;
                color: var(--price-color);
                display: flex;
                align-items: baseline;
                justify-content: center;
                gap: 8px;
                margin-bottom: 8px;
                font-family: 'Courier New', monospace;
            }}
            
            #qr-preview-wrapper .currency {{
                font-size: 1.2rem;
                color: #542804;
                font-weight: 600;
            }}
            
            #qr-preview-wrapper .unit-badge {{
                display: inline-block;
                background: var(--badge-bg);
                color: var(--badge-text);
                padding: 6px 14px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-top: 8px;
            }}
            
            #qr-preview-wrapper .footer {{
                text-align: center;
                padding: 0 24px 28px;
                border-top: 1px solid rgba(212, 175, 55, 0.1);
                padding-top: 24px;
            }}
            
            #qr-preview-wrapper .visit-btn {{
                display: inline-flex;
                align-items: center;
                gap: 10px;
                background: var(--button-bg);
                color: var(--button-text);
                padding: 16px 32px;
                border-radius: 14px;
                text-decoration: none;
                font-weight: 700;
                font-size: 1rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3);
                position: relative;
                overflow: hidden;
            }}
            
            #qr-preview-wrapper .visit-btn::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
                transition: left 0.5s;
            }}
            
            #qr-preview-wrapper .visit-btn:hover::before {{
                left: 100%;
            }}
            
            #qr-preview-wrapper .visit-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 30px rgba(212, 175, 55, 0.5);
            }}
            
            #qr-preview-wrapper .updated-at {{
                color: #666;
                font-size: 0.75rem;
                margin-top: 16px;
                font-weight: 400;
            }}
        </style>
        
        <div id="qr-preview-wrapper">
            <div class="container">
                <!-- Product Card -->
                <div class="card">
                    <!-- Product Visual Header -->
                    <div class="product-visual">
                        {f'<img src="{obj.logo.url}" alt="logo" class="product-logo">' if obj.logo else '<i class="fas fa-gem" style="font-size: 4rem; color: var(--gold); opacity: 0.8; position: relative; z-index: 1;"></i>'}
                        <span class="category-badge">قماش</span>
                    </div>
                    
                    <!-- Product Content -->
                    <div class="content">
                        <span class="product-code"><i class="fas fa-barcode"></i> DEMO001</span>
                        <h1 class="product-name">منتج تجريبي للمعاينة</h1>
                        
                        <!-- Price Section -->
                        <div class="price-section">
                            <div class="price-label">السعر</div>
                            <div class="price">
                                <span>1,500</span>
                                <span class="currency">ج.م</span>
                            </div>
                            <span class="unit-badge"><i class="fas fa-ruler"></i> لكل متر</span>
                        </div>
                    </div>
                    
                    <!-- Footer -->
                    <div class="footer">
                        <a href="#" class="visit-btn">
                            <i class="fas fa-globe"></i>
                            <span>زيارة الموقع</span>
                        </a>
                        <div class="updated-at">
                            <i class="far fa-clock"></i> معاينة فورية - يتم التحديث تلقائياً
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        (function() {{
            let updateTimer;
            
            function updatePreviewColors() {{
                clearTimeout(updateTimer);
                updateTimer = setTimeout(() => {{
                    const wrapper = document.getElementById('qr-preview-wrapper');
                    if (!wrapper) return;
                    
                    const getColor = (id, fallback) => {{
                        const el = document.getElementById('id_' + id);
                        return el ? el.value : fallback;
                    }};
                    
                    const primary = getColor('color_primary', '{obj.color_primary}');
                    const secondary = getColor('color_secondary', '{obj.color_secondary}');
                    const background = getColor('color_background', '{obj.color_background}');
                    const surface = getColor('color_surface', '{obj.color_surface}');
                    const text = getColor('color_text', '{obj.color_text}');
                    const textSecondary = getColor('color_text_secondary', '{obj.color_text_secondary}');
                    
                    wrapper.style.setProperty('--gold', primary);
                    wrapper.style.setProperty('--gold-light', secondary);
                    wrapper.style.setProperty('--gold-dark', primary);
                    wrapper.style.setProperty('--dark', background);
                    wrapper.style.setProperty('--dark-light', surface);
                    wrapper.style.setProperty('--dark-surface', surface);
                }}, 100);
            }}
            
            setTimeout(() => {{
                const colorInputs = document.querySelectorAll('input[type="color"]');
                colorInputs.forEach(input => {{
                    input.addEventListener('input', updatePreviewColors);
                    input.addEventListener('change', updatePreviewColors);
                }});
                updatePreviewColors();
            }}, 300);
        }})();
        </script>
        """
        )

    live_preview.short_description = "👁️ معاينة فورية"

    def sync_to_cloudflare(self, request, queryset):
        """مزامنة الإعدادات مع Cloudflare"""
        for obj in queryset:
            try:
                from accounting.cloudflare_sync import sync_qr_design_to_cloudflare

                result = sync_qr_design_to_cloudflare(obj)

                if result.get("success"):
                    obj.cloudflare_synced = True
                    obj.save()
                    messages.success(request, f"✅ تمت المزامنة بنجاح مع Cloudflare")
                else:
                    messages.error(request, f'❌ فشلت المزامنة: {result.get("error")}')
            except Exception as e:
                messages.error(request, f"❌ خطأ: {str(e)}")

    sync_to_cloudflare.short_description = "🔄 مزامنة مع Cloudflare"

    def test_preview(self, request, queryset):
        """معاينة التصميم"""
        messages.info(request, "افتح رابط المعاينة في تبويب جديد")

    test_preview.short_description = "👁️ معاينة التصميم"

    # ====== Custom URLs ======

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "sync/",
                self.admin_site.admin_view(self.sync_view),
                name="sync_qr_design",
            ),
        ]
        return custom_urls + urls

    def sync_view(self, request):
        """صفحة المزامنة"""
        obj = QRDesignSettings.objects.first()
        if not obj:
            messages.error(request, "لا توجد إعدادات. قم بإنشاء إعدادات أولاً.")
            return redirect("admin:public_qrdesignsettings_changelist")

        try:
            from accounting.cloudflare_sync import sync_qr_design_to_cloudflare

            result = sync_qr_design_to_cloudflare(obj)

            if result.get("success"):
                obj.cloudflare_synced = True
                obj.save()
                messages.success(request, "✅ تمت المزامنة بنجاح!")
            else:
                messages.error(request, f'❌ فشلت المزامنة: {result.get("error")}')
        except Exception as e:
            messages.error(request, f"❌ خطأ: {str(e)}")

        return redirect("admin:public_qrdesignsettings_changelist")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save_and_continue"] = False
        extra_context["show_save_and_add_another"] = False

        # إضافة رابط المعاينة
        if object_id:
            extra_context["preview_url"] = reverse("public:qr_design_preview")
            extra_context["sync_url"] = reverse("admin:sync_qr_design")

        return super().changeform_view(request, object_id, form_url, extra_context)


# إلغاء تسجيل CloudflareSettings القديم إذا كان موجود
try:
    admin.site.unregister(CloudflareSettings)
except:
    pass
