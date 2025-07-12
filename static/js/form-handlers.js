/**
 * معالج النماذج المحسن باستخدام AJAX
 * يوفر تجربة مستخدم أفضل مع تحديثات فورية
 */

class FormHandler {
    constructor(formSelector, options = {}) {
        this.form = document.querySelector(formSelector);
        this.options = {
            showLoading: true,
            showSuccess: true,
            showError: true,
            redirectOnSuccess: false,
            redirectUrl: null,
            updatePageData: false,
            ...options
        };
        
        if (this.form) {
            this.setupAjaxSubmission();
            this.setupFormValidation();
        }
    }
    
    setupAjaxSubmission() {
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitForm();
        });
    }
    
    setupFormValidation() {
        // إضافة التحقق من صحة النماذج في الوقت الفعلي
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    }
    
    async submitForm() {
        if (!this.validateForm()) {
            return;
        }
        
        const formData = new FormData(this.form);
        const submitButton = this.form.querySelector('button[type="submit"]');
        const originalButtonText = submitButton?.innerHTML;
        
        try {
            // إظهار مؤشر التحميل
            if (this.options.showLoading && submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>جاري الحفظ...';
            }
            
            const response = await fetch(this.form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.handleSuccess(data);
            } else {
                this.handleError(data.errors || data.message);
            }
            
        } catch (error) {
            console.error('Form submission error:', error);
            this.handleError('حدث خطأ في الاتصال بالخادم');
        } finally {
            // إعادة تعيين الزر
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }
        }
    }
    
    validateForm() {
        let isValid = true;
        const requiredFields = this.form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    validateField(field) {
        const value = field.value.trim();
        const isRequired = field.hasAttribute('required');
        
        // إزالة رسائل الخطأ السابقة
        this.clearFieldError(field);
        
        // التحقق من الحقول المطلوبة
        if (isRequired && !value) {
            this.showFieldError(field, 'هذا الحقل مطلوب');
            return false;
        }
        
        // التحقق من البريد الإلكتروني
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                this.showFieldError(field, 'يرجى إدخال بريد إلكتروني صحيح');
                return false;
            }
        }
        
        // التحقق من الأرقام
        if (field.type === 'number' && value) {
            if (isNaN(value)) {
                this.showFieldError(field, 'يرجى إدخال رقم صحيح');
                return false;
            }
        }
        
        return true;
    }
    
    showFieldError(field, message) {
        field.classList.add('is-invalid');
        
        let errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            field.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
    }
    
    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorElement = field.parentNode.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.remove();
        }
    }
    
    handleSuccess(data) {
        if (this.options.showSuccess) {
            this.showSuccessMessage(data.message || 'تم الحفظ بنجاح');
        }
        
        if (this.options.updatePageData && data.data) {
            this.updatePageData(data.data);
        }
        
        if (this.options.redirectOnSuccess) {
            setTimeout(() => {
                window.location.href = this.options.redirectUrl || data.redirect_url || '/';
            }, 1500);
        }
    }
    
    handleError(errors) {
        if (this.options.showError) {
            if (typeof errors === 'object') {
                // أخطاء متعددة للحقول
                Object.keys(errors).forEach(fieldName => {
                    const field = this.form.querySelector(`[name="${fieldName}"]`);
                    if (field) {
                        this.showFieldError(field, errors[fieldName]);
                    }
                });
            } else {
                // رسالة خطأ عامة
                this.showErrorMessage(errors);
            }
        }
    }
    
    showSuccessMessage(message) {
        Swal.fire({
            icon: 'success',
            title: 'نجح!',
            text: message,
            timer: 2000,
            showConfirmButton: false,
            customClass: {
                popup: 'rtl-popup'
            }
        });
    }
    
    showErrorMessage(message) {
        Swal.fire({
            icon: 'error',
            title: 'خطأ!',
            text: message,
            confirmButtonText: 'موافق',
            customClass: {
                popup: 'rtl-popup'
            }
        });
    }
    
    updatePageData(data) {
        // تحديث البيانات في الصفحة بدون إعادة تحميل
        if (data.counts) {
            Object.keys(data.counts).forEach(key => {
                const element = document.querySelector(`[data-count="${key}"]`);
                if (element) {
                    element.textContent = data.counts[key];
                }
            });
        }
        
        if (data.lists) {
            Object.keys(data.lists).forEach(key => {
                const container = document.querySelector(`[data-list="${key}"]`);
                if (container && data.lists[key]) {
                    container.innerHTML = data.lists[key];
                }
            });
        }
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
}

/**
 * معالج النماذج المتقدم مع دعم الملفات
 */
class AdvancedFormHandler extends FormHandler {
    constructor(formSelector, options = {}) {
        super(formSelector, options);
        this.setupFileUpload();
    }
    
    setupFileUpload() {
        const fileInputs = this.form.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', (e) => this.handleFileSelect(e));
        });
    }
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        const preview = this.form.querySelector(`[data-preview="${event.target.name}"]`);
        
        if (file && preview) {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        }
    }
    
    async submitForm() {
        // التحقق من حجم الملفات
        const fileInputs = this.form.querySelectorAll('input[type="file"]');
        for (const input of fileInputs) {
            if (input.files.length > 0) {
                const file = input.files[0];
                if (file.size > 5 * 1024 * 1024) { // 5MB
                    this.showErrorMessage('حجم الملف يجب أن يكون أقل من 5 ميجابايت');
                    return;
                }
            }
        }
        
        await super.submitForm();
    }
}

/**
 * معالج النماذج مع البحث المباشر
 */
class SearchFormHandler extends FormHandler {
    constructor(formSelector, options = {}) {
        super(formSelector, options);
        this.setupLiveSearch();
    }
    
    setupLiveSearch() {
        const searchInputs = this.form.querySelectorAll('input[data-search]');
        searchInputs.forEach(input => {
            let timeout;
            input.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.performSearch(e.target.value, e.target.dataset.search);
                }, 300);
            });
        });
    }
    
    async performSearch(query, searchType) {
        try {
            const response = await fetch(`/api/search/${searchType}/?q=${encodeURIComponent(query)}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            this.updateSearchResults(data.results, searchType);
            
        } catch (error) {
            console.error('Search error:', error);
        }
    }
    
    updateSearchResults(results, searchType) {
        const container = document.querySelector(`[data-results="${searchType}"]`);
        if (container) {
            container.innerHTML = results.map(item => `
                <div class="search-result-item" data-id="${item.id}">
                    <div class="search-result-title">${item.title}</div>
                    <div class="search-result-subtitle">${item.subtitle || ''}</div>
                </div>
            `).join('');
        }
    }
}

// تصدير الفئات للاستخدام العام
window.FormHandler = FormHandler;
window.AdvancedFormHandler = AdvancedFormHandler;
window.SearchFormHandler = SearchFormHandler;

// تهيئة تلقائية للنماذج
document.addEventListener('DOMContentLoaded', function() {
    // تهيئة النماذج العادية
    document.querySelectorAll('form[data-ajax="true"]').forEach(form => {
        new FormHandler(`#${form.id}`);
    });
    
    // تهيئة النماذج المتقدمة
    document.querySelectorAll('form[data-advanced="true"]').forEach(form => {
        new AdvancedFormHandler(`#${form.id}`);
    });
    
    // تهيئة نماذج البحث
    document.querySelectorAll('form[data-search-form="true"]').forEach(form => {
        new SearchFormHandler(`#${form.id}`);
    });
}); 