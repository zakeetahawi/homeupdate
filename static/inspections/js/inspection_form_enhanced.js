/**
 * تحسينات نموذج المعاينة للرفع السريع والخلفي للملفات
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeFormEnhancements();
    initializeFileUploadHandling();
    initializeCustomerHandling();
});

function initializeFormEnhancements() {
    const form = document.querySelector('form');
    const saveBtn = document.getElementById('save-btn');
    
    if (!form || !saveBtn) return;
    
    // معالجة إرسال النموذج
    form.addEventListener('submit', function(e) {
        handleFormSubmission(saveBtn);
    });
}

function handleFormSubmission(saveBtn) {
    // تفعيل حالة الحفظ
    saveBtn.disabled = true;
    
    const saveText = saveBtn.querySelector('#save-text');
    const savingText = saveBtn.querySelector('#saving-text');
    
    if (saveText) saveText.style.display = 'none';
    if (savingText) savingText.style.display = 'inline';
    
    // التحقق من وجود ملف
    const fileInputs = document.querySelectorAll('input[type="file"]');
    let hasFile = false;
    
    fileInputs.forEach(input => {
        if (input.files && input.files.length > 0) {
            hasFile = true;
        }
    });
    
    if (hasFile) {
        // عرض إشعار للمستخدم
        setTimeout(() => {
            showQuietNotification(
                'سيتم رفع الملف في الخلفية بعد الحفظ. يمكنك متابعة عملك.',
                'info'
            );
        }, 1000);
    }
}

function initializeFileUploadHandling() {
    // معالجة تغيير ملف المعاينة
    const fileInput = document.querySelector('input[name="inspection_file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            handleFileSelection(e.target);
        });
    }
}

function handleFileSelection(fileInput) {
    const file = fileInput.files[0];
    if (!file) return;
    
    // التحقق من نوع الملف
    if (file.type !== 'application/pdf') {
        showQuietNotification('يجب أن يكون الملف من نوع PDF', 'warning');
        fileInput.value = '';
        return;
    }
    
    // التحقق من حجم الملف (50 ميجابايت)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showQuietNotification('حجم الملف كبير جداً. الحد الأقصى 50 ميجابايت', 'warning');
        fileInput.value = '';
        return;
    }
    
    // عرض معاينة اسم الملف
    updateFilenamePreview(file.name);
}

function updateFilenamePreview(filename) {
    const preview = document.getElementById('filename-preview');
    if (preview) {
        preview.textContent = filename;
        preview.classList.add('text-success');
    }
}

function initializeCustomerHandling() {
    const customerSelect = document.getElementById('customer-select') || 
                          document.querySelector('select[name="customer"]');
    
    if (!customerSelect) return;
    
    customerSelect.addEventListener('change', function() {
        handleCustomerChange(this);
    });
    
    // تنفيذ عند التحميل إذا كان هناك عميل محدد
    if (customerSelect.value) {
        handleCustomerChange(customerSelect);
    }
}

function handleCustomerChange(customerSelect) {
    const customerId = customerSelect.value;
    const customerAddressContainer = document.getElementById('customer-address-container');
    const customerAddress = document.getElementById('customer-address');
    
    if (!customerAddressContainer || !customerAddress) return;
    
    if (customerId) {
        // جلب بيانات العميل
        fetch(`/customers/api/customer/${customerId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.address) {
                    customerAddress.textContent = data.address;
                    customerAddressContainer.style.display = 'block';
                } else {
                    customerAddress.textContent = 'لا يوجد عنوان مسجل';
                    customerAddressContainer.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('خطأ في جلب بيانات العميل:', error);
                customerAddress.textContent = 'حدث خطأ أثناء جلب بيانات العميل';
                customerAddressContainer.style.display = 'block';
            });
    } else {
        customerAddressContainer.style.display = 'none';
    }
}

// دالة للتحقق من حالة الرفع في الخلفية
function checkUploadStatusBackground(inspectionId) {
    let attempts = 0;
    const maxAttempts = 20; // تقليل عدد المحاولات
    
    const interval = setInterval(function() {
        attempts++;
        
        fetch(`/inspections/${inspectionId}/check-upload-status/`)
            .then(response => response.json())
            .then(data => {
                if (data.is_uploaded && data.google_drive_url) {
                    // تم الرفع بنجاح
                    clearInterval(interval);
                    updateUploadStatusUI(true, data.google_drive_url);
                    showQuietNotification('تم رفع الملف بنجاح إلى Google Drive', 'success');
                } else if (attempts >= maxAttempts) {
                    // انتهت المحاولات
                    clearInterval(interval);
                }
            })
            .catch(error => {
                console.error('خطأ في التحقق من حالة الرفع:', error);
                if (attempts >= maxAttempts) {
                    clearInterval(interval);
                }
            });
    }, 3000); // كل 3 ثوان
}

// دالة لتحديث واجهة المستخدم عند الرفع
function updateUploadStatusUI(uploaded, url) {
    const uploadAlert = document.querySelector('.alert-info');
    if (uploadAlert && uploaded) {
        uploadAlert.className = 'alert alert-success py-2';
        uploadAlert.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <strong>تم الرفع إلى Google Drive بنجاح!</strong>
            <br>
            <a href="${url}" target="_blank" class="btn btn-sm btn-primary mt-1">
                <i class="fab fa-google-drive"></i> عرض في Google Drive
            </a>
        `;
    }
}

// دالة لعرض إشعارات صامتة
function showQuietNotification(message, type = 'info') {
    // إزالة الإشعارات السابقة
    const existingToasts = document.querySelectorAll('.quiet-notification');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed quiet-notification`;
    toast.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 400px;
        opacity: 0;
        transition: opacity 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 8px;
    `;
    
    const iconClass = {
        'success': 'check-circle',
        'info': 'info-circle',
        'warning': 'exclamation-triangle',
        'danger': 'times-circle'
    }[type] || 'info-circle';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${iconClass} me-2"></i>
            <span class="flex-grow-1">${message}</span>
            <button type="button" class="btn-close btn-close-white ms-2" onclick="this.closest('.quiet-notification').remove()"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // تدرج الظهور
    setTimeout(() => toast.style.opacity = '1', 100);
    
    // إخفاء تلقائي بعد 5 ثوان
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// توفير الدوال للاستخدام العام
window.checkUploadStatusBackground = checkUploadStatusBackground;
window.showQuietNotification = showQuietNotification;
window.updateUploadStatusUI = updateUploadStatusUI;
