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
<p style="color:#666;font-size:14px;">Design settings not synced. Please sync from admin panel.</p>
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
    
    /* Product Card */
    .card {
      background: var(--card-bg);
      opacity: 0.95;
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
    
    .product-logo {
      max-width: ${design.logo_size || 200}px;
      max-height: ${Math.floor((design.logo_size || 200) * 0.7)}px;
      object-fit: contain;
      position: relative;
      z-index: 1;
      filter: drop-shadow(0 4px 20px rgba(0, 0, 0, 0.3));
    }
    
    .category-badge {
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
    }
    
    /* Content */
    .content {
      padding: 28px 24px;
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
      letter-spacing: 1px;
      border: 1px solid rgba(212, 175, 55, 0.3);
    }
    
    .product-name {
      font-size: 1.6rem;
      font-weight: 700;
      color: #1a1a1a;
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
      color: var(--price-color);
      display: flex;
      align-items: baseline;
      justify-content: center;
      gap: 8px;
      margin-bottom: 8px;
      font-family: 'Courier New', monospace;
    }
    
    .currency {
      font-size: 1.2rem;
      color: #542804;
      font-weight: 600;
    }
    
    .unit-badge {
      display: inline-block;
      background: var(--badge-bg);
      color: var(--badge-text);
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
      color: #1a1a1a;
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
    <!-- Product Card -->
    <div class="card">
      <!-- Product Visual Header -->
      <div class="product-visual">
        ${design.logo_url ? `<img src="${design.logo_url}" alt="logo" class="product-logo">` : '<i class="fas fa-gem" style="font-size: 4rem; color: var(--gold); opacity: 0.8; position: relative; z-index: 1;"></i>'}
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

        if (data.action === 'sync_all_bank') {
            // Sync all bank accounts
            const bankAccounts = data.bank_accounts || {};
            const promises = [];
            for (const [key, value] of Object.entries(bankAccounts)) {
                promises.push(env.PRODUCTS_KV.put(key, JSON.stringify(value)));
            }
            await Promise.all(promises);
            return new Response(JSON.stringify({ success: true, count: Object.keys(bankAccounts).length }), {
                headers: { 'Content-Type': 'application/json' }
            });
        }

        if (data.action === 'sync_qr_design') {
            // Sync QR design settings
            if (data.design) {
                await env.PRODUCTS_KV.put('__QR_DESIGN_SETTINGS__', JSON.stringify(data.design));
                return new Response(JSON.stringify({ success: true, message: 'QR design settings synced' }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            return new Response(JSON.stringify({ error: 'No design data provided' }), {
                status: 400,
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
 * Handle Bank Account requests
 */
async function handleBankAccount(code, env) {
    try {
        // Load design settings for use in bank pages
        let design = await env.PRODUCTS_KV.get('__QR_DESIGN_SETTINGS__', 'json');
        if (!design) {
            design = {
                colors: {
                    primary: '#d4af37',
                    secondary: '#f4d03f',
                    background: '#1a1a2e',
                    surface: '#0f3460',
                    text: '#ffffff'
                },
                logo_url: '',
                logo_text: 'الخواجة',
                show_logo: true
            };
        }
        
        // Get bank account data from KV (try both key formats for compatibility)
        let bankData = await env.PRODUCTS_KV.get(`bank_accounts:${code}`, 'json');
        if (!bankData) {
            bankData = await env.PRODUCTS_KV.get(`bank:${code}`, 'json');
        }

        if (!bankData) {
            return new Response(generateBankNotFoundPage(code, env), {
                status: 404,
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
        }

        // Check if it's "all" accounts page
        if (code === 'all' && bankData.type === 'all_accounts') {
            return new Response(generateAllBankAccountsPage(bankData, env, design), {
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
        }

        // Single bank account page
        return new Response(await generateBankAccountPage(bankData, env, design), {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });

    } catch (e) {
        return new Response(generateBankErrorPage(e.message, env), {
            status: 500,
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });
    }
}

/**
 * Generate single bank account page
 */
async function generateBankAccountPage(bank, env, design) {
    // Design is now passed as parameter (already loaded)
    // No need to fetch again or set fallback

    return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${bank.bank_name} - ${env.SITE_NAME}</title>
  <meta name="description" content="الحساب البنكي لـ ${env.SITE_NAME} - ${bank.bank_name}">
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
      --success: #28a745;
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
      max-width: 500px;
      width: 100%;
      position: relative;
      z-index: 1;
    }
    
    .card {
      background: var(--card-bg);
      opacity: 0.95;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-radius: 24px;
      padding: 32px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
      border: 1px solid rgba(212, 175, 55, 0.2);
      animation: fadeInUp 0.6s ease-out;
    }
    
    .bank-header {
      text-align: center;
      margin-bottom: 28px;
      padding-bottom: 20px;
      border-bottom: 2px solid rgba(212, 175, 55, 0.3);
    }
    
    .company-logo {
      max-width: 350px;
      max-height: 245px;
      object-fit: contain;
      margin-bottom: 20px;
      filter: drop-shadow(0 4px 20px rgba(0, 0, 0, 0.3));
    }
    
    .bank-logo {
      max-width: 120px;
      max-height: 120px;
      object-fit: contain;
      margin-bottom: 12px;
      filter: drop-shadow(0 4px 8px rgba(212, 175, 55, 0.3));
    }
    
    .bank-icon {
      font-size: 3rem;
      color: var(--gold);
      margin-bottom: 12px;
      filter: drop-shadow(0 4px 8px rgba(212, 175, 55, 0.3));
    }
    
    .info-group {
      margin-bottom: 20px;
    }
    
    .info-label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9rem;
      color: var(--gold-light);
      margin-bottom: 6px;
      font-weight: 600;
    }
    
    .info-value {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(212, 175, 55, 0.2);
      border-radius: 12px;
      padding: 14px 16px;
      color: #1a1a1a;
      font-size: 1.1rem;
      font-weight: 600;
      font-family: 'Cairo', monospace;
      direction: ltr;
      text-align: center;
      position: relative;
      transition: all 0.3s ease;
    }
    
    .info-value:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: var(--gold);
    }
    
    .copy-btn {
      position: absolute;
      top: 50%;
      left: 12px;
      transform: translateY(-50%);
      background: var(--gold);
      color: var(--dark);
      border: none;
      border-radius: 8px;
      padding: 8px 12px;
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 600;
      transition: all 0.3s ease;
      opacity: 0;
    }
    
    .info-value:hover .copy-btn {
      opacity: 1;
    }
    
    .copy-btn:hover {
      background: var(--gold-light);
      transform: translateY(-50%) scale(1.05);
    }
    
    .copy-btn:active {
      transform: translateY(-50%) scale(0.95);
    }
    
    .visit-btn {
      display: block;
      width: 100%;
      padding: 16px;
      background: var(--button-bg);
      color: var(--button-text);
      text-decoration: none;
      border-radius: 16px;
      font-weight: 700;
      font-size: 1.1rem;
      text-align: center;
      margin-top: 24px;
      transition: all 0.3s ease;
      box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4);
    }
    
    .visit-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(212, 175, 55, 0.5);
    }
    
    .toast {
      position: fixed;
      top: 20px;
      right: 20px;
      background: var(--success);
      color: white;
      padding: 16px 24px;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      display: none;
      z-index: 1000;
      animation: slideInRight 0.3s ease-out;
    }
    
    @keyframes fadeInDown {
      from { opacity: 0; transform: translateY(-20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideInRight {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="bank-header">
        ${design.logo_url ? `<img src="${design.logo_url}" alt="logo" class="company-logo">` : ''}
        ${bank.bank_logo ? `<img src="${bank.bank_logo}" alt="bank logo" class="bank-logo">` : '<div class="bank-icon"><i class="fas fa-university"></i></div>'}
      </div>

      ${bank.account_holder ? `
      <div class="info-group">
        <div class="info-label">
          <i class="fas fa-user"></i>
          <span>اسم صاحب الحساب</span>
        </div>
        <div class="info-value">
          ${bank.account_holder}
          <button class="copy-btn" onclick="copyText('${bank.account_holder}', this)">
            <i class="fas fa-copy"></i> نسخ
          </button>
        </div>
      </div>
      ` : ''}

      <div class="info-group">
        <div class="info-label">
          <i class="fas fa-hashtag"></i>
          <span>رقم الحساب</span>
        </div>
        <div class="info-value">
          ${bank.account_number}
          <button class="copy-btn" onclick="copyText('${bank.account_number}', this)">
            <i class="fas fa-copy"></i> نسخ
          </button>
        </div>
      </div>

      ${bank.iban ? `
      <div class="info-group">
        <div class="info-label">
          <i class="fas fa-barcode"></i>
          <span>IBAN</span>
        </div>
        <div class="info-value">
          ${bank.iban}
          <button class="copy-btn" onclick="copyText('${bank.iban}', this)">
            <i class="fas fa-copy"></i> نسخ
          </button>
        </div>
      </div>
      ` : ''}

      ${bank.swift_code ? `
      <div class="info-group">
        <div class="info-label">
          <i class="fas fa-code"></i>
          <span>SWIFT Code</span>
        </div>
        <div class="info-value">
          ${bank.swift_code}
          <button class="copy-btn" onclick="copyText('${bank.swift_code}', this)">
            <i class="fas fa-copy"></i> نسخ
          </button>
        </div>
      </div>
      ` : ''}

      ${bank.branch ? `
      <div class="info-group">
        <div class="info-label">
          <i class="fas fa-map-marker-alt"></i>
          <span>الفرع</span>
        </div>
        <div class="info-value">
          ${bank.branch}
        </div>
      </div>
      ` : ''}

      <a href="${env.MAIN_SITE_URL}" class="visit-btn">
        <i class="fas fa-globe"></i> زيارة الموقع
      </a>
    </div>
  </div>

  <div class="toast" id="toast">
    <i class="fas fa-check-circle"></i> تم النسخ بنجاح!
  </div>

  <script>
    function copyText(text, button) {
      navigator.clipboard.writeText(text).then(() => {
        const toast = document.getElementById('toast');
        toast.style.display = 'block';
        button.innerHTML = '<i class="fas fa-check"></i> تم';
        button.style.background = '#28a745';
        
        setTimeout(() => {
          toast.style.display = 'none';
          button.innerHTML = '<i class="fas fa-copy"></i> نسخ';
          button.style.background = '';
        }, 2000);
      });
    }
  </script>
</body>
</html>`;
}

/**
 * Generate all bank accounts page
 */
function generateAllBankAccountsPage(data, env, design) {
    const accountsHTML = data.accounts.map(bank => `
        <div class="bank-card">
          <div class="bank-card-header">
            <i class="fas fa-university"></i>
            <h3>${bank.bank_name}</h3>
            <p>${bank.bank_name_en}</p>
          </div>
          <div class="bank-card-body">
            <div class="info-row">
              <span class="label">رقم الحساب:</span>
              <span class="value">${bank.account_number}</span>
              <button onclick="copyText('${bank.account_number}', this)">
                <i class="fas fa-copy"></i>
              </button>
            </div>
            ${bank.iban ? `
            <div class="info-row">
              <span class="label">IBAN:</span>
              <span class="value">${bank.iban}</span>
              <button onclick="copyText('${bank.iban}', this)">
                <i class="fas fa-copy"></i>
              </button>
            </div>
            ` : ''}
          </div>
        </div>
    `).join('');

    return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>الحسابات البنكية - ${env.SITE_NAME}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    :root {
      --gold: ${design?.colors?.primary || '#d4af37'};
      --gold-light: ${design?.colors?.secondary || '#f4d03f'};
      --gold-dark: ${design?.colors?.primary || '#b8860b'};
      --dark: ${design?.colors?.background || '#1a1a2e'};
    }
    
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: 'Cairo', sans-serif;
      background: linear-gradient(135deg, var(--dark) 0%, #16213e 50%, #0f3460 100%);
      ${design?.background_image_url ? `background-image: url("${design.background_image_url}");background-size: cover;background-position: center;background-blend-mode: overlay;` : ''}
      min-height: 100vh;
      padding: 20px;
    }
    
    .container {
      max-width: 900px;
      margin: 0 auto;
    }
    
    .header {
      text-align: center;
      margin-bottom: 32px;
      color: white;
    }
    
    .header h1 {
      font-size: 2.5rem;
      margin-bottom: 8px;
      color: var(--gold);
    }
    
    .bank-card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(20px);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 20px;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .bank-card-header {
      text-align: center;
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 2px solid rgba(212, 175, 55, 0.3);
    }
    
    .bank-card-header i {
      font-size: 2.5rem;
      color: var(--gold);
      margin-bottom: 8px;
    }
    
    .bank-card-header h3 {
      color: white;
      font-size: 1.5rem;
      margin-bottom: 4px;
    }
    
    .bank-card-header p {
      color: rgba(255, 255, 255, 0.7);
    }
    
    .info-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      margin-bottom: 8px;
    }
    
    .info-row .label {
      color: var(--gold-light);
      font-weight: 600;
    }
    
    .info-row .value {
      color: white;
      font-family: monospace;
      font-size: 1.1rem;
    }
    
    .info-row button {
      background: var(--gold);
      color: var(--dark);
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
    }
    
    .toast {
      position: fixed;
      top: 20px;
      right: 20px;
      background: #28a745;
      color: white;
      padding: 16px 24px;
      border-radius: 12px;
      display: none;
      z-index: 1000;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>
        ${design?.logo_url ? `<img src="${design.logo_url}" alt="logo" style="max-height:60px; vertical-align:middle; margin-left:10px;">` : '<i class="fas fa-gem"></i>'}
        ${design?.logo_text || env.SITE_NAME}
      </h1>
      <p>الحسابات البنكية</p>
    </div>
    
    ${accountsHTML}
  </div>

  <div class="toast" id="toast">
    <i class="fas fa-check-circle"></i> تم النسخ!
  </div>

  <script>
    function copyText(text, button) {
      navigator.clipboard.writeText(text).then(() => {
        document.getElementById('toast').style.display = 'block';
        setTimeout(() => {
          document.getElementById('toast').style.display = 'none';
        }, 2000);
      });
    }
  </script>
</body>
</html>`;
}

/**
 * Generate bank not found page
 */
function generateBankNotFoundPage(code, env) {
    return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>حساب غير موجود - ${env.SITE_NAME}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    body {
      font-family: 'Cairo', sans-serif;
      background: linear-gradient(135deg, #1a1a2e, #16213e);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      text-align: center;
      padding: 20px;
    }
    .error-icon { font-size: 5rem; color: #dc3545; margin-bottom: 20px; }
    h1 { font-size: 2rem; margin-bottom: 16px; }
    p { color: rgba(255, 255, 255, 0.7); margin-bottom: 24px; }
    a {
      display: inline-block;
      background: #d4af37;
      color: #1a1a2e;
      padding: 14px 28px;
      border-radius: 12px;
      text-decoration: none;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <div>
    <div class="error-icon"><i class="fas fa-exclamation-circle"></i></div>
    <h1>الحساب البنكي غير موجود</h1>
    <p>الكود: ${code}</p>
    <a href="${env.MAIN_SITE_URL}">
      <i class="fas fa-home"></i> العودة للموقع
    </a>
  </div>
</body>
</html>`;
}

/**
 * Generate bank error page
 */
function generateBankErrorPage(error, env) {
    return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>خطأ - ${env.SITE_NAME}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    body {
      font-family: 'Cairo', sans-serif;
      background: linear-gradient(135deg, #1a1a2e, #16213e);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      text-align: center;
      padding: 20px;
    }
    .error-icon { font-size: 5rem; color: #dc3545; margin-bottom: 20px; }
    h1 { font-size: 2rem; margin-bottom: 16px; }
    p { color: rgba(255, 255, 255, 0.7); margin-bottom: 24px; }
    code { background: rgba(255, 255, 255, 0.1); padding: 4px 8px; border-radius: 4px; }
  </style>
</head>
<body>
  <div>
    <div class="error-icon"><i class="fas fa-times-circle"></i></div>
    <h1>حدث خطأ</h1>
    <p><code>${error}</code></p>
  </div>
</body>
</html>`;
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

        // Bank account routes
        if (path.startsWith('/bank/')) {
            const code = path.replace('/bank/', '').replace('/', '');
            return handleBankAccount(code, env);
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
        } else if (path.length > 1 && !path.includes('/api/') && !path.includes('/sync') && !path.includes('/health') && !path.includes('/bank/')) {
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

            return new Response(await generateProductPage(product, env), {
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
        }

        // Default: redirect to main site
        return Response.redirect(env.MAIN_SITE_URL, 302);
    }
};
