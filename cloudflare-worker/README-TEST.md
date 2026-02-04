# Cloudflare Worker - نسخة الاختبار 🧪

## نظرة عامة

هذا Worker اختباري لصفحات المنتجات مع حساب **السعر قبل الخصم** تلقائياً حسب النظام التالي:

### نظام الخصومات

| السعر الحالي | نسبة الإضافة | المعامل | مثال |
|-------------|-------------|---------|------|
| 1-400 ج.م | +35% | ×1.35 | 100 → 135 |
| 401-600 ج.م | +30% | ×1.30 | 500 → 650 |
| 601-800 ج.م | +25% | ×1.25 | 700 → 875 |
| 801+ ج.م | +20% | ×1.20 | 1000 → 1200 |

## التثبيت والنشر

### 1. التثبيت المحلي

```bash
cd /home/zakee/homeupdate/cloudflare-worker
npm install
```

### 2. الاختبار المحلي

```bash
# اختبار Worker الاختباري
npx wrangler dev --config wrangler-test.toml

# أو مع env محدد
npx wrangler dev --config wrangler-test.toml --env staging
```

سيعمل على: `http://localhost:8787/{product_code}`

### 3. النشر على Cloudflare

```bash
# نشر على بيئة التطوير
npx wrangler deploy --config wrangler-test.toml

# نشر على بيئة الاختبار (staging)
npx wrangler deploy --config wrangler-test.toml --env staging
```

## إعداد Subdomain للاختبار

### في لوحة Cloudflare DNS:

1. افتح **DNS Settings** لنطاق `elkhawaga.uk`
2. أضف سجل CNAME جديد:
   - **Name**: `test-qr` أو `qr-test`
   - **Target**: `elkhawaga-qr-staging.workers.dev`
   - **Proxy status**: Proxied (برتقالي)
3. احفظ التغييرات

### تفعيل Route في Worker:

بعد إنشاء الـ subdomain، أضف هذا السطر في `wrangler-test.toml` تحت `[env.staging]`:

```toml
route = { pattern = "test-qr.elkhawaga.uk/*", zone_name = "elkhawaga.uk" }
```

ثم أعد النشر:

```bash
npx wrangler deploy --config wrangler-test.toml --env staging
```

## الفروقات عن Worker الأساسي

### ✅ الميزات الجديدة:

1. **حساب السعر قبل الخصم تلقائياً**
   - يعرض السعر الأصلي مشطوب باللون الأحمر
   - يعرض badge "خصم" بجانبه
   - يظهر السعر الحالي بخط كبير ذهبي

2. **شارة الاختبار**
   - شارة حمراء في أعلى الصفحة "🧪 وضع الاختبار"
   - عنوان الصفحة يحتوي على [TEST]

3. **معلومات تصحيح الأخطاء**
   - صندوق أحمر في أسفل البطاقة يعرض:
     * السعر الأصلي
     * المعامل المستخدم
     * السعر قبل الخصم (بدقة عشرية)

## استخدام API للمزامنة

### مزامنة منتج واحد:

```bash
curl -X POST https://test-qr.elkhawaga.uk/sync \
  -H "X-Sync-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "sync_product",
    "product": {
      "code": "TEST001",
      "name": "منتج تجريبي",
      "price": 150,
      "currency": "EGP",
      "category": "اختبار",
      "unit": "قطعة"
    }
  }'
```

### مزامنة متعددة:

```bash
curl -X POST https://test-qr.elkhawaga.uk/sync \
  -H "X-Sync-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "sync_all",
    "products": [
      {"code": "TEST001", "name": "منتج 1", "price": 100, "currency": "EGP"},
      {"code": "TEST002", "name": "منتج 2", "price": 500, "currency": "EGP"}
    ]
  }'
```

## اختبار الصفحات

### أمثلة URLs:

- منتج بسعر 100 ج.م: `https://test-qr.elkhawaga.uk/TEST001`
  - سيعرض: ~~135 ج.م~~ → **100 ج.م**
  
- منتج بسعر 500 ج.م: `https://test-qr.elkhawaga.uk/TEST002`
  - سيعرض: ~~650 ج.م~~ → **500 ج.م**

- منتج غير موجود: `https://test-qr.elkhawaga.uk/NOTFOUND`
  - سيعرض: صفحة 404 مع شارة الاختبار

## التكامل مع Django

استخدم الدوال في `/home/zakee/homeupdate/inventory/`:

```python
from inventory.tasks_cloudflare_sync import sync_single_product_to_cloudflare

# مزامنة منتج
result = sync_single_product_to_cloudflare(product_id)
```

أو من صفحة الاختبار:
- URL: `http://localhost:8000/inventory/cloudflare-test/`

## الأوامر المفيدة

```bash
# عرض logs مباشرة
npx wrangler tail --config wrangler-test.toml

# عرض Worker info
npx wrangler whoami

# حذف Worker
npx wrangler delete --config wrangler-test.toml
```

## الملاحظات

- ✅ Worker الاختباري يستخدم نفس KV الأساسي (آمن للاختبار)
- ✅ يمكن استخدامه بجانب Worker الأساسي دون تعارض
- ✅ جميع التغييرات يمكن نقلها للـ Worker الأساسي بعد الاختبار
- ⚠️ تأكد من تعيين `X-Sync-API-Key` في Secrets:
  ```bash
  npx wrangler secret put X-Sync-API-Key --config wrangler-test.toml
  ```

## الخطوة التالية

بعد التأكد من صحة العمل في الاختبار:

1. انسخ الكود من `src/index-test.js` إلى `src/index.js`
2. احذف قسم Debug Info
3. احذف Test Badge
4. انشر على Worker الأساسي:
   ```bash
   npx wrangler deploy --env production
   ```
