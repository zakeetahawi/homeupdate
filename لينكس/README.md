# 🚀 ملفات تشغيل النظام

## الملفات المتاحة

### 1. 🏭 `run-production.sh`
**للإنتاج مع مراقبة مبسطة + Cloudflare Tunnel**
```bash
./run-production.sh
```
- يستخدم Gunicorn (3 عمال)
- متاح على: https://elkhawaga.uk
- مراقبة كل دقيقة
- تشغيل Cloudflare Tunnel

### 2. 🛠️ `run-development.sh`
**للتطوير مع مراقبة مبسطة + Cloudflare Tunnel**
```bash
./run-development.sh
```
- يستخدم Gunicorn (2 عمال)
- إعادة تحميل تلقائية
- متاح على: https://elkhawaga.uk
- مراقبة كل 30 ثانية
- تشغيل Cloudflare Tunnel

### 3. 🏠 `run-local.sh`
**للتطوير المحلي مع مراقبة مفصلة بدون Tunnel**
```bash
./run-local.sh
```
- يستخدم Django Development Server
- متاح على: http://localhost:8000
- مراقبة مفصلة كل 10 ثواني
- بدون Cloudflare Tunnel

## المستخدم الافتراضي
- **اسم المستخدم:** admin
- **كلمة المرور:** admin123

## ملاحظات
- جميع الملفات تقوم بتفعيل البيئة الافتراضية تلقائياً
- تطبيق التحديثات وتجميع الملفات الثابتة
- إنشاء المستخدم الافتراضي إذا لم يكن موجوداً
- اضغط `Ctrl+C` لإيقاف أي خادم 