/**
 * البحث المحسن للعملاء - يحل مشكلة الوميض
 */
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('input[name="search"]');
    const searchForm = document.querySelector('form[method="get"]');
    let searchTimeout;
    let currentSearchValue = '';
    let isSearching = false;

    // إضافة مؤشر البحث
    function showSearchIndicator() {
        if (document.getElementById('search-indicator')) return; // تجنب التكرار
        
        const indicator = document.createElement('div');
        indicator.id = 'search-indicator';
        indicator.className = 'alert alert-info mt-2';
        indicator.innerHTML = '<i class="fas fa-search fa-spin me-2"></i>جاري البحث...';
        indicator.style.transition = 'opacity 0.3s ease';
        
        searchForm.appendChild(indicator);
    }

    // إزالة مؤشر البحث
    function hideSearchIndicator() {
        const indicator = document.getElementById('search-indicator');
        if (indicator) {
            indicator.style.opacity = '0';
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.remove();
                }
            }, 300);
        }
    }

    // عرض رسالة عدم وجود نتائج
    function showNoResults() {
        const existingResults = document.getElementById('search-results');
        if (existingResults) {
            existingResults.remove();
        }

        const noResultsHtml = `
            <div id="search-results" class="alert alert-warning mt-2" style="transition: opacity 0.3s ease;">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>لا توجد نتائج</h6>
                <p class="mb-0">لم يتم العثور على عملاء بهذا الرقم</p>
            </div>
        `;
        
        searchForm.insertAdjacentHTML('afterend', noResultsHtml);
        
        // إخفاء الرسالة تلقائياً بعد 3 ثوان
        setTimeout(() => {
            hideSearchResults();
        }, 3000);
    }

    // عرض نتائج البحث
    function showSearchResults(customers) {
        // إزالة النتائج السابقة ��سلاسة
        const existingResults = document.getElementById('search-results');
        if (existingResults) {
            existingResults.style.opacity = '0';
            setTimeout(() => {
                if (existingResults.parentNode) {
                    existingResults.remove();
                }
                displayResults(customers);
            }, 200);
        } else {
            displayResults(customers);
        }
    }

    function displayResults(customers) {
        let resultsHtml = '<div id="search-results" class="alert alert-success mt-2" style="opacity: 0; transition: opacity 0.3s ease;">';
        resultsHtml += '<h6><i class="fas fa-users me-2"></i>نتائج البحث السريع:</h6>';
        
        customers.forEach(customer => {
            const crossBranchBadge = customer.is_cross_branch ? 
                '<span class="badge bg-warning text-dark ms-1"><i class="fas fa-exchange-alt"></i> فرع آخر</span>' : '';
            
            resultsHtml += `
                <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                    <div>
                        <strong>${customer.name}</strong> ${crossBranchBadge}
                        <br>
                        <small class="text-muted">
                            <i class="fas fa-phone"></i> ${customer.phone}
                            <i class="fas fa-building ms-2"></i> ${customer.branch}
                        </small>
                    </div>
                    <div class="btn-group btn-group-sm">
                        <a href="${customer.url}" class="btn btn-info btn-sm">
                            <i class="fas fa-eye"></i> عرض
                        </a>
                        <a href="/orders/create/?customer_id=${customer.id}" class="btn btn-success btn-sm">
                            <i class="fas fa-plus"></i> طلب
                        </a>
                    </div>
                </div>
            `;
        });
        
        resultsHtml += '</div>';
        
        searchForm.insertAdjacentHTML('afterend', resultsHtml);
        
        // إظهار النتائج بسلاسة
        setTimeout(() => {
            const newResults = document.getElementById('search-results');
            if (newResults) {
                newResults.style.opacity = '1';
            }
        }, 50);
    }

    // إخفاء نتائج البحث
    function hideSearchResults() {
        const results = document.getElementById('search-results');
        if (results) {
            results.style.opacity = '0';
            setTimeout(() => {
                if (results.parentNode) {
                    results.remove();
                }
            }, 300);
        }
    }

    // البحث التلقائي عند كتابة رقم الهاتف
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const searchValue = this.value.trim();
            
            // تجنب البحث المتكرر لنفس القيمة
            if (searchValue === currentSearchValue) {
                return;
            }
            
            // التحقق من أن المدخل يشبه رقم هاتف
            const isPhoneNumber = /^[\d\+\-\s]+$/.test(searchValue) && searchValue.length >= 3;
            
            if (isPhoneNumber && searchValue.length >= 7) {
                currentSearchValue = searchValue;
                
                searchTimeout = setTimeout(() => {
                    // تجنب البحث المتعدد
                    if (isSearching) {
                        return;
                    }
                    
                    isSearching = true;
                    showSearchIndicator();
                    
                    // إرسال طلب AJAX للبحث
                    fetch(`/customers/api/find-by-phone/?phone=${encodeURIComponent(searchValue)}`)
                        .then(response => response.json())
                        .then(data => {
                            hideSearchIndicator();
                            isSearching = false;
                            
                            if (data.found && data.customers.length > 0) {
                                showSearchResults(data.customers);
                            } else {
                                showNoResults();
                            }
                        })
                        .catch(error => {
                            hideSearchIndicator();
                            isSearching = false;
                            console.error('خطأ في البحث:', error);
                            showNoResults();
                        });
                }, 1000); // زيادة الوقت إلى ثانية واحدة لتقليل الطلبات
            } else if (searchValue.length === 0) {
                // إخفاء النتائج فقط عند مسح الحقل تماماً
                currentSearchValue = '';
                hideSearchResults();
            }
        });

        // إخفاء النتائج عند فقدان التركيز
        searchInput.addEventListener('blur', function() {
            setTimeout(() => {
                hideSearchResults();
            }, 200); // تأخير قصير للسماح بالنقر على النتائج
        });

        // إظهار النتائج عند التركيز إذا كان هناك قيمة
        searchInput.addEventListener('focus', function() {
            const searchValue = this.value.trim();
            if (searchValue.length >= 7 && /^[\d\+\-\s]+$/.test(searchValue)) {
                // إعادة البحث عند التركيز
                this.dispatchEvent(new Event('input'));
            }
        });
    }

    // إخفاء النتائج عند النقر خارجها (مع استثناءات)
    document.addEventListener('click', function(e) {
        const searchResults = document.getElementById('search-results');
        if (searchResults && 
            !searchForm.contains(e.target) && 
            !searchResults.contains(e.target)) {
            hideSearchResults();
        }
    });

    // منع إخفاء النتائج عند النقر عليها
    document.addEventListener('click', function(e) {
        const searchResults = document.getElementById('search-results');
        if (searchResults && searchResults.contains(e.target)) {
            e.stopPropagation();
        }
    });
});