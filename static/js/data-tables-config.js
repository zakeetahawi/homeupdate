/**
 * تكوين جداول البيانات
 * يوفر هذا الملف تكوينات موحدة لجداول البيانات في النظام
 */

(function() {
    'use strict';
    
    /**
     * تعريف الترجمة العربية الكاملة لـ DataTables
     * هذا هو المصدر الوحيد للترجمة في النظام
     */
    var arabicTranslation = {
        "emptyTable": "لا يوجد بيانات متاحة في الجدول",
        "loadingRecords": "جارٍ التحميل...",
        "processing": "جارٍ المعالجة...",
        "lengthMenu": "عرض _MENU_ مدخل",
        "zeroRecords": "لم يتم العثور على نتائج مطابقة",
        "info": "عرض _START_ إلى _END_ من _TOTAL_ مدخل",
        "infoEmpty": "عرض 0 إلى 0 من 0 مدخل",
        "infoFiltered": "(تمت التصفية من _MAX_ مجموع مدخلات)",
        "infoThousands": ",",
        "search": "بحث:",
        "paginate": {
            "first": "الأول",
            "previous": "السابق",
            "next": "التالي",
            "last": "الأخير"
            },
        "aria": {
            "sortAscending": ": تفعيل لترتيب العمود تصاعدياً",
            "sortDescending": ": تفعيل لترتيب العمود تنازلياً"
            },
        "select": {
            "rows": {
                "_": "%d صفوف محددة",
                "1": "صف واحد محدد"
            }
        },
        "buttons": {
            "print": "طباعة",
            "copyKeys": "زر <i>ctrl</i> أو <i>⌘</i> + <i>C</i> لنسخ بيانات الجدول إلى الحافظة.",
            "copySuccess": {
                "_": "تم نسخ %d صف للحافظة",
                "1": "تم نسخ صف واحد للحافظة"
            },
            "pageLength": {
                "-1": "اظهار الكل",
                "_": "إظهار %d أسطر"
            },
            "collection": "مجموعة",
            "copy": "نسخ",
            "copyTitle": "نسخ إلى الحافظة",
            "csv": "CSV",
            "excel": "Excel",
            "pdf": "PDF",
            "colvis": "إظهار/إخفاء الأعمدة",
            "colvisRestore": "إعادة الأعمدة"
            }
    };

    /**
     * التكوين الافتراضي لجداول البيانات، مع استخدام الترجمة العربية
     */
    var defaultConfig = {
        language: arabicTranslation,
        dom: 'Bfrtip',
        buttons: [
            { extend: 'copy', text: '<i class="fas fa-copy"></i> نسخ', className: 'btn btn-secondary' },
            { extend: 'excel', text: '<i class="fas fa-file-excel"></i> Excel', className: 'btn btn-success' },
            { extend: 'pdf', text: '<i class="fas fa-file-pdf"></i> PDF', className: 'btn btn-danger' },
            { extend: 'print', text: '<i class="fas fa-print"></i> طباعة', className: 'btn btn-info' },
            { extend: 'colvis', text: '<i class="fas fa-eye"></i> إظهار/إخفاء', className: 'btn btn-light' }
        ],
        responsive: true,
        autoWidth: false,
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "الكل"]],
        order: [[0, 'desc']],
        stateSave: true,
        stateDuration: 60 * 60 * 24 * 7, // 7 أيام
        processing: true,
        deferRender: true,
        columnDefs: [
            {
                targets: '_all',
                defaultContent: '-'
            }
        ],
        initComplete: function() {
            // تحسين الأداء: لا تقم بإضافة فلاتر لكل الجداول تلقائياً
            // يمكن إضافتها عند الحاجة باستخدام كلاس معين
            if ($(this.api().table().node()).hasClass('filterable')) {
                this.api().columns().every(function() {
                    var column = this;
                    var header = $(column.header());
                    
                    if (header.hasClass('no-filter')) return;

                    var select = $('<select class="form-select form-select-sm"><option value="">الكل</option></select>')
                        .appendTo(header)
                        .on('change', function() {
                            var val = $.fn.dataTable.util.escapeRegex($(this).val());
                            column.search(val ? '^' + val + '$' : '', true, false).draw();
                        });

                    column.data().unique().sort().each(function(d) {
                        if (d) {
                            select.append($('<option></option>').attr('value', d).text(d));
                        }
                    });
                });
            }
        }
    };

    /**
     * تهيئة جداول البيانات عند تحميل الصفحة
     */
    $(document).ready(function() {
        // معالج الأخطاء العام
        $.fn.dataTable.ext.errMode = function(settings, helpPage, message) {
            console.error('DataTables error:', message, settings);
            Swal.fire({
                title: 'خطأ في عرض البيانات',
                text: 'حدث خطأ أثناء معالجة بيانات الجدول. يرجى تحديث الصفحة والمحاولة مرة أخرى.',
                icon: 'error',
                confirmButtonText: 'تحديث'
            }).then((result) => {
                if (result.isConfirmed) {
                    location.reload();
                }
            });
        };

        // تهيئة كل الجداول التي تحمل الكلاس .datatable
            $('table.datatable').each(function() {
                var table = $(this);
            
            // تجنب إعادة التهيئة
            if ($.fn.DataTable.isDataTable(table)) {
                return;
            }

            // دمج التكوين الافتراضي مع أي تكوينات خاصة بالجدول
            var config = $.extend(true, {}, defaultConfig);
            
                if (table.data('order')) {
                try {
                    config.order = JSON.parse(table.data('order'));
                } catch (e) {
                    console.error("Error parsing data-order attribute:", e);
                }
            }
                if (table.data('page-length')) {
                config.pageLength = parseInt(table.data('page-length'), 10);
                }

                // تهيئة DataTable
            table.DataTable(config);
        });
    });
    
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
