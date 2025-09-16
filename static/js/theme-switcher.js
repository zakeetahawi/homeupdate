/**
 * مدير تبديل السمات
 */

(function() {
    'use strict';

    // تحديد عناصر DOM
    const themeSelector = document.getElementById('themeSelector');
    const body = document.documentElement;

    // تحميل السمة المحفوظة
    function loadSavedTheme() {
        const savedTheme = localStorage.getItem('selectedTheme');
        if (savedTheme) {
            applyTheme(savedTheme);
            if (themeSelector) {
                themeSelector.value = savedTheme;
            }
        }
    }

    // تطبيق السمة
    function applyTheme(theme) {
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
    }

    // حفظ تفضيل السمة في الخادم
    function saveThemePreference(theme) {
        $.ajax({
            url: '/accounts/save-theme/',
            type: 'POST',
            data: {
                theme: theme
            },
            success: function(response) {
                if (response.status === 'success') {
                    console.log('تم حفظ تفضيل السمة بنجاح');
                }
            },
            error: function(xhr, status, error) {
                console.error('خطأ في حفظ تفضيل السمة:', error);
            }
        });
    }

    // إضافة مستمع الحدث لتغيير السمة
    if (themeSelector) {
        themeSelector.addEventListener('change', function(e) {
            applyTheme(e.target.value);
        });
    }

    // تحميل السمة المحفوظة عند تحميل الصفحة
    document.addEventListener('DOMContentLoaded', loadSavedTheme);
})(); 