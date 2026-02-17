/**
 * إصلاح التنقل بين التابات في لوحة إدارة Jazzmin
 * Jazzmin يستخدم data-toggle (Bootstrap 4) لكن Bootstrap 5 يتطلب data-bs-toggle
 * 
 * مهم: يجب عدم التأثير على السايدبار أو عناصر AdminLTE الأخرى
 */
(function() {
    'use strict';
    
    function fixTabs() {
        // === النطاق: فقط عناصر التابات داخل النماذج، وليس السايدبار ===
        // نستهدف فقط التابات داخل #jazzy-tabs أو .changeform-tabs أو .tab-content
        var tabContainers = document.querySelectorAll('#jazzy-tabs, .changeform-tabs, .object-tools');
        
        tabContainers.forEach(function(container) {
            // تحويل data-toggle="tab" و data-toggle="pill" فقط (ليس treeview أو pushmenu)
            container.querySelectorAll('[data-toggle="tab"], [data-toggle="pill"]').forEach(function(el) {
                el.setAttribute('data-bs-toggle', el.getAttribute('data-toggle'));
            });
        });

        // تفعيل التابات يدوياً - فقط داخل حاويات التابات
        var tabLinks = document.querySelectorAll('#jazzy-tabs .nav-link, .changeform-tabs .nav-link');
        
        tabLinks.forEach(function(link) {
            // تجاهل إذا سبق وأضفنا المعالج
            if (link._tabFixApplied) return;
            link._tabFixApplied = true;

            link.addEventListener('click', function(e) {
                e.preventDefault();

                var href = this.getAttribute('href');
                if (!href || href === '#') return;

                // محاولة استخدام Bootstrap 5 Tab API
                try {
                    if (typeof bootstrap !== 'undefined' && bootstrap.Tab) {
                        var bsTab = new bootstrap.Tab(this);
                        bsTab.show();
                        return; // إذا نجح، لا حاجة للمعالجة اليدوية
                    }
                } catch(err) {}

                // Fallback يدوي
                var parentUl = this.closest('ul');
                if (parentUl) {
                    parentUl.querySelectorAll('.nav-link').forEach(function(l) {
                        l.classList.remove('active');
                        l.setAttribute('aria-selected', 'false');
                    });
                }
                
                this.classList.add('active');
                this.setAttribute('aria-selected', 'true');
                
                // إخفاء كل محتوى التابات ضمن نفس الحاوية
                var form = this.closest('form') || document;
                var tabContentParent = form.querySelector('.tab-content');
                if (tabContentParent) {
                    tabContentParent.querySelectorAll('.tab-pane').forEach(function(pane) {
                        pane.classList.remove('active', 'show');
                    });
                }
                
                var targetPane = document.querySelector(href);
                if (targetPane) {
                    targetPane.classList.add('active', 'show');
                }

                if (history.replaceState) {
                    history.replaceState(null, null, href);
                }
            });
        });

        // تفعيل التاب من URL hash
        var hash = window.location.hash;
        if (hash) {
            var activeTab = document.querySelector(
                '#jazzy-tabs .nav-link[href="' + hash + '"], ' +
                '.changeform-tabs .nav-link[href="' + hash + '"]'
            );
            if (activeTab) {
                setTimeout(function() { activeTab.click(); }, 100);
            }
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixTabs);
    } else {
        fixTabs();
    }

    setTimeout(fixTabs, 300);
})();
