# 🚀 دليل خدمة الإنتاج - نظام الخواجة

## 📋 نظرة عامة

هذا الدليل يشرح كيفية استخدام نظام خدمة الإنتاج الذي يشمل:

- ✅ **Gunicorn**: خادم الويب للإنتاج
- ✅ **Celery Worker**: معالجة المهام الخلفية (رفع الملفات، إلخ)
- ✅ **Celery Beat**: المهام المجدولة (تنظيف، نسخ احتياطي)
- ✅ **Cloudflare Tunnel**: الوصول الخارجي عبر https://elkhawaga.uk
- ✅ **النسخ الاحتياطي**: نسخ تلقائي لقاعدة البيانات
- ✅ **المراقبة الدورية**: إعادة تشغيل تلقائي عند الفشل
- ✅ **Log Rotation**: إدارة تلقائية للسجلات

---

## 📦 الملفات المُنشأة

```
/home/zakee/homeupdate/لينكس/
├── run-production-daemon.sh     # سكريبت التشغيل الخلفي الكامل
├── stop-production.sh           # سكريبت الإيقاف الآمن
├── khawaja-production.service   # ملف خدمة SystemD
├── install-service.sh           # سكريبت التثبيت التلقائي
└── run-production.sh            # سكريبت التشغيل التفاعلي (الأصلي)
```

---

## 🔧 التثبيت على جهاز جديد

### الخطوة 1: استنساخ المشروع من GitHub

```bash
cd /home/zakee
git clone https://github.com/zakeetahawi/homeupdate.git
cd homeupdate
```

### الخطوة 2: إنشاء البيئة الافتراضية وتثبيت المتطلبات

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### الخطوة 3: تثبيت الخدمة

```bash
cd /home/zakee/homeupdate/لينكس
sudo ./install-service.sh
```

**هذا السكريبت سيقوم بـ:**
- ✅ التحقق من وجود جميع الملفات
- ✅ إعطاء صلاحيات التنفيذ
- ✅ إنشاء المجلدات المطلوبة
- ✅ نسخ ملف الخدمة إلى `/etc/systemd/system/`
- ✅ تفعيل البدء التلقائي
- ✅ إعداد Log Rotation
- ✅ سؤالك عن بدء الخدمة

---

## 🎮 أوامر إدارة الخدمة

### ▶️ البدء والإيقاف

```bash
# بدء الخدمة
sudo systemctl start khawaja-production

# إيقاف الخدمة
sudo systemctl stop khawaja-production

# إعادة التشغيل
sudo systemctl restart khawaja-production

# إعادة تحميل (بدون إيقاف)
sudo systemctl reload khawaja-production
```

### 📊 المراقبة والحالة

```bash
# حالة الخدمة
sudo systemctl status khawaja-production

# سجلات SystemD
sudo journalctl -u khawaja-production -f

# سجلات النظام
tail -f /home/zakee/homeupdate/logs/production-daemon.log

# جميع السجلات
tail -f /home/zakee/homeupdate/logs/*.log
```

### 🔧 التحكم في البدء التلقائي

```bash
# تفعيل البدء التلقائي
sudo systemctl enable khawaja-production

# تعطيل البدء التلقائي
sudo systemctl disable khawaja-production

# التحقق من حالة التفعيل
sudo systemctl is-enabled khawaja-production
```

---

## 📊 السجلات ومواقعها

| السجل | المسار | الوصف |
|-------|--------|-------|
| **أخطاء Gunicorn** | `logs/gunicorn-error.log` | أخطاء Django والخادم |
| **وصول Gunicorn** | `logs/gunicorn-access.log` | طلبات HTTP |
| **Celery Worker** | `logs/celery-worker.log` | مهام الخلفية |
| **Celery Beat** | `logs/celery-beat.log` | المهام المجدولة |
| **Cloudflare** | `logs/cloudflared.log` | الجسر الخارجي |
| **النسخ الاحتياطي** | `logs/db-backup.log` | عمليات النسخ |
| **Redis** | `logs/redis.log` | قاعدة الكاش |
| **النظام** | `logs/production-daemon.log` | سجل الخدمة العام |
| **SystemD** | `logs/systemd-production.log` | مخرجات SystemD |

### 🔍 أوامر متابعة السجلات

```bash
# متابعة الأخطاء
tail -f /home/zakee/homeupdate/logs/gunicorn-error.log

# متابعة كل شيء
tail -f /home/zakee/homeupdate/logs/*.log

# البحث عن أخطاء
grep -i "error\|exception\|failed" /home/zakee/homeupdate/logs/*.log

# آخر 100 سطر من الأخطاء
tail -100 /home/zakee/homeupdate/logs/gunicorn-error.log
```

---

## 🌐 العناوين والوصول

بعد التشغيل، يمكن الوصول للنظام عبر:

| العنوان | الوصف |
|---------|-------|
| `http://localhost:8000` | الوصول المحلي |
| `http://[IP]:8000` | الوصول من الشبكة المحلية |
| `https://elkhawaga.uk` | الوصول الخارجي (Cloudflare) |

**بيانات الدخول الافتراضية:**
- **المستخدم:** `admin`
- **كلمة المرور:** `admin123`

---

## 🔄 المراقبة الدورية التلقائية

الخدمة تقوم تلقائياً بـ:

| المهمة | التوقيت | الوصف |
|--------|---------|-------|
| **فحص Gunicorn** | كل 30 ثانية | إعادة تشغيل إذا توقف |
| **فحص Celery** | كل 30 ثانية | إعادة تشغيل إذا توقف |
| **فحص Tunnel** | كل دقيقة | إعادة تشغيل إذا انقطع |
| **فحص قاعدة البيانات** | كل 5 دقائق | مراقبة الاتصالات |
| **تنظيف الإشعارات** | كل 30 دقيقة | حذف القديمة |
| **رفع الملفات المعلقة** | كل 10 دقائق | استكمال الرفع |

---

## 💾 النسخ الاحتياطي

النسخ الاحتياطية تُحفظ في:
```
/home/zakee/homeupdate/media/backups/
```

تتم النسخ:
- ✅ فور بدء الخدمة
- ✅ كل ساعة تلقائياً

---

## 🛠️ استكشاف الأخطاء

### المشكلة: الخدمة لا تبدأ

```bash
# 1. فحص السجلات
sudo journalctl -u khawaja-production -n 100

# 2. فحص الصلاحيات
ls -la /home/zakee/homeupdate/لينكس/*.sh

# 3. اختبار السكريبت يدوياً
cd /home/zakee/homeupdate/لينكس
./run-production-daemon.sh

# 4. التحقق من البيئة
ls -la /home/zakee/homeupdate/venv
```

### المشكلة: Cloudflare Tunnel لا يعمل

```bash
# 1. التحقق من الملفات
ls -la /home/zakee/homeupdate/cloudflared
ls -la /home/zakee/homeupdate/cloudflared.yml

# 2. اختبار الاتصال
curl -s https://elkhawaga.uk

# 3. فحص السجل
tail -50 /home/zakee/homeupdate/logs/cloudflared.log
```

### المشكلة: استهلاك موارد عالي

```bash
# 1. فحص الاستهلاك
systemctl status khawaja-production | grep Memory

# 2. تعديل الحدود في ملف الخدمة
# MemoryMax=2G → MemoryMax=1G
sudo nano /etc/systemd/system/khawaja-production.service
sudo systemctl daemon-reload
sudo systemctl restart khawaja-production
```

### المشكلة: قاعدة البيانات غير متصلة

```bash
# 1. فحص PostgreSQL
sudo systemctl status postgresql

# 2. اختبار الاتصال
cd /home/zakee/homeupdate
source venv/bin/activate
python manage.py dbshell
```

---

## 📝 ملاحظات مهمة

### ✅ المزايا

1. **بدء تلقائي**: يعمل مع بدء الكمبيوتر (قبل تسجيل الدخول)
2. **إعادة تشغيل تلقائي**: عند فشل أي خدمة
3. **موارد محدودة**: 2GB ذاكرة كحد أقصى
4. **سجلات كاملة**: كل شيء مسجل للمتابعة
5. **أمان**: صلاحيات محدودة
6. **Log Rotation**: تنظيف تلقائي للسجلات

### ⚠️ متطلبات

1. **نظام التشغيل**: Linux مع SystemD
2. **Python**: 3.8+
3. **Redis**: للتخزين المؤقت وCelery
4. **قاعدة البيانات**: PostgreSQL أو MySQL
5. **المستخدم**: `zakee` (أو تعديل الملفات)

### 🔄 التحديث

عند سحب تحديثات من GitHub:

```bash
cd /home/zakee/homeupdate
git pull origin main

# إعادة تشغيل الخدمة
sudo systemctl restart khawaja-production
```

---

## 🚀 التثبيت السريع (ملخص)

```bash
# 1. استنساخ المشروع
cd /home/zakee
git clone https://github.com/zakeetahawi/homeupdate.git
cd homeupdate

# 2. إعداد البيئة
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. تثبيت الخدمة
cd لينكس
sudo ./install-service.sh

# 4. التحقق
sudo systemctl status khawaja-production
```

---

## 📞 المساعدة

للمشاكل والاستفسارات:

- 📂 **السجلات**: `/home/zakee/homeupdate/logs/`
- 🔍 **الحالة**: `sudo systemctl status khawaja-production`
- 📊 **المراقبة**: `sudo journalctl -u khawaja-production -f`

---

✅ **النظام جاهز للنشر على أي جهاز Linux!** 🎉
