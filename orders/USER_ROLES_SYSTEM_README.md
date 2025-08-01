# نظام الأدوار والصلاحيات الشامل - قسم الطلبات

## نظرة عامة

تم تطوير نظام شامل للأدوار والصلاحيات في قسم الطلبات يضمن أن كل مستخدم يرى ويتعامل مع الطلبات حسب دوره ومسؤولياته.

## الأدوار المتاحة

### 1. البائع (Salesperson)
- **الصلاحيات**: يرى طلباته الشخصية فقط
- **الوصول**: الطلبات التي أنشأها بنفسه
- **الإجراءات**: عرض، إضافة، تعديل طلباته فقط

### 2. مدير الفرع (Branch Manager)
- **الصلاحيات**: يرى جميع طلبات فرعه
- **الوصول**: جميع الطلبات في الفرع المحدد
- **الإجراءات**: عرض، إضافة، تعديل، حذف طلبات الفرع

### 3. مدير المنطقة (Region Manager)
- **الصلاحيات**: يرى طلب��ت الفروع المُدارة
- **الوصول**: الطلبات في الفروع المحددة له
- **الإجراءات**: عرض، إضافة، تعديل، حذف طلبات الفروع المُدارة
- **ميزة خاصة**: يمكن تحديد عدة فروع ليكون مسؤولاً عنها

### 4. المدير العام (General Manager)
- **الصلاحيات**: يرى جميع الطلبات في النظام
- **الوصول**: جميع الطلبات بدون قيود
- **الإجراءات**: جميع الإجراءات المتاحة

### 5. فني المعاينة (Inspection Technician)
- **الصلاحيات**: يرى طلبات المعاينة فقط
- **الوصول**: الطلبات التي تحتوي على نوع "معاينة"
- **الإجراءات**: عرض وإنشاء طلبات المعاينة

## قواعد النظام

### 1. دور واحد فقط
- لا يمكن للمستخدم أن يكون له أكثر من دور واحد في نفس الوقت
- يتم التحقق من هذا عند حفظ بيانات المستخدم
- رسالة خطأ تظهر عند محاولة اختيار أكثر من دور

### 2. الصلاحيات التدرجية
- المدير العام > مدير المنطقة > مدير الفرع > البائع > فني المعاينة
- كل مستوى أعلى يشمل صلاحيات المستوى الأدنى ويزيد عليها

### 3. عدم وجود طلبات
- إذا لم يكن للمستخدم طلبات حسب دوره، لن يظهر له أي طلب
- الداشبورد سيظهر إحصائيات فارغة
- رسائل واضحة تشير إلى عدم وجود طلبات

## الملفات المُحدثة

### 1. نموذج المستخدم (`accounts/models.py`)
```python
# الحقول الجديدة
is_salesperson = models.BooleanField(default=False, verbose_name="بائع")
is_branch_manager = models.BooleanField(default=False, verbose_name="مدير فرع")
is_region_manager = models.BooleanField(default=False, verbose_name="مدير منطقة")
is_general_manager = models.BooleanField(default=False, verbose_name="مدير عام")
managed_branches = models.ManyToManyField("Branch", blank=True, related_name="region_managers", verbose_name="الفروع المُدارة")

# الدوال الجديدة
def get_user_role(self)
def get_user_role_display(self)
def clean(self)  # للتحقق من دور واحد فقط
```

### 2. نظام الصلاحيات (`orders/permissions.py`)
```python
# الدوال الرئيسية
get_user_orders_queryset(user)  # الحصول على الطلبات حسب الدور
can_user_view_order(user, order)  # التحقق من إمكانية العرض
can_user_edit_order(user, order)  # التحقق من إمكانية التعديل
can_user_delete_order(user, order)  # التحقق من إمكانية الحذف
get_user_role_permissions(user)  # الحصول على صلاحيات الدور
```

### 3. دوال العرض (`orders/dashboard_views.py`)
- تطبيق الصلاحيات على جميع الصفحات
- التحقق من الصلاحيات قبل عرض المحتوى
- إحصائيات مخصصة حسب الدور

### 4. إدارة المستخدمين (`accounts/admin.py`)
- عرض الدور في قائمة المستخدمين
- تصفية حسب الأدوار
- إدارة الفروع المُدارة لمدير المنطقة

## كيفية الاستخدام

### 1. تعيين دور للمستخدم

#### من لوحة الإدارة:
1. اذهب إلى إدارة المستخدمين
2. اختر المستخدم المطلوب
3. في قسم "الصلاحيات"، اختر الدور المناسب
4. للمدير المنطقة: حدد الفروع المُدارة
5. احفظ الت��ييرات

#### من سطر الأوامر:
```bash
# تعيين بائع
python manage.py setup_user_roles --user-id 1 --role salesperson

# تعيين مدير فرع
python manage.py setup_user_roles --user-id 2 --role branch_manager --branch-id 1

# تعيين مدير منطقة
python manage.py setup_user_roles --user-id 3 --role region_manager --managed-branches 1 2 3

# تعيين مدير عام
python manage.py setup_user_roles --user-id 4 --role general_manager
```

### 2. التحقق من الصلاحيات

```python
from orders.permissions import get_user_role_permissions

# الحصول على صلاحيات المستخدم
permissions = get_user_role_permissions(user)

# التحقق من صلاحية معينة
if permissions['can_view_all_orders']:
    # المستخدم يمكنه رؤية جميع الطلبات
    pass
```

## الداشبورد والواجهات

### 1. الداشبورد الرئيسي
- يظهر معلومات الدور في الهيدر
- إحصائيات مخصصة حسب الصلاحيات
- بطاقات تفاعلية لأنواع الطلبات المختلفة

### 2. الصفحات المنفصلة
- **طلبات المعاينة**: `/orders/inspection/`
- **طلبات التركيب**: `/orders/installation/`
- **طلبات الإكسسوار**: `/orders/accessory/`
- **طلبات التسليم**: `/orders/tailoring/`

### 3. المعلومات المعروضة
- **البائع**: "طلباتي الشخصية"
- **مدير الفرع**: "فرع [اسم الفرع]"
- **مدير المنطقة**: "مسؤول عن [عدد] فرع"
- **المدير العام**: جميع الطلبات

## أمثلة عملية

### مثال 1: بائع جديد
```python
# إنشاء بائع جديد
user = User.objects.create_user(username='salesperson1', password='password')
user.is_salesperson = True
user.save()

# البائع سيرى طلباته فقط
orders = get_user_orders_queryset(user)  # طلبات created_by=user فقط
```

### مثال 2: مدير منطقة
```python
# إنشاء مدير منطقة
user = User.objects.create_user(username='region_manager1', password='password')
user.is_region_manager = True
user.save()

# تحديد الفروع المُدارة
branches = Branch.objects.filter(id__in=[1, 2, 3])
user.managed_branches.set(branches)

# المدير سيرى طلبات الفروع المحددة فقط
orders = get_user_orders_queryset(user)  # طلبات branch__in=branches
```

## الأمان والحماية

### 1. التحقق من الصلاحيات
- جميع الصفحات محمية بـ `@login_required`
- التحقق من الصلاحيات في بداية كل دالة عرض
- منع الوصول غير المصرح به

### 2. حماية البيانات
- كل مستخدم يرى بياناته فقط حسب دوره
- لا يمكن الوصول لطلبات خارج النطاق المسموح
- تشفير وحماية المعلومات الحساسة

### 3. تسجيل العمليات
- تسجيل جميع العمليات المهمة
- مراقبة محاولات الوصول غير المصرح بها
- إشعارات للمدراء عند الحاجة

## استكشاف الأخطاء

### 1. المستخدم لا يرى أي طلبات
- تحقق من أن له دور محدد
- تحقق من أن له فرع (للمدير الفرع)
- تحقق من الفروع المُدارة (لمدير المنطقة)
- تحقق من وجود طلبات فعلية

### 2. خطأ "أكثر من دور واحد"
- تأكد من اختيار دور واحد فقط
- احفظ المستخدم بعد إلغاء الأدوار الأخرى

### 3. صلاحيات غير صحيحة
- استخدم أمر `setup_user_roles` لإعادة تعيين الص��احيات
- تحقق من وجود الصلاحيات في قاعدة البيانات

## التطوير المستقبلي

### 1. ميزات مقترحة
- نظام الموافقات المتدرج
- إشعارات مخصصة حسب الدور
- تقارير مفصلة لكل دور
- نظام المهام والتكليفات

### 2. تحسينات الأداء
- تحسين استعلامات قاعدة البيانات
- تخزين مؤقت للصلاحيات
- فهرسة أفضل للجداول

### 3. واجهة المستخدم
- لوحة تحكم مخصصة لكل دور
- اختصارات سريعة
- تخصيص الألوان والثيمات

---

## الدعم والمساعدة

للحصول على المساعدة أو الإبلاغ عن مشاكل:
- راجع هذا الدليل أولاً
- تحقق من ملفات السجل
- استخدم أوامر الإدارة المتاحة
- اتصل بفريق التطوير عند الحاجة

**تم التطوير بواسطة**: zakee tahawi  
**التاريخ**: 2025-07-29  
**الإصدار**: 1.0.0