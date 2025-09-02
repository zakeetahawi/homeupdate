/**
 * إصلاح مشكلة Bootstrap dropdown مع stacking context
 * الحل الصحيح: نقل القوائم إلى body لتجنب مشاكل position: relative في البطاقات
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('تحميل bootstrap-dropdown-fix.js');
    
    // إصلاح جميع Bootstrap dropdowns الموجودة
    fixBootstrapDropdowns();
    
    // مراقبة إضافة عناصر جديدة (للمحتوى الديناميكي)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        const newDropdowns = node.querySelectorAll('[data-bs-toggle="dropdown"]');
                        if (newDropdowns.length > 0) {
                            fixBootstrapDropdowns();
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

function fixBootstrapDropdowns() {
    // البحث عن جميع Bootstrap dropdowns
    const dropdowns = document.querySelectorAll('[data-bs-toggle="dropdown"]');
    
    dropdowns.forEach(dropdown => {
        // التحقق من أن الـ dropdown لم يتم إصلاحه مسبقاً
        if (!dropdown.hasAttribute('data-dropdown-fixed')) {
            
            // إضافة علامة لتجنب الإصلاح المتكرر
            dropdown.setAttribute('data-dropdown-fixed', 'true');
            
            // إنشاء Bootstrap dropdown instance مع تخصيص container
            try {
                new bootstrap.Dropdown(dropdown, {
                    boundary: 'viewport',
                    container: 'body',
                    popperConfig: {
                        strategy: 'fixed',
                        modifiers: [
                            {
                                name: 'preventOverflow',
                                options: {
                                    boundary: 'viewport',
                                }
                            },
                            {
                                name: 'flip',
                                options: {
                                    fallbackPlacements: ['top', 'right', 'bottom', 'left'],
                                }
                            }
                        ]
                    }
                });
                
                console.log('تم إصلاح Bootstrap dropdown:', dropdown);
                
            } catch (error) {
                console.warn('خطأ في إصلاح Bootstrap dropdown:', error);
            }
        }
    });
}

// دالة لإصلاح dropdown معين
function fixSingleDropdown(dropdownElement) {
    if (dropdownElement && !dropdownElement.hasAttribute('data-dropdown-fixed')) {
        dropdownElement.setAttribute('data-dropdown-fixed', 'true');
        
        try {
            new bootstrap.Dropdown(dropdownElement, {
                boundary: 'viewport',
                container: 'body'
            });
        } catch (error) {
            console.warn('خطأ في إصلاح dropdown:', error);
        }
    }
}

// تصدير الدوال للاستخدام الخارجي
window.fixBootstrapDropdowns = fixBootstrapDropdowns;
window.fixSingleDropdown = fixSingleDropdown;
