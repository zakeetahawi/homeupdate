# دليل الحصول على Cloudflare API Token
# Cloudflare API Token Setup Guide

## الخطوات 📋

### 1️⃣ تسجيل الدخول إلى Cloudflare
```
https://dash.cloudflare.com/
```

### 2️⃣ الذهاب إلى API Tokens
```
Profile → API Tokens → Create Token
```
أو مباشرة:
```
https://dash.cloudflare.com/profile/api-tokens
```

### 3️⃣ إنشاء Token جديد
اختر: **"Create Custom Token"**

### 4️⃣ إعدادات Token

**Token Name:**
```
Bank QR System API
```

**Permissions:**
- Account | Workers KV Storage | Edit
- Account | Workers Scripts | Edit

**Account Resources:**
- Include | [اختر حسابك]

**Zone Resources:**
- Include | All zones (أو اختر نطاقك المحدد)

### 5️⃣ إنشاء Token
اضغط على **"Continue to summary"** ثم **"Create Token"**

⚠️ **مهم جداً:** انسخ Token فوراً - لن يظهر مرة أخرى!

---

## تطبيق Token في المشروع

### الطريقة 1: ملف .env (موصى بها)
افتح `/home/zakee/homeupdate/.env` وعدّل السطر:

```env
CLOUDFLARE_SYNC_API_KEY=ضع_التوكن_الحقيقي_هنا
```

### الطريقة 2: متغير بيئة Linux
```bash
export CLOUDFLARE_SYNC_API_KEY="your-real-token-here"
```

---

## معلومات إضافية مطلوبة

### Account ID
للحصول عليه:
1. اذهب إلى https://dash.cloudflare.com/
2. اختر أي Domain من قائمتك
3. في الشريط الجانبي الأيمن، ستجد **"Account ID"**
4. انسخه وأضفه في `.env`:

```env
CLOUDFLARE_ACCOUNT_ID=your-account-id-here
```

### KV Namespace ID
سيتم إنشاؤه تلقائياً عند نشر Worker:

```bash
cd cloudflare-worker
wrangler login
wrangler deploy
```

ثم انسخ Namespace ID وأضفه في `.env`:
```env
CLOUDFLARE_KV_NAMESPACE_ID=your-namespace-id-here
```

---

## اختبار Token

بعد إضافة Token الحقيقي، اختبر:

```bash
cd /home/zakee/homeupdate
python manage.py shell
```

```python
from accounting.cloudflare_sync import sync_bank_accounts_to_cloudflare
result = sync_bank_accounts_to_cloudflare()
print(result)
```

---

## الإعدادات الكاملة في .env

```env
# Cloudflare Settings
CLOUDFLARE_SYNC_ENABLED=True
CLOUDFLARE_WORKER_URL=https://qr.elkhawaga.uk
CLOUDFLARE_ACCOUNT_ID=your-account-id-here
CLOUDFLARE_SYNC_API_KEY=your-api-token-here
CLOUDFLARE_KV_NAMESPACE_ID=your-namespace-id-here
```

---

## حالياً في المشروع 🔍

**الإعدادات الحالية:**
- ✅ CLOUDFLARE_SYNC_ENABLED=True
- ✅ CLOUDFLARE_WORKER_URL=https://qr.elkhawaga.uk
- ⚠️ CLOUDFLARE_SYNC_API_KEY=dev-placeholder-token (مؤقت)
- ⚠️ CLOUDFLARE_ACCOUNT_ID=غير موجود
- ✅ CLOUDFLARE_KV_NAMESPACE_ID=5dad2f4d72b246758bdafa17dfe4eb10

**الوضع الحالي:**
- النظام يعمل في **Development Mode** (وضع المحاكاة)
- المزامنة لا ترفع بيانات فعلية
- جميع العمليات محلية فقط

---

## للتفعيل الكامل

1. احصل على API Token من Cloudflare
2. احصل على Account ID
3. عدّل `.env` بالقيم الحقيقية
4. أعد تشغيل السيرفر
5. اختبر المزامنة

---

## الأمان 🔒

⛔ **لا ترفع** `.env` إلى Git
⛔ **لا تشارك** API Token مع أحد
✅ **استخدم** `.env.example` للمشاركة فقط

الملف `.gitignore` يحتوي بالفعل على:
```
.env
```

✅ آمن!
