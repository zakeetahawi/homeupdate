# تحديث إضافة اسم المستلم وتحديث عرض المعاينات

## نظرة عامة

تم تطبيق تحديثات جديدة لإضافة اسم المستلم تحت حالة "تم التسليم" وتحديث عرض حالات التركيب والمصنع للمعاينات.

## التحديثات المطبقة

### 1. إضافة حقل اسم المستلم

**الميزة الجديدة:** إضافة حقل `delivery_recipient_name` في نموذج الطلب لتسجيل اسم الشخص الذي استلم الطلب.

#### التغييرات في النموذج (`orders/models.py`):
```python
delivery_recipient_name = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name='اسم المستلم',
    help_text='اسم الشخص الذي استلم الطلب'
)
```

#### التغييرات في النموذج (`orders/forms.py`):
- إضافة حقل `delivery_recipient_name` إلى قائمة الحقول
- إضافة widget مناسب للحقل مع placeholder

#### التغييرات في القالب (`orders/templates/orders/order_form.html`):
- إضافة حقل اسم المستلم في النموذج
- إظهار الحقل فقط عند اختيار أنواع معينة (تركيب، تفصيل، إكسسوار)
- إضافة JavaScript للتحكم في إظهار/إخفاء الحقل

### 2. عرض اسم المستلم تحت حالة "تم التسليم"

**الميزة:** إظهار اسم المستلم بشكل مصغر تحت حالة "تم التسليم" في جدول الطلبات وتفاصيل الطلب.

#### التطبيق في جدول الطلبات (`orders/templates/orders/order_list.html`):
```html
<!-- إظهار اسم المستلم تحت حالة تم التسليم -->
{% if order.get_display_status_text == 'تم التسليم' and order.delivery_recipient_name %}
    <br><small class="text-muted" style="font-size: 0.65rem;">
        <i class="fas fa-user me-1"></i>المستلم: {{ order.delivery_recipient_name }}
    </small>
{% endif %}
```

#### التطبيق في تفاصيل الطلب (`orders/templates/orders/order_detail.html`):
```html
<!-- إظهار اسم المستلم إذا كانت الحالة تم التسليم -->
{% if order.get_display_status_text == 'تم التسليم' and order.delivery_recipient_name %}
    <br><small class="text-muted" style="font-size: 0.75rem;">
        <i class="fas fa-user me-1"></i>المستلم: {{ order.delivery_recipient_name }}
    </small>
{% endif %}
```

### 3. تحديث عرض حالات التركيب والمصنع للمعاينات

**المتطلب:** إظهار "لا يوجد" لحالة التركيب وحالة المصنع في طلبات المعاينة.

#### التطبيق في جدول الطلبات (`orders/templates/orders/order_list.html`):

**حالة المصنع:**
```html
{% if 'inspection' in order_types %}
    <!-- للمعاينات: لا يوجد مصنع -->
    <span class="text-muted">لا يوجد</span>
{% else %}
    <!-- للطلبات الأخرى: عرض حالة أمر التصنيع -->
    {% if order.manufacturing_order %}
        {% with manufacturing_order=order.manufacturing_order %}
            {% get_status_badge manufacturing_order.status "manufacturing" %}
        {% endwith %}
    {% else %}
        <span class="text-muted">-</span>
    {% endif %}
{% endif %}
```

**حالة التركيب:**
```html
{% if 'installation' in order.get_selected_types_list %}
    {% get_status_badge order.installation_status "installation" %}
{% elif 'tailoring' in order.get_selected_types_list or 'accessory' in order.get_selected_types_list %}
    <span class="text-muted">لا يوجد</span>
{% elif 'inspection' in order.get_selected_types_list %}
    <span class="text-muted">لا يوجد</span>
{% else %}
    <span class="text-muted">-</span>
{% endif %}
```

## الفوائد

1. **تتبع أفضل:** معرفة من استلم الطلب عند تسليمه
2. **وضوح أكبر:** المستخدم يعرف أن المعاينات لا تحتاج تركيب أو تصنيع
3. **اتساق:** نفس المنطق في جميع الصفحات
4. **سهولة الاستخدام:** حقل اختياري لا يؤثر على الطلبات الموجودة

## الملفات المحدثة

- `orders/models.py` - إضافة حقل اسم المستلم
- `orders/forms.py` - إضافة الحقل إلى النموذج
- `orders/templates/orders/order_form.html` - إضافة حقل اسم المستلم
- `orders/templates/orders/order_list.html` - عرض اسم المستلم وتحديث حالات المعاينة
- `orders/templates/orders/order_detail.html` - عرض اسم المستلم
- `orders/migrations/0004_order_delivery_recipient_name.py` - migration جديد

## ملاحظات تقنية

- الحقل اختياري ولا يؤثر على الطلبات الموجودة
- يتم إظهار الحقل فقط للأنواع المناسبة (تركيب، تفصيل، إكسسوار)
- يتم عرض اسم المستلم فقط عند حالة "تم التسليم"
- المعاينات تظهر "لا يوجد" لحالة التركيب والمصنع 