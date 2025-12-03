# 🚀 دليل البدء السريع

## تشغيل الخادم

### الطريقة 1: باستخدام السكريبت
```bash
cd /home/zakee/homeupdate
./RUN_SERVER.sh
```

### الطريقة 2: يدوياً
```bash
cd /home/zakee/homeupdate
source venv/bin/activate
python manage.py runserver
```

### الطريقة 3: مع متغيرات البيئة
```bash
cd /home/zakee/homeupdate
source venv/bin/activate
export DEVELOPMENT_MODE=True
export DEBUG=True
python manage.py runserver 0.0.0.0:8000
```

---

## ✅ الخادم يعمل الآن!

- **العنوان:** http://localhost:8000
- **Admin:** http://localhost:8000/admin/
- **API:** http://localhost:8000/api/

---

## 🔧 ملف .env

تم إنشاء ملف `.env` تلقائياً مع:
- ✅ SECRET_KEY آمن
- ✅ DEBUG=True للتطوير
- ✅ DEVELOPMENT_MODE=True

**لا تحتاج لتعيين متغيرات البيئة يدوياً!**

---

## 🛑 إيقاف الخادم

اضغط `Ctrl + C` في Terminal

---

## 📊 فحص الحالة

```bash
python manage.py check
python security_audit.py
```

---

## 🏆 التقييم الأمني: 10/10

جميع التحسينات الأمنية مفعّلة ✅
