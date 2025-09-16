/**
 * مكتبة القوائم المنسدلة البسيطة والفعالة
 * Simple and Effective Dropdowns Library
 */

class SimpleDropdowns {
    constructor() {
        this.activeDropdown = null;
        this.dropdowns = new Map();
        this.init();
    }

    init() {
        // إضافة مستمع للنقر خارج القوائم
        document.addEventListener('click', (e) => this.handleOutsideClick(e));
        
        // إضافة مستمع لتغيير حجم النافذة
        window.addEventListener('resize', () => this.repositionActiveDropdown());
        
        // إضافة مستمع للتمرير
        window.addEventListener('scroll', () => this.repositionActiveDropdown());
        
        console.log('✅ تم تهيئة مكتبة القوائم المنسدلة البسيطة');
    }

    /**
     * تسجيل قائمة منسدلة جديدة
     */
    register(buttonId, dropdownId, options = {}) {
        const button = document.getElementById(buttonId);
        const dropdown = document.getElementById(dropdownId);
        
        if (!button || !dropdown) {
            console.error(`❌ لم يتم العثور على العناصر: ${buttonId} أو ${dropdownId}`);
            return false;
        }

        const config = {
            button,
            dropdown,
            isOpen: false,
            options: {
                position: 'bottom', // bottom, top, auto
                align: 'left', // left, right, center
                offset: 2,
                minWidth: 200,
                maxWidth: 400,
                maxHeight: 300,
                zIndex: 999999,
                ...options
            }
        };

        // إضافة الأنماط الأساسية للقائمة
        this.applyStyles(dropdown, config.options);

        // إضافة مستمع النقر للزر
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggle(buttonId);
        });

        // حفظ التكوين
        this.dropdowns.set(buttonId, config);
        
        console.log(`✅ تم تسجيل القائمة: ${buttonId} -> ${dropdownId}`);
        return true;
    }

    /**
     * تطبيق الأنماط الأساسية - نفس منطق البطاقة الناجحة
     */
    applyStyles(dropdown, options) {
        dropdown.style.display = 'none';
        dropdown.style.position = 'absolute'; // مثل البطاقة الناجحة
        dropdown.style.top = '100%'; // أسفل الزر مباشرة
        dropdown.style.left = '0px'; // محاذاة يسار
        dropdown.style.zIndex = '1050'; // z-index معقول مثل البطاقة
        dropdown.style.minWidth = options.minWidth + 'px';
        dropdown.style.maxWidth = '95vw'; // مثل البطاقة
        dropdown.style.backgroundColor = 'rgb(255, 255, 255)';
        dropdown.style.borderRadius = '12px'; // مثل البطاقة
        dropdown.style.boxShadow = 'rgba(0, 0, 0, 0.18) 0px 8px 32px'; // مثل البطاقة
        dropdown.style.border = '1px solid rgb(238, 238, 238)'; // مثل البطاقة
        dropdown.style.maxHeight = options.maxHeight + 'px';
        dropdown.style.overflowY = 'auto';
    }

    /**
     * فتح/إغلاق القائمة
     */
    toggle(buttonId) {
        const config = this.dropdowns.get(buttonId);
        if (!config) return;

        if (config.isOpen) {
            this.close(buttonId);
        } else {
            this.open(buttonId);
        }
    }

    /**
     * فتح القائمة
     */
    open(buttonId) {
        // إغلاق أي قائمة مفتوحة
        this.closeAll();

        const config = this.dropdowns.get(buttonId);
        if (!config) return;

        // حساب وتطبيق الموضع
        this.position(config);
        
        // إظهار القائمة
        config.dropdown.style.display = 'block';
        config.isOpen = true;
        this.activeDropdown = buttonId;

        console.log(`📂 تم فتح القائمة: ${buttonId}`);
    }

    /**
     * إغلاق القائمة
     */
    close(buttonId) {
        const config = this.dropdowns.get(buttonId);
        if (!config) return;

        config.dropdown.style.display = 'none';
        config.isOpen = false;
        
        if (this.activeDropdown === buttonId) {
            this.activeDropdown = null;
        }

        console.log(`📁 تم إغلاق القائمة: ${buttonId}`);
    }

    /**
     * إغلاق جميع القوائم
     */
    closeAll() {
        this.dropdowns.forEach((config, buttonId) => {
            if (config.isOpen) {
                this.close(buttonId);
            }
        });
    }

    /**
     * تموضع بسيط - مثل البطاقة الناجحة (position: absolute)
     */
    position(config) {
        const { button, dropdown, options } = config;

        // CSS يتولى التموضع الأساسي (top: 100%, left: 0)
        // نحتاج فقط لضبط العرض
        const buttonRect = button.getBoundingClientRect();
        const width = Math.max(buttonRect.width, options.minWidth);

        dropdown.style.width = width + 'px';

        console.log(`📍 تم ضبط عرض القائمة: ${width}px`);
    }

    /**
     * إعادة تموضع القائمة النشطة
     */
    repositionActiveDropdown() {
        if (this.activeDropdown) {
            const config = this.dropdowns.get(this.activeDropdown);
            if (config && config.isOpen) {
                this.position(config);
            }
        }
    }

    /**
     * التعامل مع النقر خارج القوائم
     */
    handleOutsideClick(e) {
        let clickedInsideDropdown = false;
        let clickedOnButton = false;

        // التحقق من النقر على زر أو داخل قائمة
        this.dropdowns.forEach((config, buttonId) => {
            if (config.button.contains(e.target)) {
                clickedOnButton = true;
            }
            if (config.dropdown.contains(e.target)) {
                clickedInsideDropdown = true;
            }
        });

        // إغلاق جميع القوائم إذا لم يتم النقر على زر أو داخل قائمة
        if (!clickedOnButton && !clickedInsideDropdown) {
            this.closeAll();
        }
    }

    /**
     * تدمير المكتبة وتنظيف المستمعات
     */
    destroy() {
        this.closeAll();
        this.dropdowns.clear();
        this.activeDropdown = null;
        console.log('🗑️ تم تدمير مكتبة القوائم المنسدلة');
    }
}

// إنشاء مثيل عام للمكتبة
window.SimpleDropdowns = new SimpleDropdowns();

// تصدير للاستخدام كوحدة
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimpleDropdowns;
}
