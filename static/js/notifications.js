/**
 * نظام الإشعارات المحسن
 */
class NotificationManager {
    constructor() {
        this.notifications = [];
        this.unreadCount = 0;
        this.pollingInterval = null;
        this.init();
    }

    init() {
        this.loadNotifications();
        this.setupEventListeners();
        this.startPolling();
    }

    setupEventListeners() {
        // زر الإشعارات في الشريط العلوي
        const notificationBtn = document.getElementById('notification-btn');
        if (notificationBtn) {
            notificationBtn.addEventListener('click', () => {
                this.toggleNotificationPanel();
            });
        }

        // إغلاق لوحة الإشعارات عند النقر خارجها
        document.addEventListener('click', (e) => {
            const panel = document.getElementById('notification-panel');
            const btn = document.getElementById('notification-btn');
            
            if (panel && !panel.contains(e.target) && !btn.contains(e.target)) {
                this.hideNotificationPanel();
            }
        });
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.notifications = data.notifications || [];
                this.unreadCount = data.unread_count || 0;
                this.updateNotificationBadge();
                this.renderNotifications();
            }
        } catch (error) {
            console.error('خطأ في تحميل الإشعارات:', error);
        }
    }

    updateNotificationBadge() {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = this.unreadCount;
            badge.style.display = this.unreadCount > 0 ? 'block' : 'none';
        }
    }

    renderNotifications() {
        const container = document.getElementById('notification-list');
        if (!container) return;

        if (this.notifications.length === 0) {
            container.innerHTML = '<div class="text-center p-3">لا توجد إشعارات جديدة</div>';
            return;
        }

        const notificationsHtml = this.notifications.map(notification => {
            const priorityClass = this.getPriorityClass(notification.priority);
            const typeIcon = this.getTypeIcon(notification.notification_type);
            const isRead = notification.is_read ? '' : 'unread';
            
            return `
                <div class="notification-item ${isRead} ${priorityClass}" data-id="${notification.id}">
                    <div class="notification-header">
                        <i class="${typeIcon}"></i>
                        <span class="notification-title">${notification.title}</span>
                        <span class="notification-time">${this.formatTime(notification.created_at)}</span>
                    </div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-actions">
                        ${notification.requires_action && notification.action_url ? 
                            `<a href="${notification.action_url}" class="btn btn-sm btn-primary">عرض التفاصيل</a>` : ''
                        }
                        <button class="btn btn-sm btn-outline-secondary mark-read" data-id="${notification.id}">
                            ${notification.is_read ? 'إعادة تحديد' : 'تحديد كمقروء'}
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = notificationsHtml;
        this.setupNotificationActions();
    }

    setupNotificationActions() {
        // أزرار تحديد كمقروء
        document.querySelectorAll('.mark-read').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const notificationId = btn.dataset.id;
                this.markAsRead(notificationId);
            });
        });

        // النقر على الإشعار
        document.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.notification-actions')) {
                    const notificationId = item.dataset.id;
                    this.markAsRead(notificationId);
                }
            });
        });
    }

    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/mark-read/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                // تحديث الواجهة
                const notification = this.notifications.find(n => n.id == notificationId);
                if (notification) {
                    notification.is_read = true;
                    this.unreadCount = Math.max(0, this.unreadCount - 1);
                    this.updateNotificationBadge();
                    this.renderNotifications();
                }
            }
        } catch (error) {
            console.error('خطأ في تحديد الإشعار كمقروء:', error);
        }
    }

    async markAllAsRead() {
        try {
            const response = await fetch('/api/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.notifications.forEach(n => n.is_read = true);
                this.unreadCount = 0;
                this.updateNotificationBadge();
                this.renderNotifications();
            }
        } catch (error) {
            console.error('خطأ في تحديد جميع الإشعارات كمقروءة:', error);
        }
    }

    toggleNotificationPanel() {
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.toggle('show');
        }
    }

    hideNotificationPanel() {
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.remove('show');
        }
    }

    startPolling() {
        // تحديث الإشعارات كل 30 ثانية
        this.pollingInterval = setInterval(() => {
            this.loadNotifications();
        }, 30000);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    getPriorityClass(priority) {
        const classes = {
            'low': 'priority-low',
            'medium': 'priority-medium',
            'high': 'priority-high',
            'urgent': 'priority-urgent'
        };
        return classes[priority] || 'priority-medium';
    }

    getTypeIcon(type) {
        const icons = {
            'info': 'fas fa-info-circle',
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle',
            'error': 'fas fa-times-circle',
            'order': 'fas fa-shopping-cart',
            'inspection': 'fas fa-clipboard-check',
            'manufacturing': 'fas fa-cogs',
            'inventory': 'fas fa-boxes',
            'system': 'fas fa-cog'
        };
        return icons[type] || 'fas fa-bell';
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'الآن';
        if (minutes < 60) return `منذ ${minutes} دقيقة`;
        if (hours < 24) return `منذ ${hours} ساعة`;
        if (days < 7) return `منذ ${days} يوم`;
        
        return date.toLocaleDateString('ar-SA');
    }

    getToken() {
        // الحصول على token من localStorage أو من meta tag
        return localStorage.getItem('auth_token') || 
               document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    // إشعار فوري (للاختبار)
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="${this.getTypeIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
}

// تهيئة مدير الإشعارات عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});

// تصدير للاستخدام في ملفات أخرى
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
} 