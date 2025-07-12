/**
 * AJAX Forms Handler
 * تحسين تجربة المستخدم في النماذج باستخدام AJAX
 */

class AjaxFormHandler {
    constructor() {
        this.csrfToken = this.getCSRFToken();
        this.initializeEventListeners();
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name=csrf-token]')?.content;
    }

    initializeEventListeners() {
        // Order form validation
        this.setupOrderFormValidation();
        
        // Payment form validation
        this.setupPaymentFormValidation();
        
        // Customer info loading
        this.setupCustomerInfoLoading();
        
        // Product info loading
        this.setupProductInfoLoading();
        
        // Real-time validation
        this.setupRealTimeValidation();
    }

    setupOrderFormValidation() {
        const orderForm = document.getElementById('order-form');
        if (!orderForm) return;

        const submitBtn = orderForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.validateOrderForm(orderForm);
            });
        }
    }

    setupPaymentFormValidation() {
        const paymentForm = document.getElementById('payment-form');
        if (!paymentForm) return;

        const submitBtn = paymentForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.validatePaymentForm(paymentForm);
            });
        }
    }

    setupCustomerInfoLoading() {
        const customerSelect = document.getElementById('id_customer');
        if (!customerSelect) return;

        customerSelect.addEventListener('change', (e) => {
            const customerId = e.target.value;
            if (customerId) {
                this.loadCustomerInfo(customerId);
            }
        });
    }

    setupProductInfoLoading() {
        const productSelects = document.querySelectorAll('.product-select');
        productSelects.forEach(select => {
            select.addEventListener('change', (e) => {
                const productId = e.target.value;
                if (productId) {
                    this.loadProductInfo(productId, e.target);
                }
            });
        });
    }

    setupRealTimeValidation() {
        // Real-time validation for required fields
        const requiredFields = document.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', () => {
                this.validateField(field);
            });
        });
    }

    async validateOrderForm(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }

        try {
            const response = await fetch('/orders/ajax/validate-order/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.valid) {
                this.showSuccess('البيانات صحيحة، جاري الإرسال...');
                form.submit();
            } else {
                this.showErrors(result.errors);
            }
        } catch (error) {
            this.showError('حدث خطأ في التحقق من البيانات');
        }
    }

    async validatePaymentForm(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }

        // Add order ID if available
        const orderId = form.dataset.orderId;
        if (orderId) {
            data.order_id = orderId;
        }

        try {
            const response = await fetch('/orders/ajax/validate-payment/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.valid) {
                this.showSuccess('البيانات صحيحة، جاري الإرسال...');
                form.submit();
            } else {
                this.showErrors(result.errors);
            }
        } catch (error) {
            this.showError('حدث خطأ في التحقق من البيانات');
        }
    }

    async loadCustomerInfo(customerId) {
        try {
            const response = await fetch(`/orders/ajax/customer/${customerId}/info/`);
            const customer = await response.json();
            
            this.displayCustomerInfo(customer);
        } catch (error) {
            console.error('Error loading customer info:', error);
        }
    }

    async loadProductInfo(productId, selectElement) {
        try {
            const response = await fetch(`/orders/ajax/product/${productId}/info/`);
            const product = await response.json();
            
            this.displayProductInfo(product, selectElement);
        } catch (error) {
            console.error('Error loading product info:', error);
        }
    }

    displayCustomerInfo(customer) {
        // Create or update customer info display
        let infoContainer = document.getElementById('customer-info');
        if (!infoContainer) {
            infoContainer = document.createElement('div');
            infoContainer.id = 'customer-info';
            infoContainer.className = 'alert alert-info mt-3';
            const customerSelect = document.getElementById('id_customer');
            customerSelect.parentNode.insertBefore(infoContainer, customerSelect.nextSibling);
        }

        infoContainer.innerHTML = `
            <h6>معلومات العميل:</h6>
            <p><strong>الاسم:</strong> ${customer.name}</p>
            <p><strong>الهاتف:</strong> ${customer.phone || 'غير محدد'}</p>
            <p><strong>البريد الإلكتروني:</strong> ${customer.email || 'غير محدد'}</p>
            <p><strong>العنوان:</strong> ${customer.address || 'غير محدد'}</p>
            <p><strong>الفئة:</strong> ${customer.category}</p>
            <p><strong>عدد الطلبات:</strong> ${customer.total_orders}</p>
            <p><strong>إجمالي المبيعات:</strong> ${customer.total_amount} ج.م</p>
        `;
    }

    displayProductInfo(product, selectElement) {
        // Find the closest form row to display product info
        const formRow = selectElement.closest('.form-row') || selectElement.parentNode;
        let infoContainer = formRow.querySelector('.product-info');
        
        if (!infoContainer) {
            infoContainer = document.createElement('div');
            infoContainer.className = 'product-info alert alert-info mt-2';
            formRow.appendChild(infoContainer);
        }

        infoContainer.innerHTML = `
            <small>
                <strong>المنتج:</strong> ${product.name} (${product.code})<br>
                <strong>السعر:</strong> ${product.price} ج.م<br>
                <strong>الفئة:</strong> ${product.category}<br>
                <strong>المخزون الحالي:</strong> ${product.current_stock}<br>
                <strong>الحد الأدنى:</strong> ${product.minimum_stock}
            </small>
        `;
    }

    validateField(field) {
        const value = field.value.trim();
        const isRequired = field.hasAttribute('required');
        
        if (isRequired && !value) {
            this.showFieldError(field, 'هذا الحقل مطلوب');
            return false;
        }
        
        this.clearFieldError(field);
        return true;
    }

    showFieldError(field, message) {
        this.clearFieldError(field);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        field.classList.add('is-invalid');
        field.parentNode.appendChild(errorDiv);
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    showErrors(errors) {
        // Clear previous errors
        this.clearAllErrors();
        
        // Show new errors
        Object.keys(errors).forEach(fieldName => {
            const field = document.getElementById(`id_${fieldName}`);
            if (field) {
                this.showFieldError(field, errors[fieldName]);
            } else {
                this.showGeneralError(errors[fieldName]);
            }
        });
    }

    showGeneralError(message) {
        let alertContainer = document.getElementById('general-error');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'general-error';
            alertContainer.className = 'alert alert-danger mt-3';
            const form = document.querySelector('form');
            form.insertBefore(alertContainer, form.firstChild);
        }
        
        alertContainer.textContent = message;
        alertContainer.style.display = 'block';
    }

    showSuccess(message) {
        let alertContainer = document.getElementById('success-message');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'success-message';
            alertContainer.className = 'alert alert-success mt-3';
            const form = document.querySelector('form');
            form.insertBefore(alertContainer, form.firstChild);
        }
        
        alertContainer.textContent = message;
        alertContainer.style.display = 'block';
        
        // Hide after 3 seconds
        setTimeout(() => {
            alertContainer.style.display = 'none';
        }, 3000);
    }

    showError(message) {
        this.showGeneralError(message);
    }

    clearAllErrors() {
        // Clear field errors
        document.querySelectorAll('.is-invalid').forEach(field => {
            this.clearFieldError(field);
        });
        
        // Clear general errors
        const generalError = document.getElementById('general-error');
        if (generalError) {
            generalError.style.display = 'none';
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AjaxFormHandler();
}); 