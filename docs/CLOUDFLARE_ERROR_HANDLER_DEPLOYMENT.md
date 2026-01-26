# دليل رفع Worker على Cloudflare - خطوة بخطوة

## الطريقة الأولى: عبر Cloudflare Dashboard (الأسهل - موصى بها)

### الخطوة 1: تسجيل الدخول إلى Cloudflare
1. افتح المتصفح واذهب إلى: https://dash.cloudflare.com
2. سجل دخول بحسابك

### الخطوة 2: الذهاب إلى Workers
1. من القائمة الجانبية، اضغط على **"Workers & Pages"**
2. اضغط على زر **"Create Application"** (أزرق)
3. اختر **"Create Worker"**

### الخطوة 3: إنشاء Worker
1. سيفتح محرر Worker
2. **اسم Worker**: اكتب `elkhawaga-error-handler`
3. **لا تضغط Deploy بعد!**

### الخطوة 4: نسخ الكود
1. افتح ملف: `/home/zakee/homeupdate/cloudflare-worker/src/error-handler.js`
2. انسخ **كل المحتوى** من السطر الأول حتى النهاية
3. ارجع لمحرر Cloudflare
4. **احذف كل الكود الموجود** في المحرر
5. **الصق الكود** الذي نسخته

### الخطوة 5: حفظ ونشر Worker
1. اضغط **"Save and Deploy"** (أزرق في الأعلى)
2. انتظر حتى تظهر رسالة "Successfully deployed"

---

## الخطوة 6: إعداد Routes (مهم جداً!)

### 6.1: الذهاب إلى إعدادات Worker
1. بعد النشر، ستكون في صفحة Worker
2. اضغط على تبويب **"Triggers"** (في الأعلى)
3. ابحث عن قسم **"Routes"**

### 6.2: إضافة Routes للنطاقات

**مهم جداً**: يجب إضافة route لكل نطاق على حدة!

#### Route 1: النطاق الرئيسي
1. اضغط **"Add route"**
2. **Route**: اكتب `elkhawaga.uk/*`
3. **Zone**: اختر `elkhawaga.uk`
4. اضغط **"Add route"**

#### Route 2: WWW
1. اضغط **"Add route"** مرة أخرى
2. **Route**: اكتب `www.elkhawaga.uk/*`
3. **Zone**: اختر `elkhawaga.uk`
4. اضغط **"Add route"**

#### Route 3: CRM
1. اضغط **"Add route"**
2. **Route**: اكتب `crm.elkhawaga.uk/*`
3. **Zone**: اختر `elkhawaga.uk`
4. اضغط **"Add route"**

#### Route 4: API
1. اضغط **"Add route"**
2. **Route**: اكتب `api.elkhawaga.uk/*`
3. **Zone**: اختر `elkhawaga.uk`
4. اضغط **"Add route"**

#### Route 5: Admin
1. اضغط **"Add route"**
2. **Route**: اكتب `admin.elkhawaga.uk/*`
3. **Zone**: اختر `elkhawaga.uk`
4. اضغط **"Add route"**

---

## الخطوة 7: التحقق من العمل

### 7.1: اختبار مع السيرفر يعمل
1. تأكد أن السيرفر المحلي شغال
2. افتح المتصفح واذهب إلى: https://www.elkhawaga.uk
3. **النتيجة المتوقعة**: الموقع يعمل بشكل طبيعي ✅

### 7.2: اختبار مع السيرفر متوقف
1. أوقف السيرفر المحلي:
```bash
# في Terminal حيث يعمل السيرفر
# اضغط Ctrl+C
```

2. افتح المتصفح واذهب إلى: https://www.elkhawaga.uk
3. **النتيجة المتوقعة**: صفحة الخطأ المخصصة تظهر ✅

**يجب أن ترى:**
- ✅ خلفية زخرفية داكنة
- ✅ رسالة "السيرفر متوقف مؤقتاً"
- ✅ رقم الخطأ "Cloudflare Error 1033"
- ✅ رسالة "الرجاء التواصل مع مدير النظام"
- ✅ Footer بنفس تصميم التطبيق

---

## ملاحظات مهمة جداً

### ⚠️ تحذير 1: Worker كـ Proxy
Worker **لا يستبدل** Cloudflare Tunnel!
- Worker يحاول الاتصال بالسيرفر أولاً
- إذا نجح → يمرر الطلب للسيرفر
- إذا فشل → يعرض صفحة الخطأ

### ⚠️ تحذير 2: ترتيب Routes
تأكد أن Routes موجودة **قبل** أي routes أخرى للنطاق

### ⚠️ تحذير 3: التخزين المؤقت
إذا لم تظهر التغييرات فوراً:
1. امسح cache المتصفح (Ctrl+Shift+Delete)
2. أو افتح نافذة خاصة (Incognito)

---

## الطريقة الثانية: عبر Wrangler CLI (للمتقدمين)

### المتطلبات
```bash
# تثبيت Node.js و npm إذا لم يكن مثبتاً
# تثبيت wrangler
npm install -g wrangler
```

### الخطوات
```bash
# 1. تسجيل الدخول
wrangler login

# 2. الذهاب لمجلد Worker
cd /home/zakee/homeupdate/cloudflare-worker

# 3. النشر
wrangler deploy --config wrangler-error.toml

# 4. بعد النشر، يجب إضافة Routes يدوياً من Dashboard
```

**ملاحظة**: حتى مع Wrangler CLI، يجب إضافة Routes من Dashboard!

---

## استكشاف الأخطاء

### المشكلة 1: Worker لا يعمل
**الحل**:
1. تحقق من Routes في Dashboard
2. تأكد أن Worker منشور (Status: Active)
3. راجع Logs: Workers → اسم Worker → Logs

### المشكلة 2: الموقع لا يعمل حتى مع السيرفر شغال
**الحل**:
1. تحقق من كود Worker
2. تأكد أن Worker يستخدم `fetch(request)` لتمرير الطلبات
3. احذف Routes وأعد إضافتها

### المشكلة 3: صفحة الخطأ لا تظهر
**الحل**:
1. تأكد أن Worker منشور
2. تحقق من Routes
3. امسح cache المتصفح

### المشكلة 4: الخلفية لا تظهر
**الحل**:
- الخلفية تحتاج السيرفر يكون شغال لتحميل الصورة
- إذا السيرفر متوقف، ستظهر الخلفية الاحتياطية (gradient)

---

## الملفات المرتبطة

- **Worker Code**: `/home/zakee/homeupdate/cloudflare-worker/src/error-handler.js`
- **Preview**: `/home/zakee/homeupdate/cloudflare-worker/preview.html`
- **Config**: `/home/zakee/homeupdate/cloudflare-worker/wrangler-error.toml`

---

## خلاصة سريعة

```
1. Dashboard → Workers & Pages → Create Worker
2. اسم: elkhawaga-error-handler
3. نسخ كود من error-handler.js
4. Save and Deploy
5. Triggers → Routes → Add route لكل نطاق
6. اختبار: أوقف السيرفر وافتح الموقع
```

**وقت التنفيذ المتوقع**: 5-10 دقائق ⏱️

---

## الدعم

إذا واجهت أي مشاكل:
1. راجع Cloudflare Workers Logs
2. تحقق من إعدادات Tunnel في `cloudflared.yml`
3. تأكد من Routes مضبوطة بشكل صحيح
