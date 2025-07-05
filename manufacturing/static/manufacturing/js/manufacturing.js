document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const statusSelects = document.querySelectorAll('.status-select');
    const searchInput = document.getElementById('search');
    const searchButton = document.getElementById('search-btn');
    const statusFilter = document.getElementById('status-filter');
    const typeFilter = document.getElementById('type-filter');
    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    const exitPermitModal = document.getElementById('exitPermitModal');
    const closeModal = document.querySelector('.close');
    const cancelExitPermit = document.getElementById('cancelExitPermit');
    const exitPermitForm = document.getElementById('exitPermitForm');
    const addExitPermitButtons = document.querySelectorAll('.add-exit-permit');
    
    // Status Change Handler
    statusSelects.forEach(select => {
        select.addEventListener('change', function() {
            const orderId = this.dataset.orderId;
            const newStatus = this.value;
            
            // Show loading state
            const row = this.closest('tr');
            const statusCell = this.closest('td');
            const originalContent = statusCell.innerHTML;
            statusCell.innerHTML = '<div class="loading">جاري التحديث...</div>';
            
            // Send AJAX request to update status
            fetch(`/api/manufacturing/orders/${orderId}/status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    status: newStatus
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update the status badge
                    const statusBadge = statusCell.querySelector('.status-badge');
                    statusBadge.className = 'status-badge ' + newStatus;
                    statusBadge.textContent = data.status_display;
                    
                    // Update the select value
                    this.value = newStatus;
                    
                    // Show success message
                    showToast('تم تحديث الحالة بنجاح', 'success');
                    
                    // If status is completed, reload the page to update other elements
                    if (newStatus === 'completed') {
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                } else {
                    throw new Error(data.error || 'حدث خطأ غير معروف');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                statusCell.innerHTML = originalContent; // Revert to original content
                showToast('حدث خطأ أثناء تحديث الحالة', 'error');
            });
        });
    });
    
    // Filter Table Rows
    function filterTable() {
        const searchTerm = searchInput.value.toLowerCase();
        const statusValue = statusFilter.value;
        const typeValue = typeFilter.value;
        const dateFromValue = dateFrom.value;
        const dateToValue = dateTo.value;
        
        document.querySelectorAll('#manufacturing-orders-body tr').forEach(row => {
            const status = row.getAttribute('data-status');
            const type = row.getAttribute('data-type');
            const orderDate = row.cells[5].textContent.trim();
            const rowText = row.textContent.toLowerCase();
            
            let shouldShow = true;
            
            // Search filter
            if (searchTerm && !rowText.includes(searchTerm)) {
                shouldShow = false;
            }
            
            // Status filter
            if (statusValue && status !== statusValue) {
                shouldShow = false;
            }
            
            // Type filter
            if (typeValue && type !== typeValue) {
                shouldShow = false;
            }
            
            // Date range filter
            if (dateFromValue && orderDate < dateFromValue) {
                shouldShow = false;
            }
            
            if (dateToValue && orderDate > dateToValue) {
                shouldShow = false;
            }
            
            row.style.display = shouldShow ? '' : 'none';
        });
    }
    
    // Event Listeners for Filters
    [searchInput, statusFilter, typeFilter, dateFrom, dateTo].forEach(element => {
        if (element) {
            element.addEventListener('change', filterTable);
        }
    });
    
    if (searchButton) {
        searchButton.addEventListener('click', filterTable);
    }
    
    // Exit Permit Modal
    function openModal(orderId, currentExitPermit = '') {
        document.getElementById('orderId').value = orderId;
        document.getElementById('exitPermitNumber').value = currentExitPermit;
        exitPermitModal.style.display = 'flex';
    }
    
    function closeModalHandler() {
        exitPermitModal.style.display = 'none';
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', closeModalHandler);
    }
    
    if (cancelExitPermit) {
        cancelExitPermit.addEventListener('click', closeModalHandler);
    }
    
    // Close modal when clicking outside of it
    window.addEventListener('click', function(event) {
        if (event.target === exitPermitModal) {
            closeModalHandler();
        }
    });
    
    // Handle Exit Permit Form Submission
    if (exitPermitForm) {
        exitPermitForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const orderId = document.getElementById('orderId').value;
            const exitPermitNumber = document.getElementById('exitPermitNumber').value;
            
            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الحفظ...';
            
            // Send AJAX request to update exit permit
            fetch(`/api/manufacturing/orders/${orderId}/exit-permit/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    exit_permit_number: exitPermitNumber
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update the UI
                    const exitPermitCell = document.querySelector(`.add-exit-permit[data-order-id="${orderId}"]`).closest('td');
                    exitPermitCell.innerHTML = exitPermitNumber;
                    
                    // Close the modal
                    closeModalHandler();
                    
                    // Show success message
                    showToast('تم حفظ رقم إذن الخروج بنجاح', 'success');
                } else {
                    throw new Error(data.error || 'حدث خطأ غير معروف');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('حدث خطأ أثناء حفظ رقم إذن الخروج', 'error');
            })
            .finally(() => {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            });
        });
    }
    
    // Add click event to all "Add Exit Permit" buttons
    addExitPermitButtons.forEach(button => {
        button.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            openModal(orderId);
        });
    });
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Show toast notification
    function showToast(message, type = 'info') {
        // Check if toast container exists, if not create it
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Add toast to container
        toastContainer.appendChild(toast);
        
        // Show toast with animation
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Remove toast after delay
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
                // Remove container if no more toasts
                if (toastContainer.children.length === 0) {
                    toastContainer.remove();
                }
            }, 300);
        }, 5000);
    }
    
    // Add styles for toast notifications
    const toastStyles = document.createElement('style');
    toastStyles.textContent = `
        .toast-container {
            position: fixed;
            bottom: 20px;
            left: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .toast {
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.3s, transform 0.3s;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        
        .toast-success {
            background-color: #28a745;
        }
        
        .toast-error {
            background-color: #dc3545;
        }
        
        .toast-info {
            background-color: #17a2b8;
        }
        
        .toast-warning {
            background-color: #ffc107;
            color: #212529;
        }
    `;
    document.head.appendChild(toastStyles);
});
