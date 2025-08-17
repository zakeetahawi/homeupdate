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
        didOpen: () => {
            startProgressAnimation();
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
    disableFormButtons(); // إعادة تفعيل الأزرار
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
        var customerData = e.params.data.customer;
        if (customerData) {
            $('#id_customer').val(customerData.id);
            validateFormRealTime();
        }
    });

    // عند إزالة اختيار العميل
    searchSelect.on('select2:clear', function (e) {
        $('#id_customer').val('');
        validateFormRealTime();
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
            if (data.customer) {
                window.currentCustomer = data.customer;
                console.log('تم اختيار العميل:', data.customer);

                // تحديث الحقول إذا لزم الأمر
                updateFormFields();
            }
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

    // إظهار/إخفاء حقول العقد
    const contractFields = document.querySelectorAll('.contract-field');
    const contractFileField = document.querySelector('.contract-file-field');
    const relatedInspectionField = document.querySelector('.related-inspection-field');
    
    contractFields.forEach(field => {
        if (field) field.style.display = showForContract ? 'block' : 'none';
    });
    
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

        // حساب الإجمالي مرة واحدة
        const totalAmount = document.orderItems.reduce((sum, item) => sum + item.total, 0);

        // إنشاء العناصر باستخدام template literals محسنة
        const headerHtml = `
            <div class="card">
                <div class="card-header bg-primary text-white">
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
                                    <th>الإجمالي</th>
                                    <th>الإجراءات</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        // إنشاء صفوف الجدول بكفاءة أكبر
        const rowsHtml = document.orderItems.map((item, idx) => `
            <tr>
                <td><span class="badge bg-primary">${idx+1}</span></td>
                <td>
                    <strong>${item.name}</strong>
                    ${item.code ? `<br><small class="text-muted">كود: ${item.code}</small>` : ''}
                </td>
                <td><span class="badge bg-info">${item.quantity}</span></td>
                <td>${item.unit_price} ج.م</td>
                <td><strong class="text-success">${item.total.toFixed(2)} ج.م</strong></td>
                <td>
                    <button type="button" class="btn btn-sm btn-danger"
                            onclick="removeOrderItem(${idx})" title="حذف العنصر">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');

        const footerHtml = `
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="card-footer text-center bg-success text-white">
                    <strong style="font-size: 1.1rem;">
                        <i class="fas fa-calculator me-2"></i>
                        الإجمالي: ${totalAmount.toFixed(2)} ج.م
                    </strong>
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
                            <input type="number" id="selected-quantity" class="form-control" min="1" value="1">
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
            const quantity = parseInt(document.getElementById('selected-quantity').value) || 1;
            const notes = document.getElementById('selected-notes').value || '';
            
            if (!selectedProduct) {
                Swal.showValidationMessage('يرجى اختيار منتج أولاً');
                return false;
            }
            
            if (quantity < 1) {
                Swal.showValidationMessage('يرجى إدخال كمية صحيحة');
                return false;
            }
            
            // التحقق من عدم تكرار المنتج
            const exists = document.orderItems.find(x => x.product_id === selectedProduct.id);
            if (exists) {
                Swal.showValidationMessage('تمت إضافة هذا المنتج بالفعل!');
                return false;
            }
            
            // إضافة العنصر
            document.orderItems.push({
                product_id: selectedProduct.id,
                name: selectedProduct.name,
                code: selectedProduct.code || '',
                unit_price: selectedProduct.price,
                quantity: quantity,
                total: (selectedProduct.price * quantity),
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
        const selectedProduct = Swal.getPopup().selectedProduct;
        if (selectedProduct) {
            const quantity = parseInt(this.value) || 1;
            const total = selectedProduct.price * quantity;
            totalInput.value = total.toFixed(2) + ' ج.م';
        }
    });
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
                            <label class="form-label">المبلغ المدفوع:</label>
                            <input type="number" id="paid-amount" class="form-control" min="0" value="0" step="0.01">
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

            if (!invoiceNumber) {
                Swal.showValidationMessage('يجب إدخال رقم فاتورة رئيسي');
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
                        // إضافة معالج للنموذج لمنع الإرسال المتعدد
                        orderForm.addEventListener('submit', function(e) {
                            if (window.isSubmitting) {
                                e.preventDefault();
                                return false;
                            }
                        });

                        orderForm.submit();
                    } else {
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
            const isEmpty = !element.value || element.value === '';

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
document.addEventListener('DOMContentLoaded', function() {
    console.log('تهيئة نموذج الطلب المبسط...');

    // تهيئة Select2
    initializeCustomerSearch();

    // إعداد أحداث النموذج
    setupFormEvents();

    // تحديث الحقول الأولي
    updateFormFields();

    // تحديث جدول العناصر
    updateLiveOrderItemsTable();

    // التحقق الأولي
    setTimeout(validateFormRealTime, 500);

    // منع مغادرة الصفحة أثناء الإرسال
    preventPageLeave();

    console.log('تم تهيئة النموذج بنجاح');
});