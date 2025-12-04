
/**
 * Lazy Loading للصور والمحتوى
 * يحمّل الصور فقط عند ظهورها في الشاشة
 */

(function() {
    'use strict';
    
    // دعم Intersection Observer
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    
                    // تحميل الصورة
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    
                    // تحميل srcset للـ responsive images
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                        img.removeAttribute('data-srcset');
                    }
                    
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px',  // تحميل قبل الوصول بـ 50px
            threshold: 0.01
        });
        
        // مراقبة جميع الصور بـ data-src
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
        
        // مراقبة الصور الجديدة (للمحتوى المحمّل بـ AJAX)
        const mutationObserver = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        const images = node.querySelectorAll ? 
                            node.querySelectorAll('img[data-src]') : [];
                        images.forEach(img => imageObserver.observe(img));
                        
                        if (node.matches && node.matches('img[data-src]')) {
                            imageObserver.observe(node);
                        }
                    }
                });
            });
        });
        
        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    } else {
        // Fallback للمتصفحات القديمة
        document.querySelectorAll('img[data-src]').forEach(img => {
            img.src = img.dataset.src;
        });
    }
    
    // تحميل CSS في الخلفية
    window.loadCSS = function(href) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.media = 'print';
        link.onload = function() {
            this.media = 'all';
        };
        document.head.appendChild(link);
    };
    
    // تحميل JS في الخلفية
    window.loadJS = function(src, callback) {
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        if (callback) script.onload = callback;
        document.body.appendChild(script);
    };
    
})();

// CSS للصور أثناء التحميل
const style = document.createElement('style');
style.textContent = `
    img[data-src] {
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }
    img.loaded {
        opacity: 1;
    }
    img[data-src]:not(.loaded) {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
    }
    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
`;
document.head.appendChild(style);
