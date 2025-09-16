/**
 * نظام التحقق من حالة رفع الملفات وتحديث الأيقونات
 */

class UploadStatusChecker {
    constructor() {
        this.checkInterval = null;
        this.maxAttempts = 30;
        this.checkDelay = 2000; // ثانيتين
        this.activeChecks = new Set();
    }

    /**
     * بدء التحقق من حالة رفع ملف معاينة
     */
    startChecking(inspectionId) {
        if (this.activeChecks.has(inspectionId)) {
            console.log('التحقق جاري بالفعل للمعاينة:', inspectionId);
            return;
        }

        this.activeChecks.add(inspectionId);
        console.log('بدء التحقق من حالة الرفع للمعاينة:', inspectionId);

        let attempts = 0;
        const interval = setInterval(() => {
            attempts++;
            console.log(`محاولة التحقق رقم ${attempts} للمعاينة ${inspectionId}`);

            this.checkStatus(inspectionId)
                .then(response => {
                    console.log('استجابة التحقق:', response);

                    if (response.is_uploaded && response.google_drive_url && response.file_id) {
                        // تم الرفع بنجاح
                        clearInterval(interval);
                        this.activeChecks.delete(inspectionId);
                        console.log('تم الرفع بنجاح للمعاينة:', inspectionId);

                        // تحديث الأيقونات في الصفحة
                        this.updateIcons(inspectionId, response);

                        // عرض رسالة نجاح
                        this.showSuccessMessage();

                    } else if (attempts >= this.maxAttempts) {
                        // انتهت المحاولات
                        clearInterval(interval);
                        this.activeChecks.delete(inspectionId);
                        console.log('انتهت محاولات التحقق للمعاينة:', inspectionId);
                        this.showTimeoutMessage();
                    } else {
                        // لا يزال قيد الرفع
                        console.log(`المعاينة ${inspectionId} لا تزال قيد الرفع...`);
                    }
                })
                .catch(error => {
                    console.error('خطأ في التحقق من حالة الرفع:', error);
                    if (attempts >= this.maxAttempts) {
                        clearInterval(interval);
                        this.activeChecks.delete(inspectionId);
                    }
                });
        }, this.checkDelay);
    }

    /**
     * التحقق من حالة الرفع عبر AJAX
     */
    async checkStatus(inspectionId) {
        const response = await fetch(`/inspections/${inspectionId}/check-upload-status/`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }

    /**
     * تحديث الأيقونات في الصفحة
     */
    updateIcons(inspectionId, data) {
        // البحث عن جميع الأيقونات المتعلقة بهذه المعاينة
        const selectors = [
            `[data-inspection-id="${inspectionId}"]`,
            `#inspection-${inspectionId}-file`,
            `.inspection-file-${inspectionId}`,
            `tr[data-inspection="${inspectionId}"] .file-icon`,
            `#inspection-file-${inspectionId}`
        ];

        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                this.updateSingleIcon(element, data);
            });
        });

        // تحديث أيقونات عامة (في الجداول)
        this.updateTableIcons(inspectionId, data);
    }

    /**
     * تحديث أيقونة واحدة
     */
    updateSingleIcon(element, data) {
        if (!element) return;

        // إزالة الأيقونات القديمة
        const oldIcons = element.querySelectorAll('i.fas, i.fab');
        oldIcons.forEach(icon => icon.remove());

        // إنشاء رابط جديد
        if (element.tagName === 'A') {
            element.href = data.google_drive_url;
            element.target = '_blank';
            element.title = 'عرض ملف المعاينة في Google Drive';
        } else {
            // تحويل العنصر إلى رابط
            const link = document.createElement('a');
            link.href = data.google_drive_url;
            link.target = '_blank';
            link.title = 'عرض ملف المعاينة في Google Drive';

            // نسخ المحتوى
            link.innerHTML = element.innerHTML;
            element.parentNode.replaceChild(link, element);
            element = link;
        }

        // إضافة الأيقونة الجديدة
        const icon = document.createElement('i');
        icon.className = 'fas fa-file-pdf text-danger';
        icon.style.fontSize = element.classList.contains('large-icon') ? '48px' : '20px';

        element.innerHTML = '';
        element.appendChild(icon);
    }

    /**
     * تحديث أيقونات الجداول
     */
    updateTableIcons(inspectionId, data) {
        // البحث في جداول المعاينات
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            const rows = table.querySelectorAll('tr');
            rows.forEach(row => {
                // البحث عن الصف الذي يحتوي على معرف المعاينة
                const idCell = row.querySelector('td:first-child');
                if (idCell && (
                    idCell.textContent.includes(`#${inspectionId}`) ||
                    idCell.textContent.includes(`${inspectionId}`)
                )) {
                    // العثور على خلية الملف
                    const fileCells = row.querySelectorAll('td');
                    fileCells.forEach(cell => {
                        const fileIcon = cell.querySelector('i.fa-file-pdf');
                        if (fileIcon) {
                            this.updateFileCell(cell, data);
                        }
                    });
                }
            });
        });
    }

    /**
     * تحديث خلية الملف في الجدول
     */
    updateFileCell(cell, data) {
        // إنشاء رابط جديد
        const link = document.createElement('a');
        link.href = data.google_drive_url;
        link.target = '_blank';
        link.title = 'عرض ملف المعاينة في Google Drive';

        // إنشاء أيقونة جديدة
        const icon = document.createElement('i');
        icon.className = 'fas fa-file-pdf text-danger';
        icon.style.fontSize = '20px';

        link.appendChild(icon);
        cell.innerHTML = '';
        cell.appendChild(link);
    }

    /**
     * عرض رسالة نجاح
     */
    showSuccessMessage() {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'success',
                title: 'تم رفع الملف بنجاح!',
                text: 'تم رفع ملف المعاينة إلى Google Drive',
                timer: 3000,
                showConfirmButton: false,
                toast: true,
                position: 'top-end'
            });
        }
    }

    /**
     * عرض رسالة انتهاء الوقت
     */
    showTimeoutMessage() {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: 'تأخر في الرفع',
                text: 'يرجى تحديث الصفحة للتحقق من حالة الرفع',
                confirmButtonText: 'تحديث الصفحة',
                showCancelButton: true,
                cancelButtonText: 'إلغاء'
            }).then((result) => {
                if (result.isConfirmed) {
                    location.reload();
                }
            });
        }
    }

    /**
     * إيقاف جميع عمليات التحقق
     */
    stopAllChecks() {
        this.activeChecks.clear();
    }
}

// إنشاء مثيل عام
window.uploadStatusChecker = new UploadStatusChecker();

// دالة مساعدة للاستخدام السهل
window.checkUploadStatus = function(inspectionId) {
    window.uploadStatusChecker.startChecking(inspectionId);
};

// تحديث تلقائي عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // البحث عن الملفات قيد الرفع وبدء التحقق
    const pendingUploads = document.querySelectorAll('[data-upload-pending="true"]');
    pendingUploads.forEach(element => {
        const inspectionId = element.getAttribute('data-inspection-id');
        if (inspectionId) {
            console.log('بدء التحقق من المعاينة قيد الرفع:', inspectionId);
            window.uploadStatusChecker.startChecking(parseInt(inspectionId));
        }
    });

    // التحقق من جميع المعاينات للتأكد من حالتها
    const allInspectionElements = document.querySelectorAll('[data-inspection-id]');
    allInspectionElements.forEach(element => {
        const inspectionId = element.getAttribute('data-inspection-id');
        if (inspectionId && !element.hasAttribute('data-upload-pending')) {
            // تحقق سريع من الحالة
            fetch(`/inspections/${inspectionId}/check-upload-status/`)
                .then(response => response.json())
                .then(data => {
                    if (data.is_uploaded && data.google_drive_url && data.file_id) {
                        // تحديث الأيقونة إذا كانت خاطئة
                        window.uploadStatusChecker.updateIcons(parseInt(inspectionId), data);
                    }
                })
                .catch(() => {
                    console.log('تحقق سريع فشل للمعاينة:', inspectionId);
                });
        }
    });
});
