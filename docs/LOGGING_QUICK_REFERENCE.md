# 📋 مرجع سريع لنظام Logging

## 📍 مواقع ملفات Log

```
/home/zakee/homeupdate/logs/
├── django.log           # سجلات Django العامة
├── errors.log           # الأخطاء فقط
├── security.log         # سجلات الأمان
├── performance.log      # سجلات الأداء
├── database.log         # سجلات قاعدة البيانات
├── api.log             # سجلات API
├── advanced_sync.log   # مزامنة Odoo
├── sequence_checker.log # فحص التسلسل
└── archive/            # الأرشيف
```

## 🚀 الأوامر السريعة

### عرض Logs
```bash
# عرض جميع الملفات
ls -lh logs/

# آخر 50 سطر
tail -n 50 logs/django.log

# متابعة مباشرة
tail -f logs/django.log

# عرض الأخطاء فقط
tail -f logs/errors.log
```

### البحث
```bash
# البحث عن كلمة
grep "error" logs/django.log

# البحث في جميع الملفات
grep -r "error" logs/

# البحث عن تاريخ
grep "2025-10-01" logs/django.log
```

### الإدارة
```bash
# إدارة تفاعلية
./manage_logs.sh

# إعداد النظام
python setup_logging.py

# عرض الحجم
du -h logs/*.log

# تنظيف ملف
> logs/django.log
```

## 💻 الاستخدام في الكود

```python
import logging

# الحصول على logger
logger = logging.getLogger(__name__)

# الاستخدام
logger.info('معلومة عامة')
logger.warning('تحذير')
logger.error('خطأ')
logger.critical('خطأ حرج')

# مع تفاصيل
logger.error('خطأ في الحفظ', exc_info=True)
```

## 📊 الإحصائيات

```bash
# عد الأخطاء
grep -c "ERROR" logs/django.log

# عرض أنواع الأخطاء
grep "ERROR" logs/django.log | cut -d' ' -f4 | sort | uniq -c

# إحصائيات حسب المستوى
echo "INFO: $(grep -c 'INFO' logs/django.log)"
echo "WARNING: $(grep -c 'WARNING' logs/django.log)"
echo "ERROR: $(grep -c 'ERROR' logs/django.log)"
```

## 🔧 الصيانة

```bash
# أرشفة
tar -czf logs/archive/backup_$(date +%Y%m%d).tar.gz logs/*.log

# تنظيف بعد الأرشفة
for f in logs/*.log; do > "$f"; done

# حذف الأرشيفات القديمة (أكثر من 30 يوم)
find logs/archive/ -name "*.tar.gz" -mtime +30 -delete
```

## 📚 المزيد من المعلومات

راجع الدليل الكامل: `docs/LOGGING_SYSTEM_GUIDE.md`

---

**آخر تحديث:** 2025-10-01

