/**
 * Cloudflare Worker - Error Handler with KV-Based Design
 * Loads background image from KV storage
 * Fully responsive for mobile and desktop
 */

async function generateCustomErrorPage(env) {
  // Load design settings from KV
  let design = null;
  try {
    if (env && env.PRODUCTS_KV) {
      design = await env.PRODUCTS_KV.get('__QR_DESIGN_SETTINGS__', 'json');
    }
  } catch (e) {
    console.error('KV access error:', e.message);
  }

  // Fallback design if KV not available
  if (!design) {
    design = {
      colors: {
        primary: '#D4A362',
        secondary: '#D4B896',
        background: '#1a1411',
        surface: '#2a1f1a',
        card: 'rgba(26, 20, 17, 0.95)',
      },
      background_image_url: ''
    };
  }

  const year = new Date().getFullYear();
  const siteName = env.SITE_NAME || 'الخواجة';

  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>السيرفر متوقف مؤقتاً - ${siteName}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <style>
    :root {
      --brown-dark: #5D3A1A;
      --gold: ${design.colors?.primary || '#D4A362'};
      --beige-light: #F5EBD4;
    }
    
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    html {
      height: 100%;
      overflow: hidden;
    }
    
    body {
      font-family: 'Cairo', sans-serif;
      background-color: ${design.colors?.background || '#1a1411'};
      ${design.background_image_url ? `
      background-image: url("${design.background_image_url}");
      background-size: cover;
      background-position: center;
      background-repeat: no-repeat;
      background-attachment: fixed;
      ` : `
      /* Fallback CSS pattern if no KV background */
      background-image: 
        radial-gradient(circle at 25% 25%, rgba(212, 163, 98, 0.15) 0%, transparent 3%),
        radial-gradient(circle at 75% 75%, rgba(212, 163, 98, 0.15) 0%, transparent 3%),
        repeating-linear-gradient(45deg, rgba(93, 58, 26, 0.05) 0px, rgba(93, 58, 26, 0.05) 1px, transparent 1px, transparent 10px),
        radial-gradient(ellipse at center, #2a1f1a 0%, #1a1411 70%, #0d0a08 100%);
      background-size: 80px 80px, 80px 80px, 20px 20px, 100% 100%;
      background-attachment: fixed;
      `}
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
    }
    
    body::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.3);
      z-index: 0;
    }
    
    body::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-image:
        radial-gradient(circle at 20% 80%, rgba(212, 163, 98, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(212, 163, 98, 0.06) 0%, transparent 50%);
      pointer-events: none;
      z-index: 1;
    }
    
    .main-content {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      position: relative;
      z-index: 2;
      overflow: hidden;
    }
    
    .container {
      max-width: 900px;
      width: 100%;
    }
    
    .error-card {
      background: var(--beige-light);
      border: 2px solid var(--gold);
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 10px 40px rgba(93, 58, 26, 0.5);
      animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(30px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .error-header {
      background: linear-gradient(135deg, var(--brown-dark) 0%, #4a2f15 100%);
      padding: 40px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }
    
    .error-header::before {
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: conic-gradient(from 0deg, transparent 0deg 90deg, rgba(212, 163, 98, 0.1) 90deg 180deg, transparent 180deg 270deg, rgba(212, 163, 98, 0.05) 270deg 360deg);
      animation: rotate 20s linear infinite;
    }
    
    @keyframes rotate {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    .error-icon {
      font-size: 4rem;
      color: var(--gold);
      margin-bottom: 15px;
      position: relative;
      z-index: 1;
      animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.1); }
    }
    
    .error-title {
      font-size: 2rem;
      font-weight: 700;
      color: var(--beige-light);
      margin-bottom: 10px;
      position: relative;
      z-index: 1;
    }
    
    .error-subtitle {
      font-size: 1.3rem;
      font-weight: 600;
      color: var(--gold);
      margin-bottom: 8px;
      position: relative;
      z-index: 1;
    }
    
    .error-code {
      font-size: 0.85rem;
      color: rgba(245, 235, 212, 0.7);
      font-family: 'Courier New', monospace;
      position: relative;
      z-index: 1;
    }
    
    .error-content {
      padding: 40px;
      text-align: center;
    }
    
    .error-message {
      font-size: 1.2rem;
      color: var(--brown-dark);
      margin-bottom: 25px;
      line-height: 1.8;
    }
    
    .error-message-en {
      font-size: 1rem;
      color: #6b4423;
      margin-bottom: 30px;
      font-style: italic;
      line-height: 1.6;
    }
    
    .contact-section {
      background: linear-gradient(135deg, rgba(212, 163, 98, 0.15) 0%, rgba(212, 163, 98, 0.05) 100%);
      border: 1px solid rgba(212, 163, 98, 0.3);
      border-radius: 14px;
      padding: 25px;
    }
    
    .contact-title {
      font-size: 1.2rem;
      font-weight: 700;
      color: var(--brown-dark);
      margin-bottom: 15px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }
    
    .contact-message {
      font-size: 1.1rem;
      color: var(--brown-dark);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }
    
    .contact-message i {
      color: var(--gold);
      font-size: 1.2rem;
    }
    
    .status-indicator {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(220, 53, 69, 0.1);
      border: 1px solid rgba(220, 53, 69, 0.3);
      color: #dc3545;
      padding: 10px 20px;
      border-radius: 10px;
      font-weight: 600;
      margin-bottom: 25px;
      font-size: 1rem;
    }
    
    .status-dot {
      width: 10px;
      height: 10px;
      background: #dc3545;
      border-radius: 50%;
      animation: blink 1.5s ease-in-out infinite;
    }
    
    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
    
    .footer {
      background: var(--brown-dark);
      padding: 12px 20px;
      border-top: 2px solid var(--gold);
      position: relative;
      z-index: 2;
    }
    
    .footer-content {
      max-width: 1200px;
      margin: 0 auto;
    }
    
    .footer-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
      gap: 15px;
    }
    
    .footer-brand {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--beige-light);
      font-size: 0.9rem;
      font-weight: 600;
    }
    
    .footer-brand i {
      color: var(--gold);
      font-size: 1rem;
    }
    
    .footer-links {
      display: flex;
      gap: 20px;
    }
    
    .footer-link {
      color: var(--beige-light);
      text-decoration: none;
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 0.85rem;
    }
    
    .footer-link:hover {
      color: var(--gold);
      transform: translateY(-2px);
    }
    
    .footer-link i {
      font-size: 0.9rem;
    }
    
    .copyright {
      color: var(--beige-light);
      font-size: 0.75rem;
      opacity: 0.8;
      padding-top: 8px;
      border-top: 1px solid rgba(212, 163, 98, 0.2);
      text-align: center;
    }
    
    /* Mobile Responsive Design */
    @media (max-width: 768px) {
      html {
        overflow-y: auto;
        height: auto;
      }
      
      body {
        height: auto;
        min-height: 100vh;
        overflow-y: auto;
      }
      
      .main-content {
        padding: 15px;
        overflow-y: auto;
      }
      
      .error-header {
        padding: 30px 20px;
      }
      
      .error-icon {
        font-size: 3rem;
      }
      
      .error-title {
        font-size: 1.6rem;
      }
      
      .error-subtitle {
        font-size: 1.1rem;
      }
      
      .error-content {
        padding: 30px 20px;
      }
      
      .error-message {
        font-size: 1rem;
      }
      
      .error-message-en {
        font-size: 0.9rem;
      }
      
      .contact-section {
        padding: 20px;
      }
      
      .contact-title {
        font-size: 1rem;
      }
      
      .contact-message {
        font-size: 0.95rem;
      }
      
      .footer-row {
        flex-direction: column;
        text-align: center;
        gap: 10px;
      }
      
      .footer-links {
        flex-wrap: wrap;
        justify-content: center;
        gap: 15px;
      }
      
      .footer-brand {
        font-size: 0.85rem;
      }
      
      .footer-link {
        font-size: 0.8rem;
      }
      
      .copyright {
        font-size: 0.7rem;
      }
    }
    
    /* Desktop Full Page */
    @media (min-width: 769px) {
      .container {
        max-width: 900px;
      }
      
      .error-card {
        box-shadow: 0 15px 50px rgba(93, 58, 26, 0.6);
      }
    }
  </style>
</head>
<body>
  <div class="main-content">
    <div class="container">
      <div class="error-card">
        <div class="error-header">
          <div class="error-icon">
            <i class="fas fa-server"></i>
          </div>
          <h1 class="error-title">السيرفر متوقف مؤقتاً</h1>
          <p class="error-subtitle">Server Temporarily Unavailable</p>
          <p class="error-code">Cloudflare Error 1033 • Argo Tunnel</p>
        </div>
        <div class="error-content">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span>الخدمة متوقفة حالياً</span>
          </div>
          <p class="error-message">
            نعتذر عن الإزعاج، السيرفر متوقف حالياً للصيانة أو بسبب مشكلة تقنية.
            <br>
            الرجاء المحاولة مرة أخرى بعد قليل.
          </p>
          <p class="error-message-en">
            We apologize for the inconvenience. The server is currently down for maintenance or due to a technical issue.
            <br>
            Please try again later.
          </p>
          <div class="contact-section">
            <div class="contact-title">
              <i class="fas fa-headset"></i>
              <span>الدعم الفني</span>
            </div>
            <div class="contact-message">
              <i class="fas fa-user-shield"></i>
              <span>الرجاء التواصل مع مدير النظام</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <footer class="footer">
    <div class="footer-content">
      <div class="footer-row">
        <div class="footer-brand">
          <i class="fas fa-building"></i>
          <span>${siteName} للستائر والمفروشات</span>
        </div>
        <div class="footer-links">
          <a href="/" class="footer-link">
            <i class="fas fa-home"></i>
            <span>الرئيسية</span>
          </a>
          <a href="/about" class="footer-link">
            <i class="fas fa-info-circle"></i>
            <span>عن الشركة</span>
          </a>
          <a href="/contact" class="footer-link">
            <i class="fas fa-envelope"></i>
            <span>اتصل بنا</span>
          </a>
        </div>
      </div>
      <div class="copyright">
        <i class="far fa-copyright"></i>
        ${year} جميع الحقوق محفوظة لشركة ${siteName} للستائر والمفروشات
      </div>
    </div>
  </footer>
</body>
</html>`;
}

export default {
  async fetch(request, env, ctx) {
    try {
      const response = await fetch(request.clone(), {
        cf: { timeout: 10000 },
      });

      // Catch ALL server errors (5xx), including 530 (Tunnel Error 1033)
      if (response.status >= 500 || [520, 521, 522, 523, 524, 525, 526, 527].includes(response.status)) {
        const html = await generateCustomErrorPage(env);
        return new Response(html, {
          status: 503,
          headers: { 'Content-Type': 'text/html;charset=UTF-8' },
        });
      }
      return response;
    } catch (error) {
      const html = await generateCustomErrorPage(env);
      return new Response(html, {
        status: 503,
        headers: { 'Content-Type': 'text/html;charset=UTF-8' },
      });
    }
  },
};
