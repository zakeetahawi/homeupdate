/**
 * القوائم المنسدلة المحسنة للمصنع - نفس منطق قائمة المستخدم تماماً
 * نسخ المنطق من base.html بالضبط
 */

// دالة إعداد القوائم المنسدلة المحسنة
function initCustomDropdowns(dropdownConfigs) {
    if (!dropdownConfigs || !Array.isArray(dropdownConfigs)) {
        console.warn('initCustomDropdowns: dropdownConfigs must be an array');
        return;
    }

    dropdownConfigs.forEach(dropdown => {
        const btn = document.getElementById(dropdown.btnId);
        const menu = document.getElementById(dropdown.menuId);

        if (btn && menu) {
            // لا نحتاج لنقل القائمة - ستبقى في مكانها مع position: absolute
            console.log('تهيئة القائمة المخصصة:', dropdown.menuId);

            // فتح/إغلاق القائمة - نفس منطق قائمة المستخدم بالضبط
            btn.addEventListener('click', function(e) {
                e.stopPropagation();

                // إغلاق القوائم الأخرى
                dropdownConfigs.forEach(other => {
                    if (other.menuId !== dropdown.menuId) {
                        const otherMenu = document.getElementById(other.menuId);
                        if (otherMenu) otherMenu.style.display = 'none';
                    }
                });

                // تبديل القائمة الحالية - نفس منطق قائمة المستخدم
                menu.style.display = menu.style.display === 'block' ? 'none' : 'block';

                // تحديد موقع القائمة
                if (menu.style.display === 'block') {
                    const rect = btn.getBoundingClientRect();
                    menu.style.top = (rect.bottom + window.scrollY) + 'px';
                    menu.style.left = rect.left + 'px';
                    menu.style.width = rect.width + 'px';
                }

                menu.focus();
            });

            // منع إغلاق القائمة عند النقر داخلها - نفس منطق قائمة المستخدم
            menu.addEventListener('click', function(e) {
                e.stopPropagation();
            });

            // تحديث النص عند تغيير الاختيار
            menu.querySelectorAll(`input[name="${dropdown.inputName}"]`).forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    updateDropdownText(dropdown);
                    // إرسال النموذج تلقائياً عند تغيير الفلتر (اختياري)
                    // يمكن تفعيل هذا إذا أردت إرسال تلقائي
                    // submitFilterForm();
                });
            });
        }
    });

    // إغلاق القوائم عند النقر خارجها - نفس منطق قائمة المستخدم بالضبط
    document.addEventListener('click', function(e) {
        dropdownConfigs.forEach(dropdown => {
            const menu = document.getElementById(dropdown.menuId);
            if (menu) menu.style.display = 'none';
        });
    });

    // تحديث نص القائمة المنسدلة
    function updateDropdownText(dropdown) {
        const btn = document.getElementById(dropdown.btnId);
        if (!btn) return;
        
        const selectedText = btn.querySelector('.selected-text');
        if (!selectedText) return;
        
        const checkboxes = document.querySelectorAll(`input[name="${dropdown.inputName}"]:checked`);
        
        if (checkboxes.length === 0) {
            selectedText.textContent = dropdown.defaultText;
        } else if (checkboxes.length === 1) {
            selectedText.textContent = checkboxes[0].parentElement.textContent.trim();
        } else {
            selectedText.textContent = `تم اختيار ${checkboxes.length} عنصر`;
        }
    }

    // تحديث النصوص عند تحميل الصفحة
    dropdownConfigs.forEach(dropdown => updateDropdownText(dropdown));

    // تحسين تجربة الطباعة
    window.addEventListener('beforeprint', function() {
        dropdownConfigs.forEach(dropdown => {
            const menu = document.getElementById(dropdown.menuId);
            if (menu) menu.style.display = 'none';
        });
    });
}

// دالة إرسال نموذج الفلاتر
function submitFilterForm() {
    const form = document.getElementById('filterForm');
    if (form) {
        form.submit();
    }
}

// دالة إعداد الترتيب التفاعلي
function initSortableHeaders() {
    let currentSort = { column: null, direction: 'none' };
    
    document.querySelectorAll('.sortable-header').forEach(header => {
        header.addEventListener('click', function() {
            const sortColumn = this.dataset.sort;
            const currentParams = new URLSearchParams(window.location.search);
            
            // تحديد اتجاه الترتيب
            let direction = 'asc';
            if (currentSort.column === sortColumn) {
                if (currentSort.direction === 'asc') {
                    direction = 'desc';
                } else if (currentSort.direction === 'desc') {
                    direction = 'none';
                } else {
                    direction = 'asc';
                }
            }
            
            // تحديث المعاملات
            if (direction === 'none') {
                currentParams.delete('sort');
                currentParams.delete('direction');
            } else {
                currentParams.set('sort', sortColumn);
                currentParams.set('direction', direction);
            }
            
            // إعادة التوجيه
            window.location.search = currentParams.toString();
        });
    });

    // تحديث أيقونات الترتيب
    const urlParams = new URLSearchParams(window.location.search);
    const sortColumn = urlParams.get('sort');
    const sortDirection = urlParams.get('direction') || 'none';
    
    if (sortColumn) {
        currentSort = { column: sortColumn, direction: sortDirection };
        
        document.querySelectorAll('.sortable-header').forEach(header => {
            const icon = header.querySelector('.sort-icon');
            if (header.dataset.sort === sortColumn) {
                header.classList.add('active');
                icon.className = `sort-icon ${sortDirection}`;
            } else {
                header.classList.remove('active');
                icon.className = 'sort-icon none';
            }
        });
    }
}

// دالة مساعدة لإعداد القوائم المنسدلة الشائعة
function getCommonDropdownConfigs() {
    return {
        status: { btnId: 'statusDropdownBtn', menuId: 'statusDropdown', inputName: 'status', defaultText: 'اختر الحالات' },
        branch: { btnId: 'branchDropdownBtn', menuId: 'branchDropdown', inputName: 'branch', defaultText: 'اختر الفروع' },
        orderType: { btnId: 'orderTypeDropdownBtn', menuId: 'orderTypeDropdown', inputName: 'order_type', defaultText: 'اختر الأنواع' },
        productionLine: { btnId: 'productionLineDropdownBtn', menuId: 'productionLineDropdown', inputName: 'production_line', defaultText: 'اختر خطوط الإنتاج' },
        overdue: { btnId: 'orderTypesDropdownBtnOverdue', menuId: 'orderTypesDropdownOverdue', inputName: 'order_types', defaultText: 'جميع الأنواع' }
    };
}

// تصدير الدوال للاستخدام العام
window.ManufacturingDropdowns = {
    init: initCustomDropdowns,
    initSort: initSortableHeaders,
    getCommonConfigs: getCommonDropdownConfigs
};
