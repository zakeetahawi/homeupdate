/**
 * activity-summary.js
 * ====================
 * ملخص النشاط — يظهر مرة واحدة فقط عند الدخول
 * يُغلق نهائياً عند إغلاقه ولا يعود حتى الجلسة القادمة
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'activitySummaryDismissed';
    var SESSION_ID_KEY = 'activitySummarySessionId';

    /**
     * يُعيد session ID فريد مبني على وقت تحميل الصفحة.
     * عند تسجيل الدخول من جديد، الصفحة تتحمل من جديد = session جديد.
     */
    function getCurrentSessionId() {
        var el = document.body;
        return el.getAttribute('data-session-id') || 'default';
    }

    function isDismissed() {
        var dismissed = localStorage.getItem(STORAGE_KEY);
        var currentSession = getCurrentSessionId();
        return dismissed === currentSession;
    }

    function markDismissed() {
        var currentSession = getCurrentSessionId();
        localStorage.setItem(STORAGE_KEY, currentSession);
    }

    function createOverlay() {
        var overlay = document.createElement('div');
        overlay.id = 'activitySummaryOverlay';
        overlay.className = 'activity-summary-overlay';
        overlay.innerHTML =
            '<div class="activity-summary-card">' +
                '<div class="activity-summary-header">' +
                    '<button class="activity-summary-close" onclick="dismissActivitySummary()" aria-label="إغلاق">' +
                        '<i class="fas fa-times"></i>' +
                    '</button>' +
                    '<div class="activity-summary-greeting"></div>' +
                    '<h4 class="activity-summary-title">ملخص النشاط</h4>' +
                    '<div class="activity-summary-since"><i class="fas fa-clock"></i><span></span></div>' +
                '</div>' +
                '<div class="activity-summary-body">' +
                    '<div style="text-align:center;padding:30px"><i class="fas fa-spinner fa-spin" style="font-size:1.5rem;color:#94a3b8"></i></div>' +
                '</div>' +
                '<div class="activity-summary-footer">' +
                    '<button onclick="dismissActivitySummary()"><i class="fas fa-check me-1"></i>حسناً، فهمت</button>' +
                '</div>' +
            '</div>';

        // Close on overlay click (outside card)
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) dismissActivitySummary();
        });

        document.body.appendChild(overlay);

        // حرّك الـ show class بعد frame لتفعيل الـ CSS transition
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                overlay.classList.add('show');
            });
        });

        return overlay;
    }

    function getGreeting() {
        var h = new Date().getHours();
        if (h < 6) return 'مساء الخير 🌙';
        if (h < 12) return 'صباح الخير ☀️';
        if (h < 17) return 'مرحباً 👋';
        return 'مساء الخير 🌙';
    }

    function hexToRgba(hex, alpha) {
        hex = hex.replace('#', '');
        var r = parseInt(hex.substring(0, 2), 16);
        var g = parseInt(hex.substring(2, 4), 16);
        var b = parseInt(hex.substring(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    function renderItems(overlay, data) {
        var body = overlay.querySelector('.activity-summary-body');
        var greetEl = overlay.querySelector('.activity-summary-greeting');
        var sinceSpan = overlay.querySelector('.activity-summary-since span');

        greetEl.textContent = getGreeting();
        sinceSpan.textContent = 'في آخر ' + data.since_text;

        if (!data.items || data.items.length === 0) {
            body.innerHTML =
                '<div class="activity-summary-empty">' +
                    '<i class="fas fa-coffee"></i>' +
                    '<p>لم يحدث شيء جديد أثناء غيابك</p>' +
                '</div>';
            return;
        }

        var html = '';
        data.items.forEach(function (item) {
            var bgColor = hexToRgba(item.color, 0.1);
            html +=
                '<a href="' + item.url + '" class="activity-item" onclick="dismissActivitySummary()">' +
                    '<div class="activity-item-icon" style="background:' + bgColor + ';color:' + item.color + '">' +
                        '<i class="' + item.icon + '"></i>' +
                    '</div>' +
                    '<div class="activity-item-text">' +
                        '<p class="activity-item-label">' + item.label + '</p>' +
                    '</div>' +
                    '<div class="activity-item-count" style="color:' + item.color + '">' + item.count + '</div>' +
                '</a>';
        });

        body.innerHTML = html;
    }

    function fetchAndShow() {
        var overlay = createOverlay();

        fetch('/notifications/ajax/activity-summary/?_=' + Date.now())
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success && data.total > 0) {
                    renderItems(overlay, data);
                } else if (data.success && data.total === 0) {
                    // لا شيء لعرضه — أغلق بهدوء
                    dismissActivitySummary();
                } else {
                    dismissActivitySummary();
                }
            })
            .catch(function () {
                dismissActivitySummary();
            });
    }

    window.dismissActivitySummary = function () {
        markDismissed();
        var overlay = document.getElementById('activitySummaryOverlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(function () { overlay.remove(); }, 400);
        }
    };

    // ════════════════════════════════════
    // Initialization
    // ════════════════════════════════════

    document.addEventListener('DOMContentLoaded', function () {
        // فقط على الصفحة الرئيسية
        if (window.location.pathname !== '/') return;

        // لا تعرض إذا أُغلقت سابقاً في هذه الجلسة
        if (isDismissed()) return;

        // انتظر لحظة حتى تتحمل الصفحة بالكامل
        setTimeout(fetchAndShow, 1200);
    });

})();
