# تحديث ربط المعاينات بالطلبات

## نظرة عامة

تم تطبيق تحديثات جديدة لربط المعاينات بالطلبات وإصلاح مشاكل العرض في جدول الطلبات.

## التحديثات المطبقة

### 1. إصلاح عرض كلمة "تركيب" في جدول الطلبات

**المشكلة:** كانت كلمة "تركيب" تظهر تحت حالة "غير مجدول" في جدول الطلبات.

**الحل:** تم تحديث منطق العرض في `orders/templates/orders/order_list.html`:
- لا تظهر كلمة "تركيب" عندما تكون الحالة "غير مجدول"
- تظهر فقط عندما تكون الحالة مختلفة عن "غير مجدول"

### 2. إضافة حقل "معاينة مرتبطة" للطلبات

**الميزة الجديدة:** إضافة حقل `related_inspection` في نموذج الطلب لربط المعاينات بالطلبات.

#### التغييرات في النموذج (`orders/models.py`):
```python
# المعاينة المرتبطة بالطلب
related_inspection = models.ForeignKey(
    'inspections.Inspection',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name='معاينة مرتبطة',
    help_text='المعاينة المرتبطة بهذا الطلب',
    related_name='related_orders'
)
```

#### التغييرات في النموذج (`orders/forms.py`):
- إضافة حقل `related_inspection` إلى قائمة الحقول
- تصفية المعاينات حسب العميل عند إنشاء/تعديل الطلب
- إضافة widget مناسب للحقل

#### التغييرات في القالب (`orders/templates/orders/order_form.html`):
- إضافة حقل المعاينة المرتبطة في النموذج
- إظهار الحقل فقط عند اختيار أنواع معينة (تركيب، تفصيل، إكسسوار)
- إضافة JavaScript للتحكم في إظهار/إخفاء الحقل

### 3. تحديث عرض "لا يوجد" في جدول الطلبات

**المتطلب:** إظهار "لا يوجد" بدلاً من "-" للتركيب والمعاينة في طلبات التفصيل والإكسسوار.

**التطبيق:** تم تحديث `orders/templates/orders/order_list.html`:
```html
<!-- حالة التركيب -->
{% if 'installation' in order.get_selected_types_list %}
    {% get_status_badge order.installation_status "installation" %}
{% elif 'tailoring' in order.get_selected_types_list or 'accessory' in order.get_selected_types_list %}
    <span class="text-muted">لا يوجد</span>
{% else %}
    <span class="text-muted">-</span>
{% endif %}

<!-- حالة المعاينة -->
{% if 'inspection' in order.get_selected_types_list %}
    {% get_status_badge order.inspection_status "inspection" %}
{% elif 'tailoring' in order.get_selected_types_list or 'accessory' in order.get_selected_types_list %}
    <span class="text-muted">لا يوجد</span>
{% else %}
    <span class="text-muted">-</span>
{% endif %}
```

### 4. تحديث عرض ملف المعاينة في تفاصيل الطلب

**الميزة:** إظهار ملف المعاينة المرتبطة إذا كانت موجودة، وإلا إظهار ملف المعاينة العادي.

**التطبيق:** تم تحديث `orders/templates/orders/order_detail.html`:
```html
{% if order.related_inspection and order.related_inspection.inspection_file %}
    <a href="{{ order.related_inspection.inspection_file.url }}" target="_blank" class="btn btn-sm btn-info">
        <i class="fas fa-file-alt"></i> عرض ملف المعاينة المرتبطة
    </a>
    <br><small class="text-muted">
        معاينة مرتبطة: {{ order.related_inspection.inspection_number }}
    </small>
{% else %}
    <!-- عرض ملف المعاينة العادي -->
{% endif %}
```

### 5. تحديث Views لتمرير العميل

**التطبيق:** تم تحديث `orders/views.py`:
- تمرير العميل إلى نموذج الطلب في `order_create`
- تمرير العميل إلى نموذج الطلب في `order_update`
- تصفية المعاينات حسب العميل

## الفوائد

1. **وضوح أكبر:** المستخدم يعرف متى لا ينطبق التركيب أو المعاينة على الطلب
2. **ربط أفضل:** يمكن ربط المعاينات بالطلبات مباشرة
3. **مرونة:** يمكن اختيار معاينة محددة للطلب
4. **اتساق:** نفس المنطق في جميع الصفحات

## الملفات المحدثة

- `orders/models.py` - إضافة حقل المعاينة المرتبطة
- `orders/forms.py` - إضافة الحقل إلى النموذج وتصفية المعاينات
- `orders/views.py` - تمرير العميل إلى النموذج
- `orders/templates/orders/order_form.html` - إضافة حقل المعاينة المرتبطة
- `orders/templates/orders/order_list.html` - تحديث عرض "لا يوجد"
- `orders/templates/orders/order_detail.html` - تحديث عرض ملف المعاينة
- `orders/migrations/0003_order_related_inspection.py` - migration جديد

## ملاحظات تقنية

- تم إضافة `related_name='related_orders'` لتجنب تضارب الأسماء
- تم تصفية المعاينات حسب العميل لسهولة الاختيار
- الحقل اختياري ولا يؤثر على الطلبات الموجودة
- يتم إظهار الحقل فقط للأنواع المناسبة (تركيب، تفصيل، إكسسوار) 