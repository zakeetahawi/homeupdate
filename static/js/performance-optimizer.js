/**
 * محسن أداء الواجهة الأمامية
 */

class PerformanceOptimizer {
    constructor() {
        this.observers = new Map();
        this.lazyImages = new Set();
        this.debounceTimers = new Map();
        this.init();
    }

    init() {
        this.setupLazyLoading();
        this.setupIntersectionObserver();
        this.setupDebouncing();
        this.setupPerformanceMonitoring();
        this.setupErrorHandling();
    }

    /**
     * إعداد التحميل الكسول للصور
     */
    setupLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        images.forEach(img => {
            this.lazyImages.add(img);
            img.classList.add('lazy-loading');
        });

        // إضافة placeholder للصور
        this.lazyImages.forEach(img => {
            if (!img.src) {
                img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2Y1ZjVmNSIvPjwvc3ZnPg==';
            }
        });
    }

    /**
     * إعداد مراقب التقاطع للتحميل الكسول
     */
    setupIntersectionObserver() {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    this.loadImage(img);
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.01
        });

        this.lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    }

    /**
     * تحميل الصورة
     */
    loadImage(img) {
        const dataSrc = img.getAttribute('data-src');
        if (!dataSrc) return;

        const newImg = new Image();
        newImg.onload = () => {
            img.src = dataSrc;
            img.classList.remove('lazy-loading');
            img.classList.add('lazy-loaded');
        };
        newImg.onerror = () => {
            img.classList.add('lazy-error');
            console.warn('فشل تحميل الصورة:', dataSrc);
        };
        newImg.src = dataSrc;
    }

    /**
     * إعداد debouncing للاستعلامات
     */
    setupDebouncing() {
        // debounce للبحث
        const searchInputs = document.querySelectorAll('input[type="search"], .search-input');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce((e) => {
                this.handleSearch(e.target.value);
            }, 300));
        });

        // debounce للفلاتر
        const filterInputs = document.querySelectorAll('.filter-input, select.filter-select');
        filterInputs.forEach(input => {
            input.addEventListener('change', this.debounce((e) => {
                this.handleFilter(e.target);
            }, 200));
        });
    }

    /**
     * دالة debounce
     */
    debounce(func, wait) {
        return (...args) => {
            const key = func.toString();
            clearTimeout(this.debounceTimers.get(key));
            this.debounceTimers.set(key, setTimeout(() => func.apply(this, args), wait));
        };
    }

    /**
     * معالجة البحث
     */
    handleSearch(query) {
        const searchUrl = new URL(window.location);
        searchUrl.searchParams.set('search', query);
        
        this.updateContent(searchUrl.toString());
    }

    /**
     * معالجة الفلترة
     */
    handleFilter(filterElement) {
        const filterUrl = new URL(window.location);
        const filterName = filterElement.name || filterElement.dataset.filter;
        const filterValue = filterElement.value;
        
        if (filterValue) {
            filterUrl.searchParams.set(filterName, filterValue);
        } else {
            filterUrl.searchParams.delete(filterName);
        }
        
        this.updateContent(filterUrl.toString());
    }

    /**
     * تحديث المحتوى بدون إعادة تحميل الصفحة
     */
    async updateContent(url) {
        try {
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const html = await response.text();
                this.updatePageContent(html);
                this.updateBrowserHistory(url);
            }
        } catch (error) {
            console.error('خطأ في تحديث المحتوى:', error);
        }
    }

    /**
     * تحديث محتوى الصفحة
     */
    updatePageContent(html) {
        const parser = new DOMParser();
        const newDoc = parser.parseFromString(html, 'text/html');
        
        // تحديث المحتوى الرئيسي
        const mainContent = document.querySelector('main, .main-content, #content');
        const newMainContent = newDoc.querySelector('main, .main-content, #content');
        
        if (mainContent && newMainContent) {
            mainContent.innerHTML = newMainContent.innerHTML;
        }

        // تحديث العنوان
        const newTitle = newDoc.querySelector('title');
        if (newTitle) {
            document.title = newTitle.textContent;
        }

        // إعادة تهيئة العناصر التفاعلية
        this.reinitializeInteractiveElements();
    }

    /**
     * تحديث تاريخ المتصفح
     */
    updateBrowserHistory(url) {
        window.history.pushState({}, '', url);
    }

    /**
     * إعادة تهيئة العناصر التفاعلية
     */
    reinitializeInteractiveElements() {
        // إعادة تهيئة tooltips
        const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                new bootstrap.Tooltip(tooltip);
            }
        });

        // إعادة تهيئة modals
        const modals = document.querySelectorAll('[data-toggle="modal"]');
        modals.forEach(modal => {
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                new bootstrap.Modal(modal);
            }
        });

        // إعادة تهيئة التحميل الكسول
        this.setupLazyLoading();
    }

    /**
     * إعداد مراقبة الأداء
     */
    setupPerformanceMonitoring() {
        // مراقبة وقت تحميل الصفحة
        window.addEventListener('load', () => {
            const loadTime = performance.now();
            this.sendPerformanceMetric('page_load_time', loadTime);
        });

        // مراقبة الأخطاء
        window.addEventListener('error', (event) => {
            this.sendPerformanceMetric('javascript_error', {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });

        // مراقبة الاستعلامات البطيئة
        this.monitorSlowRequests();
    }

    /**
     * مراقبة الطلبات البطيئة
     */
    monitorSlowRequests() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const startTime = performance.now();
            
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                if (duration > 1000) { // أكثر من ثانية
                    this.sendPerformanceMetric('slow_request', {
                        url: args[0],
                        duration: duration
                    });
                }
                
                return response;
            } catch (error) {
                this.sendPerformanceMetric('request_error', {
                    url: args[0],
                    error: error.message
                });
                throw error;
            }
        };
    }

    /**
     * إرسال مقاييس الأداء
     */
    sendPerformanceMetric(type, data) {
        fetch('/api/performance/metrics/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                type: type,
                data: data,
                timestamp: new Date().toISOString()
            })
        }).catch(error => {
            console.warn('فشل إرسال مقياس الأداء:', error);
        });
    }

    /**
     * الحصول على CSRF token
     */
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    }

    /**
     * إعداد معالجة الأخطاء
     */
    setupErrorHandling() {
        // معالجة أخطاء AJAX
        document.addEventListener('ajax:error', (event) => {
            const error = event.detail;
            this.showErrorMessage('حدث خطأ في الطلب. يرجى المحاولة مرة أخرى.');
            console.error('خطأ AJAX:', error);
        });

        // معالجة أخطاء التحميل
        window.addEventListener('unhandledrejection', (event) => {
            this.showErrorMessage('حدث خطأ غير متوقع. يرجى تحديث الصفحة.');
            console.error('خطأ غير معالج:', event.reason);
        });
    }

    /**
     * عرض رسالة خطأ
     */
    showErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container, .main-content');
        if (container) {
            container.insertBefore(errorDiv, container.firstChild);
        }
    }

    /**
     * تحسين الأداء للجداول
     */
    optimizeTables() {
        const tables = document.querySelectorAll('table');
        
        tables.forEach(table => {
            // إضافة virtual scrolling للجداول الكبيرة
            if (table.rows.length > 100) {
                this.setupVirtualScrolling(table);
            }
            
            // تحسين sorting
            const sortableHeaders = table.querySelectorAll('th[data-sort]');
            sortableHeaders.forEach(header => {
                header.addEventListener('click', () => {
                    this.handleTableSort(table, header);
                });
            });
        });
    }

    /**
     * إعداد virtual scrolling
     */
    setupVirtualScrolling(table) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const originalRows = Array.from(tbody.rows);
        const visibleRows = 20;
        let currentIndex = 0;

        const updateVisibleRows = () => {
            tbody.innerHTML = '';
            const endIndex = Math.min(currentIndex + visibleRows, originalRows.length);
            
            for (let i = currentIndex; i < endIndex; i++) {
                tbody.appendChild(originalRows[i].cloneNode(true));
            }
        };

        // إضافة scroll listener
        table.addEventListener('scroll', this.debounce(() => {
            const scrollTop = table.scrollTop;
            const rowHeight = 40; // ارتفاع الصف التقريبي
            currentIndex = Math.floor(scrollTop / rowHeight);
            updateVisibleRows();
        }, 16)); // 60fps

        updateVisibleRows();
    }

    /**
     * معالجة ترتيب الجدول
     */
    handleTableSort(table, header) {
        const column = header.dataset.sort;
        const currentOrder = header.dataset.order || 'asc';
        const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

        // تحديث headers
        table.querySelectorAll('th[data-sort]').forEach(th => {
            th.dataset.order = '';
            th.classList.remove('sort-asc', 'sort-desc');
        });

        header.dataset.order = newOrder;
        header.classList.add(`sort-${newOrder}`);

        // إرسال طلب للترتيب
        const url = new URL(window.location);
        url.searchParams.set('sort', column);
        url.searchParams.set('order', newOrder);
        
        this.updateContent(url.toString());
    }
}

// تهيئة محسن الأداء عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    window.performanceOptimizer = new PerformanceOptimizer();
});

// تهيئة محسن الأداء للصفحات المحملة عبر AJAX
document.addEventListener('contentLoaded', () => {
    if (window.performanceOptimizer) {
        window.performanceOptimizer.reinitializeInteractiveElements();
    }
}); 