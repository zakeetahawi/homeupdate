/**
 * Cloudflare Worker - PRODUCTION
 * نسخة الإنتاج النهائية مع السعر قبل الخصم (بدون معلومات اختبار)
 */

const SYNC_API_KEY_HEADER = 'X-Sync-API-Key';

/**
 * حساب السعر قبل الخصم
 */
function calculatePriceBeforeDiscount(currentPrice) {
  if (currentPrice <= 400) {
    return currentPrice * 1.35; // +35%
  } else if (currentPrice <= 600) {
    return currentPrice * 1.30; // +30%
  } else if (currentPrice <= 800) {
    return currentPrice * 1.25; // +25%
  } else {
    return currentPrice * 1.20; // +20%
  }
}

/**
 * صفحة المنتج مع السعر قبل الخصم
 */
async function generateProductPage(product, env) {
  let design = await env.PRODUCTS_KV.get('__QR_DESIGN_SETTINGS__', 'json');

  if (!design) {
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Configuration Required</title></head>
<body style="font-family:Arial;padding:40px;text-align:center;">
<h1>⚠️ التصميم غير متزامن</h1>
<p>يرجى مزامنة إعدادات التصميم من لوحة التحكم أولاً</p>
</body></html>`;
  }

  const currencySymbols = { 'EGP': 'ج.م', 'SAR': 'ر.س', 'USD': '$', 'EUR': '€' };
  const currencySymbol = currencySymbols[product.currency] || product.currency;
  
  const currentPrice = parseFloat(product.price);
  const formattedPrice = new Intl.NumberFormat('en-US').format(currentPrice);
  
  // حساب السعر قبل الخصم
  const priceBeforeDiscount = calculatePriceBeforeDiscount(currentPrice);
  const formattedPriceBeforeDiscount = new Intl.NumberFormat('en-US').format(Math.round(priceBeforeDiscount));

  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${product.name} - ${env.SITE_NAME}</title>
  <meta name="description" content="${product.name} - السعر: ${formattedPrice} ${currencySymbol}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    :root {
      --gold: ${design.colors?.primary};
      --gold-light: ${design.colors?.secondary};
      --dark: ${design.colors?.background};
      --dark-light: ${design.colors?.surface};
      --card-bg: ${design.colors?.card};
      --button-bg: ${design.colors?.button};
      --button-text: ${design.colors?.button_text};
      --badge-bg: ${design.colors?.badge};
      --badge-text: ${design.colors?.badge_text};
      --price-color: ${design.colors?.price};
      --product-name-color: ${design.colors?.product_name || '#d4af37'};
      --label-color: ${design.colors?.label || '#888'};
    }
    
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: 'Cairo', sans-serif;
      background: linear-gradient(135deg, var(--dark) 0%, var(--dark-light) 50%, var(--dark-light) 100%);
      ${design.background_image_url ? `background-image: url("${design.background_image_url}");background-size: cover;background-position: center;background-blend-mode: overlay;` : ''}
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      position: relative;
      overflow-x: hidden;
      color: white;
    }
    
    body::before {
      content: '';
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background-image:
        radial-gradient(circle at 20% 80%, rgba(212, 175, 55, 0.1) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(212, 175, 55, 0.08) 0%, transparent 50%);
      pointer-events: none;
      z-index: 0;
    }
    
    .container {
      max-width: 450px;
      width: 100%;
      position: relative;
      z-index: 1;
    }
    
    .card {
      background: var(--card-bg);
      opacity: 0.98;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(212, 175, 55, 0.2);
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
      animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .product-visual {
      height: 160px;
      background: linear-gradient(135deg, var(--dark-light) 0%, var(--dark) 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      border-bottom: 1px solid rgba(212, 175, 55, 0.15);
      position: relative;
    }
    
    .product-logo {
      max-width: 120px;
      max-height: 80px;
      filter: drop-shadow(0 4px 12px rgba(212, 175, 55, 0.3));
    }
    
    .content {
      padding: 24px;
    }
        .product-code {
      display: inline-block;
      background: linear-gradient(135deg, #8B4513, #654321);
      color: white;
      padding: 6px 14px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 600;
      margin-bottom: 16px;
      letter-spacing: 0.5px;
    }
    
    .product-code i {
      margin-left: 6px;
    }
        .product-code {
      display: inline-block;
      background: var(--badge-bg);
      color: var(--badge-text);
      padding: 6px 14px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 600;
      margin-bottom: 16px;
      letter-spacing: 0.5px;
    }
    
    .product-code i {
      margin-left: 6px;
    }
    
    .product-name {
      font-size: 1.6rem;
      font-weight: 800;
      color: var(--product-name-color);
      margin-bottom: 20px;
      line-height: 1.4;
    }
    
    /* Price Section with Discount */
    .price-section {
      background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(212, 175, 55, 0.05) 100%);
      border: 1px solid rgba(212, 175, 55, 0.3);
      border-radius: 16px;
      padding: 20px;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      justify-content: space-around;
      gap: 15px;
    }
    
    .price-item {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
    
    .price-divider {
      width: 1px;
      height: 70px;
      background: linear-gradient(to bottom, transparent, rgba(212, 175, 55, 0.6), transparent);
      align-self: center;
    }
    
    .price-label {
      font-size: 0.75rem;
      color: var(--label-color);
      opacity: 0.8;
    }
    
    .price-value {
      font-size: 1.8rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    
    .price-before-discount .price-value {
      color: #dc3545;
      position: relative;
    }
    
    .price-before-discount .price-value::before,
    .price-before-discount .price-value::after {
      content: '';
      position: absolute;
      left: -5%;
      right: -5%;
      top: 48%;
      height: 1px;
      background: #dc3545;
    }
    
    .price-before-discount .price-value::before {
      transform: rotate(-12deg);
    }
    
    .price-before-discount .price-value::after {
      transform: rotate(12deg);
    }
    
    .price-current .price-value {
      color: var(--price-color);
    }
    
    .currency {
      font-size: 0.9rem;
      color: var(--gold);
      font-weight: 600;
    }

    .footer {
      text-align: center;
      padding: 0 24px 28px;
      border-top: 1px solid rgba(212, 175, 55, 0.1);
      padding-top: 24px;
    }
    
    .visit-btn {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: var(--button-bg);
      color: var(--button-text);
      padding: 14px 30px;
      border-radius: 14px;
      text-decoration: none;
      font-weight: 700;
      font-size: 1rem;
      transition: all 0.3s ease;
      box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3);
    }
    
    .visit-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 30px rgba(212, 175, 55, 0.5);
    }
    
    .branches-btn {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: var(--button-bg);
      color: var(--button-text);
      padding: 14px 30px;
      border-radius: 14px;
      text-decoration: none;
      font-weight: 700;
      font-size: 1rem;
      transition: all 0.3s ease;
      box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3);
      margin-top: 12px;
    }
    
    .branches-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 30px rgba(212, 175, 55, 0.5);
    }
    
    .hotline {
      margin-top: 12px;
      padding: 10px;
      background: var(--badge-bg);
      border-radius: 8px;
      text-align: center;
      font-size: 0.85rem;
      color: var(--badge-text);
    }
    
    .hotline a {
      color: var(--badge-text);
      text-decoration: none;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    
    .hotline a:hover {
      opacity: 0.8;
    }
    
    .updated-at {
      margin-top: 16px;
      color: var(--label-color);
      font-size: 0.8rem;
    }
    
    .updated-at i {
      margin-left: 5px;
    }
    
    .social-links {
      display: flex;
      justify-content: center;
      gap: 12px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid rgba(212, 175, 55, 0.1);
    }
    
    .social-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(212, 175, 55, 0.05));
      border: 1px solid rgba(212, 175, 55, 0.3);
      color: var(--gold);
      transition: all 0.3s ease;
      text-decoration: none;
      font-size: 1.1rem;
    }
    
    .social-icon:hover {
      background: var(--gold);
      color: var(--dark);
      transform: translateY(-3px);
      box-shadow: 0 5px 15px rgba(212, 175, 55, 0.4);
    }
    
    @media (max-width: 480px) {
      .product-name { font-size: 1.3rem; }
      .price { font-size: 2rem; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="product-visual">
        ${design.logo_url ? `<img src="${design.logo_url}" alt="logo" class="product-logo">` : '<i class="fas fa-gem" style="font-size: 4rem; color: var(--gold); opacity: 0.8;"></i>'}
      </div>
      
      <div class="content">
        
        <span class="product-code">${product.name}</span>
        
        <div class="price-section">
          <div class="price-item price-before-discount">
            <div class="price-label">السعر قبل الخصم</div>
            <div class="price-value">
              <span>${formattedPriceBeforeDiscount}</span>
              <span class="currency">${currencySymbol}</span>
            </div>
          </div>
          
          <div class="price-divider"></div>
          
          <div class="price-item price-current">
            <div class="price-label">السعر بعد الخصم</div>
            <div class="price-value">
              <span>${formattedPrice}</span>
              <span class="currency">${currencySymbol}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="footer">
        <a href="${design.links?.website || env.MAIN_SITE_URL}" class="visit-btn">
          <i class="fas fa-external-link-alt"></i>
          <span>زيارة الموقع</span>
        </a>
        <a href="https://elkhawaga.com/branches/" class="branches-btn" target="_blank">
          <i class="fas fa-map-marker-alt"></i>
          <span>فروعنا</span>
        </a>
        <div class="hotline">
          <i class="fas fa-headset"></i> للتواصل: 
          <a href="tel:19148" dir="ltr">19148</a>
        </div>
        <div class="social-links">
          <a href="https://web.facebook.com/elkhawagafabrics" target="_blank" class="social-icon" title="Facebook">
            <i class="fab fa-facebook-f"></i>
          </a>
          <a href="https://www.instagram.com/elkhawagafabrics/" target="_blank" class="social-icon" title="Instagram">
            <i class="fab fa-instagram"></i>
          </a>
          <a href="https://www.tiktok.com/@elkhawagafabrics" target="_blank" class="social-icon" title="TikTok">
            <i class="fab fa-tiktok"></i>
          </a>
          <a href="https://www.linkedin.com/company/elkhawagafabrics/" target="_blank" class="social-icon" title="LinkedIn">
            <i class="fab fa-linkedin-in"></i>
          </a>
          <a href="https://youtube.com/@elkhwagafabrics" target="_blank" class="social-icon" title="YouTube">
            <i class="fab fa-youtube"></i>
          </a>
        </div>
      </div>
    </div>
  </div>
</body>
</html>`;
}

/**
 * صفحة 404
 */
async function generate404Page(code, env, design = null) {
  if (!design) {
    design = await env.PRODUCTS_KV.get('__QR_DESIGN_SETTINGS__', 'json');
  }

  const websiteUrl = design?.links?.website || env.MAIN_SITE_URL || 'https://elkhawaga.com';

  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>المنتج غير موجود - 404</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Cairo', sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      color: white;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      direction: rtl;
    }
    .container { max-width: 400px; text-align: center; }
    h1 { font-size: 120px; opacity: 0.3; }
    h2 { font-size: 24px; margin: 20px 0; }
    p { opacity: 0.7; margin-bottom: 30px; }
    .code { background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 8px; font-family: monospace; }
    a { color: #e94560; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <h1>404</h1>
    <h2>المنتج غير موجود</h2>
    <p>لم نتمكن من العثور على منتج بالكود:</p>
    <div class="code">${code}</div>
    <p style="margin-top: 30px;"><a href="${websiteUrl}">العودة للموقع الرئيسي</a></p>
  </div>
</body>
</html>`;
}

/**
 * معالج المزامنة
 */
async function handleSync(request, env) {
  const authHeader = request.headers.get(SYNC_API_KEY_HEADER);
  const expectedKey = env.SYNC_API_KEY || 'default-secret-key';

  if (authHeader !== expectedKey) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const body = await request.json();
  const { action, data } = body;

  if (action === 'sync_product') {
    await env.PRODUCTS_KV.put(data.code, JSON.stringify(data.product), {
      metadata: { last_sync: new Date().toISOString() }
    });
    return new Response(JSON.stringify({ success: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (action === 'sync_all') {
    const products = data.products;
    const results = [];
    for (const prod of products) {
      await env.PRODUCTS_KV.put(prod.code, JSON.stringify(prod), {
        metadata: { last_sync: new Date().toISOString() }
      });
      results.push(prod.code);
    }
    return new Response(JSON.stringify({ success: true, synced: results }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (action === 'delete_product') {
    await env.PRODUCTS_KV.delete(data.code);
    return new Response(JSON.stringify({ success: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (action === 'sync_qr_design') {
    await env.PRODUCTS_KV.put('__QR_DESIGN_SETTINGS__', JSON.stringify(data.design));
    return new Response(JSON.stringify({ success: true }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  return new Response(JSON.stringify({ error: 'Unknown action' }), {
    status: 400,
    headers: { 'Content-Type': 'application/json' }
  });
}

/**
 * Worker Main Handler
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.slice(1);

    if (request.method === 'POST' && path === 'sync') {
      return handleSync(request, env);
    }

    if (!path || path === '' || path === 'health') {
      return new Response('Worker Active', { status: 200 });
    }

    const productCode = path.toUpperCase();
    const productData = await env.PRODUCTS_KV.get(productCode);

    if (!productData) {
      const html = await generate404Page(productCode, env);
      return new Response(html, {
        status: 404,
        headers: { 'Content-Type': 'text/html;charset=UTF-8' }
      });
    }

    const product = JSON.parse(productData);
    const html = await generateProductPage(product, env);

    return new Response(html, {
      headers: { 'Content-Type': 'text/html;charset=UTF-8' }
    });
  }
};
