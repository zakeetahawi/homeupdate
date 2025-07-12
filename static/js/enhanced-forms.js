/**
 * Enhanced Forms JavaScript
 * تحسينات متقدمة للنماذج مع رسائل تأكيد أفضل وتجربة مستخدم محسنة
 */

(function() {
    'use strict';
    
    // Color codes for terminal messages
    const colors = {
        red: '\x1b[31m',
        green: '\x1b[32m',
        yellow: '\x1b[33m',
        blue: '\x1b[34m',
        magenta: '\x1b[35m',
        cyan: '\x1b[36m',
        white: '\x1b[37m',
        reset: '\x1b[0m'
    };
    
    /**
     * Enhanced form validation with better UX
     */
    class EnhancedFormValidator {
        constructor(formSelector) {
            this.form = document.querySelector(formSelector);
            this.submitButton = this.form.querySelector('button[type="submit"]');
            this.originalButtonText = this.submitButton ? this.submitButton.innerHTML : '';
            this.init();
        }
        
        init() {
            this.setupValidation();
            this.setupRealTimeValidation();
            this.setupAutoSave();
            this.setupConfirmationDialogs();
        }
        
        setupValidation() {
            this.form.addEventListener('submit', (e) => {
                if (!this.validateForm()) {
                    e.preventDefault();
                    this.showValidationErrors();
                } else {
                    this.showLoadingState();
                }
            });
        }
        
        setupRealTimeValidation() {
            const inputs = this.form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', () => this.validateField(input));
                input.addEventListener('input', () => this.clearFieldError(input));
            });
        }
        
        setupAutoSave() {
            let autoSaveTimer;
            const inputs = this.form.querySelectorAll('input, select, textarea');
            
            inputs.forEach(input => {
                input.addEventListener('input', () => {
                    clearTimeout(autoSaveTimer);
                    autoSaveTimer = setTimeout(() => {
                        this.autoSave();
                    }, 2000);
                });
            });
        }
        
        setupConfirmationDialogs() {
            const deleteButtons = document.querySelectorAll('.btn-delete, .delete-btn');
            deleteButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    if (!this.confirmDelete()) {
                        e.preventDefault();
                    }
                });
            });
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
            
            // Clear previous errors
            this.clearFieldError(field);
            
            // Required field validation
            if (isRequired && !value) {
                this.showFieldError(field, 'هذا الحقل مطلوب');
                return false;
            }
            
            // Email validation
            if (field.type === 'email' && value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(value)) {
                    this.showFieldError(field, 'البريد الإلكتروني غير صحيح');
                    return false;
                }
            }
            
            // Phone validation
            if (field.name.includes('phone') && value) {
                const phoneRegex = /^[\+]?[0-9\s\-\(\)]{8,}$/;
                if (!phoneRegex.test(value)) {
                    this.showFieldError(field, 'رقم الهاتف غير صحيح');
                    return false;
                }
            }
            
            // Number validation
            if (field.type === 'number' && value) {
                const numValue = parseFloat(value);
                if (isNaN(numValue) || numValue < 0) {
                    this.showFieldError(field, 'القيمة يجب أن تكون رقم موجب');
                    return false;
                }
            }
            
            // Show success state
            this.showFieldSuccess(field);
            return true;
        }
        
        showFieldError(field, message) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            
            let errorElement = field.parentNode.querySelector('.invalid-feedback');
            if (!errorElement) {
                errorElement = document.createElement('div');
                errorElement.className = 'invalid-feedback';
                field.parentNode.appendChild(errorElement);
            }
            errorElement.textContent = message;
        }
        
        showFieldSuccess(field) {
            field.classList.add('is-valid');
            field.classList.remove('is-invalid');
            
            const errorElement = field.parentNode.querySelector('.invalid-feedback');
            if (errorElement) {
                errorElement.textContent = '';
            }
        }
        
        clearFieldError(field) {
            field.classList.remove('is-invalid');
            const errorElement = field.parentNode.querySelector('.invalid-feedback');
            if (errorElement) {
                errorElement.textContent = '';
            }
        }
        
        showValidationErrors() {
            const firstInvalidField = this.form.querySelector('.is-invalid');
            if (firstInvalidField) {
                firstInvalidField.focus();
                firstInvalidField.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
            
            this.showToast('يرجى إصلاح الأخطاء في النموذج', 'error');
        }
        
        showLoadingState() {
            if (this.submitButton) {
                this.submitButton.disabled = true;
                this.submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الحفظ...';
            }
        }
        
        resetLoadingState() {
            if (this.submitButton) {
                this.submitButton.disabled = false;
                this.submitButton.innerHTML = this.originalButtonText;
            }
        }
        
        autoSave() {
            const formData = new FormData(this.form);
            const data = {};
            
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            
            // Store in localStorage
            const formId = this.form.id || 'form_' + Date.now();
            localStorage.setItem(`autosave_${formId}`, JSON.stringify(data));
            
            console.log(`${colors.green}✓${colors.reset} تم حفظ البيانات تلقائياً`);
        }
        
        loadAutoSave() {
            const formId = this.form.id || 'form_' + Date.now();
            const savedData = localStorage.getItem(`autosave_${formId}`);
            
            if (savedData) {
                try {
                    const data = JSON.parse(savedData);
                    Object.keys(data).forEach(key => {
                        const field = this.form.querySelector(`[name="${key}"]`);
                        if (field && !field.value) {
                            field.value = data[key];
                        }
                    });
                    
                    this.showToast('تم استعادة البيانات المحفوظة تلقائياً', 'info');
                } catch (e) {
                    console.error('Error loading autosave:', e);
                }
            }
        }
        
        confirmDelete() {
            return confirm('هل أنت متأكد من رغبتك في الحذف؟\nلا يمكن التراجع عن هذه العملية!');
        }
        
        showToast(message, type = 'info') {
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `
                <div class="toast-header">
                    <i class="fas fa-${this.getToastIcon(type)}"></i>
                    <strong class="me-auto">${this.getToastTitle(type)}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">${message}</div>
            `;
            
            // Add to page
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            toastContainer.appendChild(toast);
            
            // Show toast
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            
            // Remove after hidden
            toast.addEventListener('hidden.bs.toast', () => {
                toast.remove();
            });
        }
        
        getToastIcon(type) {
            const icons = {
                success: 'check-circle',
                error: 'exclamation-triangle',
                warning: 'exclamation-circle',
                info: 'info-circle'
            };
            return icons[type] || 'info-circle';
        }
        
        getToastTitle(type) {
            const titles = {
                success: 'نجح',
                error: 'خطأ',
                warning: 'تحذير',
                info: 'معلومات'
            };
            return titles[type] || 'معلومات';
        }
    }
    
    /**
     * Enhanced AJAX form handler
     */
    class EnhancedAjaxForm {
        constructor(formSelector, options = {}) {
            this.form = document.querySelector(formSelector);
            this.options = {
                successMessage: 'تم الحفظ بنجاح',
                errorMessage: 'حدث خطأ أثناء الحفظ',
                ...options
            };
            this.init();
        }
        
        init() {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSubmit();
            });
        }
        
        async handleSubmit() {
            try {
                const formData = new FormData(this.form);
                const response = await fetch(this.form.action, {
                    method: this.form.method,
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();
                
                if (response.ok && data.success) {
                    this.showSuccess(data.message || this.options.successMessage);
                    if (data.redirect) {
                        setTimeout(() => {
                            window.location.href = data.redirect;
                        }, 1500);
                    }
                } else {
                    this.showError(data.message || this.options.errorMessage);
                }
            } catch (error) {
                console.error('AJAX Error:', error);
                this.showError('حدث خطأ في الاتصال بالخادم');
            }
        }
        
        showSuccess(message) {
            this.showToast(message, 'success');
        }
        
        showError(message) {
            this.showToast(message, 'error');
        }
        
        showToast(message, type) {
            // Implementation similar to EnhancedFormValidator
            console.log(`${colors.green}✓${colors.reset} ${message}`);
        }
    }
    
    /**
     * Initialize enhanced forms when DOM is ready
     */
    document.addEventListener('DOMContentLoaded', function() {
        // Initialize enhanced validation for all forms
        const forms = document.querySelectorAll('form[data-enhanced="true"]');
        forms.forEach(form => {
            new EnhancedFormValidator(`#${form.id}`);
        });
        
        // Initialize AJAX forms
        const ajaxForms = document.querySelectorAll('form[data-ajax="true"]');
        ajaxForms.forEach(form => {
            new EnhancedAjaxForm(`#${form.id}`);
        });
        
        // Load autosaved data
        forms.forEach(form => {
            const validator = new EnhancedFormValidator(`#${form.id}`);
            validator.loadAutoSave();
        });
        
        console.log(`${colors.cyan}✓${colors.reset} تم تحميل تحسينات النماذج`);
    });
    
    // Export classes for global use
    window.EnhancedFormValidator = EnhancedFormValidator;
    window.EnhancedAjaxForm = EnhancedAjaxForm;
    
})(); 