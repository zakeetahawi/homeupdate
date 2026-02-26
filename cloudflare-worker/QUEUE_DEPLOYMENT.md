# تفعيل Cloudflare Queues — خطوات النشر

## المتطلبات
- حساب Cloudflare Workers Paid ($5/شهر) ✅ موجود
- `wrangler` مثبت: `npm install -g wrangler`
- مصادقة: `npx wrangler login`

---

## الخطوات (تُنفَّذ مرة واحدة فقط)

```bash
# 1. انتقل لمجلد الـ Worker
cd /home/zakee/homeupdate/cloudflare-worker

# 2. أنشئ الـ Queue على Cloudflare
npx wrangler queues create elkhawaga-sync-queue

# 3. انشر الـ Worker مع الإعدادات الجديدة
npx wrangler deploy

# 4. تحقق أن الـ Queue ظهر مربوطاً
npx wrangler queues list
```

---

## التحقق من نجاح النشر

```bash
# اختبر إرسال طلب مزامنة — يجب أن يعود فوراً بـ {"queued": true}
curl -X POST https://qr.elkhawaga.uk/sync \
  -H "Content-Type: application/json" \
  -H "X-Sync-API-Key: YOUR_API_KEY" \
  -d '{"action": "sync_product", "product": {"code": "TEST"}}'

# النتيجة المتوقعة:
# {"success": true, "queued": true, "action": "sync_product"}
```

---

## كيف تعمل الآن

```
Django (save منتج)
    ↓ signal post_save
    ↓ transaction.on_commit
    ↓ HTTP POST /sync (مللي ثانية)
Cloudflare Worker
    ↓ يدفع للـ Queue فوراً (لا ينتظر)
    ↓ يُعيد {"queued": true} — HTTP 200
elkhawaga-sync-queue
    ↓ يُعالج في الخلفية (max 5 ثوانٍ تأخير، 25 رسالة/دفعة)
    ↓ يكتب في KV بشكل موازٍ (Promise.all)
KV elkhawaga-qr ✅
```

---

## إعدادات Queue (في wrangler.toml)

| الإعداد | القيمة | السبب |
|---------|--------|-------|
| `max_batch_size` | 25 | معالجة 25 منتج في نفس الوقت |
| `max_batch_timeout` | 5s | لا تنتظر أكثر من 5 ثوانٍ لتجميع الدفعة |
| `max_retries` | 3 | إعادة المحاولة تلقائياً عند الفشل |

---

## في حال الاستعادة من مشكلة

إذا تعطّل الـ Worker أو فقدت بيانات KV، استخدم زر **"🔄 مزامنة جميع المنتجات"**
من `Django Admin → Public → Cloudflare Settings` لإعادة رفع كل المنتجات دفعةً واحدة.

---

## ملاحظات مهمة

- **لا تحتاج تشغيل هذه الأوامر مجدداً** — الـ Queue يبقى من إنشائه على Cloudflare
- عند نشر تحديث للـ Worker: فقط `npx wrangler deploy` بدون إنشاء Queue
- ‼️ إذا حذفت الـ Queue وأعدت إنشاءه، يجب `npx wrangler deploy` مرة أخرى
