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
    const formattedPrice = new Intl.NumberFormat('ar-EG').format(product.price);

    return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${product.name} - ${env.SITE_NAME}</title>
  <meta name="description" content="${product.name} - السعر: ${formattedPrice} ${currencySymbol}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: 'Tajawal', sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    
    .card {
      background: rgba(255, 255, 255, 0.95);
      border-radius: 24px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
      max-width: 420px;
      width: 100%;
      overflow: hidden;
      animation: slideUp 0.6s ease-out;
    }
    
    @keyframes slideUp {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .header {
      background: linear-gradient(135deg, #e94560 0%, #c73659 100%);
      color: white;
      padding: 24px;
      text-align: center;
    }
    
    .logo {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    
    .category-badge {
      display: inline-block;
      background: rgba(255, 255, 255, 0.2);
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 14px;
    }
    
    .content {
      padding: 32px 24px;
    }
    
    .product-name {
      font-size: 24px;
      font-weight: 700;
      color: #1a1a2e;
      margin-bottom: 8px;
      line-height: 1.4;
    }
    
    .product-code {
      color: #666;
      font-size: 14px;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .product-code::before {
      content: '📦';
    }
    
    .price-section {
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      border-radius: 16px;
      padding: 24px;
      text-align: center;
      margin-bottom: 24px;
    }
    
    .price-label {
      color: #666;
      font-size: 14px;
      margin-bottom: 8px;
    }
    
    .price {
      font-size: 42px;
      font-weight: 700;
      color: #e94560;
      display: flex;
      align-items: baseline;
      justify-content: center;
      gap: 8px;
    }
    
    .currency {
      font-size: 20px;
      color: #666;
    }
    
    .unit-badge {
      display: inline-block;
      background: #e94560;
      color: white;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      margin-top: 12px;
    }
    
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 24px;
    }
    
    .info-item {
      background: #f8f9fa;
      padding: 16px;
      border-radius: 12px;
      text-align: center;
    }
    
    .info-label {
      color: #666;
      font-size: 12px;
      margin-bottom: 4px;
    }
    
    .info-value {
      color: #1a1a2e;
      font-weight: 600;
      font-size: 14px;
    }
    
    .footer {
      text-align: center;
      padding: 16px 24px 24px;
      border-top: 1px solid #eee;
    }
    
    .visit-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: white;
      padding: 14px 28px;
      border-radius: 12px;
      text-decoration: none;
      font-weight: 600;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .visit-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }
    
    .updated-at {
      color: #999;
      font-size: 11px;
      margin-top: 16px;
    }
    
    .offline-badge {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0, 0, 0, 0.8);
      color: #4ade80;
      padding: 8px 16px;
      border-radius: 20px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    
    .offline-badge::before {
      content: '⚡';
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="logo">${env.SITE_NAME}</div>
      ${product.category ? `<span class="category-badge">${product.category}</span>` : ''}
    </div>
    
    <div class="content">
      <h1 class="product-name">${product.name}</h1>
      <div class="product-code">كود المنتج: ${product.code}</div>
      
      <div class="price-section">
        <div class="price-label">السعر</div>
        <div class="price">
          <span>${formattedPrice}</span>
          <span class="currency">${currencySymbol}</span>
        </div>
        ${product.unit ? `<span class="unit-badge">لكل ${product.unit}</span>` : ''}
      </div>
      
      <div class="info-grid">
        <div class="info-item">
          <div class="info-label">العملة</div>
          <div class="info-value">${product.currency}</div>
        </div>
        <div class="info-item">
          <div class="info-label">الوحدة</div>
          <div class="info-value">${product.unit || 'قطعة'}</div>
        </div>
      </div>
    </div>
    
    <div class="footer">
      <a href="${env.MAIN_SITE_URL}" class="visit-btn">
        <span>🌐</span>
        <span>زيارة الموقع</span>
      </a>
      <div class="updated-at">آخر تحديث: ${product.updated_at || 'غير محدد'}</div>
    </div>
  </div>
  
  <div class="offline-badge">يعمل بدون اتصال بالخادم</div>
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
        if (path.startsWith('/p/')) {
            const code = path.split('/')[2];
            if (!code) {
                return new Response(generate404Page('', env), {
                    status: 404,
                    headers: { 'Content-Type': 'text/html; charset=utf-8' }
                });
            }

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
