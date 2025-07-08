# إصلاحات مزامنة حالة الطلب والإشعارات المحسنة

## المشاكل المُحلولة

### 1. ✅ إصلاح تحديث حالة الطلب في صفحة التفاصيل
**المشكلة**: حالة الطلب في صفحة تفاصيل الطلب لا تتحدث عند تحديث حالة أمر التصنيع.

**الحل**:
- تم تغيير عرض الحالة من `order.status` إلى `order.tracking_status`
- إضافة جميع الحالات الممكنة مع الألوان المناسبة
- تحديث حالة الطلب الأصلي عند الموافقة/الرفض

```html
<!-- قبل الإصلاح -->
{% if order.status == 'pending' %}
<span class="badge bg-warning">قيد الانتظار</span>

<!-- بعد الإصلاح -->
{% if order.tracking_status == 'pending' %}
<span class="badge bg-warning text-dark">قيد الانتظار</span>
{% elif order.tracking_status == 'processing' %}
<span class="badge bg-info">قيد المعالجة</span>
{% elif order.tracking_status == 'warehouse' %}
<span class="badge bg-primary">في المستودع</span>
<!-- ... جميع الحالات الأخرى -->
```

### 2. ✅ إضافة عرض تفاصيل الرفض في صفحة الطلب
**المشكلة**: عند رفض الطلب، لا يظهر سبب الرفض في صفحة تفاصيل الطلب.

**الحل**:
```html
<!-- إضافة قسم تفاصيل الرفض -->
{% if order.tracking_status == 'rejected' %}
{% with manufacturing_order=order.manufacturing_order %}
    {% if manufacturing_order and manufacturing_order.rejection_reason %}
    <tr>
        <th>سبب الرفض</th>
        <td>
            <div class="alert alert-danger mb-2">
                <i class="fas fa-exclamation-triangle me-2"></i>
                {{ manufacturing_order.rejection_reason }}
            </div>
        </td>
    </tr>
    {% endif %}
{% endwith %}
{% endif %}
```

### 3. ✅ تحسين الإشعارات لتكون أكثر تفصيلاً

#### أ) إشعار إنشاء أمر التصنيع
**قبل**: إشعار عام "تم تحديث حالة الطلب"
**بعد**: إشعار مفصل مع اسم العميل

```python
send_notification(
    title=f'تم إنشاء أمر تصنيع جديد',
    message=f'تم إنشاء أمر تصنيع للعميل {order.customer.name} - الطلب #{order.order_number}',
    sender=request.user,
    sender_department_code='manufacturing',
    target_department_code='management',
    target_branch=order.branch,
    priority='medium',
    related_object=manufacturing_order
)
```

#### ب) إشعار الموافقة
```python
title = f'بدء تصنيع طلب {order.order.customer.name}'
message = f'تمت الموافقة على أمر التصنيع للعميل {order.order.customer.name} - الطلب #{order.order.order_number}\nدخل الطلب مرحلة التصنيع. رقم أمر التصنيع #{order.pk}.'
```

#### ج) إشعار الرفض
```python
title = f'طلب مرفوض - {order.order.customer.name}'
message = f'تم رفض أمر التصنيع للعميل {order.order.customer.name} - الطلب #{order.order.order_number}\n\nسبب الرفض: "{reason}"\n\nيرجى مراجعة الطلب وإجراء التعديلات المطلوبة.'
```

### 4. ✅ مزامنة حالة الطلب مع حالة التصنيع
**تم إضافة**:
- عند الموافقة: `order.tracking_status = 'in_progress'`
- عند الرفض: `order.tracking_status = 'rejected'`

```python
# عند الموافقة
if order.order:
    order.order.tracking_status = 'in_progress'
    order.order.save(update_fields=['tracking_status'])

# عند الرفض
if order.order:
    order.order.tracking_status = 'rejected'
    order.order.save(update_fields=['tracking_status'])
```

## الحالات المدعومة في صفحة تفاصيل الطلب

| الحالة | اللون | الوصف |
|--------|-------|--------|
| `pending` | أصفر | قيد الانتظار |
| `processing` | أزرق | قيد المعالجة |
| `warehouse` | أزرق أساسي | في المستودع |
| `factory` | رمادي | في المصنع |
| `cutting` | أسود | قيد القص |
| `ready` | أخضر | جاهز للتسليم |
| `delivered` | أخضر | تم التسليم |
| `cancelled` | أحمر | ملغي |
| `rejected` | أحمر | مرفوض |
| `in_progress` | أزرق | قيد التنفيذ |
| `completed` | أخضر | مكتمل |
| `ready_for_installation` | أصفر | جاهز للتركيب |

## الملفات المُحدثة

1. **`orders/templates/orders/order_detail.html`**:
   - تحديث عرض حالة الطلب
   - إضافة قسم تفاصيل الرفض

2. **`manufacturing/views.py`**:
   - تحسين إشعارات الموافقة والرفض
   - إضافة مزامنة حالة الطلب
   - تحسين إشعار إنشاء أمر التصنيع

## النتائج النهائية

### ✅ الآن يعمل بشكل صحيح:
1. **حالة الطلب تتحدث فوراً** عند تحديث حالة التصنيع
2. **يظهر سبب الرفض** في صفحة تفاصيل الطلب
3. **الإشعارات أكثر تفصيلاً** وتحتوي على اسم العميل
4. **مزامنة كاملة** بين حالة الطلب وحالة التصنيع

### 🎯 سيناريوهات الاستخدام:
- **إنشاء أمر تصنيع**: إشعار للإدارة مع اسم العميل
- **موافقة على الطلب**: إشعار للمستخدم + تحديث حالة الطلب إلى "قيد التنفيذ"
- **رفض الطلب**: إشعار للمستخدم + تحديث حالة الطلب إلى "مرفوض" + عرض سبب الرفض

هذا يحسن تجربة المستخدم بشكل كبير ويجعل النظام أكثر شفافية! 🚀 