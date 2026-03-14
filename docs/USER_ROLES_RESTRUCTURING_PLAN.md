# خطة إعادة هيكلة نظام الأدوار والصلاحيات
# User Roles & Permissions System Restructuring Plan

> **التاريخ**: 2026-03-13  
> **الحالة**: ✅ مكتملة — تم تنفيذ المراحل 1-5  
> **المسؤول**: فريق التطوير

---

## الوضع الحالي — تحليل النظام

### المشاكل المحددة

| # | المشكلة | التأثير | الأولوية |
|---|---------|---------|----------|
| 1 | 16 حقل Boolean منفصل على نموذج User | كل دور جديد = migration + admin + views + signals | عالية |
| 2 | `clean()` يمنع تعدد الأدوار (boolean واحد فقط) | لا يمكن تعيين موظف كبائع + موظف مستودع | عالية |
| 3 | 3 أنظمة متوازية غير متكاملة | Boolean fields + UserRole M2M + Django Groups | متوسطة |
| 4 | نموذج الأدمن يعرض كل الحقول دائماً | 12 قسم مشتت، الحقول غير المطلوبة ظاهرة | عالية |
| 5 | UserRole M2M موجود لكن غير مستخدم فعلياً | ازدواجية بلا فائدة، تشتت المطورين | منخفضة |
| 6 | لا يوجد ملخص للصلاحيات الفعلية | المدير لا يرى ماذا يستطيع المستخدم فعله | متوسطة |

### الهيكل الحالي للأدوار

```
User Model (accounts/models.py)
├── 13 حقل دور (is_salesperson, is_branch_manager, ...)
├── 2 علامة نوع بيع (is_wholesale, is_retail)
├── 3 صلاحيات خاصة (can_export, can_edit_price, can_apply_administrative_discount)
├── ROLE_HIERARCHY dict (16 مدخل مع مستويات 0-6 وسلسلة توريث)
├── get_user_role() → يرجع دور واحد فقط
├── get_role_permissions() → صلاحيات الدور الأساسي + الموروث
└── clean() → يمنع أكثر من boolean واحد

Secondary Systems (غير مفعّلة بالكامل):
├── Role model + UserRole M2M → أدوار مخصصة مع صلاحيات Django
├── Django Groups → مجموعات صلاحيات (تم إنشاء 3 مجموعات للمبيعات الخارجية)
└── Django Permissions → صلاحيات فردية عبر user_permissions
```

---

## المراحل التنفيذية

---

### المرحلة 1: أدمن ديناميكي (JS) ✅ مكتمل

> **الحالة**: ✅ تم التنفيذ — 2026-03-13  
> **الأثر على الإنتاج**: صفر — تغيير عرض فقط  
> **الملفات المتأثرة**:
> - `accounts/static/accounts/admin/js/dynamic_user_admin.js` ← **جديد**
> - `accounts/static/accounts/admin/css/dynamic_user_admin.css` ← **جديد**
> - `accounts/admin.py` — إضافة `class Media` + إزالة `collapse` من أقسام الأدوار

#### ما تم تنفيذه:
1. **واجهة اختيار القسم الوظيفي** — شرائح (Chips) تفاعلية تحت "الحالة والنظام"
2. **إخفاء/إظهار ديناميكي** — أقسام الأدوار تظهر فقط عند اختيار القسم
3. **حقول شرطية** — `managed_branches` تظهر فقط عند تفعيل مدير فرع/منطقة/مبيعات
4. **حقول شرطية** — `assigned_warehouse/warehouses` تظهر فقط عند تفعيل موظف مستودع
5. **حقول شرطية** — `is_wholesale/is_retail` تظهر فقط عند تفعيل أحد أدوار المبيعات
6. **شريط ملخص الأدوار** — يعرض badges بالأدوار المفعّلة
7. **تفعيل تلقائي** — عند فتح مستخدم له أدوار، تظهر الأقسام المعنية تلقائياً
8. **تنسيقات CSS** — تصميم احترافي مع دعم RTL و Responsive

#### كيفية الاختبار:
```bash
# تشغيل السيرفر
python manage.py runserver

# الذهاب لصفحة تعديل مستخدم
# http://localhost:8000/admin/accounts/user/132/change/

# الاختبار:
# 1. يجب أن تظهر شرائح الأقسام
# 2. الأقسام المخفية تظهر عند النقر على الشريحة
# 3. المستخدم الذي له دور مفعّل يظهر قسمه مفتوحاً
```

---

### المرحلة 2: تفعيل تعدد الأدوار

> **الحالة**: 🔴 لم يبدأ  
> **الأثر على الإنتاج**: متوسط — تغيير في منطق الأدوار  
> **المخاطر**: يجب اختبار كل الـ views التي تعتمد على `get_user_role()`

#### 2.1 — حذف validation تعدد الأدوار

**الملف**: `accounts/models.py` — method `clean()`

```python
# الوضع الحالي (يمنع التعدد):
def clean(self):
    roles = [
        self.is_salesperson, self.is_branch_manager, ...
    ]
    active_roles = sum(roles)
    if active_roles > 1:
        raise ValidationError(_("لا يمكن اختيار أكثر من دور وظيفي واحد للمستخدم"))

# المطلوب:
# إما حذف الشرط بالكامل
# أو تغييره لتحذير بدون منع:
def clean(self):
    # السماح بتعدد الأدوار
    pass
```

#### 2.2 — إضافة methods جديدة

```python
# إضافة في accounts/models.py:

def get_active_roles(self) -> list[str]:
    """إرجاع قائمة بكل الأدوار المفعّلة"""
    roles = []
    role_map = {
        'is_salesperson': 'salesperson',
        'is_branch_manager': 'branch_manager',
        'is_region_manager': 'region_manager',
        'is_sales_manager': 'sales_manager',
        'is_factory_manager': 'factory_manager',
        'is_factory_accountant': 'factory_accountant',
        'is_factory_receiver': 'factory_receiver',
        'is_inspection_technician': 'inspection_technician',
        'is_inspection_manager': 'inspection_manager',
        'is_installation_manager': 'installation_manager',
        'is_traffic_manager': 'traffic_manager',
        'is_warehouse_staff': 'warehouse_staff',
        'is_decorator_dept_manager': 'decorator_dept_manager',
        'is_decorator_dept_staff': 'decorator_dept_staff',
    }
    for field, role_key in role_map.items():
        if getattr(self, field, False):
            roles.append(role_key)
    return roles

def get_primary_role(self) -> str:
    """إرجاع الدور الأعلى مستوى (أقل level)"""
    roles = self.get_active_roles()
    if not roles:
        return 'user'
    if self.is_superuser:
        return 'system_admin'
    return min(roles, key=lambda r: self.ROLE_HIERARCHY.get(r, {}).get('level', 99))

def get_all_permissions(self) -> set[str]:
    """جمع صلاحيات كل الأدوار المفعّلة (مع التوريث)"""
    perms = set()
    for role in self.get_active_roles():
        perms.update(self._collect_role_permissions(role))
    return perms

def _collect_role_permissions(self, role_key: str) -> set[str]:
    """جمع صلاحيات دور معين + وراثته"""
    role_data = self.ROLE_HIERARCHY.get(role_key, {})
    perms = set(role_data.get('permissions', []))
    for parent in role_data.get('inherits_from', []):
        perms.update(self._collect_role_permissions(parent))
    return perms
```

#### 2.3 — تحديث get_user_role() (backward compatible)

```python
def get_user_role(self) -> str:
    """يرجع الدور الأساسي — للتوافق مع الكود القديم"""
    return self.get_primary_role()

def get_user_role_display(self) -> str:
    """يرجع اسم الدور الأعلى بالعربي"""
    role = self.get_primary_role()
    return self.ROLE_HIERARCHY.get(role, {}).get('display', 'مستخدم عادي')

def get_active_roles_display(self) -> str:
    """يرجع كل الأدوار بالعربي مفصولة بفاصلة"""
    roles = self.get_active_roles()
    displays = [self.ROLE_HIERARCHY.get(r, {}).get('display', r) for r in roles]
    return '، '.join(displays) if displays else 'مستخدم عادي'
```

#### 2.4 — تحديث has_role_permission()

```python
def has_role_permission(self, permission: str) -> bool:
    """فحص هل المستخدم يملك صلاحية من أي من أدواره"""
    if self.is_superuser:
        return True
    return permission in self.get_all_permissions()
```

#### 2.5 — الملفات التي تحتاج تعديل

| الملف | السبب |
|-------|-------|
| `accounts/models.py` | إضافة methods + حذف clean validation |
| `accounts/admin.py` | تحديث `get_user_role_display` في list_display |
| `accounts/mixins.py` | التأكد من عمل mixins مع تعدد الأدوار |
| `accounts/views.py` | فحص أي views تعتمد على `get_user_role()` |
| `external_sales/mixins.py` | فحص التوافق |
| `orders/views.py` | فحص فلترة الطلبات حسب الدور |
| `manufacturing/views.py` | فحص صلاحيات التصنيع |
| `inspections/views.py` | فحص صلاحيات المعاينات |
| `installations/views.py` | فحص صلاحيات التركيبات |

#### 2.6 — خطة الاختبار

```bash
# اختبارات يدوية:
# 1. إنشاء مستخدم بدورين: بائع + موظف مستودع
# 2. تسجيل دخول → التأكد من ظهور قوائم المبيعات والمستودع
# 3. فحص الصلاحيات: يجب أن تتجمع صلاحيات الدورين
# 4. فحص get_primary_role(): يجب أن يرجع الأعلى

# اختبارات آلية:
pytest accounts/tests/ -v
python manage.py test accounts.tests.test_roles
```

---

### المرحلة 3: صفحة إدارة مستخدمين مخصصة

> **الحالة**: 🔴 لم يبدأ  
> **الأثر على الإنتاج**: صفر — صفحة جديدة بالكامل  
> **التعقيد**: عالي

#### 3.1 — الهدف

إنشاء صفحة إدارة مستخدمين احترافية **خارج Django Admin** بنفس تصميم النظام (Bootstrap 5 RTL)، تكون بديلاً أسهل وأجمل.

#### 3.2 — التصميم المقترح

```
URL: /accounts/manage/users/
URL: /accounts/manage/users/<id>/edit/
URL: /accounts/manage/users/create/
```

**مكونات الصفحة:**

```
┌──────────────────────────────────────────────────────┐
│  👤 إدارة المستخدم: أحمد محمد                        │
├───────┬──────────────────────────────────────────────┤
│       │                                               │
│ قائمة │  📋 البيانات الأساسية [بطاقة]                │
│ جانبية│  ├─ الاسم، البريد، الهاتف، الفرع             │
│       │                                               │
│ فلترة │  🎭 الأدوار الوظيفية [Chips تفاعلية]         │
│ سريعة │  ┌───────────────────────────────────┐       │
│       │  │ [بائع ✕] [موظف مستودع ✕] [+ دور]  │       │
│ بحث   │  └───────────────────────────────────┘       │
│       │                                               │
│ فرز   │  ▼ إعدادات "بائع" [يظهر تلقائياً]            │
│       │  ├─ الفرع: الرياض                             │
│       │  ├─ جملة/تجزئة: ☑ ☑                          │
│       │                                               │
│       │  ▼ إعدادات "موظف مستودع" [يظهر تلقائياً]     │
│       │  ├─ المستودع: المستودع الرئيسي                │
│       │                                               │
│       │  🔐 صلاحيات إضافية                            │
│       │  ├─ ☑ تصدير  ☐ أسعار  ☐ خصم                  │
│       │                                               │
│       │  📊 ملخص الصلاحيات الفعلية [محسوب تلقائياً]  │
│       │  ┌───────────────────────────────────┐       │
│       │  │ عرض الطلبات ✅ (من: بائع)          │       │
│       │  │ إنشاء طلبات ✅ (من: بائع)          │       │
│       │  │ إدارة المخزون ✅ (من: مستودع)      │       │
│       │  │ نقل المنتجات ✅ (من: مستودع)       │       │
│       │  └───────────────────────────────────┘       │
└───────┴──────────────────────────────────────────────┘
```

#### 3.3 — الملفات المطلوبة

```
accounts/
├── views_user_management.py          ← Views (CRUD + AJAX)
├── forms_user_management.py          ← Forms (Role assignment)
├── templates/accounts/manage/
│   ├── user_list.html                ← قائمة المستخدمين
│   ├── user_form.html                ← إنشاء/تعديل (النموذج الديناميكي)
│   ├── _role_chips.html              ← Partial: شرائح الأدوار
│   ├── _role_settings.html           ← Partial: إعدادات الدور
│   └── _permissions_summary.html     ← Partial: ملخص الصلاحيات
├── static/accounts/manage/
│   ├── js/user_management.js         ← AJAX + ديناميكية
│   └── css/user_management.css       ← تصميم
└── urls.py                           ← إضافة routes جديدة
```

#### 3.4 — المميزات التقنية

| الميزة | التفاصيل |
|--------|----------|
| بحث فوري | AJAX search في قائمة المستخدمين |
| فلترة بالقسم | فلتر جانبي بالفروع والأقسام والأدوار |
| Role Chips | إضافة/حذف أدوار بالنقر، بدون إعادة تحميل |
| إعدادات شرطية | كل دور يعرض إعداداته فقط عند تفعيله |
| ملخص صلاحيات | جدول محسوب تلقائياً يوضح مصدر كل صلاحية |
| Audit Trail | تسجيل كل تغيير في الأدوار في AuditLog |
| تصدير | تصدير قائمة المستخدمين Excel |

#### 3.5 — صلاحيات الوصول

```python
# accounts/views_user_management.py
class UserManagementMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return (
            user.is_superuser or
            user.is_sales_manager or
            user.is_region_manager or
            user.has_perm('accounts.change_user')
        )
```

---

### المرحلة 4: توحيد نظام الأدوار (اختياري — طويل الأمد)

> **الحالة**: 🔴 لم يبدأ  
> **الأثر على الإنتاج**: عالي جداً — إعادة هيكلة البيانات  
> **المخاطر**: عالية — يتطلب تعديل عشرات الملفات

#### 4.1 — الهدف

التخلص من 16 Boolean field على User والاعتماد كلياً على نظام `Role` + `UserRole` M2M.

#### 4.2 — البنية المستهدفة

```
المطلوب:
                                  
User ←── UserRole ──→ Role ──→ Permission
                                  ↑
                            RoleHierarchy
                            (level, inherits)

بدلاً من:

User.is_salesperson = True/False
User.is_branch_manager = True/False
... (16 حقل)
```

#### 4.3 — مراحل التنفيذ الفرعية

**4.3.1 — إنشاء Roles من Boolean fields**

```python
# migration: create_system_roles

SYSTEM_ROLES = {
    'salesperson': {'display': 'بائع', 'level': 4},
    'branch_manager': {'display': 'مدير فرع', 'level': 3},
    'region_manager': {'display': 'مدير منطقة', 'level': 2},
    'sales_manager': {'display': 'مدير مبيعات', 'level': 1},
    'factory_manager': {'display': 'مسؤول مصنع', 'level': 2},
    'factory_accountant': {'display': 'محاسب مصنع', 'level': 3},
    'factory_receiver': {'display': 'مسؤول استلام', 'level': 4},
    'inspection_technician': {'display': 'فني معاينة', 'level': 5},
    'inspection_manager': {'display': 'مسؤول معاينات', 'level': 3},
    'installation_manager': {'display': 'مسؤول تركيبات', 'level': 3},
    'traffic_manager': {'display': 'مدير حركة', 'level': 3},
    'warehouse_staff': {'display': 'موظف مستودع', 'level': 4},
    'decorator_dept_manager': {'display': 'مدير قسم ديكور', 'level': 3},
    'decorator_dept_staff': {'display': 'موظف قسم ديكور', 'level': 4},
}
```

**4.3.2 — Data migration لنقل البيانات**

```python
# migration: migrate_boolean_to_userrole

def forward(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Role = apps.get_model('accounts', 'Role')
    UserRole = apps.get_model('accounts', 'UserRole')
    
    field_role_map = {
        'is_salesperson': 'salesperson',
        'is_branch_manager': 'branch_manager',
        # ... كل الحقول
    }
    
    for field_name, role_key in field_role_map.items():
        role = Role.objects.get(name=role_key)
        users = User.objects.filter(**{field_name: True})
        for user in users:
            UserRole.objects.get_or_create(user=user, role=role)
```

**4.3.3 — Property methods للتوافق (transition period)**

```python
# accounts/models.py

@property
def is_salesperson(self):
    """Backward compatible — يقرأ من UserRole بدل Boolean"""
    return self.user_roles.filter(role__name='salesperson').exists()

@is_salesperson.setter
def is_salesperson(self, value):
    """Backward compatible setter"""
    role = Role.objects.get(name='salesperson')
    if value:
        UserRole.objects.get_or_create(user=self, role=role)
    else:
        self.user_roles.filter(role=role).delete()
```

**4.3.4 — تحديث كل الكود**

```bash
# البحث عن كل الاستخدامات:
grep -rn "is_salesperson\|is_branch_manager\|is_region_manager" --include="*.py" \
    accounts/ orders/ manufacturing/ inspections/ installations/ \
    cutting/ inventory/ reports/ external_sales/ | wc -l

# المتوقع: 100+ ملف يحتاج تعديل
```

**4.3.5 — إزالة Boolean fields (آخر خطوة)**

```python
# migration: remove_boolean_role_fields

# فقط بعد التأكد من أن كل الكود يستخدم UserRole
# والتأكد من أن الـ properties تعمل بشكل صحيح
```

#### 4.4 — لماذا هذه المرحلة اختيارية؟

| السبب | التفاصيل |
|-------|----------|
| حجم العمل | 100+ ملف يحتاج تعديل |
| المخاطر | أي خطأ يؤثر على كل النظام |
| البديل يعمل | Boolean fields + المراحل 1-3 تحقق 80% من الهدف |
| التعقيد | الـ property setters قد تسبب مشاكل مع signals |

---

### المرحلة 5: لوحة إدارة الأدوار

> **الحالة**: 🔴 لم يبدأ  
> **الأثر على الإنتاج**: صفر — صفحة جديدة  
> **يعتمد على**: المرحلة 4 (اختياري بدونها)

#### 5.1 — الهدف

صفحة لمدير النظام لإدارة الأدوار نفسها (إنشاء، تعديل، حذف) بدون الحاجة لـ migrations.

#### 5.2 — المميزات

```
┌──────────────────────────────────────────────────────┐
│  🔐 إدارة الأدوار والصلاحيات                        │
├──────────────────────────────────────────────────────┤
│                                                       │
│  📋 الأدوار الحالية                                  │
│  ┌─────────────────────────────────────────────────┐ │
│  │ الدور          │ المستوى │ المستخدمين │ الحالة  │ │
│  │────────────────│─────────│───────────│────────│ │
│  │ مدير مبيعات    │ 1       │ 3         │ نظام ✅│ │
│  │ بائع           │ 4       │ 12        │ نظام ✅│ │
│  │ مسؤول مصنع     │ 2       │ 2         │ نظام ✅│ │
│  │ مشرف جودة      │ 3       │ 0         │ مخصص 🔧│ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  [+ إنشاء دور جديد]                                  │
│                                                       │
│  📊 مصفوفة الصلاحيات                                 │
│  ┌──────────────────────────────────────────────┐    │
│  │              │ عرض │ إنشاء │ تعديل │ حذف   │    │
│  │──────────────│─────│───────│───────│───────│    │
│  │ الطلبات      │ ✅  │ ✅    │ ✅    │ ❌    │    │
│  │ العملاء      │ ✅  │ ✅    │ ❌    │ ❌    │    │
│  │ المخزون      │ ❌  │ ❌    │ ❌    │ ❌    │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  🔗 سلسلة التوريث                                    │
│  مدير مبيعات → مدير منطقة → مدير فرع → بائع          │
│                                                       │
└──────────────────────────────────────────────────────┘
```

#### 5.3 — الملفات المطلوبة

```
accounts/
├── views_role_management.py
├── forms_role_management.py
├── templates/accounts/roles/
│   ├── role_dashboard.html
│   ├── role_form.html
│   ├── role_permissions_matrix.html
│   └── role_hierarchy_tree.html
├── static/accounts/roles/
│   ├── js/role_management.js
│   └── css/role_management.css
└── api_views.py  ← إضافة endpoints للأدوار
```

---

## الجدول الزمني المقترح

```
المرحلة 1: أدمن ديناميكي ────── ✅ مكتمل (2026-03-13)
                                      │
المرحلة 2: تعدد الأدوار ──────── ⏳ الأولوية التالية
                                      │
المرحلة 3: صفحة إدارة مخصصة ──── ⏳ بعد المرحلة 2
                                      │
المرحلة 4: توحيد النظام ─────── 🔮 مستقبلي (اختياري)
                                      │
المرحلة 5: لوحة الأدوار ────── 🔮 مستقبلي (يعتمد على 4)
```

---

## مصفوفة التأثير والمخاطر

| المرحلة | التعقيد | المخاطر | الفائدة | التأثير على الإنتاج |
|---------|---------|---------|---------|---------------------|
| 1. أدمن ديناميكي | ⭐ | 🟢 صفر | ⭐⭐⭐ | صفر |
| 2. تعدد الأدوار | ⭐⭐ | 🟡 متوسط | ⭐⭐⭐⭐ | متوسط |
| 3. صفحة مخصصة | ⭐⭐⭐ | 🟢 منخفض | ⭐⭐⭐⭐⭐ | صفر (صفحة جديدة) |
| 4. توحيد النظام | ⭐⭐⭐⭐⭐ | 🔴 عالي | ⭐⭐⭐⭐ | عالي |
| 5. لوحة الأدوار | ⭐⭐⭐ | 🟢 منخفض | ⭐⭐⭐ | صفر (صفحة جديدة) |

---

## الملفات المرجعية

| الملف | الغرض |
|-------|-------|
| `accounts/models.py` | نموذج User + ROLE_HIERARCHY |
| `accounts/admin.py` | نموذج الأدمن الحالي |
| `accounts/mixins.py` | Permission mixins |
| `accounts/forms.py` | RoleForm, UserRoleForm, RoleAssignForm |
| `accounts/views.py` | Views الحالية |
| `accounts/static/accounts/admin/js/dynamic_user_admin.js` | JS الأدمن الديناميكي |
| `accounts/static/accounts/admin/css/dynamic_user_admin.css` | CSS الأدمن الديناميكي |
| `accounts/migrations/0060_external_sales_groups_permissions.py` | مجموعات المبيعات الخارجية |

---

## ملاحظات مهمة

1. **لا تحذف Boolean fields حتى المرحلة 4** — كل الكود الحالي يعتمد عليها
2. **اختبر تعدد الأدوار على بيئة تجريبية أولاً** — المرحلة 2 تؤثر على المنطق
3. **المرحلة 3 يمكن تنفيذها بشكل مستقل** — لا تعتمد على المرحلة 2
4. **المرحلة 4 اختيارية** — المراحل 1-3 تحقق 80% من الهدف المطلوب
5. **كل مرحلة يجب أن تمر بـ**: dev → test → staging → production
