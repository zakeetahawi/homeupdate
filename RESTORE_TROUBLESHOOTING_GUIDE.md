# دليل استكشاف أخطاء الاستعادة وإصلاحها
# Restore Troubleshooting Guide

## المشاكل الشائعة في عمليات الاستعادة

### 1. العمليات المعلقة (Stuck Processes)

#### الأعراض:
- عملية الاستعادة تتوقف عند نسبة معينة (مثل 42%)
- لا يتم تحديث شريط التقدم لفترة طويلة
- الواجهة تعرض "قيد المعالجة" بدون تقدم

#### الأسباب:
- مشاكل في الذاكرة أو موارد النظام
- تعارض في المفاتيح الخارجية
- بيانات تالفة في ملف النسخة الاحتياطية
- عمليات قاعدة البيانات المعلقة

#### الحلول:

##### الحل السريع:
```bash
# إصلاح العمليات المعلقة
cd homeupdate
python manage.py shell -c "
from odoo_db_manager.models import RestoreProgress
from django.utils import timezone
from datetime import timedelta

# البحث عن العمليات المعلقة
stuck_sessions = RestoreProgress.objects.filter(
    status__in=['processing', 'starting'],
    updated_at__lt=timezone.now() - timedelta(minutes=5)
)

for session in stuck_sessions:
    session.status = 'failed'
    session.current_step = 'تم إيقاف العملية - إعادة المحاولة مطلوبة'
    session.error_message = 'العملية علقت وتم إيقافها تلقائياً'
    session.save()
    print(f'تم إصلاح الجلسة: {session.session_id}')
"

# تنظيف الكاش
python manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('تم تنظيف الكاش')
"
```

##### الحل المتقدم:
```bash
# استخدام سكريپت الإصلاح المخصص
python fix_stuck_restore.py
```

### 2. مشاكل ملفات النسخ الاحتياطية

#### الأعراض:
- خطأ "تنسيق ملف غير صالح"
- "No installed app with label 'factory'"
- بيانات JSON تالفة

#### الحلول:

##### فحص ملف النسخة الاحتياطية:
```bash
# فحص تنسيق الملف
python manage.py shell -c "
import json
file_path = 'path/to/backup.json'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'الملف صالح - يحتوي على {len(data)} عنصر')
except Exception as e:
    print(f'خطأ في الملف: {str(e)}')
"
```

##### إصلاح مراجع factory:
```bash
# استبدال مراجع factory بـ manufacturing
sed -i 's/"factory"/"manufacturing"/g' backup.json
```

### 3. مشاكل الذاكرة والأداء

#### الأعراض:
- بطء شديد في المعالجة
- توقف النظام
- خطأ "Memory Error"

#### الحلول:

##### استخدام الاستعادة المحسنة:
```bash
# استعادة محسنة للملفات الكبيرة
python optimized_restore.py backup.json true
```

##### مراقبة استخدام الذاكرة:
```bash
# فحص الذاكرة أثناء العملية
htop
# أو
free -h
```

### 4. تعارض المفاتيح الخارجية

#### الأعراض:
- خطأ "FOREIGN KEY constraint failed"
- "IntegrityError"
- فشل في حفظ بعض السجلات

#### الحلول:

##### تعطيل فحص المفاتيح الخارجية مؤقتاً:
```sql
-- في PostgreSQL
SET session_replication_role = replica;
-- تنفيذ الاستعادة
SET session_replication_role = DEFAULT;
```

##### ترتيب البيانات حسب التبعيات:
```python
# استخدام السكريپت المحسن الذي يرتب البيانات تلقائياً
python optimized_restore.py backup.json
```

### 5. مشاكل أذونات قاعدة البيانات

#### الأعراض:
- خطأ "Permission denied"
- فشل في الوصول لقاعدة البيانات

#### الحلول:

##### فحص اتصال قاعدة البيانات:
```bash
python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    print('اتصال قاعدة البيانات يعمل')
except Exception as e:
    print(f'مشكلة في الاتصال: {str(e)}')
"
```

## الأدوات المساعدة

### 1. سكريپت التشخيص السريع

```bash
# إنشاء ملف diagnostic.py
cat > diagnostic.py << 'EOF'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from odoo_db_manager.models import RestoreProgress
from django.db import connection

print("🔍 تشخيص سريع للنظام")
print("="*40)

# فحص العمليات النشطة
active = RestoreProgress.objects.filter(status='processing')
print(f"العمليات النشطة: {active.count()}")

# فحص قاعدة البيانات
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("قاعدة البيانات: ✅ متصلة")
except:
    print("قاعدة البيانات: ❌ مشكلة")

# فحص التطبيقات
from django.apps import apps
try:
    apps.get_app_config('manufacturing')
    print("تطبيق manufacturing: ✅ موجود")
except:
    print("تطبيق manufacturing: ❌ مفقود")

try:
    apps.get_app_config('factory')
    print("تطبيق factory: ⚠️ موجود (يجب إزالته)")
except:
    print("تطبيق factory: ✅ غير موجود")
EOF

python diagnostic.py
```

### 2. تنظيف شامل للنظام

```bash
# تنظيف كامل
python manage.py shell -c "
from odoo_db_manager.models import RestoreProgress
from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone

# إيقاف جميع العمليات النشطة
active_sessions = RestoreProgress.objects.filter(status__in=['processing', 'starting'])
for session in active_sessions:
    session.status = 'failed'
    session.error_message = 'تم إيقاف العملية للتنظيف'
    session.save()

print(f'تم إيقاف {active_sessions.count()} عملية')

# حذف الجلسات القديمة (أقدم من 24 ساعة)
old_sessions = RestoreProgress.objects.filter(
    created_at__lt=timezone.now() - timedelta(hours=24)
)
deleted = old_sessions.delete()[0]
print(f'تم حذف {deleted} جلسة قديمة')

# تنظيف الكاش
cache.clear()
print('تم تنظيف الكاش')
"
```

### 3. فحص تكامل النسخة الاحتياطية

```bash
# فحص تكامل الملف
python manage.py shell -c "
import json
import sys

def check_backup_integrity(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            return False, 'الملف ليس قائمة JSON صالحة'
        
        models = {}
        errors = []
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f'العنصر {i} ليس كائن JSON صالح')
                continue
                
            model = item.get('model')
            if not model:
                errors.append(f'العنصر {i} بدون نموذج')
                continue
                
            models[model] = models.get(model, 0) + 1
        
        print(f'✅ الملف صالح - {len(data)} عنصر')
        print(f'📊 النماذج الموجودة:')
        for model, count in sorted(models.items()):
            print(f'  {model}: {count}')
        
        if errors:
            print(f'⚠️ تحذيرات ({len(errors)}):')
            for error in errors[:5]:
                print(f'  - {error}')
        
        return True, 'الملف صالح'
        
    except Exception as e:
        return False, f'خطأ: {str(e)}'

# استخدام الدالة
file_path = input('أدخل مسار ملف النسخة الاحتياطية: ')
if file_path:
    valid, message = check_backup_integrity(file_path)
    print(f'النتيجة: {message}')
"
```

## نصائح الوقاية

### 1. قبل الاستعادة

- ✅ تأكد من وجود مساحة كافية على القرص
- ✅ انشئ نسخة احتياطية من البيانات الحالية
- ✅ تأكد من عدم وجود عمليات استعادة أخرى
- ✅ فحص صحة ملف النسخة الاحتياطية

### 2. أثناء الاستعادة

- ⚠️ لا تغلق المتصفح أو تنتقل من الصفحة
- ⚠️ تجنب تشغيل عمليات أخرى كثيفة الاستخدام
- ⚠️ راقب استخدام الذاكرة والمعالج

### 3. بعد الاستعادة

- ✅ تحقق من اكتمال البيانات
- ✅ اختبر الوظائف الأساسية
- ✅ نظف الملفات المؤقتة والجلسات القديمة

## أوامر مفيدة للطوارئ

```bash
# إيقاف طارئ لجميع العمليات
sudo systemctl stop postgresql  # مؤقتاً لإيقاف قاعدة البيانات
sudo systemctl start postgresql

# إعادة تشغيل خدمة Django
sudo systemctl restart gunicorn  # إذا كان يعمل كخدمة

# فحص العمليات المعلقة في النظام
ps aux | grep python | grep manage

# فحص استخدام الذاكرة
free -h
df -h  # مساحة القرص
```

## جهات الاتصال للدعم

- 📧 فريق التطوير: [developer@company.com]
- 📞 الدعم الفني: [+966XXXXXXXXX]
- 🔗 التوثيق: [docs.company.com]

---

**آخر تحديث**: 2025-07-24  
**الإصدار**: 1.0  
**المطور**: نظام إدارة العملاء والطلبات