/**
 * نظام رفع ملفات العقود إلى Google Drive
 */

// متغيرات عامة
let contractUploadInProgress = false;
let currentOrderId = null;

// تهيئة النظام عند تحميل الصفحة
$(document).ready(function() {
    initializeContractGoogleDriveUpload();
});

/**
 * تهيئة نظام رفع Google Drive للعقود
 */
function initializeContractGoogleDriveUpload() {
    // مراقبة تغيير ملف العقد
    $('#id_contract_file').on('change', function() {
        if (this.files && this.files[0]) {
            handleContractFileSelection(this.files[0]);
        }
    });
    
    // مراقبة تغيير بيانات النموذج لتحديث معاينة اسم الملف
    $('#id_customer, #id_branch, #id_order_date, #id_contract_number').on('change', function() {
        updateContractFilenamePreview();
    });
    
    // تحديث معاينة اسم الملف عند التحميل
    updateContractFilenamePreview();
}

/**
 * معالجة اختيار ملف العقد
 */
function handleContractFileSelection(file) {
    if (contractUploadInProgress) {
        showContractError('يتم رفع ملف آخر حالياً. يرجى الانتظار.');
        return;
    }
    
    // التحقق من نوع الملف
    if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
        showContractError('يجب أن يكون الملف من نوع PDF');
        return;
    }
    
    // التحقق من حجم الملف (أقل من 50MB)
    if (file.size > 50 * 1024 * 1024) {
        showContractError('حجم الملف كبير جداً (الحد الأقصى 50MB)');
        return;
    }
    
    // إذا كان هناك معرف طلب (في حالة التعديل)، رفع الملف مباشرة
    if (currentOrderId) {
        uploadContractToGoogleDrive();
    } else {
        // في حالة الإنشاء الجديد، لا نعرض معاينة - سيتم الرفع عند الحفظ
        // تم إزالة showContractUploadPreview لتجنب الإزعاج
        // console.log('تم اختيار ملف العقد:', file.name, 'سيتم رفعه عند حفظ الطلب');
    }
}

/**
 * عرض معاينة رفع العقد - تم تعطيلها نهائياً
 * تحديث: 2025-08-11 - إزالة جميع الإشعارات المنبثقة
 */
function showContractUploadPreview(file) {
    // تم تعطيل معاينة رفع العقد نهائياً لتجنب الإزعاج
    // سيتم رفع الملف تلقائياً عند حفظ الطلب بدون أي إشعارات
    // console.log('تم تعطيل معاينة رفع العقد - الملف سيرفع تلقائياً');
    return false;
}

/**
 * رفع ملف العقد إلى Google Drive
 */
function uploadContractToGoogleDrive() {
    if (!currentOrderId) {
        showContractError('يجب حفظ الطلب أولاً قبل رفع الملف');
        return;
    }
    
    contractUploadInProgress = true;
    
    const customerName = getCustomerName();
    const branchName = getBranchName();
    const contractNumber = getContractNumber();
    const date = getOrderDate();
    const expectedFilename = generateContractFilename(customerName, branchName, date, contractNumber);
    
    // عرض نافذة التقدم
    Swal.fire({
        title: 'جاري رفع ملف العقد...',
        html: `
            <div class="upload-progress">
                <p><strong>اسم الملف المتوقع:</strong> ${expectedFilename}</p>
                <div class="progress mt-3">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%" id="contract-upload-progress"></div>
                </div>
                <p class="mt-2 text-muted" id="contract-upload-status">بدء الرفع...</p>
            </div>
        `,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        customClass: {
            popup: 'upload-progress-popup'
        }
    });
    
    // محاكاة التقدم
    simulateContractProgress();
    
    // إرسال طلب الرفع
    const formData = new FormData();
    formData.append('order_id', currentOrderId);
    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
    
    $.ajax({
        url: '/orders/ajax/upload-contract-to-google-drive/',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            contractUploadInProgress = false;
            if (response.success) {
                showContractUploadSuccess(response.data);
            } else {
                showContractError(response.message);
            }
        },
        error: function(xhr, status, error) {
            contractUploadInProgress = false;
            showContractError('حدث خطأ في الشبكة أثناء رفع الملف');
        }
    });
}

/**
 * محاكاة تقدم رفع العقد
 */
function simulateContractProgress() {
    let progress = 0;
    const progressBar = document.getElementById('contract-upload-progress');
    const statusText = document.getElementById('contract-upload-status');
    
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 95) progress = 95;
        
        if (progressBar) {
            progressBar.style.width = progress + '%';
        }
        
        if (statusText) {
            if (progress < 30) {
                statusText.textContent = 'تحضير الملف...';
            } else if (progress < 60) {
                statusText.textContent = 'رفع الملف إلى Google Drive...';
            } else if (progress < 90) {
                statusText.textContent = 'معالجة الملف...';
            } else {
                statusText.textContent = 'إنهاء العملية...';
            }
        }
        
        if (progress >= 95) {
            clearInterval(interval);
        }
    }, 200);
}

/**
 * عرض رسالة نجاح رفع العقد
 */
function showContractUploadSuccess(data) {
    // إغلاق نافذة التقدم
    Swal.close();

    // إعادة تحميل الصفحة لتحديث البيانات بدون رسالة منبثقة
    setTimeout(() => {
        location.reload();
    }, 500);
}

/**
 * عرض رسالة خطأ للعقود
 */
function showContractError(message) {
    Swal.fire({
        icon: 'error',
        title: 'خطأ في رفع ملف العقد',
        text: message,
        confirmButtonText: 'موافق',
        customClass: {
            confirmButton: 'btn btn-danger'
        }
    });
}

/**
 * تحديث معاينة اسم ملف العقد
 */
function updateContractFilenamePreview() {
    const customerName = getCustomerName();
    const branchName = getBranchName();
    const contractNumber = getContractNumber();
    const date = getOrderDate();
    const filename = generateContractFilename(customerName, branchName, date, contractNumber);
    
    // تحديث معاينة اسم الملف إذا كان العنصر موجود
    const previewElement = document.getElementById('contract-filename-preview');
    if (previewElement) {
        previewElement.textContent = filename;
    }
}

// ==================== دوال مساعدة للعقود ====================

function getContractNumber() {
    const contractField = document.getElementById('id_contract_number');
    return contractField?.value || 'بدون_رقم_عقد';
}

function getOrderDate() {
    const dateField = document.getElementById('id_order_date');
    return dateField?.value || new Date().toISOString().split('T')[0];
}

function generateContractFilename(customer, branch, date, contractNumber) {
    const cleanCustomer = cleanFilename(customer);
    const cleanBranch = cleanFilename(branch);
    const cleanContract = cleanFilename(contractNumber);
    return `عقد_${cleanCustomer}_${cleanBranch}_${date}_${cleanContract}.pdf`;
}

// استخدام نفس دوال التنظيف من ملف المعاينات
function cleanFilename(name) {
    return name.replace(/[^\w\u0600-\u06FF\s-]/g, '')
               .replace(/\s+/g, '_')
               .substring(0, 50);
}

// دوال مشتركة مع ملف المعاينات
function getCustomerName() {
    const customerSelect = document.getElementById('id_customer');
    return customerSelect ? (customerSelect.options[customerSelect.selectedIndex]?.text || 'عميل_جديد') : 'عميل_جديد';
}

function getBranchName() {
    const branchSelect = document.getElementById('id_branch');
    return branchSelect ? (branchSelect.options[branchSelect.selectedIndex]?.text || 'فرع_غير_محدد') : 'فرع_غير_محدد';
}

// تعيين معرف الطلب الحالي (يتم استدعاؤها من الصفحة)
function setCurrentOrderId(orderId) {
    currentOrderId = orderId;
}
