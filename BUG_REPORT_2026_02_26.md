# تقرير الأخطاء — 26 فبراير 2026
**النظام:** El-Khawaga ERP  
**الفترة المفحوصة:** 2026-02-24 — 2026-02-26  
**آخر commit قبل الفحص:** `301ad868` (Fix BUG-011 & BUG-012 — 2026-02-25)  
**نقطة المرجع:** آخر restart للخدمة `2026-02-25 12:53:08`  
**الملفات المفحوصة:** `service_error.log`, `django.log`, `errors.log`, `startup.log`, `cloudflared.log`, `postgres-monitor.log`, `security.log`, `db_backup.log`

---

## نتيجة الإصلاحات السابقة ✅

| البق | الحالة | التكرار بعد الإصلاح |
|------|--------|----------------------|
| BUG-011 (`deduct_inventory_for_cutting` ImportError) | ✅ **مُصلح** — 0 مرة بعد 12:53 | 0 |
| BUG-012 (`duplicate key — InstallationArchive`) | ✅ **مُصلح** — 0 مرة بعد 12:53 | 0 |

---

## ملخص الأخطاء الحالية

| رقم | الشدة | العدد | الوصف | الحالة |
|-----|-------|-------|-------|--------|
| BUG-017 | 🔴 حرج (جديد) | 15 | `AttributeError: 'NoneType'` في `inventory_integration.py:35` | مفتوح |
| BUG-018 | 🟡 متوسط (جديد) | 20 | pgBouncer `connection refused` port 6432 | مفتوح |
| BUG-019 | 🟡 متوسط (جديد) | 13 | Cloudflare KV `429 Too Many Requests` | مفتوح |
| BUG-013 | 🟡 متوسط (مستمر) | 26 | محاولة سحب من مستودع فارغ (2000 / الادويه) | مفتوح |
| BUG-014 | 🟠 تحذير (متكرر) | 3 | Celery Worker يفشل عند الإقلاع | مفتوح |

---

## BUG-017 🔴 — `AttributeError: 'NoneType' object has no attribute 'product'`

### الوصف
بعد إصلاح BUG-011 وتغيير اسم الدالة إلى `complete_inventory_deduction`، أصبحت الدالة **تُستدعى بنجاح**، لكنها تنهار داخلياً عندما يكون `cutting_item.order_item = None` (عناصر القماش الخارجي `is_external=True`).

### السجل
```
[2026-02-25 13:35:40] ERROR - خطأ في خصم المخزون للعنصر 18130: 'NoneType' object has no attribute 'product'
Traceback (most recent call last):
  File ".../cutting/models.py", line 452, in mark_as_completed
    transaction = complete_inventory_deduction(self, user)
  File ".../cutting/inventory_integration.py", line 335, in complete_inventory_deduction
    return InventoryIntegrationService.process_cutting_completion(cutting_item, user)
  File ".../cutting/inventory_integration.py", line 35, in process_cutting_completion
    product = cutting_item.order_item.product
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'product'
```

### إحصائيات
- **15 خطأ** بعد تفعيل الإصلاح (12:53)
- العناصر المتأثرة: `18130`, `18197`, `18199`, `18218`, وأخرى
- يحدث كل مرة يُكتمل فيها عنصر تقطيع خارجي

### السبب الجذري
```python
# cutting/inventory_integration.py — السطر 35 (خاطئ)
product = cutting_item.order_item.product  # ← order_item قد يكون None!
required_quantity = cutting_item.order_item.quantity + cutting_item.additional_quantity  # ← نفس المشكلة
```

المشكلة موجودة في **4 أماكن** داخل `cutting/inventory_integration.py`:
- السطر **35** — `process_cutting_completion()`
- السطر **37** — `process_cutting_completion()`
- السطر **121** — (دالة أخرى)
- السطر **165-166** — (دالة أخرى)
- السطر **301** — إشعار نقص المخزون
- السطر **321** — إشعار الخصم

### طريقة الإصلاح
**الملف:** `cutting/inventory_integration.py`  
**السطر 33-38:**

```python
# قبل الإصلاح
product = cutting_item.order_item.product
required_quantity = (
    cutting_item.order_item.quantity + cutting_item.additional_quantity
)

# بعد الإصلاح
# إرجاع None بدون خطأ لعناصر التقطيع الخارجية
if not cutting_item.order_item:
    logger.info(f"⏭️ تخطي خصم المخزون للعنصر {cutting_item.id} — قماش خارجي بدون order_item")
    return None

product = cutting_item.order_item.product
if not product:
    logger.warning(f"⚠️ العنصر {cutting_item.id} لديه order_item بدون product — تخطي الخصم")
    return None

required_quantity = (
    cutting_item.order_item.quantity + cutting_item.additional_quantity
)
```

### الأثر
خصم المخزون لا يحدث للعناصر الخارجية (متوقع)، لكنه يُولّد أخطاء في كل مرة.

---

## BUG-018 🟡 — pgBouncer `OperationalError: connection refused` port 6432

### الوصف
أثناء إعادة تشغيل الخدمة في `12:50:11`، كانت pgBouncer غير متاحة لفترة قصيرة، مما تسبب في رفض طلبات المستخدمين بـ HTTP 500.

### السجل
```
[2026-02-25 12:50:11] ERROR django.request - Internal Server Error: /accounts/api/messages/recent/
psycopg2.OperationalError: connection to server at "localhost" (::1), port 6432 failed: Connection refused
  Is the server running on that host and accepting TCP/IP connections?
```

### إحصائيات
- **20 سطر** في `errors.log` (تراجعبيكات متعددة لنفس الحادث)
- حادث واحد — أثناء إعادة التشغيل في 12:50

### السبب
pgBouncer port 6432 لم يكن يعمل عند محاولة middleware تحديد هوية المستخدم.

### طريقة الإصلاح
**الخيار أ** — إضافة retry في `settings.py`:
```python
# في DATABASES
'OPTIONS': {
    'connect_timeout': 5,
},
'CONN_MAX_AGE': 60,
```

**الخيار ب** — التحقق من ترتيب بدء الخدمات:
```bash
# systemd service dependency
After=pgbouncer.service
Requires=pgbouncer.service
```

### الأثر
طلبات المستخدمين تفشل بـ 500 أثناء إعادة تشغيل الخادم.

---

## BUG-019 🟡 — Cloudflare KV `429 Too Many Requests`

### الوصف
عند مزامنة بيانات المنتجات مع Cloudflare Workers KV، يُجيب Cloudflare API بـ `429 Too Many Requests`، مما يعني أن النظام يتجاوز حدود معدل الطلبات (Rate Limit) المسموح بها.

### السجل
```
[2026-02-25 16:59:39] ERROR - Cloudflare sync failed: 500 - {"error":"KV PUT failed: 429 Too Many Requests","mode":"production"}
[2026-02-25 19:15:32] ERROR - Cloudflare sync failed: 500 - {"error":"KV DELETE failed: 429 Too Many Requests","mode":"production"}
```

### إحصائيات
- **9 خطأ** `KV PUT 429`
- **4 أخطاء** `KV DELETE 429`
- **13 خطأ** إجمالاً في `service_error.log`

### السبب الجذري
**الملف:** `public/cloudflare_sync.py`  
عمليات المزامنة تُرسَل دفعة واحدة دون احترام Rate Limit وهي:
- **Write operations**: 1000 طلب/دقيقة لكل KV namespace

### طريقة الإصلاح
**الملف:** `public/cloudflare_sync.py` أو `inventory/variant_services.py:549`

```python
import time

def sync_to_cloudflare_kv(data_list):
    """مزامنة مع exponential backoff عند الـ 429"""
    for i, item in enumerate(data_list):
        for attempt in range(3):  # 3 محاولات
            try:
                response = kv_put(item)
                break
            except CloudflareRateLimitError:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Cloudflare 429 — انتظار {wait}s قبل المحاولة {attempt+2}")
                time.sleep(wait)
        
        # تأخير بسيط بين كل طلب
        if i > 0 and i % 100 == 0:
            time.sleep(0.1)  # 100ms كل 100 عنصر
```

### الأثر
بيانات المنتجات لا تُزامن مع Cloudflare Workers KV → قد تظهر بيانات قديمة في الـ Edge.

---

## BUG-013 🟡 — محاولة سحب من مستودع فارغ (مستمر)

### الوصف
محاولات سحب مخزون من مستودعَي `2000` و`الادويه` لمنتجات ليس لها رصيد.

### إحصائيات بعد 2026-02-25 12:53
- **26 خطأ** في `service_error.log`
- مستودع `2000`: منتجات متعددة (COIN, VELVET, WOLF, OKA, OSAKA, ...)
- مستودع `الادويه`: منتجات (ROCK, NEW TOKYO, NEW AMANDA, MOSHA, ...)

### السبب
منتجات يُحاول الكود خصمها من مستودعات لا تحتوي على رصيد لها.  
(تحليل مفصّل في BUG-013 من تقرير 2026-02-25)

---

## BUG-014 🟠 — Celery Worker يفشل عند الإقلاع (متكرر)

### الوصف
يفشل Celery Worker في البدء عند كل إعادة تشغيل.

### سجل الحوادث التراكمي
```
[2026-02-24 13:33:04] ❌ ERROR: فشل في تشغيل Celery Worker
[2026-02-25 12:10:19] ❌ ERROR: فشل في تشغيل Celery Worker
[2026-02-25 12:52:56] ❌ ERROR: فشل في تشغيل Celery Worker
```

### حالة الخدمة
Celery يعمل بشكل طبيعي بعد الإقلاع (لا أخطاء في `celery_worker.log` الحالي) — المشكلة في التشغيل الأولي فقط.

---

## حالة الخدمات العامة

| الخدمة | الحالة | ملاحظات |
|---------|--------|---------|
| Daphne (port 8000) | ✅ تعمل | آخر بدء 12:53:08 |
| pgBouncer (port 6432) | ✅ تعمل حالياً | كانت متوقفة لحظياً عند 12:50 |
| PostgreSQL | ✅ تعمل | لا أخطاء في postgres-monitor.log |
| Redis/Valkey | ✅ تعمل | |
| Celery Worker | ✅ تعمل | فشل الإقلاع — يعمل لاحقاً |
| Celery Beat | ✅ تعمل | |
| Cloudflare Tunnel | ✅ تعمل | مشكلة KV 429 — ليست انقطاعاً |
| DB Backup | ✅ نجح | |

---

## أولوية الإصلاح

| الأولوية | البق | الملف | التأثير |
|----------|------|-------|---------|
| 1 🔴 | BUG-017 | `cutting/inventory_integration.py:35` | خصم المخزون يفشل للعناصر الخارجية (15×/يوم) |
| 2 🟡 | BUG-019 | `public/cloudflare_sync.py` | مزامنة المنتجات ناقصة |
| 3 🟡 | BUG-018 | `systemd service` / `settings.py` | 500 أثناء إعادة التشغيل |
| 4 🟡 | BUG-013 | `inventory` بيانات + `inventory/signals.py:62` | إشعارات false-positive |
| 5 🟠 | BUG-014 | `manage.py` startup logic | Celery يفشل أول مرة |
