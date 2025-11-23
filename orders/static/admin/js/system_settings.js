/**
 * نظام إدارة الحقول الديناميكية في إعدادات النظام
 * Dynamic Fields Management System
 */

(function($) {
    'use strict';
    
    /**
     * حذف نوع تفصيل
     */
    window.deleteTailoringType = function(index) {
        if (!confirm('هل أنت متأكد من حذف نوع التفصيل؟')) {
            return;
        }
        
        // الحصول على القيمة الحالية
        const currentValue = $('#id_tailoring_types').val();
        let types = currentValue ? JSON.parse(currentValue) : [];
        
        // حذف العنصر
        types.splice(index, 1);
        
        // تحديث الحقل
        $('#id_tailoring_types').val(JSON.stringify(types));
        
        // إعادة تحميل الصفحة
        alert('تم الحذف! يرجى حفظ التغييرات.');
        location.reload();
    };
    
    /**
     * حذف نوع قماش
     */
    window.deleteFabricType = function(index) {
        if (!confirm('هل أنت متأكد من حذف نوع القماش؟')) {
            return;
        }
        
        const currentValue = $('#id_fabric_types').val();
        let types = currentValue ? JSON.parse(currentValue) : [];
        
        types.splice(index, 1);
        $('#id_fabric_types').val(JSON.stringify(types));
        
        alert('تم الحذف! يرجى حفظ التغييرات.');
        location.reload();
    };
    
    /**
     * حذف نوع تركيب
     */
    window.deleteInstallationType = function(index) {
        if (!confirm('هل أنت متأكد من حذف نوع التركيب؟')) {
            return;
        }
        
        const currentValue = $('#id_installation_types').val();
        let types = currentValue ? JSON.parse(currentValue) : [];
        
        types.splice(index, 1);
        $('#id_installation_types').val(JSON.stringify(types));
        
        alert('تم الحذف! يرجى حفظ التغييرات.');
        location.reload();
    };
    
    /**
     * حذف طريقة دفع
     */
    window.deletePaymentMethod = function(index) {
        if (!confirm('هل أنت متأكد من حذف طريقة الدفع؟')) {
            return;
        }
        
        const currentValue = $('#id_payment_methods').val();
        let methods = currentValue ? JSON.parse(currentValue) : [];
        
        methods.splice(index, 1);
        $('#id_payment_methods').val(JSON.stringify(methods));
        
        alert('تم الحذف! يرجى حفظ التغييرات.');
        location.reload();
    };
    
    /**
     * تهيئة النظام عند تحميل الصفحة
     */
    $(document).ready(function() {
        // إضافة تنبيهات للحقول المخفية
        $('input[type="hidden"]').each(function() {
            const $input = $(this);
            const label = $input.prev('label');
            
            if (label.length) {
                label.append(' <small style="color: #666;">(مخفي - يُدار تلقائياً)</small>');
            }
        });
        
        // تحذير عند تغيير نظام الطلبات
        $('#id_order_system').on('change', function() {
            const value = $(this).val();
            let message = '';
            
            if (value === 'wizard') {
                message = 'سيتم إخفاء النظام القديم وعرض نظام الويزارد فقط.';
            } else if (value === 'legacy') {
                message = 'سيتم إخفاء نظام الويزارد وعرض النظام القديم فقط.';
            } else {
                message = 'سيتم عرض كلا النظامين للمستخدمين.';
            }
            
            if (message) {
                const $help = $(this).next('.help');
                if ($help.length === 0) {
                    $(this).after(`<p class="help">${message}</p>`);
                } else {
                    $help.text(message);
                }
            }
        });
        
        // تحذير عند تغيير أولوية التعديل
        $('#id_edit_priority').on('change', function() {
            const value = $(this).val();
            let message = '';
            
            if (value === 'wizard') {
                message = 'سيتم فتح جميع الطلبات للتعديل في نظام الويزارد.';
            } else if (value === 'legacy') {
                message = 'سيتم فتح جميع الطلبات للتعديل في النظام القديم.';
            } else {
                message = 'سيتم فتح الطلب للتعديل حسب طريقة إنشائه.';
            }
            
            const $help = $(this).next('.help');
            if ($help.length === 0) {
                $(this).after(`<p class="help">${message}</p>`);
            } else {
                $help.text(message);
            }
        });
        
        // تأكيد الحفظ
        $('form').on('submit', function(e) {
            const orderSystem = $('#id_order_system').val();
            
            if (orderSystem === 'wizard' && !$('#id_hide_legacy_system').is(':checked')) {
                if (!confirm('لقد اخترت نظام الويزارد، هل تريد أيضاً إخفاء النظام القديم تلقائياً؟')) {
                    $('#id_hide_legacy_system').prop('checked', true);
                }
            } else if (orderSystem === 'legacy' && !$('#id_hide_wizard_system').is(':checked')) {
                if (!confirm('لقد اخترت النظام القديم، هل تريد أيضاً إخفاء نظام الويزارد تلقائياً؟')) {
                    $('#id_hide_wizard_system').prop('checked', true);
                }
            }
            
            return true;
        });
        
        // إضافة أيقونات للعناوين
        $('.module h2').each(function() {
            const $h2 = $(this);
            const text = $h2.text().trim();
            
            if (text.includes('إعدادات نظام الطلبات')) {
                $h2.html('⚙️ ' + text);
            } else if (text.includes('أنواع التفصيل')) {
                $h2.html('📝 ' + text);
            } else if (text.includes('أنواع الأقمشة')) {
                $h2.html('🎨 ' + text);
            } else if (text.includes('أنواع التركيب')) {
                $h2.html('🔧 ' + text);
            } else if (text.includes('طرق الدفع')) {
                $h2.html('💰 ' + text);
            } else if (text.includes('العقود')) {
                $h2.html('📄 ' + text);
            } else if (text.includes('الإشعارات')) {
                $h2.html('🔔 ' + text);
            }
        });
    });
    
})(django.jQuery);
