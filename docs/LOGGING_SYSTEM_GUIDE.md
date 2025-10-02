# 📋 دليل نظام Logging - Logging System Guide

## 📍 مواقع ملفات Log

### المجلد الرئيسي
```
/home/zakee/homeupdate/logs/
```

### ملفات Log المتاحة

| الملف | الوصف | المستوى | الحجم الأقصى |
|------|-------|---------|-------------|
| `django.log` | سجلات Django العامة | INFO | 10 MB |
| `errors.log` | سجلات الأخطاء فقط | ERROR | 10 MB |
| `security.log` | سجلات الأمان | WARNING | 5 MB |
| `performance.log` | سجلات الأداء | INFO | 10 MB |
| `database.log` | سجلات قاعدة البيانات | WARNING | 10 MB |
| `api.log` | سجلات API | INFO | 10 MB |
| `advanced_sync.log` | سجلات مزامنة Odoo | INFO | 10 MB |
| `sequence_checker.log` | سجلات فحص التسلسل | DEBUG | 5 MB |

### مجلد الأرشيف
```
/home/zakee/homeupdate/logs/archive/
```

---

## 🚀 الإعداد السريع

### 1. إعداد نظام Logging
```bash
python setup_logging.py
```

هذا السكريبت سيقوم بـ:
- ✅ إنشاء مجلد `logs` و `logs/archive`
- ✅ إنشاء جميع ملفات Log الأساسية
- ✅ تطبيق إعدادات Logging المحسّنة
- ✅ اختبار جميع Loggers
- ✅ عرض حالة الملفات

### 2. إدارة ملفات Log
```bash
./manage_logs.sh
```

قائمة تفاعلية لإدارة ملفات Log مع خيارات متعددة.

---

## 📖 الأوامر الأساسية

### عرض ملفات Log

```bash
# عرض جميع ملفات Log
ls -lh logs/

# عرض آخر 50 سطر
tail -n 50 logs/django.log

# عرض آخر 100 سطر
tail -n 100 logs/errors.log

# متابعة Log مباشرة (real-time)
tail -f logs/django.log

# متابعة عدة ملفات
tail -f logs/django.log logs/errors.log
```

### البحث في ملفات Log

```bash
# البحث عن كلمة معينة
grep "error" logs/django.log

# البحث مع عرض رقم السطر
grep -n "error" logs/django.log

# البحث في جميع الملفات
grep -r "error" logs/

# البحث عن الأخطاء فقط
grep -i "error\|exception\|critical" logs/*.log

# البحث عن تاريخ معين
grep "2025-10-01" logs/django.log
```

### تحليل ملفات Log

```bash
# عد عدد الأخطاء
grep -c "ERROR" logs/django.log

# عرض أنواع الأخطاء
grep "ERROR" logs/django.log | cut -d' ' -f4 | sort | uniq -c

# عرض آخر 10 أخطاء
grep "ERROR" logs/errors.log | tail -n 10

# إحصائيات حسب المستوى
echo "INFO: $(grep -c 'INFO' logs/django.log)"
echo "WARNING: $(grep -c 'WARNING' logs/django.log)"
echo "ERROR: $(grep -c 'ERROR' logs/django.log)"
```

### إدارة حجم الملفات

```bash
# عرض حجم كل ملف
du -h logs/*.log

# عرض الحجم الإجمالي
du -sh logs/

# عرض أكبر 5 ملفات
du -h logs/*.log | sort -h | tail -n 5

# تنظيف ملف معين (حذف المحتوى)
> logs/django.log

# تنظيف جميع الملفات
for f in logs/*.log; do > "$f"; done
```

### أرشفة ملفات Log

```bash
# إنشاء أرشيف مضغوط
tar -czf logs/archive/logs_$(date +%Y%m%d_%H%M%S).tar.gz logs/*.log

# أرشفة وتنظيف
tar -czf logs/archive/logs_$(date +%Y%m%d_%H%M%S).tar.gz logs/*.log && \
for f in logs/*.log; do > "$f"; done

# عرض محتوى أرشيف
tar -tzf logs/archive/logs_20251001_223000.tar.gz

# استخراج أرشيف
tar -xzf logs/archive/logs_20251001_223000.tar.gz
```

---

## 🔧 الاستخدام في الكود

### استيراد Logger

```python
import logging

# الحصول على logger
logger = logging.getLogger(__name__)
```

### مستويات Logging

```python
# DEBUG - معلومات تفصيلية للتطوير
logger.debug('تفاصيل دقيقة للتطوير')

# INFO - معلومات عامة
logger.info('تم إنشاء الطلب بنجاح')

# WARNING - تحذيرات
logger.warning('القيمة قريبة من الحد الأقصى')

# ERROR - أخطاء
logger.error('فشل في حفظ البيانات')

# CRITICAL - أخطاء حرجة
logger.critical('فشل الاتصال بقاعدة البيانات')
```

### أمثلة عملية

```python
import logging

logger = logging.getLogger('orders')

def create_order(data):
    try:
        logger.info(f'بدء إنشاء طلب جديد: {data.get("id")}')
        
        # معالجة الطلب
        order = Order.objects.create(**data)
        
        logger.info(f'تم إنشاء الطلب بنجاح: {order.id}')
        return order
        
    except ValidationError as e:
        logger.warning(f'خطأ في التحقق من البيانات: {e}')
        raise
        
    except Exception as e:
        logger.error(f'خطأ غير متوقع: {e}', exc_info=True)
        raise
```

### Logging مع Context

```python
logger.info('تم تسجيل الدخول', extra={
    'user_id': user.id,
    'ip_address': request.META.get('REMOTE_ADDR'),
    'user_agent': request.META.get('HTTP_USER_AGENT')
})
```

---

## ⚙️ التكوين المتقدم

### تغيير مستوى Logging

في `crm/settings.py`:

```python
LOGGING = {
    'loggers': {
        'django': {
            'level': 'DEBUG',  # تغيير من INFO إلى DEBUG
        },
    },
}
```

### إضافة Logger جديد

```python
LOGGING = {
    'handlers': {
        'custom_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/custom.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'custom_app': {
            'handlers': ['custom_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

---

## 📊 المراقبة والتحليل

### سكريبت مراقبة تلقائي

```bash
#!/bin/bash
# monitor_logs.sh

while true; do
    clear
    echo "=== Log Monitoring ==="
    echo "Time: $(date)"
    echo ""
    
    echo "Recent Errors:"
    tail -n 5 logs/errors.log
    echo ""
    
    echo "Log Sizes:"
    du -h logs/*.log
    echo ""
    
    sleep 10
done
```

### تصفية Logs حسب الوقت

```bash
# آخر ساعة
grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" logs/django.log

# اليوم
grep "$(date '+%Y-%m-%d')" logs/django.log

# بين وقتين
awk '/2025-10-01 10:00/,/2025-10-01 11:00/' logs/django.log
```

---

## 🔄 Rotation التلقائي

النظام يستخدم `RotatingFileHandler` الذي يقوم بـ:

- ✅ تدوير الملفات تلقائياً عند الوصول للحد الأقصى
- ✅ الاحتفاظ بعدد محدد من النسخ الاحتياطية
- ✅ ضغط الملفات القديمة (اختياري)

### مثال على الملفات بعد Rotation:
```
django.log          # الملف الحالي
django.log.1        # النسخة السابقة
django.log.2        # النسخة الأقدم
django.log.3
django.log.4
django.log.5        # أقدم نسخة (سيتم حذفها عند التدوير التالي)
```

---

## 🛠️ استكشاف الأخطاء

### المشكلة: لا تظهر Logs

```bash
# التحقق من الصلاحيات
ls -l logs/

# التحقق من إعدادات Django
python manage.py shell -c "from django.conf import settings; print(settings.LOGGING)"

# إعادة تشغيل النظام
python setup_logging.py
```

### المشكلة: الملفات كبيرة جداً

```bash
# أرشفة وتنظيف
./manage_logs.sh
# اختر الخيار 7 (أرشفة)

# أو يدوياً
tar -czf logs/archive/backup_$(date +%Y%m%d).tar.gz logs/*.log
for f in logs/*.log; do > "$f"; done
```

### المشكلة: بطء في الكتابة

```python
# تقليل مستوى Logging في الإنتاج
LOGGING['loggers']['django']['level'] = 'WARNING'
```

---

## 📝 أفضل الممارسات

1. **استخدم المستوى المناسب**
   - DEBUG: للتطوير فقط
   - INFO: للعمليات العادية
   - WARNING: للتحذيرات
   - ERROR: للأخطاء
   - CRITICAL: للأخطاء الحرجة

2. **أضف Context مفيد**
   ```python
   logger.info(f'Order {order_id} created by user {user_id}')
   ```

3. **لا تسجل معلومات حساسة**
   ```python
   # ❌ خطأ
   logger.info(f'Password: {password}')
   
   # ✅ صحيح
   logger.info(f'User authenticated: {username}')
   ```

4. **استخدم exc_info للأخطاء**
   ```python
   try:
       # code
   except Exception as e:
       logger.error('Error occurred', exc_info=True)
   ```

5. **راقب حجم الملفات**
   ```bash
   # أضف إلى crontab
   0 0 * * * cd /home/zakee/homeupdate && ./manage_logs.sh archive
   ```

---

## 🔗 روابط مفيدة

- [Django Logging Documentation](https://docs.djangoproject.com/en/stable/topics/logging/)
- [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [Logging Best Practices](https://docs.python-guide.org/writing/logging/)

---

## 📞 الدعم

للمساعدة أو الاستفسارات:
- راجع هذا الدليل
- استخدم `./manage_logs.sh` للإدارة التفاعلية
- تحقق من `logs/errors.log` للأخطاء

---

**آخر تحديث:** 2025-10-01

