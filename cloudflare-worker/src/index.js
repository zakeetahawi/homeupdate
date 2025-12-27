/**
 * Cloudflare Worker for QR Code Product Scanner
 * Provides fast, always-available product information
 */

// API Key for sync operations (will be set via wrangler secret)
const SYNC_API_KEY_HEADER = 'X-Sync-API-Key';

/**
 * Generate beautiful product page HTML
 */
async function generateProductPage(product, env) {
  // Load design settings from KV (REQUIRED - no fallback)
  let design = await env.PRODUCTS_KV.get('__QR_DESIGN_SETTINGS__', 'json');

  // If design not found, return error (admin must sync design first)
  if (!design) {
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Configuration Required</title></head>
<body style="font-family:Arial;padding:40px;text-align:center;">
<h1>⚠️ التصميم غير متزامن</h1>
<p>يرجى مزامنة إعدادات التصميم من لوحة التحكم أولاً</p>
</body></html>`;
  }

  const currencySymbols = {
    'EGP': 'ج.م',
    'SAR': 'ر.س',
    'USD': '$',
    'EUR': '€'
  };

  const currencySymbol = currencySymbols[product.currency] || product.currency;
  // Format price in English numbers
  const formattedPrice = new Intl.NumberFormat('en-US').format(product.price);

  // Variants Section - Disabled
  let variantsHtml = '';

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
      --gold-dark: ${design.colors?.primary};
      --dark: ${design.colors?.background};
      --dark-light: ${design.colors?.surface};
      --dark-surface: ${design.colors?.surface};
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
      background: linear-gradient(135deg, var(--dark) 0%, var(--dark-light) 50%, var(--dark-surface) 100%);
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
    
    /* Product Card */
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
    
    /* Product Visual Header */
    .product-visual {
      height: 160px;
      background: linear-gradient(135deg, var(--dark-surface) 0%, var(--dark-light) 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
    }
    
    .product-visual::before {
      content: '';
      position: absolute;
      top: -50%; left: -50%; width: 200%; height: 200%;
      background: conic-gradient(from 0deg, transparent 0deg 90deg, rgba(212, 175, 55, 0.1) 90deg 180deg, transparent 180deg 270deg, rgba(212, 175, 55, 0.05) 270deg 360deg);
      animation: rotate 20s linear infinite;
    }
    
    @keyframes rotate {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    .product-logo {
      max-width: ${design.logo_size || 200}px;
      max-height: ${Math.floor((design.logo_size || 200) * 0.7)}px;
      object-fit: contain;
      position: relative;
      z-index: 1;
      filter: drop-shadow(0 4px 20px rgba(0, 0, 0, 0.3));
    }
    
    /* Content */
    .content {
      padding: 24px;
    }
    
    .product-code {
      display: inline-block;
      background: var(--badge-bg);
      color: var(--badge-text);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 12px;
      font-family: 'Courier New', monospace;
      border: 1px solid rgba(212, 175, 55, 0.3);
    }
    
    .product-name {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--product-name-color);
      margin-bottom: 20px;
      line-height: 1.4;
    }
    
    /* Price Section */
    .price-section {
      background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(212, 175, 55, 0.05) 100%);
      border: 1px solid rgba(212, 175, 55, 0.3);
      border-radius: 16px;
      padding: 20px;
      text-align: center;
      margin-bottom: 24px;
    }
    
    .price {
      font-size: 2.5rem;
      font-weight: 800;
      color: var(--price-color);
      display: flex;
      align-items: baseline;
      justify-content: center;
      gap: 6px;
    }
    
    .currency {
      font-size: 1.1rem;
      color: var(--gold);
      font-weight: 600;
    }


    /* Footer */
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
    
    .updated-at {
      color: #888;
      font-size: 0.75rem;
      margin-top: 16px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <!-- Header -->
      <div class="product-visual">
        ${design.logo_url ? `<img src="${design.logo_url}" alt="logo" class="product-logo">` : '<i class="fas fa-gem" style="font-size: 4rem; color: var(--gold); opacity: 0.8;"></i>'}
      </div>
      
      <!-- Content -->
      <div class="content">
        <span class="product-code"><i class="fas fa-barcode"></i> ${product.code}</span>
        <h1 class="product-name">${product.name}</h1>
        
        <!-- Base Price -->
        <div class="price-section">
          <div style="font-size:0.8rem;color:var(--label-color);margin-bottom:5px;">سعر المنتج الأساسي</div>
          <div class="price">
            <span>${formattedPrice}</span>
            <span class="currency">${currencySymbol}</span>
          </div>
        </div>
        
        <!-- Info Grid -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;">
           <div style="background:rgba(255,255,255,0.05);padding:10px;border-radius:8px;text-align:center;">
             <div style="color:var(--label-color);font-size:0.8rem;">النوع</div>
             <div style="font-weight:bold;color:var(--label-color);">${product.category || 'عام'}</div>
           </div>
           <div style="background:rgba(255,255,255,0.05);padding:10px;border-radius:8px;text-align:center;">
             <div style="color:var(--label-color);font-size:0.8rem;">الوحدة</div>
             <div style="font-weight:bold;color:var(--label-color);">${product.unit || 'قطعة'}</div>
           </div>
        </div>

      </div>
      
      <!-- Footer -->
      <div class="footer">
        <a href="${design.links?.website || 'https://elkhawaga.com'}" class="visit-btn">
          <i class="fas fa-globe"></i>
          <span>زيارة الموقع</span>
        </a>
        <div class="updated-at">
          <i class="far fa-clock"></i> آخر تحديث: ${product.updated_at || 'غير محدد'}
        </div>
      </div>
    </div>
  </div>
</body>
</html>`;
}

/**
 * Generate 404 page
 */
async function generate404Page(code, env, design = null) {
  // If design not passed, try to load it
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
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
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
    .container { max-width: 400px; }
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

async function handleSync(request, env) {
  // Basic sync handler implementation 
  // (Shortened version of previous full logic to focus on render)
  const apiKey = request.headers.get(SYNC_API_KEY_HEADER);
  const storedKey = await env.PRODUCTS_KV.get('__SYNC_API_KEY__');

  if (!apiKey || apiKey !== storedKey) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
  }

  try {
    const data = await request.json();

    if (data.action === 'sync_product') {
      await env.PRODUCTS_KV.put(data.product.code, JSON.stringify(data.product));
      return new Response(JSON.stringify({ success: true }));
    }

    if (data.action === 'sync_all') {
      const promises = data.products.map(p => env.PRODUCTS_KV.put(p.code, JSON.stringify(p)));
      await Promise.all(promises);
      return new Response(JSON.stringify({ success: true, count: data.products.length }));
    }

    if (data.action === 'delete_product') {
      await env.PRODUCTS_KV.delete(data.code);
      return new Response(JSON.stringify({ success: true }));
    }

    if (data.action === 'sync_qr_design') {
      await env.PRODUCTS_KV.put('__QR_DESIGN_SETTINGS__', JSON.stringify(data.design));
      return new Response(JSON.stringify({ success: true }));
    }

    return new Response(JSON.stringify({ error: 'Unknown action' }), { status: 400 });

  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), { status: 500 });
  }
}

async function handleAPI(code, env) {
  const product = await env.PRODUCTS_KV.get(code, 'json');
  if (!product) return new Response(JSON.stringify({ error: 'Not found' }), { status: 404 });
  return new Response(JSON.stringify(product), { headers: { 'Content-Type': 'application/json' } });
}

// ... Bank handlers omitted for brevity/focus, handled by separate logic or previous full impl ...

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Sync Endpoint
    if (path === '/sync' && request.method === 'POST') {
      return handleSync(request, env);
    }

    // Get Product Code (e.g. /CODE)
    const code = decodeURIComponent(path.substring(1));

    if (!code) {
      return new Response("QR Worker Active", { status: 200 });
    }

    // Fetch Data
    const product = await env.PRODUCTS_KV.get(code, 'json');

    if (!product) {
      return new Response(await generate404Page(code, env), {
        status: 404,
        headers: { 'Content-Type': 'text/html; charset=utf-8' }
      });
    }

    // Render Page
    const html = await generateProductPage(product, env);
    return new Response(html, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
};
