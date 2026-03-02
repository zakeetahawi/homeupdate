# تحديثات Templates - نظام الدفعات الجديد

## Templates المطلوب حذفها

إذا كانت موجودة في `accounting/templates/accounting/`:

```bash
# تحقق من وجودها:
ls -la accounting/templates/accounting/ | grep advance

# احذف هذه الملفات إن وجدت:
rm -f accounting/templates/accounting/advance_list.html
rm -f accounting/templates/accounting/advance_form.html
rm -f accounting/templates/accounting/advance_detail.html
rm -f accounting/templates/accounting/customer_advances.html
rm -f accounting/templates/accounting/reports/advances.html
```

---

## تحديث customer_financial.html

**الملف:** `accounting/templates/accounting/customer_financial.html`

### التغيير 1: استبدال active_advances بـ general_payments

**قبل:**
```django
{% if active_advances %}
<div class="card mb-4">
    <div class="card-header">
        <h5>العربونات النشطة</h5>
    </div>
    <div class="card-body">
        <table class="table">
            <thead>
                <tr>
                    <th>رقم العربون</th>
                    <th>التاريخ</th>
                    <th>المبلغ</th>
                    <th>المتبقي</th>
                    <th>الحالة</th>
                </tr>
            </thead>
            <tbody>
                {% for advance in active_advances %}
                <tr>
                    <td>{{ advance.advance_number }}</td>
                    <td>{{ advance.created_at|date:"Y-m-d" }}</td>
                    <td>{{ advance.amount }}</td>
                    <td>{{ advance.remaining_amount }}</td>
                    <td>{{ advance.get_status_display }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endif %}
```

**بعد:**
```django
{% if general_payments %}
<div class="card mb-4">
    <div class="card-header">
        <h5>الدفعات العامة غير المخصصة بالكامل</h5>
    </div>
    <div class="card-body">
        <table class="table">
            <thead>
                <tr>
                    <th>رقم المرجع</th>
                    <th>التاريخ</th>
                    <th>المبلغ الإجمالي</th>
                    <th>المخصص</th>
                    <th>المتبقي</th>
                    <th>طريقة الدفع</th>
                </tr>
            </thead>
            <tbody>
                {% for payment in general_payments %}
                <tr>
                    <td>{{ payment.reference_number|default:"—" }}</td>
                    <td>{{ payment.payment_date|date:"Y-m-d" }}</td>
                    <td>{{ payment.amount }}</td>
                    <td>{{ payment.allocated_amount }}</td>
                    <td>{{ payment.remaining_amount }}</td>
                    <td>{{ payment.get_payment_method_display }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endif %}
```

### التغيير 2: حذف أزرار العربونات

**قبل:**
```django
<div class="action-buttons">
    <a href="{% url 'accounting:register_advance' customer.id %}" class="btn btn-primary">
        تسجيل عربون
    </a>
    <a href="{% url 'accounting:customer_advances' customer.id %}" class="btn btn-secondary">
        عرض جميع العربونات
    </a>
</div>
```

**بعد:**
```django
<div class="action-buttons">
    <!-- سيتم إضافة زر دفعة عامة لاحقاً عند إنشاء الـ view -->
    <!-- <a href="{% url 'orders:create_general_payment' customer.id %}" class="btn btn-primary">
        تسجيل دفعة عامة
    </a> -->
    
    <a href="{% url 'accounting:customer_payments' customer.id %}" class="btn btn-secondary">
        عرض جميع الدفعات
    </a>
</div>
```

### التغيير 3: تحديث summary cards

**قبل:**
```django
<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h6>إجمالي العربونات</h6>
                <h3>{{ summary.total_advances }}</h3>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h6>العربونات المستخدمة</h6>
                <h3>{{ summary.used_advances }}</h3>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h6>العربونات المتبقية</h6>
                <h3>{{ summary.remaining_advances }}</h3>
            </div>
        </div>
    </div>
</div>
```

**بعد:**
```django
<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h6>إجمالي الديون</h6>
                <h3>{{ summary.total_debt }}</h3>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h6>إجمالي المدفوع</h6>
                <h3>{{ summary.total_paid }}</h3>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <h6>رصيد الدفعات العامة</h6>
                <h3>{{ summary.remaining_advances }}</h3>
                <small class="text-muted">دفعات غير مخصصة</small>
            </div>
        </div>
    </div>
</div>
```

---

## إنشاء Template جديد: general_payment_form.html

**الموقع:** `orders/templates/orders/general_payment_form.html`

```django
{% extends "base.html" %}
{% load static %}
{% load widget_tweaks %}

{% block title %}تسجيل دفعة عامة - {{ customer.name }}{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-md-8 offset-md-2">
            <div class="card">
                <div class="card-header">
                    <h4>تسجيل دفعة عامة للعميل: {{ customer.name }}</h4>
                    <p class="text-muted mb-0">ستخصص هذه الدفعة تلقائياً للطلبات المعلقة (الأقدم أولاً)</p>
                </div>
                <div class="card-body">
                    <!-- معلومات العميل -->
                    <div class="alert alert-info mb-4">
                        <div class="row">
                            <div class="col-md-6">
                                <strong>العميل:</strong> {{ customer.name }}<br>
                                <strong>الهاتف:</strong> {{ customer.phone }}
                            </div>
                            <div class="col-md-6">
                                <strong>إجمالي الديون:</strong> {{ customer.financial_summary.total_debt }}<br>
                                <strong>رصيد الدفعات:</strong> {{ customer.financial_summary.remaining_advances }}
                            </div>
                        </div>
                    </div>

                    <!-- النموذج -->
                    <form method="post" class="needs-validation" novalidate>
                        {% csrf_token %}
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="form-group mb-3">
                                    <label for="{{ form.amount.id_for_label }}">المبلغ *</label>
                                    {% render_field form.amount class="form-control" placeholder="أدخل المبلغ" %}
                                    {% if form.amount.errors %}
                                        <div class="invalid-feedback d-block">
                                            {{ form.amount.errors }}
                                        </div>
                                    {% endif %}
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <div class="form-group mb-3">
                                    <label for="{{ form.payment_method.id_for_label }}">طريقة الدفع *</label>
                                    {% render_field form.payment_method class="form-control" %}
                                    {% if form.payment_method.errors %}
                                        <div class="invalid-feedback d-block">
                                            {{ form.payment_method.errors }}
                                        </div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>

                        <div class="form-group mb-3">
                            <label for="{{ form.reference_number.id_for_label }}">رقم المرجع</label>
                            {% render_field form.reference_number class="form-control" placeholder="رقم الإيصال أو المرجع" %}
                            {% if form.reference_number.errors %}
                                <div class="invalid-feedback d-block">
                                    {{ form.reference_number.errors }}
                                </div>
                            {% endif %}
                        </div>

                        <div class="form-group mb-3">
                            <label for="{{ form.notes.id_for_label }}">ملاحظات</label>
                            {% render_field form.notes class="form-control" rows="3" placeholder="ملاحظات إضافية (اختياري)" %}
                            {% if form.notes.errors %}
                                <div class="invalid-feedback d-block">
                                    {{ form.notes.errors }}
                                </div>
                            {% endif %}
                        </div>

                        <!-- معلومات إضافية -->
                        <div class="alert alert-warning">
                            <strong>ملاحظة:</strong> 
                            <ul class="mb-0">
                                <li>سيتم تخصيص المبلغ تلقائياً للطلبات المعلقة الأقدم أولاً (FIFO)</li>
                                <li>إذا كان المبلغ أكبر من إجمالي الديون، سيبقى الفائض كرصيد للعميل</li>
                                <li>يمكنك عرض تفاصيل التخصيصات بعد حفظ الدفعة</li>
                            </ul>
                        </div>

                        <!-- الأزرار -->
                        <div class="form-group mb-0">
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-save"></i> حفظ الدفعة
                            </button>
                            <a href="{% url 'accounting:customer_financial' customer.id %}" class="btn btn-secondary">
                                <i class="fas fa-times"></i> إلغاء
                            </a>
                        </div>
                    </form>
                </div>
            </div>

            <!-- الطلبات المعلقة -->
            {% if pending_orders %}
            <div class="card mt-4">
                <div class="card-header">
                    <h5>الطلبات المعلقة للعميل</h5>
                    <small class="text-muted">سيتم التخصيص لهذه الطلبات حسب الترتيب</small>
                </div>
                <div class="card-body">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>رقم الطلب</th>
                                <th>التاريخ</th>
                                <th>الإجمالي</th>
                                <th>المدفوع</th>
                                <th>المتبقي</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for order in pending_orders %}
                            <tr>
                                <td>{{ forloop.counter }}</td>
                                <td>{{ order.order_number }}</td>
                                <td>{{ order.created_at|date:"Y-m-d" }}</td>
                                <td>{{ order.total_price }}</td>
                                <td>{{ order.paid_amount }}</td>
                                <td class="text-danger font-weight-bold">{{ order.remaining_amount }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                        <tfoot>
                            <tr class="font-weight-bold">
                                <td colspan="5">إجمالي المتبقي:</td>
                                <td class="text-danger">{{ total_pending }}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
```

---

## تحديث Dashboard Template

**الملف:** `accounting/templates/accounting/dashboard.html` (إن وجد)

### قبل:
```django
<div class="stat-card">
    <h6>العربونات النشطة</h6>
    <h3 id="active-advances">0</h3>
</div>
```

### بعد:
```django
<div class="stat-card">
    <h6>رصيد الدفعات العامة</h6>
    <h3 id="general-payments">0</h3>
</div>
```

### تحديث JavaScript:
```javascript
// قبل:
fetch('/accounting/api/dashboard/stats/')
    .then(response => response.json())
    .then(data => {
        document.getElementById('active-advances').textContent = data.active_advances;
    });

// بعد:
fetch('/accounting/api/dashboard/stats/')
    .then(response => response.json())
    .then(data => {
        document.getElementById('general-payments').textContent = data.general_payments;
    });
```

---

## تحديث Navigation/Sidebar

**إزالة روابط العربونات:**

```django
<!-- قبل: -->
<li class="nav-item">
    <a class="nav-link" href="{% url 'accounting:advance_list' %}">
        <i class="fas fa-hand-holding-usd"></i> العربونات
    </a>
</li>
<li class="nav-item">
    <a class="nav-link" href="{% url 'accounting:advances_report' %}">
        <i class="fas fa-chart-line"></i> تقرير العربونات
    </a>
</li>

<!-- بعد: -->
<!-- تم إزالة هذه الروابط - الدفعات العامة تدار من صفحة العميل -->
```

---

## البحث عن جميع الإشارات

استخدم هذا الأمر للبحث عن أي إشارات متبقية للعربونات في Templates:

```bash
# البحث عن "advance" في جميع templates
find templates -name "*.html" -exec grep -Hn "advance" {} \;

# البحث عن "register_advance" url tag
find templates -name "*.html" -exec grep -Hn "register_advance" {} \;

# البحث عن "customer_advances" url tag
find templates -name "*.html" -exec grep -Hn "customer_advances" {} \;

# البحث عن "advance_list" url tag
find templates -name "*.html" -exec grep -Hn "advance_list" {} \;
```

---

## ملخص التغييرات

| Template | الإجراء | الوصف |
|----------|---------|-------|
| advance_list.html | حذف | قائمة العربونات |
| advance_form.html | حذف | نموذج إنشاء عربون |
| advance_detail.html | حذف | تفاصيل العربون |
| customer_advances.html | حذف | عربونات العميل |
| reports/advances.html | حذف | تقرير العربونات |
| customer_financial.html | تحديث | استبدال active_advances بـ general_payments |
| dashboard.html | تحديث | استبدال active_advances بـ general_payments |
| navigation | تحديث | إزالة روابط العربونات |
| general_payment_form.html | إنشاء جديد | نموذج الدفعة العامة |

---

**ملاحظة:** 
- بعد تطبيق التغييرات، اختبر جميع الصفحات للتأكد من عدم وجود روابط معطوبة
- تأكد من أن جميع url tags محدثة
- راجع JavaScript code للتأكد من عدم استخدام old API endpoints
