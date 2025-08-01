# نظام داشبورد الطلبات الجديد

## نظرة عامة

تم إنشاء نظام داشبورد شامل لإدارة الطلبات مع أربع بطاقات رئيسية لأنواع الطلبات المختلفة وصفحات منفصلة لكل نوع.

## الميزات الجديدة

### 1. الداشبورد الرئيسي (`/orders/`)
- **4 بطاقات تفاعلية** لأنواع الطلبات:
  - 🔍 **طلبات المعاينة** - لون بنفسجي
  - 🔧 **طلبات التركيب** - لون وردي
  - 💎 **طلبات الإكسسوار** - لون أزرق
  - 🚚 **طلبات التسليم** - لون أخضر

- **إحصائيات عامة**:
  - إجمالي الطلبات
  - طلبات قيد الانتظار
  - طلبات مكتملة
  - إجمالي الإيرادات

- **أحدث الطلبات** مع إجراءات سريعة

### 2. الصفحات المنفصلة

#### أ) صف��ة طلبات المعاينة (`/orders/inspection/`)
- تصفية خاصة بطلبات المعاينة فقط
- إحصائيات: إجمالي، في الانتظار، قيد التنفيذ، مكتملة
- عرض حالة المعاينة وتاريخ المعاينة المتوقع
- بحث وتصفية متقدمة

#### ب) صفحة طلبات التركيب (`/orders/installation/`)
- تصفية خاصة بطلبات التركيب فقط
- إحصائيات: إجمالي، بحاجة جدولة، قيد التركيب، مكتملة
- عرض حالة التصنيع وحالة التركيب
- عرض تاريخ الجدولة وعنوان التركيب

#### ج) صفحة طلبات الإكسسوار (`/orders/accessory/`)
- تصفية خاصة بطلبات الإكسسوار فقط
- إحصائيات: إجمالي، في الانتظار، جاهز للتسليم، تم التسليم
- عرض المنتجات والمبالغ
- عرض نوع التسليم (منزلي/فرع)

#### د) صفحة طلبات التسليم (`/orders/tailoring/`)
- تصفية خاصة بطلبات التسليم فقط
- إحصائيات: إجمالي، قيد التصنيع، جاهز للتسليم، تم التسليم
- عرض رقم العقد وملف العق��
- تصفية إضافية برقم العقد ونوع التسليم

### 3. الجدول الشامل (`/orders/all/`)
- يحتوي على جميع الطلبات (الصفحة القديمة)
- تم الاحتفاظ بجميع الميزات الموجودة

## نظام الصلاحيات

### الصلاحيات المطبقة:
1. **عرض الطلبات الخاصة**: المستخدم يرى طلباته فقط
2. **عرض طلبات الفرع**: مدير الفرع يرى جميع طلبات فرعه
3. **عرض جميع الطلبات**: المدير العام يرى جميع طلبات النظام

### المجموعات:
- **بائع**: يمكنه إنشاء وعرض وتعديل طلباته الخاصة
- **مدير فرع**: يمكنه إدارة جميع طلبات الفرع
- **مدير عام**: يمكنه إدارة جميع طلبات النظام

## الملفات الجديدة

### 1. Templates
- `orders/templates/orders/orders_dashboard.html` - الداشبورد الرئيسي
- `orders/templates/orders/inspection_orders.html` - صفحة طلبات المعاينة
- `orders/templates/orders/installation_orders.html` - صفحة طلبات التركيب
- `orders/templates/orders/accessory_orders.html` - صفحة طلبات الإ��سسوار
- `orders/templates/orders/tailoring_orders.html` - صفحة طلبات التسليم

### 2. Views
- `orders/dashboard_views.py` - دوال العرض للداشبورد والصفحات الجديدة
- `orders/permissions.py` - نظام الصلاحيات البسيط

### 3. Management Commands
- `orders/management/commands/setup_orders_permissions.py` - إعداد الصلاحيات

### 4. URLs
- تم تحديث `orders/urls.py` لإضافة الروابط الجديدة

## كيفية الاستخدام

### 1. إعداد الصلاحيات (اختياري)
```bash
python manage.py setup_orders_permissions
```

### 2. الوصول للنظام
- **الداشبورد الرئيسي**: `/orders/`
- **طلبات المعاينة**: `/orders/inspection/`
- **طلبات التركيب**: `/orders/installation/`
- **طلبات الإكسسوار**: `/orders/accessory/`
- **طلبات التسليم**: `/orders/tailoring/`
- **الجدول الشامل**: `/orders/all/`

### 3. التنقل
- من الداشبورد: اضغط على أي بطاقة للانتقال لصفحة النوع المحدد
- من أي صفحة: استخدم الروابط في الإجراءات السريعة

## الهوية البصرية

### الألوان ��لمستخدمة:
- **المعاينة**: بنفسجي (`#667eea` إلى `#764ba2`)
- **التركيب**: وردي (`#f093fb` إلى `#f5576c`)
- **الإكسسوار**: أزرق (`#4facfe` إلى `#00f2fe`)
- **التسليم**: أخضر (`#43e97b` إلى `#38f9d7`)

### التأثيرات:
- تأثيرات hover تفاعلية للبطاقات
- انتقالات سلسة
- أيقونات Font Awesome مناسبة لكل نوع

## التوافق

- متوافق مع النظام الحالي بالكامل
- لا يؤثر على الوظائف الموجودة
- يمكن الوصول للجدول القديم عبر `/orders/all/`

## المتطلبات

- Django 3.2+
- Bootstrap 5
- Font Awesome 6
- النظام الحالي للطلبات

## الصيانة

### إضافة نوع طلب جديد:
1. أضف النوع في `Order.ORDER_TYPES`
2. أنشئ template جديد
3. أضف view في `dashboard_views.py`
4. أضف URL في `urls.py`
5. أضف بطاقة في الداشبورد

### تخصيص الصلاحيات:
- عدّل `permissions.py` لإضافة منطق صلاحيات جديد
- استخدم `setup_orders_permissions` لإنشاء صلاحيات إضافية

## الدعم

للمساعدة أو الاستفسارات، راج��:
- كود المشروع في `/orders/`
- ملفات التوثيق الأخرى
- تعليقات الكود في الملفات