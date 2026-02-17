/**
 * إصلاح التنقل بين التابات في لوحة إدارة Jazzmin
 * Jazzmin يستخدم data-toggle (Bootstrap 4) لكن Bootstrap 5 يتطلب data-bs-toggle
 */
(function() {
    'use strict';
    
    // تشغيل فوري + عند DOMContentLoaded
    function fixTabs() {
        // 1. تحويل كل data-toggle إلى data-bs-toggle
        document.querySelectorAll('[data-toggle]').forEach(function(el) {
            el.setAttribute('data-bs-toggle', el.getAttribute('data-toggle'));
        });
        
        // 2. تحويل data-dismiss
        document.querySelectorAll('[data-dismiss]').forEach(function(el) {
            el.setAttribute('data-bs-dismiss', el.getAttribute('data-dismiss'));
        });
        
        // 3. تحويل data-target
        document.querySelectorAll('[data-target]').forEach(function(el) {
            el.setAttribute('data-bs-target', el.getAttribute('data-target'));
        });

        // 4. تحويل data-slide
        document.querySelectorAll('[data-slide]').forEach(function(el) {
            el.setAttribute('data-bs-slide', el.getAttribute('data-slide'));
        });

        // 5. تحويل data-ride
        document.querySelectorAll('[data-ride]').forEach(function(el) {
            el.setAttribute('data-bs-ride', el.getAttribute('data-ride'));
        });

        // 6. تفعيل التابات يدوياً عبر Bootstrap 5 Tab API
        var tabLinks = document.querySelectorAll('#jazzy-tabs .nav-link, .nav-tabs .nav-link, .nav-pills .nav-link');
        
        tabLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                var href = this.getAttribute('href');
                if (!href || href === '#') return;

                // محاولة استخدام Bootstrap 5 Tab API
                try {
                    if (typeof bootstrap !== 'undefined' && bootstrap.Tab) {
                        var bsTab = new bootstrap.Tab(this);
                        bsTab.show();
                    }
                } catch(err) {
                    // fallback يدوي
                }

                // تمرير يدوي كاحتياط
                // إزالة active من كل التابات
                var parentUl = this.closest('ul');
                if (parentUl) {
                    parentUl.querySelectorAll('.nav-link').forEach(function(l) {
                        l.classList.remove('active');
                        l.setAttribute('aria-selected', 'false');
                    });
                }
                
                // تفعيل التاب الحالي
                this.classList.add('active');
                this.setAttribute('aria-selected', 'true');
                
                // إخفاء كل محتوى التابات
                var tabContentParent = document.querySelector('.tab-content');
                if (tabContentParent) {
                    tabContentParent.querySelectorAll('.tab-pane').forEach(function(pane) {
                        pane.classList.remove('active', 'show');
                    });
                }
                
                // عرض محتوى التاب المختار
                var targetPane = document.querySelector(href);
                if (targetPane) {
                    targetPane.classList.add('active', 'show');
                }

                // تحديث URL
                if (history.replaceState) {
                    history.replaceState(null, null, href);
                }
            });
        });

        // 7. تفعيل التاب من URL hash عند تحميل الصفحة
        var hash = window.location.hash;
        if (hash) {
            // البحث عن التاب المطابق
            var activeTab = document.querySelector(
                '#jazzy-tabs .nav-link[href="' + hash + '"], ' +
                '.nav-tabs .nav-link[href="' + hash + '"], ' +
                '.nav-pills .nav-link[href="' + hash + '"]'
            );
            if (activeTab) {
                setTimeout(function() { activeTab.click(); }, 100);
            }
        }
    }
    
    // تشغيل عند جاهزية DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixTabs);
    } else {
        fixTabs();
    }

    // تشغيل مرة أخرى بعد تأخير قصير للتأكد من تحميل كل شيء
    setTimeout(fixTabs, 300);
})();
