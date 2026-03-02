# 📋 تقرير فحص السجلات الشامل - نظام الخواجة ERP
**التاريخ:** 2 مارس 2026  
**الفترة المفحوصة:** 28 فبراير - 2 مارس 2026  
**المُعد بواسطة:** GitHub Copilot - تحليل آلي  

---

## 📊 ملخص تنفيذي

| المقياس | القيمة |
|---------|--------|
| إجمالي الأخطاء (ERROR) | 30 خطأ |
| إجمالي التحذيرات (WARNING) | 330+ تحذير |
| حالة الخدمة الرئيسية | ✅ تعمل (منذ 28 فبراير) |
| حالة قاعدة البيانات | ✅ PostgreSQL سليمة |
| حالة Valkey/Redis | ✅ تعمل بدون أخطاء |
| حالة Cloudflare Tunnel | ⚠️ انقطاعات متقطعة |
| استهلاك الذاكرة | 1.6 GB (من 15 GB) |
| مساحة القرص | 14% مستخدم (63 GB من 460 GB) |

---

## 🔴 الأخطاء الحرجة (Critical Errors)

### 1. مشكلة إيقاف الخدمة - Timeout عند Stop (خطورة: عالية)

**الوصف:**  
كل عملية إيقاف للخدمة تفشل بـ timeout بعد 60 ثانية، مما يضطر systemd لإرسال SIGKILL.

**الأدلة من السجلات:**
```
homeupdate.service: State 'stop-sigterm' timed out. Killing.
homeupdate.service: Killing process XXXX (db-backup.sh) with signal SIGKILL.
homeupdate.service: Killing process XXXXX (sleep) with signal SIGKILL.
homeupdate.service: Failed with result 'timeout'.
```

**السبب الجذري:**  
سكريبت `db-backup.sh` يستخدم حلقة `sleep 3600` (ساعة كاملة) للنسخ الاحتياطي الدوري. عند إرسال SIGTERM، العملية `sleep` لا تستجيب للإشارة حتى ينتهي وقت النوم، وبما أن `TimeoutStopSec=60` في ملف الخدمة، يتم القتل القسري.

**التأثير:**
- ⚠️ قد يؤدي لفقدان بيانات نسخ احتياطي غير مكتملة
- ⚠️ إغلاق غير نظيف لـ Celery Workers قد يفقد مهام قيد التنفيذ
- ⚠️ كل إعادة تشغيل تُسجل كـ "Failed" في systemd

**الإصلاح المقترح:**
```bash
# في db-backup.sh - استبدال sleep بحلقة قصيرة تستجيب للإشارات
# بدلاً من:
sleep 3600

# استخدم:
for i in $(seq 1 360); do
    sleep 10
    # التحقق من إشارة الإيقاف
    if [ ! -f "$PIDS_DIR/db_backup.pid" ]; then
        exit 0
    fi
done
```

أو إضافة trap في `db-backup.sh`:
```bash
trap 'echo "Received stop signal"; exit 0' SIGTERM SIGINT
```

وزيادة `TimeoutStopSec` في ملف الخدمة:
```ini
TimeoutStopSec=90
```

---

### 2. محاولات سحب من مستودعات فارغة (خطورة: عالية)

**الوصف:**  
26 خطأ في سحب منتجات من مستودع "الادويه" بكميات كبيرة رغم عدم توفر رصيد.

**الأدلة:**
```
❌ محاولة سحب من مستودع فارغ! المنتج: SHADOW /C16 (10100303519) المستودع: الادويه الكمية: 40.000
❌ محاولة سحب من مستودع فارغ! المنتج: KOYA/C1 (10100300340) المستودع: الادويه الكمية: 35.000
❌ محاولة سحب من مستودع فارغ! المنتج: VIGO /C2 (10100303528) المستودع: الادويه الكمية: 30.000
❌ رصيد غير كافٍ! المنتج: ONTARIO-280/C BLUE المستودع: الادويه الرصيد المتاح: 0.00 الكمية المطلوبة: 4.000
```

**المنتجات المتأثرة (عينة):**

| المنتج | الكمية المطلوبة | الطلب |
|--------|-----------------|-------|
| SHADOW /C16 | 40.000 | 10-1009-0003 |
| KOYA/C1 | 35.000 | 13-0892-0039 |
| ZARA /C1 | 30.000 | 9-1320-0009 |
| VIGO /C2 | 30.000 | 12-0890-0002 |
| KOYA-STOCK/C1 | 30.000 | 10-1923-0002 |
| SOHO/C9 | 20.000 | 9-1008-0012 |
| ATX/C1 | 15.000 | 9-1000-0004 |
| ROCK/C22 | 14.000 | 3-0669-0002 |
| NEW AMANDA/C16 | 10.500 | 13-1241-0001 |

**التأثير:**
- ⛔ أرصدة المخزون غير دقيقة — قد تكون سالبة
- ⛔ طلبات تمت بدون توفر فعلي للمنتج
- ⛔ التقارير المالية والمخزنية ستكون غير صحيحة

**الإصلاح المقترح:**
1. تشغيل أمر تسوية المخزون:
   ```bash
   python manage.py verify_customer_balances --fix
   ```
2. إضافة validation في الـ signal لمنع الخصم من مستودع فارغ:
   ```python
   # في inventory/signals.py - stock_manager_handler
   if warehouse_stock.available_quantity < required_quantity:
       # إنشاء طلب نقل تلقائي أو تنبيه بدلاً من السحب
       create_transfer_request(product, warehouse, required_quantity)
       return  # لا تسحب من رصيد صفري
   ```
3. مراجعة أرصدة مستودع "الادويه" يدوياً وتحديثها

---

### 3. خطأ تكرار مفتاح الطلب المسودة (خطورة: متوسطة-عالية)

**الوصف:**  
خطأ `unique_draft_order_sequence` عند إضافة ستارة لطلب.

**الأدلة:**
```
ERROR orders.wizard_views wizard_add_curtain:2719 - Error adding curtain: 
duplicate key value violates unique constraint "unique_draft_order_sequence"
```

**التأثير:**
- ⚠️ فشل في إضافة عناصر للطلب
- ⚠️ تجربة مستخدم سيئة — الخطأ يظهر بشكل 500 Internal Server Error

**الإصلاح المقترح:**
```python
# في orders/wizard_views.py - wizard_add_curtain
# إضافة معالجة لحالة التكرار
from django.db import IntegrityError

try:
    # كود إضافة الستارة الحالي
    order_item.save()
except IntegrityError:
    # إعادة حساب sequence_number
    max_seq = OrderItem.objects.filter(
        order=order
    ).aggregate(Max('sequence_number'))['sequence_number__max'] or 0
    order_item.sequence_number = max_seq + 1
    order_item.save()
```

---

### 4. خطأ تغيير العميل بعد إنشاء الطلب (خطورة: متوسطة)

**الوصف:**  
6 محاولات متكررة لتغيير العميل في الطلب `15-0515-0002` بعد إنشائه.

**الأدلة:**
```
ERROR orders.models save:736 - خطأ في حفظ الطلب 15-0515-0002: 
['لا يمكن تغيير العميل بعد إنشاء الطلب. رقم الطلب مرتبط بالعميل الأصلي.']
```

**التأثير:**
- ⚠️ المستخدم حاول 6 مرات → تجربة مستخدم محبطة
- ⚠️ 6 طلبات Internal Server Error متتالية

**الإصلاح المقترح:**
1. إضافة validation في الـ frontend (JavaScript) قبل إرسال الطلب
2. عرض رسالة خطأ واضحة للمستخدم بدون إرسال الطلب للسيرفر
3. في `wizard_finalize` — التقاط `ValidationError` وإرجاع رسالة JSON مفهومة:
   ```python
   except ValidationError as e:
       return JsonResponse({
           'success': False,
           'message': str(e.messages[0]),
           'error_type': 'customer_change_not_allowed'
       }, status=400)  # 400 بدلاً من 500
   ```

---

## 🟡 التحذيرات المهمة (Warnings)

### 5. خطوط WeasyPrint غير محملة (خطورة: منخفضة-متوسطة)

**الوصف:**  
214 تحذير "Font-face 'Noto Naskh Arabic' cannot be loaded" رغم أن الخط **مثبت فعلياً** على النظام.

**الأدلة:**
```
WARNING weasyprint fonts.add_font_face:250 - Font-face 'Noto Naskh Arabic' cannot be loaded
```
الخط موجود في: `/usr/share/fonts/noto/NotoNaskhArabic-*.ttf`

**السبب الجذري:**  
WeasyPrint يبحث عن الخط بصيغة/مسار مختلف عن المثبت في النظام. غالباً المشكلة في تعريف `@font-face` في CSS.

**التأثير:**
- ⚠️ تقارير PDF قد تظهر بخط بديل غير مثالي
- ⚠️ تشويش في السجلات (214 تحذير يخفي أخطاء حقيقية)

**الإصلاح المقترح:**
```bash
# 1. إعادة بناء cache الخطوط
sudo fc-cache -fv

# 2. في إعدادات WeasyPrint/CSS
# التأكد من أن @font-face يشير للمسار الصحيح
@font-face {
    font-family: 'Noto Naskh Arabic';
    src: url('/usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf') format('truetype');
}
```

---

### 6. عدم تقديم Device Token عند تسجيل الدخول (خطورة: منخفضة)

**الوصف:**  
47 تحذير "No device token provided" عند تسجيل دخول مستخدمين.

**التأثير:**
- ⚠️ إشعارات الدفع (Push Notifications) لن تعمل لهؤلاء المستخدمين
- ℹ️ طبيعي للمتصفحات التي لا تدعم الإشعارات

**الإصلاح المقترح:**
- تقليل مستوى السجل من WARNING إلى DEBUG لأنه سلوك متوقع:
```python
# في accounts/views.py - login_view
logger.debug(f"⚠️ No device token provided")  # بدلاً من warning
```

---

### 7. أخطاء CSRF Token (خطورة: متوسطة)

**الوصف:**  
5 حالات فشل CSRF للمستخدمين: `magdy.alham`, `hossam.sobhy`, `yousef.lamey`

**الأدلة:**
```
CSRF failure for user magdy.alham from IP 127.0.0.1: CSRF token from POST incorrect.
CSRF failure for user yousef.lamey from IP 127.0.0.1: CSRF token from POST incorrect.
```

**السبب المحتمل:**  
- جلسة منتهية الصلاحية والمستخدم يحاول إرسال نموذج
- تبويبات متعددة مفتوحة في نفس الوقت

**الإصلاح المقترح:**
- إضافة JavaScript لاكتشاف انتهاء الجلسة وتحويل المستخدم لتسجيل الدخول:
```javascript
// في base.html
document.addEventListener('submit', function(e) {
    // التحقق من صلاحية الجلسة قبل الإرسال
    fetch('/accounts/check-session/', {method: 'HEAD'})
        .then(r => { if (r.status === 401) window.location = '/accounts/login/'; });
});
```

---

### 8. نقص في المخزون لطلبات متعددة (خطورة: عالية - تشغيلية)

**الوصف:**  
16 تحذير بنقص المخزون مع إجمالي كميات كبيرة.

**الطلبات المتأثرة:**

| الطلب | النقص (متر) |
|-------|------------|
| 10-1009-0003 | 56.000 |
| 13-0892-0039 | 42.000 |
| 10-1926-0001 | 20.000 |
| 10-1923-0002 | 30.000 |
| 12-0890-0002 | 30.000 |
| 9-1320-0009 | 30.000 |
| 9-1008-0012 | 20.000 |

**التأثير:**
- ⛔ طلبات تم تأكيدها بدون رصيد كافٍ
- ⛔ احتمال تأخير التسليم للعملاء

---

## 🔵 حالة الخدمات

### خدمة homeupdate.service
| البند | الحالة |
|-------|--------|
| الحالة | ✅ active (running) |
| آخر بدء | 28 فبراير 17:39 |
| المهام | 62 task |
| الذاكرة | 1.6 GB (peak: 1.7 GB) |
| CPU | 50 دقيقة إجمالي |
| مشكلة الإيقاف | 🔴 timeout في كل مرة |

### خدمة Valkey (Redis)
| البند | الحالة |
|-------|--------|
| الحالة | ✅ active (running) |
| أخطاء | لا توجد |

### PostgreSQL
| البند | الحالة |
|-------|--------|
| الحالة | ✅ accepting connections |
| مراقبة | كل دقيقة - OK |

### pgBouncer
| البند | الحالة |
|-------|--------|
| الحالة | 🔴 غير مثبت |
| تأثير | تحذير عند كل بدء تشغيل |

### Cloudflare Tunnel
| البند | الحالة |
|-------|--------|
| الحالة | ⚠️ يعمل مع انقطاعات |
| آخر أخطاء | طلبات بحث المنتجات تنتهي بـ context canceled |
| فترة الانقطاع | 1 مارس ~10:42-10:48 UTC |

### Celery
| البند | الحالة |
|-------|--------|
| Worker | ✅ يعمل (solo pool, 1 concurrency) |
| Beat | ✅ يعمل |
| سجلات أخطاء | فارغة ✅ |

---

## 🔧 ملخص أولويات الإصلاح

### أولوية 1 — عاجل (يؤثر على البيانات)
| # | المشكلة | الملف | الإصلاح |
|---|---------|-------|---------|
| 1 | سحب من مستودعات فارغة | `inventory/signals.py` | إضافة validation قبل السحب + تسوية المخزون |
| 2 | نقص مخزون كبير | تشغيلي | مراجعة أرصدة مستودع "الادويه" فوراً |

### أولوية 2 — مهم (يؤثر على الاستقرار)
| # | المشكلة | الملف | الإصلاح |
|---|---------|-------|---------|
| 3 | timeout عند إيقاف الخدمة | `لينكس/db-backup.sh` + `homeupdate.service` | trap + sleep قصير |
| 4 | تكرار مفتاح الطلب | `orders/wizard_views.py` | معالجة IntegrityError |
| 5 | خطأ تغيير العميل يظهر كـ 500 | `orders/wizard_views.py` | إرجاع 400 مع رسالة واضحة |

### أولوية 3 — تحسينات
| # | المشكلة | الملف | الإصلاح |
|---|---------|-------|---------|
| 6 | تحذيرات خطوط WeasyPrint | CSS + نظام | `fc-cache -fv` + تصحيح مسار الخط |
| 7 | تحذيرات Device Token | `accounts/views.py` | تخفيض مستوى السجل |
| 8 | pgBouncer غير مثبت | النظام | تثبيت أو إزالة التحقق من السكريبت |
| 9 | أخطاء CSRF | Frontend | إضافة فحص الجلسة |

### أولوية 4 — Cloudflare Tunnel
| # | المشكلة | الملف | الإصلاح |
|---|---------|-------|---------|
| 10 | طلبات بحث المنتجات تنقطع | البنية التحتية | فحص أداء API البحث وزيادة timeout |

---

## 📈 إحصائيات السجلات

| ملف السجل | الحجم | عدد الأسطر | ملاحظات |
|-----------|-------|-----------|---------|
| `django.log` | 2.1 MB | 13,335 | الأخطاء الرئيسية |
| `daphne_access.log` | 15 MB | 149,012 | سجلات الوصول |
| `service.log` | 3.8 MB | 92,909 | معظمها DEBUG |
| `service_error.log` | 1.4 MB | 12,075 | أخطاء الخدمة |
| `cloudflared.log` | 204 KB | 1,218 | انقطاعات |
| `startup.log` | 423 KB | 7,560 | بدء التشغيل |
| `postgres-monitor.log` | 177 KB | 2,765 | كلها OK ✅ |
| `security.log` | 545 B | 5 | CSRF فقط |
| `celery_worker.log` | 0 B | 0 | فارغ ✅ |
| `celery_beat.log` | 0 B | 0 | فارغ ✅ |
| `attacks.log` | 0 B | 0 | لا هجمات ✅ |
| `performance.log` | 0 B | 0 | معطل |
| `slow_queries.log` | 0 B | 0 | لا استعلامات بطيئة ✅ |

---

## 🔐 حالة الأمان

- **محاولات تسجيل دخول فاشلة (Axes):** 614 سجل (من بداية التشغيل — يشمل جلسات منتهية)
- **هجمات:** لا توجد (ملف فارغ ✅)
- **CSRF failures:** 5 حالات (سلوك طبيعي — جلسات منتهية)
- **حالة django-axes:** ✅ يعمل ويسجل المحاولات

---

## 💡 توصيات إضافية

1. **تنظيف السجلات:** `service.log` يكتب DEBUG في الإنتاج — تقليل مستوى السجل
2. **log rotation:** إضافة logrotate لملفات السجلات الكبيرة (daphne_access.log = 15 MB)
3. **مراقبة المخزون:** إضافة تنبيهات تلقائية عند وصول رصيد منتج لـ 0
4. **pgBouncer:** إما تثبيته أو إزالة التحقق منه في `start-service.sh`
5. **Celery concurrency:** المعالج الحالي `--pool=solo --concurrency=1` — يمكن زيادته مع الذاكرة المتاحة (11 GB فارغة)

---

*تم إنشاء هذا التقرير تلقائياً بواسطة تحليل سجلات النظام في 2 مارس 2026*
