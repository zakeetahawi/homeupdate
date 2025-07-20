/**
 * تحسين الانتقال السلس بين الأقسام - حل مشكلة الوميض
 * Smooth Navigation Enhancement - Fix Flickering
 */

document.addEventListener('DOMContentLoaded', function() {
    // تحسين الانتقال السلس بين الأقسام
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    const mainContent = document.getElementById('main-content');
    const mainFooter = document.getElementById('main-footer');
    
    // إضافة تأثير انتقالي للروابط مع منع الوميض
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // تجاهل الروابط التي تحتوي على dropdown أو external links
            if (this.getAttribute('data-bs-toggle') || this.target === '_blank') {
                return;
            }
            
            // منع السلوك الافتراضي للرابط
            e.preventDefault();
            
            // إضافة تأثير انتقالي سلس بدون وميض
            if (mainContent) {
                mainContent.style.transition = 'opacity 0.2s ease';
                mainContent.style.opacity = '0.9';
            }
            
            // الانتقال إلى الصفحة الجديدة بعد فترة قصيرة
            setTimeout(() => {
                window.location.href = this.href;
            }, 150);
        });
    });
    
    // تحسين تحميل الصفحة - منع الوميض عند التحميل
    window.addEventListener('load', function() {
        if (mainContent) {
            mainContent.style.opacity = '1';
            mainContent.style.transition = 'opacity 0.3s ease';
        }
        
        // إضافة تأثير التحميل التدريجي
        const elements = document.querySelectorAll('.container-fluid, .card, .table, .row');
        elements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(10px)';
            element.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 50);
        });
    });
    
    // تحسين للهواتف المحمولة
    function adjustForMobile() {
        const isMobile = window.innerWidth <= 768;
        const isTablet = window.innerWidth > 768 && window.innerWidth <= 1024;
        const footer = document.querySelector('.footer-area');
        
        if (footer) {
            if (isMobile) {
                footer.style.position = 'relative';
                footer.style.bottom = '0';
            } else if (isTablet) {
                footer.style.position = 'relative';
                footer.style.bottom = '0';
            } else {
                footer.style.position = 'relative';
                footer.style.bottom = '0';
            }
        }
    }
    
    // تطبيق التحسينات عند تحميل الصفحة وتغيير الحجم
    adjustForMobile();
    window.addEventListener('resize', adjustForMobile);
    
    // تحسين الأداء - إضافة debounce للـ resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(adjustForMobile, 250);
    });
    
    // تحسين التمرير السلس
    const smoothScroll = function(target) {
        const element = document.querySelector(target);
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    };
    
    // إضافة تأثير hover للروابط
    navLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        link.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // تحسين تحميل الصفحة للثيمات
    function applyThemeOptimizations() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const footer = document.querySelector('.footer-area');
        
        if (footer && currentTheme) {
            // تطبيق تحسينات خاصة بالثيم
            if (currentTheme === 'modern-black') {
                footer.style.borderTop = '1px solid var(--border)';
            } else {
                footer.style.borderTop = 'none';
            }
        }
    }
    
    // تطبيق تحسينات الثيم
    applyThemeOptimizations();
    
    // مراقبة تغييرات الثيم
    const themeObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                applyThemeOptimizations();
            }
        });
    });
    
    themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });
    
    // تحسين للأجهزة اللوحية
    function adjustForTablet() {
        const isTablet = window.innerWidth > 768 && window.innerWidth <= 1024;
        const isLandscape = window.innerWidth > window.innerHeight;
        
        if (isTablet) {
            const footer = document.querySelector('.footer-area');
            if (footer) {
                if (isLandscape) {
                    footer.style.padding = '8px 0 4px 0';
                } else {
                    footer.style.padding = '10px 0 5px 0';
                }
            }
        }
    }
    
    // تطبيق تحسينات الأجهزة اللوحية
    adjustForTablet();
    window.addEventListener('resize', adjustForTablet);
    
    // تحسين الأداء - إضافة intersection observer للفوتر
    const footerObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
            }
        });
    }, {
        threshold: 0.1
    });
    
    // مراقبة الفوتر
    const footer = document.querySelector('.footer-area');
    if (footer) {
        footerObserver.observe(footer);
    }
    
    // تحسين للشاشات عالية الدقة
    function adjustForHighDPI() {
        const isHighDPI = window.devicePixelRatio > 1;
        if (isHighDPI) {
            document.body.style.webkitFontSmoothing = 'antialiased';
            document.body.style.mozOsxFontSmoothing = 'grayscale';
        }
    }
    
    // تطبيق تحسينات الشاشات عالية الدقة
    adjustForHighDPI();
    
    // تحسين التحميل التدريجي - منع الوميض
    function progressiveLoad() {
        const elements = document.querySelectorAll('.container-fluid, .card, .table, .row, .col');
        elements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(5px)';
            element.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 30);
        });
    }
    
    // تطبيق التحميل التدريجي بعد تحميل الصفحة
    setTimeout(progressiveLoad, 100);
    
    // منع الوميض عند التحميل الأولي
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.3s ease';
    
    window.addEventListener('load', function() {
        document.body.style.opacity = '1';
    });
});

// تحسين الأداء العام - منع الوميض
window.addEventListener('load', function() {
    // إزالة تأثيرات التحميل
    document.body.classList.add('loaded');
    
    // تحسين التمرير
    if ('scrollBehavior' in document.documentElement.style) {
        // المتصفح يدعم التمرير السلس
    } else {
        // fallback للمتصفحات القديمة
        const smoothScrollPolyfill = function(target) {
            const element = document.querySelector(target);
            if (element) {
                element.scrollIntoView();
            }
        };
    }
    
    // منع الوميض في العناصر المهمة
    const importantElements = document.querySelectorAll('header, nav, footer, main');
    importantElements.forEach(element => {
        element.style.transition = 'opacity 0.3s ease';
        element.style.opacity = '1';
    });
});

// تحسين إضافي لمنع الوميض
document.addEventListener('DOMContentLoaded', function() {
    // إضافة CSS لمنع الوميض
    const style = document.createElement('style');
    style.textContent = `
        * {
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        body {
            opacity: 1 !important;
            transition: opacity 0.3s ease !important;
        }
        
        .container-fluid, .card, .table, .row, .col {
            transition: opacity 0.3s ease, transform 0.3s ease !important;
        }
        
        /* منع الوميض في العناصر المهمة */
        header, nav, footer, main {
            opacity: 1 !important;
            transition: opacity 0.3s ease !important;
        }
    `;
    document.head.appendChild(style);
}); 