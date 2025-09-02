/**
 * Apple Dark Mode Icons System
 * نظام أيقونات الوضع الليلي بنمط Apple
 */

document.addEventListener('DOMContentLoaded', function() {
    // تطبيق الأيقونات عند تحميل الصفحة
    applyAppleIcons();

    // مراقبة تغيير الثيم
    const themeSelector = document.getElementById('themeSelector');
    if (themeSelector) {
        themeSelector.addEventListener('change', function() {
            setTimeout(applyAppleIcons, 100);
        });
    }

    // مراقبة التغييرات في DOM لتطبيق الأيقونات على العناصر الجديدة
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                setTimeout(applyAppleIcons, 50);
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // إعادة تطبيق الأيقونات عند تحميل محتوى جديد عبر AJAX
    document.addEventListener('ajaxComplete', function() {
        setTimeout(applyAppleIcons, 100);
    });
});

function applyAppleIcons() {
    const currentTheme = document.body.getAttribute('data-theme');

    // تطبيق الأيقونات فقط للثيم Apple Dark Mode
    if (currentTheme === 'apple-dark-mode') {
        applyNavigationAppleIcons();
        applyActionAppleIcons();
        applyTableAppleIcons();
        applyButtonAppleIcons();
        applyFormAppleIcons();
        applyNotificationIcons();
        addAppleAnimations();
    } else {
        // إعادة الأيقونات إلى Font Awesome عند تغيير الثيم
        revertToFontAwesome();
    }
}

function revertToFontAwesome() {
    // إعادة جميع الأيقونات إلى Font Awesome
    const allIcons = document.querySelectorAll('.apple-icon');
    allIcons.forEach(icon => {
        // استعادة الأيقونة الأصلية من data attribute
        const originalIcon = icon.getAttribute('data-original-icon');
        if (originalIcon) {
            icon.className = originalIcon;
            icon.textContent = '';
            icon.style.fontSize = '';
            icon.style.color = '';
        }
        icon.classList.remove('apple-icon');
    });
}

function applyNavigationAppleIcons() {
    // توحيد أيقونات التنقل بنمط Apple
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href') || '';
        const icon = link.querySelector('i');

        if (icon && !icon.classList.contains('apple-icon')) {
            // حفظ الأيقونة الأصلية
            icon.setAttribute('data-original-icon', icon.className);

            // إزالة الفئات الحالية وإضافة فئة Apple
            icon.className = 'apple-icon';

            // إضافة الأيقونات بنمط Apple حسب القسم
            if (href.includes('home') || href === '/') {
                icon.innerHTML = '🏠';
                icon.style.color = '#30d158';
            } else if (href.includes('customers')) {
                icon.innerHTML = '👥';
                icon.style.color = '#007aff';
            } else if (href.includes('orders')) {
                icon.innerHTML = '🛒';
                icon.style.color = '#ff9500';
            } else if (href.includes('inventory')) {
                icon.innerHTML = '📦';
                icon.style.color = '#bf5af2';
            } else if (href.includes('inspections')) {
                icon.innerHTML = '✅';
                icon.style.color = '#5ac8fa';
            } else if (href.includes('installations')) {
                icon.innerHTML = '🔧';
                icon.style.color = '#ffcc02';
            } else if (href.includes('factory')) {
                icon.innerHTML = '🏭';
                icon.style.color = '#ff6482';
            } else if (href.includes('reports')) {
                icon.innerHTML = '📊';
                icon.style.color = '#64d2ff';
            } else if (href.includes('database') || href.includes('data')) {
                icon.innerHTML = '💾';
                icon.style.color = '#a28bfe';
            }

            // إضافة تأثيرات Apple
            icon.style.fontSize = '14px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)';
            icon.style.display = 'inline-block';
        }
    });
}

function applyActionAppleIcons() {
    // توحيد أيقونات الإجراءات بنمط Apple
    const actionButtons = document.querySelectorAll('.btn-link, .action-btn');

    actionButtons.forEach(button => {
        const icon = button.querySelector('i');
        const title = button.getAttribute('title') || '';
        const text = button.textContent.toLowerCase();

        if (icon && !icon.classList.contains('apple-icon')) {
            // حفظ الأيقونة الأصلية
            icon.setAttribute('data-original-icon', icon.className);

            // إزالة الفئات الحالية
            icon.className = 'apple-icon';

            // إضافة الأيقونات بنمط Apple حسب الوظيفة
            if (title.includes('عرض') || title.includes('تفاصيل') || text.includes('عرض')) {
                icon.innerHTML = '👁️';
                button.classList.add('text-info');
            } else if (title.includes('تحميل') || title.includes('نسخة احتياطية') || text.includes('تحميل')) {
                icon.innerHTML = '⬇️';
                button.classList.add('text-success');
            } else if (title.includes('تعديل') || title.includes('تحرير') || text.includes('تعديل')) {
                icon.innerHTML = '✏️';
                button.classList.add('text-warning');
            } else if (title.includes('حذف') || text.includes('حذف')) {
                icon.innerHTML = '🗑️';
                button.classList.add('text-danger');
            } else if (title.includes('تنشيط') || title.includes('تفعيل')) {
                icon.innerHTML = '⚡';
                button.classList.add('text-primary');
            } else if (title.includes('جدولة') || title.includes('وقت')) {
                icon.innerHTML = '⏰';
                button.classList.add('text-warning');
            } else if (title.includes('إعدادات') || title.includes('ضبط')) {
                icon.innerHTML = '⚙️';
                button.classList.add('text-info');
            } else if (title.includes('طباعة')) {
                icon.innerHTML = '🖨️';
                button.classList.add('text-secondary');
            } else if (title.includes('تصدير')) {
                icon.innerHTML = '📤';
                button.classList.add('text-success');
            } else if (title.includes('استيراد')) {
                icon.innerHTML = '📥';
                button.classList.add('text-primary');
            } else if (title.includes('نسخ')) {
                icon.innerHTML = '📋';
                button.classList.add('text-info');
            } else if (title.includes('مشاركة')) {
                icon.innerHTML = '📤';
                button.classList.add('text-primary');
            } else if (title.includes('بحث')) {
                icon.innerHTML = '🔍';
                button.classList.add('text-info');
            } else if (title.includes('تصفية')) {
                icon.innerHTML = '🔽';
                button.classList.add('text-warning');
            } else if (title.includes('تحديث')) {
                icon.innerHTML = '🔄';
                button.classList.add('text-info');
            } else if (title.includes('إضافة')) {
                icon.innerHTML = '➕';
                button.classList.add('text-success');
            } else if (title.includes('معلومات')) {
                icon.innerHTML = 'ℹ️';
                button.classList.add('text-info');
            } else if (title.includes('تحذير')) {
                icon.innerHTML = '⚠️';
                button.classList.add('text-warning');
            } else if (title.includes('نجاح')) {
                icon.innerHTML = '✅';
                button.classList.add('text-success');
            } else if (title.includes('خطأ')) {
                icon.innerHTML = '❌';
                button.classList.add('text-danger');
            }

            // إضافة تأثيرات Apple
            icon.style.fontSize = '12px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)';
            icon.style.display = 'inline-block';
        }
    });
}

function applyTableAppleIcons() {
    // توحيد أيقونات الجداول
    const tableIcons = document.querySelectorAll('table i, .table i');

    tableIcons.forEach(icon => {
        const parentButton = icon.closest('button, a, .btn-link');

        if (parentButton && !icon.classList.contains('apple-icon')) {
            const buttonClass = parentButton.className;
            const title = parentButton.getAttribute('title') || '';
            const href = parentButton.getAttribute('href') || '';

            // حفظ الأيقونة الأصلية
            icon.setAttribute('data-original-icon', icon.className);

            // إزالة الفئات الحالية
            icon.className = 'apple-icon';

            // إضافة الأيقونات حسب نوع الزر
            if (buttonClass.includes('text-info') || title.includes('عرض') || title.includes('تفاصيل')) {
                icon.innerHTML = '👁️';
            } else if (buttonClass.includes('text-success') || title.includes('تحميل') || title.includes('نسخة احتياطية')) {
                icon.innerHTML = '⬇️';
            } else if (buttonClass.includes('text-warning') || title.includes('جدولة') || title.includes('وقت') || title.includes('تعديل')) {
                if (title.includes('تعديل')) {
                    icon.innerHTML = '✏️';
                } else {
                    icon.innerHTML = '⏰';
                }
            } else if (buttonClass.includes('text-danger') || title.includes('حذف')) {
                icon.innerHTML = '🗑️';
            } else if (buttonClass.includes('text-primary') || title.includes('تنشيط') || title.includes('تفعيل')) {
                icon.innerHTML = '⚡';
            } else if (title.includes('إعدادات')) {
                icon.innerHTML = '⚙️';
            } else if (title.includes('طباعة')) {
                icon.innerHTML = '🖨️';
            } else if (href.includes('edit') || href.includes('update')) {
                icon.innerHTML = '✏️';
                parentButton.classList.add('text-warning');
            } else if (href.includes('delete') || href.includes('remove')) {
                icon.innerHTML = '🗑️';
                parentButton.classList.add('text-danger');
            } else if (href.includes('view') || href.includes('detail')) {
                icon.innerHTML = '👁️';
                parentButton.classList.add('text-info');
            }

            // إضافة تأثيرات Apple
            icon.style.fontSize = '12px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)';
            icon.style.display = 'inline-block';
        }
    });
}

function applyButtonAppleIcons() {
    // توحيد أيقونات الأزرار العامة
    const buttons = document.querySelectorAll('.btn');

    buttons.forEach(button => {
        const icon = button.querySelector('i');
        const text = button.textContent.toLowerCase();

        if (icon && text && !icon.classList.contains('apple-icon')) {
            // حفظ الأيقونة الأصلية
            icon.setAttribute('data-original-icon', icon.className);

            // إزالة الفئات الحالية
            icon.className = 'apple-icon';

            // إضافة الأيقونات حسب النص
            if (text.includes('إضافة') || text.includes('جديد')) {
                icon.innerHTML = '➕';
            } else if (text.includes('حفظ')) {
                icon.innerHTML = '💾';
            } else if (text.includes('إلغاء')) {
                icon.innerHTML = '❌';
            } else if (text.includes('بحث')) {
                icon.innerHTML = '🔍';
            } else if (text.includes('تصفية')) {
                icon.innerHTML = '🔽';
            } else if (text.includes('تحديث')) {
                icon.innerHTML = '🔄';
            } else if (text.includes('رجوع')) {
                icon.innerHTML = '⬅️';
            } else if (text.includes('التالي')) {
                icon.innerHTML = '➡️';
            } else if (text.includes('تسجيل الدخول')) {
                icon.innerHTML = '🔐';
            } else if (text.includes('تسجيل الخروج')) {
                icon.innerHTML = '🚪';
            } else if (text.includes('إرسال')) {
                icon.innerHTML = '📤';
            } else if (text.includes('تأكيد')) {
                icon.innerHTML = '✅';
            }

            // إضافة تأثيرات Apple
            icon.style.fontSize = '12px';
            icon.style.transition = 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)';
            icon.style.marginLeft = '6px';
            icon.style.display = 'inline-block';
        }
    });
}

function applyFormAppleIcons() {
    // إضافة أيقونات للنماذج بنمط Apple
    const formGroups = document.querySelectorAll('.form-group, .mb-3, .form-floating');

    formGroups.forEach(group => {
        const label = group.querySelector('label');
        const input = group.querySelector('input, select, textarea');

        if (label && input && !label.querySelector('.apple-icon')) {
            const labelText = label.textContent.toLowerCase();
            const inputType = input.type || '';
            const inputName = input.name || '';
            let iconEmoji = '';

            // تحديد الأيقونة حسب النص أو نوع الحقل
            if (labelText.includes('اسم') || labelText.includes('name') || inputName.includes('name')) {
                iconEmoji = '👤';
            } else if (labelText.includes('بريد') || labelText.includes('email') || inputType === 'email') {
                iconEmoji = '📧';
            } else if (labelText.includes('هاتف') || labelText.includes('phone') || inputType === 'tel') {
                iconEmoji = '📱';
            } else if (labelText.includes('عنوان') || labelText.includes('address')) {
                iconEmoji = '📍';
            } else if (labelText.includes('تاريخ') || labelText.includes('date') || inputType === 'date') {
                iconEmoji = '📅';
            } else if (labelText.includes('وقت') || labelText.includes('time') || inputType === 'time') {
                iconEmoji = '⏰';
            } else if (labelText.includes('كلمة المرور') || labelText.includes('password') || inputType === 'password') {
                iconEmoji = '🔒';
            } else if (labelText.includes('بحث') || labelText.includes('search') || inputType === 'search') {
                iconEmoji = '🔍';
            } else if (labelText.includes('ملف') || labelText.includes('file') || inputType === 'file') {
                iconEmoji = '📎';
            } else if (labelText.includes('صورة') || labelText.includes('image')) {
                iconEmoji = '🖼️';
            } else if (labelText.includes('رقم') || labelText.includes('number') || inputType === 'number') {
                iconEmoji = '🔢';
            } else if (labelText.includes('مبلغ') || labelText.includes('سعر') || labelText.includes('price')) {
                iconEmoji = '💰';
            } else if (labelText.includes('وصف') || labelText.includes('description') || input.tagName === 'TEXTAREA') {
                iconEmoji = '📝';
            } else if (labelText.includes('فئة') || labelText.includes('category') || input.tagName === 'SELECT') {
                iconEmoji = '📂';
            } else if (labelText.includes('حالة') || labelText.includes('status')) {
                iconEmoji = 'ℹ️';
            } else if (labelText.includes('موقع') || labelText.includes('location')) {
                iconEmoji = '🗺️';
            } else if (labelText.includes('شركة') || labelText.includes('company')) {
                iconEmoji = '🏢';
            } else if (labelText.includes('مدينة') || labelText.includes('city')) {
                iconEmoji = '🏙️';
            } else if (labelText.includes('دولة') || labelText.includes('country')) {
                iconEmoji = '🌍';
            } else if (labelText.includes('رمز') || labelText.includes('code')) {
                iconEmoji = '🔐';
            } else if (labelText.includes('ملاحظات') || labelText.includes('notes')) {
                iconEmoji = '📋';
            } else if (labelText.includes('كمية') || labelText.includes('quantity')) {
                iconEmoji = '📦';
            } else if (labelText.includes('وزن') || labelText.includes('weight')) {
                iconEmoji = '⚖️';
            } else if (labelText.includes('طول') || labelText.includes('عرض') || labelText.includes('ارتفاع')) {
                iconEmoji = '📏';
            }

            if (iconEmoji) {
                const icon = document.createElement('span');
                icon.className = 'apple-icon';
                icon.innerHTML = iconEmoji;
                icon.style.fontSize = '12px';
                icon.style.marginLeft = '6px';
                icon.style.display = 'inline-block';
                icon.style.verticalAlign = 'middle';

                label.insertBefore(icon, label.firstChild);
            }
        }
    });
}

function applyNotificationIcons() {
    // تم تعطيل تدخل Apple Icons في أيقونات الإشعارات
    // لتجنب التضارب مع نظام الإشعارات المخصص

    // تطبيق أيقونات خاصة لزر الإشعارات وعناصر الهيدر - معطل
    // const notificationButton = document.querySelector('[data-bs-toggle="dropdown"][aria-expanded]');
    // if (notificationButton && !notificationButton.querySelector('.apple-icon')) {
    //     const icon = notificationButton.querySelector('i');
    //     if (icon) {
    //         icon.setAttribute('data-original-icon', icon.className);
    //         icon.className = 'apple-icon';
    //         icon.innerHTML = '🔔';
    //         icon.style.fontSize = '16px';
    //         icon.style.color = '#ff9500';
    //         icon.style.transition = 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)';
    //     }
    // }

    // أيقونات القائمة المنسدلة للمستخدم
    const userDropdownItems = document.querySelectorAll('.dropdown-item');
    userDropdownItems.forEach(item => {
        const icon = item.querySelector('i');
        const text = item.textContent.toLowerCase();

        if (icon && !icon.classList.contains('apple-icon')) {
            icon.setAttribute('data-original-icon', icon.className);
            icon.className = 'apple-icon';

            if (text.includes('ملف') || text.includes('profile')) {
                icon.innerHTML = '👤';
            } else if (text.includes('إعدادات') || text.includes('settings')) {
                icon.innerHTML = '⚙️';
            } else if (text.includes('خروج') || text.includes('logout')) {
                icon.innerHTML = '🚪';
            } else if (text.includes('لوحة') || text.includes('admin')) {
                icon.innerHTML = '🛠️';
            }

            icon.style.fontSize = '14px';
            icon.style.display = 'inline-block';
        }
    });

    // أيقونات الإشعارات والتنبيهات
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (!alert.querySelector('.apple-icon')) {
            let iconEmoji = '';

            if (alert.classList.contains('alert-success')) {
                iconEmoji = '✅';
            } else if (alert.classList.contains('alert-danger')) {
                iconEmoji = '❌';
            } else if (alert.classList.contains('alert-warning')) {
                iconEmoji = '⚠️';
            } else if (alert.classList.contains('alert-info')) {
                iconEmoji = 'ℹ️';
            }

            if (iconEmoji) {
                const icon = document.createElement('span');
                icon.className = 'apple-icon';
                icon.innerHTML = iconEmoji;
                icon.style.fontSize = '16px';
                icon.style.marginLeft = '8px';
                icon.style.display = 'inline-block';
                icon.style.verticalAlign = 'middle';

                alert.insertBefore(icon, alert.firstChild);
            }
        }
    });
}

function addAppleAnimations() {
    // إضافة تأثيرات الحركة بنمط Apple
    const allAppleIcons = document.querySelectorAll('.apple-icon');

    allAppleIcons.forEach(icon => {
        const parentElement = icon.parentElement;

        // إضافة تأثير hover
        parentElement.addEventListener('mouseenter', function() {
            icon.style.transform = 'scale(1.1)';
            icon.style.filter = 'brightness(1.2)';
        });

        parentElement.addEventListener('mouseleave', function() {
            icon.style.transform = 'scale(1)';
            icon.style.filter = 'brightness(1)';
        });

        // إضافة تأثير النقر بنمط Apple
        parentElement.addEventListener('mousedown', function() {
            icon.style.transform = 'scale(0.9)';
        });

        parentElement.addEventListener('mouseup', function() {
            icon.style.transform = 'scale(1.1)';
            setTimeout(() => {
                icon.style.transform = 'scale(1)';
            }, 100);
        });

        // تأثير النبض للإشعارات
        if (icon.innerHTML === '🔔') {
            setInterval(() => {
                icon.style.transform = 'scale(1.1)';
                setTimeout(() => {
                    icon.style.transform = 'scale(1)';
                }, 200);
            }, 3000);
        }
    });
}

// تصدير الوظائف للاستخدام الخارجي
window.AppleDarkIcons = {
    apply: applyAppleIcons,
    navigation: applyNavigationAppleIcons,
    actions: applyActionAppleIcons,
    tables: applyTableAppleIcons,
    buttons: applyButtonAppleIcons,
    forms: applyFormAppleIcons,
    notifications: applyNotificationIcons,
    animations: addAppleAnimations,
    revert: revertToFontAwesome
};
