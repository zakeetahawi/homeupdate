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
        unifyFormIcons();
        unifyNotificationIcons();
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
    const tableIcons = document.querySelectorAll('table i, .table i');

    tableIcons.forEach(icon => {
        const parentButton = icon.closest('button, a, .btn-link');

        if (parentButton) {
            const buttonClass = parentButton.className;
            const title = parentButton.getAttribute('title') || '';
            const href = parentButton.getAttribute('href') || '';

            // إزالة الفئات الحالية
            icon.className = icon.className.replace(/fa-\w+/g, '');
            if (!icon.classList.contains('fas')) {
                icon.classList.add('fas');
            }

            // إضافة الأيقونات حسب نوع الزر أو العنوان أو الرابط
            if (buttonClass.includes('text-info') || title.includes('عرض') || title.includes('تفاصيل')) {
                icon.classList.add('fa-eye');
            } else if (buttonClass.includes('text-success') || title.includes('تحميل') || title.includes('نسخة احتياطية')) {
                icon.classList.add('fa-download');
            } else if (buttonClass.includes('text-warning') || title.includes('جدولة') || title.includes('وقت') || title.includes('تعديل')) {
                if (title.includes('تعديل')) {
                    icon.classList.add('fa-edit');
                } else {
                    icon.classList.add('fa-clock');
                }
            } else if (buttonClass.includes('text-danger') || title.includes('حذف')) {
                icon.classList.add('fa-trash');
            } else if (buttonClass.includes('text-primary') || title.includes('تنشيط') || title.includes('تفعيل')) {
                icon.classList.add('fa-power-off');
            } else if (title.includes('إعدادات')) {
                icon.classList.add('fa-cog');
            } else if (title.includes('طباعة')) {
                icon.classList.add('fa-print');
            } else if (href.includes('edit') || href.includes('update')) {
                icon.classList.add('fa-edit');
                parentButton.classList.add('text-warning');
            } else if (href.includes('delete') || href.includes('remove')) {
                icon.classList.add('fa-trash');
                parentButton.classList.add('text-danger');
            } else if (href.includes('view') || href.includes('detail')) {
                icon.classList.add('fa-eye');
                parentButton.classList.add('text-info');
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

function unifyFormIcons() {
    // توحيد أيقونات النماذج
    const formGroups = document.querySelectorAll('.form-group, .mb-3, .form-floating');

    formGroups.forEach(group => {
        const label = group.querySelector('label');
        const input = group.querySelector('input, select, textarea');

        if (label && input && !label.querySelector('i.fas')) {
            const labelText = label.textContent.toLowerCase();
            const inputType = input.type || '';
            const inputName = input.name || '';
            let iconClass = '';

            // تحديد الأيقونة حسب النص أو نوع الحقل
            if (labelText.includes('اسم') || labelText.includes('name') || inputName.includes('name')) {
                iconClass = 'fa-user';
            } else if (labelText.includes('بريد') || labelText.includes('email') || inputType === 'email') {
                iconClass = 'fa-envelope';
            } else if (labelText.includes('هاتف') || labelText.includes('phone') || inputType === 'tel') {
                iconClass = 'fa-phone';
            } else if (labelText.includes('عنوان') || labelText.includes('address')) {
                iconClass = 'fa-map-marker-alt';
            } else if (labelText.includes('تاريخ') || labelText.includes('date') || inputType === 'date') {
                iconClass = 'fa-calendar';
            } else if (labelText.includes('وقت') || labelText.includes('time') || inputType === 'time') {
                iconClass = 'fa-clock';
            } else if (labelText.includes('كلمة المرور') || labelText.includes('password') || inputType === 'password') {
                iconClass = 'fa-lock';
            } else if (labelText.includes('بحث') || labelText.includes('search') || inputType === 'search') {
                iconClass = 'fa-search';
            } else if (labelText.includes('ملف') || labelText.includes('file') || inputType === 'file') {
                iconClass = 'fa-file';
            } else if (labelText.includes('صورة') || labelText.includes('image')) {
                iconClass = 'fa-image';
            } else if (labelText.includes('رقم') || labelText.includes('number') || inputType === 'number') {
                iconClass = 'fa-hashtag';
            } else if (labelText.includes('مبلغ') || labelText.includes('سعر') || labelText.includes('price')) {
                iconClass = 'fa-dollar-sign';
            } else if (labelText.includes('وصف') || labelText.includes('description') || input.tagName === 'TEXTAREA') {
                iconClass = 'fa-align-left';
            } else if (labelText.includes('فئة') || labelText.includes('category') || input.tagName === 'SELECT') {
                iconClass = 'fa-list';
            } else if (labelText.includes('حالة') || labelText.includes('status')) {
                iconClass = 'fa-info-circle';
            }

            if (iconClass) {
                const icon = document.createElement('i');
                icon.className = `fas ${iconClass}`;
                icon.style.marginLeft = '8px';
                icon.style.color = '#007bff';

                label.insertBefore(icon, label.firstChild);
            }
        }
    });
}

function unifyNotificationIcons() {
    // توحيد أيقونات الإشعارات والتنبيهات
    const notificationButton = document.querySelector('[data-bs-toggle="dropdown"][aria-expanded]');
    if (notificationButton) {
        const icon = notificationButton.querySelector('i');
        if (icon) {
            icon.className = 'fas fa-bell';
            icon.style.color = '#ff9500';
        }
    }

    // أيقونات القائمة المنسدلة للمستخدم
    const userDropdownItems = document.querySelectorAll('.dropdown-item');
    userDropdownItems.forEach(item => {
        const icon = item.querySelector('i');
        const text = item.textContent.toLowerCase();

        if (icon) {
            icon.className = icon.className.replace(/fa-\w+/g, '');
            if (!icon.classList.contains('fas')) {
                icon.classList.add('fas');
            }

            if (text.includes('ملف') || text.includes('profile')) {
                icon.classList.add('fa-user');
            } else if (text.includes('إعدادات') || text.includes('settings')) {
                icon.classList.add('fa-cog');
            } else if (text.includes('خروج') || text.includes('logout')) {
                icon.classList.add('fa-sign-out-alt');
            } else if (text.includes('لوحة') || text.includes('admin')) {
                icon.classList.add('fa-tachometer-alt');
            }
        }
    });

    // أيقونات الإشعارات والتنبيهات
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (!alert.querySelector('i.fas')) {
            let iconClass = '';

            if (alert.classList.contains('alert-success')) {
                iconClass = 'fa-check-circle';
            } else if (alert.classList.contains('alert-danger')) {
                iconClass = 'fa-exclamation-circle';
            } else if (alert.classList.contains('alert-warning')) {
                iconClass = 'fa-exclamation-triangle';
            } else if (alert.classList.contains('alert-info')) {
                iconClass = 'fa-info-circle';
            }

            if (iconClass) {
                const icon = document.createElement('i');
                icon.className = `fas ${iconClass}`;
                icon.style.marginLeft = '8px';

                alert.insertBefore(icon, alert.firstChild);
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
    unifyForms: unifyFormIcons,
    unifyNotifications: unifyNotificationIcons,
    addAnimations: addIconAnimations
};
