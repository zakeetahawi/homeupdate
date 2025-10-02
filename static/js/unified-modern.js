/**
 * UNIFIED MODERN JAVASCRIPT - OPTIMIZED
 * Generated: 2025-10-02
 * Purpose: Single optimized JS file for core functionality
 */

(function() {
  'use strict';

  /* ========== SIDEBAR MANAGEMENT ========== */
  class SidebarManager {
    constructor() {
      this.sidebar = document.querySelector('.modern-sidebar');
      this.overlay = document.querySelector('.sidebar-overlay');
      this.menuToggle = document.querySelector('.menu-toggle');
      this.init();
    }

    init() {
      if (!this.sidebar || !this.overlay || !this.menuToggle) return;
      
      this.menuToggle.addEventListener('click', () => this.toggle());
      this.overlay.addEventListener('click', () => this.close());
      
      // Close on escape key
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.sidebar.classList.contains('open')) {
          this.close();
        }
      });

      // Handle submenu toggles
      const submenuToggles = document.querySelectorAll('.has-submenu > .sidebar-menu-link');
      submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
          e.preventDefault();
          const parent = toggle.parentElement;
          parent.classList.toggle('expanded');
        });
      });
    }

    toggle() {
      this.sidebar.classList.toggle('open');
      this.overlay.classList.toggle('active');
      document.body.style.overflow = this.sidebar.classList.contains('open') ? 'hidden' : '';
    }

    close() {
      this.sidebar.classList.remove('open');
      this.overlay.classList.remove('active');
      document.body.style.overflow = '';
    }

    open() {
      this.sidebar.classList.add('open');
      this.overlay.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  /* ========== DROPDOWN MANAGEMENT ========== */
  class DropdownManager {
    constructor() {
      this.dropdowns = new Map();
      this.init();
    }

    init() {
      const triggers = document.querySelectorAll('[data-dropdown-trigger]');
      triggers.forEach(trigger => {
        const targetId = trigger.getAttribute('data-dropdown-trigger');
        const dropdown = document.querySelector(`[data-dropdown="${targetId}"]`);
        
        if (dropdown) {
          this.dropdowns.set(targetId, { trigger, dropdown });
          trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle(targetId);
          });
        }
      });

      // Close dropdowns when clicking outside
      document.addEventListener('click', (e) => {
        if (!e.target.closest('[data-dropdown]') && !e.target.closest('[data-dropdown-trigger]')) {
          this.closeAll();
        }
      });

      // Close on escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeAll();
        }
      });
    }

    toggle(id) {
      const item = this.dropdowns.get(id);
      if (!item) return;

      const isOpen = item.dropdown.classList.contains('show');
      this.closeAll();
      
      if (!isOpen) {
        item.dropdown.classList.add('show');
        this.positionDropdown(item.trigger, item.dropdown);
      }
    }

    close(id) {
      const item = this.dropdowns.get(id);
      if (item) {
        item.dropdown.classList.remove('show');
      }
    }

    closeAll() {
      this.dropdowns.forEach((item) => {
        item.dropdown.classList.remove('show');
      });
    }

    positionDropdown(trigger, dropdown) {
      const triggerRect = trigger.getBoundingClientRect();
      const dropdownRect = dropdown.getBoundingClientRect();
      const viewportWidth = window.innerWidth;

      // Center below trigger by default
      let left = triggerRect.left + (triggerRect.width / 2) - (dropdownRect.width / 2);

      // Adjust if would go off-screen
      if (left < 10) left = 10;
      if (left + dropdownRect.width > viewportWidth - 10) {
        left = viewportWidth - dropdownRect.width - 10;
      }

      dropdown.style.left = `${left}px`;
      dropdown.style.top = `${triggerRect.bottom + 8}px`;
    }
  }

  /* ========== NOTIFICATION SYSTEM ========== */
  class NotificationManager {
    constructor() {
      this.badge = document.querySelector('#notification-count-badge');
      this.dropdown = document.querySelector('[data-dropdown="notifications"]');
      this.pollingInterval = 30000; // 30 seconds
      this.init();
    }

    init() {
      if (!this.dropdown) return;
      
      // Initial load
      this.loadNotifications();
      
      // Poll for updates
      setInterval(() => this.loadNotifications(), this.pollingInterval);
    }

    async loadNotifications() {
      try {
        const response = await fetch('/api/notifications/recent/', {
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': this.getCSRFToken()
          }
        });
        
        if (!response.ok) throw new Error('Failed to load notifications');
        
        const data = await response.json();
        this.updateBadge(data.unread_count);
        this.renderNotifications(data.notifications);
      } catch (error) {
        console.error('Error loading notifications:', error);
      }
    }

    updateBadge(count) {
      if (!this.badge) return;
      
      if (count > 0) {
        this.badge.textContent = count > 99 ? '99+' : count;
        this.badge.style.display = 'block';
      } else {
        this.badge.style.display = 'none';
      }
    }

    renderNotifications(notifications) {
      const container = this.dropdown?.querySelector('.dropdown-body');
      if (!container) return;

      if (notifications.length === 0) {
        container.innerHTML = '<div class="dropdown-item text-center text-muted">لا توجد إشعارات</div>';
        return;
      }

      container.innerHTML = notifications.map(notif => `
        <a href="${notif.url || '#'}" class="dropdown-item ${notif.is_read ? '' : 'unread'}">
          <div class="d-flex align-items-start gap-md">
            <div class="notification-icon">
              <i class="${notif.icon || 'fas fa-bell'}"></i>
            </div>
            <div class="flex-grow-1">
              <div class="notification-title">${notif.title}</div>
              <div class="notification-message">${notif.message}</div>
              <div class="notification-time">${notif.time_ago}</div>
            </div>
          </div>
        </a>
      `).join('');
    }

    async markAsRead(notificationId) {
      try {
        await fetch(`/api/notifications/${notificationId}/mark-read/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        this.loadNotifications();
      } catch (error) {
        console.error('Error marking notification as read:', error);
      }
    }

    async markAllAsRead() {
      try {
        await fetch('/api/notifications/mark-all-read/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        this.loadNotifications();
      } catch (error) {
        console.error('Error marking all notifications as read:', error);
      }
    }

    getCSRFToken() {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
             document.querySelector('meta[name="csrf-token"]')?.content || '';
    }
  }

  /* ========== TABLE ENHANCEMENT ========== */
  class TableEnhancer {
    constructor() {
      this.tables = document.querySelectorAll('table:not(.no-enhance)');
      this.init();
    }

    init() {
      this.tables.forEach(table => {
        // Add modern-table class
        table.classList.add('modern-table');
        
        // Make responsive
        if (!table.parentElement.classList.contains('table-responsive')) {
          const wrapper = document.createElement('div');
          wrapper.className = 'table-responsive';
          table.parentNode.insertBefore(wrapper, table);
          wrapper.appendChild(table);
        }

        // Add sorting if enabled
        if (table.hasAttribute('data-sortable')) {
          this.addSorting(table);
        }
      });
    }

    addSorting(table) {
      const headers = table.querySelectorAll('thead th');
      headers.forEach((header, index) => {
        if (header.hasAttribute('data-sortable-column')) {
          header.style.cursor = 'pointer';
          header.addEventListener('click', () => this.sortTable(table, index));
        }
      });
    }

    sortTable(table, columnIndex) {
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      
      const sortedRows = rows.sort((a, b) => {
        const aValue = a.cells[columnIndex]?.textContent.trim() || '';
        const bValue = b.cells[columnIndex]?.textContent.trim() || '';
        return aValue.localeCompare(bValue, 'ar');
      });

      tbody.innerHTML = '';
      sortedRows.forEach(row => tbody.appendChild(row));
    }
  }

  /* ========== FORM ENHANCEMENTS ========== */
  class FormEnhancer {
    constructor() {
      this.forms = document.querySelectorAll('form:not(.no-enhance)');
      this.init();
    }

    init() {
      this.forms.forEach(form => {
        // Add modern classes
        form.querySelectorAll('input, select, textarea').forEach(input => {
          if (!input.classList.contains('modern-form-control')) {
            input.classList.add('modern-form-control');
          }
        });

        // Add validation feedback
        form.addEventListener('submit', (e) => this.handleSubmit(e, form));
      });
    }

    handleSubmit(e, form) {
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;

      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          field.classList.add('is-invalid');
          this.showError(field, 'هذا الحقل مطلوب');
        } else {
          field.classList.remove('is-invalid');
          this.removeError(field);
        }
      });

      if (!isValid) {
        e.preventDefault();
      }
    }

    showError(field, message) {
      let error = field.parentElement.querySelector('.error-message');
      if (!error) {
        error = document.createElement('div');
        error.className = 'error-message text-danger small mt-1';
        field.parentElement.appendChild(error);
      }
      error.textContent = message;
    }

    removeError(field) {
      const error = field.parentElement.querySelector('.error-message');
      if (error) {
        error.remove();
      }
    }
  }

  /* ========== LAZY LOADING ========== */
  class LazyLoader {
    constructor() {
      this.observer = null;
      this.init();
    }

    init() {
      if ('IntersectionObserver' in window) {
        this.observer = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              this.loadElement(entry.target);
              this.observer.unobserve(entry.target);
            }
          });
        }, {
          rootMargin: '50px'
        });

        // Observe all lazy-loadable elements
        document.querySelectorAll('[data-lazy-src]').forEach(el => {
          this.observer.observe(el);
        });
      }
    }

    loadElement(element) {
      const src = element.getAttribute('data-lazy-src');
      if (!src) return;

      if (element.tagName === 'IMG') {
        element.src = src;
        element.removeAttribute('data-lazy-src');
      } else {
        // Load other content types
        fetch(src)
          .then(response => response.text())
          .then(html => {
            element.innerHTML = html;
            element.removeAttribute('data-lazy-src');
          })
          .catch(error => console.error('Lazy load error:', error));
      }
    }
  }

  /* ========== TOAST NOTIFICATIONS ========== */
  class ToastManager {
    constructor() {
      this.container = null;
      this.init();
    }

    init() {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      this.container.style.cssText = 'position:fixed;top:80px;left:20px;z-index:9999;';
      document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
      const toast = document.createElement('div');
      toast.className = `toast toast-${type} fade-in`;
      toast.style.cssText = `
        background:var(--white);
        padding:1rem 1.5rem;
        border-radius:8px;
        box-shadow:0 4px 12px rgba(0,0,0,0.15);
        margin-bottom:0.5rem;
        border-right:4px solid var(--${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'});
        max-width:400px;
      `;
      toast.innerHTML = `
        <div class="d-flex align-items-center gap-md">
          <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
          <div>${message}</div>
        </div>
      `;

      this.container.appendChild(toast);

      setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
  }

  /* ========== INITIALIZATION ========== */
  class App {
    constructor() {
      this.sidebar = null;
      this.dropdown = null;
      this.notifications = null;
      this.tables = null;
      this.forms = null;
      this.lazyLoader = null;
      this.toast = null;
    }

    init() {
      // Wait for DOM to be ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.initComponents());
      } else {
        this.initComponents();
      }
    }

    initComponents() {
      this.sidebar = new SidebarManager();
      this.dropdown = new DropdownManager();
      this.notifications = new NotificationManager();
      this.tables = new TableEnhancer();
      this.forms = new FormEnhancer();
      this.lazyLoader = new LazyLoader();
      this.toast = new ToastManager();

      // Make toast available globally
      window.showToast = (message, type, duration) => {
        this.toast.show(message, type, duration);
      };

      // Expose managers globally for external access
      window.AppManagers = {
        sidebar: this.sidebar,
        dropdown: this.dropdown,
        notifications: this.notifications
      };

      console.log('✅ Modern UI initialized successfully');
    }
  }

  // Initialize the app
  const app = new App();
  app.init();

  // Export for module systems
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = app;
  }

})();
