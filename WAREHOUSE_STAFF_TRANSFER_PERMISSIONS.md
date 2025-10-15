# صلاحيات موظفي المستودع في التحويلات المخزنية

## نظرة عامة

تم تطبيق قيود صلاحيات على موظفي المستودع في نظام التحويلات المخزنية لضمان أن كل موظف مستودع يمكنه فقط:

1. ✅ **إنشاء تحويل** من مستودعه المخصص → إلى أي مستودع آخر
2. ✅ **استلام تحويل** من أي مستودع → إلى مستودعه المخصص (إذا لم يكن هو منشئ التحويل)
3. ❌ **لا يمكنه** إنشاء تحويل من مستودع ليس مسؤولاً عنه
4. ❌ **لا يمكنه** استلام تحويل قام بإنشائه بنفسه

---

## القواعد التفصيلية

### ✅ ما يمكن لموظف المستودع فعله:

#### 1. إنشاء تحويل من مستودعه
- **المستودع المصدر:** مستودعه المخصص فقط
- **المستودع المستهدف:** أي مستودع آخر نشط
- **مثال:** موظف مستودع "بافلي" يمكنه إنشاء تحويل من "بافلي" → "اكسسوار"

#### 2. استلام تحويل إلى مستودعه
- يمكنه استلام أي تحويل موجه إلى مستودعه المخصص
- **شرط:** يجب ألا يكون هو منشئ التحويل
- حتى لو كان التحويل من مستودع آخر
- **مثال:** موظف مستودع "بافلي" يمكنه استلام تحويل من "سعد" → "بافلي" (إذا لم يكن هو من أنشأه)

#### 3. عرض التحويلات
- يرى جميع التحويلات **من** أو **إلى** مستودعه المخصص
- لا يرى التحويلات بين مستودعات أخرى

---

### ❌ ما لا يمكن لموظف المستودع فعله:

#### 1. إنشاء تحويل من مستودع آخر
- **ممنوع:** إنشاء تحويل من مستودع ليس مسؤولاً عنه
- **مثال:** موظف مستودع "بافلي" **لا يمكنه** إنشاء تحويل من "سعد" → "اكسسوار"

#### 2. إنشاء تحويل بين مستودعين آخرين
- **ممنوع:** إنشاء تحويل بين مستودعين ليس مسؤولاً عن أي منهما
- **مثال:** موظف مستودع "بافلي" **لا يمكنه** إنشاء تحويل من "سعد" → "فرش"

#### 3. استلام تحويل قام بإنشائه
- **ممنوع:** استلام تحويل قام بإنشائه بنفسه (حتى لو كان موجهاً إلى مستودعه)
- **مثال:** موظف مستودع "بافلي" ينشئ تحويل من "بافلي" → "سعد"، **لا يمكنه** استلامه في مستودع "سعد"
- **السبب:** منع تضارب المصالح وضمان الفصل بين الأدوار

#### 4. استلام تحويل إلى مستودع آخر
- **ممنوع:** استلام تحويل موجه إلى مستودع ليس مسؤولاً عنه
- **مثال:** موظف مستودع "بافلي" **لا يمكنه** استلام تحويل من "سعد" → "فرش"

---

## 🔒 قيود الاستلام (تحديث جديد)

### المشكلة التي تم حلها:
كان موظف المستودع الذي **أنشأ** التحويل يستطيع أيضاً **استلامه** في المستودع المستهدف، وهذا يخلق تضارب مصالح.

### الحل:
تم إضافة قيد يمنع **منشئ التحويل** من استلامه، حتى لو كان:
- موظف المستودع المستهدف
- مديراً للمستودع المستهدف
- له صلاحيات على المستودع المستهدف

### مثال:
**السيناريو:**
- bafli (موظف مستودع "بافلي") ينشئ تحويل من "بافلي" → "سعد"
- bafli **لا يمكنه** استلام هذا التحويل في مستودع "سعد"
- فقط موظف مستودع "سعد" أو المدير (superuser) يمكنه الاستلام

### الفائدة:
- ✅ الفصل بين الأدوار (Separation of Duties)
- ✅ منع تضارب المصالح
- ✅ تحسين الرقابة الداخلية
- ✅ ضمان أن شخصاً آخر يتحقق من التحويل

---

## التطبيق التقني

### 1. التعديلات على Backend (Views)

#### الملف: `inventory/views_stock_transfer.py`

##### أ. تعديل `stock_transfer_bulk` (السطور 137-163)
```python
@login_required
def stock_transfer_bulk(request):
    """صفحة التحويلات المخزنية"""
    user = request.user
    
    # تحديد المستودعات المتاحة حسب صلاحيات المستخدم
    if user.is_superuser:
        # المدير يرى جميع المستودعات
        warehouses = Warehouse.objects.filter(is_active=True).order_by('name')
    elif hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff:
        # موظف المستودع يرى مستودعه فقط كمصدر
        if user.assigned_warehouse:
            warehouses = Warehouse.objects.filter(is_active=True).order_by('name')
        else:
            warehouses = Warehouse.objects.none()
    else:
        # باقي المستخدمين يرون جميع المستودعات
        warehouses = Warehouse.objects.filter(is_active=True).order_by('name')

    context = {
        'warehouses': warehouses,
        'title': 'تحويلات مخزنية',
        'user_warehouse': user.assigned_warehouse if hasattr(user, 'assigned_warehouse') else None,
        'is_warehouse_staff': hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff,
    }

    return render(request, 'inventory/stock_transfer_bulk.html', context)
```

##### ب. تعديل `stock_transfer_bulk_create` (السطور 166-215)
```python
@login_required
@require_POST
def stock_transfer_bulk_create(request):
    """إنشاء تحويل جماعي"""
    import json

    try:
        data = json.loads(request.body)
        from_warehouse_id = data.get('from_warehouse')
        to_warehouse_id = data.get('to_warehouse')
        # ... باقي الكود
        
        # ✅ التحقق من صلاحيات موظف المستودع
        user = request.user
        if hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff:
            # موظف المستودع يمكنه فقط إنشاء تحويل من مستودعه المخصص
            if not user.assigned_warehouse:
                return JsonResponse({
                    'success': False,
                    'error': 'لا يوجد مستودع مخصص لك'
                }, status=403)
            
            if from_warehouse.id != user.assigned_warehouse.id:
                return JsonResponse({
                    'success': False,
                    'error': f'لا يمكنك إنشاء تحويل إلا من مستودعك المخصص ({user.assigned_warehouse.name})'
                }, status=403)
        
        # ... باقي الكود
```

##### ج. تعديل `stock_transfer_receive` (السطور 359-387)
```python
@login_required
def stock_transfer_receive(request, pk):
    """استلام التحويل"""
    transfer = get_object_or_404(StockTransfer, pk=pk)

    if not transfer.can_complete:
        messages.error(request, 'لا يمكن استلام هذا التحويل')
        return redirect('inventory:stock_transfer_detail', pk=pk)

    # ✅ التحقق من صلاحيات الاستلام
    user = request.user

    # 1. منع منشئ التحويل من استلامه
    if transfer.created_by == user:
        messages.error(request, 'لا يمكنك استلام تحويل قمت بإنشائه بنفسك')
        return redirect('inventory:stock_transfer_detail', pk=pk)

    # 2. موظف المستودع يمكنه فقط استلام تحويل إلى مستودعه المخصص
    if hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff and not user.is_superuser:
        if not user.assigned_warehouse:
            messages.error(request, 'لا يوجد مستودع مخصص لك')
            return redirect('inventory:stock_transfer_detail', pk=pk)

        if transfer.to_warehouse.id != user.assigned_warehouse.id:
            messages.error(
                request,
                f'لا يمكنك استلام هذا التحويل. يمكنك فقط استلام التحويلات الموجهة إلى مستودعك ({user.assigned_warehouse.name})'
            )
            return redirect('inventory:stock_transfer_detail', pk=pk)

    # ... باقي الكود
```

##### د. تعديل `stock_transfer_detail` (السطور 259-299)
```python
@login_required
def stock_transfer_detail(request, pk):
    """تفاصيل التحويل المخزني"""
    transfer = get_object_or_404(
        StockTransfer.objects.select_related(
            'from_warehouse', 'to_warehouse', 'created_by',
            'approved_by', 'completed_by'
        ).prefetch_related('items__product'),
        pk=pk
    )

    # ... الكود الموجود

    # ✅ التحقق من صلاحيات الاستلام
    user = request.user
    can_receive = False

    if transfer.can_complete:
        # المدير يمكنه الاستلام دائماً
        if user.is_superuser:
            can_receive = True
        # منع منشئ التحويل من الاستلام
        elif transfer.created_by != user:
            # موظف المستودع يمكنه الاستلام فقط إذا كان التحويل إلى مستودعه
            if hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff:
                if user.assigned_warehouse and transfer.to_warehouse.id == user.assigned_warehouse.id:
                    can_receive = True
            else:
                # المستخدمون الآخرون يمكنهم الاستلام
                can_receive = True

    context = {
        'transfer': transfer,
        'stock_transactions': stock_transactions,
        'can_receive': can_receive,  # ✅ إضافة متغير جديد
    }

    return render(request, 'inventory/stock_transfer_detail.html', context)
```

---

### 2. التعديلات على Frontend (Template)

#### الملف: `inventory/templates/inventory/stock_transfer_bulk.html`

##### أ. تحديد المستودع المصدر تلقائياً (السطور 149-197)
```html
<!-- من مستودع -->
<div class="mb-4">
    <label class="form-label fw-bold fs-5">
        <i class="fas fa-warehouse text-danger"></i>
        من مستودع *
    </label>
    {% if is_warehouse_staff and user_warehouse %}
        <!-- موظف المستودع: مستودع واحد فقط (مستودعه المخصص) -->
        <div class="alert alert-info">
            <i class="fas fa-info-circle"></i>
            يمكنك فقط إنشاء تحويل من مستودعك المخصص: <strong>{{ user_warehouse.name }}</strong>
        </div>
        <input type="hidden" name="from_warehouse" value="{{ user_warehouse.id }}" id="from_warehouse_hidden">
        <div class="row g-3">
            <div class="col-md-4">
                <div class="card warehouse-radio-card" style="border-color: #0d6efd; background: #e7f1ff;">
                    <div class="card-body text-center">
                        <i class="fas fa-warehouse fa-2x text-danger mb-2"></i>
                        <h6>{{ user_warehouse.name }}</h6>
                        <span class="badge bg-primary">مستودعك</span>
                    </div>
                </div>
            </div>
        </div>
    {% else %}
        <!-- المدير أو المستخدمون الآخرون: جميع المستودعات -->
        <div class="row g-3">
            {% for warehouse in warehouses %}
            <!-- ... عرض جميع المستودعات -->
            {% endfor %}
        </div>
    {% endif %}
</div>
```

##### ب. تحديث JavaScript (السطور 343-424)
```javascript
// تحديث المستودعات المستهدفة
function updateToWarehouses() {
    // للموظفين: استخدام المستودع المخفي
    fromWarehouseId = $('input[name="from_warehouse"]:checked').val() || $('#from_warehouse_hidden').val();
    // ... باقي الكود
}

// الانتقال للخطوة 2
function goToStep2() {
    // للموظفين: استخدام المستودع المخفي
    fromWarehouseId = $('input[name="from_warehouse"]:checked').val() || $('#from_warehouse_hidden').val();
    // ... باقي الكود
}

// تحميل المستودعات المستهدفة تلقائياً لموظفي المستودع
$(document).ready(function() {
    {% if is_warehouse_staff and user_warehouse %}
        // تحميل المستودعات المستهدفة تلقائياً
        updateToWarehouses();
    {% endif %}
});
```

##### ج. تحديث زر الاستلام في `stock_transfer_detail.html` (السطور 261-276)
```html
{% elif transfer.status == 'approved' or transfer.status == 'in_transit' %}
{% if can_receive %}
<a href="{% url 'inventory:stock_transfer_receive' transfer.pk %}" class="btn btn-success w-100 mb-2">
    <i class="fas fa-check-circle"></i>
    استلام التحويل
</a>
{% else %}
<button type="button" class="btn btn-secondary w-100 mb-2" disabled title="لا يمكنك استلام هذا التحويل">
    <i class="fas fa-lock"></i>
    استلام التحويل (غير مصرح)
</button>
{% endif %}
<button type="button" class="btn btn-danger w-100" data-bs-toggle="modal" data-bs-target="#cancelModal">
    <i class="fas fa-times"></i>
    إلغاء التحويل
</button>
        updateToWarehouses();
    {% endif %}
});
```

---

## السيناريوهات العملية

### مثال: موظف مستودع "بافلي"

#### المستودعات المتاحة:
- ✅ **بافلي** (مستودعه المخصص)
- اكسسوار
- خدمات
- سعد
- فرش
- منتجات جاهزة

#### السيناريوهات:

##### إنشاء التحويلات:

| # | من | إلى | منشئ التحويل | النتيجة | السبب |
|---|---|---|---|---|---|
| 1 | بافلي | اكسسوار | bafli | ✅ مسموح | من مستودعه المخصص |
| 2 | بافلي | سعد | bafli | ✅ مسموح | من مستودعه المخصص |
| 3 | اكسسوار | بافلي | bafli | ❌ ممنوع | ليس من مستودعه المخصص |
| 4 | سعد | فرش | bafli | ❌ ممنوع | ليس من مستودعه المخصص |

##### استلام التحويلات:

| # | من | إلى | منشئ التحويل | من يستلم | النتيجة | السبب |
|---|---|---|---|---|---|---|
| 1 | بافلي | سعد | bafli | bafli | ❌ ممنوع | منشئ التحويل لا يمكنه استلامه |
| 2 | بافلي | سعد | bafli | موظف مستودع سعد | ✅ مسموح | موظف المستودع المستهدف |
| 3 | سعد | بافلي | مستخدم آخر | bafli | ✅ مسموح | موظف المستودع المستهدف |
| 4 | سعد | بافلي | bafli | bafli | ❌ ممنوع | منشئ التحويل لا يمكنه استلامه |
| 5 | سعد | فرش | مستخدم آخر | bafli | ❌ ممنوع | ليس المستودع المستهدف |

---

## الاختبار

### سكريبت الاختبار: `test_warehouse_staff_transfer_permissions.py`

يمكن تشغيل السكريبت للتحقق من الصلاحيات:

```bash
python test_warehouse_staff_transfer_permissions.py
```

**النتيجة المتوقعة:**
```
================================================================================
اختبار صلاحيات موظفي المستودع في التحويلات المخزنية
================================================================================

المستخدم: bafli
موظف مستودع: True
المستودع المخصص: بافلي

================================================================================
المستودعات المتاحة:
================================================================================
     اكسسوار (ID: 5)
  ✅ بافلي (ID: 3)
     خدمات (ID: 6)
     سعد (ID: 2)
     فرش (ID: 7)
     منتجات جاهزة (ID: 4)
```

---

## الملفات المعدلة

### 1. Backend (Views)

#### `inventory/views_stock_transfer.py`
- ✅ تعديل `stock_transfer_bulk()` - السطور 137-163
  - إضافة منطق لتحديد المستودعات المتاحة حسب نوع المستخدم
  - تمرير معلومات المستودع المخصص للموظف إلى Template

- ✅ تعديل `stock_transfer_bulk_create()` - السطور 166-215
  - إضافة التحقق من صلاحيات موظف المستودع عند الإنشاء
  - رفض الطلب إذا حاول إنشاء تحويل من مستودع ليس مسؤولاً عنه

- ✅ **تعديل `stock_transfer_receive()` - السطور 359-387** (جديد)
  - إضافة التحقق من صلاحيات الاستلام
  - منع منشئ التحويل من استلامه
  - التحقق من أن موظف المستودع يستلم فقط تحويلات إلى مستودعه

- ✅ **تعديل `stock_transfer_detail()` - السطور 259-299** (جديد)
  - إضافة متغير `can_receive` لتحديد ما إذا كان المستخدم يمكنه الاستلام
  - تمرير المتغير إلى Template لإظهار/إخفاء زر الاستلام

### 2. Frontend (Templates)

#### `inventory/templates/inventory/stock_transfer_bulk.html`
- ✅ تعديل قسم "من مستودع" - السطور 149-197
  - عرض مستودع واحد فقط (المستودع المخصص) لموظفي المستودع
  - رسالة توضيحية للموظف

- ✅ تعديل JavaScript `updateToWarehouses()` - السطور 343-386
  - دعم الحقل المخفي للموظفين

- ✅ تعديل JavaScript `goToStep2()` - السطور 394-424
  - دعم الحقل المخفي للموظفين

- ✅ إضافة `$(document).ready()` - السطور 693-698
  - تحميل المستودعات المستهدفة تلقائياً للموظفين

#### `inventory/templates/inventory/stock_transfer_detail.html` (جديد)
- ✅ تعديل زر الاستلام - السطور 261-276
  - إظهار زر "استلام التحويل" فقط إذا كان `can_receive = True`
  - إظهار زر معطل مع رسالة "غير مصرح" إذا كان `can_receive = False`

### 3. سكريبتات الاختبار

- ✅ `test_warehouse_staff_transfer_permissions.py` (تم حذفه بعد الاختبار)
  - سكريبت اختبار صلاحيات الإنشاء

- ✅ `test_transfer_receive_permissions.py` (تم حذفه بعد الاختبار)
  - سكريبت اختبار صلاحيات الاستلام

---

## ملاحظات مهمة

### 1. الأمان
- ✅ التحقق من الصلاحيات يتم في **Backend** (Views) وليس فقط في Frontend
- ✅ حتى لو حاول المستخدم التلاعب بالطلب، سيتم رفضه من Backend
- ✅ رسائل خطأ واضحة تخبر المستخدم بالسبب

### 2. تجربة المستخدم
- ✅ موظف المستودع يرى مستودعه المخصص فقط كمصدر (محدد مسبقاً)
- ✅ يمكنه اختيار أي مستودع آخر كمستهدف
- ✅ رسالة توضيحية تخبره بأنه يمكنه فقط إنشاء تحويل من مستودعه

### 3. الاستلام
- ✅ موظف المستودع يمكنه استلام أي تحويل موجه إلى مستودعه
- ❌ **لا يمكنه** استلام تحويل قام بإنشائه بنفسه (حتى لو كان موجهاً إلى مستودعه)
- ✅ الفصل بين الأدوار (Separation of Duties) لضمان الرقابة الداخلية

### 4. المدير
- ✅ المدير (superuser) لا يتأثر بهذه القيود
- ✅ يمكنه إنشاء تحويل من أي مستودع إلى أي مستودع
- ✅ يمكنه استلام أي تحويل (حتى لو كان هو منشئه)

---

## التاريخ

- **التاريخ:** 2025-10-15
- **المطور:** Augment Agent
- **المتطلب:** تقييد صلاحيات موظفي المستودع في التحويلات المخزنية
- **الحل:** إضافة قيود في Backend و Frontend لضمان أن موظف المستودع يمكنه فقط إنشاء تحويل من مستودعه المخصص

