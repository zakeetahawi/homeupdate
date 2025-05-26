/**
 * سكريبت لوحة تحكم المخزون
 */

(function() {
    'use strict';
    
    // تهيئة عند تحميل الصفحة
    document.addEventListener('DOMContentLoaded', function() {
        // زر تبديل القائمة الجانبية للشاشات الصغيرة
        setupSidebarToggle();
        
        // تهيئة الرسوم البيانية
        initCharts();
        
        // تهيئة جداول البيانات
        initDataTables();
        
        // تهيئة التنبيهات
        setupAlerts();
    });
    
    /**
     * إعداد زر تبديل القائمة الجانبية
     */
    function setupSidebarToggle() {
        const sidebarToggleBtn = document.getElementById('sidebar-toggle');
        const sidebar = document.querySelector('.inventory-sidebar');
        
        if (sidebarToggleBtn && sidebar) {
            sidebarToggleBtn.addEventListener('click', function() {
                sidebar.classList.toggle('active');
            });
        }
        
        // إغلاق القائمة الجانبية عند النقر خارجها في الشاشات الصغيرة
        document.addEventListener('click', function(event) {
            if (window.innerWidth <= 768 && 
                sidebar && 
                sidebar.classList.contains('active') && 
                !sidebar.contains(event.target) && 
                event.target !== sidebarToggleBtn) {
                sidebar.classList.remove('active');
            }
        });
    }
    
    /**
     * تهيئة الرسوم البيانية
     */
    function initCharts() {
        // رسم بياني للمخزون حسب الفئة
        const stockByCategoryChart = document.getElementById('stockByCategoryChart');
        if (stockByCategoryChart) {
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
                    cutoutPercentage: 70,
                    legend: {
                        position: 'right',
                        rtl: true
                    },
                    tooltips: {
                        rtl: true,
                        callbacks: {
                            label: function(tooltipItem, data) {
                                const dataset = data.datasets[tooltipItem.datasetIndex];
                                const total = dataset.data.reduce((acc, val) => acc + val, 0);
                                const currentValue = dataset.data[tooltipItem.index];
                                const percentage = Math.round((currentValue / total) * 100);
                                return `${data.labels[tooltipItem.index]}: ${currentValue} (${percentage}%)`;
                            }
                        }
                    }
                }
            });
        }
        
        // رسم بياني لحركة المخزون
        const stockMovementChart = document.getElementById('stockMovementChart');
        if (stockMovementChart) {
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
                        xAxes: [{
                            gridLines: {
                                display: false
                            },
                            ticks: {
                                fontColor: '#858796'
                            }
                        }],
                        yAxes: [{
                            gridLines: {
                                color: 'rgba(0, 0, 0, 0.05)',
                                zeroLineColor: 'rgba(0, 0, 0, 0.1)'
                            },
                            ticks: {
                                fontColor: '#858796',
                                beginAtZero: true
                            }
                        }]
                    },
                    legend: {
                        rtl: true,
                        position: 'top'
                    },
                    tooltips: {
                        rtl: true,
                        mode: 'index',
                        intersect: false
                    }
                }
            });
        }
    }
    
    /**
     * تهيئة جداول البيانات
     */
    function initDataTables() {
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
    
    // تصدير الوظائف العامة
    window.InventoryDashboard = {
        refreshChart: function(chartId, newData) {
            const chart = Chart.getChart(chartId);
            if (chart) {
                chart.data = newData;
                chart.update();
            }
        },
        
        toggleSidebar: function() {
            const sidebar = document.querySelector('.inventory-sidebar');
            if (sidebar) {
                sidebar.classList.toggle('active');
            }
        }
    };
})();
