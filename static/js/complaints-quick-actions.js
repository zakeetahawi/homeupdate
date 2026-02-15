/**
 * Unified Quick Actions for Complaints System
 * Consolidates all quick action functionality across the system
 */

// Global configuration
const ComplaintsQuickActions = {
    // Status names mapping
    statusNames: {
        'new': 'جديدة',
        'in_progress': 'قيد المعالجة',
        'resolved': 'محلولة',
        'closed': 'مغلقة',
        'cancelled': 'ملغية',
        'escalated': 'مصعدة'
    },

    // Priority names mapping
    priorityNames: {
        'low': 'منخفضة',
        'medium': 'متوسطة',
        'high': 'عالية',
        'urgent': 'عاجلة'
    },

    // API endpoints
    endpoints: {
        status: '/complaints/api/{id}/status/',
        escalate: '/complaints/api/{id}/escalate/',
        assign: '/complaints/api/{id}/assign/',
        note: '/complaints/api/{id}/note/'
    },

    // Initialize quick actions
    init: function() {
        this.bindEvents();
        this.setupCSRF();
    },

    // Bind event listeners
    bindEvents: function() {
        // Global event delegation for quick action buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-quick-action]')) {
                e.preventDefault();
                this.handleQuickAction(e.target);
            }
        });
    },

    // Setup CSRF token
    setupCSRF: function() {
        this.csrfToken = this.getCookie('csrftoken');
    },

    // Handle quick action button clicks
    handleQuickAction: function(button) {
        const action = button.dataset.quickAction;
        const complaintId = button.dataset.complaintId;
        const value = button.dataset.value;

        // Add loading state to button
        this.setButtonLoading(button, true);

        switch (action) {
            case 'status':
                this.updateStatus(complaintId, value, button);
                break;
            case 'escalate':
                this.escalateComplaint(complaintId, button);
                break;
            case 'assign':
                this.assignComplaint(complaintId, button);
                break;
            case 'note':
                this.addNote(complaintId, button);
                break;
            default:
                // console.warn('Unknown quick action:', action);
                this.setButtonLoading(button, false);
        }
    },

    // Set button loading state
    setButtonLoading: function(button, loading) {
        if (loading) {
            button.classList.add('loading');
            button.disabled = true;
            button.dataset.originalText = button.innerHTML;
            const icon = button.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-spinner fa-spin me-2';
            }
        } else {
            button.classList.remove('loading');
            button.disabled = false;
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
                delete button.dataset.originalText;
            }
        }
    },

    // Reset all button states
    resetButtonStates: function() {
        document.querySelectorAll('[data-quick-action].loading').forEach(button => {
            this.setButtonLoading(button, false);
        });
    },

    // Update complaint status with SweetAlert2 confirmation
    updateStatus: function(complaintId, newStatus, button = null) {
        const statusName = this.statusNames[newStatus] || newStatus;

        // If resolving, show resolution method selection
        if (newStatus === 'resolved') {
            this.showResolutionMethodDialog(complaintId, button);
            return;
        }

        Swal.fire({
            title: 'تحديث حالة الشكوى',
            text: `هل تريد تغيير حالة الشكوى إلى "${statusName}"؟`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'نعم، قم بالتحديث',
            cancelButtonText: 'إلغاء',
            customClass: {
                container: 'swal-rtl'
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.performStatusUpdate(complaintId, newStatus);
            } else {
                // Reset button state if cancelled
                if (button) this.setButtonLoading(button, false);
            }
        });
    },

    // Show resolution method selection dialog
    showResolutionMethodDialog: function(complaintId, button = null) {
        // First fetch available resolution methods
        fetch('/complaints/api/resolution-methods/')
            .then(response => response.json())
            .then(methods => {
                let methodOptions = '';
                methods.forEach(method => {
                    methodOptions += `<option value="${method.id}">${method.name}</option>`;
                });

                Swal.fire({
                    title: '✅ حل الشكوى',
                    html: `
                        <div class="text-start">
                            <div class="alert alert-success mb-3">
                                <i class="fas fa-check-circle me-2"></i>
                                <strong>تهانينا!</strong> أنت على وشك حل هذه الشكوى
                            </div>
                            <div class="mb-3">
                                <label for="resolution_method" class="form-label">طريقة الحل:</label>
                                <select id="resolution_method" class="form-select" required>
                                    <option value="">اختر طريقة الحل...</option>
                                    ${methodOptions}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="resolution_notes" class="form-label">ملاحظات الحل:</label>
                                <textarea id="resolution_notes" class="form-control" rows="3" placeholder="أضف تفاصيل حول كيفية حل الشكوى..."></textarea>
                            </div>
                        </div>
                    `,
                    showCancelButton: true,
                    confirmButtonColor: '#28a745',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: '🎉 حل الشكوى',
                    cancelButtonText: 'إلغاء',
                    customClass: {
                        container: 'swal-rtl'
                    },
                    preConfirm: () => {
                        const resolutionMethod = document.getElementById('resolution_method').value;
                        const notes = document.getElementById('resolution_notes').value;

                        if (!resolutionMethod) {
                            Swal.showValidationMessage('يرجى اختيار طريقة الحل');
                            return false;
                        }

                        return { resolutionMethod, notes };
                    }
                }).then((result) => {
                    if (result.isConfirmed) {
                        this.performStatusUpdate(complaintId, 'resolved', result.value);
                    } else {
                        // Reset button state if cancelled
                        if (button) this.setButtonLoading(button, false);
                    }
                });
            })
            .catch(error => {
                console.error('Error fetching resolution methods:', error);
                this.showError('حدث خطأ في تحميل طرق الحل');
                if (button) this.setButtonLoading(button, false);
            });
    },

    // Perform the actual status update
    performStatusUpdate: function(complaintId, newStatus, extraData = null) {
        const url = this.endpoints.status.replace('{id}', complaintId);

        const requestData = { status: newStatus };
        if (extraData) {
            Object.assign(requestData, extraData);
        }

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            // Reset all button states
            this.resetButtonStates();

            if (data.success) {
                const statusName = this.statusNames[newStatus] || newStatus;
                this.showSuccess(`🎉 تم تحديث حالة الشكوى إلى "${statusName}" بنجاح`);
                setTimeout(() => location.reload(), 2000);
            } else {
                this.showError(data.error || 'حدث خطأ في تحديث الحالة');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.resetButtonStates();
            this.showError('حدث خطأ في الاتصال');
        });
    },

    // Escalate complaint with enhanced form and user selection
    escalateComplaint: function(complaintId, button = null) {
        // First fetch available users for escalation
        fetch('/complaints/api/users-for-escalation/')
            .then(response => response.json())
            .then(users => {
                let userOptions = '';
                users.forEach(user => {
                    userOptions += `<option value="${user.id}">${user.name} - ${user.department || 'غير محدد'}</option>`;
                });

                Swal.fire({
                    title: '⚠️ تصعيد الشكوى - إشعار فوري',
                    html: `
                        <div class="text-start">
                            <div class="alert alert-warning mb-3">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                <strong>تنبيه:</strong> سيتم إرسال إشعار فوري للمستخدم المحدد
                            </div>
                            <div class="mb-3">
                                <label for="escalated_to" class="form-label">المستخدم المراد التصعيد إليه:</label>
                                <select id="escalated_to" class="form-select" required>
                                    <option value="">اختر المستخدم...</option>
                                    ${userOptions}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="escalation_reason" class="form-label">سبب التصعيد:</label>
                                <select id="escalation_reason" class="form-select">
                                    <option value="overdue">متأخرة عن الموعد المحدد</option>
                                    <option value="urgent">حالة عاجلة تتطلب تدخل فوري</option>
                                    <option value="complex">مشكلة معقدة تحتاج خبرة متخصصة</option>
                                    <option value="customer_request">طلب مباشر من العميل</option>
                                    <option value="technical">مشكلة فنية متقدمة</option>
                                    <option value="management">يتطلب موافقة إدارية</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="escalation_notes" class="form-label">ملاحظات التصعيد:</label>
                                <textarea id="escalation_notes" class="form-control" rows="3" placeholder="أضف تفاصيل حول سبب التصعيد وأي معلومات مهمة..."></textarea>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="urgent_notification" checked>
                                <label class="form-check-label" for="urgent_notification">
                                    إرسال إشعار عاجل فوري
                                </label>
                            </div>
                        </div>
                    `,
                    showCancelButton: true,
                    confirmButtonColor: '#dc3545',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: '🚨 تصعيد فوري',
                    cancelButtonText: 'إلغاء',
                    customClass: {
                        container: 'swal-rtl'
                    },
                    preConfirm: () => {
                        const escalatedTo = document.getElementById('escalated_to').value;
                        const reason = document.getElementById('escalation_reason').value;
                        const notes = document.getElementById('escalation_notes').value;
                        const urgentNotification = document.getElementById('urgent_notification').checked;

                        if (!escalatedTo) {
                            Swal.showValidationMessage('يرجى اختيار المستخدم المراد التصعيد إليه');
                            return false;
                        }

                        return { escalatedTo, reason, notes, urgentNotification };
                    }
                }).then((result) => {
                    if (result.isConfirmed) {
                        this.performEscalation(complaintId, result.value);
                    } else {
                        // Reset button state if cancelled
                        if (button) this.setButtonLoading(button, false);
                    }
                });
            })
            .catch(error => {
                console.error('Error fetching users:', error);
                this.showError('حدث خطأ في تحميل قائمة المستخدمين');
                if (button) this.setButtonLoading(button, false);
            });
    },

    // Perform escalation with real-time notification
    performEscalation: function(complaintId, escalationData) {
        const url = this.endpoints.escalate.replace('{id}', complaintId);

        // Show loading state
        Swal.fire({
            title: 'جاري التصعيد...',
            html: 'يتم تصعيد الشكوى وإرسال الإشعارات',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                escalated_to: escalationData.escalatedTo,
                reason: escalationData.reason,
                description: escalationData.notes,
                urgent_notification: escalationData.urgentNotification
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: '✅ تم التصعيد بنجاح',
                    html: `
                        <div class="text-center">
                            <p><strong>${data.message}</strong></p>
                            <p>تم التصعيد إلى: <span class="badge bg-primary">${data.escalated_to}</span></p>
                            ${data.notification_sent ? '<p class="text-success"><i class="fas fa-bell me-1"></i>تم إرسال إشعار فوري</p>' : ''}
                        </div>
                    `,
                    confirmButtonText: 'موافق',
                    timer: 3000,
                    timerProgressBar: true
                }).then(() => {
                    setTimeout(() => location.reload(), 500);
                });
            } else {
                this.showError(data.error || 'حدث خطأ في تصعيد الشكوى');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showError('حدث خطأ في الاتصال');
        });
    },

    // Assign complaint with user selection dropdown
    assignComplaint: function(complaintId, button = null) {
        // First fetch available users for assignment
        fetch('/complaints/api/users-for-assignment/')
            .then(response => response.json())
            .then(users => {
                let userOptions = '';
                users.forEach(user => {
                    const displayName = user.name + (user.department ? ` - ${user.department}` : '');
                    const badgeClass = user.is_supervisor ? 'bg-warning' : user.is_manager ? 'bg-success' : 'bg-secondary';
                    const badge = user.is_supervisor ? 'مشرف' : user.is_manager ? 'مدير' : 'موظف';

                    userOptions += `<option value="${user.id}" data-department="${user.department || ''}" data-role="${badge}">
                        ${displayName} (${badge})
                    </option>`;
                });

                Swal.fire({
                    title: '👤 تعيين الشكوى',
                    html: `
                        <div class="text-start">
                            <div class="alert alert-info mb-3">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>تنبيه:</strong> سيتم إرسال إشعار فوري للمستخدم المحدد
                            </div>
                            <div class="mb-3">
                                <label for="assigned_to" class="form-label">المستخدم المراد التعيين إليه:</label>
                                <select id="assigned_to" class="form-select" required>
                                    <option value="">اختر المستخدم...</option>
                                    ${userOptions}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="assigned_department" class="form-label">القسم (اختياري):</label>
                                <select id="assigned_department" class="form-select">
                                    <option value="">اختر القسم...</option>
                                    <option value="technical">الدعم الفني</option>
                                    <option value="customer_service">خدمة العملاء</option>
                                    <option value="sales">المبيعات</option>
                                    <option value="management">الإدارة</option>
                                    <option value="quality">ضمان الجودة</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="assignment_notes" class="form-label">ملاحظات التعيين:</label>
                                <textarea id="assignment_notes" class="form-control" rows="3" placeholder="أضف ملاحظات حول التعيين وأي تعليمات خاصة..."></textarea>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="urgent_assignment" checked>
                                <label class="form-check-label" for="urgent_assignment">
                                    إرسال إشعار عاجل فوري
                                </label>
                            </div>
                        </div>
                    `,
                    showCancelButton: true,
                    confirmButtonColor: '#007bff',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: '📋 تعيين الشكوى',
                    cancelButtonText: 'إلغاء',
                    customClass: {
                        container: 'swal-rtl'
                    },
                    preConfirm: () => {
                        const assignedTo = document.getElementById('assigned_to').value;
                        const assignedDepartment = document.getElementById('assigned_department').value;
                        const notes = document.getElementById('assignment_notes').value;
                        const urgentAssignment = document.getElementById('urgent_assignment').checked;

                        if (!assignedTo) {
                            Swal.showValidationMessage('يرجى اختيار المستخدم المراد التعيين إليه');
                            return false;
                        }

                        return { assignedTo, assignedDepartment, notes, urgentAssignment };
                    }
                }).then((result) => {
                    if (result.isConfirmed) {
                        this.performAssignment(complaintId, result.value);
                    } else {
                        // Reset button state if cancelled
                        if (button) this.setButtonLoading(button, false);
                    }
                });
            })
            .catch(error => {
                console.error('Error fetching users:', error);
                this.showError('حدث خطأ في تحميل قائمة المستخدمين');
                if (button) this.setButtonLoading(button, false);
            });
    },

    // Perform assignment with enhanced feedback
    performAssignment: function(complaintId, assignmentData) {
        const url = this.endpoints.assign.replace('{id}', complaintId);

        // Show loading state
        Swal.fire({
            title: 'جاري التعيين...',
            html: 'يتم تعيين الشكوى وإرسال الإشعارات',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                assigned_to: assignmentData.assignedTo,
                assigned_department: assignmentData.assignedDepartment,
                assignment_notes: assignmentData.notes,
                urgent_notification: assignmentData.urgentAssignment
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: '✅ تم التعيين بنجاح',
                    html: `
                        <div class="text-center">
                            <p><strong>${data.message}</strong></p>
                            <p>تم التعيين إلى: <span class="badge bg-primary">${data.assigned_to}</span></p>
                            ${data.notification_sent ? '<p class="text-success"><i class="fas fa-bell me-1"></i>تم إرسال إشعار فوري</p>' : ''}
                        </div>
                    `,
                    confirmButtonText: 'موافق',
                    timer: 3000,
                    timerProgressBar: true
                }).then(() => {
                    setTimeout(() => location.reload(), 500);
                });
            } else {
                this.showError(data.error || 'حدث خطأ في تعيين الشكوى');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showError('حدث خطأ في الاتصال');
        });
    },

    // Add note to complaint
    addNote: function(complaintId, button = null) {
        Swal.fire({
            title: '📝 إضافة ملاحظة',
            html: `
                <div class="text-start">
                    <div class="mb-3">
                        <label for="note_title" class="form-label">عنوان الملاحظة:</label>
                        <input type="text" id="note_title" class="form-control" placeholder="أدخل عنوان الملاحظة..." required>
                    </div>
                    <div class="mb-3">
                        <label for="note_content" class="form-label">محتوى الملاحظة:</label>
                        <textarea id="note_content" class="form-control" rows="4" placeholder="اكتب تفاصيل الملاحظة هنا..." required></textarea>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="note_visible_to_customer">
                        <label class="form-check-label" for="note_visible_to_customer">
                            <i class="fas fa-eye me-1"></i>
                            <strong>مرئية للعميل</strong>
                            <br>
                            <small class="text-muted">إذا تم تفعيل هذا الخيار، سيتمكن العميل من رؤية هذه الملاحظة</small>
                        </label>
                    </div>
                </div>
            `,
            showCancelButton: true,
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#6c757d',
            confirmButtonText: '💾 إضافة الملاحظة',
            cancelButtonText: 'إلغاء',
            customClass: {
                container: 'swal-rtl'
            },
            preConfirm: () => {
                const title = document.getElementById('note_title').value;
                const content = document.getElementById('note_content').value;
                const visibleToCustomer = document.getElementById('note_visible_to_customer').checked;

                if (!title.trim()) {
                    Swal.showValidationMessage('يرجى إدخال عنوان الملاحظة');
                    return false;
                }

                if (!content.trim()) {
                    Swal.showValidationMessage('يرجى كتابة محتوى الملاحظة');
                    return false;
                }

                return { title, content, visibleToCustomer };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.performAddNote(complaintId, result.value);
            } else {
                // Reset button state if cancelled
                if (button) this.setButtonLoading(button, false);
            }
        });
    },

    // Perform add note
    performAddNote: function(complaintId, noteData) {
        const url = this.endpoints.note.replace('{id}', complaintId);

        // Show loading state
        Swal.fire({
            title: 'جاري إضافة الملاحظة...',
            html: 'يتم حفظ الملاحظة',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                title: noteData.title,
                content: noteData.content,
                is_visible_to_customer: noteData.visibleToCustomer
            })
        })
        .then(response => response.json())
        .then(data => {
            // Reset all button states
            this.resetButtonStates();

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: '✅ تم إضافة الملاحظة بنجاح',
                    html: `
                        <div class="text-center">
                            <p><strong>العنوان:</strong> ${noteData.title}</p>
                            <p class="text-muted">تم حفظ الملاحظة وإضافتها للشكوى</p>
                        </div>
                    `,
                    confirmButtonText: 'موافق',
                    timer: 3000,
                    timerProgressBar: true
                }).then(() => {
                    setTimeout(() => location.reload(), 500);
                });
            } else {
                this.showError(data.error || 'حدث خطأ في إضافة الملاحظة');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.resetButtonStates();
            this.showError('حدث خطأ في الاتصال');
        });
    },

    // Show success notification
    showSuccess: function(message) {
        Swal.fire({
            icon: 'success',
            title: 'نجح العملية',
            text: message,
            timer: 3000,
            timerProgressBar: true,
            showConfirmButton: false,
            toast: true,
            position: 'top-end',
            customClass: {
                container: 'swal-rtl'
            }
        });
    },

    // Show error notification
    showError: function(message) {
        Swal.fire({
            icon: 'error',
            title: 'خطأ',
            text: message,
            confirmButtonText: 'موافق',
            customClass: {
                container: 'swal-rtl'
            }
        });
    },

    // يستخدم CSRFHandler المركزي من csrf-handler.js
    getCookie: function(name) {
        if (window.CSRFHandler) return window.CSRFHandler.getToken();
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    ComplaintsQuickActions.init();
});

// Export for global use
window.ComplaintsQuickActions = ComplaintsQuickActions;
