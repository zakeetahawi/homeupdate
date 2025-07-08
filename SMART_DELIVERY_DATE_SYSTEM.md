# 📅 نظام التاريخ الذكي لتسليم الطلبات

## 📋 نظرة عامة

تم تطوير نظام ذكي لعرض تاريخ التسليم في جداول الطلبات بحيث يعرض التاريخ المناسب حسب حالة الطلب:

- **عند إنشاء الطلب**: يظهر تاريخ التسليم المتوقع
- **عند اكتمال التصنيع**: يظهر تاريخ الإكمال الفعلي من المصنع
- **عند التسليم**: يظهر تاريخ التسليم الفعلي

## 🔧 المكونات المطورة

### 1. دوال ذكية في نموذج الطلب

```python
def get_smart_delivery_date(self):
    """إرجاع التاريخ المناسب حسب حالة الطلب"""
    if self.order_status in ['completed', 'ready_install', 'delivered']:
        # للطلبات المكتملة، عرض تاريخ الإكمال
        if hasattr(self, 'manufacturing_order') and self.manufacturing_order.completion_date:
            return self.manufacturing_order.completion_date.date()
        # للطلبات المسلمة، عرض تاريخ التسليم الفعلي
        elif self.order_status == 'delivered' and hasattr(self, 'manufacturing_order') and self.manufacturing_order.delivery_date:
            return self.manufacturing_order.delivery_date.date()
    
    # في الحالات الأخرى، عرض التاريخ المتوقع
    return self.expected_delivery_date

def get_delivery_date_label(self):
    """إرجاع تسمية التاريخ المناسبة حسب حالة الطلب"""
    if self.order_status in ['completed', 'ready_install']:
        return "تاريخ الإكمال"
    elif self.order_status == 'delivered':
        return "تاريخ التسليم"
    else:
        return "تاريخ التسليم المتوقع"
```

### 2. تحديث تلقائي لتاريخ الإكمال

```python
def update_order_status(self):
    """تحديث حالة الطلب وتاريخ الإكمال"""
    # تحديث تاريخ الإكمال عند الوصول لحالة مكتمل أو جاهز للتركيب
    if self.status in ['completed', 'ready_install'] and not self.completion_date:
        self.completion_date = timezone.now()
        ManufacturingOrder.objects.filter(pk=self.pk).update(
            completion_date=self.completion_date
        )
```

### 3. تحديث القوالب

#### قائمة الطلبات (`order_list.html`)
```html
<td>
    {% if order.get_smart_delivery_date %}
        <span class="d-block">{{ order.get_smart_delivery_date|date:"Y-m-d" }}</span>
        <small class="text-muted">{{ order.get_delivery_date_label }}</small>
    {% else %}
        <span class="text-muted">-</span>
    {% endif %}
</td>
```

#### تفاصيل الطلب (`order_detail.html`)
```html
<tr>
    <th>{{ order.get_delivery_date_label }}</th>
    <td>
        <span class="badge {% if order.order_status == 'delivered' %}bg-success{% elif order.order_status == 'completed' or order.order_status == 'ready_install' %}bg-warning text-dark{% else %}bg-info{% endif %}">
            <i class="fas fa-calendar me-1"></i>
            {{ order.get_smart_delivery_date|date:"Y-m-d" }}
        </span>
        <!-- معلومات إضافية حسب الحالة -->
    </td>
</tr>
```

## 📊 منطق العرض

| حالة الطلب | التاريخ المعروض | التسمية | المصدر |
|------------|----------------|---------|---------|
| `pending_approval` | التاريخ المتوقع | تاريخ التسليم المتوقع | `expected_delivery_date` |
| `pending` | التاريخ المتوقع | تاريخ التسليم المتوقع | `expected_delivery_date` |
| `in_progress` | التاريخ المتوقع | تاريخ التسليم المتوقع | `expected_delivery_date` |
| `ready_install` | تاريخ الإكمال | تاريخ الإكمال | `manufacturing_order.completion_date` |
| `completed` | تاريخ الإكمال | تاريخ الإكمال | `manufacturing_order.completion_date` |
| `delivered` | تاريخ التسليم | تاريخ التسليم | `manufacturing_order.delivery_date` |
| `rejected` | التاريخ المتوقع | تاريخ التسليم المتوقع | `expected_delivery_date` |
| `cancelled` | التاريخ المتوقع | تاريخ التسليم المتوقع | `expected_delivery_date` |

## 🎨 الألوان والتنسيق

### قائمة الطلبات
- **التاريخ الرئيسي**: يظهر بخط عادي
- **التسمية**: تظهر بخط صغير ولون رمادي

### تفاصيل الطلب
- **تاريخ متوقع**: Badge أزرق (`bg-info`)
- **تاريخ إكمال**: Badge أصفر (`bg-warning text-dark`)
- **تاريخ تسليم**: Badge أخضر (`bg-success`)

## 🔄 التحديث التلقائي

### عند تغيير حالة التصنيع:
1. **إلى `completed` أو `ready_install`**: يتم تعيين `completion_date` تلقائياً
2. **إلى `delivered`**: يتم تعيين `delivery_date` يدوياً من المستخدم
3. **تحديث الطلب**: يتم تحديث `order_status` و `tracking_status` تلقائياً

### الإشارات المستخدمة:
```python
@receiver(post_save, sender=ManufacturingOrder)
def update_related_models(sender, instance, **kwargs):
    """تحديث النماذج المرتبطة عند تحديث أمر التصنيع"""
    instance.update_order_status()
```

## 🧪 اختبار النظام

```python
# اختبار الحالات المختلفة
order = Order.objects.get(order_number='TEST-DELIVERY-001')

# 1. حالة قيد الانتظار
print(f'التاريخ الذكي: {order.get_smart_delivery_date()}')
print(f'تسمية التاريخ: {order.get_delivery_date_label()}')

# 2. حالة مكتمل
mfg_order.status = 'completed'
mfg_order.save()
print(f'التاريخ الذكي: {order.get_smart_delivery_date()}')  # تاريخ الإكمال
print(f'تسمية التاريخ: {order.get_delivery_date_label()}')  # "تاريخ الإكمال"

# 3. حالة تم التسليم
mfg_order.status = 'delivered'
mfg_order.delivery_date = timezone.now()
mfg_order.save()
print(f'التاريخ الذكي: {order.get_smart_delivery_date()}')  # تاريخ التسليم
print(f'تسمية التاريخ: {order.get_delivery_date_label()}')  # "تاريخ التسليم"
```

## ✅ الفوائد المحققة

1. **وضوح المعلومات**: المستخدم يرى التاريخ المناسب حسب حالة الطلب
2. **دقة البيانات**: التواريخ تعكس الحالة الفعلية للطلب
3. **تحديث تلقائي**: لا حاجة لتدخل يدوي لتحديث التواريخ
4. **تجربة مستخدم محسنة**: عرض واضح ومنظم للمعلومات
5. **مرونة في التطوير**: سهولة إضافة حالات جديدة مستقبلاً

## 🚀 الاستخدام

النظام يعمل تلقائياً في:
- **قائمة الطلبات**: `/orders/`
- **تفاصيل الطلب**: `/orders/<id>/`
- **تقارير الطلبات**: (يمكن تطبيقه لاحقاً)

## 📝 ملاحظات للتطوير المستقبلي

1. **قسم التركيبات**: يمكن إضافة منطق خاص عند تطوير قسم التركيبات
2. **إشعارات التسليم**: يمكن ربط النظام بإشعارات تلقائية
3. **تتبع الشحن**: يمكن إضافة تتبع مراحل الشحن
4. **تقارير متقدمة**: استخدام النظام في تقارير الأداء

---

**تم التطوير والاختبار بنجاح ✅**

*آخر تحديث: يوليو 2025* 