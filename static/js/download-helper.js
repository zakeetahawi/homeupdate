/**
 * مساعد التحميل المتقدم
 * ========================
 *
 * هذا السكريپت يوفر وظائف تحميل محسنة للملفات المضغوطة
 * ويضمن تحميل الملفات بدلاً من فتحها في المتصفح
 */

class AdvancedDownloadHelper {
    constructor() {
        this.downloadQueue = [];
        this.isDownloading = false;
    }

    /**
     * تحميل ملف باستخدام fetch API
     * @param {string} url - رابط الملف
     * @param {string} filename - اسم الملف (اختياري)
     * @param {function} onProgress - دالة مراقبة التقدم (اختياري)
     */
    async downloadFile(url, filename = null, onProgress = null) {
        try {
            console.log('🚀 بدء تحميل الملف:', url);

            // إظهار مؤشر التحميل
            this.showDownloadIndicator();

            // طلب الملف
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/octet-stream, application/gzip, application/json, */*',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`خطأ في الشبكة: ${response.status} ${response.statusText}`);
            }

            // الحصول على اسم الملف من headers
            if (!filename) {
                const contentDisposition = response.headers.get('Content-Disposition');
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                    if (filenameMatch && filenameMatch[1]) {
                        filename = filenameMatch[1].replace(/['"]/g, '');
                    }
                }

                // اسم افتراضي إذا لم يتم العثور على اسم
                if (!filename) {
                    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
                    filename = `backup_${timestamp}.gz`;
                }
            }

            // قراءة البيانات كـ blob
            const blob = await response.blob();

            console.log('✅ تم تحميل البيانات:', blob.size, 'bytes');

            // تحميل الملف
            this.saveBlob(blob, filename);

            // إخفاء مؤشر التحميل
            this.hideDownloadIndicator();

            console.log('🎉 تم تحميل الملف بنجاح:', filename);
            return true;

        } catch (error) {
            console.error('❌ خطأ في تحميل الملف:', error);
            this.hideDownloadIndicator();
            this.showError('فشل في تحميل الملف: ' + error.message);
            return false;
        }
    }

    /**
     * حفظ blob كملف
     * @param {Blob} blob - البيانات
     * @param {string} filename - اسم الملف
     */
    saveBlob(blob, filename) {
        // التأكد من نوع البيانات الصحيح للملفات المضغوطة
        let finalBlob;
        if (filename.endsWith('.gz')) {
            finalBlob = new Blob([blob], { type: 'application/gzip' });
        } else if (filename.endsWith('.json')) {
            finalBlob = new Blob([blob], { type: 'application/json' });
        } else {
            finalBlob = new Blob([blob], { type: 'application/octet-stream' });
        }

        // إنشاء رابط التحميل
        const url = window.URL.createObjectURL(finalBlob);
        const link = document.createElement('a');

        link.href = url;
        link.download = filename;
        link.style.display = 'none';

        // إضافة الرابط للصفحة وتشغيله
        document.body.appendChild(link);
        link.click();

        // تنظيف الموارد
        setTimeout(() => {
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        }, 100);
    }

    /**
     * تحميل متعدد الملفات
     * @param {Array} urls - قائمة الروابط
     */
    async downloadMultiple(urls) {
        console.log('📦 بدء تحميل متعدد:', urls.length, 'ملف');

        const results = [];
        for (let i = 0; i < urls.length; i++) {
            const url = urls[i];
            console.log(`📥 تحميل ${i + 1}/${urls.length}:`, url);

            const result = await this.downloadFile(url);
            results.push(result);

            // توقف قصير بين التحميلات
            if (i < urls.length - 1) {
                await this.delay(500);
            }
        }

        const successful = results.filter(r => r).length;
        console.log(`✅ اكتمل التحميل: ${successful}/${urls.length} ملف`);

        return results;
    }

    /**
     * تأخير لفترة محددة
     * @param {number} ms - المدة بالميلي ثانية
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * إظهار مؤشر التحميل
     */
    showDownloadIndicator() {
        // إزالة المؤشر السابق إن وجد
        this.hideDownloadIndicator();

        const indicator = document.createElement('div');
        indicator.id = 'download-indicator';
        indicator.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 10000;
                font-family: Arial, sans-serif;
                font-size: 14px;
            ">
                <i class="fas fa-spinner fa-spin" style="margin-left: 8px;"></i>
                جاري تحميل الملف...
            </div>
        `;

        document.body.appendChild(indicator);
    }

    /**
     * إخفاء مؤشر التحميل
     */
    hideDownloadIndicator() {
        const indicator = document.getElementById('download-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * إظهار رسالة خطأ
     * @param {string} message - رسالة الخطأ
     */
    showError(message) {
        // إزالة الرسائل السابقة
        const existingError = document.getElementById('download-error');
        if (existingError) {
            existingError.remove();
        }

        const errorDiv = document.createElement('div');
        errorDiv.id = 'download-error';
        errorDiv.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 10000;
                font-family: Arial, sans-serif;
                font-size: 14px;
                max-width: 300px;
            ">
                <i class="fas fa-exclamation-triangle" style="margin-left: 8px;"></i>
                ${message}
                <button onclick="this.parentElement.parentElement.remove()"
                        style="background: none; border: none; color: white; float: left; cursor: pointer;">
                    ×
                </button>
            </div>
        `;

        document.body.appendChild(errorDiv);

        // إزالة الرسالة تلقائياً بعد 5 ثوانٍ
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.remove();
            }
        }, 5000);
    }

    /**
     * تحسين أزرار التحميل في الصفحة
     */
    enhanceDownloadButtons() {
        console.log('🔧 تحسين أزرار التحميل...');

        // البحث عن جميع روابط التحميل
        const downloadLinks = document.querySelectorAll('a[href*="backup_download"], a[href*="download"]');

        downloadLinks.forEach(link => {
            // تجنب التحسين المكرر
            if (link.hasAttribute('data-enhanced')) {
                return;
            }
            link.setAttribute('data-enhanced', 'true');

            // إضافة مستمع الأحداث
            link.addEventListener('click', (e) => {
                e.preventDefault();

                const url = link.href;
                const filename = link.getAttribute('data-filename') || null;

                // بدء التحميل
                this.downloadFile(url, filename);

                return false;
            });

            console.log('✅ تم تحسين رابط التحميل:', link.href);
        });

        console.log(`🎯 تم تحسين ${downloadLinks.length} رابط تحميل`);
    }

    /**
     * اختبار وظيفة التحميل
     */
    testDownload() {
        console.log('🧪 اختبار وظيفة التحميل...');

        // إنشاء ملف اختبار صغير
        const testData = JSON.stringify({
            test: true,
            timestamp: new Date().toISOString(),
            message: 'هذا ملف اختبار للتحميل'
        }, null, 2);

        const blob = new Blob([testData], { type: 'application/json' });
        this.saveBlob(blob, 'test_download.json');

        console.log('✅ تم إنشاء ملف اختبار');
    }

    /**
     * تحقق من دعم المتصفح للتحميل
     */
    checkBrowserSupport() {
        const support = {
            fetch: typeof fetch !== 'undefined',
            blob: typeof Blob !== 'undefined',
            url: typeof URL !== 'undefined' && typeof URL.createObjectURL !== 'undefined',
            download: document.createElement('a').download !== undefined
        };

        console.log('🔍 دعم المتصفح للتحميل:', support);

        const allSupported = Object.values(support).every(Boolean);
        if (!allSupported) {
            console.warn('⚠️ المتصفح لا يدعم جميع ميزات التحميل المطلوبة');
        }

        return allSupported;
    }
}

// إنشاء مثيل عام
window.downloadHelper = new AdvancedDownloadHelper();

// تشغيل التحسينات عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 تحميل مساعد التحميل المتقدم...');

    // فحص دعم المتصفح
    if (window.downloadHelper.checkBrowserSupport()) {
        // تحسين أزرار التحميل
        window.downloadHelper.enhanceDownloadButtons();
        console.log('✅ تم تفعيل مساعد التحميل المتقدم');
    } else {
        console.error('❌ المتصفح لا يدعم ميزات التحميل المطلوبة');
    }
});

// إضافة وظائف مساعدة للاستخدام العام
window.downloadFile = function(url, filename) {
    return window.downloadHelper.downloadFile(url, filename);
};

window.testDownload = function() {
    return window.downloadHelper.testDownload();
};

// معالج الأخطاء العام
window.addEventListener('error', function(e) {
    if (e.message && e.message.includes('download')) {
        console.error('❌ خطأ في التحميل:', e.message);
    }
});

console.log('📥 تم تحميل مساعد التحميل المتقدم - الإصدار 1.0');
