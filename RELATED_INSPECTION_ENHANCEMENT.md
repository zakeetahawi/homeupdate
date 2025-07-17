# تحديث حقل المعاينة المرتبطة

## نظرة عامة

تم تطبيق تحديثات جديدة لحقل المعاينة المرتبطة ليعرض فقط معاينات العميل المختار مع خيار "طرف العميل"، وتحديث عرض حالة المعاينة في جدول الطلبات.

## التحديثات المطبقة

### 1. تحديث حقل المعاينة المرتبطة

**الميزة الجديدة:** تصفية المعاينات حسب العميل المختار مع إضافة خيار "طرف العميل".

#### التغييرات في النموذج (`orders/forms.py`):
```python
# تصفية المعاينات حسب العميل إذا تم توفيره
if customer:
    from inspections.models import Inspection
    # إضافة خيار "طرف العميل" في بداية القائمة
    self.fields['related_inspection'].choices = [
        ('', 'اختر المعاينة المرتبطة'),
        ('customer_side', 'طرف العميل')
    ] + [
        (inspection.id, f"{inspection.inspection_number} - {inspection.created_at.strftime('%Y-%m-%d')}")
        for inspection in Inspection.objects.filter(customer=customer).order_by('-created_at')
    ]
```

#### إضافة حقل نوع المعاينة المرتبطة (`orders/models.py`):
```python
# نوع المعاينة المرتبطة
related_inspection_type = models.CharField(
    max_length=20,
    choices=[
        ('inspection', 'معاينة فعلية'),
        ('customer_side', 'طرف العميل'),
    ],
    blank=True,
    null=True,
    verbose_name='نوع المعاينة المرتبطة',
    help_text='نوع المعاينة المرتبطة بالطلب'
)
```

### 2. إضافة دالة عرض حالة المعاينة

**الميزة:** دالة جديدة لتحديد حالة المعاينة المعروضة بناءً على نوع المعاينة المرتبطة.

#### الدالة الجديدة (`orders/models.py`):
```python
def get_display_inspection_status(self):
    """إرجاع حالة المعاينة المعروضة بناءً على نوع المعاينة المرتبطة"""
    if self.related_inspection_type == 'customer_side':
        return {
            'status': 'customer_side',
            'text': 'طرف العميل',
            'badge_class': 'bg-info',
            'icon': 'fas fa-user'
        }
    elif self.related_inspection and self.related_inspection_type == 'inspection':
        # إرجاع حالة المعاينة الفعلية
        return {
            'status': self.related_inspection.status,
            'text': self.related_inspection.get_status_display(),
            'badge_class': self.related_inspection.get_status_badge_class(),
            'icon': self.related_inspection.get_status_icon()
        }
    else:
        # إذا لم تكن هناك معاينة مرتبطة
        return {
            'status': 'not_related',
            'text': 'لا يوجد',
            'badge_class': 'bg-secondary',
            'icon': 'fas fa-minus'
        }
```

### 3. تحديث عرض حالة المعاينة في جدول الطلبات

**الميزة:** عرض حالة المعاينة بناءً على ما تم تحديده في نموذج الطلب.

#### التطبيق في جدول الطلبات (`orders/templates/orders/order_list.html`):
```html
<!-- حالة المعاينة -->
<td class="text-center">
    {% if 'inspection' in order.get_selected_types_list %}
        {% with inspection_status=order.get_display_inspection_status %}
            <span class="badge {{ inspection_status.badge_class }}" style="font-size: 0.75rem;">
                <i class="{{ inspection_status.icon }} me-1"></i>
                {{ inspection_status.text }}
            </span>
        {% endwith %}
    {% elif 'tailoring' in order.get_selected_types_list or 'accessory' in order.get_selected_types_list %}
        <span class="text-muted">لا يوجد</span>
    {% else %}
        <span class="text-muted">-</span>
    {% endif %}
</td>
```

### 4. تحديث معالجة البيانات في Views

**الميزة:** معالجة صحيحة لقيم حقل المعاينة المرتبطة.

#### التطبيق في `orders/views.py`:
```python
# معالجة حقل المعاينة المرتبطة
related_inspection_value = form.cleaned_data.get('related_inspection')
if related_inspection_value == 'customer_side':
    order.related_inspection_type = 'customer_side'
    order.related_inspection = None
elif related_inspection_value and related_inspection_value != '':
    try:
        from inspections.models import Inspection
        inspection = Inspection.objects.get(id=related_inspection_value)
        order.related_inspection = inspection
        order.related_inspection_type = 'inspection'
    except Inspection.DoesNotExist:
        order.related_inspection = None
        order.related_inspection_type = None
else:
    order.related_inspection = None
    order.related_inspection_type = None
```

### 5. تحديث عرض المعاينة المرتبطة في تفاصيل الطلب

**الميزة:** عرض نوع المعاينة المرتبطة بشكل واضح.

#### التطبيق في تفاصيل الطلب (`orders/templates/orders/order_detail.html`):
```html
{% if order.related_inspection_type == 'customer_side' %}
    <span class="badge bg-info">
        <i class="fas fa-user me-1"></i>طرف العميل
    </span>
    <br><small class="text-muted">
        تم تحديد المعاينة كطرف العميل
    </small>
{% elif order.related_inspection and order.related_inspection.inspection_file %}
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

## الفوائد

1. **تصفية ذكية:** عرض فقط معاينات العميل المختار
2. **خيار مرن:** إمكانية اختيار "طرف العميل" كبديل للمعاينة الفعلية
3. **عرض واضح:** حالة المعاينة تعكس ما تم تحديده في النموذج
4. **اتساق:** نفس المنطق في جميع الصفحات
5. **سهولة الاستخدام:** واجهة واضحة ومفهومة

## الملفات المحدثة

- `orders/models.py` - إضافة حقل نوع المعاينة المرتبطة ودالة عرض الحالة
- `orders/forms.py` - تحديث تصفية المعاينات وإضافة تنظيف البيانات
- `orders/views.py` - تحديث معالجة البيانات في order_create و order_update
- `orders/templates/orders/order_list.html` - تحديث عرض حالة المعاينة
- `orders/templates/orders/order_detail.html` - تحديث عرض المعاينة المرتبطة
- `orders/migrations/0005_order_related_inspection_type.py` - migration جديد

## ملاحظات تقنية

- تم إضافة حقل `related_inspection_type` لتخزين نوع المعاينة المرتبطة
- يتم تصفية المعاينات حسب العميل المختار
- خيار "طرف العميل" يظهر في بداية القائمة
- يتم معالجة البيانات بشكل صحيح في views
- عرض الحالة يعكس ما تم تحديده في النموذج 