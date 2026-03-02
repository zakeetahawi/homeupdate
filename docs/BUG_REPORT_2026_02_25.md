# تقرير الأخطاء — 25 فبراير 2026
**النظام:** El-Khawaga ERP  
**الفترة:** 2026-02-24 (بعد إعادة التشغيل 13:33) — 2026-02-25 00:00  
**المُعِدّ:** فحص تلقائي للسجلات  
**الملفات المفحوصة:** `django.log`, `service_error.log`, `service.log`, `startup.log`, `cloudflared.log`, `postgres-monitor.log`, `db_backup.log`, `security.log`

---

## ملخص الأخطاء

| رقم  | الشدة    | العدد | الوصف                                               | الحالة   |
|------|----------|-------|-----------------------------------------------------|----------|
| BUG-011 | 🔴 حرج  | 117   | `deduct_inventory_for_cutting` — دالة غير موجودة   | مفتوح    |
| BUG-012 | 🟡 متوسط | 2     | `duplicate key` عند إنشاء `InstallationArchive`    | مفتوح    |
| BUG-013 | 🟡 متوسط | 32    | محاولة سحب من مستودع 2000 وهو فارغ                 | مفتوح    |
| BUG-014 | 🟠 تحذير | 1     | فشل تشغيل Celery Worker عند الإقلاع                | مفتوح    |
| BUG-015 | ℹ️ معلومة | 19+  | Cloudflare: connection refused أثناء إعادة التشغيل | مقبول    |
| BUG-016 | 🔵 منخفض | 1     | CSRF token غير صحيح في `/accounts/login/`          | مفتوح    |

---

## BUG-011 🔴 — `ImportError: deduct_inventory_for_cutting`

### الوصف
عند اكتمال أي عنصر تقطيع (`CuttingOrderItem.mark_as_completed`)، يحاول الكود استيراد دالة باسم `deduct_inventory_for_cutting` من `cutting.inventory_integration`، لكن هذه الدالة غير موجودة في الملف.

### السجل
```
ERROR cutting.models models.mark_as_completed:459 - خطأ في خصم المخزون للعنصر XXXXX:
cannot import name 'deduct_inventory_for_cutting' from 'cutting.inventory_integration'
(/home/zakee/homeupdate/cutting/inventory_integration.py)
```

### إحصائيات
- **117 خطأ** في `django.log`
- **117 خطأ** في `service_error.log`
- يحدث عند كل عملية إكمال تقطيع

### السبب الجذري
```python
# cutting/models.py — السطر 448 (خاطئ)
from .inventory_integration import deduct_inventory_for_cutting
transaction = deduct_inventory_for_cutting(self, user)
```

الدوال الموجودة فعلياً في `cutting/inventory_integration.py`:
```python
def complete_inventory_deduction(cutting_item, user):   # ← الاسم الصحيح
def reverse_inventory_deduction(cutting_item, user, reason="إلغاء التقطيع"):
def check_cutting_stock_availability(cutting_order):
```

### طريقة الإصلاح
**الملف:** `cutting/models.py`  
**السطر:** 448-450

```python
# قبل الإصلاح (خاطئ)
from .inventory_integration import deduct_inventory_for_cutting
# ...
transaction = deduct_inventory_for_cutting(self, user)

# بعد الإصلاح (صحيح)
from .inventory_integration import complete_inventory_deduction
# ...
transaction = complete_inventory_deduction(self, user)
```

### الأثر
خصم المخزون لا يحدث عند اكتمال التقطيع → المخزون لا يتناقص → بيانات مخزونية غير دقيقة.

---

## BUG-012 🟡 — `IntegrityError: duplicate key — InstallationArchive`

### الوصف
عند تحديث حالة تركيب إلى `modification_completed`، يحاول الكود إنشاء سجل `InstallationArchive` جديد دون التحقق من وجوده مسبقاً، مما يتسبب في انتهاك قيد `unique`.

### السجل
```
ERROR - خطأ في إنشاء أرشيف التعديل: duplicate key value violates unique constraint
"installations_installationarchive_installation_id_key"
DETAIL:  Key (installation_id)=(16088) already exists.
```

### إحصائيات
- **2 خطأ** في `service_error.log`
- التركيب المتأثر: `installation_id=16088`

### السبب الجذري
```python
# installations/models.py — السطر 590 (خاطئ)
InstallationArchive.objects.create(
    installation=self,
    archive_notes=f'تم إكمال التعديل...',
)
```

يستخدم `.create()` مباشرة بينما يستخدم Signal في `installations/signals.py:28` الطريقة الصحيحة:
```python
archive, created = InstallationArchive.objects.get_or_create(installation=installation)
```

### طريقة الإصلاح
**الملف:** `installations/models.py`  
**السطر:** 590

```python
# قبل الإصلاح
InstallationArchive.objects.create(
    installation=self,
    archive_notes=f'...',
)

# بعد الإصلاح
archive, created = InstallationArchive.objects.get_or_create(
    installation=self,
    defaults={'archive_notes': f'تم إكمال التعديل مع تركيب مكتمل - {self.notes or ""}'},
)
if not created:
    # تحديث الملاحظات للأرشيف الموجود
    archive.archive_notes = f'تم إكمال التعديل مع تركيب مكتمل - {self.notes or ""}'
    archive.save(update_fields=['archive_notes'])
```

### الأثر
الخطأ يُلتقط بـ `except Exception` ولا يوقف الحفظ، لكنه يُولّد ضجيجاً في السجلات.

---

## BUG-013 🟡 — محاولة سحب من مستودع 2000 وهو فارغ

### الوصف
يحاول النظام سحب كميات من المستودع رقم `2000` لكنه يكتشف أن المخزون غير كافٍ أو غير موجود.

### السجل
```
ERROR inventory.signals signals.stock_manager_handler:62 - ❌ محاولة سحب من مستودع فارغ!
المنتج: COIN-2/C BEIGE (10100302100) المستودع: 2000 الكمية: 2.000
```

### إحصائيات  
- **32 خطأ** في `service_error.log`  
- منتجات متعددة تتكرر: KOYA/C1, COIN-2/C BEIGE, ELANTRA, BERLIN, NEW TOKYO, WOLF, ...  
- أكبر كمية: `KOYA/C1` — 180 متر

### السبب الجذري
إما:
1. مستودع `2000` لا يحتوي على مخزون كافٍ لهذه المنتجات (مشكلة بيانات)
2. أو الكود يوجّه الكميات للمستودع الخاطئ

### طريقة الإصلاح
**أ. التحقق من البيانات:**
```bash
python manage.py shell -c "
from inventory.models import Stock
from django.db.models import Sum
print(Stock.objects.filter(warehouse_id=2000).values('product__name','product__code','quantity')[:20])
"
```

**ب. إضافة فحص قبل السحب في `inventory/signals.py` السطر 62:**
```python
# إرسال تنبيه بدلاً من إيقاف العملية
if warehouse.quantity < quantity:
    notify_stock_shortage(product, warehouse, quantity)
    logger.warning(f"⚠️ مخزون غير كافٍ: {product.name} — متوفر: {warehouse.quantity}, مطلوب: {quantity}")
    return  # أو التعامل مع المخزون السالب حسب السياسة
```

**ج. تحديث المخزون إذا كان المستودع 2000 هو مستودع المصنع:**
```bash
python manage.py shell -c "
from inventory.models import Warehouse
print(Warehouse.objects.get(id=2000))
"
```

### الأثر
المخزون لا يُخصم من مستودع 2000 → بيانات مخزونية غير متزامنة.

---

## BUG-014 🟠 — فشل تشغيل Celery Worker عند الإقلاع

### الوصف
عند إعادة تشغيل الخدمة، فشل Celery Worker في البدء للمرة الأولى.

### السجل
```
[2026-02-24 13:33:04] ❌ ERROR: فشل في تشغيل Celery Worker
```

### إحصائيات
- **1 مرة** في `startup.log`
- الخدمة عادت للعمل الطبيعي بعد ذلك (Celery يعمل بشكل طبيعي)

### السبب المحتمل
- `manage.py` يُشغّل Celery Worker لكنه قد يحاول قبل أن يكون Redis/Valkey جاهزاً

### طريقة الإصلاح
**الملف:** `manage.py` (منطق تشغيل Celery)

```python
# إضافة retry عند فشل التشغيل
import time

def start_celery_worker():
    for attempt in range(3):
        try:
            # تشغيل Celery
            subprocess.Popen([...])
            return True
        except Exception as e:
            logger.warning(f"محاولة {attempt+1}/3 لتشغيل Celery فشلت: {e}")
            time.sleep(3)
    logger.error("❌ فشل تشغيل Celery Worker بعد 3 محاولات")
    return False
```

---

## BUG-015 ℹ️ — Cloudflare: connection refused أثناء إعادة التشغيل

### الوصف
طلبات خارجية وصلت عبر Cloudflare Tunnel أثناء فترة قصيرة كانت فيها Daphne لا تزال تُقلع.

### السجل
```
2026-02-24T11:30:20Z ERR error="Unable to reach the origin service...
dial tcp 127.0.0.1:8000: connect: connection refused"
```

### إحصائيات
- **~19 طلب** في فترة أقل من دقيقة واحدة (11:30:20 — 11:30:21)
- الخدمة عادت للعمل في 13:33:16

### السبب
فجوة زمنية بين إيقاف وإعادة تشغيل Daphne (نحو 3 ساعات). Cloudflare Tunnel مستمر في استقبال الطلبات بينما المنفذ 8000 مُغلق.

### ملاحظة
هذا سلوك طبيعي ومتوقع أثناء إعادة التشغيل. للتخفيف:
- تفعيل **Health Check** في Cloudflare Zero Trust
- أو استخدام **maintenance page** من Cloudflare

---

## BUG-016 🔵 — CSRF Token Mismatch في صفحة تسجيل الدخول

### الوصف
طلب واحد إلى `/accounts/login/` رُفض بسبب CSRF token غير صحيح.

### السجل
```
[SECURITY] 2026-02-24 23:05:52 | WARNING | Forbidden (CSRF token from POST incorrect.): /accounts/login/
```

### إحصائيات
- **1 مرة فقط** في `security.log`

### الأسباب المحتملة
1. المستخدم فتح نموذج تسجيل الدخول ثم تُجدّد الجلسة
2. الطلب جاء بعد انتهاء صلاحية الكوكيز
3. مشكلة في تعامل middleware مع طلبات Cloudflare

### طريقة الإصلاح
- لا يستوجب إصلاحاً (تكرار واحد)
- للمراقبة: إذا زاد التكرار، يجب التحقق من `CSRF_TRUSTED_ORIGINS` في `crm/settings.py`

---

## أحداث أمنية (ليست أخطاء)

| الوقت | الحدث | التفاصيل |
|-------|-------|----------|
| 14:47:23 | `wrong_branch` × 4 | مستخدم حاول تسجيل الدخول من جهاز فرع مختلف |
| 15:35:02 | `device_not_registered` × 2 | محاولة دخول من جهاز غير مسجّل |

**ملاحظة:** نظام حماية الأجهزة يعمل بشكل صحيح ✅

---

## حالة الخدمات

| الخدمة | الحالة | ملاحظات |
|---------|--------|---------|
| Daphne (port 8000) | ✅ تعمل | بدأت 13:33:16 |
| Redis/Valkey | ✅ تعمل | |
| Celery Worker | ✅ تعمل | فشل مرة واحدة عند الإقلاع — BUG-014 |
| Celery Beat | ✅ تعمل | |
| PostgreSQL | ✅ تعمل | لا أخطاء في postgres-monitor.log |
| pgBouncer | ✅ تعمل | |
| Cloudflare Tunnel | ✅ تعمل | 19 خطأ أثناء إعادة التشغيل فقط |
| DB Backup | ✅ نجح | `backup-20260224_133315.sql.gz` |

---

## أولوية الإصلاح

1. **🔴 فوري — BUG-011**: إصلاح `deduct_inventory_for_cutting` → `complete_inventory_deduction` في `cutting/models.py:448`
2. **🟡 قريباً — BUG-013**: التحقق من بيانات مستودع 2000 وإضافة مخزون للمنتجات الناقصة
3. **🟡 قريباً — BUG-012**: تغيير `.create()` → `.get_or_create()` في `installations/models.py:590`
4. **🟠 عند الفرصة — BUG-014**: تحسين منطق retry لـ Celery في `manage.py`
