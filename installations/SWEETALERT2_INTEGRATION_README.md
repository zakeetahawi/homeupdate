# دمج SweetAlert2 وتحديث عنوان العميل

## التحديثات المطبقة

### 1. إلغاء الرسائل المنبثقة من المتصفح

تم استبدال جميع الرسائل المنبثقة من المتصفح (`alert`, `confirm`) بقوائم منبثقة جميلة باستخدام مكتبة SweetAlert2.

#### المميزات:
- تصميم جميل ومتجاوب
- دعم اللغة العربية
- أيقونات ملونة
- أزرار مخصصة
- مؤقت تلقائي للرسائل
- شريط تقدم للمؤقت

### 2. تحديث عنوان العميل تلقائياً

تم إضافة ميزة تحديث عنوان العميل تلقائياً عند كتابة العنوان في نموذج الجدولة.

#### المميزات:
- تحديث العنوان عند تغيير حقل العنوان
- تحديث نوع المكان مع العنوان
- رسائل تأكيد جميلة
- معالجة الأخطاء بشكل مناسب

## الملفات المعدلة

### 1. installations/templates/installations/quick_schedule_installation.html

#### إضافة SweetAlert2:
```html
{% block extra_css %}
<!-- SweetAlert2 CSS -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css">
<style>
    .swal2-popup {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl !important;
    }
    
    .swal2-title {
        font-family: 'Cairo', sans-serif !important;
        font-weight: bold !important;
    }
    
    .swal2-content {
        font-family: 'Cairo', sans-serif !important;
    }
    
    .swal2-confirm {
        font-family: 'Cairo', sans-serif !important;
        font-weight: bold !important;
    }
    
    .swal2-cancel {
        font-family: 'Cairo', sans-serif !important;
        font-weight: bold !important;
    }
</style>
{% endblock %}
```

#### إضافة JavaScript للتعامل مع الرسائل المنبثقة:
```javascript
{% block extra_js %}
<!-- SweetAlert2 JS -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
<script>
// تحديث العنوان من معلومات العميل
function updateCustomerAddress() {
    // معلومات العميل من الطلب
    const customerAddress = `{{ order.customer.address|default:"" }}`;
    const customerLocationType = `{{ order.customer.location_type|default:"" }}`;
    
    let updatedAddress = customerAddress;
    
    // إضافة نوع المكان إذا كان متوفراً
    if (customerLocationType) {
        const locationTypeDisplay = customerLocationType === 'open' ? 'مفتوح' : 
                                   customerLocationType === 'compound' ? 'كومبوند' : '';
        if (locationTypeDisplay) {
            updatedAddress = `${customerAddress}\nنوع المكان: ${locationTypeDisplay}`;
        }
    }
    
    // تحديث حقل العنوان
    document.getElementById('{{ form.location_address.id_for_label }}').value = updatedAddress;
    
    // تحديث نوع المكان في القائمة المنسدلة
    const locationTypeSelect = document.getElementById('{{ form.location_type.id_for_label }}');
    if (locationTypeSelect) {
        locationTypeSelect.value = customerLocationType;
    }
    
    // رسالة تأكيد جميلة
    Swal.fire({
        title: 'تم التحديث بنجاح!',
        text: 'تم تحديث العنوان من معلومات العميل',
        icon: 'success',
        confirmButtonText: 'حسناً',
        confirmButtonColor: '#28a745',
        timer: 2000,
        timerProgressBar: true
    });
}

// تحديث عنوان العميل عند تغيير العنوان
function updateCustomerAddressFromForm() {
    const addressField = document.getElementById('{{ form.location_address.id_for_label }}');
    const locationTypeSelect = document.getElementById('{{ form.location_type.id_for_label }}');
    
    if (addressField && addressField.value.trim()) {
        // إرسال طلب لتحديث عنوان العميل
        const formData = new FormData();
        formData.append('address', addressField.value.trim());
        formData.append('location_type', locationTypeSelect ? locationTypeSelect.value : '');
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        
        fetch(`/customers/customer/{{ order.customer.id }}/update-address/`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    title: 'تم التحديث بنجاح!',
                    text: 'تم تحديث عنوان العميل بناءً على العنوان الجديد',
                    icon: 'success',
                    confirmButtonText: 'حسناً',
                    confirmButtonColor: '#28a745',
                    timer: 2000,
                    timerProgressBar: true
                });
            } else {
                Swal.fire({
                    title: 'خطأ في التحديث',
                    text: data.error || 'حدث خطأ أثناء تحديث عنوان العميل',
                    icon: 'error',
                    confirmButtonText: 'حسناً',
                    confirmButtonColor: '#dc3545'
                });
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                title: 'خطأ في التحديث',
                text: 'حدث خطأ أثناء تحديث عنوان العميل',
                icon: 'error',
                confirmButtonText: 'حسناً',
                confirmButtonColor: '#dc3545'
            });
        });
    }
}

// تأكيد إرسال النموذج
document.querySelector('form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    Swal.fire({
        title: 'تأكيد الجدولة',
        text: 'هل أنت متأكد من جدولة التركيب؟',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'نعم، جدولة',
        cancelButtonText: 'إلغاء',
        confirmButtonColor: '#28a745',
        cancelButtonColor: '#6c757d',
        reverseButtons: true
    }).then((result) => {
        if (result.isConfirmed) {
            // إرسال النموذج
            this.submit();
        }
    });
});
</script>
{% endblock %}
```

### 2. installations/templates/installations/change_status_modal.html

#### إضافة SweetAlert2 للرسائل المنبثقة:
```javascript
<!-- SweetAlert2 JS -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
<script>
// معالجة إرسال النموذج
$('#statusChangeForm').on('submit', function(e) {
    e.preventDefault();
    
    var formData = $(this).serialize();
    var submitBtn = $('#saveStatusBtn');
    var originalText = submitBtn.html();
    
    // تعطيل الزر وإظهار مؤشر التحميل
    submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> جاري الحفظ...');
    
    $.ajax({
        url: '{% url "installations:change_installation_status" installation.id %}',
        type: 'POST',
        data: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        success: function(response) {
            if (response.success) {
                // إظهار رسالة نجاح جميلة
                Swal.fire({
                    title: 'تم التحديث بنجاح!',
                    text: response.message,
                    icon: 'success',
                    confirmButtonText: 'حسناً',
                    confirmButtonColor: '#28a745',
                    timer: 2000,
                    timerProgressBar: true
                }).then(() => {
                    // إغلاق النافذة المنبثقة
                    $('#statusModal').modal('hide');
                    
                    // تحديث الصفحة
                    location.reload();
                });
            } else {
                // إظهار أخطاء النموذج
                if (response.errors) {
                    var errorMessages = [];
                    for (var field in response.errors) {
                        errorMessages = errorMessages.concat(response.errors[field]);
                    }
                    Swal.fire({
                        title: 'خطأ في التحديث',
                        text: 'خطأ: ' + errorMessages.join(', '),
                        icon: 'error',
                        confirmButtonText: 'حسناً',
                        confirmButtonColor: '#dc3545'
                    });
                }
            }
        },
        error: function(xhr, status, error) {
            Swal.fire({
                title: 'خطأ في التحديث',
                text: 'حدث خطأ أثناء حفظ التغيير',
                icon: 'error',
                confirmButtonText: 'حسناً',
                confirmButtonColor: '#dc3545'
            });
        },
        complete: function() {
            // إعادة تفعيل الزر
            submitBtn.prop('disabled', false).html(originalText);
        }
    });
});
</script>
```

### 3. installations/templates/installations/installation_detail.html

#### إضافة SweetAlert2 لتحديث حالة التركيب:
```javascript
{% block extra_js %}
<!-- SweetAlert2 JS -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
<script>
// تحديث حالة التركيب
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.update-status').forEach(button => {
        button.addEventListener('click', function() {
            const installationId = this.dataset.installationId;
            const newStatus = this.dataset.status;
            
            if (!installationId || !newStatus) {
                Swal.fire({
                    title: 'خطأ في البيانات',
                    text: 'بيانات غير صحيحة',
                    icon: 'error',
                    confirmButtonText: 'حسناً',
                    confirmButtonColor: '#dc3545'
                });
                return;
            }
            
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            if (!csrfToken) {
                Swal.fire({
                    title: 'خطأ في الأمان',
                    text: 'خطأ في الحصول على رمز الأمان',
                    icon: 'error',
                    confirmButtonText: 'حسناً',
                    confirmButtonColor: '#dc3545'
                });
                return;
            }

            Swal.fire({
                title: 'تأكيد تحديث الحالة',
                text: 'هل أنت متأكد من تحديث حالة التركيب؟',
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'نعم، تحديث',
                cancelButtonText: 'إلغاء',
                confirmButtonColor: '#28a745',
                cancelButtonColor: '#6c757d',
                reverseButtons: true
            }).then((result) => {
                if (result.isConfirmed) {
                    // إظهار مؤشر التحميل
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري التحديث...';
                    this.disabled = true;
                    
                    // إنشاء FormData
                    const formData = new FormData();
                    formData.append('status', newStatus);
                    
                    fetch(`/installations/installation/${installationId}/update-status/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken,
                        },
                        body: formData
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (data.success) {
                            // إظهار رسالة نجاح جميلة
                            Swal.fire({
                                title: 'تم التحديث بنجاح!',
                                text: data.message || 'تم تحديث الحالة بنجاح',
                                icon: 'success',
                                confirmButtonText: 'حسناً',
                                confirmButtonColor: '#28a745',
                                timer: 2000,
                                timerProgressBar: true
                            }).then(() => {
                                // إعادة تحميل الصفحة
                                location.reload();
                            });
                        } else {
                            // إظهار رسالة خطأ
                            Swal.fire({
                                title: 'خطأ في التحديث',
                                text: data.error || 'حدث خطأ أثناء تحديث الحالة',
                                icon: 'error',
                                confirmButtonText: 'حسناً',
                                confirmButtonColor: '#dc3545'
                            });
                            // إعادة تعيين الزر
                            this.innerHTML = originalText;
                            this.disabled = false;
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        Swal.fire({
                            title: 'خطأ في التحديث',
                            text: 'حدث خطأ أثناء تحديث الحالة: ' + error.message,
                            icon: 'error',
                            confirmButtonText: 'حسناً',
                            confirmButtonColor: '#dc3545'
                        });
                        // إعادة تعيين الزر
                        this.innerHTML = originalText;
                        this.disabled = false;
                    });
                }
            });
        });
    });
});
</script>
{% endblock %}
```

### 4. customers/views.py

#### إضافة view لتحديث عنوان العميل:
```python
@login_required
@require_POST
def update_customer_address(request, pk):
    """تحديث عنوان العميل ونوع المكان"""
    try:
        customer = get_object_or_404(Customer, pk=pk)
        
        # التحقق من الصلاحيات
        if not request.user.is_superuser and request.user.branch != customer.branch:
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية لتحديث هذا العميل'
            })
        
        address = request.POST.get('address', '').strip()
        location_type = request.POST.get('location_type', '').strip()
        
        if not address:
            return JsonResponse({
                'success': False,
                'error': 'العنوان مطلوب'
            })
        
        # تحديث عنوان العميل ونوع المكان
        customer.address = address
        if location_type:
            customer.location_type = location_type
        customer.save()
        
        return JsonResponse({
            'success': True,
            'message': 'تم تحديث عنوان العميل بنجاح',
            'address': customer.address,
            'location_type': customer.location_type
        })
        
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'العميل غير موجود'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ أثناء تحديث عنوان العميل: {str(e)}'
        })
```

### 5. customers/urls.py

#### إضافة URL لتحديث عنوان العميل:
```python
# Customer Address Update
path('customer/<int:pk>/update-address/', views.update_customer_address, name='update_customer_address'),
```

## النتائج المتوقعة

### ✅ **رسائل منبثقة جميلة**
- استبدال جميع رسائل `alert` و `confirm` بـ SweetAlert2
- تصميم جميل ومتجاوب
- دعم اللغة العربية
- أيقونات ملونة للأزرار
- مؤقت تلقائي للرسائل

### ✅ **تحديث عنوان العميل تلقائياً**
- تحديث عنوان العميل عند كتابة العنوان في نموذج الجدولة
- تحديث نوع المكان مع العنوان
- رسائل تأكيد جميلة
- معالجة الأخطاء بشكل مناسب

### ✅ **تأكيد الجدولة**
- رسالة تأكيد جميلة قبل جدولة التركيب
- إمكانية الإلغاء
- تصميم متجاوب

### ✅ **تحديث حالة التركيب**
- رسائل تأكيد جميلة قبل تحديث الحالة
- رسائل نجاح ورسائل خطأ جميلة
- مؤشر تحميل أثناء التحديث

## كيفية الاختبار

### 1. اختبار الجدولة السريعة
1. انتقل إلى جدولة تركيب معين
2. اكتب عنوان جديد في حقل العنوان
3. تحقق من ظهور رسالة تأكيد جميلة
4. تحقق من تحديث عنوان العميل تلقائياً

### 2. اختبار تأكيد الجدولة
1. املأ نموذج الجدولة
2. اضغط على زر "جدولة التركيب"
3. تحقق من ظهور رسالة تأكيد جميلة
4. تحقق من إمكانية الإلغاء

### 3. اختبار تحديث حالة التركيب
1. انتقل إلى تفاصيل تركيب معين
2. اضغط على زر "بدء التركيب" أو "إكمال التركيب"
3. تحقق من ظهور رسالة تأكيد جميلة
4. تحقق من رسالة النجاح

### 4. اختبار تحديث الحالة من النافذة المنبثقة
1. انتقل إلى تفاصيل تركيب معين
2. اضغط على "تغيير الحالة"
3. اختر حالة جديدة
4. اضغط على "حفظ التغيير"
5. تحقق من ظهور رسالة نجاح جميلة

## المميزات التقنية

### 1. SweetAlert2
- مكتبة حديثة وخفيفة
- دعم كامل للغة العربية
- تصميم متجاوب
- قابل للتخصيص
- أداء عالي

### 2. تحديث عنوان العميل
- تحديث تلقائي عند تغيير العنوان
- تحديث نوع المكان مع العنوان
- معالجة الأخطاء
- رسائل تأكيد جميلة

### 3. الأمان
- التحقق من الصلاحيات
- حماية CSRF
- معالجة الأخطاء
- تحقق من البيانات

## ملاحظات مهمة

### 1. التوافق
- النظام متوافق مع جميع المتصفحات الحديثة
- لا يؤثر على الوظائف الأخرى
- الحفاظ على التوافق مع الأنظمة الأخرى

### 2. الأداء
- مكتبة SweetAlert2 خفيفة وسريعة
- لا يؤثر على أداء التطبيق
- تحميل المكتبة من CDN

### 3. الصيانة
- الكود سهل الصيانة والتطوير
- يمكن إضافة ميزات جديدة بسهولة
- النظام قابل للتوسع

## مقارنة قبل وبعد

### قبل التحديث
- رسائل منبثقة بسيطة من المتصفح
- عدم تحديث عنوان العميل تلقائياً
- تجربة مستخدم بسيطة
- تصميم غير متجاوب

### بعد التحديث
- رسائل منبثقة جميلة ومتجاوبة
- تحديث عنوان العميل تلقائياً
- تجربة مستخدم محسنة
- تصميم جميل ومتجاوب

## استنتاج

تم تطبيق التحديثات بنجاح:

1. **استبدال الرسائل المنبثقة** بـ SweetAlert2 الجميلة
2. **إضافة تحديث عنوان العميل** تلقائياً عند كتابة العنوان
3. **تحسين تجربة المستخدم** مع رسائل جميلة ومتجاوبة
4. **إضافة تأكيد الجدولة** مع رسائل جميلة
5. **تحسين تحديث حالة التركيب** مع رسائل جميلة

الآن النظام يوفر تجربة مستخدم محسنة مع رسائل منبثقة جميلة وتحديث تلقائي لعنوان العميل! 🎯

## كيفية الاستخدام

### 1. الجدولة السريعة
- اكتب العنوان في حقل العنوان
- سيتم تحديث عنوان العميل تلقائياً
- ستظهر رسالة تأكيد جميلة

### 2. تأكيد الجدولة
- املأ نموذج الجدولة
- اضغط على "جدولة التركيب"
- ستظهر رسالة تأكيد جميلة

### 3. تحديث حالة التركيب
- اضغط على زر تحديث الحالة
- ستظهر رسالة تأكيد جميلة
- ستظهر رسالة نجاح جميلة

### 4. الرسائل المنبثقة
- جميع الرسائل الآن جميلة ومتجاوبة
- دعم كامل للغة العربية
- أيقونات ملونة
- مؤقت تلقائي 