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
                setTimeout(() => {
                    this.style.borderColor = '#e9ecef';
                }, 1000);
            });
        });
        
        // إضافة تأثير للزر
        const submitBtn = filterForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.addEventListener('click', function() {
                this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>جاري التطبيق...';
                this.disabled = true;
                
                setTimeout(() => {
                    this.innerHTML = '<i class="fas fa-search me-2"></i>تطبيق الفلاتر';
                    this.disabled = false;
                }, 2000);
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