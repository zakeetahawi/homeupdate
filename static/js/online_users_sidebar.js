/**
 * Professional Online Users Sidebar JavaScript
 * تفاعل احترافي للقائمة الجانبية للمستخدمين النشطين
 */

(function() {
    'use strict';

    // ===== ENHANCED CONFIGURATION =====
    const CONFIG = {
        UPDATE_INTERVAL: 8000, // Optimized to 8 seconds to reduce server load
        ACTIVITY_UPDATE_INTERVAL: 15000, // 15 seconds for activities
        ANIMATION_DURATION: 400, // Smoother animations
        API_ENDPOINT: '/accounts/api/online-users/',
        USER_ACTIVITIES_ENDPOINT: '/accounts/api/user-activities/',
        DEBUG_MODE: false,
        MAX_RETRIES: 3,
        RETRY_DELAY: 2000,
        ENABLE_SOUND_NOTIFICATIONS: false,
        ENABLE_ACTIVITY_TRACKING: true
    };

    // ===== UTILITY FUNCTIONS =====
    const Utils = {
        log: function(message, type = 'info') {
            if (CONFIG.DEBUG_MODE) {
                console[type](`[OnlineUsersSidebar] ${message}`);
            }
        },

        formatDuration: function(seconds) {
            if (seconds < 60) return `${seconds} ث`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)} د`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)} س`;
            return `${Math.floor(seconds / 86400)} ي`;
        },

        formatTime: function(dateString) {
            const date = new Date(dateString);
            return date.toLocaleTimeString('ar-SA', {
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        getCsrfToken: function() {
            const meta = document.querySelector('meta[name=csrf-token]');
            return meta ? meta.getAttribute('content') :
                   document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        },

        showToast: function(message, type = 'info') {
            // استخدام SweetAlert2 إذا كان متوفراً
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    text: message,
                    icon: type,
                    toast: true,
                    position: 'top-end',
                    showConfirmButton: false,
                    timer: 3000,
                    timerProgressBar: true
                });
            } else {
                console.log(`[${type.toUpperCase()}] ${message}`);
            }
        }
    };

    // ===== SIDEBAR MANAGER =====
    const SidebarManager = {
        sidebar: null,
        toggleBtn: null,
        collapsedToggle: null,
        isCollapsed: false,
        isInitialized: false,

        init: function() {
            this.sidebar = document.getElementById('online-users-sidebar');
            this.toggleBtn = document.getElementById('sidebar-toggle');
            this.collapsedToggle = document.getElementById('sidebar-collapsed-toggle');

            if (!this.sidebar) {
                Utils.log('Sidebar element not found', 'error');
                return;
            }

            // إضافة class visible لجعل القائمة مرئية
            this.sidebar.classList.add('visible');

            // تحديد الحالة الأولية بناءً على وجود class "collapsed"
            this.isCollapsed = this.sidebar.classList.contains('collapsed');

            // إظهار/إخفاء الزر المخفي حسب الحالة
            if (this.collapsedToggle) {
                if (this.isCollapsed) {
                    this.collapsedToggle.classList.add('show');
                } else {
                    this.collapsedToggle.classList.remove('show');
                }
            }

            // تحديث أيقونة الزر الرئيسي حسب الحالة الأولية
            this.updateToggleIcon();

            this.setupEventListeners();
            this.isInitialized = true;
            Utils.log('Sidebar manager initialized, collapsed:', this.isCollapsed);
        },

        setupEventListeners: function() {
            // Toggle button
            if (this.toggleBtn) {
                this.toggleBtn.addEventListener('click', () => this.toggle());
            }

            // Collapsed toggle button
            if (this.collapsedToggle) {
                this.collapsedToggle.addEventListener('click', () => this.expand());
            }

            // Close on outside click (mobile)
            document.addEventListener('click', (e) => {
                if (window.innerWidth <= 768 &&
                    !this.sidebar.contains(e.target) &&
                    !this.collapsedToggle.contains(e.target) &&
                    !this.isCollapsed) {
                    this.collapse();
                }
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'u') {
                    e.preventDefault();
                    this.toggle();
                }
            });
        },

        toggle: function() {
            if (this.isCollapsed) {
                this.expand();
            } else {
                this.collapse();
            }
        },

        expand: function() {
            if (!this.sidebar) return;

            this.sidebar.classList.remove('collapsed');
            this.isCollapsed = false;
            if (this.collapsedToggle) {
                this.collapsedToggle.classList.remove('show');
            }

            this.updateToggleIcon();

            Utils.log('Sidebar expanded');
        },

        collapse: function() {
            if (!this.sidebar) return;

            this.sidebar.classList.add('collapsed');
            this.isCollapsed = true;
            if (this.collapsedToggle) {
                this.collapsedToggle.classList.add('show');
            }

            this.updateToggleIcon();

            Utils.log('Sidebar collapsed');
        },

        updateToggleIcon: function() {
            if (this.toggleBtn) {
                // عندما تكون القائمة مفتوحة، الأيقونة للإغلاق (يسار)
                // عندما تكون القائمة مخفية، الأيقونة للفتح (يمين)
                const iconClass = this.isCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
                this.toggleBtn.querySelector('i').className = iconClass;
            }
        }
    };

    // ===== USERS MANAGER =====
    const UsersManager = {
        usersList: null,
        onlineCount: null,
        totalCount: null,
        lastUpdateTime: null,
        refreshBtn: null,
        updateInterval: null,
        isLoading: false,

        init: function() {
            this.usersList = document.getElementById('users-list');
            this.onlineCount = document.getElementById('online-count');
            this.totalCount = document.getElementById('total-count');
            this.lastUpdateTime = document.getElementById('last-update-time');
            this.refreshBtn = document.getElementById('refresh-users');

            if (!this.usersList) {
                Utils.log('Users list element not found', 'error');
                return;
            }

            this.setupEventListeners();
            this.loadUsers();
            this.startAutoUpdate();

            Utils.log('Users manager initialized');
        },

        setupEventListeners: function() {
            // Refresh button
            if (this.refreshBtn) {
                this.refreshBtn.addEventListener('click', () => this.refresh());
            }

            // User item clicks
            // When a user item is clicked, show a lightweight inline panel
            // Do NOT fetch activities from the server to avoid DB load.
            this.usersList.addEventListener('click', (e) => {
                const userItem = e.target.closest('.user-item');
                if (userItem) {
                    // Toggle an inline details panel built from already-available data-attributes
                    const existingPanel = userItem.querySelector('.inline-user-panel');
                    if (existingPanel) {
                        existingPanel.remove();
                        return;
                    }

                    const username = userItem.dataset.username || '';
                    const fullName = userItem.querySelector('.user-name')?.textContent?.trim() || '';
                    const role = userItem.querySelector('.user-role')?.textContent?.trim() || '';
                    const branch = userItem.querySelector('.user-branch')?.textContent?.trim() || '';
                    const duration = userItem.querySelector('.user-duration')?.textContent?.trim() || '';

                    const panel = document.createElement('div');
                    panel.className = 'inline-user-panel';
                    panel.innerHTML = `
                        <div class="inline-panel-card">
                            <div class="inline-row"><strong>الاسم:</strong> ${fullName || username}</div>
                            ${role ? `<div class="inline-row"><strong>الدور:</strong> ${role}</div>` : ''}
                            ${branch ? `<div class="inline-row"><strong>الفرع:</strong> ${branch}</div>` : ''}
                            ${duration ? `<div class="inline-row"><strong>الحالة:</strong> ${duration}</div>` : ''}
                        </div>
                    `;

                    userItem.appendChild(panel);
                    // Remove panel after 12 seconds to keep UI tidy
                    setTimeout(() => {
                        panel.remove();
                    }, 12000);
                }
            });
        },

        loadUsers: async function() {
            if (this.isLoading) return;

            this.isLoading = true;
            this.showLoading();

            try {
                const response = await fetch(CONFIG.API_ENDPOINT, {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': Utils.getCsrfToken(),
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                this.renderUsers(data.users || [], data.total_online || 0, data.total_users || 0);
                this.updateOnlineCount(data.total_online || 0);
                this.updateTotalCount(data.total_users || 0);
                this.updateLastUpdateTime();

                Utils.log(`Loaded ${data.users?.length || 0} users (${data.total_online || 0} online, ${data.total_users || 0} total)`);

            } catch (error) {
                Utils.log(`Error loading users: ${error.message}`, 'error');
                this.showError('فشل في تحديث قائمة المستخدمين');
            } finally {
                this.isLoading = false;
            }
        },

        renderUsers: function(users, totalOnline, totalUsers) {
            if (!this.usersList) return;

            if (users.length === 0) {
                this.usersList.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-users fa-2x text-muted mb-2"></i>
                        <p class="text-muted small">لا يوجد مستخدمون نشطون حالياً</p>
                    </div>
                `;
                // تحديث العدادات حتى لو لم يكن هناك مستخدمون
                this.updateOnlineCount(totalOnline || 0);
                this.updateTotalCount(totalUsers || 0);
                return;
            }

            // Ensure online users are shown first (client-side safeguard)
            const sortedUsers = users.slice().sort((a, b) => {
                if (a.is_online === b.is_online) {
                    const aLogin = a.last_login || '';
                    const bLogin = b.last_login || '';
                    if (aLogin === bLogin) return 0;
                    return bLogin > aLogin ? 1 : -1;
                }
                return a.is_online ? -1 : 1;
            });

            const usersHtml = sortedUsers.map(user => this.createUserHtml(user)).join('');
            this.usersList.innerHTML = usersHtml;

            // تحديث العدادات باستخدام القيم المُرسلة من API
            this.updateOnlineCount(totalOnline || 0);
            this.updateTotalCount(totalUsers || 0);
        },

        createUserHtml: function(user) {
            const avatarHtml = user.avatar_url
                ? `<img src="${user.avatar_url}" alt="${user.full_name}">`
                : `<div class="user-initial">${user.full_name.charAt(0).toUpperCase()}</div>`;

            // Enhanced status indicators
            const indicatorHtml = user.is_online
                ? '<div class="online-indicator online"><div class="pulse-ring"></div></div>'
                : '<div class="online-indicator offline"></div>';

            // Enhanced status text with activity context
            const statusText = user.is_online ? 'متصل الآن' : 'غير متصل';
            const durationText = user.is_online
                ? `نشط منذ ${user.online_duration}`
                : `آخر ظهور: ${user.last_login_formatted || 'غير محدد'}`;

            // Activity indicator
            const activityIndicator = user.current_activity
                ? `<div class="activity-indicator" title="${user.current_activity}">
                     <i class="fas fa-circle"></i>
                   </div>`
                : '';

            // User class with enhanced states
            const userClass = `user-item ${user.is_online ? 'online' : 'offline'} ${user.role?.toLowerCase() || ''}`;

            return `
                <div class="${userClass}"
                     data-user-id="${user.id}"
                     data-username="${user.username}"
                     data-role="${user.role}"
                     data-branch="${user.branch}"
                     data-online="${user.is_online}">
                    <div class="user-avatar">
                        ${avatarHtml}
                        ${indicatorHtml}
                        ${activityIndicator}
                    </div>
                    <div class="user-info">
                        <div class="user-name">
                            <span class="name-text">${user.full_name}</span>
                            <span class="user-status ${user.is_online ? 'online' : 'offline'}">${statusText}</span>
                        </div>
                        <div class="user-details">
                            <div class="user-role">
                                <i class="fas fa-user-tag"></i>
                                ${user.role}
                            </div>
                            <div class="user-branch">
                                <i class="fas fa-building"></i>
                                ${user.branch}
                            </div>
                            <div class="user-duration">
                                <i class="fas fa-clock"></i>
                                ${durationText}
                            </div>
                        </div>
                    </div>
                    <div class="user-actions">
                        <button class="action-btn expand-btn" title="عرض التفاصيل">
                            <i class="fas fa-chevron-down"></i>
                        </button>
                    </div>
                </div>
            `;
        },

        updateOnlineCount: function(count) {
            if (this.onlineCount) {
                this.onlineCount.textContent = count;
            }
            // تحديث العداد الخارجي على الزر إذا وُجد
            const externalBadge = document.getElementById('external-online-badge');
            if (externalBadge) {
                externalBadge.textContent = count;
                externalBadge.style.display = count > 0 ? 'inline-block' : 'none';
            }
            // تحديث العداد الموجود على الزر المخفي (collapsed)
            const collapsedBadge = document.getElementById('collapsed-online-badge');
            if (collapsedBadge) {
                collapsedBadge.textContent = count;
                collapsedBadge.style.display = count > 0 ? 'inline-block' : 'none';
            }
        },

        updateTotalCount: function(count) {
            if (this.totalCount) {
                this.totalCount.textContent = count;
            }
        },

        updateLastUpdateTime: function() {
            if (this.lastUpdateTime) {
                const now = new Date();
                this.lastUpdateTime.textContent = `آخر تحديث: ${now.toLocaleTimeString('ar-SA', {
                    hour: '2-digit',
                    minute: '2-digit'
                })}`;
            }
        },

        showUserActivities: async function(userId, userItem) {
            try {
                // Show loading in modal
                const modal = new bootstrap.Modal(document.getElementById('userActivitiesModal'));
                const modalContent = document.getElementById('user-activities-content');
                modalContent.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border" role="status">
                            <span class="visually-hidden">جاري التحميل...</span>
                        </div>
                    </div>
                `;
                modal.show();

                // Fetch user activities
                const response = await fetch(`${CONFIG.USER_ACTIVITIES_ENDPOINT}${userId}/`, {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': Utils.getCsrfToken(),
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                this.renderUserActivities(data.activities || [], userItem.dataset);

            } catch (error) {
                Utils.log(`Error loading user activities: ${error.message}`, 'error');
                this.showError('فشل في تحميل نشاطات المستخدم');
            }
        },

        renderUserActivities: function(activities, userData) {
            const modalContent = document.getElementById('user-activities-content');

            if (activities.length === 0) {
                modalContent.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-history fa-2x text-muted mb-2"></i>
                        <p class="text-muted">لا توجد نشاطات حديثة لهذا المستخدم</p>
                    </div>
                `;
                return;
            }

            const activitiesHtml = activities.map(activity => this.createActivityHtml(activity)).join('');
            modalContent.innerHTML = `
                <div class="activities-list">
                    ${activitiesHtml}
                </div>
            `;
        },

        createActivityHtml: function(activity) {
            const iconClass = this.getActivityIconClass(activity.action_type);
            const timeAgo = this.formatTimeAgo(activity.timestamp);

            // إضافة رابط تفاعلي إذا كان متوفراً
            const linkHtml = activity.link_url && activity.link_text ?
                `<a href="${activity.link_url}" class="activity-link" target="_blank" title="${activity.link_text}">
                    <i class="fas fa-external-link-alt"></i> ${activity.link_text}
                </a>` : '';

            // إضافة تفاصيل الكائن إذا كانت متوفرة
            const entityDetails = activity.entity_name ?
                `<div class="activity-entity">
                    <small class="text-muted">
                        <i class="fas fa-tag"></i> ${activity.entity_type}: ${activity.entity_name}
                    </small>
                </div>` : '';

            return `
                <div class="activity-item">
                    <div class="activity-icon ${iconClass}">
                        <i class="fas ${this.getActivityIcon(activity.action_type)}"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">${activity.title}</div>
                        <div class="activity-description">${activity.description}</div>
                        ${entityDetails}
                        ${linkHtml ? `<div class="activity-link-container">${linkHtml}</div>` : ''}
                        <div class="activity-time">${timeAgo}</div>
                    </div>
                </div>
            `;
        },

        getActivityIconClass: function(actionType) {
            const classes = {
                'login': 'login',
                'logout': 'logout',
                'view': 'view',
                'create': 'create',
                'update': 'update',
                'delete': 'delete'
            };
            return classes[actionType] || 'other';
        },

        getActivityIcon: function(actionType) {
            const icons = {
                'login': 'fa-sign-in-alt',
                'logout': 'fa-sign-out-alt',
                'view': 'fa-eye',
                'create': 'fa-plus',
                'update': 'fa-edit',
                'delete': 'fa-trash',
                'search': 'fa-search',
                'export': 'fa-download',
                'import': 'fa-upload'
            };
            return icons[actionType] || 'fa-circle';
        },

        formatTimeAgo: function(timestamp) {
            const now = new Date();
            const time = new Date(timestamp);
            const diff = now - time;

            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);

            if (minutes < 1) return 'الآن';
            if (minutes < 60) return `منذ ${minutes} دقيقة`;
            if (hours < 24) return `منذ ${hours} ساعة`;
            return `منذ ${days} يوم`;
        },

        refresh: function() {
            if (this.refreshBtn) {
                this.refreshBtn.classList.add('refreshing');
            }
            this.loadUsers();
            setTimeout(() => {
                if (this.refreshBtn) {
                    this.refreshBtn.classList.remove('refreshing');
                }
            }, 1000);
        },

        startAutoUpdate: function() {
            this.updateInterval = setInterval(() => {
                this.loadUsers();
            }, CONFIG.UPDATE_INTERVAL);
        },

        stopAutoUpdate: function() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
                this.updateInterval = null;
            }
        },

        showLoading: function() {
            if (!this.usersList) return;

            this.usersList.innerHTML = `
                <div class="loading-indicator">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">جاري التحميل...</span>
                    </div>
                    <span class="loading-text">جاري تحديث البيانات...</span>
                </div>
            `;
        },

        showError: function(message) {
            if (!this.usersList) return;

            this.usersList.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-exclamation-triangle fa-2x text-danger mb-2"></i>
                    <p class="text-danger small">${message}</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="OnlineUsersSidebar.UsersManager.refresh()">
                        <i class="fas fa-sync-alt"></i> إعادة المحاولة
                    </button>
                </div>
            `;
        }
    };

    // ===== MAIN INITIALIZATION =====
    const OnlineUsersSidebar = {
        SidebarManager: SidebarManager,
        UsersManager: UsersManager,

        init: function() {
            Utils.log('Initializing Online Users Sidebar...');

            // Initialize components
            SidebarManager.init();
            UsersManager.init();

            // Setup global error handling
            window.addEventListener('error', (e) => {
                Utils.log(`Global error: ${e.error}`, 'error');
            });

            // Setup visibility change handling
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    UsersManager.stopAutoUpdate();
                } else {
                    UsersManager.loadUsers();
                    UsersManager.startAutoUpdate();
                }
            });

            Utils.log('Online Users Sidebar initialized successfully');
        }
    };

    // ===== AUTO INITIALIZE =====
    document.addEventListener('DOMContentLoaded', function() {
        // Check if sidebar exists
        if (document.getElementById('online-users-sidebar')) {
            OnlineUsersSidebar.init();
        }
    });

    // Enhanced functionality for filter tabs and user interactions
    OnlineUsersSidebar.enhancedFeatures = {
        // Handle filter tab switching
        handleFilterTab(tab) {
            // Remove active class from all tabs
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));

            // Add active class to clicked tab
            tab.classList.add('active');

            // Get filter type
            const filter = tab.dataset.filter;

            // Filter users based on selection
            this.filterUsers(filter);
        },

        // Filter users based on selected tab
        filterUsers(filter) {
            const userItems = document.querySelectorAll('.user-item');

            userItems.forEach(item => {
                const isOnline = item.classList.contains('online');
                const department = item.dataset.department;

                let shouldShow = true;

                switch(filter) {
                    case 'online':
                        shouldShow = isOnline;
                        break;
                    case 'departments':
                        shouldShow = department && department !== 'undefined';
                        break;
                    case 'all':
                    default:
                        shouldShow = true;
                        break;
                }

                item.style.display = shouldShow ? 'block' : 'none';
            });

            // Update user count
            this.updateUserCount();
        },

        // Update user count display
        updateUserCount() {
            const visibleUsers = document.querySelectorAll('.user-item:not([style*="display: none"])');
            const onlineCount = Array.from(visibleUsers).filter(item => item.classList.contains('online')).length;

            const countElement = document.querySelector('.user-count');
            if (countElement) {
                countElement.textContent = `${onlineCount} متصل من ${visibleUsers.length}`;
            }
        }
    };

    // Add enhanced event listeners
    document.addEventListener('click', (e) => {
        // Handle filter tab clicks
        if (e.target.matches('.filter-tab')) {
            e.preventDefault();
            OnlineUsersSidebar.enhancedFeatures.handleFilterTab(e.target);
        }
    });

    // ===== EXPOSE TO GLOBAL SCOPE =====
    window.OnlineUsersSidebar = OnlineUsersSidebar;

})();