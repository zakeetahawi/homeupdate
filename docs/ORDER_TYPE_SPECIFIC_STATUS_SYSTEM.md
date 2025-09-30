# نظام سجل الحالة المحدد حسب نوع الطلب

## نظرة عامة

تم تطوير نظام سجل الحالة ليستخدم الحالات المحددة حسب نوع الطلب بدلاً من الحالات العامة، مما يوفر معلومات أكثر دقة ووضوحاً.

## أنواع الطلبات والحالات المدعومة

### 1. طلبات المعاينة (Inspection)
**الحالات المتاحة:**
- `not_scheduled`: غير مجدولة
- `pending`: قيد الانتظار
- `scheduled`: مجدول
- `in_progress`: قيد التنفيذ
- `completed`: مكتملة
- `cancelled`: ملغية
- `postponed_by_customer`: مؤجل من طرف العميل

**الأيقونة:** `fas fa-search`
**اللون:** برتقالي (#fd7e14)

### 2. طلبات التركيب (Installation)
**الحالات المتاحة:**
- `needs_scheduling`: بحاجة جدولة
- `scheduled`: مجدول
- `in_installation`: قيد التركيب
- `completed`: مكتمل
- `cancelled`: ملغي
- `modification_required`: يحتاج تعديل
- `modification_scheduled`: جدولة التعديل
- `modification_in_progress`: التعديل قيد التنفيذ
- `modification_completed`: التعديل مكتمل

**الأيقونة:** `fas fa-tools`
**اللون:** بنفسجي (#6f42c1)

### 3. طلبات المنتجات (Products)
**الحالات المتاحة:**
- `pending`: قيد الانتظار
- `in_progress`: قيد التقطيع
- `completed`: مكتمل
- `rejected`: مرفوض

**الأيقونة:** `fas fa-cut`
**اللون:** أحمر (#dc3545)

### 4. طلبات الإكسسوار (Accessory)
**الحالات المتاحة:**
- `pending`: في الانتظار
- `approved`: موافق عليه
- `in_progress`: قيد التنفيذ
- `completed`: مكتمل
- `cancelled`: ملغي

**الأيقونة:** `fas fa-gem`
**اللون:** أخضر مائي (#20c997)

### 5. طلبات التسليم (Tailoring)
**الحالات المتاحة:**
- `pending`: في الانتظار
- `approved`: موافق عليه
- `in_progress`: قيد التنفيذ
- `completed`: مكتمل
- `cancelled`: ملغي

**الأيقونة:** `fas fa-shipping-fast`
**اللون:** أصفر (#ffc107)

## التحسينات المنجزة

### 1. تحسين نموذج OrderStatusLog

#### دوال جديدة:
```python
@classmethod
def get_status_choices_for_order_type(cls, order_types):
    """إرجاع خيارات الحالة المناسبة لنوع الطلب"""

def _get_order_type_name(self, order_types):
    """إرجاع اسم نوع الطلب بالعربية"""

def _status_label(self, code):
    """إرجاع تسمية الحالة حسب نوع الطلب"""
```

#### تحسين الخصائص:
- `change_icon`: أيقونات مخصصة حسب نوع الطلب
- `old_status_pretty` و `new_status_pretty`: عرض الحالات بالتسميات المحددة
- `get_detailed_description()`: وصف مفصل يتضمن نوع الطلب

### 2. تحسين القالب (Template)

#### أنماط CSS جديدة:
```css
.status-log-item[data-order-type*="inspection"] {
    border-left-color: #fd7e14;
    background: linear-gradient(135deg, #fff3cd 0%, #f8f9fa 100%);
}
```

#### عرض محسن:
- إضافة `data-order-type` للعناصر
- عرض نوع الطلب في badge
- ألوان وأيقونات مخصصة

### 3. تحسين Signals

#### دالة مساعدة:
```python
def _get_order_type_name_for_signal(order_types):
    """إرجاع اسم نوع الطلب للاستخدام في الـ signals"""
```

#### signals جديدة:
- `track_inspection_status_changes`: تتبع تغييرات المعاينة
- `track_cutting_status_changes`: تتبع تغييرات التقطيع

## أمثلة الاستخدام

### إنشاء سجل مخصص:
```python
OrderStatusLog.create_detailed_log(
    order=order,
    change_type='status',
    old_value='pending',
    new_value='in_progress',
    notes='تم بدء العمل على التركيب'
)
```

### الحصول على الحالات المتاحة:
```python
order_types = order.get_selected_types_list()
choices = OrderStatusLog.get_status_choices_for_order_type(order_types)
```

### عرض الوصف المحسن:
```python
log = OrderStatusLog.objects.get(pk=1)
description = log.get_detailed_description()
# النتيجة: "تم تبديل حالة التركيب من مجدول إلى قيد التركيب"
```

## الفوائد

1. **دقة أكبر**: عرض الحالات الفعلية لكل نوع طلب
2. **وضوح محسن**: أيقونات وألوان مميزة لكل نوع
3. **تتبع مفصل**: معلومات أكثر تفصيلاً عن التغييرات
4. **سهولة الفهم**: رسائل واضحة تتضمن نوع الطلب
5. **مرونة**: دعم إضافة أنواع طلبات جديدة

## النتائج

### قبل التحسين:
```
تم تبديل الحالة من قيد التصنيع إلى قيد التصنيع
تعديل الطلب: حالة التتبع: من "قيد المعالجة" إلى "قيد الانتظار"
```

### بعد التحسين:
```
🔧 تم تبديل حالة التركيب من مجدول إلى قيد التركيب
🔍 تم تبديل حالة المعاينة من قيد الانتظار إلى مكتملة
✂️ تم تبديل حالة التقطيع من قيد الانتظار إلى قيد التقطيع
💎 تم تبديل حالة الإكسسوار من في الانتظار إلى مكتمل
```

## الاختبار

تم اختبار النظام بنجاح على:
- ✅ طلبات المعاينة
- ✅ طلبات التركيب  
- ✅ طلبات المنتجات
- ✅ طلبات الإكسسوار
- ✅ طلبات التسليم

## الخلاصة

النظام الجديد يوفر تجربة مستخدم محسنة بشكل كبير مع معلومات دقيقة ومفصلة عن حالات الطلبات حسب نوعها، مما يساعد في تتبع تقدم العمل بوضوح ودقة.
