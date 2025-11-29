# إصلاحات أمنية عاجلة - يجب تطبيقها فوراً

## 🔴 إصلاح فوري للمشاكل عالية الخطورة

### الإصلاح #1: SQL Injection في odoo_db_manager/advanced_sync_service.py

**السطر 201**:

```python
# ❌ الكود الحالي (خطير)
cursor.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}')

# ✅ الكود الآمن
from psycopg2 import sql

cursor.execute(
    sql.SQL('SELECT COALESCE(MAX(id), 0) + 1 FROM {}').format(
        sql.Identifier(table_name)
    )
)
```

**البحث والاستبدال**:
1. افتح الملف: `odoo_db_manager/advanced_sync_service.py`
2. ابحث عن السطر 201
3. استبدل الكود القديم بالكود الجديد
4. تأكد من إضافة: `from psycopg2 import sql` في بداية الملف

---

### الإصلاح #2: SQL Injection في crm/management/commands/sequence_manager.py

**السطر 266**:

```python
# ❌ الكود الحالي (خطير)
cursor.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}')

# ✅ الكود الآمن
from psycopg2 import sql

cursor.execute(
    sql.SQL('SELECT COALESCE(MAX(id), 0) + 1 FROM {}').format(
        sql.Identifier(table_name)
    )
)
```

**البحث والاستبدال**:
1. افتح الملف: `crm/management/commands/sequence_manager.py`
2. ابحث عن السطر 266
3. استبدل الكود القديم بالكود الجديد
4. تأكد من إضافة: `from psycopg2 import sql` في بداية الملف

---

### الإصلاح #3: SQL Injection في accounts/management/commands/reset_sequence.py

**السطر 14**:

```python
# ❌ الكود الحالي (خطير)
cursor.execute(f"SELECT setval('accounts_user_id_seq', {max_id + 1}, false);")

# ✅ الكود الآمن
cursor.execute("SELECT setval('accounts_user_id_seq', %s, false);", [max_id + 1])
```

**البحث والاستبدال**:
1. افتح الملف: `accounts/management/commands/reset_sequence.py`
2. ابحث عن السطر 14
3. استبدل الكود القديم بالكود الجديد

---

### الإصلاح #4: استخدام __import__() في update_requirements.py

**السطر 114**:

```python
# ❌ الكود الحالي (خطير)
module = __import__(package_name)

# ✅ الكود الآمن
import importlib
try:
    module = importlib.import_module(package_name)
except ImportError:
    module = None
```

**البحث والاستبدال**:
1. افتح الملف: `accounts/management/commands/update_requirements.py`
2. ابحث عن السطر 114
3. استبدل الكود القديم بالكود الجديد
4. تأكد من إضافة: `import importlib` في بداية الملف

---

## 📝 سكريبت إصلاح تلقائي

يمكنك تشغيل هذا السكريبت لإصلاح المشاكل تلقائياً:

```bash
#!/bin/bash
# اسم الملف: fix_critical_security_issues.sh

echo "🔧 بدء إصلاح المشاكل الأمنية العاجلة..."

# النسخ الاحتياطي
echo "📦 إنشاء نسخ احتياطية..."
cp odoo_db_manager/advanced_sync_service.py odoo_db_manager/advanced_sync_service.py.backup
cp crm/management/commands/sequence_manager.py crm/management/commands/sequence_manager.py.backup
cp accounts/management/commands/reset_sequence.py accounts/management/commands/reset_sequence.py.backup
cp accounts/management/commands/update_requirements.py accounts/management/commands/update_requirements.py.backup

echo "✅ تم إنشاء النسخ الاحتياطية"

# تطبيق الإصلاحات
echo "🔨 تطبيق الإصلاحات..."

# الإصلاح #1
echo "  - إصلاح odoo_db_manager/advanced_sync_service.py"
# يحتاج تعديل يدوي بسبب تعقيد الكود

# الإصلاح #2
echo "  - إصلاح crm/management/commands/sequence_manager.py"
# يحتاج تعديل يدوي بسبب تعقيد الكود

# الإصلاح #3
echo "  - إصلاح accounts/management/commands/reset_sequence.py"
sed -i "s/cursor.execute(f\"SELECT setval('accounts_user_id_seq', {max_id + 1}, false);\")/cursor.execute(\"SELECT setval('accounts_user_id_seq', %s, false);\", [max_id + 1])/" accounts/management/commands/reset_sequence.py

# الإصلاح #4
echo "  - إصلاح accounts/management/commands/update_requirements.py"
# يحتاج تعديل يدوي

echo ""
echo "✅ انتهى الإصلاح!"
echo "⚠️  تحذير: بعض الإصلاحات تحتاج تعديل يدوي"
echo "📖 راجع SECURITY_FIXES_URGENT.md للتفاصيل"
```

---

## ⚡ اختبار بعد الإصلاح

بعد تطبيق الإصلاحات، قم بتشغيل:

```bash
# 1. اختبار الكود
python manage.py check

# 2. اختبار قاعدة البيانات
python manage.py migrate --check

# 3. تشغيل الاختبارات
python manage.py test

# 4. فحص أمني
python manage.py security_check
```

---

## 📋 قائمة التحقق

- [ ] تم عمل نسخة احتياطية من الملفات
- [ ] تم تطبيق الإصلاح #1 (advanced_sync_service.py)
- [ ] تم تطبيق الإصلاح #2 (sequence_manager.py)
- [ ] تم تطبيق الإصلاح #3 (reset_sequence.py)
- [ ] تم تطبيق الإصلاح #4 (update_requirements.py)
- [ ] تم اختبار الكود بدون أخطاء
- [ ] تم التحقق من عمل الوظائف المتأثرة

---

## ⏰ الوقت المتوقع

- **النسخ الاحتياطي**: 5 دقائق
- **تطبيق الإصلاحات**: 15-20 دقيقة
- **الاختبار**: 10 دقائق
- **الإجمالي**: ~30-35 دقيقة

---

**ملاحظة هامة**: هذه الإصلاحات **عاجلة** ويجب تطبيقها في أقرب وقت ممكن قبل النشر للإنتاج.
