# دليل الرفع على Cloudflare Workers
# Cloudflare Workers Deployment Guide

## 📊 المعلومات الحالية من Git History

### 🔑 البيانات المحفوظة

من الـ commits السابقة (21 ديسمبر 2025):

```toml
# من wrangler.toml
KV Namespace ID: 5dad2f4d72b246758bdafa17dfe4eb10
Worker Name: elkhawaga-qr
Worker URL: https://qr.elkhawaga.uk
Domain: elkhawaga.uk
```

**الإعدادات الموجودة:**
- ✅ KV Namespace موجود ومعرّف
- ✅ Worker كان منشوراً من قبل
- ✅ النطاق: qr.elkhawaga.uk

---

## 🚀 خطوات الرفع (من السابق)

### 1️⃣ تثبيت Wrangler CLI

```bash
# تثبيت عالمي
sudo npm install -g wrangler

# أو تثبيت محلي في المشروع
cd /home/zakee/homeupdate/cloudflare-worker
npm install wrangler --save-dev
```

### 2️⃣ تسجيل الدخول

```bash
cd /home/zakee/homeupdate/cloudflare-worker
wrangler login
```

سيفتح متصفح للمصادقة على حسابك في Cloudflare.

### 3️⃣ التحقق من الإعدادات

تأكد من `wrangler.toml` (موجود بالفعل):

```toml
name = "elkhawaga-qr"
main = "src/index.js"
compatibility_date = "2024-01-01"
workers_dev = true

# KV Namespace binding
[[kv_namespaces]]
binding = "PRODUCTS_KV"
id = "5dad2f4d72b246758bdafa17dfe4eb10"

# Production environment
[env.production]
name = "elkhawaga-qr"
workers_dev = false
route = { pattern = "qr.elkhawaga.uk/*", zone_name = "elkhawaga.uk" }
```

### 4️⃣ النشر

```bash
# للتطوير (Testing)
wrangler deploy

# للإنتاج (Production)
wrangler deploy --env production
```

---

## 📝 تحديث نظام Bank Accounts

### الفرق بين النظامين

| العنصر | نظام المنتجات القديم | نظام Bank Accounts الجديد |
|--------|---------------------|---------------------------|
| **Model** | `inventory/models.py` | `accounting/models.py` (BankAccount) |
| **Sync Module** | `public/cloudflare_sync.py` | `accounting/cloudflare_sync.py` |
| **Management Command** | `sync_to_cloudflare` | `sync_bank_accounts` |
| **KV Keys** | `product:<code>` | `bank:<code>`, `bank:all` |
| **Worker Routes** | `/p/<code>` | `/bank/<code>`, `/bank/all` |

### تحديث Worker لدعم Bank Accounts

الكود موجود بالفعل في `cloudflare-worker/src/index.js` - تم إضافته مؤخراً!

---

## 🔐 الحصول على API Token

### الطريقة الصحيحة (من التجربة السابقة):

1. **الدخول لـ Cloudflare Dashboard:**
   ```
   https://dash.cloudflare.com/profile/api-tokens
   ```

2. **Create Token → Edit Cloudflare Workers**
   - أو استخدم Template: "Edit Cloudflare Workers"

3. **الصلاحيات المطلوبة:**
   - Account | Workers KV Storage | Edit
   - Account | Workers Scripts | Edit
   - Zone | Workers Routes | Edit

4. **نسخ Token وإضافته في `.env`:**
   ```bash
   cd /home/zakee/homeupdate
   nano .env
   ```

   أضف:
   ```env
   CLOUDFLARE_SYNC_API_KEY=your-real-api-token-here
   ```

---

## 🔧 الإعداد الكامل

### 1. ملف .env

```env
# Cloudflare Workers Settings
CLOUDFLARE_SYNC_ENABLED=True
CLOUDFLARE_WORKER_URL=https://qr.elkhawaga.uk
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_SYNC_API_KEY=your-api-token
CLOUDFLARE_KV_NAMESPACE_ID=5dad2f4d72b246758bdafa17dfe4eb10

# Site Settings
SITE_URL=https://www.elkhawaga.uk
MAIN_SITE_URL=https://elkhawaga.com
SITE_NAME=الخواجة
```

### 2. الحصول على Account ID

```bash
# بعد wrangler login
wrangler whoami
```

أو من Dashboard:
```
https://dash.cloudflare.com/ → اختر أي Domain → Account ID في الجانب
```

### 3. تثبيت Dependencies

```bash
cd /home/zakee/homeupdate/cloudflare-worker

# إذا لم يكن موجود package.json dependencies
npm install

# تثبيت wrangler محلياً
npm install wrangler --save-dev
```

### 4. اختبار محلي

```bash
cd /home/zakee/homeupdate/cloudflare-worker
npx wrangler dev
```

سيفتح على: `http://localhost:8787`

اختبر:
- `/bank/CIB001` (لحساب واحد)
- `/bank/all` (لكل الحسابات)

### 5. الرفع للإنتاج

```bash
# تسجيل دخول مرة واحدة
npx wrangler login

# الرفع
npx wrangler deploy --env production
```

---

## 📊 مزامنة البيانات

### من Django Admin

1. افتح Admin: `http://127.0.0.1:8000/admin/accounting/bankaccount/`
2. اختر الحسابات
3. Actions → **"🔄 مزامنة مع Cloudflare"**

### من Command Line

```bash
cd /home/zakee/homeupdate

# مزامنة جميع الحسابات النشطة
python manage.py sync_bank_accounts

# توليد QR Codes
python manage.py generate_bank_qr --all
```

---

## 🧪 الاختبار

### 1. اختبار محلي (Development Mode)

النظام حالياً في وضع التطوير:
- `CLOUDFLARE_SYNC_API_KEY=dev-placeholder-token`
- المزامنة تحاكي النجاح فقط
- لا يتم رفع بيانات فعلية

### 2. اختبار Worker محلياً

```bash
cd /home/zakee/homeupdate/cloudflare-worker
npx wrangler dev
```

افتح: `http://localhost:8787/bank/CIB001`

### 3. اختبار بعد النشر

```
https://qr.elkhawaga.uk/bank/CIB001
https://qr.elkhawaga.uk/bank/all
```

---

## 📱 التحقق من النشر

```bash
# عرض معلومات Worker
npx wrangler deployments list

# عرض Logs مباشرة
npx wrangler tail

# التحقق من KV
npx wrangler kv:key list --namespace-id=5dad2f4d72b246758bdafa17dfe4eb10
```

---

## 🔄 سير العمل الكامل

```bash
# 1. تأكد من البيئة
cd /home/zakee/homeupdate

# 2. فعّل virtual environment
source venv/bin/activate

# 3. تأكد من الإعدادات
cat .env | grep CLOUDFLARE

# 4. إنشاء حساب بنكي من Admin
# افتح http://127.0.0.1:8000/admin/accounting/bankaccount/add/

# 5. مزامنة من Django
python manage.py sync_bank_accounts

# 6. انتقل لـ Worker
cd cloudflare-worker

# 7. الرفع
npx wrangler deploy --env production

# 8. اختبار
curl https://qr.elkhawaga.uk/bank/CIB001
```

---

## ⚠️ المشاكل الشائعة وحلولها

### 1. "wrangler: command not found"

```bash
# استخدم npx
npx wrangler --version

# أو ثبت عالمياً
sudo npm install -g wrangler
```

### 2. "KV namespace not found"

KV Namespace موجود بالفعل: `5dad2f4d72b246758bdafa17dfe4eb10`

إذا احتجت إنشاء جديد:
```bash
npx wrangler kv:namespace create "PRODUCTS_KV"
```

### 3. "Authentication required"

```bash
npx wrangler login
```

### 4. "Route already exists"

Worker كان منشوراً من قبل على `qr.elkhawaga.uk`

للتحديث فقط:
```bash
npx wrangler deploy --env production
```

---

## 📚 الأوامر المفيدة

```bash
# معلومات الحساب
npx wrangler whoami

# قائمة Workers
npx wrangler deployments list

# حذف Worker
npx wrangler delete

# عرض KV keys
npx wrangler kv:key list --namespace-id=5dad2f4d72b246758bdafa17dfe4eb10

# قراءة قيمة من KV
npx wrangler kv:key get "bank:CIB001" --namespace-id=5dad2f4d72b246758bdafa17dfe4eb10

# حذف key من KV
npx wrangler kv:key delete "bank:CIB001" --namespace-id=5dad2f4d72b246758bdafa17dfe4eb10

# مسح كل KV (احذر!)
npx wrangler kv:bulk delete --namespace-id=5dad2f4d72b246758bdafa17dfe4eb10
```

---

## ✅ Checklist قبل الرفع

- [ ] تسجيل دخول: `npx wrangler login`
- [ ] API Token موجود في `.env`
- [ ] Account ID موجود في `.env`
- [ ] KV Namespace ID صحيح: `5dad2f4d72b246758bdafa17dfe4eb10`
- [ ] Worker code محدث في `src/index.js`
- [ ] اختبار محلي: `npx wrangler dev`
- [ ] مزامنة البيانات: `python manage.py sync_bank_accounts`
- [ ] النشر: `npx wrangler deploy --env production`
- [ ] اختبار الإنتاج: `https://qr.elkhawaga.uk/bank/CIB001`

---

## 🎯 الخلاصة

**البيانات موجودة ومحفوظة:**
- ✅ KV Namespace ID: `5dad2f4d72b246758bdafa17dfe4eb10`
- ✅ Worker Name: `elkhawaga-qr`
- ✅ Domain: `qr.elkhawaga.uk`
- ✅ Worker Code: `cloudflare-worker/src/index.js`
- ✅ Config: `cloudflare-worker/wrangler.toml`

**ما تحتاجه للرفع:**
- 🔑 API Token من Cloudflare (مرة واحدة)
- 🆔 Account ID من Dashboard
- 🚀 `npx wrangler deploy --env production`

**تم إنشاء النظام بتاريخ:** 21 ديسمبر 2025
**آخر تحديث:** 23 ديسمبر 2025
