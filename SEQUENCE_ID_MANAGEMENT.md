# 🔧 دليل إدارة تسلسل ID الشامل

## 📋 نظرة عامة

هذا الدليل يوضح كيفية استخدام نظام إدارة تسلسل ID الشامل الذي تم تطويره لحل مشاكل تضارب ID خاصة بعد استعادة النسخ الاحتياطية في قواعد بيانات PostgreSQL.

## 🚨 المشكلة

بعد استعادة النسخ الاحتياطية، قد تحدث مشاكل في تسلسل ID حيث:
- قيمة التسلسل (sequence) تصبح أقل من أعلى ID موجود في الجدول
- يؤدي هذا إلى تضارب في ID عند إنشاء سجلات جديدة
- تظهر أخطاء "duplicate key value violates unique constraint"

## 🛠️ الحلول المطورة

تم تطوير مجموعة شاملة من الأدوات لحل هذه المشكلة:

### 1. أداة الإصلاح الشاملة
```bash
python manage.py fix_all_sequences
```

**الخيارات:**
- `--app <app_name>`: إصلاح تطبيق محدد فقط
- `--table <table_name>`: إصلاح جدول محدد فقط
- `--dry-run`: معاينة التغييرات دون تطبيقها
- `--verbose`: عرض تفاصيل أكثر

**أمثلة:**
```bash
# إصلاح جميع التسلسلات
python manage.py fix_all_sequences

# إصلاح تطبيق العملاء فقط
python manage.py fix_all_sequences --app customers

# معاينة التغييرات
python manage.py fix_all_sequences --dry-run --verbose
```

### 2. أداة فحص التسلسل
```bash
python manage.py check_sequences
```

**الخيارات:**
- `--app <app_name>`: فحص تطبيق محدد
- `--table <table_name>`: فحص جدول محدد
- `--show-all`: عرض جميع الجداول حتى السليمة
- `--export <filename>`: تصدير النتائج إلى ملف JSON

**أمثلة:**
```bash
# فحص جميع التسلسلات
python manage.py check_sequences --show-all

# فحص تطبيق الطلبات
python manage.py check_sequences --app orders

# تصدير تقرير الفحص
python manage.py check_sequences --export sequence_report.json
```

### 3. أداة الإصلاح التلقائي
```bash
python manage.py auto_fix_sequences
```

**الخيارات:**
- `--check-only`: فحص فقط دون إصلاح
- `--force`: إجبار الإصلاح حتى لو لم تُكتشف مشاكل
- `--log-file <filename>`: ملف تسجيل العمليات

**أمثلة:**
```bash
# فحص وإصلاح تلقائي
python manage.py auto_fix_sequences

# فحص فقط
python manage.py auto_fix_sequences --check-only

# إصلاح مع تسجيل
python manage.py auto_fix_sequences --log-file /var/log/sequence_fix.log
```

### 4. أداة المراقبة الدورية
```bash
python manage.py monitor_sequences
```

**الخيارات:**
- `--interval <minutes>`: فترة المراقبة بالدقائق (افتراضي: 60)
- `--email-alerts`: إرسال تنبيهات بالبريد الإلكتروني
- `--auto-fix`: إصلاح تلقائي عند اكتشاف مشاكل
- `--daemon`: تشغيل كخدمة في الخلفية
- `--report-file <filename>`: ملف تقرير المراقبة

**أمثلة:**
```bash
# مراقبة كل 30 دقيقة مع إصلاح تلقائي
python manage.py monitor_sequences --interval 30 --auto-fix

# تشغيل كخدمة مع تنبيهات
python manage.py monitor_sequences --daemon --email-alerts --auto-fix
```

### 5. أداة الإدارة الشاملة
```bash
python manage.py sequence_manager
```

هذه أداة موحدة تجمع جميع الوظائف:

**الإجراءات:**
- `check`: فحص حالة التسلسل
- `fix`: إصلاح التسلسل
- `monitor`: مراقبة التسلسل
- `auto`: إصلاح تلقائي
- `info`: معلومات التسلسل
- `reset`: إعادة تعيين التسلسل

**أمثلة:**
```bash
# فحص شامل
python manage.py sequence_manager check --show-all

# إصلاح شامل
python manage.py sequence_manager fix

# معلومات مفصلة
python manage.py sequence_manager info --detailed

# إعادة تعيين تسلسل جدول محدد
python manage.py sequence_manager reset customers_customer --confirm
```

## 🔄 الإصلاح التلقائي

تم تطوير نظام إصلاح تلقائي يعمل في الخلفية:

### الإشارات (Signals)
- يتم تشغيل فحص تلقائي بعد كل عملية `migrate`
- يكتشف مشاكل التسلسل ويصلحها تلقائياً
- يسجل جميع العمليات في ملفات السجل

### المراقب التلقائي
- يفحص التسلسلات بشكل دوري
- يرسل تنبيهات عند اكتشاف مشاكل
- يمكن تكوينه للإصلاح التلقائي

## 📊 أنواع المشاكل المكتشفة

### 1. مشاكل حرجة (Critical)
- التسلسل أقل من أو يساوي أعلى ID في الجدول
- **الخطر:** تضارب ID فوري
- **الحل:** إصلاح فوري مطلوب

### 2. تحذيرات (Warnings)
- فجوة كبيرة في التسلسل (> 1000)
- **الخطر:** هدر في المساحة
- **الحل:** إعادة تعيين اختيارية

### 3. حالة سليمة (Healthy)
- التسلسل يعمل بشكل صحيح
- **الحل:** لا حاجة لإجراء

## 🔧 الاستخدام بعد استعادة النسخ الاحتياطية

### الخطوات الموصى بها:

1. **فحص فوري:**
```bash
python manage.py check_sequences --show-all
```

2. **إصلاح شامل:**
```bash
python manage.py fix_all_sequences --verbose
```

3. **التحقق من النتائج:**
```bash
python manage.py check_sequences
```

4. **تفعيل المراقبة:**
```bash
python manage.py monitor_sequences --daemon --auto-fix
```

## 📝 ملفات السجل

### مواقع ملفات السجل:
- `/media/auto_fix_sequences.log`: سجل الإصلاح التلقائي
- `/media/sequence_monitor.log`: سجل المراقبة
- `/media/sync_from_sheets.log`: سجل مزامنة Google Sheets

### مراقبة السجلات:
```bash
# مراقبة سجل الإصلاح التلقائي
tail -f media/auto_fix_sequences.log

# مراقبة سجل المراقبة
tail -f media/sequence_monitor.log
```

## ⚙️ التكوين المتقدم

### إعدادات البريد الإلكتروني للتنبيهات:
```python
# في settings.py
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
ADMINS = [('Admin', 'admin@example.com')]
```

### جدولة المراقبة الدورية:
```bash
# إضافة إلى crontab للمراقبة كل ساعة
0 * * * * cd /path/to/project && python manage.py auto_fix_sequences

# مراقبة يومية شاملة
0 3 * * * cd /path/to/project && python manage.py check_sequences --export daily_report.json
```

## 🚀 أفضل الممارسات

### 1. الفحص الدوري
- قم بفحص التسلسلات أسبوعياً على الأقل
- استخدم المراقبة التلقائية في بيئة الإنتاج

### 2. النسخ الاحتياطية
- قم بفحص التسلسل فوراً بعد استعادة أي نسخة احتياطية
- احتفظ بسجل لعمليات الإصلاح

### 3. المراقبة
- فعّل التنبيهات بالبريد الإلكتروني
- راجع ملفات السجل بانتظام

### 4. الاختبار
- اختبر الأدوات في بيئة التطوير أولاً
- استخدم `--dry-run` لمعاينة التغييرات

## 🔍 استكشاف الأخطاء

### مشاكل شائعة:

1. **خطأ في الاتصال بقاعدة البيانات:**
```bash
# تحقق من إعدادات قاعدة البيانات
python manage.py dbshell
```

2. **صلاحيات غير كافية:**
```bash
# تأكد من صلاحيات المستخدم في PostgreSQL
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
```

3. **جداول مفقودة:**
```bash
# تحقق من وجود الجداول
python manage.py sequence_manager info
```

## 📞 الدعم

في حالة وجود مشاكل:
1. راجع ملفات السجل
2. استخدم `--verbose` للحصول على تفاصيل أكثر
3. جرب `--dry-run` لمعاينة التغييرات
4. تحقق من صلاحيات قاعدة البيانات

## 🔄 التحديثات المستقبلية

الميزات المخططة:
- واجهة ويب لإدارة التسلسل
- تقارير مرئية للمراقبة
- دعم قواعد بيانات أخرى
- تحسينات في الأداء
