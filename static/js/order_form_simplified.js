// ملف JavaScript مبسط ومتكامل لنموذج الطلب
// order_form_simplified.js

// تعريف المتغيرات العامة
if (typeof document.orderItems === 'undefined') {
    document.orderItems = [];
}

// متغيرات لمنع الإرسال المتعدد وتتبع التقدم
window.isSubmitting = false;
window.submissionStartTime = null;
window.progressInterval = null;

// دالة لإظهار مؤشر التقدم المحسن
function showProgressIndicator() {
    if (window.isSubmitting) {
        return; // تجنب إظهار مؤشرات متعددة
    }

    window.isSubmitting = true;
    window.submissionStartTime = Date.now();

    // إنشاء مؤشر التقدم المحسن
    Swal.fire({
        title: 'جاري إنشاء الطلب...',
        html: `
            <div class="progress-container">
                <div class="progress mb-3" style="height: 25px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated bg-success"
                         role="progressbar" style="width: 0%" id="order-progress-bar">
                        <span id="progress-text">0%</span>
                    </div>
                </div>
                <div class="progress-steps">
                    <div class="step active" id="step-1">
                        <i class="fas fa-check-circle"></i>
                        <span>التحقق من البيانات</span>
                    </div>
                    <div class="step" id="step-2">
                        <i class="fas fa-save"></i>
                        <span>حفظ الطلب</span>
                    </div>
                    <div class="step" id="step-3">
                        <i class="fas fa-cloud-upload-alt"></i>
                        <span>معالجة الملفات</span>
                    </div>
                    <div class="step" id="step-4">
                        <i class="fas fa-check"></i>
                        <span>إنهاء العملية</span>
                    </div>
                </div>
                <div class="time-indicator mt-3">
                    <small class="text-muted">الوقت المنقضي: <span id="elapsed-time">0</span> ثانية</small>
                </div>
            </div>
            <style>
                .progress-container {
                    text-align: center;
                }
                .progress-steps {
                    display: flex;
                    justify-content: space-between;
                    margin-top: 20px;
                }
                .step {
                    flex: 1;
                    text-align: center;
                    padding: 10px;
                    opacity: 0.5;
                    transition: all 0.3s ease;
                }
                .step.active {
                    opacity: 1;
                    color: #28a745;
                }
                .step.completed {
                    opacity: 1;
                    color: #28a745;
                }
                .step i {
                    display: block;
                    font-size: 24px;
                    margin-bottom: 5px;
                }
                .step span {
                    font-size: 12px;
                    display: block;
                }
            </style>
        `,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        showCancelButton: true,
        cancelButtonText: 'إلغاء',
        cancelButtonColor: '#dc3545',
        didOpen: () => {
            startProgressAnimation();
        }
    }).then((result) => {
        // إذا تم الضغط على إلغاء
        if (result.dismiss === Swal.DismissReason.cancel) {
            console.log('⚠️ تم إلغاء العملية من قبل المستخدم');
            hideProgressIndicator();
            Swal.fire({
                icon: 'info',
                title: 'تم الإلغاء',
                text: 'تم إلغاء إنشاء الطلب',
                confirmButtonText: 'موافق'
            });
        }
    });
}

// دالة لتحديث مؤشر التقدم
function updateProgress(step, percentage, message) {
    const progressBar = document.getElementById('order-progress-bar');
    const progressText = document.getElementById('progress-text');

    if (progressBar && progressText) {
        progressBar.style.width = percentage + '%';
        progressText.textContent = percentage + '%';
    }

    // تحديث الخطوات
    for (let i = 1; i <= 4; i++) {
        const stepElement = document.getElementById(`step-${i}`);
        if (stepElement) {
            if (i < step) {
                stepElement.classList.add('completed');
                stepElement.classList.remove('active');
            } else if (i === step) {
                stepElement.classList.add('active');
                stepElement.classList.remove('completed');
            } else {
                stepElement.classList.remove('active', 'completed');
            }
        }
    }

    // تحديث العنوان إذا تم تمرير رسالة
    if (message) {
        const titleElement = document.querySelector('.swal2-title');
        if (titleElement) {
            titleElement.textContent = message;
        }
    }
}

// دالة لبدء تحريك مؤشر التقدم
function startProgressAnimation() {
    let currentStep = 1;
    let currentProgress = 0;

    // تحديث الوقت المنقضي
    window.progressInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - window.submissionStartTime) / 1000);
        const elapsedElement = document.getElementById('elapsed-time');
        if (elapsedElement) {
            elapsedElement.textContent = elapsed;
        }
    }, 1000);

    // محاكاة التقدم
    const progressSteps = [
        { step: 1, progress: 25, message: 'جاري التحقق من البيانات...', delay: 500 },
        { step: 2, progress: 50, message: 'جاري حفظ الطلب...', delay: 1000 },
        { step: 3, progress: 75, message: 'جاري معالجة الملفات...', delay: 1500 },
        { step: 4, progress: 90, message: 'جاري إنهاء العملية...', delay: 2000 }
    ];

    progressSteps.forEach((stepData, index) => {
        setTimeout(() => {
            updateProgress(stepData.step, stepData.progress, stepData.message);
        }, stepData.delay);
    });
}

// دالة لإخفاء مؤشر التقدم
function hideProgressIndicator() {
    window.isSubmitting = false;
    if (window.progressInterval) {
        clearInterval(window.progressInterval);
        window.progressInterval = null;
    }

    // إغلاق SweetAlert إذا كان مفتوحاً
    if (Swal.isVisible()) {
        Swal.close();
    }

    disableFormButtons(); // إعادة تفعيل الأزرار
    console.log('✅ تم إخفاء مؤشر التقدم وإعادة تعيين الحالة');
    Swal.close();
}

// دالة لإظهار رسالة نجاح محسنة
function showSuccessMessage(message, redirectUrl) {
    hideProgressIndicator();

    Swal.fire({
        icon: 'success',
        title: 'تم بنجاح!',
        text: message || 'تم إنشاء الطلب بنجاح',
        confirmButtonText: 'موافق',
        timer: 3000,
        timerProgressBar: true
    }).then(() => {
        if (redirectUrl) {
            window.location.href = redirectUrl;
        }
    });
}

// دالة لإظهار رسالة خطأ محسنة
function showErrorMessage(message, details) {
    hideProgressIndicator();

    let htmlContent = `<p>${message || 'حدث خطأ أثناء إنشاء الطلب'}</p>`;

    if (details) {
        htmlContent += `
            <div class="mt-3">
                <button class="btn btn-sm btn-outline-secondary" onclick="toggleErrorDetails()">
                    عرض التفاصيل
                </button>
                <div id="error-details" style="display: none; margin-top: 10px;">
                    <small class="text-muted">${details}</small>
                </div>
            </div>
        `;
    }

    Swal.fire({
        icon: 'error',
        title: 'خطأ',
        html: htmlContent,
        confirmButtonText: 'موافق',
        customClass: {
            popup: 'error-popup'
        }
    });
}

// دالة لتبديل عرض تفاصيل الخطأ
function toggleErrorDetails() {
    const detailsDiv = document.getElementById('error-details');
    if (detailsDiv) {
        detailsDiv.style.display = detailsDiv.style.display === 'none' ? 'block' : 'none';
    }
}

// تهيئة Select2 للبحث عن العملاء
function initializeCustomerSearch() {
    console.log('تهيئة Select2 للبحث عن العملاء...');

    // التحقق من وجود jQuery و Select2
    if (typeof $ === 'undefined') {
        console.log('jQuery غير محمل - تأجيل التهيئة');
        setTimeout(initializeCustomerSearch, 500);
        return;
    }

    if (typeof $.fn.select2 === 'undefined') {
        console.log('Select2 غير محمل - تأجيل التهيئة');
        setTimeout(initializeCustomerSearch, 500);
        return;
    }

    const searchSelect = $('#customer_search_select');
    if (searchSelect.length === 0) {
        console.log('عنصر البحث عن العملاء غير موجود - البحث عن بدائل...');

        // البحث عن حقل العميل الأصلي
        const originalCustomerField = $('#id_customer');
        if (originalCustomerField.length > 0) {
            console.log('تم العثور على حقل العميل الأصلي - تهيئة Select2 عليه');
            initializeSelect2OnOriginalField(originalCustomerField);
        } else {
            console.log('لم يتم العثور على أي حقل عميل');
        }
        return;
    }
    
    searchSelect.select2({
        theme: 'bootstrap-5',
        language: 'ar',
        placeholder: 'ابحث عن العميل بالاسم أو الهاتف...',
        allowClear: true,
        minimumInputLength: 2,
        ajax: {
            url: '/customers/api/customers/',
            dataType: 'json',
            delay: 300,
            data: function (params) {
                return {
                    q: params.term,
                    page: params.page
                };
            },
            processResults: function (data, params) {
                if (data.error || !data.results) {
                    return { results: [] };
                }
                return {
                    results: data.results.map(function(customer) {
                        return {
                            id: customer.id,
                            text: customer.name + ' - ' + customer.phone,
                            customer: customer
                        };
                    })
                };
            },
            cache: true
        },
        templateResult: function(customer) {
            if (customer.loading) return customer.text;
            if (!customer.customer) return customer.text;
            
            return $('<div><div class="fw-bold">' + customer.customer.name + '</div><div class="text-muted small">' + customer.customer.phone + ' - ' + (customer.customer.email || '') + '</div></div>');
        },
        templateSelection: function(customer) {
            if (!customer.customer) return customer.text;
            return customer.customer.name + ' - ' + customer.customer.phone;
        }
    });

    // عند اختيار عميل
    searchSelect.on('select2:select', function (e) {
        var data = e.params.data;
        console.log('✅ تم اختيار العميل من Select2:', data);

        // الحصول على معرف العميل من البيانات
        var customerId = data.id || (data.customer && data.customer.id);
        var customerName = data.text || (data.customer && (data.customer.name + ' - ' + data.customer.phone));

        if (customerId) {
            console.log('✅ معرف العميل:', customerId);
            console.log('✅ اسم العميل:', customerName);

            // تعيين القيمة في الحقل المخفي باستخدام jQuery
            const customerField = $('#id_customer');
            console.log('🔍 حقل العميل موجود؟', customerField.length > 0);
            console.log('🔍 نوع حقل العميل:', customerField.prop('tagName'));
            console.log('🔍 القيمة الحالية:', customerField.val());

            if (customerField.length > 0) {
                // التحقق من وجود الخيار في القائمة
                var optionExists = customerField.find('option[value="' + customerId + '"]').length > 0;
                console.log('🔍 الخيار موجود في القائمة؟', optionExists);

                if (!optionExists) {
                    // إضافة الخيار إلى القائمة إذا لم يكن موجودًا
                    var newOption = new Option(customerName, customerId, true, true);
                    customerField.append(newOption);
                    console.log('✅ تم إضافة خيار جديد للعميل:', customerId);
                }

                // تعيين القيمة
                customerField.val(customerId);
                console.log('✅ تم تعيين قيمة العميل في الحقل:', customerField.val());

                // إزالة علامة invalid وإضافة valid
                customerField.removeClass('is-invalid');
                customerField.addClass('is-valid');

                // تفعيل حدث change لضمان تحديث النموذج
                customerField.trigger('change');
            } else {
                console.error('❌ لم يتم العثور على حقل id_customer');
            }

            // التحقق من النموذج بعد تأخير قصير للتأكد من تحديث القيمة
            setTimeout(function() {
                validateFormRealTime();
            }, 150);
        } else {
            console.error('❌ لم يتم العثور على معرف العميل في البيانات:', data);
        }
    });

    // عند إزالة اختيار العميل
    searchSelect.on('select2:clear', function (e) {
        console.log('⚠️ تم إزالة اختيار العميل');

        const customerField = document.getElementById('id_customer');
        if (customerField) {
            customerField.value = '';
            customerField.classList.remove('is-valid');
            customerField.classList.add('is-invalid');
        }

        setTimeout(function() {
            validateFormRealTime();
        }, 150);
    });
}

// دالة لتهيئة Select2 على حقل العميل الأصلي
function initializeSelect2OnOriginalField(field) {
    try {
        field.select2({
            theme: 'bootstrap-5',
            language: 'ar',
            placeholder: 'اختر العميل...',
            allowClear: true,
            minimumInputLength: 0,
            ajax: {
                url: '/customers/api/customers/',
                dataType: 'json',
                delay: 300,
                data: function (params) {
                    return {
                        q: params.term || '',
                        page: params.page || 1
                    };
                },
                processResults: function (data, params) {
                    if (data.error || !data.results) {
                        return { results: [] };
                    }
                    return {
                        results: data.results.map(function(customer) {
                            return {
                                id: customer.id,
                                text: customer.name + ' - ' + customer.phone,
                                customer: customer
                            };
                        })
                    };
                },
                cache: true
            },
            templateResult: function(customer) {
                if (customer.loading) return customer.text;
                if (!customer.customer) return customer.text;

                return $('<div><div class="fw-bold">' + customer.customer.name + '</div><div class="text-muted small">' + customer.customer.phone + ' - ' + (customer.customer.email || '') + '</div></div>');
            },
            templateSelection: function(customer) {
                if (!customer.customer) return customer.text;
                return customer.customer.name + ' - ' + customer.customer.phone;
            }
        });

        // معالج تغيير الاختيار
        field.on('select2:select', function (e) {
            const data = e.params.data;
            console.log('✅ تم اختيار العميل من الحقل الأصلي:', data);

            // الحصول على معرف العميل من البيانات
            var customerId = data.id || (data.customer && data.customer.id);
            var customerName = data.text || (data.customer && (data.customer.name + ' - ' + data.customer.phone));

            if (customerId) {
                console.log('✅ معرف العميل:', customerId);

                // حفظ بيانات العميل في المتغير العام
                if (data.customer) {
                    window.currentCustomer = data.customer;
                }

                // التأكد من تعيين القيمة في الحقل
                const customerField = $('#id_customer');
                if (customerField.length > 0) {
                    // التحقق من وجود الخيار في القائمة
                    var optionExists = customerField.find('option[value="' + customerId + '"]').length > 0;

                    if (!optionExists) {
                        // إضافة الخيار إلى القائمة إذا لم يكن موجودًا
                        var newOption = new Option(customerName, customerId, true, true);
                        customerField.append(newOption);
                        console.log('✅ تم إضافة خيار جديد للعميل:', customerId);
                    }

                    customerField.val(customerId);
                    console.log('✅ تم تعيين قيمة العميل:', customerField.val());

                    // إزالة علامة invalid وإضافة valid
                    customerField.removeClass('is-invalid');
                    customerField.addClass('is-valid');
                }

                // تحديث الحقول إذا لزم الأمر
                updateFormFields();

                // التحقق من النموذج بعد تأخير قصير
                setTimeout(function() {
                    validateFormRealTime();
                }, 150);
            } else {
                console.error('❌ لم يتم العثور على معرف العميل في البيانات:', data);
            }
        });

        // معالج إزالة الاختيار
        field.on('select2:clear', function (e) {
            console.log('⚠️ تم إزالة اختيار العميل من الحقل الأصلي');

            const customerField = document.getElementById('id_customer');
            if (customerField) {
                customerField.value = '';
                customerField.classList.remove('is-valid');
                customerField.classList.add('is-invalid');
            }

            window.currentCustomer = null;

            setTimeout(function() {
                validateFormRealTime();
            }, 150);
        });

        console.log('تم تهيئة Select2 على حقل العميل الأصلي بنجاح');

    } catch (error) {
        console.error('خطأ في تهيئة Select2 على الحقل الأصلي:', error);
    }
}

// إدارة حقول النموذج بناءً على نوع الطلب
function updateFormFields() {
    const selectedRadio = document.querySelector('input[name="order_type_selector"]:checked');
    const selectedType = selectedRadio ? selectedRadio.value : 'none';

    // مزامنة الراديو الأصلي من Django
    const realRadios = document.querySelectorAll('input[name="selected_types"]');
    realRadios.forEach(radio => {
        radio.checked = (radio.value === selectedType);
    });

    console.log('✅ تم تحديث نوع الطلب:', selectedType);
    console.log('✅ عدد الراديو الأصلي:', realRadios.length);

    const showForContract = ['installation', 'tailoring', 'accessory'].includes(selectedType);
    const showRelatedInspection = ['installation', 'tailoring', 'accessory'].includes(selectedType);

    console.log('🔍 نوع الطلب:', selectedType);
    console.log('🔍 إظهار حقول العقد:', showForContract);
    console.log('🔍 إظهار المعاينة المرتبطة:', showRelatedInspection);

    // إظهار/إخفاء حقول العقد
    const contractFields = document.querySelectorAll('.contract-field');
    const contractElectronicBtnField = document.querySelector('.contract-electronic-btn-field');
    const contractFileField = document.querySelector('.contract-file-field');
    const relatedInspectionField = document.querySelector('.related-inspection-field');

    console.log('🔍 عدد حقول العقد:', contractFields.length);
    console.log('🔍 حقل زر العقد الإلكتروني:', contractElectronicBtnField ? 'موجود' : 'غير موجود');
    console.log('🔍 حقل ملف العقد:', contractFileField ? 'موجود' : 'غير موجود');
    console.log('🔍 حقل المعاينة المرتبطة:', relatedInspectionField ? 'موجود' : 'غير موجود');

    contractFields.forEach(field => {
        if (field) field.style.display = showForContract ? 'block' : 'none';
    });

    // إظهار زر العقد الإلكتروني وحقل رفع الملف للطلبات التي تتطلب عقد
    if (contractElectronicBtnField) {
        contractElectronicBtnField.style.display = showForContract ? 'block' : 'none';
    }

    if (contractFileField) {
        contractFileField.style.display = showForContract ? 'block' : 'none';
    }

    if (relatedInspectionField) {
        relatedInspectionField.style.display = showRelatedInspection ? 'block' : 'none';
    }
    
    // إعادة التحقق من النموذج
    setTimeout(validateFormRealTime, 100);
}

// تحديث جدول العناصر المباشر مع تحسينات الأداء
function updateLiveOrderItemsTable() {
    const tableDiv = document.getElementById('live-order-items-table');
    if (!tableDiv) return;

    // استخدام requestAnimationFrame لتحسين الأداء
    requestAnimationFrame(() => {
        if (document.orderItems.length === 0) {
            tableDiv.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-shopping-cart text-muted" style="font-size: 2rem;"></i>
                    <p class="text-muted mt-2">لم يتم اختيار أي عناصر بعد</p>
                    <p class="small">اضغط على زر "إضافة عنصر" لبدء إضافة المنتجات</p>
                </div>
            `;
            syncOrderItemsToFormFields();
            validateFormRealTime();
            return;
        }

        // حساب الإجمالي مع الخصم
        const totalAmount = document.orderItems.reduce((sum, item) => sum + item.total, 0);
        const totalDiscount = document.orderItems.reduce((sum, item) => {
            const discountPercentage = item.discount_percentage || 0;
            return sum + (item.total * discountPercentage / 100);
        }, 0);
        const totalAfterDiscount = totalAmount - totalDiscount;

        // إنشاء العناصر باستخدام template literals محسنة
        const headerHtml = `
            <div class="card">
                <div class="card-header text-white" style="background-color: #198754; font-weight: bold;">
                    <h6 class="mb-0">
                        <i class="fas fa-list me-2"></i>
                        العناصر المختارة (${document.orderItems.length})
                    </h6>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>#</th>
                                    <th>المنتج</th>
                                    <th>الكمية</th>
                                    <th>سعر الوحدة</th>
                                    <th>الخصم %</th>
                                    <th>مبلغ الخصم</th>
                                    <th>الإجمالي بعد الخصم</th>
                                    <th>الإجراءات</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        // إنشاء صفوف الجدول بكفاءة أكبر
        const rowsHtml = document.orderItems.map((item, idx) => {
            const discountPercentage = item.discount_percentage || 0;
            const discountAmount = (item.total * discountPercentage / 100);
            const totalAfterDiscount = item.total - discountAmount;
            
            return `
            <tr>
                <td><span class="badge bg-primary">${idx+1}</span></td>
                <td>
                    <strong>${item.name}</strong>
                    ${item.code ? `<br><small class="text-muted">كود: ${item.code}</small>` : ''}
                    ${item.notes ? `<br><small class="text-info"><i class="fas fa-sticky-note me-1"></i>${item.notes}</small>` : ''}
                </td>
                <td><span class="badge bg-info">${parseFloat(item.quantity).toFixed(3).replace(/\.?0+$/, '')}</span></td>
                <td>${item.unit_price} ج.م</td>
                <td>
                    <select class="form-select form-select-sm discount-select" 
                            onchange="updateItemDiscount(${idx}, this.value)" 
                            style="width: 80px; font-size: 0.875rem;">
                        <option value="0" ${discountPercentage == 0 ? 'selected' : ''}>0%</option>
                        <option value="1" ${discountPercentage == 1 ? 'selected' : ''}>1%</option>
                        <option value="2" ${discountPercentage == 2 ? 'selected' : ''}>2%</option>
                        <option value="3" ${discountPercentage == 3 ? 'selected' : ''}>3%</option>
                        <option value="4" ${discountPercentage == 4 ? 'selected' : ''}>4%</option>
                        <option value="5" ${discountPercentage == 5 ? 'selected' : ''}>5%</option>
                        <option value="6" ${discountPercentage == 6 ? 'selected' : ''}>6%</option>
                        <option value="7" ${discountPercentage == 7 ? 'selected' : ''}>7%</option>
                        <option value="8" ${discountPercentage == 8 ? 'selected' : ''}>8%</option>
                        <option value="9" ${discountPercentage == 9 ? 'selected' : ''}>9%</option>
                        <option value="10" ${discountPercentage == 10 ? 'selected' : ''}>10%</option>
                        <option value="11" ${discountPercentage == 11 ? 'selected' : ''}>11%</option>
                        <option value="12" ${discountPercentage == 12 ? 'selected' : ''}>12%</option>
                        <option value="13" ${discountPercentage == 13 ? 'selected' : ''}>13%</option>
                        <option value="14" ${discountPercentage == 14 ? 'selected' : ''}>14%</option>
                        <option value="15" ${discountPercentage == 15 ? 'selected' : ''}>15%</option>
                    </select>
                </td>
                <td>
                    ${discountAmount > 0 ? 
                        `<span class="text-danger">-${discountAmount.toFixed(2)} ج.م</span>` : 
                        '<span class="text-muted">0.00 ج.م</span>'
                    }
                </td>
                <td><strong class="text-success">${totalAfterDiscount.toFixed(2)} ج.م</strong></td>
                <td>
                    <button type="button" class="btn btn-sm btn-danger"
                            onclick="removeOrderItem(${idx})" title="حذف العنصر">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        }).join('');

        const footerHtml = `
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="card-footer text-center bg-success text-white">
                    <div class="row">
                        <div class="col-md-4">
                            <strong class="fs-6">
                                <i class="fas fa-calculator me-2"></i>
                                الإجمالي: ${totalAmount.toFixed(2)} ج.م
                            </strong>
                        </div>
                        <div class="col-md-4">
                            <strong class="fs-6">
                                <i class="fas fa-percentage me-2"></i>
                                إجمالي الخصم: ${totalDiscount.toFixed(2)} ج.م
                            </strong>
                        </div>
                        <div class="col-md-4">
                            <strong class="fs-5">
                                <i class="fas fa-money-bill-wave me-2"></i>
                                الإجمالي النهائي: ${totalAfterDiscount.toFixed(2)} ج.م
                            </strong>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // تحديث المحتوى مرة واحدة
        tableDiv.innerHTML = headerHtml + rowsHtml + footerHtml;
    });
    
    // حفظ العناصر في الحقول المخفية
    syncOrderItemsToFormFields();
    
    // تحديث حالة الأزرار
    validateFormRealTime();
}

// مزامنة العناصر مع الحقول المخفية
function syncOrderItemsToFormFields() {
    const orderItemsField = document.getElementById('order_items');
    const selectedProductsField = document.getElementById('selected_products');
    
    const itemsJson = JSON.stringify(document.orderItems);
    
    if (orderItemsField) {
        orderItemsField.value = itemsJson;
    }
    if (selectedProductsField) {
        selectedProductsField.value = itemsJson;
    }
    
    console.log('تم حفظ العناصر:', document.orderItems.length > 0 ? `${document.orderItems.length} عنصر` : 'لا توجد عناصر');
}

// حذف عنصر من القائمة
function removeOrderItem(idx) {
    if (confirm('هل تريد حذف هذا العنصر من الطلب؟')) {
        document.orderItems.splice(idx, 1);
        updateLiveOrderItemsTable();
    }
}

// تحديث خصم العنصر
function updateItemDiscount(idx, discountPercentage) {
    if (document.orderItems[idx]) {
        document.orderItems[idx].discount_percentage = parseFloat(discountPercentage);
        updateLiveOrderItemsTable();
    }
}

// إضافة عنصر للطلب باستخدام SweetAlert
function showAddItemModal() {
    Swal.fire({
        title: 'إضافة عنصر للطلب',
        html: `
            <div class="text-start">
                <div class="mb-3">
                    <label class="form-label">البحث عن المنتج:</label>
                    <input type="text" id="product-search" class="form-control" placeholder="اكتب اسم المنتج أو الكود...">
                    <div id="search-results" class="mt-2" style="max-height: 200px; overflow-y: auto;"></div>
                </div>
                
                <div id="product-details" style="display: none;">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">اسم المنتج:</label>
                            <input type="text" id="selected-product-name" class="form-control" readonly>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">كود المنتج:</label>
                            <input type="text" id="selected-product-code" class="form-control" readonly>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <label class="form-label">سعر الوحدة:</label>
                            <input type="text" id="selected-product-price" class="form-control" readonly>
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">الكمية:</label>
                            <input type="number" id="selected-quantity" class="form-control" min="0.001" step="0.001" value="1" placeholder="مثال: 4.25">
                        </div>
                        <div class="col-md-4 mb-3">
                            <label class="form-label">الإجمالي:</label>
                            <input type="text" id="selected-total" class="form-control" readonly>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">ملاحظات:</label>
                        <textarea id="selected-notes" class="form-control" rows="2" placeholder="ملاحظات العنصر (اختياري)"></textarea>
                    </div>
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'إضافة العنصر',
        cancelButtonText: 'إلغاء',
        width: '600px',
        preConfirm: () => {
            const selectedProduct = Swal.getPopup().selectedProduct;
            const quantityInput = document.getElementById('selected-quantity');
            const notes = document.getElementById('selected-notes').value || '';

            if (!selectedProduct) {
                Swal.showValidationMessage('يرجى اختيار منتج أولاً');
                return false;
            }

            // تحسين معالجة الكمية لحل مشكلة الاقتطاع في الهواتف المحمولة
            let quantity;
            try {
                const quantityStr = quantityInput.value.trim();
                if (!quantityStr) {
                    Swal.showValidationMessage('يرجى إدخال الكمية');
                    return false;
                }

                // استخدام Number بدلاً من parseFloat للحصول على دقة أفضل
                quantity = Number(quantityStr);

                // التحقق من صحة القيمة
                if (isNaN(quantity) || !isFinite(quantity)) {
                    Swal.showValidationMessage('يرجى إدخال كمية صحيحة');
                    return false;
                }

                if (quantity <= 0) {
                    Swal.showValidationMessage('يجب أن تكون الكمية أكبر من صفر');
                    return false;
                }

                // التحقق من الحد الأقصى المعقول للكمية
                if (quantity > 999999) {
                    Swal.showValidationMessage('الكمية كبيرة جداً');
                    return false;
                }

                // التأكد من أن الكمية لها دقة مناسبة (حتى 3 منازل عشرية)
                const decimalPlaces = (quantityStr.split('.')[1] || '').length;
                if (decimalPlaces > 3) {
                    Swal.showValidationMessage('الكمية يمكن أن تحتوي على 3 منازل عشرية كحد أقصى');
                    return false;
                }

                console.log(`✅ تم التحقق من الكمية: ${quantityStr} → ${quantity}`);

            } catch (error) {
                console.error('خطأ في معالجة الكمية:', error);
                Swal.showValidationMessage('خطأ في معالجة الكمية');
                return false;
            }

            // التحقق من عدم تكرار المنتج
            const exists = document.orderItems.find(x => x.product_id === selectedProduct.id);
            if (exists) {
                Swal.showValidationMessage('تمت إضافة هذا المنتج بالفعل!');
                return false;
            }

            // حساب الإجمالي بدقة
            const total = Number((selectedProduct.price * quantity).toFixed(2));

            // إضافة العنصر مع الحفاظ على دقة القيم العشرية
            document.orderItems.push({
                product_id: selectedProduct.id,
                name: selectedProduct.name,
                code: selectedProduct.code || '',
                unit_price: selectedProduct.price,
                quantity: quantity, // استخدام القيمة المحولة بدقة
                discount_percentage: 0, // خصم افتراضي 0%
                total: total,
                notes: notes
            });
            
            updateLiveOrderItemsTable();
            
            return true;
        },
        didOpen: () => {
            setupProductSearch();
        }
    });
}

// إعداد البحث عن المنتجات داخل النافذة المنبثقة
function setupProductSearch() {
    const searchInput = document.getElementById('product-search');
    const searchResults = document.getElementById('search-results');
    const productDetails = document.getElementById('product-details');
    const quantityInput = document.getElementById('selected-quantity');
    const totalInput = document.getElementById('selected-total');
    
    // البحث عن المنتجات مع تحسينات الأداء
    let searchTimeout;
    let searchController;

    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        if (query.length < 2) {
            searchResults.innerHTML = '';
            return;
        }

        // إظهار مؤشر التحميل
        searchResults.innerHTML = '<div class="text-center p-3"><i class="fas fa-spinner fa-spin"></i> جاري البحث...</div>';

        // تأخير البحث لتجنب الطلبات الكثيرة
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {

            // إلغاء الطلب السابق إذا كان موجوداً
            if (searchController) {
                searchController.abort();
            }
            searchController = new AbortController();

            fetch(`/inventory/api/product-autocomplete/?query=${encodeURIComponent(query)}`, {
                signal: searchController.signal,
                headers: {
                    'Cache-Control': 'max-age=300' // تخزين مؤقت لـ 5 دقائق
                }
            })
                .then(res => {
                    if (!res.ok) throw new Error('Network response was not ok');
                    return res.json();
                })
                .then(data => {
                    // التحقق من أن الطلب لم يتم إلغاؤه
                    if (searchController.signal.aborted) return;

                    searchResults.innerHTML = '';
                    if (data.length > 0) {
                        // استخدام DocumentFragment لتحسين الأداء
                        const fragment = document.createDocumentFragment();

                        data.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'border rounded p-2 mb-2 cursor-pointer product-search-item';
                            div.style.cursor = 'pointer';
                            div.innerHTML = `
                                <strong>${item.name}</strong>
                                ${item.code ? `<small class="text-muted ms-2">(${item.code})</small>` : ''}
                                <br>
                                <small class="text-muted">السعر: ${item.price} ج.م | المخزون: ${item.current_stock}</small>
                            `;

                            // حفظ بيانات المنتج في dataset
                            div.dataset.productData = JSON.stringify(item);

                            // إضافة معالج النقر
                            div.addEventListener('click', function() {
                                selectProduct(item);
                            });

                            fragment.appendChild(div);
                        });

                        searchResults.appendChild(fragment);
                    } else {
                        searchResults.innerHTML = '<p class="text-muted">لا توجد نتائج</p>';
                    }
                })
                .catch(error => {
                    if (error.name === 'AbortError') {
                        console.log('تم إلغاء طلب البحث');
                        return;
                    }
                    console.error('خطأ في البحث:', error);
                    searchResults.innerHTML = '<p class="text-danger">خطأ في البحث. يرجى المحاولة مرة أخرى.</p>';
                });
        }, 300); // تقليل وقت التأخير من 500 إلى 300
    });
    
    // تحديث الإجمالي عند تغيير الكمية
    quantityInput.addEventListener('input', function() {
        updateTotalWithDiscount();
    });
}

// دالة لحساب الإجمالي
function setupTotalCalculation() {
    const quantityInput = document.getElementById('selected-quantity');
    
    if (quantityInput) {
        quantityInput.addEventListener('input', updateTotal);
    }
}

// دالة تحديث الإجمالي مع معالجة محسنة للقيم العشرية
function updateTotal() {
    const selectedProduct = Swal.getPopup().selectedProduct;
    const totalInput = document.getElementById('selected-total');
    const quantityInput = document.getElementById('selected-quantity');

    if (selectedProduct && totalInput && quantityInput) {
        try {
            const quantityStr = quantityInput.value.trim();
            if (!quantityStr) {
                totalInput.value = '0.00 ج.م';
                return;
            }

            // استخدام Number بدلاً من parseFloat للحصول على دقة أفضل
            const quantity = Number(quantityStr);

            if (isNaN(quantity) || !isFinite(quantity) || quantity < 0) {
                totalInput.value = '0.00 ج.م';
                return;
            }

            // حساب الإجمالي بدقة
            const total = Number((selectedProduct.price * quantity).toFixed(2));
            totalInput.value = total.toFixed(2) + ' ج.م';

        } catch (error) {
            console.error('خطأ في حساب الإجمالي:', error);
            totalInput.value = '0.00 ج.م';
        }
    }
}

// اختيار منتج من نتائج البحث
function selectProduct(item) {
    // حفظ المنتج المختار
    Swal.getPopup().selectedProduct = item;
    
    // ملء التفاصيل
    document.getElementById('selected-product-name').value = item.name;
    document.getElementById('selected-product-code').value = item.code || '';
    document.getElementById('selected-product-price').value = item.price + ' ج.م';
    document.getElementById('selected-quantity').value = '1';
    document.getElementById('selected-quantity').max = item.current_stock;
    document.getElementById('selected-total').value = item.price + ' ج.م';
    
    // إظهار قسم التفاصيل
    document.getElementById('product-details').style.display = 'block';
    document.getElementById('search-results').innerHTML = '';
    document.getElementById('product-search').value = item.name;
    
    // إضافة مستمعي الأحداث لحساب الإجمالي
    setupTotalCalculation();
}

// عرض نافذة الدفع والفوترة
function showPaymentModal() {
    // التحقق من وجود عناصر
    if (!document.orderItems || document.orderItems.length === 0) {
        Swal.fire({
            icon: 'warning',
            title: 'لا توجد عناصر',
            text: 'يجب إضافة عنصر واحد على الأقل قبل المتابعة'
        });
        return;
    }
    
    const totalAmount = document.orderItems.reduce((sum, item) => sum + item.total, 0);
    
    Swal.fire({
        title: 'تأكيد الدفع والفوترة',
        html: `
            <div class="text-start">
                <!-- ملخص الطلب -->
                <div class="card mb-3">
                    <div class="card-header">
                        <h6 class="mb-0">ملخص الطلب</h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6"><strong>عدد العناصر:</strong> ${document.orderItems.length}</div>
                            <div class="col-6"><strong>المبلغ الإجمالي:</strong> ${totalAmount.toFixed(2)} ج.م</div>
                        </div>
                    </div>
                </div>
                
                <!-- أرقام الفواتير -->
                <div class="card mb-3">
                    <div class="card-header">
                        <h6 class="mb-0">أرقام الفواتير</h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label class="form-label">رقم الفاتورة الرئيسي *</label>
                            <input type="text" id="invoice-number" class="form-control" required>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">رقم فاتورة إضافي 1</label>
                                <input type="text" id="invoice-number-2" class="form-control">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">رقم فاتورة إضافي 2</label>
                                <input type="text" id="invoice-number-3" class="form-control">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- معلومات الدفع -->
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">معلومات الدفع</h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label class="form-label">المبلغ المدفوع: <span class="text-danger">*</span></label>
                            <input type="number" id="paid-amount" class="form-control" min="0" step="0.01" placeholder="أدخل المبلغ المدفوع" required>
                            <small class="form-text text-muted">يجب إدخال المبلغ المدفوع (يمكن أن يكون صفر إذا لم يتم الدفع بعد)</small>
                        </div>
                        
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" id="payment-verified">
                            <label class="form-check-label" for="payment-verified">
                                تم التحقق من الدفع
                            </label>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">ملاحظات الدفعة:</label>
                            <textarea id="payment-notes" class="form-control" rows="2"></textarea>
                        </div>
                    </div>
                </div>
            </div>
        `,
        showCancelButton: true,
        confirmButtonText: 'حفظ الطلب',
        cancelButtonText: 'إلغاء',
        width: '600px',
        preConfirm: () => {
            // التحقق من عدم وجود إرسال جاري
            if (window.isSubmitting) {
                Swal.showValidationMessage('جاري إرسال الطلب، يرجى الانتظار...');
                return false;
            }

            const invoiceNumber = document.getElementById('invoice-number').value.trim();
            const paidAmountInput = document.getElementById('paid-amount');
            const paidAmount = paidAmountInput.value.trim();

            if (!invoiceNumber) {
                Swal.showValidationMessage('يجب إدخال رقم فاتورة رئيسي');
                return false;
            }

            // التحقق من المبلغ المدفوع - يجب أن يكون قد تم إدخاله (حتى لو كان صفر)
            if (paidAmount === '' || paidAmount === null || paidAmount === undefined) {
                Swal.showValidationMessage('يجب إدخال المبلغ المدفوع ');
                paidAmountInput.focus();
                return false;
            }

            // التحقق من أن القيمة رقم صحيح وليس سالب
            const paidAmountNumber = parseFloat(paidAmount);
            if (isNaN(paidAmountNumber) || paidAmountNumber < 0) {
                Swal.showValidationMessage('المبلغ المدفوع يجب أن يكون رقم صحيح وغير سالب');
                paidAmountInput.focus();
                return false;
            }

            // حفظ بيانات الدفع في الحقول المخفية
            savePaymentData();

            // حفظ العناصر
            syncOrderItemsToFormFields();

            console.log('تم حفظ جميع البيانات، سيتم إرسال النموذج...');

            // إظهار مؤشر التقدم
            setTimeout(() => {
                showProgressIndicator();

                // إرسال النموذج بعد إظهار المؤشر
                setTimeout(() => {
                    const orderForm = document.getElementById('orderForm');
                    if (orderForm) {
                        try {
                            // إضافة معالج للنموذج لمنع الإرسال المتعدد
                            orderForm.addEventListener('submit', function(e) {
                                if (window.isSubmitting && e.type === 'submit') {
                                    console.log('⚠️ منع الإرسال المتعدد');
                                    e.preventDefault();
                                    return false;
                                }
                            });

                            // إضافة timeout للحماية من التعليق
                            const submitTimeout = setTimeout(() => {
                                if (window.isSubmitting) {
                                    console.log('⚠️ انتهت مهلة الإرسال - إعادة تعيين');
                                    hideProgressIndicator();
                                    Swal.fire({
                                        icon: 'error',
                                        title: 'انتهت مهلة الإرسال',
                                        text: 'يرجى المحاولة مرة أخرى',
                                        confirmButtonText: 'موافق'
                                    });
                                }
                            }, 30000); // 30 ثانية

                            console.log('🚀 إرسال النموذج عبر AJAX...');
                            submitFormViaAjax(orderForm);

                        } catch (error) {
                            console.error('❌ خطأ في إرسال النموذج:', error);
                            hideProgressIndicator();
                            Swal.fire({
                                icon: 'error',
                                title: 'خطأ في الإرسال',
                                text: 'حدث خطأ أثناء إرسال النموذج. يرجى المحاولة مرة أخرى.',
                                confirmButtonText: 'موافق'
                            });
                        }
                    } else {
                        console.error('❌ لم يتم العثور على النموذج');
                        hideProgressIndicator();
                        Swal.fire('خطأ', 'لم يتم العثور على النموذج', 'error');
                    }
                }, 500);
            }, 100);

            return true;
        }
    });
}

// حفظ بيانات الدفع في الحقول المخفية
function savePaymentData() {
    const paidAmount = document.getElementById('paid-amount').value || '0';
    const paymentVerified = document.getElementById('payment-verified').checked ? '1' : '0';
    const paymentNotes = document.getElementById('payment-notes').value || '';
    const invoiceNumber = document.getElementById('invoice-number').value || '';
    const invoiceNumber2 = document.getElementById('invoice-number-2').value || '';
    const invoiceNumber3 = document.getElementById('invoice-number-3').value || '';
    
    // حفظ في الحقول المخفية
    document.getElementById('paid_amount').value = paidAmount;
    document.getElementById('payment_verified').value = paymentVerified;
    document.getElementById('payment_notes').value = paymentNotes;
    document.getElementById('invoice_number').value = invoiceNumber;
    document.getElementById('invoice_number_2').value = invoiceNumber2;
    document.getElementById('invoice_number_3').value = invoiceNumber3;
}

// التحقق من صحة النموذج مع تحسينات الأداء
let validationTimeout;
function validateFormRealTime() {
    // استخدام debouncing لتجنب التحقق المتكرر
    clearTimeout(validationTimeout);
    validationTimeout = setTimeout(() => {
        performValidation();
    }, 100);
}

function performValidation() {
    const errors = [];
    let isValid = true;

    // التحقق من الحقول المطلوبة بكفاءة أكبر
    const requiredFields = [
        { id: 'id_customer', name: 'العميل' },
        { id: 'id_salesperson', name: 'البائع' },
        { id: 'id_branch', name: 'الفرع' }
    ];

    // استخدام for loop بدلاً من forEach لتحسين الأداء
    for (let i = 0; i < requiredFields.length; i++) {
        const field = requiredFields[i];
        const element = document.getElementById(field.id);

        if (element) {
            // معالجة خاصة لحقل العميل - التحقق من القيمة الفعلية
            let isEmpty;
            if (field.id === 'id_customer') {
                // التحقق من القيمة الفعلية للحقل
                const value = element.value;
                isEmpty = !value || value === '' || value === 'None' || value === 'null';

                // إذا كان الحقل مخفي، تحقق من وجود قيمة صحيحة
                if (!isEmpty) {
                    console.log('✅ حقل العميل يحتوي على قيمة:', value);
                } else {
                    console.log('❌ حقل العميل فارغ أو غير صحيح:', value);
                }
            } else {
                isEmpty = !element.value || element.value === '';
            }

            if (isEmpty) {
                isValid = false;
                errors.push(field.name);
                if (!element.classList.contains('is-invalid')) {
                    element.classList.add('is-invalid');
                }
            } else {
                if (element.classList.contains('is-invalid')) {
                    element.classList.remove('is-invalid');
                }
            }
        } else {
            // إذا لم يتم العثور على العنصر
            console.log('⚠️ لم يتم العثور على العنصر:', field.id);
        }
    }

    // التحقق من نوع الطلب
    const selectedOrderType = document.querySelector('input[name="order_type_selector"]:checked');
    if (!selectedOrderType) {
        isValid = false;
        errors.push('نوع الطلب');
    }

    // التحقق من حقول العقد إذا كانت مطلوبة
    if (selectedOrderType && ['installation', 'tailoring', 'accessory'].includes(selectedOrderType.value)) {
        const contractNumberField = document.getElementById('id_contract_number');
        if (contractNumberField) {
            const isEmpty = !contractNumberField.value || contractNumberField.value.trim() === '';

            if (isEmpty) {
                isValid = false;
                errors.push('رقم العقد الرئيسي');
                if (!contractNumberField.classList.contains('is-invalid')) {
                    contractNumberField.classList.add('is-invalid');
                }
            } else {
                if (contractNumberField.classList.contains('is-invalid')) {
                    contractNumberField.classList.remove('is-invalid');
                }
            }
        }
    }

    // تحديث حالة الأزرار بكفاءة
    updateButtonStates(isValid, errors);
}

function updateButtonStates(isValid, errors) {
    const addItemBtn = document.getElementById('add-order-item-btn-custom');
    const saveOrderBtn = document.getElementById('save-order-btn-custom');
    const hasItems = document.orderItems && document.orderItems.length > 0;
    
    if (addItemBtn) {
        addItemBtn.disabled = !isValid;
    }
    
    if (saveOrderBtn) {
        saveOrderBtn.disabled = !isValid || !hasItems;
    }
    
    return isValid;
}

// إعداد أحداث النموذج
function setupFormEvents() {
    // أحداث الراديو
    const styledRadios = document.querySelectorAll('.styled-radio');
    styledRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateFormFields();

            // تحديث فوري للراديو الأصلي
            const selectedType = this.value;
            const realRadios = document.querySelectorAll('input[name="selected_types"]');
            realRadios.forEach(realRadio => {
                realRadio.checked = (realRadio.value === selectedType);

                // إطلاق حدث change على الراديو الأصلي
                if (realRadio.checked) {
                    const changeEvent = new Event('change', { bubbles: true });
                    realRadio.dispatchEvent(changeEvent);
                }
            });

            console.log('✅ تم تحديث selected_types إلى:', selectedType);
            console.log('✅ عدد الراديو المحدث:', realRadios.length);
        });
    });
    
    // زر إضافة العناصر
    const addItemBtn = document.getElementById('add-order-item-btn-custom');
    if (addItemBtn) {
        addItemBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showAddItemModal();
        });
    }
    
    // زر حفظ الطلب
    const saveOrderBtn = document.getElementById('save-order-btn-custom');
    if (saveOrderBtn) {
        saveOrderBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showPaymentModal();
        });
    }
    
    // مستمعات التحقق الفوري
    const fieldsToWatch = ['id_customer', 'id_salesperson', 'id_branch', 'id_contract_number'];
    fieldsToWatch.forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element) {
            element.addEventListener('change', validateFormRealTime);
            element.addEventListener('input', validateFormRealTime);
        }
    });
    
    // مستمع لـ Select2
    $('#customer_search_select').on('select2:select select2:clear', function() {
        setTimeout(validateFormRealTime, 100);
    });
}

// دالة لمنع مغادرة الصفحة أثناء الإرسال
function preventPageLeave() {
    window.addEventListener('beforeunload', function(e) {
        if (window.isSubmitting) {
            const message = 'جاري إرسال الطلب، هل أنت متأكد من مغادرة الصفحة؟';
            e.preventDefault();
            e.returnValue = message;
            return message;
        }
    });
}

// دالة لتعطيل جميع الأزرار أثناء الإرسال
function disableFormButtons() {
    const buttons = document.querySelectorAll('button, input[type="submit"]');
    buttons.forEach(button => {
        if (window.isSubmitting) {
            button.disabled = true;
            button.classList.add('disabled');
        } else {
            button.disabled = false;
            button.classList.remove('disabled');
        }
    });
}

// تهيئة النظام عند تحميل الصفحة
// دالة لإرسال النموذج عبر AJAX
function submitFormViaAjax(form) {
    const formData = new FormData(form);

    // إضافة header للـ AJAX
    fetch(form.action || window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            return response.json().then(data => {
                throw new Error(data.message || 'حدث خطأ في الخادم');
            });
        }
    })
    .then(data => {
        console.log('✅ تم إرسال النموذج بنجاح:', data);
        hideProgressIndicator();

        if (data.success) {
            // نجح الإرسال
            Swal.fire({
                icon: 'success',
                title: 'تم بنجاح!',
                text: data.message,
                confirmButtonText: 'موافق'
            }).then(() => {
                // إعادة توجيه للصفحة المحددة
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.reload();
                }
            });
        } else {
            // فشل الإرسال
            let errorMessage = data.message || 'حدث خطأ غير معروف';

            // إضافة تفاصيل الأخطاء إذا وجدت
            if (data.errors) {
                errorMessage += '\n\nتفاصيل الأخطاء:\n';
                for (const [field, errors] of Object.entries(data.errors)) {
                    errorMessage += `- ${field}: ${errors.join(', ')}\n`;
                }
            }

            Swal.fire({
                icon: 'error',
                title: 'خطأ في النموذج',
                text: errorMessage,
                confirmButtonText: 'موافق'
            });
        }
    })
    .catch(error => {
        console.error('❌ خطأ في إرسال النموذج:', error);
        hideProgressIndicator();

        Swal.fire({
            icon: 'error',
            title: 'خطأ في الإرسال',
            text: error.message || 'حدث خطأ أثناء إرسال النموذج. يرجى المحاولة مرة أخرى.',
            confirmButtonText: 'موافق'
        });
    });
}

// معالج أخطاء JavaScript العامة
window.addEventListener('error', function(e) {
    if (window.isSubmitting) {
        console.error('❌ خطأ JavaScript أثناء الإرسال:', e.error);
        hideProgressIndicator();
        Swal.fire({
            icon: 'error',
            title: 'حدث خطأ',
            text: 'حدث خطأ غير متوقع. يرجى إعادة تحميل الصفحة والمحاولة مرة أخرى.',
            confirmButtonText: 'إعادة تحميل',
            allowOutsideClick: false
        }).then(() => {
            window.location.reload();
        });
    }
});

// معالج لأخطاء الشبكة
window.addEventListener('unhandledrejection', function(e) {
    if (window.isSubmitting) {
        console.error('❌ خطأ شبكة أثناء الإرسال:', e.reason);
        hideProgressIndicator();
        Swal.fire({
            icon: 'error',
            title: 'خطأ في الاتصال',
            text: 'حدث خطأ في الاتصال. يرجى التحقق من الإنترنت والمحاولة مرة أخرى.',
            confirmButtonText: 'موافق'
        });
    }
});

// دالة لتحسين معالجة القيم العشرية على الهواتف المحمولة
function setupMobileDecimalSupport() {
    // التحقق من كون الجهاز محمول
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
                     window.innerWidth <= 768;

    if (isMobile) {
        console.log('🔧 تطبيق تحسينات الهواتف المحمولة للقيم العشرية...');

        // تحسين جميع حقول الأرقام
        const numberInputs = document.querySelectorAll('input[type="number"]');
        numberInputs.forEach(input => {
            // إضافة inputmode للحصول على لوحة مفاتيح عشرية
            input.setAttribute('inputmode', 'decimal');

            // إضافة مستمع للتحقق من القيم العشرية
            input.addEventListener('input', function(e) {
                const value = e.target.value;

                // السماح بالقيم العشرية والأرقام فقط
                if (value && !/^\d*\.?\d*$/.test(value)) {
                    // إزالة الأحرف غير المسموحة
                    e.target.value = value.replace(/[^\d.]/g, '');
                }

                // منع أكثر من نقطة عشرية واحدة
                const parts = e.target.value.split('.');
                if (parts.length > 2) {
                    e.target.value = parts[0] + '.' + parts.slice(1).join('');
                }

                // تحديد عدد المنازل العشرية حسب نوع الحقل
                if (e.target.classList.contains('item-quantity') || e.target.id === 'selected-quantity') {
                    // حقول الكمية: 3 منازل عشرية كحد أقصى
                    if (parts[1] && parts[1].length > 3) {
                        e.target.value = parts[0] + '.' + parts[1].substring(0, 3);
                    }
                } else if (e.target.classList.contains('item-price')) {
                    // حقول السعر: منزلتان عشريتان كحد أقصى
                    if (parts[1] && parts[1].length > 2) {
                        e.target.value = parts[0] + '.' + parts[1].substring(0, 2);
                    }
                }
            });

            // إضافة مستمع للتحقق عند فقدان التركيز
            input.addEventListener('blur', function(e) {
                const value = parseFloat(e.target.value);
                if (!isNaN(value) && isFinite(value)) {
                    // تنسيق القيمة حسب نوع الحقل
                    if (e.target.classList.contains('item-quantity') || e.target.id === 'selected-quantity') {
                        e.target.value = value.toFixed(3).replace(/\.?0+$/, '');
                    } else if (e.target.classList.contains('item-price')) {
                        e.target.value = value.toFixed(2);
                    }
                }
            });
        });

        console.log(`✅ تم تطبيق تحسينات الهواتف المحمولة على ${numberInputs.length} حقل رقمي`);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('تهيئة نموذج الطلب المبسط...');

    // تطبيق تحسينات الهواتف المحمولة
    setupMobileDecimalSupport();

    // تهيئة Select2
    initializeCustomerSearch();

    // إعداد أحداث النموذج
    setupFormEvents();

    // تحديث الحقول الأولي
    updateFormFields();

    // تحديث جدول العناصر
    updateLiveOrderItemsTable();

    // التحقق من حقل العميل المحدد مسبقاً
    const customerField = document.getElementById('id_customer');
    const hiddenCustomerBackup = document.getElementById('hidden_customer_backup');

    // إذا كان هناك حقل احتياطي مخفي، استخدمه لتعيين قيمة الحقل الأصلي
    if (hiddenCustomerBackup && hiddenCustomerBackup.value && customerField) {
        console.log('✅ تم العثور على حقل احتياطي للعميل:', hiddenCustomerBackup.value);
        customerField.value = hiddenCustomerBackup.value;
        customerField.classList.remove('is-invalid');
        customerField.classList.add('is-valid');
    } else if (customerField && customerField.value) {
        console.log('✅ تم العثور على عميل محدد مسبقاً:', customerField.value);
        // إزالة علامة invalid إذا كانت موجودة
        customerField.classList.remove('is-invalid');
        customerField.classList.add('is-valid');
    }

    // التحقق الأولي
    setTimeout(validateFormRealTime, 500);

    // منع مغادرة الصفحة أثناء الإرسال
    preventPageLeave();

    console.log('تم تهيئة النموذج بنجاح');
});

// ==================== دوال إدارة العقد الإلكتروني ====================

/**
 * التعامل مع النقر على زر إنشاء عقد إلكتروني
 */
function handleElectronicContractClick() {
    const orderItems = document.orderItems || [];

    console.log('🔍 عدد عناصر الطلب الحالية:', orderItems.length);

    if (orderItems.length === 0) {
        Swal.fire({
            icon: 'warning',
            title: 'تنبيه',
            html: `
                <div class="text-end">
                    <p class="mb-3">لإنشاء عقد إلكتروني، يجب إضافة عناصر للطلب أولاً.</p>
                    <p class="mb-0"><strong>هل تريد إضافة عناصر الآن؟</strong></p>
                </div>
            `,
            showCancelButton: true,
            confirmButtonText: '<i class="fas fa-plus me-1"></i> إضافة عناصر',
            cancelButtonText: 'إلغاء',
            confirmButtonColor: '#28a745',
            cancelButtonColor: '#6c757d',
            reverseButtons: true
        }).then((result) => {
            if (result.isConfirmed) {
                // التمرير إلى قسم إضافة العناصر
                const addItemButton = document.getElementById('add-order-item-btn-custom');
                if (addItemButton) {
                    addItemButton.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // تسليط الضوء على الزر
                    addItemButton.classList.add('btn-pulse');
                    setTimeout(() => {
                        addItemButton.classList.remove('btn-pulse');
                    }, 2000);
                }
            }
        });
    } else {
        // فتح المودال لإضافة تفاصيل الستائر
        console.log('✅ فتح مودال العقد الإلكتروني');
        openElectronicContractModal();
    }
}

/**
 * فتح مودال العقد الإلكتروني
 */
function openElectronicContractModal() {
    const modal = new bootstrap.Modal(document.getElementById('electronicContractModal'));
    modal.show();

    // إعادة تعيين البيانات
    window.contractCurtains = [];
    window.curtainCounter = 0;

    // إضافة ستارة واحدة افتراضياً
    addCurtainToModal();
}

/**
 * متغير عالمي لتخزين بيانات الستائر
 */
window.contractCurtains = [];
window.curtainCounter = 0;

/**
 * إضافة ستارة جديدة للمودال
 */
function addCurtainToModal() {
    const template = document.getElementById('curtain-modal-template');
    if (!template) {
        console.error('❌ لم يتم العثور على قالب الستارة');
        return;
    }

    const clone = template.content.cloneNode(true);
    const card = clone.querySelector('.curtain-card-modal');

    window.curtainCounter++;
    const curtainIndex = window.curtainCounter - 1;

    card.dataset.curtainIndex = curtainIndex;
    card.querySelector('.curtain-number').textContent = window.curtainCounter;

    // إضافة بيانات الستارة للمصفوفة
    window.contractCurtains.push({
        room_name: '',
        width: '',
        height: '',
        fabrics: [],
        accessories: {}
    });

    // إضافة معالجات الأحداث للحقول
    const roomNameInput = card.querySelector('.room-name-input');
    const widthInput = card.querySelector('.width-input');
    const heightInput = card.querySelector('.height-input');

    roomNameInput.addEventListener('input', (e) => {
        window.contractCurtains[curtainIndex].room_name = e.target.value;
    });

    widthInput.addEventListener('input', (e) => {
        window.contractCurtains[curtainIndex].width = e.target.value;
    });

    heightInput.addEventListener('input', (e) => {
        window.contractCurtains[curtainIndex].height = e.target.value;
    });

    // إضافة قماش واحد افتراضياً
    const fabricsContainer = card.querySelector('.fabrics-container');
    addFabricToContainer(fabricsContainer, curtainIndex);

    // إضافة الإكسسوارات
    addAccessoriesToCurtain(card, curtainIndex);

    // إضافة البطاقة للقائمة
    const curtainsList = document.getElementById('curtains-list-modal');
    if (curtainsList) {
        curtainsList.appendChild(card);
    }

    console.log(`✅ تم إضافة ستارة ${window.curtainCounter}`);
}

/**
 * إضافة قماش لحاوية الأقمشة
 */
function addFabricToContainer(container, curtainIndex) {
    const template = document.getElementById('fabric-modal-template');
    if (!template) return;

    const clone = template.content.cloneNode(true);
    const fabricItem = clone.querySelector('.fabric-item-modal');

    const fabricIndex = window.contractCurtains[curtainIndex].fabrics.length;
    fabricItem.dataset.fabricIndex = fabricIndex;
    fabricItem.querySelector('.fabric-number').textContent = fabricIndex + 1;

    // إضافة بيانات القماش للمصفوفة
    window.contractCurtains[curtainIndex].fabrics.push({
        type: '',
        name: '',
        fabric_id: '',
        pieces: 1,
        meters: '',
        tailoring: ''
    });

    // ملء قائمة اسم القماش من عناصر الطلب
    const nameSelect = fabricItem.querySelector('.fabric-name-input');
    const orderItems = document.orderItems || [];

    // مسح الخيارات الموجودة (ما عدا الخيار الافتراضي)
    while (nameSelect.options.length > 1) {
        nameSelect.remove(1);
    }

    // إضافة عناصر الطلب
    orderItems.forEach(item => {
        const option = document.createElement('option');
        option.value = item.product_id;
        option.textContent = `${item.name} (متوفر: ${item.quantity})`;
        nameSelect.appendChild(option);
    });

    // إضافة معالجات الأحداث
    const typeInput = fabricItem.querySelector('.fabric-type-input');
    const piecesInput = fabricItem.querySelector('.fabric-pieces-input');
    const metersInput = fabricItem.querySelector('.fabric-meters-input');
    const tailoringInput = fabricItem.querySelector('.fabric-tailoring-input');

    typeInput.addEventListener('change', (e) => {
        window.contractCurtains[curtainIndex].fabrics[fabricIndex].type = e.target.value;
    });

    nameSelect.addEventListener('change', (e) => {
        const selectedOption = e.target.options[e.target.selectedIndex];
        window.contractCurtains[curtainIndex].fabrics[fabricIndex].fabric_id = e.target.value;
        window.contractCurtains[curtainIndex].fabrics[fabricIndex].name = selectedOption.textContent;
    });

    piecesInput.addEventListener('input', (e) => {
        window.contractCurtains[curtainIndex].fabrics[fabricIndex].pieces = e.target.value;
    });

    metersInput.addEventListener('input', (e) => {
        window.contractCurtains[curtainIndex].fabrics[fabricIndex].meters = e.target.value;
    });

    tailoringInput.addEventListener('change', (e) => {
        window.contractCurtains[curtainIndex].fabrics[fabricIndex].tailoring = e.target.value;
    });

    container.appendChild(fabricItem);
}

/**
 * إضافة قماش جديد للستارة
 */
function addFabricToModal(button) {
    const card = button.closest('.curtain-card-modal');
    const curtainIndex = parseInt(card.dataset.curtainIndex);
    const container = card.querySelector('.fabrics-container');

    addFabricToContainer(container, curtainIndex);
}

/**
 * حذف قماش
 */
function removeFabricFromModal(button) {
    const fabricItem = button.closest('.fabric-item-modal');
    const card = button.closest('.curtain-card-modal');
    const curtainIndex = parseInt(card.dataset.curtainIndex);
    const fabricIndex = parseInt(fabricItem.dataset.fabricIndex);

    // حذف من المصفوفة
    window.contractCurtains[curtainIndex].fabrics.splice(fabricIndex, 1);

    // حذف من DOM
    fabricItem.remove();

    // إعادة ترقيم الأقمشة المتبقية
    const remainingFabrics = card.querySelectorAll('.fabric-item-modal');
    remainingFabrics.forEach((item, index) => {
        item.dataset.fabricIndex = index;
        item.querySelector('.fabric-number').textContent = index + 1;
    });
}

/**
 * إضافة الإكسسوارات للستارة
 */
function addAccessoriesToCurtain(card, curtainIndex) {
    const accessoriesGrid = card.querySelector('.accessories-grid-modal');
    if (!accessoriesGrid) return;

    const orderItems = document.orderItems || [];

    const accessories = [
        {key: 'wood', label: 'خشب', icon: 'tree', hasSelect: false},
        {key: 'track', label: 'مجرى', icon: 'grip-lines', hasSelect: true},
        {key: 'pipe', label: 'مواسير', icon: 'circle', hasSelect: true},
        {key: 'bracket', label: 'كوابيل', icon: 'angle-double-right', hasSelect: true},
        {key: 'finial', label: 'نهايات', icon: 'circle-notch', hasSelect: true},
        {key: 'ring', label: 'طبة', icon: 'ring', hasSelect: true},
        {key: 'hanger', label: 'شماعات', icon: 'paperclip', hasSelect: true},
        {key: 'valance', label: 'فرانشة', icon: 'window-maximize', hasSelect: true}
    ];

    accessories.forEach(acc => {
        const accDiv = document.createElement('div');
        accDiv.className = 'col-md-3';

        // إنشاء حقل النوع (إما select أو input)
        let typeField = '';
        if (acc.hasSelect) {
            typeField = `
                <select class="form-select form-select-sm mb-1 acc-type">
                    <option value="">-- اختر النوع --</option>
                </select>
            `;
        } else {
            typeField = `<input type="text" class="form-control form-control-sm mb-1 acc-type" placeholder="النوع">`;
        }

        accDiv.innerHTML = `
            <div class="border rounded p-2">
                <div class="form-check mb-2">
                    <input class="form-check-input acc-checkbox" type="checkbox" id="acc-${curtainIndex}-${acc.key}">
                    <label class="form-check-label" for="acc-${curtainIndex}-${acc.key}">
                        <i class="fas fa-${acc.icon} me-1"></i>${acc.label}
                    </label>
                </div>
                <div class="acc-fields" style="display: none;">
                    ${typeField}
                    <input type="number" class="form-control form-control-sm acc-quantity" placeholder="العدد" min="0">
                </div>
            </div>
        `;

        const checkbox = accDiv.querySelector('.acc-checkbox');
        const fields = accDiv.querySelector('.acc-fields');
        const typeInput = accDiv.querySelector('.acc-type');
        const quantityInput = accDiv.querySelector('.acc-quantity');

        // ملء القائمة المنسدلة إذا كانت موجودة
        if (acc.hasSelect && typeInput.tagName === 'SELECT') {
            orderItems.forEach(item => {
                const option = document.createElement('option');
                option.value = item.product_id;
                option.textContent = `${item.name} (متوفر: ${item.quantity})`;
                typeInput.appendChild(option);
            });
        }

        checkbox.addEventListener('change', (e) => {
            fields.style.display = e.target.checked ? 'block' : 'none';
            if (!e.target.checked) {
                delete window.contractCurtains[curtainIndex].accessories[acc.key];
                typeInput.value = '';
                quantityInput.value = '';
            }
        });

        typeInput.addEventListener(acc.hasSelect ? 'change' : 'input', (e) => {
            if (!window.contractCurtains[curtainIndex].accessories[acc.key]) {
                window.contractCurtains[curtainIndex].accessories[acc.key] = {};
            }
            if (acc.hasSelect) {
                window.contractCurtains[curtainIndex].accessories[acc.key].type_id = e.target.value;
                const selectedOption = e.target.options[e.target.selectedIndex];
                window.contractCurtains[curtainIndex].accessories[acc.key].type = selectedOption.textContent;
            } else {
                window.contractCurtains[curtainIndex].accessories[acc.key].type = e.target.value;
            }
        });

        quantityInput.addEventListener('input', (e) => {
            if (!window.contractCurtains[curtainIndex].accessories[acc.key]) {
                window.contractCurtains[curtainIndex].accessories[acc.key] = {};
            }
            window.contractCurtains[curtainIndex].accessories[acc.key].quantity = e.target.value;
        });

        accessoriesGrid.appendChild(accDiv);
    });
}

/**
 * حذف ستارة
 */
function removeCurtainModal(button) {
    const card = button.closest('.curtain-card-modal');
    const curtainIndex = parseInt(card.dataset.curtainIndex);

    Swal.fire({
        icon: 'warning',
        title: 'تأكيد الحذف',
        text: `هل تريد حذف الستارة ${curtainIndex + 1}؟`,
        showCancelButton: true,
        confirmButtonText: 'نعم، احذف',
        cancelButtonText: 'إلغاء',
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d'
    }).then((result) => {
        if (result.isConfirmed) {
            // حذف من المصفوفة
            window.contractCurtains.splice(curtainIndex, 1);

            // حذف من DOM
            card.remove();

            // إعادة ترقيم الستائر المتبقية
            const remainingCurtains = document.querySelectorAll('.curtain-card-modal');
            remainingCurtains.forEach((c, index) => {
                c.dataset.curtainIndex = index;
                c.querySelector('.curtain-number').textContent = index + 1;
            });

            window.curtainCounter = remainingCurtains.length;

            Swal.fire({
                icon: 'success',
                title: 'تم الحذف',
                text: 'تم حذف الستارة بنجاح',
                timer: 1500,
                showConfirmButton: false
            });
        }
    });
}