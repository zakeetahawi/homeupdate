/**
 * Google Material Icons System
 * نظام أيقونات Google Material Design
 */

document.addEventListener('DOMContentLoaded', function() {
    // تطبيق الأيقونات عند تحميل الصفحة
    applyMaterialIcons();

    // مراقبة تغيير الثيم
    const themeSelector = document.getElementById('themeSelector');
    if (themeSelector) {
        themeSelector.addEventListener('change', function() {
            setTimeout(applyMaterialIcons, 100);
        });
    }

    // مراقبة التغييرات في DOM لتطبيق الأيقونات على العناصر الجديدة
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // تطبيق الأيقونات على العناصر الجديدة
                setTimeout(applyMaterialIcons, 50);
            }
        });
    });

    // بدء مراقبة التغييرات
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // إعادة تطبيق الأيقونات عند تحميل محتوى جديد عبر AJAX
    document.addEventListener('ajaxComplete', function() {
        setTimeout(applyMaterialIcons, 100);
    });

    // إعادة تطبيق الأيقونات عند تغيير الصفحة (للتطبيقات أحادية الصفحة)
    window.addEventListener('popstate', function() {
        setTimeout(applyMaterialIcons, 100);
    });
});

function applyMaterialIcons() {
    const currentTheme = document.body.getAttribute('data-theme');

    // تطبيق الأيقونات فقط للثيم Material
    if (currentTheme === 'google-material-pro') {
        applyNavigationMaterialIcons();
        applyActionMaterialIcons();
        applyTableMaterialIcons();
        applyButtonMaterialIcons();
        applyFormMaterialIcons();
        addMaterialAnimations();
    } else {
        // إعادة الأيقونات إلى Font Awesome عند تغيير الثيم
        revertToFontAwesome();
    }
}

function revertToFontAwesome() {
    // إعادة أيقونات التنقل إلى Font Awesome
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        const href = link.getAttribute('href') || '';
        const icon = link.querySelector('i');

        if (icon && icon.classList.contains('material-icons-outlined')) {
            icon.className = '';
            icon.classList.add('fas');
            icon.textContent = '';

            if (href.includes('home') || href === '/') {
                icon.classList.add('fa-home');
            } else if (href.includes('customers')) {
                icon.classList.add('fa-users');
            } else if (href.includes('orders')) {
                icon.classList.add('fa-shopping-cart');
            } else if (href.includes('inventory')) {
                icon.classList.add('fa-boxes');
            } else if (href.includes('inspections')) {
                icon.classList.add('fa-clipboard-check');
            } else if (href.includes('installations')) {
                icon.classList.add('fa-tools');
            } else if (href.includes('factory')) {
                icon.classList.add('fa-industry');
            } else if (href.includes('reports')) {
                icon.classList.add('fa-chart-bar');
            } else if (href.includes('database') || href.includes('data')) {
                icon.classList.add('fa-database');
            }

            icon.style.fontSize = '';
            icon.style.color = '';
        }
    });

    // إعادة أيقونات الإجراءات إلى Font Awesome
    const actionButtons = document.querySelectorAll('.btn-link, .action-btn');
    actionButtons.forEach(button => {
        const icon = button.querySelector('i');
        const title = button.getAttribute('title') || '';
        const text = button.textContent.toLowerCase();

        if (icon && icon.classList.contains('material-icons-outlined')) {
            icon.className = '';
            icon.classList.add('fas');
            icon.textContent = '';

            if (title.includes('عرض') || title.includes('تفاصيل') || text.includes('عرض')) {
                icon.classList.add('fa-eye');
            } else if (title.includes('تحميل') || title.includes('نسخة احتياطية') || text.includes('تحميل')) {
                icon.classList.add('fa-download');
            } else if (title.includes('تعديل') || title.includes('تحرير') || text.includes('تعديل')) {
                icon.classList.add('fa-edit');
            } else if (title.includes('حذف') || text.includes('حذف')) {
                icon.classList.add('fa-trash');
            } else if (title.includes('تنشيط') || title.includes('تفعيل')) {
                icon.classList.add('fa-power-off');
            } else if (title.includes('جدولة') || title.includes('وقت')) {
                icon.classList.add('fa-clock');
            } else if (title.includes('إعدادات') || title.includes('ضبط')) {
                icon.classList.add('fa-cog');
            } else if (title.includes('طباعة')) {
                icon.classList.add('fa-print');
            } else if (title.includes('تصدير')) {
                icon.classList.add('fa-file-export');
            } else if (title.includes('استيراد')) {
                icon.classList.add('fa-file-import');
            }

            icon.style.fontSize = '';
        }
    });

    // إعادة أيقونات الأزرار إلى Font Awesome
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        const icon = button.querySelector('i');
        const text = button.textContent.toLowerCase();

        if (icon && icon.classList.contains('material-icons-outlined')) {
            icon.className = '';
            icon.classList.add('fas');
            icon.textContent = '';

            if (text.includes('إضافة') || text.includes('جديد')) {
                icon.classList.add('fa-plus');
            } else if (text.includes('حفظ')) {
                icon.classList.add('fa-save');
            } else if (text.includes('إلغاء')) {
                icon.classList.add('fa-times');
            } else if (text.includes('بحث')) {
                icon.classList.add('fa-search');
            } else if (text.includes('تصفية')) {
                icon.classList.add('fa-filter');
            } else if (text.includes('تحديث')) {
                icon.classList.add('fa-sync-alt');
            } else if (text.includes('رجوع')) {
                icon.classList.add('fa-arrow-left');
            } else if (text.includes('التالي')) {
                icon.classList.add('fa-arrow-right');
            }

            icon.style.fontSize = '';
            icon.style.marginLeft = '';
        }
    });

    // إزالة أيقونات النماذج المضافة
    const formIcons = document.querySelectorAll('label .material-icons-outlined');
    formIcons.forEach(icon => {
        icon.remove();
    });
}

function applyNavigationMaterialIcons() {
    // توحيد أيقونات التنقل بنمط Material Design
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href') || '';
        const icon = link.querySelector('i');

        if (icon) {
            // إزالة الفئات الحالية
            icon.className = '';
            icon.classList.add('material-icons-outlined');

            // إضافة الأيقونات Material حسب القسم
            if (href.includes('home') || href === '/') {
                icon.textContent = 'home';
                icon.style.color = '#4caf50';
            } else if (href.includes('customers')) {
                icon.textContent = 'people';
                icon.style.color = '#2196f3';
            } else if (href.includes('orders')) {
                icon.textContent = 'shopping_cart';
                icon.style.color = '#ff9800';
            } else if (href.includes('inventory')) {
                icon.textContent = 'inventory_2';
                icon.style.color = '#9c27b0';
            } else if (href.includes('inspections')) {
                icon.textContent = 'fact_check';
                icon.style.color = '#00bcd4';
            } else if (href.includes('installations')) {
                icon.textContent = 'build';
                icon.style.color = '#795548';
            } else if (href.includes('factory')) {
                icon.textContent = 'precision_manufacturing';
                icon.style.color = '#607d8b';
            } else if (href.includes('reports')) {
                icon.textContent = 'analytics';
                icon.style.color = '#e91e63';
            } else if (href.includes('database') || href.includes('data')) {
                icon.textContent = 'storage';
                icon.style.color = '#3f51b5';
            }

            // إضافة تأثيرات Material
            icon.style.fontSize = '20px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';
        }
    });
}

function applyActionMaterialIcons() {
    // توحيد أيقونات الإجراءات بنمط Material
    const actionButtons = document.querySelectorAll('.btn-link, .action-btn');

    actionButtons.forEach(button => {
        const icon = button.querySelector('i');
        const title = button.getAttribute('title') || '';
        const text = button.textContent.toLowerCase();

        if (icon) {
            // إزالة الفئات الحالية
            icon.className = '';
            icon.classList.add('material-icons-outlined');

            // إضافة الأيقونات Material حسب الوظيفة
            if (title.includes('عرض') || title.includes('تفاصيل') || text.includes('عرض')) {
                icon.textContent = 'visibility';
                button.classList.add('text-info');
            } else if (title.includes('تحميل') || title.includes('نسخة احتياطية') || text.includes('تحميل')) {
                icon.textContent = 'download';
                button.classList.add('text-success');
            } else if (title.includes('تعديل') || title.includes('تحرير') || text.includes('تعديل')) {
                icon.textContent = 'edit';
                button.classList.add('text-warning');
            } else if (title.includes('حذف') || text.includes('حذف')) {
                icon.textContent = 'delete';
                button.classList.add('text-danger');
            } else if (title.includes('تنشيط') || title.includes('تفعيل')) {
                icon.textContent = 'power_settings_new';
                button.classList.add('text-primary');
            } else if (title.includes('جدولة') || title.includes('وقت')) {
                icon.textContent = 'schedule';
                button.classList.add('text-warning');
            } else if (title.includes('إعدادات') || title.includes('ضبط')) {
                icon.textContent = 'settings';
                button.classList.add('text-info');
            } else if (title.includes('طباعة')) {
                icon.textContent = 'print';
                button.classList.add('text-secondary');
            } else if (title.includes('تصدير')) {
                icon.textContent = 'file_upload';
                button.classList.add('text-success');
            } else if (title.includes('استيراد')) {
                icon.textContent = 'file_download';
                button.classList.add('text-primary');
            } else if (title.includes('نسخ') || title.includes('copy')) {
                icon.textContent = 'content_copy';
                button.classList.add('text-info');
            } else if (title.includes('مشاركة') || title.includes('share')) {
                icon.textContent = 'share';
                button.classList.add('text-primary');
            } else if (title.includes('بحث') || title.includes('search')) {
                icon.textContent = 'search';
                button.classList.add('text-info');
            } else if (title.includes('تصفية') || title.includes('filter')) {
                icon.textContent = 'filter_list';
                button.classList.add('text-warning');
            } else if (title.includes('تحديث') || title.includes('refresh')) {
                icon.textContent = 'refresh';
                button.classList.add('text-info');
            } else if (title.includes('إضافة') || title.includes('add')) {
                icon.textContent = 'add';
                button.classList.add('text-success');
            } else if (title.includes('معلومات') || title.includes('info')) {
                icon.textContent = 'info';
                button.classList.add('text-info');
            } else if (title.includes('تحذير') || title.includes('warning')) {
                icon.textContent = 'warning';
                button.classList.add('text-warning');
            } else if (title.includes('نجاح') || title.includes('success')) {
                icon.textContent = 'check_circle';
                button.classList.add('text-success');
            } else if (title.includes('خطأ') || title.includes('error')) {
                icon.textContent = 'error';
                button.classList.add('text-danger');
            }

            // إضافة تأثيرات Material
            icon.style.fontSize = '18px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';
        }
    });
}

function applyTableMaterialIcons() {
    // توحيد أيقونات الجداول
    const tableIcons = document.querySelectorAll('table i, .table i');

    tableIcons.forEach(icon => {
        const parentButton = icon.closest('button, a, .btn-link');

        if (parentButton) {
            const buttonClass = parentButton.className;
            const title = parentButton.getAttribute('title') || '';
            const href = parentButton.getAttribute('href') || '';

            // إزالة الفئات الحالية
            icon.className = '';
            icon.classList.add('material-icons-outlined');

            // إضافة الأيقونات حسب نوع الزر أو العنوان أو الرابط
            if (buttonClass.includes('text-info') || title.includes('عرض') || title.includes('تفاصيل')) {
                icon.textContent = 'visibility';
            } else if (buttonClass.includes('text-success') || title.includes('تحميل') || title.includes('نسخة احتياطية')) {
                icon.textContent = 'download';
            } else if (buttonClass.includes('text-warning') || title.includes('جدولة') || title.includes('وقت') || title.includes('تعديل')) {
                if (title.includes('تعديل')) {
                    icon.textContent = 'edit';
                } else {
                    icon.textContent = 'schedule';
                }
            } else if (buttonClass.includes('text-danger') || title.includes('حذف')) {
                icon.textContent = 'delete';
            } else if (buttonClass.includes('text-primary') || title.includes('تنشيط') || title.includes('تفعيل')) {
                icon.textContent = 'power_settings_new';
            } else if (title.includes('إعدادات') || title.includes('ضبط')) {
                icon.textContent = 'settings';
            } else if (title.includes('طباعة')) {
                icon.textContent = 'print';
            } else if (title.includes('تصدير')) {
                icon.textContent = 'file_upload';
            } else if (title.includes('استيراد')) {
                icon.textContent = 'file_download';
            } else if (title.includes('نسخ')) {
                icon.textContent = 'content_copy';
            } else if (title.includes('مشاركة')) {
                icon.textContent = 'share';
            } else if (href.includes('edit') || href.includes('update')) {
                icon.textContent = 'edit';
                parentButton.classList.add('text-warning');
            } else if (href.includes('delete') || href.includes('remove')) {
                icon.textContent = 'delete';
                parentButton.classList.add('text-danger');
            } else if (href.includes('view') || href.includes('detail')) {
                icon.textContent = 'visibility';
                parentButton.classList.add('text-info');
            }

            // إضافة تأثيرات Material
            icon.style.fontSize = '18px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';
        }
    });

    // البحث عن أيقونات إضافية في خلايا الجداول
    const tableCells = document.querySelectorAll('td, th');
    tableCells.forEach(cell => {
        const icons = cell.querySelectorAll('i:not(.material-icons-outlined)');
        icons.forEach(icon => {
            const parentElement = icon.closest('button, a, .btn-link, .btn');
            if (parentElement) {
                const classes = icon.className;

                // تحويل أيقونات Font Awesome الشائعة إلى Material
                if (classes.includes('fa-eye')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'visibility';
                } else if (classes.includes('fa-edit')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'edit';
                } else if (classes.includes('fa-trash')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'delete';
                } else if (classes.includes('fa-download')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'download';
                } else if (classes.includes('fa-upload')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'upload';
                } else if (classes.includes('fa-cog') || classes.includes('fa-settings')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'settings';
                } else if (classes.includes('fa-power-off')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'power_settings_new';
                } else if (classes.includes('fa-clock')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'schedule';
                } else if (classes.includes('fa-print')) {
                    icon.className = 'material-icons-outlined';
                    icon.textContent = 'print';
                }

                icon.style.fontSize = '18px';
                icon.style.transition = 'all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';
            }
        });
    });
}

function applyButtonMaterialIcons() {
    // توحيد أيقونات الأزرار العامة
    const buttons = document.querySelectorAll('.btn');

    buttons.forEach(button => {
        const icon = button.querySelector('i');
        const text = button.textContent.toLowerCase();

        if (icon && text) {
            // إزالة الفئات الحالية
            icon.className = '';
            icon.classList.add('material-icons-outlined');

            // إضافة الأيقونات حسب النص
            if (text.includes('إضافة') || text.includes('جديد')) {
                icon.textContent = 'add';
            } else if (text.includes('حفظ')) {
                icon.textContent = 'save';
            } else if (text.includes('إلغاء')) {
                icon.textContent = 'close';
            } else if (text.includes('بحث')) {
                icon.textContent = 'search';
            } else if (text.includes('تصفية')) {
                icon.textContent = 'filter_list';
            } else if (text.includes('تحديث')) {
                icon.textContent = 'refresh';
            } else if (text.includes('رجوع')) {
                icon.textContent = 'arrow_back';
            } else if (text.includes('التالي')) {
                icon.textContent = 'arrow_forward';
            } else if (text.includes('تسجيل الدخول')) {
                icon.textContent = 'login';
            } else if (text.includes('تسجيل الخروج')) {
                icon.textContent = 'logout';
            } else if (text.includes('إرسال')) {
                icon.textContent = 'send';
            } else if (text.includes('تأكيد')) {
                icon.textContent = 'check';
            }

            // إضافة تأثيرات Material
            icon.style.fontSize = '18px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1)';
            icon.style.marginLeft = '8px';
        }
    });
}

function applyFormMaterialIcons() {
    // إضافة أيقونات للنماذج
    const formGroups = document.querySelectorAll('.form-group, .mb-3, .form-floating');

    formGroups.forEach(group => {
        const label = group.querySelector('label');
        const input = group.querySelector('input, select, textarea');

        if (label && input && !label.querySelector('.material-icons-outlined')) {
            const labelText = label.textContent.toLowerCase();
            const inputType = input.type || '';
            const inputName = input.name || '';
            const inputId = input.id || '';
            let iconText = '';

            // تحديد الأيقونة حسب النص أو نوع الحقل
            if (labelText.includes('اسم') || labelText.includes('name') || inputName.includes('name')) {
                iconText = 'person';
            } else if (labelText.includes('بريد') || labelText.includes('email') || inputType === 'email') {
                iconText = 'email';
            } else if (labelText.includes('هاتف') || labelText.includes('phone') || inputType === 'tel') {
                iconText = 'phone';
            } else if (labelText.includes('عنوان') || labelText.includes('address')) {
                iconText = 'location_on';
            } else if (labelText.includes('تاريخ') || labelText.includes('date') || inputType === 'date') {
                iconText = 'event';
            } else if (labelText.includes('وقت') || labelText.includes('time') || inputType === 'time') {
                iconText = 'access_time';
            } else if (labelText.includes('كلمة المرور') || labelText.includes('password') || inputType === 'password') {
                iconText = 'lock';
            } else if (labelText.includes('بحث') || labelText.includes('search') || inputType === 'search') {
                iconText = 'search';
            } else if (labelText.includes('ملف') || labelText.includes('file') || inputType === 'file') {
                iconText = 'attach_file';
            } else if (labelText.includes('صورة') || labelText.includes('image')) {
                iconText = 'image';
            } else if (labelText.includes('رقم') || labelText.includes('number') || inputType === 'number') {
                iconText = 'tag';
            } else if (labelText.includes('مبلغ') || labelText.includes('سعر') || labelText.includes('price')) {
                iconText = 'attach_money';
            } else if (labelText.includes('وصف') || labelText.includes('description') || input.tagName === 'TEXTAREA') {
                iconText = 'description';
            } else if (labelText.includes('فئة') || labelText.includes('category') || input.tagName === 'SELECT') {
                iconText = 'category';
            } else if (labelText.includes('حالة') || labelText.includes('status')) {
                iconText = 'info';
            } else if (labelText.includes('موقع') || labelText.includes('location')) {
                iconText = 'place';
            } else if (labelText.includes('شركة') || labelText.includes('company')) {
                iconText = 'business';
            } else if (labelText.includes('مدينة') || labelText.includes('city')) {
                iconText = 'location_city';
            } else if (labelText.includes('دولة') || labelText.includes('country')) {
                iconText = 'public';
            } else if (labelText.includes('رمز') || labelText.includes('code')) {
                iconText = 'qr_code';
            } else if (labelText.includes('ملاحظات') || labelText.includes('notes')) {
                iconText = 'note';
            } else if (labelText.includes('كمية') || labelText.includes('quantity')) {
                iconText = 'inventory';
            } else if (labelText.includes('وزن') || labelText.includes('weight')) {
                iconText = 'scale';
            } else if (labelText.includes('طول') || labelText.includes('عرض') || labelText.includes('ارتفاع')) {
                iconText = 'straighten';
            }

            if (iconText) {
                const icon = document.createElement('i');
                icon.className = 'material-icons-outlined';
                icon.textContent = iconText;
                icon.style.fontSize = '16px';
                icon.style.marginLeft = '8px';
                icon.style.color = '#757575';
                icon.style.verticalAlign = 'middle';

                label.insertBefore(icon, label.firstChild);
            }
        }
    });

    // تطبيق أيقونات على الأزرار في النماذج
    const formButtons = document.querySelectorAll('form .btn, form button');
    formButtons.forEach(button => {
        const icon = button.querySelector('i:not(.material-icons-outlined)');
        const text = button.textContent.toLowerCase();

        if (icon) {
            const classes = icon.className;

            // تحويل أيقونات Font Awesome إلى Material
            if (classes.includes('fa-save')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'save';
            } else if (classes.includes('fa-plus')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'add';
            } else if (classes.includes('fa-times')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'close';
            } else if (classes.includes('fa-search')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'search';
            } else if (classes.includes('fa-filter')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'filter_list';
            } else if (classes.includes('fa-refresh') || classes.includes('fa-sync')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'refresh';
            } else if (classes.includes('fa-arrow-left')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'arrow_back';
            } else if (classes.includes('fa-arrow-right')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'arrow_forward';
            } else if (classes.includes('fa-check')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'check';
            } else if (classes.includes('fa-send')) {
                icon.className = 'material-icons-outlined';
                icon.textContent = 'send';
            }

            icon.style.fontSize = '18px';
            icon.style.marginLeft = '8px';
        }
    });
}

function addMaterialAnimations() {
    // إضافة تأثيرات الحركة Material
    const allIcons = document.querySelectorAll('.material-icons-outlined');

    allIcons.forEach(icon => {
        const parentElement = icon.parentElement;

        // إضافة تأثير hover
        parentElement.addEventListener('mouseenter', function() {
            icon.style.transform = 'scale(1.1)';
        });

        parentElement.addEventListener('mouseleave', function() {
            icon.style.transform = 'scale(1)';
        });

        // إضافة تأثير النقر (Ripple Effect)
        parentElement.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = parentElement.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
                z-index: 1000;
            `;

            parentElement.style.position = 'relative';
            parentElement.style.overflow = 'hidden';
            parentElement.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });

    // إضافة CSS للرسوم المتحركة
    if (!document.getElementById('material-animations')) {
        const style = document.createElement('style');
        style.id = 'material-animations';
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }

            .material-icons-outlined {
                font-family: 'Material Icons Outlined';
                font-weight: normal;
                font-style: normal;
                font-size: 24px;
                line-height: 1;
                letter-spacing: normal;
                text-transform: none;
                display: inline-block;
                white-space: nowrap;
                word-wrap: normal;
                direction: ltr;
                -webkit-font-feature-settings: 'liga';
                -webkit-font-smoothing: antialiased;
            }
        `;
        document.head.appendChild(style);
    }
}

// تصدير الوظائف للاستخدام الخارجي
window.GoogleMaterialIcons = {
    apply: applyMaterialIcons,
    navigation: applyNavigationMaterialIcons,
    actions: applyActionMaterialIcons,
    tables: applyTableMaterialIcons,
    buttons: applyButtonMaterialIcons,
    forms: applyFormMaterialIcons,
    animations: addMaterialAnimations
};
