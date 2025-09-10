/**
 * Assignment Notifications System
 * Handles popup notifications for complaint assignments on dashboard
 */

class AssignmentNotifications {
    constructor() {
        this.checkInterval = 30000; // Check every 30 seconds
        this.notificationQueue = [];
        this.isInitialized = false;
        this.lastCheckTime = null;
        
        this.init();
    }
    
    init() {
        if (this.isInitialized) return;
        
        console.log('🔔 Initializing Assignment Notifications System...');
        
        // Check for notifications immediately
        this.checkForAssignments();
        
        // Set up periodic checking
        setInterval(() => {
            this.checkForAssignments();
        }, this.checkInterval);
        
        this.isInitialized = true;
        console.log('✅ Assignment Notifications System initialized');
    }
    
    async checkForAssignments() {
        try {
            const response = await fetch('/complaints/api/assignment-notifications/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.processNotifications(data.notifications);
                this.updateAssignmentBadge(data.unread_assignments);
            }
            
        } catch (error) {
            console.error('❌ Error checking for assignments:', error);
        }
    }
    
    processNotifications(notifications) {
        // Filter new notifications since last check
        const newNotifications = notifications.filter(notification => {
            if (!this.lastCheckTime) return !notification.is_read;
            
            const notificationTime = new Date(notification.created_at);
            return notificationTime > this.lastCheckTime && !notification.is_read;
        });
        
        // Show popup for new notifications
        newNotifications.forEach(notification => {
            this.showAssignmentPopup(notification);
        });
        
        this.lastCheckTime = new Date();
    }
    
    showAssignmentPopup(notification) {
        // Check if SweetAlert2 is available
        if (typeof Swal === 'undefined') {
            console.warn('⚠️ SweetAlert2 not available, falling back to browser notification');
            this.showBrowserNotification(notification);
            return;
        }
        
        const isAssignment = notification.type === 'assignment';
        const icon = isAssignment ? 'info' : 'warning';
        const color = isAssignment ? '#17a2b8' : '#ffc107';
        
        Swal.fire({
            title: 'إشعار تعيين شكوى',
            html: `
                <div class="text-start">
                    <div class="alert alert-${isAssignment ? 'info' : 'warning'} mb-3">
                        <h6 class="mb-2">
                            <i class="fas fa-${isAssignment ? 'user-check' : 'exclamation-triangle'} me-2"></i>
                            ${notification.title}
                        </h6>
                        <p class="mb-2">${notification.message}</p>
                        <div class="row">
                            <div class="col-6">
                                <small class="text-muted">
                                    <i class="fas fa-hashtag me-1"></i>
                                    ${notification.complaint_number}
                                </small>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">
                                    <i class="fas fa-user me-1"></i>
                                    ${notification.customer_name}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            `,
            icon: icon,
            showCancelButton: true,
            confirmButtonColor: color,
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'عرض الشكوى',
            cancelButtonText: 'إغلاق',
            customClass: {
                container: 'swal-rtl'
            },
            timer: 15000, // Auto close after 15 seconds
            timerProgressBar: true,
            allowOutsideClick: false
        }).then((result) => {
            if (result.isConfirmed) {
                // Navigate to complaint
                window.location.href = notification.url;
            }
            
            // Mark notification as read if it's a real notification (has numeric ID)
            if (typeof notification.id === 'number') {
                this.markAsRead(notification.id);
            }
        });
        
        // Play notification sound if available
        this.playNotificationSound();
    }
    
    showBrowserNotification(notification) {
        // Fallback to browser notification if SweetAlert2 is not available
        if ('Notification' in window) {
            if (Notification.permission === 'granted') {
                new Notification(notification.title, {
                    body: notification.message,
                    icon: '/static/images/logo.png',
                    tag: `assignment-${notification.id}`
                });
            } else if (Notification.permission !== 'denied') {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        new Notification(notification.title, {
                            body: notification.message,
                            icon: '/static/images/logo.png',
                            tag: `assignment-${notification.id}`
                        });
                    }
                });
            }
        }
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/complaints/api/assignment-notifications/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                }
            });
            
            if (response.ok) {
                console.log('✅ Notification marked as read:', notificationId);
            }
            
        } catch (error) {
            console.error('❌ Error marking notification as read:', error);
        }
    }
    
    updateAssignmentBadge(count) {
        const badge = document.querySelector('#assignment-notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline';
                badge.classList.add('animate__animated', 'animate__pulse');
            } else {
                badge.style.display = 'none';
                badge.classList.remove('animate__animated', 'animate__pulse');
            }
        }
    }
    
    playNotificationSound() {
        // Try to play a notification sound
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Ignore audio play errors (user interaction required)
            });
        } catch (error) {
            // Ignore audio errors
        }
    }
    
    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
}

// Initialize assignment notifications when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on dashboard pages
    if (window.location.pathname.includes('dashboard') || 
        window.location.pathname === '/' || 
        window.location.pathname.includes('complaints')) {
        
        window.assignmentNotifications = new AssignmentNotifications();
    }
});

// Export for manual initialization if needed
window.AssignmentNotifications = AssignmentNotifications;
