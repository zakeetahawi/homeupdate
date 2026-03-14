# 📝 ملاحظات مهمة للتشغيل

## ⚠️ تفعيل البيئة الافتراضية

**المشكلة:** الأوامر تفشل لأن البيئة الافتراضية غير مفعلة

**الحل:**

### الطريقة 1: تفعيل يدوي
```bash
source venv/bin/activate
```

بعد ذلك يمكنك تشغيل أي أمر:
```bash
python manage.py check --deploy
python scripts/security/check_api_permissions.py
python scripts/security/migrate_secrets.py
```

### الطريقة 2: استخدام السكريبت المساعد
```bash
./activate_and_run.sh python manage.py check --deploy
./activate_and_run.sh python scripts/security/migrate_secrets.py
```

### الطريقة 3: فتح shell مع البيئة مفعلة
```bash
./activate_and_run.sh
# الآن البيئة مفعلة تلقائياً
```

---

## 🚀 الأوامر المطلوب تشغيلها

### 1. نقل الأسرار (أولوية عالية)
```bash
source venv/bin/activate
python scripts/security/migrate_secrets.py
```

**ملاحظة:** سيعطيك كلمة مرور جديدة، احفظها!

### 2. تحديث كلمة مرور PostgreSQL
```bash
# استخدم كلمة المرور من الخطوة السابقة
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'NEW_PASSWORD_HERE';"
```

### 3. فحص صلاحيات API
```bash
source venv/bin/activate
python scripts/security/check_api_permissions.py
```

### 4. فحص Django
```bash
source venv/bin/activate
python manage.py check --deploy
```

### 5. حذف الملفات الاحتياطية
```bash
bash scripts/cleanup/delete_backups.sh
```

### 6. تثبيت أدوات التطوير (اختياري)
```bash
source venv/bin/activate
pip install black isort flake8 mypy django-stubs
```

---

## ✅ التحقق من التثبيت

```bash
source venv/bin/activate
python -c "import django; print(f'Django {django.get_version()}')"
```

يجب أن يطبع: `Django 6.0`

---

## 🔄 إعادة تشغيل الخادم

بعد تطبيق جميع التغييرات:

```bash
source venv/bin/activate
python manage.py runserver
```

أو إذا كنت تستخدم Gunicorn:

```bash
source venv/bin/activate
gunicorn crm.wsgi:application --bind 0.0.0.0:8000
```

---

## 📊 ملخص الإصلاحات المطبقة

### ✅ مكتمل:
1. نقل كلمة مرور قاعدة البيانات إلى `.env`
2. إزالة `DisableCSRFMiddleware`
3. تقليل مدة JWT إلى 15 دقيقة
4. إصلاح `force_debug_cursor`
5. إصلاح ملح التشفير
6. إصلاح استعلام N+1
7. إضافة نظام صلاحيات للمخزون

### ⏳ مطلوب منك:
1. تشغيل `migrate_secrets.py`
2. تحديث كلمة مرور PostgreSQL
3. إعادة تشغيل الخادم

---

## 🆘 في حالة المشاكل

### المشكلة: "No module named 'django'"
**الحل:** تأكد من تفعيل البيئة الافتراضية
```bash
source venv/bin/activate
```

### المشكلة: "Permission denied"
**الحل:** أعط صلاحيات التنفيذ
```bash
chmod +x activate_and_run.sh
chmod +x scripts/cleanup/delete_backups.sh
```

### المشكلة: "DB_PASSWORD not set"
**الحل:** تأكد من وجود `.env` وتشغيل `migrate_secrets.py`

---

**آخر تحديث:** 2026-01-22 01:11:29
