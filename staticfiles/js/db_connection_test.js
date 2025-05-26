/**
 * سكريبت اختبار الاتصال بقاعدة البيانات وإضافة زر للانتقال إلى صفحة قواعد البيانات
 */
$(document).ready(function() {
    // إنشاء بطاقة جديدة لاختبار الاتصال بقاعدة البيانات
    var testCard = $('<div class="card mb-4" id="db-test-card">' +
                    '<div class="card-header pb-0">' +
                    '<h6>اختبار الاتصال بقاعدة البيانات الحالية</h6>' +
                    '</div>' +
                    '<div class="card-body">' +
                    '<p>اختبار الاتصال بقاعدة البيانات الحالية المستخدمة في النظام.</p>' +
                    '<button id="test-current-connection" class="btn btn-primary btn-sm">' +
                    '<i class="fas fa-database"></i> اختبار الاتصال' +
                    '</button>' +
                    '<div id="connection-result" class="mt-3" style="display: none;">' +
                    '<div class="alert" role="alert"></div>' +
                    '<div id="db-info" class="mt-2"></div>' +
                    '</div>' +
                    '</div>' +
                    '</div>');

    // إنشاء بطاقة جديدة للانتقال إلى صفحة قواعد البيانات
    var dbListCard = $('<div class="card mb-4" id="db-list-card">' +
                      '<div class="card-header pb-0">' +
                      '<h6>إدارة قواعد البيانات</h6>' +
                      '</div>' +
                      '<div class="card-body">' +
                      '<p>عرض وإدارة قواعد البيانات المتاحة في النظام.</p>' +
                      '<a href="/data_management/db-manager/databases/" class="btn btn-success btn-sm">' +
                      '<i class="fas fa-database"></i> عرض قواعد البيانات' +
                      '</a>' +
                      '</div>' +
                      '</div>');

    // إضافة البطاقات إلى الصفحة
    // نبحث عن العنصر الأب المناسب لإضافة البطاقات إليه
    var container = $('.container-fluid .row').first();

    // إنشاء عمود جديد للبطاقة الأولى
    var column1 = $('<div class="col-md-6 mb-4"></div>');
    column1.append(testCard);

    // إنشاء عمود جديد للبطاقة الثانية
    var column2 = $('<div class="col-md-6 mb-4"></div>');
    column2.append(dbListCard);

    // إضافة الأعمدة إلى الصف
    container.append(column1);
    container.append(column2);

    // اختبار الاتصال بقاعدة البيانات الحالية
    $('#test-current-connection').on('click', function() {
        var button = $(this);
        var resultDiv = $('#connection-result');
        var alertDiv = resultDiv.find('.alert');

        // تغيير حالة الزر
        button.prop('disabled', true);
        button.html('<i class="fas fa-spinner fa-spin"></i> جاري الاختبار...');

        // إخفاء نتيجة الاختبار السابقة
        resultDiv.hide();

        // إرسال طلب AJAX
        $.ajax({
            url: '/data_management/db-manager/test-current-connection/',
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                // عرض نتيجة الاختبار
                if (response.success) {
                    alertDiv.removeClass('alert-danger').addClass('alert-success');
                    alertDiv.html('<i class="fas fa-check-circle"></i> ' + response.message);

                    // إنشاء جدول لعرض معلومات قاعدة البيانات
                    var tableHtml = '<h6>معلومات قاعدة البيانات</h6>' +
                        '<table class="table table-sm">' +
                        '<tbody>' +
                        '<tr><th>المحرك</th><td>' + (response.db_info.engine || '-') + '</td></tr>' +
                        '<tr><th>الاسم</th><td>' + (response.db_info.name || '-') + '</td></tr>' +
                        '<tr><th>المضيف</th><td>' + (response.db_info.host || '-') + '</td></tr>' +
                        '<tr><th>المستخدم</th><td>' + (response.db_info.user || '-') + '</td></tr>' +
                        '<tr><th>الإصدار</th><td>' + (response.db_info.version || '-') + '</td></tr>' +
                        '<tr><th>الحجم</th><td>' + (response.db_info.size || '-') + '</td></tr>' +
                        '<tr><th>عدد الجداول</th><td>' + (response.db_info.tables_count || '-') + '</td></tr>' +
                        '</tbody>' +
                        '</table>';

                    // عرض معلومات قاعدة البيانات
                    $('#db-info').html(tableHtml);
                    $('#db-info').show();
                } else {
                    alertDiv.removeClass('alert-success').addClass('alert-danger');
                    alertDiv.html('<i class="fas fa-times-circle"></i> ' + response.message);

                    // إخفاء معلومات قاعدة البيانات
                    $('#db-info').hide();
                }

                // عرض نتيجة الاختبار
                resultDiv.show();
            },
            error: function(xhr, status, error) {
                // عرض رسالة الخطأ
                alertDiv.removeClass('alert-success').addClass('alert-danger');
                alertDiv.html('<i class="fas fa-times-circle"></i> حدث خطأ أثناء الاختبار: ' + error);

                // إخفاء معلومات قاعدة البيانات
                $('#db-info').hide();

                // عرض نتيجة الاختبار
                resultDiv.show();
            },
            complete: function() {
                // إعادة تفعيل الزر
                button.prop('disabled', false);
                button.html('<i class="fas fa-database"></i> اختبار الاتصال بقاعدة البيانات');
            }
        });
    });
});
