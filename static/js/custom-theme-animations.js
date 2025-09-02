/**
 * تأثيرات حركية إضافية للثيم المخصص
 * Additional Animation Effects for Custom Theme
 */
document.addEventListener('DOMContentLoaded', function() {
    // التحقق من استخدام الثيم المخصص
    const isCustomTheme = document.documentElement.getAttribute('data-theme') === 'custom-theme';
    
    if (!isCustomTheme) return;
    
    // إضافة صنف للعناصر التي ستظهر بتأثير حركي عند التمرير
    const sectionsToAnimate = document.querySelectorAll('.card, .table-responsive, .section-container, .alert:not(.alert-sticky)');
    sectionsToAnimate.forEach(section => {
        section.classList.add('animate-on-scroll');
        section.style.opacity = "0";
    });
    
    // تطبيق التأثير عند التمرير
    const applyScrollAnimation = () => {
        const scrolled = window.scrollY;
        const viewportHeight = window.innerHeight;
        
        document.querySelectorAll('.animate-on-scroll').forEach(element => {
            const elementTop = element.getBoundingClientRect().top + scrolled;
            const elementVisible = 150; // مقدار الظهور قبل تطبيق التأثير
            
            if (scrolled + viewportHeight > elementTop + elementVisible) {
                element.style.opacity = "1";
                element.style.animation = "slideUp 0.5s ease-out forwards";
                element.classList.remove('animate-on-scroll');
            }
        });
    };
    
    // تطبيق التأثير عند التحميل وعند التمرير
    setTimeout(applyScrollAnimation, 300);
    window.addEventListener('scroll', applyScrollAnimation);
    
    // إضافة تأثيرات للأيقونات في الصفحة خارج الهيدر
    const enhancePageIcons = () => {
        // الأيقونات في الصفحة (خارج الهيدر)
        const pageIcons = document.querySelectorAll('.card i.fa, .card i.fas, .card i.far, .card-header i, .btn i:not(.navbar i)');
        
        pageIcons.forEach(icon => {
            // تجنب إضافة التأثير مرتين
            if (icon.classList.contains('enhanced')) return;
            
            // إضافة تأثيرات متنوعة
            icon.classList.add('enhanced');
            icon.style.transition = "all 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28)";
            
            // تأثير عند التحويم (hover)
            icon.closest('.card, .btn').addEventListener('mouseenter', function() {
                icon.style.transform = "scale(1.2) rotate(5deg)";
                icon.style.color = getRandomBrightColor();
                icon.style.textShadow = "0 0 8px rgba(255, 255, 255, 0.5)";
            });
            
            // إعادة للحالة الأصلية
            icon.closest('.card, .btn').addEventListener('mouseleave', function() {
                icon.style.transform = "scale(1) rotate(0deg)";
                icon.style.color = "";
                icon.style.textShadow = "";
            });
        });
    };
    
    // لون عشوائي مشرق للأيقونات
    const getRandomBrightColor = () => {
        const brightColors = [
            '#6A5743', // لون الثيم الأساسي
            '#8B6E4E', // لون الثيم الثانوي
            '#3CBD41', // أخضر نجاح
            '#FF8500', // برتقالي تحذير
            '#E53935', // أحمر
            '#1E88E5', // أزرق
            '#C1A78A', // لون متوافق
        ];
        return brightColors[Math.floor(Math.random() * brightColors.length)];
    };
    
    // تطبيق تأثيرات الأيقونات وإعادة تطبيقها عند التحميل الجزئي بواسطة AJAX
    enhancePageIcons();
    
    // مراقبة التغييرات في DOM لتطبيق التأثيرات على المحتوى المضاف ديناميكياً
    const observer = new MutationObserver(function(mutations) {
        enhancePageIcons();
        applyScrollAnimation();
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
});

/**
 * تطبيق تأثيرات إضافية عند تحديد الثيم المخصص
 * Apply additional effects when custom theme is selected
 */
document.addEventListener('DOMContentLoaded', function() {
    const themeSelector = document.getElementById('themeSelector');
    if (!themeSelector) return;
    
    themeSelector.addEventListener('change', function(e) {
        if (e.target.value === 'custom-theme') {
            // تطبيق نظام الحركة بعد تأخير للسماح لتغيير الثيم بالانتهاء
            setTimeout(() => {
                // تنشيط أي أكواد إضافية مطلوبة للثيم المخصص
                const event = new Event('customThemeApplied');
                document.dispatchEvent(event);
                
                // إعادة تحميل التأثيرات
                const script = document.createElement('script');
                script.src = '/static/js/custom-theme-animations.js';
                script.onload = function() {
                    console.log('تم تطبيق تأثيرات الثيم المخصص بنجاح');
                };
                document.head.appendChild(script);
            }, 300);
        }
    });
});
