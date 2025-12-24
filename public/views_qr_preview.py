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
    """توليد HTML للمعاينة - مطابق 100% لقالب Cloudflare Worker"""
    
    # Format price with English numbers
    formatted_price = f"{product['price']:,.0f}".replace(',', ',')
    
    # Background image style
    bg_image_style = ''
    if settings.background_image:
        bg_image_style = f'background-image: url({settings.background_image.url});background-size: cover;background-position: center;background-blend-mode: overlay;'
    
    html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{product['name']} - معاينة محلية</title>
  <meta name="description" content="{product['name']} - السعر: {formatted_price} ج.م">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    :root {{
      --gold: {settings.color_primary};
      --gold-light: {settings.color_secondary};
      --gold-dark: {settings.color_primary};
      --dark: {settings.color_background};
      --dark-light: {settings.color_surface};
      --dark-surface: {settings.color_surface};
      --card-bg: {settings.color_card};
      --button-bg: {settings.color_button};
      --button-text: {settings.color_button_text};
      --badge-bg: {settings.color_badge};
      --badge-text: {settings.color_badge_text};
      --price-color: {settings.color_price};
    }}
    
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    
    body {{
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
    }}
    
    body::before {{
      content: '';
      position: fixed;
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
    
    .container {{
      max-width: 450px;
      width: 100%;
      position: relative;
      z-index: 1;
    }}
    
    .preview-badge {{
      position: fixed;
      top: 20px;
      left: 20px;
      background: #dc3545;
      color: white;
      padding: 10px 20px;
      border-radius: 25px;
      font-size: 14px;
      font-weight: bold;
      box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4);
      z-index: 1000;
      animation: pulse 2s infinite;
    }}
    
    @keyframes pulse {{
      0%, 100% {{ transform: scale(1); }}
      50% {{ transform: scale(1.05); }}
    }}
    
    /* Product Card */
    .card {{
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
    
    /* Product Visual Header */
    .product-visual {{
      height: 180px;
      background: linear-gradient(135deg, var(--dark-surface) 0%, var(--dark-light) 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
    }}
    
    .product-visual::before {{
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
    
    .product-logo {{
      max-width: {settings.logo_size}px;
      max-height: {int(settings.logo_size * 0.7)}px;
      object-fit: contain;
      position: relative;
      z-index: 1;
      filter: drop-shadow(0 4px 20px rgba(0, 0, 0, 0.3));
    }}
    
    .category-badge {{
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
    
    /* Content */
    .content {{
      padding: 28px 24px;
    }}
    
    .product-code {{
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
    
    .product-name {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 20px;
      line-height: 1.4;
    }}
    
    /* Price Section */
    .price-section {{
      background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(212, 175, 55, 0.05) 100%);
      border: 1px solid rgba(212, 175, 55, 0.3);
      border-radius: 16px;
      padding: 24px;
      text-align: center;
      margin-bottom: 24px;
      position: relative;
      overflow: hidden;
    }}
    
    .price-section::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--gold), transparent);
    }}
    
    .price-label {{
      color: #a0a0a0;
      font-size: 0.85rem;
      margin-bottom: 8px;
      font-weight: 500;
    }}
    
    .price {{
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
    
    .currency {{
      font-size: 1.2rem;
      color: #a0a0a0;
      font-weight: 600;
    }}
    
    .unit-badge {{
      display: inline-block;
      background: var(--badge-bg);
      color: var(--badge-text);
      padding: 6px 14px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 600;
      margin-top: 8px;
    }}
    
    /* Footer */
    .footer {{
      text-align: center;
      padding: 0 24px 28px;
      border-top: 1px solid rgba(212, 175, 55, 0.1);
      padding-top: 24px;
    }}
    
    .visit-btn {{
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
    
    .visit-btn::before {{
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
      transition: left 0.5s;
    }}
    
    .visit-btn:hover::before {{
      left: 100%;
    }}
    
    .visit-btn:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 30px rgba(212, 175, 55, 0.5);
    }}
    
    .updated-at {{
      color: #666;
      font-size: 0.75rem;
      margin-top: 16px;
      font-weight: 400;
    }}
  </style>
</head>
<body>
  <div class="preview-badge">
    <i class="fas fa-eye"></i> معاينة محلية
  </div>

  <div class="container">
    <!-- Product Card -->
    <div class="card">
      <!-- Product Visual Header -->
      <div class="product-visual">
        {f'<img src="{settings.logo.url}" alt="logo" class="product-logo">' if settings.logo else '<i class="fas fa-gem" style="font-size: 4rem; color: var(--gold); opacity: 0.8; position: relative; z-index: 1;"></i>'}
        <span class="category-badge">{product['category']}</span>
      </div>
      
      <!-- Product Content -->
      <div class="content">
        <span class="product-code"><i class="fas fa-barcode"></i> {product['code']}</span>
        <h1 class="product-name">{product['name']}</h1>
        
        <!-- Price Section -->
        <div class="price-section">
          <div class="price-label">السعر</div>
          <div class="price">
            <span>{formatted_price}</span>
            <span class="currency">ج.م</span>
          </div>
          <span class="unit-badge"><i class="fas fa-ruler"></i> لكل {product['unit']}</span>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="footer">
        <a href="{settings.website_url or 'https://elkhawaga.com'}" class="visit-btn">
          <i class="fas fa-globe"></i>
          <span>زيارة الموقع</span>
        </a>
        <div class="updated-at">
          <i class="far fa-clock"></i> معاينة محلية - يتم التحديث مباشرة من قاعدة البيانات
        </div>
      </div>
    </div>
  </div>
</body>
</html>'''
    
    return html
