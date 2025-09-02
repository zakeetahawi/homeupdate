// وظائف JavaScript لواجهة الاستيراد

// اختيار الجدول للاستيراد
function selectSheet(sheetKey) {
    window.location.href = importSelectUrl + "?sheet=" + sheetKey;
}

// تحديث نطاق الصفحات
function updatePageRange() {
    const importAll = document.getElementById('id_import_all');
    const pageRangeFields = document.getElementById('page-range-fields');
    
    if (importAll.checked) {
        pageRangeFields.style.display = 'none';
    } else {
        pageRangeFields.style.display = 'block';
    }
}

// معاينة البيانات
function previewData() {
    const form = document.getElementById('import-form');
    const previewUrl = form.getAttribute('data-preview-url');
    form.action = previewUrl;
    form.submit();
}

// تنفيذ الاستيراد
function executeImport() {
    const form = document.getElementById('import-form');
    const executeUrl = form.getAttribute('data-execute-url');
    
    // تأكيد الاستيراد
    Swal.fire({
        title: 'تأكيد الاستيراد',
        text: 'هل أنت متأكد من تنفيذ عملية الاستيراد؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'نعم، قم بالاستيراد',
        cancelButtonText: 'إلغاء'
    }).then((result) => {
        if (result.isConfirmed) {
            // عرض مؤشر التقدم
            const progressModal = new bootstrap.Modal(document.getElementById('progress-modal'));
            progressModal.show();
            
            // تنفيذ الاستيراد
            form.action = executeUrl;
            form.submit();
        }
    });
}

// تحديث مؤشر التقدم
function updateProgress(progress) {
    const progressBar = document.querySelector('.progress-bar');
    progressBar.style.width = progress + '%';
    progressBar.setAttribute('aria-valuenow', progress);
    progressBar.textContent = progress + '%';
}
