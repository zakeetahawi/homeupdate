// Admin Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // تهيئة الرسوم البيانية
    initializeCharts();
    
    // إضافة تأثيرات تفاعلية
    addInteractiveEffects();
    
    // إعداد الفلاتر
    setupFilters();
    
    // إضافة تحديث تلقائي
    setupAutoRefresh();
});

function initializeCharts() {
    // تهيئة الرسوم البيانية إذا كانت موجودة
    const ordersChart = document.getElementById('ordersChart');
    const customersChart = document.getElementById('customersChart');
    
    if (ordersChart) {
        setupOrdersChart();
    }
    
    if (customersChart) {
        setupCustomersChart();
    }
}

function setupOrdersChart() {
    const ctx = document.getElementById('ordersChart').getContext('2d');
    
    // الحصول على البيانات من الصفحة
    const chartData = window.ordersChartData || [];
    const months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 
                   'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: 'الطلبات',
                data: chartData,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 14,
                            family: 'Cairo, sans-serif'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#667eea',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        font: {
                            family: 'Cairo, sans-serif'
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        font: {
                            family: 'Cairo, sans-serif'
                        }
                    }
                }
            }
        }
    });
}

function setupCustomersChart() {
    const ctx = document.getElementById('customersChart').getContext('2d');
    
    // الحصول على البيانات من الصفحة
    const chartData = window.customersChartData || [];
    const months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 
                   'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: 'العملاء',
                data: chartData,
                borderColor: '#f093fb',
                backgroundColor: 'rgba(240, 147, 251, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#f093fb',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 14,
                            family: 'Cairo, sans-serif'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#f093fb',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        font: {
                            family: 'Cairo, sans-serif'
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        font: {
                            family: 'Cairo, sans-serif'
                        }
                    }
                }
            }
        }
    });
}

function addInteractiveEffects() {
    // إضافة تأثيرات للبطاقات
    const cards = document.querySelectorAll('.dashboard-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // إضافة تأثيرات للعناصر المترية
    const metricItems = document.querySelectorAll('.metric-item');
    metricItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
            this.style.boxShadow = '0 6px 25px rgba(0, 0, 0, 0.15)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
        });
    });
}

function setupFilters() {
    const filterForm = document.querySelector('.filter-form');
    if (filterForm) {
        // إضافة تأثيرات للفلاتر
        const selects = filterForm.querySelectorAll('select');
        selects.forEach(select => {
            select.addEventListener('change', function() {
                // إضافة تأثير بصري عند التغيير
                this.style.borderColor = '#667eea';
                this.style.boxShadow = '0 0 0 0.2rem rgba(102, 126, 234, 0.25)';
                
                setTimeout(() => {
                    this.style.borderColor = '#e9ecef';
                    this.style.boxShadow = 'none';
                }, 1000);
                
                // تطبيق الفلاتر تلقائياً إذا كان الخيار "السنة الكاملة"
                if (this.name === 'month' && this.value === 'year') {
                    console.log('تم اختيار السنة الكاملة - تطبيق الفلاتر تلقائياً');
                    filterForm.submit();
                }
                
                // تطبيق الفلاتر تلقائياً عند تغيير الفرع
                if (this.name === 'branch') {
                    console.log('تم تغيير الفرع - تطبيق الفلاتر تلقائياً');
                    filterForm.submit();
                }
                
                // تطبيق الفلاتر تلقائياً عند تغيير السنة
                if (this.name === 'year') {
                    console.log('تم تغيير السنة - تطبيق الفلاتر تلقائياً');
                    filterForm.submit();
                }
            });
        });
        
        // إضافة تأثير للزر
        const submitBtn = filterForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.addEventListener('click', function(e) {
                e.preventDefault();
                
                // إظهار حالة التحميل
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>جاري التطبيق...';
                this.disabled = true;
                this.style.opacity = '0.7';
                
                // إرسال النموذج
                setTimeout(() => {
                    filterForm.submit();
                }, 500);
            });
        }
        
        // إضافة وظيفة لإخفاء/إظهار فلاتر المقارنة حسب النوع
        const comparisonTypeSelect = document.getElementById('comparison-type-select');
        const comparisonMonthGroup = document.getElementById('comparison-month-group');
        
        if (comparisonTypeSelect && comparisonMonthGroup) {
            comparisonTypeSelect.addEventListener('change', function() {
                if (this.value === 'year') {
                    comparisonMonthGroup.style.display = 'none';
                } else {
                    comparisonMonthGroup.style.display = 'block';
                }
            });
            
            // تطبيق الإعداد الأولي
            if (comparisonTypeSelect.value === 'year') {
                comparisonMonthGroup.style.display = 'none';
            }
        }
        
        // إضافة وظيفة لتطبيق الفلاتر عند تغيير الفرع
        const branchSelect = filterForm.querySelector('select[name="branch"]');
        if (branchSelect) {
            branchSelect.addEventListener('change', function() {
                console.log('تم تغيير الفرع إلى:', this.value);
                // يمكن إضافة منطق إضافي هنا إذا لزم الأمر
            });
        }
        
        // إضافة وظيفة لتطبيق الفلاتر عند تغيير السنة
        const yearSelect = filterForm.querySelector('select[name="year"]');
        if (yearSelect) {
            yearSelect.addEventListener('change', function() {
                console.log('تم تغيير السنة إلى:', this.value);
                // يمكن إضافة منطق إضافي هنا إذا لزم الأمر
            });
        }
        
        // Auto-submit when period changes to "year"
        const periodSelect = document.getElementById('period-select');
        if (periodSelect) {
            periodSelect.addEventListener('change', function() {
                if (this.value === 'year') {
                    console.log('Auto-submitting filters for year selection');
                    filterForm.submit();
                }
            });
            
            // تأكد من أن القيمة الافتراضية هي "السنة الكاملة"
            if (!periodSelect.value || periodSelect.value === '') {
                periodSelect.value = 'year';
            }
        }
        
        // إضافة وظيفة لإظهار رسالة تأكيد عند تطبيق الفلاتر
        const form = document.getElementById('dashboard-filters');
        if (form) {
            form.addEventListener('submit', function() {
                // إظهار رسالة تأكيد
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: 'جاري تطبيق الفلاتر...',
                        text: 'يرجى الانتظار',
                        icon: 'info',
                        timer: 1500,
                        timerProgressBar: true,
                        showConfirmButton: false,
                        position: 'top-end',
                        toast: true
                    });
                }
            });
        }
    }
}

function setupAutoRefresh() {
    // تحديث تلقائي كل 5 دقائق
    setInterval(() => {
        // تحديث الإحصائيات فقط إذا كانت الصفحة نشطة
        if (!document.hidden) {
            refreshStatistics();
        }
    }, 5 * 60 * 1000); // 5 دقائق
}

function refreshStatistics() {
    // إرسال طلب AJAX لتحديث الإحصائيات
    const currentUrl = new URL(window.location);
    
    fetch(currentUrl.pathname + currentUrl.search)
        .then(response => response.text())
        .then(html => {
            // تحديث البطاقات الإحصائية فقط
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // تحديث أرقام الإحصائيات
            updateStatNumbers(doc);
        })
        .catch(error => {
            console.log('خطأ في تحديث الإحصائيات:', error);
        });
}

function updateStatNumbers(newDoc) {
    // تحديث أرقام الإحصائيات في البطاقات
    const statNumbers = document.querySelectorAll('.stat-number');
    const newStatNumbers = newDoc.querySelectorAll('.stat-number');
    
    statNumbers.forEach((stat, index) => {
        if (newStatNumbers[index]) {
            const newValue = newStatNumbers[index].textContent;
            if (stat.textContent !== newValue) {
                // إضافة تأثير انتقالي
                stat.style.transition = 'all 0.3s ease';
                stat.style.color = '#28a745';
                stat.textContent = newValue;
                
                setTimeout(() => {
                    stat.style.color = '';
                }, 1000);
            }
        }
    });
}

// وظائف مساعدة
function formatNumber(num) {
    return new Intl.NumberFormat('ar-EG').format(num);
}

function showNotification(message, type = 'info') {
    // إظهار إشعار للمستخدم
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // إزالة الإشعار تلقائياً بعد 5 ثوان
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// تصدير الوظائف للاستخدام العام
window.AdminDashboard = {
    refreshStatistics,
    showNotification,
    formatNumber
}; 