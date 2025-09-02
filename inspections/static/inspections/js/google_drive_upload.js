/**
 * نظام رفع ملفات المعاينات إلى Google Drive
 */

// متغيرات عامة
let uploadInProgress = false;
let currentInspectionId = null;

// تهيئة النظام عند تحميل الصفحة
$(document).ready(function() {
    initializeGoogleDriveUpload();
});

/**
 * تهيئة نظام رفع Google Drive
 */
function initializeGoogleDriveUpload() {
    // مراقبة تغيير ملف المعاينة
    $('#id_inspection_file').on('change', function() {
        if (this.files && this.files[0]) {
            handleFileSelection(this.files[0]);
        }
    });
    
    // مراقبة تغيير بيانات النموذج لتحديث معاينة اسم الملف
    $('#id_customer, #id_branch, #id_scheduled_date, #id_order, #id_contract_number').on('change', function() {
        updateFilenamePreview();
    });
    
    // تحديث معاينة اسم الملف عند التحميل
    updateFilenamePreview();
}

/**
 * معالجة اختيار الملف
 */
function handleFileSelection(file) {
    if (uploadInProgress) {
        showError('يتم رفع ملف آخر حالياً. يرجى الانتظار.');
        return;
    }
    
    // التحقق من نوع الملف
    if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
        showError('يجب أن يكون الملف من نوع PDF');
        return;
    }
    
    // التحقق من حجم الملف (أقل من 50MB)
    if (file.size > 50 * 1024 * 1024) {
        showError('حجم الملف كبير جداً (الحد الأقصى 50MB)');
        return;
    }
    
    // إذا كان هناك معرف معاينة (في حالة التعديل)، رفع الملف مباشرة
    if (currentInspectionId) {
        uploadToGoogleDrive();
    } else {
        // في حالة الإنشاء الجديد، عرض معاينة فقط
        showUploadPreview(file);
    }
}

/**
 * عرض معاينة الرفع
 */
function showUploadPreview(file) {
    const customerName = getCustomerName();
    const branchName = getBranchName();
    const orderNumber = getOrderNumber();
    const date = getScheduledDate();
    const expectedFilename = generateFilename(customerName, branchName, date, orderNumber);
    
    Swal.fire({
        title: 'ملف جاهز للرفع',
        html: `
            <div class="upload-preview">
                <div class="file-info mb-3">
                    <i class="fas fa-file-pdf fa-3x text-danger mb-2"></i>
                    <p><strong>الملف:</strong> ${file.name}</p>
                    <p><strong>الحجم:</strong> ${formatFileSize(file.size)}</p>
                </div>
                <hr>
                <div class="upload-info">
                    <h6>معلومات الرفع:</h6>
                    <p><strong>العميل:</strong> ${customerName}</p>
                    <p><strong>الفرع:</strong> ${branchName}</p>
                    <p><strong>التاريخ:</strong> ${date}</p>
                    <p><strong>رقم الطلب:</strong> ${orderNumber}</p>
                    <hr>
                    <p class="text-muted small"><strong>اسم الملف في Google Drive:</strong><br>${expectedFilename}</p>
                </div>
            </div>
        `,
        icon: 'info',
        confirmButtonText: 'موافق',
        customClass: {
            popup: 'swal-upload-popup',
            confirmButton: 'btn btn-primary'
        }
    });
}

/**
 * رفع الملف إلى Google Drive
 */
function uploadToGoogleDrive() {
    if (!currentInspectionId) {
        showError('يجب حفظ المعاينة أولاً قبل رفع الملف');
        return;
    }
    
    uploadInProgress = true;
    
    const customerName = getCustomerName();
    const branchName = getBranchName();
    const orderNumber = getOrderNumber();
    const date = getScheduledDate();
    const expectedFilename = generateFilename(customerName, branchName, date, orderNumber);
    
    // عرض شريط التقدم
    Swal.fire({
        title: 'جاري رفع الملف...',
        html: `
            <div class="upload-progress">
                <div class="progress mb-3">
                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                         style="width: 0%" id="uploadProgress"></div>
                </div>
                <div class="upload-info">
                    <p><strong>العميل:</strong> ${customerName}</p>
                    <p><strong>الفرع:</strong> ${branchName}</p>
                    <p><strong>التاريخ:</strong> ${date}</p>
                    <p><strong>رقم الطلب:</strong> ${orderNumber}</p>
                    <hr>
                    <p class="text-muted small">اسم الملف: ${expectedFilename}</p>
                </div>
            </div>
        `,
        allowOutsideClick: false,
        showConfirmButton: false,
        customClass: {
            popup: 'swal-upload-popup'
        }
    });
    
    // محاكاة التقدم
    simulateProgress();
    
    // إرسال طلب الرفع
    const formData = new FormData();
    formData.append('inspection_id', currentInspectionId);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: '/inspections/ajax/upload-to-google-drive/',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            uploadInProgress = false;
            if (response.success) {
                showUploadSuccess(response.data);
            } else {
                showError(response.message);
            }
        },
        error: function(xhr, status, error) {
            uploadInProgress = false;
            showError('حدث خطأ في الشبكة أثناء رفع الملف');
        }
    });
}

/**
 * محاكاة شريط التقدم
 */
function simulateProgress() {
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        
        const progressBar = document.getElementById('uploadProgress');
        if (progressBar) {
            progressBar.style.width = progress + '%';
        } else {
            clearInterval(interval);
        }
    }, 200);
    
    // إيقاف المحاكاة بعد 10 ثوان
    setTimeout(() => {
        clearInterval(interval);
    }, 10000);
}

/**
 * عرض رسالة نجاح الرفع
 */
function showUploadSuccess(data) {
    Swal.fire({
        icon: 'success',
        title: 'تم رفع الملف بنجاح!',
        html: `
            <div class="success-info">
                <p><strong>تم رفع ملف المعاينة إلى Google Drive</strong></p>
                <hr>
                <p><strong>اسم الملف:</strong> ${data.filename}</p>
                <p><strong>العميل:</strong> ${data.customer_name}</p>
                <p><strong>الفرع:</strong> ${data.branch_name}</p>
                <a href="${data.view_url}" target="_blank" class="btn btn-primary btn-sm mt-2">
                    <i class="fas fa-external-link-alt"></i> عرض في Google Drive
                </a>
            </div>
        `,
        confirmButtonText: 'موافق',
        customClass: {
            confirmButton: 'btn btn-success'
        }
    }).then(() => {
        // إعادة تحميل الصفحة لتحديث البيانات
        location.reload();
    });
}

/**
 * عرض رسالة خطأ
 */
function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'خطأ',
        text: message,
        confirmButtonText: 'موافق',
        customClass: {
            confirmButton: 'btn btn-danger'
        }
    });
}

/**
 * تحديث معاينة اسم الملف
 */
function updateFilenamePreview() {
    const customerName = getCustomerName();
    const branchName = getBranchName();
    const orderNumber = getOrderNumber();
    const date = getScheduledDate();
    const filename = generateFilename(customerName, branchName, date, orderNumber);
    
    // عرض المعاينة إذا كان هناك عنصر لذلك
    const preview = document.getElementById('filename-preview');
    if (preview) {
        preview.textContent = filename;
    }
}

// ==================== دوال مساعدة ====================

function getCustomerName() {
    const customerSelect = document.getElementById('id_customer');
    return customerSelect ? (customerSelect.options[customerSelect.selectedIndex]?.text || 'عميل_جديد') : 'عميل_جديد';
}

function getBranchName() {
    const branchSelect = document.getElementById('id_branch');
    return branchSelect ? (branchSelect.options[branchSelect.selectedIndex]?.text || 'فرع_غير_محدد') : 'فرع_غير_محدد';
}

function getOrderNumber() {
    const orderField = document.getElementById('id_order');
    const contractField = document.getElementById('id_contract_number');
    return (orderField?.value || contractField?.value || 'بدون_رقم');
}

function getScheduledDate() {
    const dateField = document.getElementById('id_scheduled_date');
    return dateField?.value || new Date().toISOString().split('T')[0];
}

function generateFilename(customer, branch, date, order) {
    const cleanCustomer = cleanFilename(customer);
    const cleanBranch = cleanFilename(branch);
    const cleanOrder = cleanFilename(order);
    return `${cleanCustomer}_${cleanBranch}_${date}_${cleanOrder}.pdf`;
}

function cleanFilename(name) {
    return name.replace(/[^\w\u0600-\u06FF\s-]/g, '')
               .replace(/\s+/g, '_')
               .substring(0, 50);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// تعيين معرف المعاينة (يتم استدعاؤها من القالب)
function setCurrentInspectionId(id) {
    currentInspectionId = id;
}
