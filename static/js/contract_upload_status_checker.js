/**
 * نظام فحص حالة رفع ملفات العقود إلى Google Drive
 */

// نظام فحص حالة رفع العقود
window.contractUploadStatusChecker = {
    // قائمة العقود المعلقة
    pendingContracts: new Set(),
    
    // فترة الفحص (بالثواني)
    checkInterval: 5,
    
    // عداد المحاولات القصوى
    maxRetries: 12, // 12 * 5 ثواني = دقيقة واحدة
    
    // خريطة عدادات المحاولات
    retryCounters: new Map(),
    
    /**
     * بدء فحص حالة رفع العقد
     */
    startChecking: function(orderId) {
        console.log('بدء فحص حالة رفع العقد:', orderId);
        
        // إضافة إلى قائمة المعلقة
        this.pendingContracts.add(orderId);
        this.retryCounters.set(orderId, 0);
        
        // تحديث الأيقونة فوراً
        this.updateIcons(orderId, { is_uploaded: false });
        
        // بدء الفحص الدوري
        this.scheduleCheck(orderId);
    },
    
    /**
     * جدولة فحص العقد
     */
    scheduleCheck: function(orderId) {
        setTimeout(() => {
            this.checkContractStatus(orderId);
        }, this.checkInterval * 1000);
    },
    
    /**
     * فحص حالة رفع العقد
     */
    checkContractStatus: function(orderId) {
        if (!this.pendingContracts.has(orderId)) {
            return; // تم إلغاء الفحص
        }
        
        const retryCount = this.retryCounters.get(orderId) || 0;
        
        if (retryCount >= this.maxRetries) {
            console.log('تم الوصول للحد الأقصى من المحاولات للعقد:', orderId);
            this.stopChecking(orderId);
            this.updateIcons(orderId, { is_uploaded: false, error: 'timeout' });
            return;
        }
        
        // زيادة عداد المحاولات
        this.retryCounters.set(orderId, retryCount + 1);
        
        console.log(`فحص حالة العقد ${orderId} - المحاولة ${retryCount + 1}/${this.maxRetries}`);
        
        // إرسال طلب فحص الحالة
        fetch(`/orders/${orderId}/check-contract-upload-status/`)
            .then(response => response.json())
            .then(data => {
                console.log('نتيجة فحص العقد:', orderId, data);
                
                if (data.is_uploaded && data.google_drive_url && data.file_id) {
                    // تم الرفع بنجاح
                    console.log('تم رفع العقد بنجاح:', orderId);
                    this.stopChecking(orderId);
                    this.updateIcons(orderId, data);
                    
                    // إشعار بالنجاح
                    this.showSuccessNotification(orderId, data);
                } else {
                    // لم يتم الرفع بعد، جدولة فحص آخر
                    this.scheduleCheck(orderId);
                }
            })
            .catch(error => {
                console.error('خطأ في فحص حالة العقد:', orderId, error);
                
                // في حالة الخطأ، جدولة فحص آخر
                this.scheduleCheck(orderId);
            });
    },
    
    /**
     * إيقاف فحص العقد
     */
    stopChecking: function(orderId) {
        this.pendingContracts.delete(orderId);
        this.retryCounters.delete(orderId);
        console.log('تم إيقاف فحص العقد:', orderId);
    },
    
    /**
     * تحديث أيقونات حالة رفع العقد
     */
    updateIcons: function(orderId, data) {
        // البحث عن عناصر العقد في الصفحة
        const contractElements = document.querySelectorAll(`[data-order-id="${orderId}"]`);
        
        contractElements.forEach(element => {
            const iconContainer = element.querySelector('.contract-upload-status');
            if (!iconContainer) return;
            
            // إزالة الأيقونات القديمة
            iconContainer.innerHTML = '';
            
            if (data.is_uploaded && data.google_drive_url) {
                // أيقونة النجاح
                iconContainer.innerHTML = `
                    <a href="${data.google_drive_url}" target="_blank" 
                       class="btn btn-success btn-sm" 
                       title="تم رفع العقد إلى Google Drive - ${data.file_name || 'ملف العقد'}">
                        <i class="fas fa-cloud-upload-alt"></i>
                        <span class="d-none d-md-inline">تم الرفع</span>
                    </a>
                `;
            } else if (data.error === 'timeout') {
                // أيقونة انتهاء الوقت
                iconContainer.innerHTML = `
                    <button type="button" class="btn btn-warning btn-sm" 
                            onclick="contractUploadStatusChecker.retryCheck(${orderId})"
                            title="انتهت مهلة الفحص - اضغط للمحاولة مرة أخرى">
                        <i class="fas fa-clock"></i>
                        <span class="d-none d-md-inline">إعادة فحص</span>
                    </button>
                `;
            } else {
                // أيقونة الانتظار
                iconContainer.innerHTML = `
                    <button type="button" class="btn btn-info btn-sm" disabled
                            title="جاري فحص حالة رفع العقد...">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span class="d-none d-md-inline">جاري الفحص</span>
                    </button>
                `;
            }
        });
    },
    
    /**
     * إعادة محاولة فحص العقد
     */
    retryCheck: function(orderId) {
        console.log('إعادة محاولة فحص العقد:', orderId);
        this.startChecking(orderId);
    },
    
    /**
     * عرض إشعار النجاح
     */
    showSuccessNotification: function(orderId, data) {
        // تسجيل النجاح في وحدة التحكم فقط - بدون رسائل منبثقة
        console.log(`✅ تم رفع العقد ${orderId} بنجاح إلى Google Drive`);
    },
    
    /**
     * فحص جميع العقود في الصفحة
     */
    checkAllContractsOnPage: function() {
        const contractElements = document.querySelectorAll('[data-order-id]');
        contractElements.forEach(element => {
            const orderId = element.getAttribute('data-order-id');
            const uploadStatus = element.querySelector('.contract-upload-status');
            
            if (orderId && uploadStatus && !element.hasAttribute('data-contract-upload-checked')) {
                // وضع علامة أنه تم فحصه
                element.setAttribute('data-contract-upload-checked', 'true');
                
                // فحص سريع للحالة
                fetch(`/orders/${orderId}/check-contract-upload-status/`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.is_uploaded && data.google_drive_url && data.file_id) {
                            this.updateIcons(parseInt(orderId), data);
                        }
                    })
                    .catch(() => {
                        console.log('فحص سريع فشل للعقد:', orderId);
                    });
            }
        });
    }
};

// تهيئة النظام عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    console.log('تهيئة نظام فحص حالة رفع العقود...');
    
    // فحص جميع العقود في الصفحة
    window.contractUploadStatusChecker.checkAllContractsOnPage();
    
    // التحقق من جميع العقود للتأكد من حالتها
    const allContractElements = document.querySelectorAll('[data-order-id]');
    allContractElements.forEach(element => {
        const orderId = element.getAttribute('data-order-id');
        if (orderId && !element.hasAttribute('data-contract-upload-pending')) {
            // تحقق سريع من الحالة
            fetch(`/orders/${orderId}/check-contract-upload-status/`)
                .then(response => response.json())
                .then(data => {
                    if (data.is_uploaded && data.google_drive_url && data.file_id) {
                        // تحديث الأيقونة إذا كانت خاطئة
                        window.contractUploadStatusChecker.updateIcons(parseInt(orderId), data);
                    }
                })
                .catch(() => {
                    console.log('تحقق سريع فشل للعقد:', orderId);
                });
        }
    });
});
