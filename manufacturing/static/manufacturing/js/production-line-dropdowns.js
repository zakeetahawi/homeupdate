/**
 * قوائم خطوط الإنتاج المخصصة - نفس منطق قائمة المستخدم تماماً
 * مخصصة بالكامل + نقل إلى body + بدون Bootstrap dropdown
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('تحميل production-line-dropdowns.js');
    
    // تهيئة جميع قوائم خطوط الإنتاج
    initProductionLineDropdowns();
    
    // مراقبة إضافة عناصر جديدة (للمحتوى الديناميكي)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        const newButtons = node.querySelectorAll('[id^="productionLineBtn_"]');
                        if (newButtons.length > 0) {
                            initProductionLineDropdowns();
                        }
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

function initProductionLineDropdowns() {
    // البحث عن جميع أزرار قوائم خطوط الإنتاج
    const buttons = document.querySelectorAll('[id^="productionLineBtn_"]');
    
    buttons.forEach(button => {
        // التحقق من أن الزر لم يتم تهيئته مسبقاً
        if (!button.hasAttribute('data-dropdown-initialized')) {
            
            // إضافة علامة لتجنب التهيئة المتكررة
            button.setAttribute('data-dropdown-initialized', 'true');
            
            // استخراج ID خط الإنتاج من ID الزر
            const lineId = button.id.replace('productionLineBtn_', '');
            const menu = document.getElementById('productionLineMenu_' + lineId);
            
            if (menu) {
                // لا نحتاج لنقل القائمة - ستبقى داخل الـ container مع position: absolute
                console.log('تهيئة القائمة:', menu);

                // إضافة event listener للزر
                button.addEventListener('click', function(e) {
                    e.stopPropagation();

                    console.log('تم النقر على زر خط الإنتاج:', lineId);
                    console.log('الزر:', button);
                    console.log('القائمة:', menu);

                    // إغلاق جميع القوائم الأخرى
                    closeAllProductionLineDropdowns();

                    // تبديل القائمة الحالية - نفس منطق قائمة المستخدم
                    if (menu.style.display === 'block') {
                        menu.style.display = 'none';
                        console.log('إغلاق القائمة');
                    } else {
                        menu.style.display = 'block';
                        console.log('فتح القائمة');

                        // القائمة ستظهر تلقائياً أسفل الزر بسبب position: absolute و top: 100%
                        console.log('فتح القائمة - ستظهر أسفل الزر تلقائياً');
                    }
                });
                
                // منع إغلاق القائمة عند النقر داخلها - نفس منطق قائمة المستخدم
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
                
                console.log('تم تهيئة قائمة خط الإنتاج:', lineId);
            }
        }
    });
    
    // إضافة event listener لإغلاق القوائم عند النقر خارجها - نفس منطق قائمة المستخدم
    document.addEventListener('click', function(e) {
        // التحقق من أن النقر ليس على زر أو قائمة
        if (!e.target.closest('[id^="productionLineBtn_"]') && 
            !e.target.closest('[id^="productionLineMenu_"]')) {
            closeAllProductionLineDropdowns();
        }
    });
}

// لا نحتاج لدالة positionDropdownMenu لأن CSS سيتولى الأمر

function closeAllProductionLineDropdowns() {
    // إغلاق جميع قوائم خطوط الإنتاج
    const menus = document.querySelectorAll('[id^="productionLineMenu_"]');
    menus.forEach(menu => {
        menu.style.display = 'none';
    });
}

// إغلاق القوائم عند الضغط على Escape - نفس منطق قائمة المستخدم
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAllProductionLineDropdowns();
    }
});

// لا نحتاج لإغلاق القوائم عند التمرير لأن position: absolute سيحافظ على الموقع النسبي



// تصدير الدوال للاستخدام الخارجي
window.initProductionLineDropdowns = initProductionLineDropdowns;
window.closeAllProductionLineDropdowns = closeAllProductionLineDropdowns;
