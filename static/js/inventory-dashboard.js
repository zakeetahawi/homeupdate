/**
 * سكريبت لوحة تحكم المخزون الجديدة
 */

(function() {
    'use strict';
    
    // تهيئة عند تحميل الصفحة
    document.addEventListener('DOMContentLoaded', function() {
        // تهيئة الرسوم البيانية
        initCharts();
        
        // تهيئة جداول البيانات
        initDataTables();
        
        // تهيئة التنبيهات
        setupAlerts();
        
        // تهيئة بطاقات الأيقونات
        setupIconCards();
    });
    
    /**
     * تهيئة الرسوم البيانية
     */
    function initCharts() {
        // التحقق من وجود Chart.js
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js غير متوفر');
            return;
        }
        
        // رسم بياني للمخزون حسب الفئة
        const stockByCategoryChart = document.getElementById('stockByCategoryChart');
        if (stockByCategoryChart && typeof stockByCategoryData !== 'undefined') {
            new Chart(stockByCategoryChart, {
                type: 'doughnut',
                data: {
                    labels: stockByCategoryData.labels,
                    datasets: [{
                        data: stockByCategoryData.data,
                        backgroundColor: [
                            '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
                            '#5a5c69', '#6f42c1', '#fd7e14', '#20c9a6', '#858796'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            position: 'right',
                            rtl: true
                        },
                        tooltip: {
                            rtl: true,
                            callbacks: {
                                label: function(tooltipItem) {
                                    const dataset = tooltipItem.dataset;
                                    const total = dataset.data.reduce((acc, val) => acc + val, 0);
                                    const currentValue = dataset.data[tooltipItem.dataIndex];
                                    const percentage = Math.round((currentValue / total) * 100);
                                    return `${tooltipItem.label}: ${currentValue} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // رسم بياني لحركة المخزون
        const stockMovementChart = document.getElementById('stockMovementChart');
        if (stockMovementChart && typeof stockMovementData !== 'undefined') {
            new Chart(stockMovementChart, {
                type: 'line',
                data: {
                    labels: stockMovementData.labels,
                    datasets: [
                        {
                            label: 'وارد',
                            data: stockMovementData.inData,
                            borderColor: '#1cc88a',
                            backgroundColor: 'rgba(28, 200, 138, 0.1)',
                            borderWidth: 2,
                            pointBackgroundColor: '#1cc88a',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 4,
                            fill: true
                        },
                        {
                            label: 'صادر',
                            data: stockMovementData.outData,
                            borderColor: '#e74a3b',
                            backgroundColor: 'rgba(231, 74, 59, 0.1)',
                            borderWidth: 2,
                            pointBackgroundColor: '#e74a3b',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 4,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#858796'
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)',
                                zeroLineColor: 'rgba(0, 0, 0, 0.1)'
                            },
                            ticks: {
                                color: '#858796',
                                beginAtZero: true
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            rtl: true,
                            position: 'top'
                        },
                        tooltip: {
                            rtl: true,
                            mode: 'index',
                            intersect: false
                        }
                    }
                }
            });
        }
    }
    
    /**
     * تهيئة جداول البيانات
     */
    function initDataTables() {
        // التحقق من وجود DataTable
        if (typeof $.fn.DataTable === 'undefined') {
            console.warn('DataTables غير متوفر');
            return;
        }
        
        const dataTables = document.querySelectorAll('.datatable');
        
        if (dataTables.length > 0) {
            dataTables.forEach(function(table) {
                $(table).DataTable({
                    language: {
                        processing: "جارٍ التحميل...",
                        search: "بحث:",
                        lengthMenu: "عرض _MENU_ سجلات",
                        info: "عرض _START_ إلى _END_ من أصل _TOTAL_ سجل",
                        infoEmpty: "عرض 0 إلى 0 من أصل 0 سجل",
                        infoFiltered: "(منتقاة من مجموع _MAX_ سجل)",
                        infoPostFix: "",
                        loadingRecords: "جارٍ التحميل...",
                        zeroRecords: "لم يعثر على أية سجلات",
                        emptyTable: "لا توجد بيانات متاحة في الجدول",
                        paginate: {
                            first: "الأول",
                            previous: "السابق",
                            next: "التالي",
                            last: "الأخير"
                        },
                        aria: {
                            sortAscending: ": تفعيل لترتيب العمود تصاعدياً",
                            sortDescending: ": تفعيل لترتيب العمود تنازلياً"
                        }
                    },
                    responsive: true,
                    autoWidth: false,
                    dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
                         '<"row"<"col-sm-12"tr>>' +
                         '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
                    pageLength: 10,
                    lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "الكل"]]
                });
            });
        }
    }
    
    /**
     * إعداد التنبيهات
     */
    function setupAlerts() {
        // إخفاء التنبيهات بعد فترة
        const alerts = document.querySelectorAll('.alert-dismissible');
        
        if (alerts.length > 0) {
            alerts.forEach(function(alert) {
                setTimeout(function() {
                    $(alert).fadeOut('slow', function() {
                        $(this).remove();
                    });
                }, 5000);
            });
        }
    }
    
    /**
     * إعداد بطاقات الأيقونات
     */
    function setupIconCards() {
        const iconCards = document.querySelectorAll('.icon-card');
        
        if (iconCards.length > 0) {
            iconCards.forEach(function(card) {
                card.addEventListener('mouseenter', function() {
                    const icon = this.querySelector('.icon-card-icon i');
                    if (icon) {
                        icon.classList.add('fa-bounce');
                    }
                });
                
                card.addEventListener('mouseleave', function() {
                    const icon = this.querySelector('.icon-card-icon i');
                    if (icon) {
                        icon.classList.remove('fa-bounce');
                    }
                });
            });
        }
    }
    
    // تصدير الوظائف العامة
    window.InventoryDashboardNew = {
        refreshChart: function(chartId, newData) {
            const chart = Chart.getChart(chartId);
            if (chart) {
                chart.data = newData;
                chart.update();
            }
        }
    };
})();
