/**
 * نظام الرسائل الداخلية والمستخدمين النشطين في القائمة المنسدلة
 */

(function() {
    'use strict';

    const CONFIG = {
        UPDATE_INTERVAL: 10000, // 10 ثواني
        MESSAGES_API: '/accounts/api/messages/unread-count/',
        ONLINE_USERS_API: '/accounts/api/messages/online-users/'
    };

    // إدارة القائمة المنسدلة
    const DropdownManager = {
        init: function() {
            // تحديث البيانات عند فتح القائمة
            const dropdown = document.getElementById('internalMessagesDropdown');
            if (dropdown) {
                dropdown.addEventListener('show.bs.dropdown', () => {
                    this.loadOnlineUsers();
                    this.updateMessageCount();
                });
            }
            
            // تحديث دوري
            this.startAutoUpdate();
        },

        startAutoUpdate: function() {
            setInterval(() => {
                this.updateMessageCount();
                // تحديث المستخدمين فقط إذا كانت القائمة مفتوحة
                const dropdown = document.getElementById('internalMessagesDropdown');
                if (dropdown && dropdown.getAttribute('aria-expanded') === 'true') {
                    this.loadOnlineUsers();
                }
            }, CONFIG.UPDATE_INTERVAL);
        },

        updateMessageCount: function() {
            fetch(CONFIG.MESSAGES_API, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                const badge = document.getElementById('internal-messages-badge');
                if (badge) {
                    if (data.unread_count > 0) {
                        badge.textContent = data.unread_count;
                        badge.style.display = 'inline-block';
                    } else {
                        badge.style.display = 'none';
                    }
                }
            })
            .catch(error => console.error('Error updating message count:', error));
        },

        loadOnlineUsers: function() {
            const listContainer = document.getElementById('online-users-list-dropdown');
            if (!listContainer) return;

            fetch(CONFIG.ONLINE_USERS_API, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                this.renderOnlineUsers(data.users || []);
                this.updateOnlineCount(data.total_online || 0);
            })
            .catch(error => {
                console.error('Error loading online users:', error);
                listContainer.innerHTML = `
                    <div class="text-center p-3 text-danger">
                        <i class="fas fa-exclamation-triangle"></i>
                        <br>
                        <small>فشل تحميل المستخدمين</small>
                    </div>
                `;
            });
        },

        renderOnlineUsers: function(users) {
            const listContainer = document.getElementById('online-users-list-dropdown');
            if (!listContainer) return;

            if (users.length === 0) {
                listContainer.innerHTML = `
                    <div class="text-center p-3 text-muted">
                        <i class="fas fa-users"></i>
                        <br>
                        <small>لا يوجد مستخدمون نشطون الآن</small>
                    </div>
                `;
                return;
            }

            const usersHtml = users.map(user => this.createUserHtml(user)).join('');
            listContainer.innerHTML = usersHtml;
        },

        createUserHtml: function(user) {
            const unreadBadge = user.unread_messages > 0 
                ? `<span class="badge bg-danger rounded-pill">${user.unread_messages}</span>`
                : '';

            return `
                <div class="d-flex align-items-center p-2 border-bottom user-item-dropdown" style="cursor: pointer; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f8f9fa'" onmouseout="this.style.backgroundColor='white'">
                    <div class="position-relative me-2">
                        ${user.avatar_url 
                            ? `<img src="${user.avatar_url}" alt="${user.full_name}" class="rounded-circle" style="width: 40px; height: 40px; object-fit: cover;">`
                            : `<div class="rounded-circle bg-primary d-flex align-items-center justify-content-center text-white" style="width: 40px; height: 40px; font-weight: bold;">
                                ${user.full_name.charAt(0).toUpperCase()}
                            </div>`
                        }
                        <span class="position-absolute bottom-0 end-0 badge rounded-pill bg-success" style="width: 12px; height: 12px; padding: 0; border: 2px solid white;"></span>
                    </div>
                    <div class="flex-grow-1 min-width-0">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="fw-semibold text-truncate" style="font-size: 0.9rem;">${user.full_name}</span>
                            ${unreadBadge}
                        </div>
                        <div class="text-muted small text-truncate">${user.role}</div>
                        <div class="text-muted" style="font-size: 0.75rem;">${user.branch}</div>
                    </div>
                    <a href="/accounts/messages/compose/?to=${user.id}" class="btn btn-sm btn-outline-primary ms-2" title="إرسال رسالة" onclick="event.stopPropagation();">
                        <i class="fas fa-envelope"></i>
                    </a>
                </div>
            `;
        },

        updateOnlineCount: function(count) {
            const countBadge = document.getElementById('online-users-count-header');
            if (countBadge) {
                countBadge.textContent = count;
            }
        },

        getCsrfToken: function() {
            const meta = document.querySelector('meta[name=csrf-token]');
            return meta ? meta.getAttribute('content') :
                   document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        }
    };

    // التهيئة عند تحميل الصفحة
    document.addEventListener('DOMContentLoaded', function() {
        DropdownManager.init();
    });

    // تصدير للاستخدام الخارجي
    window.InternalMessagesDropdown = DropdownManager;

})();
