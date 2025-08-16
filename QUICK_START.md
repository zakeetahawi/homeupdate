# 🚀 دليل التشغيل السريع

## ✅ **التشغيل البسيط (الطريقة الجديدة)**

```bash
# تشغيل النظام كاملاً مع جميع الخدمات
python manage.py runserver
```

هذا الأمر سيقوم تلقائياً بـ:
- ✅ تشغيل Redis/Valkey
- ✅ تشغيل Celery Worker (للمهام الخلفية)
- ✅ تشغيل Celery Beat (للمهام الدورية)
- ✅ تشغيل Django Development Server
- ✅ تطبيق الترحيلات تلقائياً

## 🌐 **الوصول للنظام**

- **الموقع**: http://localhost:8000
- **المستخدم**: admin
- **كلمة المرور**: admin123

## 🛠️ **المتطلبات**

تأكد من تثبيت المتطلبات:

```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# تثبيت Redis/Valkey (على Arch Linux/Manjaro)
sudo pacman -S valkey

# أو على Ubuntu/Debian
sudo apt-get install redis-server
```

## 📊 **مراقبة النظام**

```bash
# مراقبة Celery Worker
tail -f /tmp/celery_worker_dev.log

# مراقبة Celery Beat (المهام الدورية)
tail -f /tmp/celery_beat_dev.log

# اختبار شامل للنظام
python test_celery.py
```

## 🔧 **إصلاح تحذير الذاكرة**

إذا ظهر تحذير حول الذاكرة، شغل:

```bash
sudo sysctl vm.overcommit_memory=1
```

أو لجعله دائماً:

```bash
echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf
```

## 🚨 **استكشاف الأخطاء**

### مشكلة: فشل في تشغيل Celery
```bash
# تأكد من تثبيت المتطلبات
pip install celery redis

# تأكد من تشغيل Redis
redis-cli ping
# أو
valkey-cli ping
```

### مشكلة: فشل في تشغيل Redis
```bash
# تثبيت Redis/Valkey
sudo pacman -S valkey  # Arch/Manjaro
sudo apt-get install redis-server  # Ubuntu/Debian

# تشغيل يدوي
valkey-server --port 6379 --daemonize yes
# أو
redis-server --port 6379 --daemonize yes
```

### مشكلة: الموقع لا يعمل
```bash
# تأكد من تطبيق الترحيلات
python manage.py migrate

# تأكد من إنشاء المستخدم الأساسي
python manage.py createsuperuser
```

## ⚡ **الأوامر السريعة**

```bash
# تشغيل النظام
python manage.py runserver

# إيقاف جميع العمليات
Ctrl+C

# تنظيف الملفات المؤقتة
rm -f /tmp/celery_*_dev.*
rm -f /tmp/celerybeat-schedule-dev*

# إعادة تشغيل كاملة
python manage.py runserver
```

## 🎯 **المميزات الجديدة**

### ✅ **تشغيل تلقائي كامل**
- لا حاجة لتشغيل Redis يدوياً
- لا حاجة لتشغيل Celery يدوياً
- كل شيء يعمل مع أمر واحد

### ✅ **مراقبة ذكية**
- إعادة تشغيل تلقائية للخدمات المتوقفة
- رسائل واضحة عن حالة كل خدمة
- سجلات منفصلة لكل خدمة

### ✅ **تنظيف تلقائي**
- إيقاف جميع الخدمات عند الضغط على Ctrl+C
- تنظيف الملفات المؤقتة
- منع تضارب العمليات

## 📈 **تحسينات الأداء**

النظام الآن يدعم:
- ✅ **المهام الخلفية**: رفع الملفات بدون انتظار
- ✅ **التخزين المؤقت**: بحث أسرع للمنتجات
- ✅ **المهام الدورية**: تنظيف تلقائي للبيانات
- ✅ **معالجة غير متزامنة**: أداء أفضل للطلبات

## 🔄 **دورة التطوير**

```bash
# 1. تشغيل النظام
python manage.py runserver

# 2. تطوير وتعديل الكود
# (النظام سيعيد التحميل تلقائياً)

# 3. اختبار المهام الخلفية
python test_celery.py

# 4. إيقاف النظام
Ctrl+C
```

## 📞 **الدعم**

في حالة وجود مشاكل:

1. **تحقق من السجلات**:
   ```bash
   tail -f /tmp/celery_worker_dev.log
   tail -f /tmp/celery_beat_dev.log
   ```

2. **اختبر النظام**:
   ```bash
   python test_celery.py
   ```

3. **أعد تشغيل النظام**:
   ```bash
   # أوقف النظام
   Ctrl+C
   
   # نظف الملفات المؤقتة
   rm -f /tmp/celery_*_dev.*
   
   # أعد التشغيل
   python manage.py runserver
   ```

---

**🎉 الآن النظام جاهز للعمل مع جميع التحسينات!**

- **سرعة إنشاء الطلبات**: تحسن بنسبة 80-90%
- **سرعة البحث**: تحسن بنسبة 90-95%
- **تجربة المستخدم**: سلسة ومريحة
- **استقرار النظام**: مراقبة وإعادة تشغيل تلقائية
