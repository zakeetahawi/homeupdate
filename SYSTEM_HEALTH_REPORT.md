# 📋 تقرير صحة النظام - El-Khawaga ERP System
**تاريخ التقرير:** 2026-03-03  
**الجهاز:** zakee-hpz230towerworkstation (HP Z230 Tower Workstation)  
**المشروع:** https://github.com/zakeetahawi/homeupdate  

---

## 🖥️ معلومات الشبكة والاتصال عن بُعد

| المعلومة | القيمة |
|---|---|
| **عنوان IP المحلي (الشبكة الداخلية)** | `192.168.20.160` |
| **الشبكة الفرعية** | `192.168.20.0/24` |
| **اسم الجهاز (Hostname)** | `zakee-hpz230towerworkstation` |
| **المنفذ الافتراضي للتطبيق** | `8000` |
| **الرابط العام للموقع** | https://elkhawaga.uk |

> **للاتصال عن طريق برنامج AnyDesk/Remmina:**  
> استخدم عنوان IP: **`192.168.20.160`**  
> يجب أن يكون الجهاز المُتصِل على نفس الشبكة المحلية `192.168.20.x`  
> أو استخدام VPN للوصول عن بُعد عبر الإنترنت.

---

## 🟢 حالة الخدمات الحالية

| الخدمة | الحالة | التفاصيل |
|---|---|---|
| **Daphne (ASGI Server)** | ✅ يعمل | PID: 2204، يعمل منذ 2026-03-02 |
| **Celery Worker** | ✅ يعمل | PID: 2111، Queue: celery, file_uploads |
| **Celery Beat** | ✅ يعمل | PID: 2152، مجدول المهام يعمل |
| **Valkey/Redis** | ✅ يعمل | يعمل منذ 2026-03-02 11:27:16، ذاكرة: 11.2MB |
| **PostgreSQL** | ✅ يعمل | يعمل منذ 2026-03-02 11:27:21، ذاكرة: **3.6GB** |
| **Cloudflared Tunnel** | ✅ يعمل | 4 اتصالات نشطة (mrs06, mxp04) |
| **run-production.service** | ⚠️ غير نشط (Inactive/Disabled) | الخدمة لا تعمل كـ systemd |
| **Nginx** | ❌ غير موجود | لا يوجد Nginx |
| **النسخ الاحتياطية** | ✅ تعمل | كل ساعة، آخر نسخة: 2026-03-03 09:30 |

---

## 🔴 المشاكل الحرجة (Critical Issues)

### 1. خطأ مكتبة pg_trgm في PostgreSQL
**الخطورة:** 🔴 حرجة  
**الوقت:** 2026-03-02 11:21 - 11:25 (عند بدء التشغيل)  
**الخطأ:**
```
could not load library "/usr/lib/postgresql/pg_trgm.so": 
/usr/lib/postgresql/pg_trgm.so: undefined symbol: pg_mblen_unbounded
```
**التأثير:** تسبب في أخطاء 500 Internal Server Error متعددة في:
- `/manufacturing/approval/17833/` (10+ مرات)
- `/orders/wizard/finalize/`
- `/manufacturing/api/update_status/17725/`
- `/orders/order/28436/contract/regenerate/`

**السبب:** عدم توافق نسخة مكتبة `pg_trgm` مع نسخة PostgreSQL المثبتة.  
**طريقة الإصلاح:**
```bash
# إعادة بناء الامتداد
sudo -u postgres psql -d <اسم_قاعدة_البيانات> -c "DROP EXTENSION IF EXISTS pg_trgm; CREATE EXTENSION pg_trgm;"

# أو تحديث حزمة postgres-contrib
sudo pacman -S postgresql-contrib  # على Arch Linux
# أو
sudo apt-get install postgresql-contrib  # على Debian/Ubuntu

# ثم إعادة تشغيل PostgreSQL
sudo systemctl restart postgresql
```

---

### 2. خدمة run-production.service معطلة (Disabled)
**الخطورة:** 🟠 عالية  
**الحالة:** `inactive (dead)` و `disabled`  
**التأثير:** إذا أُعيد تشغيل الجهاز، لن تبدأ الخدمات تلقائياً  
**طريقة الإصلاح:**
```bash
# تفعيل الخدمة للبدء التلقائي
sudo systemctl enable run-production.service

# تشغيلها الآن إذا لزم
sudo systemctl start run-production.service

# التحقق من الحالة
sudo systemctl status run-production.service
```

---

## 🟡 المشاكل المتكررة (Recurring Issues)

### 3. رصيد مخزون سالب - مستودع الادويه
**الخطورة:** 🟡 متوسطة  
**التكرار:** أكثر من 20 مرة يومياً  
**المنتجات المتأثرة في 2026-03-02:**

| المنتج | الكود | النقص |
|---|---|---|
| HARMONY /C1 | 10100303955 | -40.000 |
| KOYA/C51 | 10100300375 | -60.000 |
| dona/C STEEL 1989 | 10100300247 | -41.000 |
| MO-GERMAN/C5 | 10100300457 | -58.000 |
| PRINT-KASTER | 10100200001 | -8.000 |
| VILLA-NEW \C8 | 10100304007 | -6.500 |
| MOSHA PD /C17 | 10100303368 | -15.000 |
| KOYA/C20 | 10100300349 | -20.500 |
| OKAA/C16 | 10100302649 | -8.000 |
| ATX/C2 | 10100300120 | -3.000 |

**السبب:** يتم إنشاء أوامر طلب بمنتجات غير متوفرة في مستودع "الادويه"  
**طريقة الإصلاح:**
```bash
# مراجعة الأرصدة ومطابقة المخزون
python manage.py shell_plus
# ثم مراجعة StockMovement وInventoryItem للمنتجات المتأثرة
# تحديث الكميات الصحيحة من المستودع المادي
```

---

### 4. أخطاء CSRF Token
**الخطورة:** 🟡 منخفضة  
**التكرار:** 9 مرات في 2026-03-02  
**الأنواع:**
- `CSRF token from POST incorrect` - من IP: 127.0.0.1 (داخلي)
- `Referer checking failed - no Referer` - محاولات على `/admin/login/`

**السبب:** روبوتات مسح أمني أو جلسات منتهية الصلاحية  
**طريقة الإصلاح:**
- تأكد من تفعيل SameSite=Lax لملفات الكوكيز
- مراجعة إعدادات `CSRF_TRUSTED_ORIGINS` في settings.py
- إضافة rate limiting على `/admin/login/`

---

### 5. مشكلة خط Noto Naskh Arabic في PDF
**الخطورة:** 🟡 منخفضة  
**الخطأ:** `Font-face 'Noto Naskh Arabic' cannot be loaded`  
**التأثير:** قد تظهر العقود/المستندات بخط غير صحيح  
**طريقة الإصلاح:**
```bash
# تثبيت الخط
sudo pip install reportlab
# أو تثبيت الخط على مستوى النظام
sudo cp path/to/NotoNaskhArabic.ttf /usr/share/fonts/
sudo fc-cache -fv
```

---

### 6. عدم استقرار نفق Cloudflare
**الخطورة:** 🟡 منخفضة  
**الوقت:** 2026-03-03 05:22-05:23 UTC  
**الخطأ:** `failed to dial to edge with quic: timeout: no recent network activity`  
**المدة:** حوالي دقيقة واحدة ثم عادت الاتصالات (4 اتصالات نشطة الآن)  
**طريقة الإصلاح:**
```bash
# مراقبة السجل بشكل مستمر
tail -f /home/zakee/homeupdate/logs/cloudflared.log

# إذا توقف النفق يمكن إعادة تشغيله
pkill cloudflared
/home/zakee/homeupdate/cloudflared tunnel run --config /home/zakee/homeupdate/cloudflared.yml &
```

---

## 🟢 الأنظمة التي تعمل بشكل صحيح

### قاعدة البيانات (PostgreSQL)
- ✅ تقبل الاتصالات - فحوصات كل دقيقة تؤكد ذلك
- ✅ آخر فحص ناجح: 2026-03-03 10:10:23

### النسخ الاحتياطية
- ✅ تعمل كل ساعة بشكل منتظم
- ✅ 20+ نسخة احتياطية في الـ 24 ساعة الماضية
- ✅ مسار الحفظ: `/home/zakee/homeupdate/media/backups/`

### نظام تسجيل الدخول
- ✅ AXES يعمل بشكل صحيح (حماية من القوة الغاشمة)
- ✅ تقييد الأجهزة يعمل (اكتشاف محاولة دخول غير مصرح بها: ahmed.elshemi)
- ✅ WhatsApp messages تعمل (إرسال customer_welcome ناجح)

### أنظمة المحاسبة والطلبات
- ✅ إنشاء الطلبات يعمل (آخر طلب: 4-0511-0001)
- ✅ توليد العقود يعمل
- ✅ أوامر التقطيع تُنشأ تلقائياً

---

## 📊 إحصائيات السجلات (24 ساعة الماضية)

| السجل | الحجم | ملاحظات |
|---|---|---|
| `daphne_access.log` | 131,716 سطر | طلبات HTTP كثيفة - طبيعي |
| `service.log` | 117,821 سطر | سجل الخدمة الرئيسي |
| `django.log` | 9,621 سطر | أخطاء وتحذيرات |
| `service_error.log` | 8,961 سطر | INFO + بعض أخطاء المخزون |
| `celery_worker.log` | 0 سطر | ⚠️ Celery لا يكتب للملف |
| `celery_beat.log` | 0 سطر | ⚠️ Beat لا يكتب للملف |
| `slow_queries.log` | 0 سطر | ✅ لا استعلامات بطيئة |
| `performance.log` | 0 سطر | ✅ لا مشاكل أداء |

---

## 🔧 خطة الإصلاح المقترحة (بالأولوية)

### أولوية عاجلة
1. **إصلاح pg_trgm.so** - إعادة بناء/تثبيت امتداد pg_trgm لتجنب أخطاء 500
2. **تفعيل run-production.service** - لضمان عودة الخدمات تلقائياً بعد الإقلاع

### أولوية متوسطة  
3. **ضبط مخزون مستودع الادويه** - مطابقة المخزون الفعلي مع قاعدة البيانات
4. **إعداد Celery logs** - التأكد من كتابة السجلات للملفات
5. **إضافة rate limiting للأدمن** - حماية `/admin/login/`

### أولوية منخفضة
6. **تثبيت خط Noto Naskh Arabic** - لتحسين جودة PDF
7. **مراقبة Cloudflare Tunnel** - إضافة إنذار عند انقطاع النفق

---

## 📌 أوامر مفيدة للمراقبة السريعة

```bash
# فحص الحالة الكاملة
ps aux | grep -E "daphne|celery" | grep -v grep

# مراقبة الأخطاء الحية  
tail -f /home/zakee/homeupdate/logs/django.log | grep ERROR

# فحص استخدام موارد النظام
htop  # أو: top

# فحص الاتصالات النشطة على المنفذ 8000
ss -tlnp | grep 8000

# إعادة تشغيل الخدمات (إذا لزم)
cd /home/zakee/homeupdate
bash لينكس/run-production.sh
```

---

*آخر تحديث: 2026-03-03 | GitHub Copilot System Analysis*
