# تقرير الأخطاء - 22 فبراير 2026

## الملخص التنفيذي

تم تحليل جميع سجلات التطبيق والخدمات والتانل. التطبيق يعمل لكن توجد **مشكلتان حرجتان** تتطلبان إصلاحًا فوريًا، وعدة مشاكل ثانوية.

---

## 🔴 الأخطاء الحرجة (Priority 1)

### BUG-001: UnboundLocalError في wizard_views.py - الخطوة 4

**الملف:** `orders/wizard_views.py` السطر **1237** و **1313**

**الخطأ:**
```
UnboundLocalError: cannot access local variable 'messages'
where it is not associated with a value
```

**URL المتأثر:** `POST /orders/wizard/step/4/`

**التأثير:** الخطوة 4 (تفاصيل الفاتورة والدفع) تعيد 500 Internal Server Error لكل مستخدم لا يمر بمسار `FileNotFoundError`.

**وقوع المشكلة:** مرّت مرتين على الأقل: `2026-02-21 20:37` و `2026-02-21 23:09`

**السبب الجذري:**
داخل دالة `wizard_step_4_invoice_payment`، يوجد import داخل كتلة `except`:

```python
# السطر ~1237 داخل except FileNotFoundError:
from django.contrib import messages   # ← هذا السطر هو المشكلة
messages.warning(request, "...")
```

لأن Python يعتبر أي متغير مُسنَد داخل دالة (بما فيها `from X import Y`) متغيرًا **محليًا** لكامل الدالة، حتى في الأجزاء التي تسبق الإسناد. وبما أن `messages` موجود في الـ import العلوي (السطر 12) كـ module-level import، فعند إضافة `from django.contrib import messages` داخل الدالة يتحول `messages` إلى local variable وكأنه لم يُعرَّف حين نصل للسطر 1313.

**الإصلاح:**
حذف السطر `from django.contrib import messages` من داخل الـ `except` block (السطر ~1237) لأن `messages` مستورد بالفعل في أعلى الملف (السطر 12).

```python
# قبل الإصلاح:
except FileNotFoundError:
    ...
    from django.contrib import messages   # احذف هذا السطر
    messages.warning(request, "...")

# بعد الإصلاح:
except FileNotFoundError:
    ...
    messages.warning(request, "...")      # يعمل مباشرة من top-level import
```

---

### BUG-002: فشل هجرة installation_accounting - 0004_technicianshare_unique_together

**الملف:** `installation_accounting/migrations/0004_technicianshare_unique_together.py`

**الخطأ:**
```
psycopg2.errors.UniqueViolation: could not create unique index
"installation_accounting__card_id_technician_id_511c86d7_uniq"
django.db.utils.IntegrityError: could not create unique index
"installation_accounting__card_id_technician_id_511c86d7_uniq"
```

**التأثير:**
- هجرة `0004` غير مطبّقة حتى الآن
- كل `./deploy_update.sh` أو `python manage.py migrate` يفشل بهذا الخطأ
- الـ deploy يُسجَّل كـ failure رغم أن التطبيق يعمل

**السبب:**
توجد بيانات مكررة في جدول `installation_accounting_technicianshare` حيث يوجد أكثر من صف بنفس قيمتي `(card_id, technician_id)`.

**الإصلاح المطلوب (خطوتان):**

**الخطوة 1:** تنظيف البيانات المكررة في قاعدة البيانات:
```sql
-- عرض التكرارات
SELECT card_id, technician_id, COUNT(*) as cnt
FROM installation_accounting_technicianshare
GROUP BY card_id, technician_id
HAVING COUNT(*) > 1;

-- حذف التكرارات والإبقاء على الأحدث
DELETE FROM installation_accounting_technicianshare
WHERE id NOT IN (
    SELECT MAX(id)
    FROM installation_accounting_technicianshare
    GROUP BY card_id, technician_id
);
```

**الخطوة 2:** تطبيق الهجرة بعد التنظيف:
```bash
python manage.py migrate installation_accounting
```

---

## 🟠 مشاكل مهمة (Priority 2)

### BUG-003: خط Noto Naskh Arabic لا يُحمَّل في WeasyPrint

**الخطأ:**
```
WARNING weasyprint fonts.add_font_face:250 - Font-face 'Noto Naskh Arabic' cannot be loaded
```

**التأثير:** تُولَّد عقود PDF بخط احتياطي بدلاً من الخط العربي، قد يؤثر على جودة العرض.

**الإصلاح:**
```bash
# تثبيت الخط على النظام
sudo pacman -S noto-fonts-arabic  # أو 
sudo apt install fonts-noto-core
fc-cache -fv
```

ثم التحقق من مسار الخط في إعدادات WeasyPrint أو ملف CSS المستخدم لتوليد PDF.

---

### BUG-004: مهام Celery لطلب محذوف (Order 28280)

**الخطأ المتكرر:**
```
WARNING orders.tasks tasks.calculate_order_totals_async:290
تم تجاهل المهمة: الطلب 28280 غير موجود (محذوف أو غير موجود)
```

**التأثير:** 13+ تحذير في جلسة واحدة، ضياع موارد Celery.

**السبب:** يبدو أن إنشاء كل عنصر في الطلب الجديد يُطلق مهمة `calculate_order_totals_async` برقم مسودة (28280) بدلاً من رقم الطلب الفعلي.

**الإصلاح المقترح:** مراجعة الـ signal أو الكود الذي يُطلق `calculate_order_totals_async` للتأكد من تمرير الـ `order_id` الصحيح بعد إنشاء الطلب وليس رقم المسودة.

---

### BUG-005: CSS غير مدعوم في WeasyPrint (تحذيرات PDF)

**التحذيرات:**
```
Ignored `word-break: break-word` - invalid value
Ignored `box-shadow: 0 4px 6px rgba(0,0,0,0.1)` - unknown property
```

**الإصلاح:** في قالب PDF:
- استبدال `word-break: break-word` بـ `word-break: normal` أو حذفها
- حذف `box-shadow` (غير مدعوم في WeasyPrint)

---

## 🟡 مشاكل الخدمة والـ Infrastructure (Priority 3)

### BUG-006: تجاوز TimeoutStop عند إيقاف الخدمة

**الخطأ:**
```
homeupdate.service: State 'stop-sigterm' timed out. Killing.
homeupdate.service: Killing process (db-backup.sh) with signal SIGKILL
homeupdate.service: Failed with result 'timeout'
```

**السبب:** `db-backup.sh` يستغرق أكثر من 60 ثانية (حد `TimeoutStopSec=60`).

**الإصلاح في `/etc/systemd/system/homeupdate.service`:**
```ini
TimeoutStopSec=120   # زيادة من 60 إلى 120 ثانية
```
أو إضافة `KillMode=mixed` للسماح بإيقاف الـ main process بينما يكمل الـ child processes.

---

### BUG-007: فشل تشغيل Celery Worker عند الـ deploy

**الخطأ:**
```
❌ ERROR: فشل في تشغيل Celery Worker
```

**الملاحظة:** الـ Worker يعمل حاليًا (PID: 2235). المشكلة في `لينكس/start-service.sh` التي تتحقق من تشغيل الـ Worker بعد وقت قصير جدًا.

**الإصلاح في `لينكس/start-service.sh`:** زيادة وقت الانتظار قبل التحقق من تشغيل Celery Worker:
```bash
sleep 5  # زيادة من 3 إلى 5 ثوانٍ قبل التحقق
```

---

## 🔵 الأمان (Priority 4)

### BUG-008: محاولات CSRF مشبوهة على صفحة تسجيل الدخول

**السجل:** `security.log`
```
Forbidden (CSRF token from POST incorrect.): /accounts/login/
```

**العدد:** 11 محاولة في يوم 21 فبراير بين 12:30 و 23:25

**التوصية:**
- مراجعة إعدادات AXES (موجودة بالفعل)
- إضافة rate limiting على `/accounts/login/` إذا لزم

---

### BUG-009: بوتات تصل لـ /accounts/logout/

- **AhrefsBot** يصل لـ `/accounts/logout/` ويُسبب logout غير مقصود
- **Googlebot** يفعل نفس الشيء

**التوصية:** إضافة `robots.txt` rule أو حماية `/accounts/logout/` بـ CSRF فقط (POST method فقط).

---

## 📊 حالة الخدمات الحالية

| الخدمة | PID | الحالة |
|--------|-----|--------|
| Daphne (ASGI) | 2431 | ✅ يعمل |
| Celery Worker | 2235 | ✅ يعمل |
| Celery Beat | 2321 | ✅ يعمل |
| Valkey/Redis | 785 | ✅ يعمل |
| PostgreSQL | - | ✅ يعمل |
| pgBouncer | - | ✅ يعمل |
| Cloudflare Tunnel | - | ✅ يعمل (مع انقطاعات QUIC دورية طبيعية) |
| هجرة installation_accounting | - | ❌ 0004 غير مطبّقة |

---

## ترتيب الإصلاحات المقترح

```
1. BUG-001  → حذف سطر import داخل except في wizard_views.py:1237
2. BUG-002  → تنظيف بيانات installation_accounting ثم migrate
3. BUG-003  → تثبيت خط noto-fonts-arabic
4. BUG-005  → إصلاح CSS في قالب PDF
5. BUG-004  → مراجعة calculate_order_totals_async signal
6. BUG-006  → زيادة TimeoutStopSec
7. BUG-007  → زيادة sleep في start-service.sh
8. BUG-009  → حماية logout من البوتات
```

---

*تاريخ التقرير: 2026-02-22*  
*تم التحليل من: service.log, service_error.log, django.log, errors.log, cloudflared.log, security.log, startup.log, postgres-monitor.log*
