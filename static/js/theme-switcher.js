/**
 * مدير تبديل السمات - نظام محدث يدعم 6 ثيمات
 * Theme Switcher Manager - Updated System Supporting 6 Themes
 * 
 * الثيمات المتاحة:
 * 1. default - الثيم الافتراضي (البني الكلاسيكي)
 * 2. custom-theme - ثيم مخصص مع تأثيرات متقدمة
 * 3. modern-black - ثيم أسود عصري
 * 4. mocha-mousse - Pantone 2025
 * 5. warm-earth - ألوان ترابية دافئة
 * 6. coffee-elegance - أناقة القهوة
 */

(function() {
    'use strict';

    // قائمة الثيمات المتاحة مع أسمائها
    const availableThemes = {
        'default': 'الثيم الافتراضي',
        'custom-theme': 'ثيم مخصص',
        'modern-black': 'أسود عصري',
        'mocha-mousse': 'Mocha Mousse (Pantone 2025)',
        'warm-earth': 'ألوان ترابية دافئة',
        'coffee-elegance': 'أناقة القهوة'
    };

    // تحديد عناصر DOM
    const themeSelector = document.getElementById('themeSelector');
    const body = document.documentElement;

    // تحميل السمة المحفوظة
    function loadSavedTheme() {
        const savedTheme = localStorage.getItem('selectedTheme');
        if (savedTheme && availableThemes[savedTheme]) {
            applyTheme(savedTheme);
            if (themeSelector) {
                themeSelector.value = savedTheme;
            }
        } else {
            // إذا لم يكن هناك ثيم محفوظ أو غير صالح، استخدم الافتراضي
            applyTheme('default');
        }
    }

    // تطبيق السمة
    function applyTheme(theme) {
        // التحقق من صلاحية الثيم
        if (!availableThemes[theme]) {
            console.warn(`الثيم "${theme}" غير متاح. استخدام الثيم الافتراضي.`);
            theme = 'default';
        }

        if (theme === 'default') {
            body.removeAttribute('data-theme');
        } else {
            body.setAttribute('data-theme', theme);
        }
        
        localStorage.setItem('selectedTheme', theme);

        // إرسال السمة المحددة إلى الخادم إذا كان المستخدم مسجل الدخول
        if (body.getAttribute('data-user-authenticated') === 'true') {
            saveThemePreference(theme);
        }

        // تطبيق تأثير التحول السلس
        addTransitionEffect();

        // إرسال حدث تغيير الثيم
        document.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { 
                theme: theme,
                themeName: availableThemes[theme]
            } 
        }));

        console.log(`✓ تم تطبيق الثيم: ${availableThemes[theme]}`);
    }

    // إضافة تأثير انتقالي سلس عند تغيير الثيم
    function addTransitionEffect() {
        const transitionElement = document.createElement('div');
        transitionElement.className = 'theme-transition-overlay';
        document.body.appendChild(transitionElement);
        
        // إزالة عنصر التحول بعد انتهاء التأثير
        setTimeout(() => {
            transitionElement.classList.add('fade-out');
            setTimeout(() => {
                if (transitionElement.parentNode) {
                    transitionElement.parentNode.removeChild(transitionElement);
                }
            }, 300);
        }, 50);
    }

    // حفظ تفضيل السمة في الخادم
    function saveThemePreference(theme) {
        // استخدام fetch API (حديث وأفضل من jQuery Ajax)
        if (typeof fetch !== 'undefined') {
            fetch('/accounts/save-theme/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ theme: theme })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log('✓ تم حفظ تفضيل الثيم بنجاح');
                }
            })
            .catch(error => {
                console.error('✗ خطأ في حفظ تفضيل الثيم:', error);
            });
        } else if (typeof $ !== 'undefined' && $.ajax) {
            // استخدام jQuery كبديل إذا كان متاحاً
            $.ajax({
                url: '/accounts/save-theme/',
                type: 'POST',
                data: { theme: theme },
                success: function(response) {
                    if (response.status === 'success') {
                        console.log('✓ تم حفظ تفضيل الثيم بنجاح');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('✗ خطأ في حفظ تفضيل الثيم:', error);
                }
            });
        }
    }

    // الحصول على CSRF Token
    function getCsrfToken() {
        const csrfMeta = document.querySelector('[name="csrf-token"]');
        if (csrfMeta) {
            return csrfMeta.getAttribute('content');
        }
        const csrfInput = document.querySelector('[name="csrfmiddlewaretoken"]');
        if (csrfInput) {
            return csrfInput.value;
        }
        return '';
    }

    // إضافة مستمع الحدث لتغيير السمة
    if (themeSelector) {
        themeSelector.addEventListener('change', function(e) {
            const selectedTheme = e.target.value;
            applyTheme(selectedTheme);
        });

        // ملء القائمة المنسدلة بالثيمات المتاحة (إذا كانت فارغة)
        if (themeSelector.options.length === 0) {
            Object.keys(availableThemes).forEach(themeKey => {
                const option = document.createElement('option');
                option.value = themeKey;
                option.textContent = availableThemes[themeKey];
                themeSelector.appendChild(option);
            });
        }
    }

    // تحميل السمة المحفوظة عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadSavedTheme);
    } else {
        loadSavedTheme();
    }

    // إضافة وظيفة عامة للتبديل بين الثيمات (للاستخدام من Console أو أماكن أخرى)
    window.switchTheme = function(themeName) {
        if (availableThemes[themeName]) {
            applyTheme(themeName);
            if (themeSelector) {
                themeSelector.value = themeName;
            }
            return `تم التبديل إلى: ${availableThemes[themeName]}`;
        } else {
            return `الثيم "${themeName}" غير متاح. الثيمات المتاحة: ${Object.keys(availableThemes).join(', ')}`;
        }
    };

    // عرض الثيمات المتاحة في Console
    console.log('📋 الثيمات المتاحة:');
    Object.keys(availableThemes).forEach((key, index) => {
        console.log(`  ${index + 1}. ${key} - ${availableThemes[key]}`);
    });
    console.log('💡 للتبديل: switchTheme("theme-name")');
})(); 