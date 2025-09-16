// دالة للتحقق من المديونية قبل الجدولة
function checkDebtBeforeScheduling(orderId, scheduleUrl) {
    // التحقق من المديونية
    fetch(`/installations/check-debt/${orderId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.has_debt) {
                // إذا كان هناك مديونية، عرض تحذير Sweet Alert
                Swal.fire({
                    title: '⚠️ تنبيه مديونية',
                    html: `
                        <div class="text-right" style="direction: rtl;">
                            <p><strong>العميل:</strong> ${data.customer_name}</p>
                            <p><strong>رقم الطلب:</strong> ${data.order_number}</p>
                            <p><strong>إجمالي المبلغ:</strong> ${data.total_amount.toLocaleString()} ${data.currency_symbol}</p>
                            <p><strong>المبلغ المدفوع:</strong> ${data.paid_amount.toLocaleString()} ${data.currency_symbol}</p>
                            <p class="text-danger"><strong>المبلغ المتبقي:</strong> ${data.debt_amount.toLocaleString()} ${data.currency_symbol}</p>
                            <hr>
                            <p class="text-warning">يوجد مديونية على هذا العميل. هل تريد المتابعة مع الجدولة؟</p>
                        </div>
                    `,
                    icon: 'warning',
                    showCancelButton: true,
                    showDenyButton: true,
                    confirmButtonText: '💰 تسديد من المنزل والمتابعة',
                    denyButtonText: '👨‍💼 متابعة مع البائع',
                    cancelButtonText: '❌ إلغاء',
                    confirmButtonColor: '#28a745',
                    denyButtonColor: '#ffc107',
                    cancelButtonColor: '#6c757d',
                    customClass: {
                        popup: 'text-right',
                        title: 'text-center',
                        htmlContainer: 'text-right'
                    },
                    width: '600px'
                }).then((result) => {
                    if (result.isConfirmed) {
                        // تسديد من المنزل - السماح بالجدولة
                        Swal.fire({
                            title: '✅ تم التأكيد',
                            text: 'سيتم تسديد المديونية من المنزل. يمكن المتابعة مع الجدولة.',
                            icon: 'success',
                            confirmButtonText: 'متابعة الجدولة',
                            confirmButtonColor: '#007bff'
                        }).then(() => {
                            // الانتقال لصفحة الجدولة
                            window.location.href = scheduleUrl;
                        });
                    } else if (result.isDenied) {
                        // متابعة مع البائع - منع الجدولة
                        Swal.fire({
                            title: '🚫 لا يمكن الجدولة',
                            html: `
                                <div class="text-right" style="direction: rtl;">
                                    <p>يجب إغلاق المديونية مع البائع أولاً قبل السماح بالجدولة.</p>
                                    <p class="text-info">💡 يرجى التواصل مع البائع لإغلاق المديونية ثم المحاولة مرة أخرى.</p>
                                </div>
                            `,
                            icon: 'error',
                            confirmButtonText: 'فهمت',
                            confirmButtonColor: '#dc3545'
                        });
                    }
                    // إذا ضغط إلغاء، لا نفعل شيء
                });
            } else {
                // لا توجد مديونية، السماح بالجدولة مباشرة
                window.location.href = scheduleUrl;
            }
        })
        .catch(error => {
            console.error('خطأ في التحقق من المديونية:', error);
            Swal.fire({
                title: '❌ خطأ',
                text: 'حدث خطأ أثناء التحقق من المديونية. يرجى المحاولة مرة أخرى.',
                icon: 'error',
                confirmButtonText: 'موافق'
            });
        });
}

// دالة مساعدة لتطبيق التحقق على جميع أزرار الجدولة
function initializeDebtChecking() {
    // البحث عن جميع أزرار الجدولة وإضافة التحقق لها
    document.querySelectorAll('[data-schedule-url]').forEach(button => {
        // تجنب إضافة listener متعدد للزر نفسه
        if (!button.hasAttribute('data-debt-check-enabled')) {
            button.setAttribute('data-debt-check-enabled', 'true');
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                const orderId = this.getAttribute('data-order-id');
                const scheduleUrl = this.getAttribute('data-schedule-url');
                
                if (orderId && scheduleUrl) {
                    checkDebtBeforeScheduling(orderId, scheduleUrl);
                } else {
                    console.error('مفقود: order-id أو schedule-url');
                }
            });
        }
    });
}

// تشغيل الدالة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', initializeDebtChecking);

// تشغيل الدالة عندما يتم تحديث المحتوى (للمحتوى المحمل ديناميكياً)
if (typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver(function(mutations) {
        let shouldReinitialize = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && (
                        node.querySelector && node.querySelector('[data-schedule-url]') ||
                        node.hasAttribute && node.hasAttribute('data-schedule-url')
                    )) {
                        shouldReinitialize = true;
                    }
                });
            }
        });
        
        if (shouldReinitialize) {
            setTimeout(initializeDebtChecking, 100); // تأخير قصير للتأكد من اكتمال التحديث
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}
