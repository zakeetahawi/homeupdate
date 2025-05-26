/**
 * تكوين جداول البيانات
 * يوفر هذا الملف تكوينات موحدة لجداول البيانات في النظام
 */

(function() {
    'use strict';
    
    /**
     * تكوين افتراضي لجداول البيانات
     */
    var defaultConfig = {
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
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        responsive: true,
        autoWidth: false,
        pageLength: 10,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "الكل"]],
        order: [[0, 'desc']],
        stateSave: true,
        stateDuration: 60 * 60 * 24 * 7, // 7 أيام
        processing: true,
        deferRender: true
    };
    
    /**
     * تهيئة جداول البيانات
     */
    document.addEventListener('DOMContentLoaded', function() {
        // تهيئة جداول البيانات العادية
        initializeDataTables();
        
        // تهيئة جداول البيانات مع خيارات إضافية
        initializeAdvancedDataTables();
    });
    
    /**
     * تهيئة جداول البيانات العادية
     */
    function initializeDataTables() {
        var tables = document.querySelectorAll('.datatable');
        
        if (tables.length > 0) {
            Array.prototype.slice.call(tables).forEach(function(table) {
                var config = Object.assign({}, defaultConfig);
                
                // إضافة خيارات مخصصة من سمات البيانات
                if (table.dataset.pageLength) {
                    config.pageLength = parseInt(table.dataset.pageLength);
                }
                
                if (table.dataset.order) {
                    try {
                        config.order = JSON.parse(table.dataset.order);
                    } catch (e) {
                        console.error('خطأ في تحليل سمة data-order:', e);
                    }
                }
                
                // تهيئة الجدول
                $(table).DataTable(config);
            });
        }
    }
    
    /**
     * تهيئة جداول البيانات المتقدمة
     */
    function initializeAdvancedDataTables() {
        // جداول البيانات مع أزرار التصدير
        var exportTables = document.querySelectorAll('.datatable-export');
        
        if (exportTables.length > 0) {
            Array.prototype.slice.call(exportTables).forEach(function(table) {
                var config = Object.assign({}, defaultConfig);
                
                // إضافة أزرار التصدير
                config.dom = '<"row"<"col-sm-12 col-md-6"B><"col-sm-12 col-md-6"f>>' +
                             '<"row"<"col-sm-12"tr>>' +
                             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>';
                
                config.buttons = [
                    {
                        extend: 'copy',
                        text: 'نسخ',
                        className: 'btn btn-sm btn-outline-secondary',
                        exportOptions: {
                            columns: ':not(.no-export)'
                        }
                    },
                    {
                        extend: 'excel',
                        text: 'Excel',
                        className: 'btn btn-sm btn-outline-success',
                        exportOptions: {
                            columns: ':not(.no-export)'
                        }
                    },
                    {
                        extend: 'pdf',
                        text: 'PDF',
                        className: 'btn btn-sm btn-outline-danger',
                        exportOptions: {
                            columns: ':not(.no-export)'
                        },
                        customize: function(doc) {
                            doc.defaultStyle.direction = 'rtl';
                            doc.defaultStyle.font = 'Cairo';
                        }
                    },
                    {
                        extend: 'print',
                        text: 'طباعة',
                        className: 'btn btn-sm btn-outline-primary',
                        exportOptions: {
                            columns: ':not(.no-export)'
                        }
                    }
                ];
                
                // إضافة خيارات مخصصة من سمات البيانات
                if (table.dataset.pageLength) {
                    config.pageLength = parseInt(table.dataset.pageLength);
                }
                
                if (table.dataset.order) {
                    try {
                        config.order = JSON.parse(table.dataset.order);
                    } catch (e) {
                        console.error('خطأ في تحليل سمة data-order:', e);
                    }
                }
                
                // تهيئة الجدول
                $(table).DataTable(config);
            });
        }
    }
    
    /**
     * تصدير الوظائف العامة
     */
    window.DataTablesConfig = {
        getDefaultConfig: function() {
            return Object.assign({}, defaultConfig);
        },
        
        initializeDataTable: function(selector, customConfig) {
            var config = Object.assign({}, defaultConfig, customConfig || {});
            return $(selector).DataTable(config);
        }
    };
})();
