/**
 * base-notifications.js
 * =======================
 * نظام الإشعارات المُستخرج من base.html
 * تاريخ الاستخراج: 2026-02-15
 *
 * يعتمد على data attributes في عنصر body:
 *   data-notifications-count-url
 *   data-notifications-recent-url
 *   data-notifications-mark-all-url
 *   data-notifications-list-url
 *
 * يحتوي على:
 * - تحديث عداد الإشعارات العامة
 * - إشعارات التعيين (الشكاوى)
 * - إشعارات الشكاوى غير المحلولة
 * - Popup الشكاوى المسندة والمصعدة
 * - Popup الإشعارات العامة
 * - القائمة المنسدلة للإشعارات
 * - CSRF handling
 */

(function () {
    'use strict';

    // ═══════════════════════════════════════════════════════════════════
    // URL Configuration — from body data attributes
    // ═══════════════════════════════════════════════════════════════════

    var body = document.body;
    var URLS = {
        notificationsCount: body.getAttribute('data-notifications-count-url') || '',
        notificationsRecent: body.getAttribute('data-notifications-recent-url') || '',
        notificationsMarkAll: body.getAttribute('data-notifications-mark-all-url') || '',
        notificationsList: body.getAttribute('data-notifications-list-url') || ''
    };

    // ═══════════════════════════════════════════════════════════════════
    // 1. تحديث عداد الإشعارات العامة
    // ═══════════════════════════════════════════════════════════════════

    window.updateNotificationCount = function () {
        if (!URLS.notificationsCount) return;
        fetch(URLS.notificationsCount + '?_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    var badge = document.querySelector('#notification-count-badge');
                    if (badge) {
                        if (data.count > 0) {
                            badge.textContent = data.count;
                            badge.style.display = 'inline';
                        } else {
                            badge.style.display = 'none';
                        }
                    }
                }
            })
            .catch(function () {});
    };

    // ═══════════════════════════════════════════════════════════════════
    // 2. تحديث إشعارات التعيين
    // ═══════════════════════════════════════════════════════════════════

    window.updateAssignmentNotifications = function () {
        var list = document.querySelector('#assignment-notifications-list');
        if (!list) return;

        fetch('/complaints/api/assignment-notifications/')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    var badge = document.querySelector('#assignment-notification-badge');
                    var list = document.querySelector('#assignment-notifications-list');
                    var loading = document.querySelector('#assignment-notifications-loading');
                    var empty = document.querySelector('#assignment-notifications-empty');

                    if (badge) {
                        if (data.unread_assignments > 0) {
                            badge.textContent = data.unread_assignments;
                            badge.style.display = 'inline';
                        } else {
                            badge.style.display = 'none';
                        }
                    }

                    if (list && loading && empty) {
                        loading.style.display = 'none';

                        if (data.notifications.length > 0) {
                            empty.style.display = 'none';
                            var html = '';

                            data.notifications.forEach(function (notification) {
                                var isUnread = !notification.is_read;
                                html += '<li>' +
                                    '<a class="dropdown-item py-3 px-3 ' + (isUnread ? 'bg-light border-start border-info border-3' : '') + '" href="' + notification.url + '" style="border-radius: 8px; margin: 2px 8px; white-space: normal; word-wrap: break-word;">' +
                                    '<div class="d-flex justify-content-between align-items-start">' +
                                    '<div class="flex-grow-1">' +
                                    '<h6 class="mb-1 fw-bold">' + notification.title + '</h6>' +
                                    '<p class="mb-1 text-muted small">' + notification.message + '</p>' +
                                    '<div class="d-flex justify-content-between">' +
                                    '<small class="text-muted"><i class="fas fa-hashtag me-1"></i>' + notification.complaint_number + '</small>' +
                                    '<small class="text-muted">' + notification.created_at + '</small>' +
                                    '</div></div>' +
                                    (isUnread ? '<span class="badge bg-info ms-2">جديد</span>' : '') +
                                    '</div></a></li>';
                            });

                            list.innerHTML = html;
                        } else {
                            empty.style.display = 'block';
                            list.innerHTML = '';
                        }
                    }
                }
            })
            .catch(function () {});
    };

    // ═══════════════════════════════════════════════════════════════════
    // 3. تحديث عداد إشعارات الشكاوى
    // ═══════════════════════════════════════════════════════════════════

    window.updateComplaintsNotificationCount = function () {
        var complaintsCenterDropdown = document.querySelector('#complaintsCenterDropdown');
        if (!complaintsCenterDropdown) return;

        fetch('/complaints/api/unresolved-stats/?_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    var unresolvedBadge = document.querySelector('#unresolved-complaints-badge');
                    var unresolvedDisplay = document.querySelector('#unresolved-count-display');

                    if (unresolvedBadge && unresolvedDisplay) {
                        if (data.unresolved_count > 0) {
                            unresolvedBadge.textContent = data.unresolved_count;
                            unresolvedBadge.style.display = 'inline';
                            unresolvedDisplay.textContent = data.unresolved_count;

                            if (data.urgent_count > 0) {
                                unresolvedBadge.className = 'position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger';
                            } else if (data.overdue_count > 0) {
                                unresolvedBadge.className = 'position-absolute top-0 start-100 translate-middle badge rounded-pill bg-warning';
                            } else {
                                unresolvedBadge.className = 'position-absolute top-0 start-100 translate-middle badge rounded-pill bg-info';
                            }
                        } else {
                            unresolvedBadge.style.display = 'none';
                            unresolvedDisplay.textContent = '0';
                        }
                    }
                }
            })
            .catch(function () {});

        fetch('/complaints/api/notifications/?_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    var notificationBadge = document.querySelector('#complaints-notification-count-badge');
                    var notificationDisplay = document.querySelector('#new-notifications-display');

                    if (notificationBadge && notificationDisplay) {
                        if (data.unread_count > 0) {
                            notificationBadge.textContent = data.unread_count;
                            notificationBadge.style.display = 'inline';
                            notificationDisplay.textContent = data.unread_count;
                        } else {
                            notificationBadge.style.display = 'none';
                            notificationDisplay.textContent = '0';
                        }
                    }
                }
            })
            .catch(function () {});
    };

    // ═══════════════════════════════════════════════════════════════════
    // 4. تحميل إشعارات الشكاوى في القائمة المنسدلة
    // ═══════════════════════════════════════════════════════════════════

    window.loadComplaintsNotifications = function () {
        var loadingElement = document.getElementById('complaints-notifications-loading');
        var emptyElement = document.getElementById('complaints-notifications-empty');
        var listElement = document.getElementById('complaints-notifications-list');

        if (loadingElement) loadingElement.style.display = 'block';
        if (emptyElement) emptyElement.style.display = 'none';
        if (listElement) listElement.innerHTML = '';

        fetch('/complaints/api/notifications/?limit=5&_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (loadingElement) loadingElement.style.display = 'none';

                if (data.success && data.notifications && data.notifications.length > 0) {
                    var html = '';
                    data.notifications.forEach(function (notification) {
                        var typeIcon = getComplaintNotificationIcon(notification.type);
                        var ago = getTimeAgo(notification.created_at);

                        html += '<li class="dropdown-item-text p-3 border-bottom">' +
                            '<div class="d-flex align-items-start">' +
                            '<div class="me-2"><i class="' + typeIcon + ' text-primary"></i></div>' +
                            '<div class="flex-grow-1">' +
                            '<h6 class="mb-1 fw-bold">' + notification.title + '</h6>' +
                            '<p class="mb-1 small text-muted">' + notification.message + '</p>' +
                            '<small class="text-muted"><i class="fas fa-clock me-1"></i>' + ago +
                            (notification.complaint_number ? ' | ' + notification.complaint_number : '') +
                            '</small></div></div></li>';
                    });

                    if (listElement) listElement.innerHTML = html;
                } else {
                    if (emptyElement) emptyElement.style.display = 'block';
                }
            })
            .catch(function () {
                if (loadingElement) loadingElement.style.display = 'none';
                if (emptyElement) emptyElement.style.display = 'block';
            });
    };

    // ═══════════════════════════════════════════════════════════════════
    // 5. Helper Functions
    // ═══════════════════════════════════════════════════════════════════

    function getComplaintNotificationIcon(type) {
        var icons = {
            'new_complaint': 'fas fa-plus-circle',
            'status_change': 'fas fa-exchange-alt',
            'assignment': 'fas fa-user-tag',
            'escalation': 'fas fa-arrow-up',
            'deadline': 'fas fa-clock',
            'overdue': 'fas fa-exclamation-triangle',
            'comment': 'fas fa-comment'
        };
        return icons[type] || 'fas fa-bell';
    }

    window.getTimeAgo = function (dateString) {
        var now = new Date();
        var date = new Date(dateString);
        var diffInSeconds = Math.floor((now - date) / 1000);

        if (diffInSeconds < 60) return 'الآن';
        if (diffInSeconds < 3600) return Math.floor(diffInSeconds / 60) + ' دقيقة';
        if (diffInSeconds < 86400) return Math.floor(diffInSeconds / 3600) + ' ساعة';
        return Math.floor(diffInSeconds / 86400) + ' يوم';
    };

    function timeAgo(dateString) {
        return window.getTimeAgo(dateString);
    }

    function getPriorityColor(priority) {
        var colors = { 'high': 'danger', 'medium': 'warning', 'low': 'success' };
        return colors[priority] || 'secondary';
    }

    function getPriorityText(priority) {
        var texts = { 'high': 'عالية', 'medium': 'متوسطة', 'low': 'منخفضة' };
        return texts[priority] || 'غير محدد';
    }

    // ═══════════════════════════════════════════════════════════════════
    // 6. مسح جميع إشعارات الشكاوى
    // ═══════════════════════════════════════════════════════════════════

    window.clearComplaintsNotifications = function () {
        if (confirm('هل أنت متأكد من مسح جميع إشعارات الشكاوى؟')) {
            fetch('/complaints/api/notifications/clear/', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (data.success) {
                        updateComplaintsNotificationCount();
                        loadComplaintsNotifications();

                        var dropdown = document.getElementById('complaintsCenterDropdown');
                        if (dropdown) {
                            var bsDropdown = bootstrap.Dropdown.getInstance(dropdown);
                            if (bsDropdown) bsDropdown.hide();
                        }

                        showNotificationMessage('تم مسح ' + (data.updated_count || 0) + ' إشعار بنجاح', 'success');
                    } else {
                        showNotificationMessage('حدث خطأ أثناء مسح الإشعارات', 'error');
                    }
                })
                .catch(function () {
                    showNotificationMessage('حدث خطأ أثناء مسح الإشعارات', 'error');
                });
        }
    };

    // ═══════════════════════════════════════════════════════════════════
    // 7. Popup الشكاوى المسندة
    // ═══════════════════════════════════════════════════════════════════

    window.checkAssignedComplaints = function () {
        var snoozedUntil = localStorage.getItem('complaintsPopupSnoozed');
        if (snoozedUntil && new Date() < new Date(snoozedUntil)) return;

        fetch('/complaints/api/assigned/?_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success && data.complaints && data.complaints.length > 0) {
                    showAssignedComplaintsPopup(data.complaints);
                }
            })
            .catch(function () {});
    };

    function showAssignedComplaintsPopup(complaints) {
        var popup = document.getElementById('assignedComplaintsPopup');
        var content = document.getElementById('assignedComplaintsContent');
        if (!popup || !content) return;

        var html = '';
        complaints.forEach(function (complaint) {
            var priorityClass = 'complaint-priority-' + complaint.priority;
            var ago = getTimeAgo(complaint.created_at);

            html += '<div class="complaint-item ' + priorityClass + '">' +
                '<div class="d-flex justify-content-between align-items-start mb-2">' +
                '<h6 class="mb-0"><a href="/complaints/' + complaint.id + '/" class="text-decoration-none">شكوى رقم ' + complaint.complaint_number + '</a></h6>' +
                '<span class="badge bg-' + getPriorityColor(complaint.priority) + '">' + getPriorityText(complaint.priority) + '</span>' +
                '</div>' +
                '<p class="mb-1 small">' + complaint.title + '</p>' +
                '<div class="d-flex justify-content-between align-items-center">' +
                '<small class="text-muted">العميل: ' + complaint.customer_name + '</small>' +
                '<small class="text-muted">' + ago + '</small>' +
                '</div>' +
                (complaint.deadline ? '<div class="mt-1"><small class="text-danger"><i class="fas fa-clock"></i> الموعد النهائي: ' + new Date(complaint.deadline).toLocaleDateString('ar-EG') + '</small></div>' : '') +
                '</div>';
        });

        content.innerHTML = html;
        popup.style.display = 'block';
    }

    window.hideComplaintsPopup = function () {
        var popup = document.getElementById('assignedComplaintsPopup');
        if (popup) popup.style.display = 'none';
    };

    window.snoozeComplaintsPopup = function () {
        var hours = prompt('كم ساعة تريد تأجيل الإشعارات؟ (افتراضي: 4 ساعات)', '4');
        if (hours && !isNaN(hours)) {
            var snoozeUntil = new Date();
            snoozeUntil.setHours(snoozeUntil.getHours() + parseInt(hours));
            localStorage.setItem('complaintsPopupSnoozed', snoozeUntil.toISOString());
            hideComplaintsPopup();
            showNotificationMessage('تم تأجيل إشعارات الشكاوى لمدة ' + hours + ' ساعة', 'info');
        }
    };

    // ═══════════════════════════════════════════════════════════════════
    // 8. Popup الشكاوى المصعدة
    // ═══════════════════════════════════════════════════════════════════

    window.checkEscalatedComplaints = function () {
        var snoozedUntil = localStorage.getItem('escalatedPopupSnoozed');
        if (snoozedUntil && new Date() < new Date(snoozedUntil)) return;

        fetch('/complaints/api/escalated/?_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success && data.complaints && data.complaints.length > 0) {
                    showEscalatedComplaintsPopup(data.complaints);
                }
            })
            .catch(function () {});
    };

    function showEscalatedComplaintsPopup(complaints) {
        var popup = document.getElementById('escalatedComplaintsPopup');
        var content = document.getElementById('escalatedComplaintsContent');
        if (!popup || !content) return;

        var html = '<div class="alert alert-danger mb-3"><i class="fas fa-fire me-2"></i><strong>تحذير:</strong> هذه الشكاوى مصعدة إليك وتحتاج تدخل فوري!</div>';

        complaints.forEach(function (complaint) {
            var ago = getTimeAgo(complaint.created_at);

            html += '<div class="complaint-item mb-3 p-3 border rounded">' +
                '<div class="d-flex justify-content-between align-items-start mb-2">' +
                '<h6 class="mb-0 text-danger">' +
                '<a href="/complaints/' + complaint.id + '/" class="text-decoration-none text-danger">' +
                '<i class="fas fa-fire me-1"></i>شكوى رقم ' + complaint.complaint_number +
                '</a></h6>' +
                '<span class="badge bg-danger">مصعدة</span>' +
                '</div>' +
                '<p class="mb-1 fw-bold">' + complaint.title + '</p>' +
                '<div class="alert alert-warning mb-2 py-2">' +
                '<small><i class="fas fa-exclamation-triangle me-1"></i><strong>سبب التصعيد:</strong> ' + complaint.escalation_reason + '</small>' +
                (complaint.escalation_description ? '<br><small class="text-muted">' + complaint.escalation_description + '</small>' : '') +
                '</div>' +
                '<div class="d-flex justify-content-between align-items-center mb-2">' +
                '<small class="text-muted">العميل: ' + complaint.customer_name + '</small>' +
                '<small class="text-muted">المسؤول: ' + complaint.assigned_to + '</small>' +
                '</div>' +
                '<div class="d-flex justify-content-between align-items-center">' +
                '<small class="text-danger"><i class="fas fa-clock"></i> منذ ' + ago + '</small>' +
                (complaint.deadline ? '<small class="text-danger fw-bold"><i class="fas fa-exclamation-triangle"></i> تجاوز الموعد النهائي</small>' : '') +
                '</div></div>';
        });

        content.innerHTML = html;
        popup.style.display = 'block';
    }

    window.hideEscalatedPopup = function () {
        var popup = document.getElementById('escalatedComplaintsPopup');
        if (popup) popup.style.display = 'none';
    };

    window.snoozeEscalatedPopup = function () {
        var hours = prompt('كم ساعة تريد تأجيل إشعارات الشكاوى المصعدة؟ (افتراضي: 2 ساعة)', '2');
        if (hours && !isNaN(hours)) {
            var snoozeUntil = new Date();
            snoozeUntil.setHours(snoozeUntil.getHours() + parseInt(hours));
            localStorage.setItem('escalatedPopupSnoozed', snoozeUntil.toISOString());
            hideEscalatedPopup();
            showNotificationMessage('تم تأجيل إشعارات الشكاوى المصعدة لمدة ' + hours + ' ساعة', 'warning');
        }
    };

    // ═══════════════════════════════════════════════════════════════════
    // 9. Popup الإشعارات العامة
    // ═══════════════════════════════════════════════════════════════════

    window.checkSystemNotifications = function () {
        var snoozedUntil = localStorage.getItem('systemPopupSnoozed');
        if (snoozedUntil && new Date() < new Date(snoozedUntil)) return;

        var complaintsPopup = document.getElementById('assignedComplaintsPopup');
        var escalatedPopup = document.getElementById('escalatedComplaintsPopup');
        if ((complaintsPopup && complaintsPopup.style.display !== 'none') ||
            (escalatedPopup && escalatedPopup.style.display !== 'none')) return;

        fetch('/notifications/ajax/popup/?_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success && data.notifications && data.notifications.length > 0) {
                    showSystemNotificationsPopup(data.notifications);
                }
            })
            .catch(function () {});
    };

    function showSystemNotificationsPopup(notifications) {
        var popup = document.getElementById('systemNotificationsPopup');
        var content = document.getElementById('systemNotificationsContent');
        if (!popup || !content) return;

        var header = popup.querySelector('.system-popup-header');
        var hasUrgent = notifications.some(function (n) { return n.priority === 'urgent' || n.priority === 'high'; });
        if (hasUrgent) {
            header.style.background = 'linear-gradient(135deg, #dc3545, #c82333)';
        } else {
            header.style.background = 'linear-gradient(135deg, #0d6efd, #0b5ed7)';
        }

        var html = '';
        notifications.forEach(function (notification) {
            var ago = getTimeAgo(notification.created_at);
            var priorityBorderColor = {
                'urgent': '#dc3545', 'high': '#dc3545', 'normal': '#ffc107', 'low': '#28a745'
            }[notification.priority] || '#6c757d';

            html += '<div class="notification-popup-item" style="border-right: 4px solid ' + priorityBorderColor + ';">' +
                '<div class="d-flex justify-content-between align-items-start mb-1">' +
                '<div class="d-flex align-items-center">' +
                '<span class="notification-popup-icon" style="color: ' + notification.icon_color + '; background: ' + notification.icon_bg + ';">' +
                '<i class="' + notification.icon_class + '"></i></span>' +
                '<div class="me-2"><h6 class="mb-0 small fw-bold">' +
                '<a href="' + notification.url + '" class="text-decoration-none text-dark" onclick="markNotifAndGo(' + notification.id + ', \'' + notification.url + '\'); return false;">' +
                notification.title + '</a></h6></div></div>' +
                '<span class="badge bg-' + notification.priority_color + ' badge-sm">' + notification.priority_text + '</span>' +
                '</div>' +
                '<p class="mb-1 small text-muted pe-3">' + notification.message + '</p>' +
                '<div class="d-flex justify-content-between align-items-center">' +
                (notification.created_by ? '<small class="text-primary"><i class="fas fa-user-edit me-1"></i>' + notification.created_by + '</small>' : '<small></small>') +
                '<small class="text-muted">' + ago + '</small>' +
                '</div></div>';
        });

        content.innerHTML = html;
        popup.style.display = 'block';
    }

    window.hideSystemPopup = function () {
        var popup = document.getElementById('systemNotificationsPopup');
        if (popup) popup.style.display = 'none';
    };

    window.snoozeSystemPopup = function () {
        var hours = prompt('كم ساعة تريد تأجيل الإشعارات المنبثقة؟ (افتراضي: 1 ساعة)', '1');
        if (hours && !isNaN(hours)) {
            var snoozeUntil = new Date();
            snoozeUntil.setHours(snoozeUntil.getHours() + parseInt(hours));
            localStorage.setItem('systemPopupSnoozed', snoozeUntil.toISOString());
            hideSystemPopup();
            showNotificationMessage('تم تأجيل الإشعارات المنبثقة لمدة ' + hours + ' ساعة', 'info');
        }
    };

    // ═══════════════════════════════════════════════════════════════════
    // 10. Mark Notification & Navigate
    // ═══════════════════════════════════════════════════════════════════

    window.markNotifAndGo = function (notifId, url) {
        fetch('/notifications/mark-read/' + notifId + '/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                'Content-Type': 'application/json',
            },
        }).finally(function () {
            window.location.href = url;
        });
    };

    // ═══════════════════════════════════════════════════════════════════
    // 11. Dropdown Notification Management
    // ═══════════════════════════════════════════════════════════════════

    window.markDropdownNotificationAsRead = function (notificationId, targetUrl) {
        var csrfToken = getCsrfToken();
        if (!csrfToken) {
            window.location.href = targetUrl;
            return;
        }

        fetch('/notifications/mark-read/' + notificationId + '/', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    updateNotificationCount();
                    updateRecentNotifications();
                    setTimeout(function () { window.location.href = targetUrl; }, 500);
                } else {
                    window.location.href = targetUrl;
                }
            })
            .catch(function () {
                window.location.href = targetUrl;
            });
    };

    window.setupDropdownNotificationListeners = function () {
        var dropdownItems = document.querySelectorAll('.notification-dropdown-item, .dropdown-item[data-notification-id]');
        dropdownItems.forEach(function (item) {
            item.removeEventListener('click', handleNotificationClick);
            item.addEventListener('click', handleNotificationClick);
        });
    };

    function handleNotificationClick(event) {
        var notificationId = this.getAttribute('data-notification-id');
        var isRead = this.getAttribute('data-is-read') === 'true';
        var url = this.getAttribute('href');

        if (!isRead) {
            event.preventDefault();
            markDropdownNotificationAsRead(notificationId, url);
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // 12. Update Recent Notifications Dropdown
    // ═══════════════════════════════════════════════════════════════════

    window.updateRecentNotifications = function () {
        var notificationsDropdown = document.querySelector('#notificationsDropdown');
        if (!notificationsDropdown || !URLS.notificationsRecent) return;

        fetch(URLS.notificationsRecent + '?limit=10&_=' + Date.now())
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    var dropdown = notificationsDropdown.nextElementSibling;
                    if (!dropdown) return;

                    var html = '<li>' +
                        '<div class="dropdown-header d-flex justify-content-between align-items-center py-2 px-3 bg-light border-bottom">' +
                        '<span class="fw-bold text-dark small">' +
                        '<i class="fas fa-bell me-1 text-primary"></i>الإشعارات' +
                        (data.count > 0 ? '<span class="badge bg-primary rounded-pill ms-1" style="font-size: 0.65rem;">' + data.count + '</span>' : '') +
                        '</span>' +
                        (data.count > 0 ? '<button type="button" class="btn btn-sm btn-outline-primary py-0 px-2" onclick="markAllNotificationsRead()" style="font-size: 0.7rem;"><i class="fas fa-check-double me-1"></i>تحديد الكل</button>' : '') +
                        '</div></li>';

                    if (data.notifications.length > 0) {
                        data.notifications.forEach(function (notification) {
                            var extraData = notification.extra_data || {};
                            var iconClass = notification.icon_class || 'fas fa-bell';
                            var iconColor = notification.color_class || '#6c757d';
                            var iconBg = notification.bg_color || '#f5f5f5';
                            var ago = timeAgo(notification.created_at);

                            html += '<li>' +
                                '<a class="dropdown-item notification-dropdown-item px-3 py-2 ' + (!notification.is_read ? 'bg-light' : '') + '"' +
                                ' href="' + notification.url + '"' +
                                ' data-notification-id="' + notification.id + '"' +
                                ' data-is-read="' + notification.is_read + '">' +
                                '<div class="d-flex gap-2 align-items-start">' +
                                '<div class="flex-shrink-0" style="width: 36px; height: 36px; border-radius: 50%; background: ' + iconBg + '; border: 1.5px solid ' + iconColor + '; display: flex; align-items: center; justify-content: center;">' +
                                '<i class="' + iconClass + '" style="color: ' + iconColor + '; font-size: 14px;"></i></div>' +
                                '<div class="flex-grow-1" style="min-width: 0;">' +
                                '<div class="d-flex justify-content-between align-items-center mb-0">' +
                                '<h6 class="mb-0 text-truncate ' + (!notification.is_read ? 'fw-semibold text-dark' : 'text-muted') + '" style="font-size: 0.8rem; max-width: 260px;">' +
                                (!notification.is_read ? '<i class="fas fa-circle text-primary me-1" style="font-size: 5px; vertical-align: middle;"></i>' : '') +
                                notification.title + '</h6>' +
                                '<small class="text-muted flex-shrink-0 ms-2" style="font-size: 0.65rem;">' + ago + '</small></div>' +
                                '<p class="mb-0 text-muted" style="font-size: 0.72rem; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;">' + notification.message + '</p>';

                            if (extraData.customer_name || extraData.order_number || notification.created_by_name || extraData.changed_by) {
                                html += '<div class="d-flex gap-1 mt-1 flex-wrap">';
                                if (notification.created_by_name) {
                                    html += '<span class="badge bg-light text-dark border" style="font-size: 0.6rem; font-weight: normal;"><i class="fas fa-user-edit text-primary me-1"></i>' + notification.created_by_name + '</span>';
                                } else if (extraData.changed_by) {
                                    html += '<span class="badge bg-light text-dark border" style="font-size: 0.6rem; font-weight: normal;"><i class="fas fa-user-edit text-primary me-1"></i>' + extraData.changed_by + '</span>';
                                }
                                if (extraData.order_number) {
                                    html += '<span class="badge bg-light text-dark border" style="font-size: 0.6rem; font-weight: normal;"><i class="fas fa-hashtag text-info me-1"></i>' + extraData.order_number + '</span>';
                                }
                                if (extraData.customer_name) {
                                    html += '<span class="badge bg-light text-dark border" style="font-size: 0.6rem; font-weight: normal;"><i class="fas fa-user text-success me-1"></i>' + extraData.customer_name + '</span>';
                                }
                                html += '</div>';
                            }

                            html += '</div></div></a></li>';
                        });

                        html += '<li class="border-top">' +
                            '<a class="dropdown-item text-center py-2 text-primary fw-semibold" style="font-size: 0.8rem;" href="' + URLS.notificationsList + '">' +
                            '<i class="fas fa-list me-1"></i>عرض جميع الإشعارات</a></li>';
                    } else {
                        html += '<li><div class="text-center text-muted py-4 px-3">' +
                            '<i class="fas fa-bell-slash fa-2x mb-2 d-block opacity-50"></i>' +
                            '<small>لا توجد إشعارات</small></div></li>';
                    }

                    dropdown.innerHTML = html;
                    setTimeout(function () { setupDropdownNotificationListeners(); }, 100);
                }
            })
            .catch(function () {});
    };

    // ═══════════════════════════════════════════════════════════════════
    // 13. Mark All Notifications Read
    // ═══════════════════════════════════════════════════════════════════

    window.markAllNotificationsRead = function () {
        if (!confirm('هل تريد تحديد جميع الإشعارات كمقروءة؟')) return;

        var csrfToken = getCsrfToken();
        if (!csrfToken) {
            showNotificationMessage('خطأ في الأمان - لا يمكن تنفيذ العملية', 'error');
            return;
        }

        fetch(URLS.notificationsMarkAll, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success) {
                    removeAllNewBadgesFromDropdown();
                    updateNotificationCount();
                    updateRecentNotifications();
                    showNotificationMessage('تم تحديد جميع الإشعارات كمقروءة', 'success');
                } else {
                    showNotificationMessage('حدث خطأ أثناء تحديث الإشعارات', 'error');
                }
            })
            .catch(function () {
                showNotificationMessage('حدث خطأ أثناء تحديث الإشعارات', 'error');
            });
    };

    function removeAllNewBadgesFromDropdown() {
        var dropdownMenu = document.querySelector('#notificationsDropdown')?.nextElementSibling;
        if (!dropdownMenu) return;

        dropdownMenu.querySelectorAll('.badge').forEach(function (badge) {
            if (badge.textContent.includes('جديد')) badge.remove();
        });

        dropdownMenu.querySelectorAll('.fa-circle').forEach(function (dot) {
            if (dot.classList.contains('text-primary')) dot.remove();
        });

        dropdownMenu.querySelectorAll('.bg-light.border-start.border-primary').forEach(function (item) {
            item.classList.remove('bg-light', 'border-start', 'border-primary', 'border-3');
            item.setAttribute('data-is-read', 'true');
            var title = item.querySelector('h6');
            if (title) {
                title.classList.remove('fw-bold', 'text-dark');
                title.classList.add('text-muted');
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // 14. CSRF Token & Cookie Helpers
    // ═══════════════════════════════════════════════════════════════════

    // يستخدم CSRFHandler المركزي من csrf-handler.js
    window.getCsrfToken = function () {
        if (window.CSRFHandler) return window.CSRFHandler.getToken();
        var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfInput ? csrfInput.value : '';
    };

    // ═══════════════════════════════════════════════════════════════════
    // 15. Alert Message Helper
    // ═══════════════════════════════════════════════════════════════════

    window.showNotificationMessage = function (message, type) {
        var alertClass = type === 'success' ? 'alert-success' : (type === 'warning' ? 'alert-warning' : 'alert-danger');
        var iconClass = type === 'success' ? 'fa-check-circle' : (type === 'warning' ? 'fa-exclamation-triangle' : 'fa-exclamation-circle');

        var alertDiv = document.createElement('div');
        alertDiv.className = 'alert ' + alertClass + ' alert-dismissible fade show position-fixed';
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = '<i class="fas ' + iconClass + ' me-2"></i>' + message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';

        document.body.appendChild(alertDiv);
        setTimeout(function () { if (alertDiv.parentNode) alertDiv.remove(); }, 5000);
    };

    // ═══════════════════════════════════════════════════════════════════
    // 16. Initialization — DOMContentLoaded
    // ═══════════════════════════════════════════════════════════════════

    document.addEventListener('DOMContentLoaded', function () {
        updateNotificationCount();
        updateComplaintsNotificationCount();
        updateAssignmentNotifications();
        updateRecentNotifications();

        setTimeout(function () { setupDropdownNotificationListeners(); }, 500);
        setTimeout(function () { setupDropdownNotificationListeners(); }, 2000);

        var complaintsCenterDropdown = document.getElementById('complaintsCenterDropdown');
        if (complaintsCenterDropdown) {
            complaintsCenterDropdown.addEventListener('show.bs.dropdown', function () {
                loadComplaintsNotifications();
                updateAssignmentNotifications();
            });
        }

        setTimeout(checkAssignedComplaints, 2000);
        setTimeout(checkEscalatedComplaints, 3000);
        setTimeout(checkSystemNotifications, 4000);

        // Test functions
        window.testEscalatedPopup = function () {
            localStorage.removeItem('escalatedPopupSnoozed');
            checkEscalatedComplaints();
        };

        window.showTestPopup = function () {
            showEscalatedComplaintsPopup([{
                id: 1, complaint_number: 'TEST-001', title: 'شكوى تجريبية',
                customer_name: 'عميل تجريبي', assigned_to: 'مستخدم تجريبي',
                created_at: new Date().toISOString(), escalation_reason: 'اختبار',
                escalation_description: 'هذا اختبار للبوب أب'
            }]);
        };

        // Periodic update every 60 seconds
        setInterval(function () {
            updateNotificationCount();
            updateComplaintsNotificationCount();
            updateAssignmentNotifications();
            updateRecentNotifications();
            checkAssignedComplaints();
            checkEscalatedComplaints();
            checkSystemNotifications();
        }, 60000);
    });

})();
