/**
 * ماسح الباركود المبسط باستخدام حقل الإدخال
 * Simple Barcode Scanner using Input Field
 */

class SimpleBarcodeScanner {
    constructor(inputSelector, options = {}) {
        this.inputElement = document.querySelector(inputSelector);
        this.onScanSuccess = options.onScanSuccess || this.defaultOnSuccess;
        this.scanButton = null;
        this.init();
    }

    init() {
        if (!this.inputElement) {
            console.error('عنصر الإدخال غير موجود');
            return;
        }

        // إنشاء زر المسح
        this.createScanButton();
        
        // إضافة مستمع للضغط على Enter
        this.inputElement.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.processScan();
            }
        });
    }

    createScanButton() {
        // إنشاء زر بجانب حقل الإدخال
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-primary ms-2';
        button.innerHTML = '<i class="fas fa-barcode me-1"></i>مسح';
        button.onclick = () => this.processScan();

        // إدراج الزر بعد حقل الإدخال
        this.inputElement.parentNode.insertBefore(button, this.inputElement.nextSibling);
        this.scanButton = button;
    }

    async processScan() {
        const barcode = this.inputElement.value.trim();
        
        if (!barcode) {
            this.showMessage('error', 'يرجى إدخال الباركود');
            return;
        }

        // تمييز الحقل بأنه قيد المعالجة
        this.inputElement.classList.add('border-primary');
        this.scanButton.disabled = true;
        this.scanButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>جاري البحث...';

        try {
            // استدعاء معالج النجاح
            await this.onScanSuccess(barcode);
            
            // مسح الحقل بعد النجاح
            this.inputElement.value = '';
            this.inputElement.focus();
            
        } catch (error) {
            this.showMessage('error', error.message || 'حدث خطأ أثناء المعالجة');
        } finally {
            this.inputElement.classList.remove('border-primary');
            this.scanButton.disabled = false;
            this.scanButton.innerHTML = '<i class="fas fa-barcode me-1"></i>مسح';
        }
    }

    showMessage(type, message) {
        // إنشاء رسالة Toast
        const toastHTML = `
            <div class="toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0" 
                 role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        // إضافة Toast إلى الصفحة
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        const toastElement = document.createElement('div');
        toastElement.innerHTML = toastHTML;
        toastContainer.appendChild(toastElement.firstElementChild);

        const toast = new bootstrap.Toast(toastElement.firstElementChild);
        toast.show();

        // إزالة Toast بعد الإخفاء
        toastElement.firstElementChild.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    defaultOnSuccess(barcode) {
        console.log('تم مسح الباركود:', barcode);
        this.showMessage('success', `تم المسح بنجاح: ${barcode}`);
        return Promise.resolve();
    }
}

// تصدير الكلاس
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimpleBarcodeScanner;
}
