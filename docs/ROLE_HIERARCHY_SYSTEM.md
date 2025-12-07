# نظام التسلسل الهرمي للأدوار والصلاحيات

## نظرة عامة
تم تطوير نظام تسلسل هرمي متقدم للأدوار يدعم **وراثة الصلاحيات**، حيث يرث كل دور صلاحيات الأدوار الأدنى منه تلقائياً.

## التسلسل الهرمي للأدوار

```
المستوى 1: مدير عام (general_manager)
    ↓ يرى ويدير الكل
    
المستوى 2: 
    - مدير منطقة (region_manager) → يرث من مدير فرع
    - مسؤول مصنع (factory_manager)
    ↓
    
المستوى 3:
    - مدير فرع (branch_manager) → يرث من بائع
    - مسؤول معاينات (inspection_manager) → يرث من فني معاينة
    - مسؤول تركيبات (installation_manager)
    ↓
    
المستوى 4:
    - بائع (salesperson)
    - موظف مستودع (warehouse_staff)
    ↓
    
المستوى 5:
    - فني معاينة (inspection_technician)
    ↓
    
المستوى 6:
    - مستخدم عادي (user)
```

## الصلاحيات حسب الدور

### 1. مدير عام (المستوى 1)
- **جميع الصلاحيات**
- يرى ويدير كل شيء في النظام

### 2. مدير منطقة (المستوى 2)
**يرث من:** مدير فرع → بائع
- إدارة الفروع في منطقته
- رؤية جميع طلبات الفروع المُدارة
- إدارة المستخدمين في فروعه
- + جميع صلاحيات مدير الفرع والبائع

### 3. مدير فرع (المستوى 3)
**يرث من:** بائع
- رؤية جميع طلبات فرعه
- إدارة مستخدمي الفرع
- اعتماد الطلبات
- + جميع صلاحيات البائع

### 4. مسؤول مصنع (المستوى 2)
- رؤية جميع الطلبات
- إدارة التصنيع
- إدارة المخزون

### 5. مسؤول معاينات (المستوى 3)
**يرث من:** فني معاينة
- رؤية جميع المعاينات
- تعيين المعاينات للفنيين
- إدارة الفنيين
- + جميع صلاحيات فني المعاينة

### 6. مسؤول تركيبات (المستوى 3)
- رؤية جميع التركيبات
- تعيين التركيبات
- إدارة المركبين

### 7. بائع (المستوى 4)
- إنشاء طلبات جديدة
- رؤية طلباته فقط
- تعديل طلباته الخاصة

### 8. موظف مستودع (المستوى 4)
- إدارة مخزون مستودعه
- نقل المنتجات
- رؤية طلبات الفرع

### 9. فني معاينة (المستوى 5)
- رؤية المعاينات المعينة له
- تحديث حالة المعاينة

### 10. مستخدم عادي (المستوى 6)
- رؤية لوحة التحكم فقط

## الدوال الجديدة في نموذج User

### `get_user_role_display()`
```python
role_display = user.get_user_role_display()
# يرجع: "مدير عام", "مدير منطقة", إلخ...
```

### `get_role_level()`
```python
level = user.get_role_level()
# يرجع: 1, 2, 3, ... (المستوى في التسلسل الهرمي)
```

### `get_inherited_roles()`
```python
inherited = user.get_inherited_roles()
# مثال لمدير منطقة: ['branch_manager', 'salesperson']
```

### `get_all_permissions()`
```python
all_perms = user.get_all_permissions()
# يرجع قائمة بجميع الصلاحيات بما فيها الموروثة
```

### `has_role_permission(permission)`
```python
if user.has_role_permission('create_orders'):
    # السماح بإنشاء طلب
```

### `can_manage_user(other_user)`
```python
if manager.can_manage_user(employee):
    # المدير يمكنه إدارة الموظف
```

## الدوال الجديدة في permissions.py

### `user_has_role_or_higher(user, target_role)`
```python
if user_has_role_or_higher(request.user, 'branch_manager'):
    # المستخدم مدير فرع أو أعلى
```

### `get_users_manageable_by(user)`
```python
manageable_users = get_users_manageable_by(manager)
# جميع المستخدمين الذين يمكن للمدير إدارتهم
```

## أمثلة الاستخدام

### مثال 1: التحقق من الصلاحيات
```python
from orders.permissions import get_user_role_permissions

perms = get_user_role_permissions(request.user)
if perms['can_view_all_orders']:
    orders = Order.objects.all()
elif perms['can_view_branch_orders']:
    orders = Order.objects.filter(branch=request.user.branch)
```

### مثال 2: التحقق من إمكانية الإدارة
```python
# في صفحة إدارة المستخدمين
users = User.objects.all()
for user in users:
    if request.user.can_manage_user(user):
        # عرض أزرار التحرير والحذف
        pass
```

### مثال 3: الصلاحيات الموروثة
```python
# مدير منطقة يحصل تلقائياً على صلاحيات البائع
region_manager = User.objects.get(is_region_manager=True)
inherited = region_manager.get_inherited_roles()
# النتيجة: ['branch_manager', 'salesperson']

all_perms = region_manager.get_all_permissions()
# النتيجة تشمل صلاحيات: مدير منطقة + مدير فرع + بائع
```

## الفوائد

1. ✅ **عدم التكرار**: لا حاجة لتعريف الصلاحيات المكررة
2. ✅ **المرونة**: سهولة إضافة أدوار جديدة
3. ✅ **الوضوح**: التسلسل الهرمي واضح ومنطقي
4. ✅ **الأمان**: التحقق التلقائي من الصلاحيات
5. ✅ **سهولة الصيانة**: تغيير واحد يؤثر على جميع الأدوار التابعة

## ملاحظات مهمة

- المستوى الأقل = الصلاحيات الأعلى (المدير العام = مستوى 1)
- كل دور يرث تلقائياً صلاحيات الأدوار المحددة في `inherits_from`
- الوراثة تعمل بشكل تسلسلي (A يرث من B، B يرث من C → A يرث من B و C)
- المستخدم لا يمكنه إدارة نفسه
- المستخدم يمكنه فقط إدارة من هم أدنى منه في التسلسل الهرمي

## التاريخ
- **تم الإنشاء**: 7 ديسمبر 2025
- **الإصدار**: 1.0
- **الحالة**: نشط ✅
