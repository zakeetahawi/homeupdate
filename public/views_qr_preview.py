"""
QR Design Preview Views
معاينة تصميم صفحات QR محلياً قبل المزامنة
"""
from django.shortcuts import render
from django.http import HttpResponse
from public.models import QRDesignSettings


def qr_design_preview(request):
    """
    معاينة تصميم صفحة QR محلياً
    """
    # الحصول على الإعدادات (مباشرة من DB بدون cache للمعاينة)
    from django.core.cache import cache
    cache.delete('qr_design_settings')  # مسح cache لضمان قراءة آخر التحديثات
    settings = QRDesignSettings.get_settings()
    
    # بيانات تجريبية للمنتج
    sample_product = {
        'code': 'DEMO001',
        'name': 'منتج تجريبي',
        'name_en': 'Demo Product',
        'price': 1500.00,
        'unit': 'متر',
        'category': 'قماش'
    }
    
    # بيانات تجريبية للبنك
    sample_bank = {
        'code': 'CIB002',
        'bank_name': 'بنك CIB شركات',
        'bank_name_en': 'CIB Companies',
        'account_number': '100054913731',
        'account_holder': 'شركات',
        'account_holder_en': 'Companies',
        'currency': 'EGP'
    }
    
    # HTML template
    html_template = generate_preview_html(settings, sample_product, sample_bank)
    
    return HttpResponse(html_template)


def generate_preview_html(settings, product, bank):
    """توليد HTML للمعاينة"""
    
    # تحديد الألوان
    colors = {
        'primary': settings.color_primary,
        'secondary': settings.color_secondary,
        'background': settings.color_background,
        'surface': settings.color_surface,
        'text': settings.color_text,
        'text_secondary': settings.color_text_secondary,
    }
    
    # بناء أزرار التواصل الاجتماعي
    social_buttons = ''
    if settings.show_social_media:
        social_list = []
        
        if settings.facebook_url:
            social_list.append(f'<a href="{settings.facebook_url}" target="_blank" class="social-btn" title="Facebook"><i class="fab fa-facebook-f"></i></a>')
        
        if settings.instagram_url:
            social_list.append(f'<a href="{settings.instagram_url}" target="_blank" class="social-btn" title="Instagram"><i class="fab fa-instagram"></i></a>')
        
        if settings.twitter_url:
            social_list.append(f'<a href="{settings.twitter_url}" target="_blank" class="social-btn" title="Twitter"><i class="fab fa-twitter"></i></a>')
        
        if settings.youtube_url:
            social_list.append(f'<a href="{settings.youtube_url}" target="_blank" class="social-btn" title="YouTube"><i class="fab fa-youtube"></i></a>')
        
        if settings.tiktok_url:
            social_list.append(f'<a href="{settings.tiktok_url}" target="_blank" class="social-btn" title="TikTok"><i class="fab fa-tiktok"></i></a>')
        
        if settings.whatsapp_number:
            whatsapp_link = f'https://wa.me/{settings.whatsapp_number}'
            social_list.append(f'<a href="{whatsapp_link}" target="_blank" class="social-btn whatsapp" title="WhatsApp"><i class="fab fa-whatsapp"></i></a>')
        
        if settings.phone_number:
            social_list.append(f'<a href="tel:{settings.phone_number}" class="social-btn" title="اتصل بنا"><i class="fas fa-phone"></i></a>')
        
        if settings.email:
            social_list.append(f'<a href="mailto:{settings.email}" class="social-btn" title="البريد الإلكتروني"><i class="fas fa-envelope"></i></a>')
        
        if social_list:
            social_buttons = '<div class="social-media">' + ''.join(social_list) + '</div>'
    
    # زر الشكوى
    complaint_button = ''
    if settings.show_complaint_button:
        complaint_button = f'''
            <a href="{settings.complaint_url}" class="btn btn-complaint" target="_blank">
                <i class="fas fa-exclamation-circle"></i> {settings.complaint_button_text}
            </a>
        '''
    
    # زر الموقع
    website_button = ''
    if settings.show_website_button:
        website_button = f'''
            <a href="{settings.website_url}" class="btn btn-primary" target="_blank">
                <i class="fas fa-globe"></i> زيارة الموقع
            </a>
        '''
    
    # الشعار
    logo_html = ''
    if settings.show_logo:
        if settings.logo:
            logo_html = f'<img src="{settings.logo.url}" alt="{settings.logo_text}" class="logo">'
        else:
            logo_html = f'<h1 class="logo-text">{settings.logo_text}</h1>'
    
    # Footer
    footer_html = ''
    if settings.show_footer:
        footer_html = f'<div class="footer">{settings.footer_text}</div>'
    
    # تطبيق الأنيميشن
    animation_class = 'animated' if settings.enable_animations else ''
    glassmorphism_class = 'glass' if settings.enable_glassmorphism else ''
    
    html = f'''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>معاينة تصميم QR - {settings.logo_text}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {{
            --primary: {colors['primary']};
            --secondary: {colors['secondary']};
            --background: {colors['background']};
            --surface: {colors['surface']};
            --text: {colors['text']};
            --text-secondary: {colors['text_secondary']};
            --border-radius: {settings.card_border_radius}px;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Cairo', sans-serif;
            background: var(--background);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            background: linear-gradient(135deg, var(--background) 0%, #0f1419 100%);
            position: relative;
            overflow-x: hidden;
        }}
        
        /* Animated background circles */
        body::before, body::after {{
            content: '';
            position: absolute;
            border-radius: 50%;
            opacity: 0.1;
            animation: float 20s infinite ease-in-out;
        }}
        
        body::before {{
            width: 300px;
            height: 300px;
            background: var(--primary);
            top: -150px;
            right: -150px;
        }}
        
        body::after {{
            width: 400px;
            height: 400px;
            background: var(--secondary);
            bottom: -200px;
            left: -200px;
            animation-delay: -10s;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0) rotate(0deg); }}
            50% {{ transform: translateY(-20px) rotate(180deg); }}
        }}
        
        .container {{
            max-width: 600px;
            width: 100%;
            position: relative;
            z-index: 1;
        }}
        
        .card {{
            background: var(--surface);
            border-radius: var(--border-radius);
            padding: 30px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            position: relative;
        }}
        
        .card.glass {{
            /* استخدام لون البطاقة من الإعدادات مع شفافية */
            background: {colors['surface']}cc;
            backdrop-filter: blur(10px);
            border: 1px solid {colors['primary']}33;
        }}
        
        .card.animated {{
            animation: fadeIn 0.8s ease-out;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .logo {{
            max-width: 150px;
            margin-bottom: 20px;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
        }}
        
        .logo-text {{
            font-size: 2.5em;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }}
        
        .preview-badge {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: #dc3545;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .section-title {{
            color: var(--primary);
            font-size: 1.3em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            justify-content: center;
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .info-row:last-child {{
            border-bottom: none;
        }}
        
        .info-label {{
            color: var(--text-secondary);
            font-size: 0.9em;
        }}
        
        .info-value {{
            color: var(--text);
            font-weight: 600;
        }}
        
        .social-media {{
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
            margin: 20px 0;
        }}
        
        .social-btn {{
            width: 45px;
            height: 45px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            font-size: 18px;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .social-btn:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px {colors['primary']}66;
        }}
        
        .social-btn.whatsapp {{
            background: linear-gradient(135deg, #25D366, #128C7E);
        }}
        
        .btn {{
            display: inline-block;
            padding: 12px 30px;
            margin: 10px 5px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s;
            border: 2px solid transparent;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: scale(1.05);
            box-shadow: 0 5px 20px {colors['primary']}66;
        }}
        
        .btn-complaint {{
            background: transparent;
            color: var(--primary);
            border-color: var(--primary);
        }}
        
        .btn-complaint:hover {{
            background: var(--primary);
            color: var(--background);
        }}
        
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
            color: var(--text-secondary);
            font-size: 0.85em;
        }}
        
        {settings.custom_css}
    </style>
</head>
<body>
    <div class="container">
        <div class="card {glassmorphism_class} {animation_class}">
            <div class="preview-badge">معاينة محلية</div>
            
            {logo_html}
            
            <!-- قسم المنتج التجريبي -->
            <div class="section">
                <div class="section-title">
                    <i class="fas fa-box-open"></i>
                    <span>منتج تجريبي</span>
                </div>
                <div class="info-row">
                    <span class="info-label">الكود</span>
                    <span class="info-value">{product['code']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">الاسم</span>
                    <span class="info-value">{product['name']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">السعر</span>
                    <span class="info-value" style="color: var(--primary);">{product['price']:,.2f} جنيه</span>
                </div>
            </div>
            
            <!-- قسم البنك التجريبي -->
            <div class="section">
                <div class="section-title">
                    <i class="fas fa-university"></i>
                    <span>حساب بنكي تجريبي</span>
                </div>
                <div class="info-row">
                    <span class="info-label">البنك</span>
                    <span class="info-value">{bank['bank_name']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">رقم الحساب</span>
                    <span class="info-value">{bank['account_number']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">صاحب الحساب</span>
                    <span class="info-value">{bank['account_holder']}</span>
                </div>
            </div>
            
            <!-- التواصل الاجتماعي -->
            {social_buttons}
            
            <!-- الأزرار -->
            <div style="margin-top: 30px;">
                {website_button}
                {complaint_button}
            </div>
            
            <!-- التذييل -->
            {footer_html}
        </div>
    </div>
    
    <script>
        {settings.custom_js}
    </script>
</body>
</html>
'''
    
    return html
