/**
 * إصلاح شامل لجميع القوائم المنسدلة في تطبيق المصنع
 * يطبق نفس منطق قوائم خطوط الإنتاج على جميع القوائم
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('تحميل universal-dropdown-fix.js');
    
    // إصلاح جميع أنواع القوائم المنسدلة
    fixAllDropdowns();
    
    // مراقبة إضافة عناصر جديدة
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        fixAllDropdowns();
                    }
                });
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

function fixAllDropdowns() {
    // إصلاح القوائم المخصصة (الفلاتر)
    fixCustomDropdowns();
    
    // إصلاح قوائم خطوط الإنتاج
    fixProductionLineDropdowns();
    
    // إصلاح Bootstrap dropdowns
    fixBootstrapDropdowns();
}

function fixCustomDropdowns() {
    // البحث عن جميع الأزرار التي تنتهي بـ DropdownBtn
    const buttons = document.querySelectorAll('[id$="DropdownBtn"]');

    buttons.forEach(button => {
        if (!button.hasAttribute('data-dropdown-fixed')) {
            button.setAttribute('data-dropdown-fixed', 'true');

            // استخراج اسم القائمة من اسم الزر
            const menuId = button.id.replace('Btn', '');
            const menu = document.getElementById(menuId);

            if (menu) {
                // نقل القائمة إلى body - نفس منطق قائمة المستخدم تماماً
                console.log('نقل القائمة إلى body:', menuId);
                document.body.appendChild(menu);

                // تغيير position إلى fixed
                menu.style.position = 'fixed';
                menu.style.top = 'auto';
                menu.style.left = 'auto';

                // إضافة event listener للزر
                button.addEventListener('click', function(e) {
                    e.stopPropagation();

                    // إغلاق جميع القوائم الأخرى
                    closeAllCustomDropdowns();

                    // تبديل القائمة الحالية
                    if (menu.style.display === 'block') {
                        menu.style.display = 'none';
                    } else {
                        menu.style.display = 'block';

                        // حساب موقع القائمة - نفس منطق قائمة المستخدم
                        positionDropdownMenu(button, menu);
                    }
                });

                // منع إغلاق القائمة عند النقر داخلها
                menu.addEventListener('click', function(e) {
                    e.stopPropagation();
                });

                // تحديث نص الزر عند تغيير الاختيارات
                const checkboxes = menu.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    checkbox.addEventListener('change', function() {
                        updateDropdownButtonText(button, menu);
                    });
                });

                // تحديث النص عند التحميل
                updateDropdownButtonText(button, menu);

                console.log('تم إصلاح القائمة المخصصة:', menuId);
            }
        }
    });
}

function fixProductionLineDropdowns() {
    // البحث عن جميع أزرار قوائم خطوط الإنتاج
    const buttons = document.querySelectorAll('[id^="productionLineBtn_"]');

    buttons.forEach(button => {
        if (!button.hasAttribute('data-dropdown-fixed')) {
            button.setAttribute('data-dropdown-fixed', 'true');

            const lineId = button.id.replace('productionLineBtn_', '');
            const menu = document.getElementById('productionLineMenu_' + lineId);

            if (menu) {
                // إبقاء قوائم خطوط الإنتاج كما هي (position: absolute) لأنها تعمل بشكل صحيح
                console.log('تهيئة قائمة خط الإنتاج:', lineId);

                // إضافة event listener للزر
                button.addEventListener('click', function(e) {
                    e.stopPropagation();

                    // إغلاق جميع القوائم الأخرى
                    closeAllProductionLineDropdowns();

                    // تبديل القائمة الحالية
                    if (menu.style.display === 'block') {
                        menu.style.display = 'none';
                    } else {
                        menu.style.display = 'block';
                    }
                });

                // منع إغلاق القائمة عند النقر داخلها
                menu.addEventListener('click', function(e) {
                    e.stopPropagation();
                });

                // إضافة تأثير hover للعناصر
                const dropdownItems = menu.querySelectorAll('.dropdown-item');
                dropdownItems.forEach(item => {
                    item.addEventListener('mouseenter', function() {
                        this.style.backgroundColor = '#f8f9fa';
                    });

                    item.addEventListener('mouseleave', function() {
                        this.style.backgroundColor = 'transparent';
                    });

                    // إغلاق القائمة عند النقر على الرابط
                    item.addEventListener('click', function() {
                        closeAllProductionLineDropdowns();
                    });
                });

                console.log('تم إصلاح قائمة خط الإنتاج:', lineId);
            }
        }
    });
}

function fixBootstrapDropdowns() {
    // البحث عن جميع Bootstrap dropdowns
    const dropdowns = document.querySelectorAll('[data-bs-toggle="dropdown"]');
    
    dropdowns.forEach(dropdown => {
        if (!dropdown.hasAttribute('data-dropdown-fixed')) {
            dropdown.setAttribute('data-dropdown-fixed', 'true');
            
            // التأكد من أن الحاوي له position: relative
            const container = dropdown.closest('.dropdown');
            if (container && !container.classList.contains('position-relative')) {
                container.classList.add('position-relative');
            }
            
            console.log('تم إصلاح Bootstrap dropdown:', dropdown);
        }
    });
}

function closeAllCustomDropdowns() {
    const menus = document.querySelectorAll('[id$="Dropdown"]');
    menus.forEach(menu => {
        menu.style.display = 'none';
    });
}

function closeAllProductionLineDropdowns() {
    const menus = document.querySelectorAll('[id^="productionLineMenu_"]');
    menus.forEach(menu => {
        menu.style.display = 'none';
    });
}

function positionDropdownMenu(button, menu) {
    // حساب موقع الزر - نفس منطق قائمة المستخدم بالضبط
    const rect = button.getBoundingClientRect();

    // الموقع البسيط: أسفل الزر مباشرة
    const top = rect.bottom + 2; // 2px مسافة صغيرة
    const left = rect.left;

    // تطبيق الموقع
    menu.style.top = top + 'px';
    menu.style.left = left + 'px';
    menu.style.minWidth = Math.max(rect.width, 180) + 'px';

    console.log('موقع الزر:', rect);
    console.log('موقع القائمة:', { top, left });
}

function updateDropdownButtonText(button, menu) {
    const selectedText = button.querySelector('.selected-text');
    if (!selectedText) return;

    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');

    if (checkboxes.length === 0) {
        // تحديد النص الافتراضي حسب نوع القائمة
        if (button.id.includes('status')) {
            selectedText.textContent = 'اختر الحالات';
        } else if (button.id.includes('branch')) {
            selectedText.textContent = 'اختر الفروع';
        } else if (button.id.includes('orderType')) {
            selectedText.textContent = 'اختر الأنواع';
        } else if (button.id.includes('productionLine')) {
            selectedText.textContent = 'اختر خطوط الإنتاج';
        } else {
            selectedText.textContent = 'اختر العناصر';
        }
    } else if (checkboxes.length === 1) {
        // عرض النص للعنصر المختار
        const label = checkboxes[0].parentElement;
        selectedText.textContent = label.textContent.trim();
    } else {
        // عرض عدد العناصر المختارة
        selectedText.textContent = `تم اختيار ${checkboxes.length} عنصر`;
    }
}

function closeAllDropdowns() {
    closeAllCustomDropdowns();
    closeAllProductionLineDropdowns();
}

// إغلاق القوائم عند النقر خارجها
document.addEventListener('click', function(e) {
    if (!e.target.closest('[id$="DropdownBtn"]') && 
        !e.target.closest('[id$="Dropdown"]') &&
        !e.target.closest('[id^="productionLineBtn_"]') && 
        !e.target.closest('[id^="productionLineMenu_"]')) {
        closeAllDropdowns();
    }
});

// إغلاق القوائم عند الضغط على Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAllDropdowns();
    }
});

// تصدير الدوال للاستخدام الخارجي
window.UniversalDropdownFix = {
    fixAll: fixAllDropdowns,
    fixCustom: fixCustomDropdowns,
    fixProductionLine: fixProductionLineDropdowns,
    fixBootstrap: fixBootstrapDropdowns,
    closeAll: closeAllDropdowns
};
