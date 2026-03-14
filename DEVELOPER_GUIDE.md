# 📚 دليل المطور الشامل - نظام ERP

**آخر تحديث:** 2026-01-22  
**الإصدار:** 2.0 (بعد الإصلاحات)

---

## 🏗️ البنية المعمارية

### التقنيات المستخدمة:
- **Framework:** Django 6.0
- **Language:** Python 3.13
- **Database:** PostgreSQL
- **Cache:** Redis (3 databases)
- **Task Queue:** Celery 5.5.3
- **Web Server:** Gunicorn

### التطبيقات الرئيسية:
```
accounts/          # المصادقة والمستخدمين
orders/            # إدارة الطلبات
manufacturing/     # التصنيع
inventory/         # المخزون
installations/     # التركيبات
customers/         # العملاء
```

---

## 🚀 البدء السريع

### 1. تفعيل البيئة الافتراضية:
```bash
source venv/bin/activate
```

### 2. تشغيل الخادم:
```bash
python manage.py runserver
```

### 3. الوصول للنظام:
```
http://localhost:8000
```

---

## 🔒 الأمان

### الإصلاحات المطبقة:
1. ✅ كلمة مرور قاعدة البيانات في `.env`
2. ✅ إزالة تجاوز CSRF
3. ✅ JWT tokens: 15 دقيقة
4. ✅ ملح تشفير آمن
5. ✅ force_debug_cursor فقط في DEBUG
6. ✅ نظام صلاحيات للمخزون

### الإعدادات الأمنية:
```python
# في الإنتاج
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 📦 طبقة الخدمة (Service Layer)

### استخدام OrderService:
```python
from orders.services import OrderService

# إنشاء طلب
order = OrderService.create_order(
    customer_id=1,
    items_data=[...],
    created_by=request.user
)

# إلغاء طلب
OrderService.cancel_order(
    order=order,
    reason='سبب الإلغاء',
    cancelled_by=request.user
)

# حساب الإجمالي
total = OrderService.calculate_order_total(order)
```

---

## 🧪 الاختبارات

### تشغيل جميع الاختبارات:
```bash
python manage.py test
```

### اختبارات محددة:
```bash
# اختبارات الوحدة
python manage.py test tests.unit

# اختبارات التكامل
python manage.py test tests.integration

# اختبار محدد
python manage.py test tests.unit.test_manufacturing_utils
```

### تغطية الاختبارات:
```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # تقرير HTML
```

---

## 🛠️ أدوات التطوير

### Black (تنسيق الكود):
```bash
black .
```

### isort (ترتيب الاستيرادات):
```bash
isort .
```

### flake8 (فحص الجودة):
```bash
flake8 .
```

### mypy (فحص الأنواع):
```bash
mypy manufacturing/ core/
```

---

## 📁 هيكل المشروع

```
homeupdate/
├── accounts/              # المستخدمين والصلاحيات
├── orders/
│   ├── models.py         # نماذج الطلبات
│   ├── views.py          # عروض الطلبات
│   └── services/         # طبقة الخدمة
│       └── order_service.py
├── manufacturing/
│   ├── models.py
│   ├── views.py
│   └── utils.py          # ✅ محسّن (N+1 fixed)
├── inventory/
│   ├── models.py
│   ├── views.py
│   └── permissions.py    # ✅ جديد
├── core/
│   └── encryption.py     # ✅ محسّن
├── scripts/
│   ├── security/
│   │   ├── migrate_secrets.py
│   │   └── check_api_permissions.py
│   └── cleanup/
│       └── delete_backups.sh
├── tests/
│   ├── unit/
│   └── integration/
├── crm/
│   └── settings.py       # ✅ محسّن
├── pyproject.toml        # ✅ جديد
├── .flake8              # ✅ جديد
└── manage.py
```

---

## 🔧 السكريبتات المساعدة

### نقل الأسرار:
```bash
python scripts/security/migrate_secrets.py
```

### فحص صلاحيات API:
```bash
python scripts/security/check_api_permissions.py
```

### حذف الملفات الاحتياطية:
```bash
bash scripts/cleanup/delete_backups.sh
```

### تفعيل البيئة وتشغيل أمر:
```bash
./activate_and_run.sh python manage.py check
```

---

## 📊 قاعدة البيانات

### Migrations:
```bash
# إنشاء migrations
python manage.py makemigrations

# تطبيق migrations
python manage.py migrate

# عرض migrations
python manage.py showmigrations
```

### النسخ الاحتياطي:
```bash
# نسخ احتياطي
python manage.py dbbackup

# استعادة
python manage.py dbrestore
```

---

## 🚨 استكشاف الأخطاء

### المشكلة: "No module named 'django'"
**الحل:**
```bash
source venv/bin/activate
```

### المشكلة: "DB_PASSWORD not set"
**الحل:**
```bash
python scripts/security/migrate_secrets.py
# ثم حدّث PostgreSQL
```

### المشكلة: CSRF errors
**الحل:** تأكد من حذف `DisableCSRFMiddleware` ✅

### المشكلة: JWT expired
**الحل:** استخدم refresh token للحصول على access token جديد

---

## 📈 الأداء

### تحسينات مطبقة:
1. ✅ إصلاح N+1 في `manufacturing/utils.py`
2. ✅ Connection pooling (CONN_MAX_AGE=300)
3. ✅ Redis caching (3 databases)
4. ✅ Query prefetching

### مراقبة الأداء:
```python
# في settings.py
# QueryPerformanceLoggingMiddleware
# يسجل الصفحات البطيئة (>1s) والاستعلامات البطيئة (>100ms)
```

---

## 🔐 الصلاحيات

### استخدام صلاحيات المخزون:
```python
from inventory.permissions import view_product, add_product

@view_product
def product_list(request):
    # ...

@add_product
def product_create(request):
    # ...
```

### فحص الصلاحيات في Template:
```django
{% if perms.inventory.view_product %}
    <!-- عرض المنتجات -->
{% endif %}
```

---

## 📞 الدعم

### الأسئلة الشائعة:
راجع `RUNNING_COMMANDS.md`

### التوثيق الكامل:
- تقرير المراجعة: `تقرير_المراجعة_الشاملة.md`
- خطة الإصلاح: `خطة_الإصلاح_الشاملة.md`
- ملخص الإنجازات: `ملخص_الإنجازات.md`

---

**تم إعداد هذا الدليل:** 2026-01-22  
**الحالة:** جاهز للإنتاج ✅
