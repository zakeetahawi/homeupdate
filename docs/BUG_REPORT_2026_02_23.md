# تقرير الأخطاء اليومي - 23 فبراير 2026
**الفترة:** 2026-02-22 09:00 → 2026-02-23 09:53  
**المصادر:** `django.log` · `service_error.log` · `service.log` · `cloudflared.log` · `startup.log` · `security.log` · `error.log` · `db_backup.log`

---

## 🔴 أخطاء حرجة (Priority 1)

### BUG-006: SyntaxError في cutting/inventory_integration.py السطر 321

**النوع:** `SyntaxError` — يُخفَت تلقائياً بـ try/except في النموذج، لكنه يمنع خصم المخزون كلياً عند إكمال أوامر التقطيع

**الخطأ:**
```
ERROR cutting.models models.mark_as_completed:459
خطأ في خصم المخزون للعنصر 17826: expected 'except' or 'finally' block
خطأ في خصم المخزون للعنصر 17827: expected 'except' or 'finally' block
خطأ في خصم المخزون للعنصر 17828: expected 'except' or 'finally' block
خطأ في خصم المخزون للعنصر 17829: expected 'except' or 'finally' block
خطأ في خصم المخزون للعنصر 14028: expected 'except' or 'finally' block
خطأ في خصم المخزون للعنصر 17853: expected 'except' or 'finally' block
```

**العناصر المتأثرة:** 6 عناصر تقطيع لم يُخصَم مخزونها  
**التأثير:** أوامر التقطيع تُكتمل دون خصم فعلي من المخزون → تضارب في أرصدة المخزون

**السبب الجذري:**  
في `cutting/inventory_integration.py`، الدالة `_send_stock_shortage_notification` تحتوي على `try:` بدون `except` أو `finally`. بعدها يوجد سطران مُعزولان (orphaned) يُفترض أنهما جسم دالة `complete_inventory_deduction` لكن سطر `def` مفقود:

```python
# السطر 295-321 — try بدون except
@staticmethod
def _send_stock_shortage_notification(...):
    try:
        ...
        notification.visible_to.add(order_creator)    # السطر ~321 — ينتهي هنا بدون except/finally

# السطران المُعزولان OUTSIDE الكلاس (السطر 322-323):
"""دالة مساعدة لخصم المخزون عند إكمال التقطيع"""   # ← الـ docstring موجود
return InventoryIntegrationService.process_cutting_completion(...)  # ← لكن الـ def مفقود!
```

**الإصلاح المطلوب (`cutting/inventory_integration.py`):**

1. إضافة `except Exception as e` لإغلاق `try` block في `_send_stock_shortage_notification` (السطر ~321):
```python
        notification.visible_to.add(order_creator)
        except Exception as e:                          # ← أضف هذا
            logger.error(f"خطأ في إرسال إشعار نقص المخزون: {str(e)}")
```

2. إضافة سطر `def` المفقود (السطر ~322):
```python
# قبل الإصلاح:
    """دالة مساعدة لخصم المخزون عند إكمال التقطيع"""
    return InventoryIntegrationService.process_cutting_completion(...)

# بعد الإصلاح:
def complete_inventory_deduction(cutting_item, user):    # ← أضف هذا السطر
    """دالة مساعدة لخصم المخزون عند إكمال التقطيع"""
    return InventoryIntegrationService.process_cutting_completion(cutting_item, user)
```

---

### BUG-003 (مستمر): WeasyPrint لا يزال لا يُحمّل خط Noto Naskh Arabic

**الخطأ (يتكرر في كل توليد PDF):**
```
WARNING weasyprint descriptors.preprocess_descriptors:62
Ignored `src: url("/usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf")
format("truetype")` at 6:17, Relative URI reference without a base URI: None.

WARNING weasyprint __init__.preprocess_stylesheet:1601
Missing src descriptor in '@font-face' rule at 2:13

WARNING weasyprint fonts.add_font_face:250
Font-face 'Noto Naskh Arabic' cannot be loaded
```

**الأوامر المتأثرة:** طلبات 10-1881-0002، 13-1228-0001، 15-0514-0002، 7-0999-0002، 7-1613-0001، 3-0565-0006 وغيرها

**السبب:** الإصلاح السابق (BUG-003 كوميت ca17376) استخدم المسار `/usr/share/fonts/...` بدلاً من `file:///usr/share/fonts/...`. WeasyPrint لا يستطيع تحليل المسار النسبي بدون `base_url` صحيح

**الإصلاح في `orders/services/contract_generation_service.py`:**

```python
# قبل الإصلاح — مسار نسبي لا يعمل:
src: url("/usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf") format("truetype")

# بعد الإصلاح — مسار مطلق بـ file:// scheme:
src: url("file:///usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf") format("truetype")
```

يجب تطبيق هذا على الـ 3 variants: Regular, Bold, Medium

---

## 🟠 مشاكل مهمة (Priority 2)

### BUG-007: محاولة سحب من مستودع رقم 2000 الفارغ — 6 حالات

**الخطأ:**
```
ERROR inventory.signals signals.stock_manager_handler:62
❌ محاولة سحب من مستودع فارغ! المنتج: MOSHA PD/C18 (10100303369)  المستودع: 2000 الكمية: 10.000
❌ محاولة سحب من مستودع فارغ! المنتج: dona/C STEEL 1989 (10100300247) المستودع: 2000 الكمية: 70.000
❌ محاولة سحب من مستودع فارغ! المنتج: dona/C BLACK 261 (10100300210)  المستودع: 2000 الكمية: 7.000
❌ محاولة سحب من مستودع فارغ! المنتج: dona/C LAVORY (10100300226)    المستودع: 2000 الكمية: 14.000
❌ محاولة سحب من مستودع فارغ! المنتج: MZ-900-3 OFFWHITE (20100100339) المستودع: 2000 الكمية: 3.000
❌ محاولة سحب من مستودع فارغ! المنتج: MZ-900-1 OFFWHITE (20100100337) المستودع: 2000 الكمية: 3.000
```

**الطلبات المتأثرة:** 7-1613-0001، 3-0565-0006، 10-1142-0003، 7-1617-0001  
**التأثير:** المنتجات المذكورة لا يُخصَم مخزونها رغم أن الطلب يُكتمل بشكل طبيعي

**السبب المحتمل:** المنتجات محددة على مستودع برقم 2000 الذي لا يحتوي على مخزون أو يحتوي على رصيد صفر. يحتاج مراجعة تعيين مستودعات هذه المنتجات.

**الإجراء المطلوب:**
- مراجعة إعداد المستودع الافتراضي لهذه المنتجات
- أو تغيير منطق `_get_warehouse_for_cutting` ليبحث عن أقرب مستودع يحتوي على مخزون كافٍ

---

### BUG-008: خطأ AuditLog مع Anonymous User

**الخطأ:**
```
ERROR core.audit audit.log:142
خطأ في تسجيل سجل التدقيق:
Cannot assign "<django.contrib.auth.models.AnonymousUser object at ...>":
"AuditLog.user" must be a "User" instance.
```

**وقوعه:** 2026-02-22 13:51:46 — بعد تسجيل خروج `ahmad.zain` (جهاز غير مسجل)

**السبب:** `core.audit` يحاول تسجيل عملية للـ `AnonymousUser` بدون التحقق مما إذا كان `request.user.is_authenticated`

**الإصلاح في `core/audit.py` السطر ~142:**
```python
# قبل الإصلاح:
AuditLog.objects.create(user=request.user, ...)

# بعد الإصلاح:
if request.user and request.user.is_authenticated:
    AuditLog.objects.create(user=request.user, ...)
else:
    logger.debug("تخطي تسجيل التدقيق للمستخدم غير الموثق")
```

---

## 🟡 مشاكل الخدمة والتشغيل (Priority 3)

### BUG-009: انقطاع الخدمة 3 دقائق أثناء الـ Deploy

**التوقيت:** 2026-02-22 09:18 — 09:21  
**السجل (cloudflared.log):**
```
ERR Unable to reach the origin service.
dial tcp 127.0.0.1:8000: connect: connection refused
→ /orders/wizard/step/1/
→ /ws/chat/
→ /notifications/ajax/
→ /complaints/api/
```

**الملاحظة:** هذا متوقع أثناء إعادة تشغيل الخدمة، لكن 3 دقائق وقت طويل. يُفضَّل تطبيق zero-downtime deploy.

---

### إشعار: فشل تشغيل Celery Worker (مرة واحدة)

**السجل (`error.log` و `startup.log`):**
```
[2026-02-22 11:21:41] ❌ ERROR: فشل في تشغيل Celery Worker
```

**الملاحظة:** الـ Worker يعمل حالياً. المشكلة في فترة انتظار الـ health-check في `start-service.sh` (BUG-007 من التقرير السابق، لم يُعالج بعد)

---

## 🔵 الأمان والمراقبة (Priority 4)

### حوادث تسجيل الدخول المشبوهة

| الوقت | المستخدم | السبب | IP |
|-------|---------|-------|-----|
| 13:05 | `ishak.abdelnour` | جهاز غير مسجل | — |
| 13:06 | `ishak.abdelnour` | جهاز غير مسجل | — |
| 13:17 | — | — | — |
| 13:51 | `ahmad.zain` | جهاز غير مسجل | — |
| 13:56 | `mohamed.fahmi` | اسم مستخدم خاطئ | 156.204.160.50 |
| 13:57 | `mohamed.fahmi` | اسم مستخدم خاطئ | 156.204.160.50 |
| 17:16 | — | لا token | — |
| 18:40 | — | لا token | — |
| 01:00 | `housam.hassan` | جهاز غير مسجل | — |

**ملاحظات:**
- `ishak.abdelnour` و `ahmad.zain` و `housam.hassan`: مستخدمون حقيقيون يحاولون من أجهزة غير مسجلة — يحتاجون تسجيل أجهزتهم
- `mohamed.fahmi`: اسم خاطئ من IP خارجي — مراقبة AXES مفعّلة وتعمل
- IP `156.204.160.50`: مشبوه، جاري blocking بواسطة AXES

### CSRF Failures

```
[SECURITY] 2026-02-22 14:06:54 — Iman — CSRF token from POST incorrect
[SECURITY] 2026-02-22 18:40:06 — emil.yousef × 3
[SECURITY] 2026-02-22 23:34:35 — ?
```

**5 حالات** — الأرجح جلسات مؤقتة منتهية الصلاحية (cache بعد deploying)

---

### أخطاء Cloudflare التشغيلية

| النوع | العدد | الحالة |
|-------|-------|--------|
| connection refused (أثناء deploy) | ~20 | ✅ طبيعي |
| DNS timeout `region1.v2.argotunnel` | 2 | ⚠️ متكرر |
| context canceled (WebSocket /ws/chat/) | 3 | ⚠️ مراقبة |
| context canceled (Product search) | 2 | ℹ️ المستخدم ألغى |

---

## 📊 حالة الخدمات - 23 فبراير 2026

| الخدمة | الحالة |
|--------|--------|
| Daphne (ASGI) | ✅ يعمل |
| Celery Worker | ✅ يعمل |
| Celery Beat | ✅ يعمل |
| Valkey/Redis | ✅ يعمل |
| PostgreSQL | ✅ يعمل |
| pgBouncer | ✅ يعمل |
| Cloudflare Tunnel | ✅ يعمل |
| جميع الهجرات | ✅ مطبّقة |
| النسخ الاحتياطية | ✅ backup-20260222_112151 |

---

## ✅ إصلاحات الكوميت السابق (ca17376) — حالة التحقق

| Bug | الوصف | الحالة |
|-----|-------|--------|
| BUG-001 | UnboundLocalError في wizard_views.py:1237 | ✅ مُصلَح ومؤكَّد |
| BUG-002 | هجرة installation_accounting 0004 | ✅ مطبّقة |
| BUG-003 | Noto Naskh Arabic font WeasyPrint | ❌ **لا يزال يفشل** (يحتاج file:/// prefix) |
| BUG-004 | Celery task على طلب محذوف | ✅ transaction.on_commit مُطبَّق |
| BUG-005 | CSS غير مدعوم في WeasyPrint | ✅ box-shadow محذوف |

---

## ترتيب الإصلاحات المقترح

```
1. BUG-006  → إصلاح SyntaxError في cutting/inventory_integration.py
             - أضف except في _send_stock_shortage_notification
             - أضف def complete_inventory_deduction() المفقود

2. BUG-003  → تصحيح مسار الخط في contract_generation_service.py
             - غيّر /usr/share/fonts/... → file:///usr/share/fonts/...

3. BUG-008  → حماية AuditLog من AnonymousUser في core/audit.py

4. BUG-007  → مراجعة تعيين مستودعات المنتجات (مستودع 2000)
```

---

*تاريخ التقرير: 2026-02-23*  
*المحلِّل: GitHub Copilot — فحص آلي لسجلات آخر 24 ساعة*
