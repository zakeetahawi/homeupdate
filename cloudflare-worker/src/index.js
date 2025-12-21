/**
 * Cloudflare Worker for QR Code Product Scanner
 * Provides fast, always-available product information
 */

// API Key for sync operations (will be set via wrangler secret)
const SYNC_API_KEY_HEADER = 'X-Sync-API-Key';

/**
 * Generate beautiful product page HTML
 */
function generateProductPage(product, env) {
    const currencySymbols = {
        'EGP': 'ج.م',
        'SAR': 'ر.س',
        'USD': '$',
        'EUR': '€'
    };

    const currencySymbol = currencySymbols[product.currency] || product.currency;
    // Format price in English numbers
    const formattedPrice = new Intl.NumberFormat('en-US').format(product.price);

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
      --gold: #d4af37;
      --gold-light: #f4d03f;
      --gold-dark: #b8860b;
      --dark: #1a1a2e;
      --dark-light: #16213e;
      --dark-surface: #0f3460;
    }
    
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: 'Cairo', sans-serif;
      background: linear-gradient(135deg, var(--dark) 0%, var(--dark-light) 50%, var(--dark-surface) 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      position: relative;
      overflow-x: hidden;
    }
    
    body::before {
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
    }
    
    .container {
      max-width: 450px;
      width: 100%;
      position: relative;
      z-index: 1;
    }
    
    /* Brand Header with Logo */
    .brand-header {
      text-align: center;
      margin-bottom: 24px;
      animation: fadeInDown 0.6s ease-out;
    }
    
    .logo-container {
      margin-bottom: 12px;
    }
    
    .logo-icon {
      font-size: 3.5rem;
      background: linear-gradient(135deg, var(--gold-dark), var(--gold), var(--gold-light));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      filter: drop-shadow(0 0 20px rgba(212, 175, 55, 0.4));
    }
    
    .brand-name {
      font-size: 2rem;
      font-weight: 800;
      background: linear-gradient(135deg, var(--gold-dark), var(--gold), var(--gold-light));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: 2px;
      margin-top: 8px;
    }
    
    .brand-tagline {
      color: #a0a0a0;
      font-size: 0.85rem;
      margin-top: 4px;
      font-weight: 400;
    }
    
    /* Product Card */
    .card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(212, 175, 55, 0.2);
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
      animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInDown {
      from { opacity: 0; transform: translateY(-20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    /* Product Visual Header */
    .product-visual {
      height: 180px;
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
    }
    
    @keyframes rotate {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    .product-icon {
      font-size: 4rem;
      color: var(--gold);
      opacity: 0.8;
      position: relative;
      z-index: 1;
    }
    
    .category-badge {
      position: absolute;
      top: 16px;
      right: 16px;
      background: linear-gradient(135deg, var(--gold-dark), var(--gold));
      color: var(--dark);
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 600;
      z-index: 2;
      box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4);
    }
    
    /* Content */
    .content {
      padding: 28px 24px;
    }
    
    .product-code {
      display: inline-block;
      background: rgba(212, 175, 55, 0.15);
      color: var(--gold);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 12px;
      font-family: 'Courier New', monospace;
      letter-spacing: 1px;
      border: 1px solid rgba(212, 175, 55, 0.3);
    }
    
    .product-name {
      font-size: 1.6rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 20px;
      line-height: 1.4;
    }
    
    /* Price Section */
    .price-section {
      background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(212, 175, 55, 0.05) 100%);
      border: 1px solid rgba(212, 175, 55, 0.3);
      border-radius: 16px;
      padding: 24px;
      text-align: center;
      margin-bottom: 24px;
      position: relative;
      overflow: hidden;
    }
    
    .price-section::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--gold), transparent);
    }
    
    .price-label {
      color: #a0a0a0;
      font-size: 0.85rem;
      margin-bottom: 8px;
      font-weight: 500;
    }
    
    .price {
      font-size: 2.8rem;
      font-weight: 800;
      background: linear-gradient(135deg, var(--gold-dark), var(--gold), var(--gold-light));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      display: flex;
      align-items: baseline;
      justify-content: center;
      gap: 8px;
      margin-bottom: 8px;
      font-family: 'Courier New', monospace;
    }
    
    .currency {
      font-size: 1.2rem;
      color: #a0a0a0;
      font-weight: 600;
    }
    
    .unit-badge {
      display: inline-block;
      background: linear-gradient(135deg, var(--gold-dark), var(--gold));
      color: var(--dark);
      padding: 6px 14px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 600;
      margin-top: 8px;
    }
    
    /* Info Grid */
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 24px;
    }
    
    .info-item {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(212, 175, 55, 0.15);
      padding: 16px;
      border-radius: 12px;
      text-align: center;
    }
    
    .info-label {
      color: #a0a0a0;
      font-size: 0.75rem;
      margin-bottom: 6px;
      font-weight: 500;
    }
    
    .info-value {
      color: #ffffff;
      font-weight: 700;
      font-size: 0.95rem;
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
      background: linear-gradient(135deg, var(--gold-dark), var(--gold), var(--gold-light));
      color: var(--dark);
      padding: 16px 32px;
      border-radius: 14px;
      text-decoration: none;
      font-weight: 700;
      font-size: 1rem;
      transition: all 0.3s ease;
      box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3);
      position: relative;
      overflow: hidden;
    }
    
    .visit-btn::before {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
      transition: left 0.5s;
    }
    
    .visit-btn:hover::before {
      left: 100%;
    }
    
    .visit-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 30px rgba(212, 175, 55, 0.5);
    }
    
    .updated-at {
      color: #666;
      font-size: 0.75rem;
      margin-top: 16px;
      font-weight: 400;
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Brand Header with Logo -->
    <div class="brand-header">
      <div class="logo-container">
        <i class="fas fa-gem logo-icon"></i>
      </div>
      <div class="brand-name">${env.SITE_NAME}</div>
      <div class="brand-tagline">الجودة والتميز في كل تفصيل</div>
    </div>
    
    <!-- Product Card -->
    <div class="card">
      <!-- Product Visual Header -->
      <div class="product-visual">
        <i class="fas fa-box-open product-icon"></i>
        ${product.category ? `<span class="category-badge">${product.category}</span>` : ''}
      </div>
      
      <!-- Product Content -->
      <div class="content">
        <span class="product-code"><i class="fas fa-barcode"></i> ${product.code}</span>
        <h1 class="product-name">${product.name}</h1>
        
        <!-- Price Section -->
        <div class="price-section">
          <div class="price-label">السعر</div>
          <div class="price">
            <span>${formattedPrice}</span>
            <span class="currency">${currencySymbol}</span>
          </div>
          ${product.unit ? `<span class="unit-badge"><i class="fas fa-ruler"></i> لكل ${product.unit}</span>` : ''}
        </div>
        
        <!-- Info Grid -->
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label"><i class="fas fa-money-bill-wave"></i> العملة</div>
            <div class="info-value">${product.currency}</div>
          </div>
          <div class="info-item">
            <div class="info-label"><i class="fas fa-cube"></i> الوحدة</div>
            <div class="info-value">${product.unit || 'قطعة'}</div>
          </div>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="footer">
        <a href="https://elkhawaga.com" class="visit-btn">
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
function generate404Page(code, env) {
    return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>المنتج غير موجود - ${env.SITE_NAME}</title>
  <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Tajawal', sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      color: white;
      text-align: center;
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
    <p style="margin-top: 30px;"><a href="${env.MAIN_SITE_URL}">العودة للموقع الرئيسي</a></p>
  </div>
</body>
</html>`;
}

/**
 * Handle sync request from Django
 */
async function handleSync(request, env) {
    // Verify API key
    const apiKey = request.headers.get(SYNC_API_KEY_HEADER);
    const storedKey = await env.PRODUCTS_KV.get('__SYNC_API_KEY__');

    if (!apiKey || apiKey !== storedKey) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' }
        });
    }

    try {
        const data = await request.json();

        if (data.action === 'sync_product') {
            // Sync single product
            const product = data.product;
            await env.PRODUCTS_KV.put(product.code, JSON.stringify(product));
            return new Response(JSON.stringify({ success: true, code: product.code }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }

        if (data.action === 'sync_all') {
            // Sync all products (bulk)
            const products = data.products;
            const promises = products.map(p => env.PRODUCTS_KV.put(p.code, JSON.stringify(p)));
            await Promise.all(promises);
            return new Response(JSON.stringify({ success: true, count: products.length }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }

        if (data.action === 'delete_product') {
            // Delete product
            await env.PRODUCTS_KV.delete(data.code);
            return new Response(JSON.stringify({ success: true, deleted: data.code }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }

        return new Response(JSON.stringify({ error: 'Unknown action' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
        });

    } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

/**
 * Handle API requests (get product info as JSON)
 */
async function handleAPI(code, env) {
    const product = await env.PRODUCTS_KV.get(code, 'json');

    if (!product) {
        return new Response(JSON.stringify({ error: 'Product not found', code }), {
            status: 404,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        });
    }

    return new Response(JSON.stringify(product), {
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    });
}

/**
 * Main fetch handler
 */
export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);
        const path = url.pathname;

        // Handle CORS preflight
        if (request.method === 'OPTIONS') {
            return new Response(null, {
                headers: {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, X-Sync-API-Key'
                }
            });
        }

        // Sync endpoint (POST only)
        if (path === '/sync' && request.method === 'POST') {
            return handleSync(request, env);
        }

        // Health check
        if (path === '/health' || path === '/') {
            const productCount = await env.PRODUCTS_KV.list();
            return new Response(JSON.stringify({
                status: 'ok',
                service: 'elkhawaga-qr',
                products_cached: productCount.keys.length,
                timestamp: new Date().toISOString()
            }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }

        // API endpoint (returns JSON)
        if (path.startsWith('/api/')) {
            const code = path.replace('/api/', '').replace('/', '');
            return handleAPI(code, env);
        }

        // Product page (returns HTML)
        // Support both /p/<code> and /<code> formats
        let code = null;
        
        if (path.startsWith('/p/')) {
            code = path.split('/')[2];
        } else if (path.length > 1 && !path.includes('/api/') && !path.includes('/sync') && !path.includes('/health')) {
            // Direct code format: /<code>
            code = path.substring(1).replace('/', '');
        }
        
        if (code) {
            const product = await env.PRODUCTS_KV.get(code, 'json');

            if (!product) {
                return new Response(generate404Page(code, env), {
                    status: 404,
                    headers: { 'Content-Type': 'text/html; charset=utf-8' }
                });
            }

            return new Response(generateProductPage(product, env), {
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
        }

        // Default: redirect to main site
        return Response.redirect(env.MAIN_SITE_URL, 302);
    }
};
