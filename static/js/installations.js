// ملف JavaScript لقسم التركيبات

// تحديث حالة التركيب
function updateInstallationStatus(installationId, newStatus) {
    if (confirm('هل أنت متأكد من تحديث حالة التركيب؟')) {
        fetch(`/installations/update-status/${installationId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `status=${newStatus}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('تم تحديث الحالة بنجاح', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showNotification('حدث خطأ أثناء تحديث الحالة', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('حدث خطأ في الاتصال', 'error');
        });
    }
}

// إضافة دفعة
function addPayment(installationId) {
    const amount = document.getElementById('payment-amount').value;
    const paymentType = document.getElementById('payment-type').value;
    const paymentMethod = document.getElementById('payment-method').value;
    const notes = document.getElementById('payment-notes').value;

    if (!amount || amount <= 0) {
        showNotification('يرجى إدخال مبلغ صحيح', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('amount', amount);
    formData.append('payment_type', paymentType);
    formData.append('payment_method', paymentMethod);
    formData.append('notes', notes);

    fetch(`/installations/add-payment/${installationId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('تم إضافة الدفعة بنجاح', 'success');
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showNotification(data.message || 'حدث خطأ أثناء إضافة الدفعة', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('حدث خطأ في الاتصال', 'error');
    });
}

// إكمال التركيب
function completeInstallation(installationId) {
    if (confirm('هل أنت متأكد من إكمال التركيب؟ هذا الإجراء لا يمكن التراجع عنه.')) {
        fetch(`/installations/complete/${installationId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('تم إكمال التركيب بنجاح', 'success');
                setTimeout(() => {
                    window.location.href = '/installations/';
                }, 1500);
            } else {
                showNotification(data.message || 'حدث خطأ أثناء إكمال التركيب', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('حدث خطأ في الاتصال', 'error');
        });
    }
}

// البحث في التركيبات
function searchInstallations() {
    const searchTerm = document.getElementById('search-input').value;
    const statusFilter = document.getElementById('status-filter').value;
    const teamFilter = document.getElementById('team-filter').value;

    const params = new URLSearchParams();
    if (searchTerm) params.append('search', searchTerm);
    if (statusFilter) params.append('status', statusFilter);
    if (teamFilter) params.append('team', teamFilter);

    window.location.href = `/installations/list/?${params.toString()}`;
}

// تحديث الجدول اليومي
function refreshDailySchedule() {
    const date = document.getElementById('schedule-date').value;
    if (date) {
        window.location.href = `/installations/daily-schedule/?date=${date}`;
    }
}

// طباعة الجدول اليومي
function printDailySchedule() {
    const date = document.getElementById('schedule-date').value;
    if (date) {
        window.open(`/installations/print-daily-schedule/?date=${date}`, '_blank');
    } else {
        window.open('/installations/print-daily-schedule/', '_blank');
    }
}

// إظهار الإشعارات
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // إزالة الإشعار تلقائياً بعد 5 ثوان
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// الحصول على CSRF token
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

// تحديث الإحصائيات
function updateStats() {
    fetch('/installations/stats-api/')
        .then(response => response.json())
        .then(data => {
            document.getElementById('total-installations').textContent = data.total;
            document.getElementById('pending-installations').textContent = data.pending;
            document.getElementById('scheduled-installations').textContent = data.scheduled;
            document.getElementById('completed-installations').textContent = data.completed;
        })
        .catch(error => {
            console.error('Error updating stats:', error);
        });
}

// تحميل معاينة الملف
function previewFile(input) {
    const file = input.files[0];
    const preview = document.getElementById('file-preview');
    const previewContent = document.getElementById('preview-content');
    
    if (file) {
        preview.style.display = 'block';
        
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewContent.innerHTML = `
                    <img src="${e.target.result}" class="img-fluid rounded" style="max-height: 200px;" alt="معاينة الملف">
                    <p class="mt-2"><strong>اسم الملف:</strong> ${file.name}</p>
                    <p><strong>الحجم:</strong> ${(file.size / 1024 / 1024).toFixed(2)} ميجابايت</p>
                `;
            };
            reader.readAsDataURL(file);
        } else {
            previewContent.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-file"></i>
                    <strong>اسم الملف:</strong> ${file.name}<br>
                    <strong>الحجم:</strong> ${(file.size / 1024 / 1024).toFixed(2)} ميجابايت<br>
                    <strong>النوع:</strong> ${file.type}
                </div>
            `;
        }
    } else {
        preview.style.display = 'none';
    }
}

// التحقق من حجم الملف
function validateFileSize(input, maxSizeMB = 5) {
    const file = input.files[0];
    const maxSize = maxSizeMB * 1024 * 1024;
    
    if (file && file.size > maxSize) {
        showNotification(`حجم الملف يجب أن يكون أقل من ${maxSizeMB} ميجابايت`, 'error');
        input.value = '';
        document.getElementById('file-preview').style.display = 'none';
        return false;
    }
    return true;
}

// تحديث المبلغ المستلم
function updateAmountReceived() {
    const paymentType = document.getElementById('payment-type');
    const amountField = document.getElementById('amount-received');
    const remainingAmount = parseFloat(amountField.dataset.remaining || 0);
    
    if (paymentType && paymentType.value === 'remaining') {
        amountField.value = remainingAmount;
        amountField.readOnly = true;
    } else {
        amountField.readOnly = false;
    }
}

// تهيئة الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // إضافة مستمعي الأحداث للأزرار
    document.querySelectorAll('.update-status-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const installationId = this.dataset.installationId;
            const newStatus = this.dataset.status;
            updateInstallationStatus(installationId, newStatus);
        });
    });

    // إضافة مستمعي الأحداث للنماذج
    document.querySelectorAll('.payment-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const installationId = this.dataset.installationId;
            addPayment(installationId);
        });
    });

    // تحديث الإحصائيات كل 30 ثانية
    setInterval(updateStats, 30000);

    // تهيئة معاينة الملفات
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function() {
            previewFile(this);
            validateFileSize(this);
        });
    });

    // تهيئة تحديث المبلغ المستلم
    const paymentTypeSelect = document.getElementById('payment-type');
    if (paymentTypeSelect) {
        paymentTypeSelect.addEventListener('change', updateAmountReceived);
    }
});

// تصدير البيانات
function exportInstallations(format = 'csv') {
    const searchParams = new URLSearchParams(window.location.search);
    searchParams.append('export', format);
    
    window.location.href = `/installations/export/?${searchParams.toString()}`;
}

// إرسال إشعار للعميل
function sendCustomerNotification(installationId, message) {
    fetch(`/installations/send-notification/${installationId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('تم إرسال الإشعار بنجاح', 'success');
        } else {
            showNotification('فشل في إرسال الإشعار', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('حدث خطأ في إرسال الإشعار', 'error');
    });
} 