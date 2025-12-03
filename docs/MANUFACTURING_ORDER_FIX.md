# إصلاح إنشاء أوامر التصنيع من الويزارد
## Manufacturing Order Creation Fix

**التاريخ:** 2025-11-23  
**الوقت:** 15:01

---

## المشكلة

عند إنشاء طلب من الويزارد بنوع **تركيب** أو **تسليم** أو **إكسسوار**، لم يتم إنشاء **Manufacturing Order** تلقائياً.

### السبب

في `orders/signals.py::create_manufacturing_order_on_order_creation()`:

```python
# الكود القديم (خاطئ)
try:
    parsed_types = json.loads(instance.selected_types)  # ❌
    if isinstance(parsed_types, list):
        order_types = set(parsed_types)
except (json.JSONDecodeError, TypeError):
    if isinstance(instance.selected_types, str):
        order_types = {instance.selected_types}
```

**المشكلة:** 
- `selected_types` هو `JSONField` في Django
- Django يُرجع `list` مباشرة، وليس JSON string
- محاولة عمل `json.loads()` على list تفشل
- لذلك لم يتم التعرف على نوع الطلب

---

## الحل

تحديث منطق معالجة `selected_types` في الـ signal:

```python
# الكود الجديد (صحيح)
order_types = set()

# selected_types is a JSONField that returns a Python list directly
if isinstance(instance.selected_types, list):
    order_types = set(instance.selected_types)  # ✅
elif isinstance(instance.selected_types, str):
    # Fallback: try to parse as JSON string
    try:
        parsed_types = json.loads(instance.selected_types)
        if isinstance(parsed_types, list):
            order_types = set(parsed_types)
        else:
            order_types = {instance.selected_types}
    except (json.JSONDecodeError, TypeError, ValueError):
        # Single string value
        order_types = {instance.selected_types}
```

---

## الاختبار

### قبل الإصلاح
```python
order = Order.objects.create(
    customer=customer,
    branch=branch,
    selected_types=['installation'],
    invoice_number='TEST-001',
    ...
)

# ❌ لا يتم إنشاء Manufacturing Order
ManufacturingOrder.objects.filter(order=order).exists()  # False
```

### بعد الإصلاح
```python
order = Order.objects.create(
    customer=customer,
    branch=branch,
    selected_types=['installation'],
    invoice_number='TEST-001',
    ...
)

# ✅ يتم إنشاء Manufacturing Order تلقائياً
mfg = ManufacturingOrder.objects.filter(order=order).first()
print(f'Manufacturing Order: {mfg.id}')  # Manufacturing Order: 13327
print(f'Type: {mfg.order_type}')         # Type: installation
print(f'Status: {mfg.status}')           # Status: pending_approval
```

---

## التأثير على النظام

### الويزارد الآن ينشئ تلقائياً:

#### 1. طلبات المنتجات (`products`)
- ✅ عناصر الفاتورة
- ✅ أوامر التقطيع (Cutting Orders)
- ❌ لا manufacturing order
- ❌ لا عقد

#### 2. طلبات المعاينة (`inspection`)
- ✅ عناصر الفاتورة (اختياري)
- ✅ معاينة في قسم المعاينات (Inspection)
- ❌ لا cutting orders
- ❌ لا manufacturing order
- ❌ لا عقد

#### 3. طلبات التركيب (`installation`)
- ✅ عناصر الفاتورة
- ✅ أوامر التقطيع (Cutting Orders)
- ✅ أمر التصنيع (Manufacturing Order) ← **تم الإصلاح**
- ✅ عقد إلكتروني أو PDF

#### 4. طلبات التسليم (`tailoring`)
- ✅ عناصر الفاتورة
- ✅ أوامر التقطيع (Cutting Orders)
- ✅ أمر التصنيع (Manufacturing Order) ← **تم الإصلاح**
- ✅ عقد إلكتروني أو PDF

#### 5. طلبات الإكسسوار (`accessory`)
- ✅ عناصر الفاتورة
- ✅ أوامر التقطيع (Cutting Orders)
- ✅ أمر التصنيع (Manufacturing Order) ← **تم الإصلاح**
- ✅ عقد إلكتروني أو PDF

---

## الملفات المُعدّلة

### `/home/zakee/homeupdate/orders/signals.py`

**الدالة:** `create_manufacturing_order_on_order_creation()`  
**السطور:** ~467-490  
**التغيير:** معالجة `selected_types` كـ `list` مباشرة

---

## الخلاصة

✅ **تم إصلاح** إنشاء Manufacturing Orders من الويزارد  
✅ **يعمل تلقائياً** للأنواع: installation, tailoring, accessory  
✅ **متوافق** مع النظام التقليدي  
✅ **مُختبَر** وجاهز للاستخدام

---

## المرجع السريع - الـ Signals التلقائية

| النوع | Cutting Order | Manufacturing Order | Inspection |
|-------|---------------|---------------------|------------|
| `products` | ✅ | ❌ | ❌ |
| `inspection` | ❌ | ❌ | ✅ |
| `installation` | ✅ | ✅ | ❌ |
| `tailoring` | ✅ | ✅ | ❌ |
| `accessory` | ✅ | ✅ | ❌ |

### الـ Signals المسؤولة

1. **Cutting Orders:** `cutting/signals.py::create_cutting_orders_on_order_save()`
2. **Manufacturing Orders:** `orders/signals.py::create_manufacturing_order_on_order_creation()`
3. **Inspections:** `orders/signals.py::create_inspection_on_order_creation()`

---

**تم الإصلاح بنجاح ✅**
