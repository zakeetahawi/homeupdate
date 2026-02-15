/**
 * معالج CSRF تلقائي لتحسين تجربة المستخدم
 */

(function() {
    'use strict';
    
    // إعدادات CSRF
    const CSRF_CONFIG = {
        tokenName: 'csrfmiddlewaretoken',
        headerName: 'X-CSRFToken',
        cookieName: 'elkhawaga_csrftoken',  // اسم الكوكيز المخصص في Django
        refreshUrl: '/csrf-token/',
        maxRetries: 3,
        retryDelay: 1000
    };
    
    // متغيرات عامة
    let csrfToken = null;
    let retryCount = 0;
    
    /**
     * جلب CSRF token من الكوكيز
     */
    function getCsrfTokenFromCookie() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === CSRF_CONFIG.cookieName) {
                return decodeURIComponent(value);
            }
        }
        return null;
    }
    
    /**
     * جلب CSRF token من meta tag
     */
    function getCsrfTokenFromMeta() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : null;
    }
    
    /**
     * جلب CSRF token من النموذج
     */
    function getCsrfTokenFromForm() {
        const tokenInput = document.querySelector(`input[name="${CSRF_CONFIG.tokenName}"]`);
        return tokenInput ? tokenInput.value : null;
    }
    
    /**
     * الحصول على CSRF token من أي مصدر متاح
     */
    function getCurrentCsrfToken() {
        return getCsrfTokenFromCookie() || 
               getCsrfTokenFromMeta() || 
               getCsrfTokenFromForm() || 
               csrfToken;
    }
    
    /**
     * تحديث CSRF token في جميع النماذج
     */
    function updateCsrfTokenInForms(newToken) {
        const tokenInputs = document.querySelectorAll(`input[name="${CSRF_CONFIG.tokenName}"]`);
        tokenInputs.forEach(input => {
            input.value = newToken;
        });
        
        // تحديث meta tag إذا وجد
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            metaTag.setAttribute('content', newToken);
        }
        
        csrfToken = newToken;
        // console.log('✅ تم تحديث CSRF token في جميع النماذج');
    }
    
    /**
     * جلب CSRF token جديد من الخادم
     */
    async function refreshCsrfToken() {
        try {
            const response = await fetch(CSRF_CONFIG.refreshUrl, {
                method: 'GET',
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.csrf_token) {
                    updateCsrfTokenInForms(data.csrf_token);
                    retryCount = 0; // إعادة تعيين عداد المحاولات
                    return data.csrf_token;
                }
            }
            
            throw new Error('فشل في جلب CSRF token جديد');
            
        } catch (error) {
            console.error('❌ خطأ في تحديث CSRF token:', error);
            return null;
        }
    }
    
    /**
     * معالج أخطاء CSRF
     */
    function handleCsrfError(error, originalRequest) {
        // console.warn('⚠️ خطأ CSRF detected:', error);
        
        if (retryCount < CSRF_CONFIG.maxRetries) {
            retryCount++;
            // console.log(`🔄 محاولة ${retryCount} من ${CSRF_CONFIG.maxRetries} لإعادة المحاولة...`);
            
            return refreshCsrfToken().then(newToken => {
                if (newToken && originalRequest) {
                    // إعادة المحاولة مع الـ token الجديد
                    setTimeout(() => {
                        if (originalRequest.retry) {
                            originalRequest.retry(newToken);
                        }
                    }, CSRF_CONFIG.retryDelay);
                    return true;
                }
                return false;
            });
        } else {
            // عرض رسالة للمستخدم
            showCsrfErrorMessage();
            return Promise.resolve(false);
        }
    }
    
    /**
     * عرض رسالة خطأ CSRF للمستخدم
     */
    function showCsrfErrorMessage() {
        // إنشاء modal أو alert
        if (typeof Swal !== 'undefined') {
            // استخدام SweetAlert إذا كان متاحاً
            Swal.fire({
                icon: 'warning',
                title: 'انتهت صلاحية الجلسة',
                text: 'انتهت صلاحية رمز الحماية. سيتم إعادة تحميل الصفحة.',
                confirmButtonText: 'إعادة تحميل',
                allowOutsideClick: false
            }).then(() => {
                window.location.reload();
            });
        } else {
            // استخدام alert عادي
            if (confirm('انتهت صلاحية رمز الحماية. هل تريد إعادة تحميل الصفحة؟')) {
                window.location.reload();
            }
        }
    }
    
    /**
     * إعداد CSRF للطلبات AJAX
     */
    function setupAjaxCsrf() {
        // jQuery AJAX setup
        if (typeof $ !== 'undefined' && $.ajaxSetup) {
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    if (!this.crossDomain && !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                        const token = getCurrentCsrfToken();
                        if (token) {
                            xhr.setRequestHeader(CSRF_CONFIG.headerName, token);
                        }
                    }
                },
                error: function(xhr, status, error) {
                    if (xhr.status === 403 && xhr.responseJSON && xhr.responseJSON.code === 'CSRF_FAILURE') {
                        handleCsrfError(error, {
                            retry: (newToken) => {
                                // إعادة المحاولة مع الـ token الجديد
                                this.headers = this.headers || {};
                                this.headers[CSRF_CONFIG.headerName] = newToken;
                                $.ajax(this);
                            }
                        });
                    }
                }
            });
        }
        
        // Fetch API interceptor
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            // إضافة CSRF token للطلبات POST/PUT/DELETE
            if (options.method && !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.method)) {
                const token = getCurrentCsrfToken();
                if (token) {
                    options.headers = options.headers || {};
                    options.headers[CSRF_CONFIG.headerName] = token;
                }
            }
            
            return originalFetch(url, options).catch(error => {
                if (error.status === 403) {
                    return handleCsrfError(error, {
                        retry: (newToken) => {
                            options.headers = options.headers || {};
                            options.headers[CSRF_CONFIG.headerName] = newToken;
                            return originalFetch(url, options);
                        }
                    });
                }
                throw error;
            });
        };
    }
    
    /**
     * مراقبة النماذج وإضافة معالجات CSRF
     */
    function setupFormCsrf() {
        document.addEventListener('submit', function(event) {
            const form = event.target;
            if (form.method && form.method.toLowerCase() === 'post') {
                const tokenInput = form.querySelector(`input[name="${CSRF_CONFIG.tokenName}"]`);
                if (!tokenInput) {
                    // console.warn('⚠️ نموذج بدون CSRF token:', form);
                    
                    // إضافة CSRF token تلقائياً
                    const token = getCurrentCsrfToken();
                    if (token) {
                        const hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.name = CSRF_CONFIG.tokenName;
                        hiddenInput.value = token;
                        form.appendChild(hiddenInput);
                        // console.log('✅ تم إضافة CSRF token تلقائياً للنموذج');
                    }
                }
            }
        });
    }
    
    /**
     * تحديث دوري لـ CSRF token
     */
    function setupPeriodicRefresh() {
        // تحديث كل 30 دقيقة
        setInterval(() => {
            refreshCsrfToken().then(newToken => {
                if (newToken) {
                    // console.log('🔄 تم تحديث CSRF token دورياً');
                }
            });
        }, 30 * 60 * 1000); // 30 دقيقة
    }
    
    /**
     * تهيئة معالج CSRF
     */
    function initCsrfHandler() {
        // الحصول على الـ token الحالي
        csrfToken = getCurrentCsrfToken();

        if (!csrfToken) {
            // console.warn('⚠️ لم يتم العثور على CSRF token');
            refreshCsrfToken();
        }

        // إعداد المعالجات
        setupAjaxCsrf();
        setupFormCsrf();
        setupPeriodicRefresh();
    }
    
    /**
     * API عام للاستخدام الخارجي
     */
    window.CSRFHandler = {
        getToken: getCurrentCsrfToken,
        refreshToken: refreshCsrfToken,
        updateForms: updateCsrfTokenInForms,
        handleError: handleCsrfError
    };
    
    // تهيئة تلقائية عند تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCsrfHandler);
    } else {
        initCsrfHandler();
    }
    
})();
