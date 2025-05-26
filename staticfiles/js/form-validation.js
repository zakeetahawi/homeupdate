/**
 * تحسين التحقق من صحة النماذج
 * يوفر هذا الملف وظائف لتحسين التحقق من صحة النماذج في جانب العميل
 */

(function() {
    'use strict';
    
    /**
     * إضافة التحقق من صحة النماذج لجميع النماذج التي تحتوي على فئة needs-validation
     */
    document.addEventListener('DOMContentLoaded', function() {
        // الحصول على جميع النماذج التي تحتاج إلى تحقق
        var forms = document.querySelectorAll('.needs-validation');
        
        // التكرار على كل نموذج وإضافة مستمع للحدث submit
        Array.prototype.slice.call(forms).forEach(function(form) {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                    
                    // إظهار رسالة خطأ عامة
                    showFormError(form, 'يرجى التحقق من صحة البيانات المدخلة وإصلاح الأخطاء المشار إليها.');
                    
                    // التمرير إلى أول حقل غير صالح
                    scrollToFirstInvalidField(form);
                }
                
                form.classList.add('was-validated');
            }, false);
            
            // إضافة مستمعي أحداث للحقول للتحقق من صحتها أثناء الكتابة
            addFieldValidationListeners(form);
        });
    });
    
    /**
     * إضافة مستمعي أحداث للحقول للتحقق من صحتها أثناء الكتابة
     * @param {HTMLFormElement} form - النموذج المراد إضافة مستمعي الأحداث له
     */
    function addFieldValidationListeners(form) {
        var inputs = form.querySelectorAll('input, select, textarea');
        
        Array.prototype.slice.call(inputs).forEach(function(input) {
            // التحقق من صحة الحقل عند تغيير قيمته
            input.addEventListener('change', function() {
                validateField(input);
            });
            
            // التحقق من صحة الحقل عند الخروج منه
            input.addEventListener('blur', function() {
                validateField(input);
            });
            
            // إزالة رسائل الخطأ عند الكتابة
            input.addEventListener('input', function() {
                if (input.classList.contains('is-invalid')) {
                    input.classList.remove('is-invalid');
                    
                    // إزالة رسالة الخطأ المخصصة إذا كانت موجودة
                    var errorElement = input.parentNode.querySelector('.invalid-feedback');
                    if (errorElement) {
                        errorElement.textContent = '';
                    }
                }
            });
        });
    }
    
    /**
     * التحقق من صحة حقل
     * @param {HTMLElement} field - الحقل المراد التحقق من صحته
     */
    function validateField(field) {
        // التحقق من صحة الحقل
        var isValid = field.checkValidity();
        
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            
            // إضافة رسالة خطأ مخصصة
            addCustomErrorMessage(field);
        }
        
        return isValid;
    }
    
    /**
     * إضافة رسالة خطأ مخصصة للحقل
     * @param {HTMLElement} field - الحقل المراد إضافة رسالة خطأ له
     */
    function addCustomErrorMessage(field) {
        var errorMessage = '';
        
        // تحديد نوع الخطأ وإنشاء رسالة مناسبة
        if (field.validity.valueMissing) {
            errorMessage = 'هذا الحقل مطلوب';
        } else if (field.validity.typeMismatch) {
            if (field.type === 'email') {
                errorMessage = 'يرجى إدخال عنوان بريد إلكتروني صالح';
            } else if (field.type === 'url') {
                errorMessage = 'يرجى إدخال رابط صالح';
            } else {
                errorMessage = 'القيمة المدخلة غير متوافقة مع النوع المطلوب';
            }
        } else if (field.validity.tooShort) {
            errorMessage = `يجب أن يحتوي هذا الحقل على ${field.minLength} أحرف على الأقل (تم إدخال ${field.value.length} أحرف)`;
        } else if (field.validity.tooLong) {
            errorMessage = `يجب أن يحتوي هذا الحقل على ${field.maxLength} أحرف كحد أقصى (تم إدخال ${field.value.length} أحرف)`;
        } else if (field.validity.rangeUnderflow) {
            errorMessage = `يجب أن تكون القيمة ${field.min} أو أكبر`;
        } else if (field.validity.rangeOverflow) {
            errorMessage = `يجب أن تكون القيمة ${field.max} أو أقل`;
        } else if (field.validity.patternMismatch) {
            errorMessage = 'القيمة المدخلة لا تتطابق مع النمط المطلوب';
        } else {
            errorMessage = 'القيمة المدخلة غير صالحة';
        }
        
        // إضافة رسالة الخطأ إلى العنصر المناسب
        var errorElement = field.parentNode.querySelector('.invalid-feedback');
        
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            field.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = errorMessage;
    }
    
    /**
     * إظهار رسالة خطأ عامة للنموذج
     * @param {HTMLFormElement} form - النموذج المراد إظهار رسالة خطأ له
     * @param {string} message - رسالة الخطأ
     */
    function showFormError(form, message) {
        var errorContainer = form.querySelector('.form-error-container');
        
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'alert alert-danger form-error-container mt-3';
            form.prepend(errorContainer);
        }
        
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
    
    /**
     * التمرير إلى أول حقل غير صالح في النموذج
     * @param {HTMLFormElement} form - النموذج المراد التمرير فيه
     */
    function scrollToFirstInvalidField(form) {
        var firstInvalidField = form.querySelector(':invalid');
        
        if (firstInvalidField) {
            firstInvalidField.focus();
            firstInvalidField.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    }
    
    /**
     * تصدير الوظائف العامة
     */
    window.FormValidator = {
        validateField: validateField,
        validateForm: function(form) {
            var isValid = form.checkValidity();
            
            if (!isValid) {
                form.classList.add('was-validated');
                scrollToFirstInvalidField(form);
            }
            
            return isValid;
        }
    };
})();
