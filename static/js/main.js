/**
 * Theme Management System
 * نظام إدارة الثيمات الموحد
 */

document.addEventListener('DOMContentLoaded', function() {
    // الحصول على عنصر اختيار الثيم
    const themeSelector = document.getElementById('themeSelector');
    if (!themeSelector) return;

    // تحديث حالة select لتطابق الثيم الحالي
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'default';
    themeSelector.value = currentTheme;

    // الاستماع لتغييرات الثيم
    themeSelector.addEventListener('change', function(e) {
        const selectedTheme = e.target.value;
        applyTheme(selectedTheme);
        localStorage.setItem('selectedTheme', selectedTheme);

        // حفظ الثيم في قاعدة البيانات إذا كان المستخدم مسجل
        if (document.body.dataset.userAuthenticated === 'true') {
            fetch('/accounts/set_default_theme/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                },
                body: JSON.stringify({ theme: selectedTheme })
            });
        }
        
        // تطبيق تأثير التحول السلس
        addTransitionEffect();
        
        // لتحديث أي مكونات تحتاج تحديثاً خاصاً مع تغيير الثيم
        updateComponentsOnThemeChange();
    });
    
    // التطبيق الأولي للثيم - يضمن تحديث جميع العناصر
    updateComponentsOnThemeChange();
});

/**
 * تطبيق الثيم المحدد على عنصر body
 * @param {string} theme - اسم الثيم المراد تطبيقه
 */
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
}

/**
 * إضافة تأثير انتقالي سلس عند تغيير الثيم
 */
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

/**
 * تحديث المكونات التي قد تحتاج تحديثاً خاصاً عند تغيير الثيم
 */
function updateComponentsOnThemeChange() {
    // تحديث مخططات البيانات إذا وجدت
    updateCharts();
    
    // تحديث الجداول إذا وجدت
    updateTables();
    
    // إرسال حدث تغيير الثيم لاستخدامه في المكونات الأخرى
    const event = new CustomEvent('themeChanged', { 
        detail: { theme: document.body.getAttribute('data-theme') } 
    });
    document.dispatchEvent(event);
}

/**
 * تحديث مخططات البيانات عند تغيير الثيم
 */
function updateCharts() {
    // إذا كانت مكتبة Chart.js متاحة، قم بتحديث الألوان
    if (window.Chart && window.Chart.instances) {
        Object.values(window.Chart.instances).forEach(chart => {
            if (chart.config && chart.update) {
                chart.update();
            }
        });
    }
}

/**
 * تحديث تنسيقات الجداول عند تغيير الثيم
 */
function updateTables() {
    // إذا كانت مكتبة DataTables متاحة، قم بتحديث الجداول
    if (window.$.fn && window.$.fn.dataTable) {
        window.$.fn.dataTable.tables({ visible: true, api: true }).draw();
    }
}
