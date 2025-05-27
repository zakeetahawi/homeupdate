/**
 * Unified Icons Theme - Professional Silver-Blue
 * نظام الأيقونات الموحدة للثيم الفضي الأزرق الاحترافي
 */

document.addEventListener('DOMContentLoaded', function() {
    // تطبيق الأيقونات الموحدة عند تحميل الصفحة
    applyUnifiedIcons();

    // مراقبة تغيير الثيم
    const themeSelector = document.getElementById('themeSelector');
    if (themeSelector) {
        themeSelector.addEventListener('change', function() {
            setTimeout(applyUnifiedIcons, 100); // تأخير قصير للسماح بتطبيق الثيم
        });
    }

    // مراقبة التغييرات في DOM لتطبيق الأيقونات على العناصر الجديدة
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                setTimeout(applyUnifiedIcons, 50);
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

function applyUnifiedIcons() {
    const currentTheme = document.body.getAttribute('data-theme');

    // تطبيق الأيقونات الموحدة فقط للثيم الفضي الأزرق الاحترافي
    if (currentTheme === 'professional-silver-blue') {
        unifyNavigationIcons();
        unifyActionIcons();
        unifyTableIcons();
        unifyButtonIcons();
        addIconAnimations();
    }
}

function unifyNavigationIcons() {
    // توحيد أيقونات التنقل الرئيسية
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href') || '';
        const icon = link.querySelector('i');

        if (icon) {
            // إزالة الفئات الحالية والاحتفاظ بـ Font Awesome الأساسي
            icon.className = icon.className.replace(/fa-\w+/g, '');

            // إضافة الأيقونات الموحدة حسب القسم
            if (href.includes('home') || href === '/') {
                icon.classList.add('fas', 'fa-home');
            } else if (href.includes('customers')) {
                icon.classList.add('fas', 'fa-users');
            } else if (href.includes('orders')) {
                icon.classList.add('fas', 'fa-shopping-cart');
            } else if (href.includes('inventory')) {
                icon.classList.add('fas', 'fa-boxes');
            } else if (href.includes('inspections')) {
                icon.classList.add('fas', 'fa-clipboard-check');
            } else if (href.includes('installations')) {
                icon.classList.add('fas', 'fa-tools');
            } else if (href.includes('factory')) {
                icon.classList.add('fas', 'fa-industry');
            } else if (href.includes('reports')) {
                icon.classList.add('fas', 'fa-chart-bar');
            } else if (href.includes('database') || href.includes('data')) {
                icon.classList.add('fas', 'fa-database');
            }
        }
    });
}

function unifyActionIcons() {
    // توحيد أيقونات الإجراءات في الجداول
    const actionButtons = document.querySelectorAll('.btn-link, .action-btn');

    actionButtons.forEach(button => {
        const icon = button.querySelector('i');
        const title = button.getAttribute('title') || '';
        const text = button.textContent.toLowerCase();

        if (icon) {
            // إزالة الفئات الحالية
            icon.className = icon.className.replace(/fa-\w+/g, '');

            // إضافة الأيقونات الموحدة حسب الوظيفة
            if (title.includes('عرض') || title.includes('تفاصيل') || text.includes('عرض')) {
                icon.classList.add('fas', 'fa-eye');
                button.classList.add('text-info');
            } else if (title.includes('تحميل') || title.includes('نسخة احتياطية') || text.includes('تحميل')) {
                icon.classList.add('fas', 'fa-download');
                button.classList.add('text-success');
            } else if (title.includes('تعديل') || title.includes('تحرير') || text.includes('تعديل')) {
                icon.classList.add('fas', 'fa-edit');
                button.classList.add('text-warning');
            } else if (title.includes('حذف') || text.includes('حذف')) {
                icon.classList.add('fas', 'fa-trash');
                button.classList.add('text-danger');
            } else if (title.includes('تنشيط') || title.includes('تفعيل')) {
                icon.classList.add('fas', 'fa-power-off');
                button.classList.add('text-primary');
            } else if (title.includes('جدولة') || title.includes('وقت')) {
                icon.classList.add('fas', 'fa-clock');
                button.classList.add('text-warning');
            } else if (title.includes('إعدادات') || title.includes('ضبط')) {
                icon.classList.add('fas', 'fa-cog');
                button.classList.add('text-info');
            } else if (title.includes('طباعة')) {
                icon.classList.add('fas', 'fa-print');
                button.classList.add('text-secondary');
            } else if (title.includes('تصدير')) {
                icon.classList.add('fas', 'fa-file-export');
                button.classList.add('text-success');
            } else if (title.includes('استيراد')) {
                icon.classList.add('fas', 'fa-file-import');
                button.classList.add('text-primary');
            }
        }
    });
}

function unifyTableIcons() {
    // توحيد أيقونات الجداول
    const tableIcons = document.querySelectorAll('table i');

    tableIcons.forEach(icon => {
        const parentCell = icon.closest('td');
        const parentButton = icon.closest('button, a');

        if (parentButton && parentCell) {
            const buttonClass = parentButton.className;

            // إزالة الفئات الحالية
            icon.className = icon.className.replace(/fa-\w+/g, '');

            // إضافة الأيقونات حسب نوع الزر
            if (buttonClass.includes('text-info')) {
                icon.classList.add('fas', 'fa-eye');
            } else if (buttonClass.includes('text-success')) {
                icon.classList.add('fas', 'fa-download');
            } else if (buttonClass.includes('text-warning')) {
                icon.classList.add('fas', 'fa-clock');
            } else if (buttonClass.includes('text-danger')) {
                icon.classList.add('fas', 'fa-trash');
            } else if (buttonClass.includes('text-primary')) {
                icon.classList.add('fas', 'fa-power-off');
            }
        }
    });
}

function unifyButtonIcons() {
    // توحيد أيقونات الأزرار العامة
    const buttons = document.querySelectorAll('.btn');

    buttons.forEach(button => {
        const icon = button.querySelector('i');
        const text = button.textContent.toLowerCase();

        if (icon && text) {
            // إزالة الفئات الحالية
            icon.className = icon.className.replace(/fa-\w+/g, '');

            // إضافة الأيقونات حسب النص
            if (text.includes('إضافة') || text.includes('جديد')) {
                icon.classList.add('fas', 'fa-plus');
            } else if (text.includes('حفظ')) {
                icon.classList.add('fas', 'fa-save');
            } else if (text.includes('إلغاء')) {
                icon.classList.add('fas', 'fa-times');
            } else if (text.includes('بحث')) {
                icon.classList.add('fas', 'fa-search');
            } else if (text.includes('تصفية')) {
                icon.classList.add('fas', 'fa-filter');
            } else if (text.includes('تحديث')) {
                icon.classList.add('fas', 'fa-sync-alt');
            } else if (text.includes('رجوع')) {
                icon.classList.add('fas', 'fa-arrow-left');
            } else if (text.includes('التالي')) {
                icon.classList.add('fas', 'fa-arrow-right');
            }
        }
    });
}

function addIconAnimations() {
    // إضافة تأثيرات الحركة للأيقونات
    const allIcons = document.querySelectorAll('i[class*="fa"]');

    allIcons.forEach(icon => {
        const parentElement = icon.parentElement;

        // إضافة تأثير hover للأيقونات
        parentElement.addEventListener('mouseenter', function() {
            icon.style.transform = 'scale(1.1)';
            icon.style.transition = 'all 0.3s ease';
        });

        parentElement.addEventListener('mouseleave', function() {
            icon.style.transform = 'scale(1)';
        });

        // إضافة تأثير النقر
        parentElement.addEventListener('click', function() {
            icon.style.transform = 'scale(0.9)';
            setTimeout(() => {
                icon.style.transform = 'scale(1.1)';
            }, 100);
        });
    });
}

// تصدير الوظائف للاستخدام الخارجي
window.UnifiedIconsTheme = {
    apply: applyUnifiedIcons,
    unifyNavigation: unifyNavigationIcons,
    unifyActions: unifyActionIcons,
    unifyTables: unifyTableIcons,
    unifyButtons: unifyButtonIcons,
    addAnimations: addIconAnimations
};
