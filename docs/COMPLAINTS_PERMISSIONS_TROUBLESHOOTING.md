# دليل استكشاف أخطاء صلاحيات نظام الشكاوى وإصلاحها

## المشكلة الأساسية
كانت المشكلة الرئيسية هي عدم وجود المجموعات المطلوبة لنظام الشكاوى في قاعدة البيانات، مما أدى إلى ظهور خطأ 403 (Forbidden) عند محاولة تعديل حالة الشكاوى.

## المجموعات المطلوبة
يحتاج نظام الشكاوى إلى المجموعات التالية:

1. **Complaints_Supervisors** - مشرفو الشكاوى
2. **Managers** - المدراء
3. **Complaints_Managers** - مدراء الشكاوى
4. **Complaints_Staff** - موظفو الشكاوى

## الحل المطبق

### 1. إنشاء المجموعات المطلوبة
```bash
python manage.py setup_complaints_permissions --create-groups
```

### 2. إعداد الصلاحيات
```bash
python manage.py setup_complaints_permissions --setup-permissions
```

### 3. إسناد المستخدمين
```bash
python manage.py setup_complaints_permissions --assign-users
```

### 4. تنفيذ جميع العمليات مرة واحدة
```bash
python manage.py setup_complaints_permissions --all
```

## فحص الصلاحيات

### فحص المجموعات الموجودة
```python
from django.contrib.auth.models import Group

# فحص المجموعات المطلوبة
required_groups = ['Complaints_Supervisors', 'Managers', 'Complaints_Managers']
for group_name in required_groups:
    exists = Group.objects.filter(name=group_name).exists()
    print(f'{group_name}: {"موجود" if exists else "غير موجود"}')
```

### فحص صلاحيات مستخدم معين
```python
from accounts.models import User

user = User.objects.get(username='اسم_المستخدم')
print(f'في مجموعة Complaints_Supervisors: {user.groups.filter(name="Complaints_Supervisors").exists()}')
print(f'في مجموعة Managers: {user.groups.filter(name="Managers").exists()}')
```

### فحص صلاحيات الشكاوى
```python
from complaints.models import ComplaintUserPermissions

# فحص صلاحيات مستخدم
try:
    permissions = user.complaint_permissions
    print(f'يمكن تعديل جميع الشكاوى: {permissions.can_edit_all_complaints}')
    print(f'يمكن عرض جميع الشكاوى: {permissions.can_view_all_complaints}')
except ComplaintUserPermissions.DoesNotExist:
    print('لا توجد صلاحيات شكاوى لهذا المستخدم')
```

## الأخطاء الشائعة وحلولها

### خطأ 403 عند تعديل الشكوى
**السبب:** المستخدم ليس في المجموعات المطلوبة
**الحل:**
```bash
python manage.py setup_complaints_permissions --assign-users
```

### عدم ظهور خيارات تعديل الشكوى
**السبب:** عدم وجود صلاحيات في ComplaintUserPermissions
**الحل:**
```python
from complaints.models import ComplaintUserPermissions
from accounts.models import User

user = User.objects.get(username='اسم_المستخدم')
permissions, created = ComplaintUserPermissions.objects.get_or_create(
    user=user,
    defaults={
        'can_edit_all_complaints': True,
        'can_view_all_complaints': True,
        'can_be_assigned_complaints': True,
        'is_active': True
    }
)
```

### عدم وجود المجموعات
**السبب:** لم يتم إنشاء المجموعات بعد
**الحل:**
```bash
python manage.py setup_complaints_permissions --create-groups
```

## نصائح للصيانة

### 1. فحص دوري للصلاحيات
قم بتشغيل هذا الأمر بشكل دوري للتأكد من سلامة الصلاحيات:
```bash
python manage.py setup_complaints_permissions --all
```

### 2. إضافة مستخدم جديد لإدارة الشكاوى
```python
from django.contrib.auth.models import Group
from accounts.models import User
from complaints.models import ComplaintUserPermissions

# إنشاء أو تحديث صلاحيات المستخدم
user = User.objects.get(username='اسم_المستخدم')
permissions, created = ComplaintUserPermissions.objects.get_or_create(
    user=user,
    defaults={
        'can_edit_all_complaints': True,
        'can_view_all_complaints': True,
        'can_be_assigned_complaints': True,
        'is_active': True
    }
)

# إضافة المستخدم للمجموعات
groups = Group.objects.filter(name__in=['Complaints_Supervisors', 'Managers'])
user.groups.add(*groups)
```

### 3. إزالة صلاحيات مستخدم
```python
user = User.objects.get(username='اسم_المستخدم')

# إزالة من المجموعات
complaint_groups = Group.objects.filter(name__startswith='Complaints_')
user.groups.remove(*complaint_groups)

# تعطيل الصلاحيات
if hasattr(user, 'complaint_permissions'):
    user.complaint_permissions.is_active = False
    user.complaint_permissions.save()
```

## مراقبة الأداء

### عدد المستخدمين في كل مجموعة
```python
from django.contrib.auth.models import Group

groups = ['Complaints_Supervisors', 'Managers', 'Complaints_Managers', 'Complaints_Staff']
for group_name in groups:
    try:
        group = Group.objects.get(name=group_name)
        count = group.user_set.count()
        print(f'{group_name}: {count} مستخدم')
    except Group.DoesNotExist:
        print(f'{group_name}: غير موجود')
```

### إحصائيات الصلاحيات
```python
from complaints.models import ComplaintUserPermissions

total = ComplaintUserPermissions.objects.count()
active = ComplaintUserPermissions.objects.filter(is_active=True).count()
can_edit_all = ComplaintUserPermissions.objects.filter(can_edit_all_complaints=True).count()

print(f'إجمالي المستخدمين: {total}')
print(f'المستخدمين النشطين: {active}')
print(f'يمكنهم تعديل جميع الشكاوى: {can_edit_all}')
```

## الملفات المتأثرة
- `complaints/api_views.py` - فحص الصلاحيات
- `complaints/models.py` - نموذج ComplaintUserPermissions
- `complaints/management/commands/setup_complaints_permissions.py` - أمر الإعداد
- `crm/urls.py` - مسارات النظام

## التحقق من نجاح الإصلاح
بعد تطبيق الحل، يجب أن تتمكن من:
1. تعديل حالة الشكاوى دون ظهور خطأ 403
2. رؤية جميع خيارات التحكم في الشكاوى
3. إسناد الشكاوى وتصعيدها
4. إضافة ملاحظات وتحديثات

## الدعم
في حالة استمرار المشاكل، تحقق من:
1. سجلات الأخطاء في Django
2. إعدادات قاعدة البيانات
3. صلاحيات المستخدم الحالي
4. حالة الخدمات (Redis, Celery)
