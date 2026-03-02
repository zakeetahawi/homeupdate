# خطة إصلاح نظام الشكاوى الشاملة
## Complaints Module - Complete Fix Plan

**تاريخ البدء**: 2026-02-14
**الحالة**: ✅ المرحلة 1 مكتملة | ✅ المرحلة 2 مكتملة | ✅ المرحلة 3 مكتملة

---

## المرحلة 1 — إصلاحات فورية (Critical Fixes)

### 1.1 ✅ نظام إشعارات منبثقة عام (General Popup Notification System)
- **المشكلة**: الإشعارات المنبثقة الجميلة (popup) موجودة فقط للشكاوى، باقي النظام يستخدم dropdown فقط
- **الحل**: إنشاء نظام popup عام يعرض أحدث الإشعارات غير المقروءة من جميع الأقسام بنفس التصميم
- **الملفات المتأثرة**: 
  - `templates/base.html` - إضافة popup عام + JavaScript
  - `notifications/views.py` - إنشاء API endpoint جديد للإشعارات المنبثقة
  - `notifications/urls.py` - إضافة مسار API

### 1.2 ✅ إصلاح أولوية الإسناد الافتراضي
- **المشكلة**: منشئ الشكوى (created_by) يُعيَّن كمسؤول عن الحل (خطأ منطقي)
- **الحل**: الأولوية لـ `default_assignee` من نوع الشكوى، ثم `created_by` كمرجع أخير
- **الملف**: `complaints/models.py` - دالة `save()`

### 1.3 ✅ حذف حقل response_time_hours المكرر
- **المشكلة**: الحقل `response_time_hours` معرّف مرتين في `ComplaintSLA`
- **الحل**: حذف التعريف الأول (بدون validators) والإبقاء على الثاني (مع validators)
- **الملف**: `complaints/models.py` - `ComplaintSLA` model

### 1.4 ✅ ربط فحص المواعيد النهائية بـ Celery Beat
- **المشكلة**: دالة `check_complaint_deadlines()` موجودة لكن لا تُستدعى أبداً
- **الحل**: إنشاء Celery task وربطها بـ Beat schedule
- **الملفات المتأثرة**:
  - `complaints/tasks.py` - إضافة task
  - `crm/settings.py` - إضافة CELERY_BEAT_SCHEDULE

### 1.5 ✅ توحيد نظام الإشعارات
- **المشكلة**: نظامان منفصلان (ComplaintNotification + Notification الرئيسي)
- **الحل**: إضافة أنواع شكاوى في notifications/signals.py لتغطية كل الأحداث (status_change, assignment, escalation) بالإضافة للإشعارات الداخلية
- **الملف**: `notifications/signals.py` - إضافة signal handlers جديدة

---

## المرحلة 2 — تحسينات الأداء والتكامل (Performance & Integration)

### 2.1 ✅ تحسين أداء escalated_complaints_api
- **المشكلة**: N+1 queries في Python loop
- **الحل**: استبدال بـ Subquery في استعلام واحد
- **الملف**: `complaints/api_views.py`

### 2.2 ✅ إصلاح رابط البريد الإلكتروني
- **المشكلة**: hardcoded `localhost:8000`
- **الحل**: استخدام `settings.SITE_URL` أو `settings.ALLOWED_HOSTS` ديناميكياً
- **الملف**: `complaints/services/notification_service.py`

### 2.3 ✅ تفعيل ComplaintUserPermissions
- **المشكلة**: نظام صلاحيات غني لكن غير مستخدم
- **الحل**: إضافة فحوصات `can_be_assigned_complaints` و `can_accept_new_complaint()` و `can_assign_complaints` في views الإسناد
- **الملفات**: `complaints/api_views.py` - `ComplaintAssignmentUpdateView`

---

## المرحلة 3 — تكامل شامل مع النظام (Full System Integration)

### 3.1 ✅ إنشاء شكاوى تلقائية من تأخر الطلبات والتركيبات
- **الحل**: Celery task `auto_create_delay_complaints` يعمل يومياً الساعة 9 صباحاً
- يفحص الطلبات المتأخرة 3+ أيام والتركيبات المتأخرة 2+ يوم
- ينشئ شكوى تلقائية بـ `source="auto"` مع تجنب التكرار
- **الملفات**: `complaints/tasks.py`, `complaints/models.py` (حقل source), `crm/settings.py`

### 3.2 ⬜ ربط الشكاوى بنظام WhatsApp

### 3.3 ✅ إضافة KPIs في لوحة المعلومات الرئيسية
- **الحل**: إضافة إحصائيات SLA (نسبة الالتزام، ضمن SLA، خارج SLA، اقتراب الموعد)
- إحصائيات الشكاوى التلقائية (إجمالي، مفتوحة، محلولة)
- إحصائيات حسب المصدر (يدوي، تلقائي، عميل)
- **الملفات**: `complaints/views.py`, `complaints/templates/complaints/dashboard.html`

### 3.4 ✅ دمج تقارير الشكاوى مع reports/
- **الحل**: إضافة SLA report (ضمن/خارج SLA + نسبة الالتزام)
- إحصائيات المصدر (يدوي/تلقائي/عميل)
- أداء الموظفين في SLA (إجمالي مسند، محلول، محلول ضمن SLA)
- **الملف**: `complaints/views.py` - `ComplaintReportsView`

---

## تنظيف الازدواجية (Duplication Cleanup)

### ✅ إزالة كل استخدامات ComplaintNotification
- **المشكلة**: ازدواجية في الإشعارات — نظامان يعملان بالتوازي
- **الحل**: 
  - `complaints/signals.py` — أعيد كتابته ليحتوي فقط على pre_save handler (تتبع التغييرات)
  - `notifications/signals.py` — يحتوي على كل signal handlers للشكاوى (post_save Complaint, ComplaintEscalation, ComplaintUpdate)
  - `complaints/services/notification_service.py` — أعيد كتابة `_send_notification()` لاستخدام Notification الرئيسي
  - `complaints/api_views.py` — كل الـ API endpoints تستعلم من NotificationVisibility بدلاً من ComplaintNotification
  - إضافة نوع `complaint_comment` في Notification model

---

## سجل التغييرات
| التاريخ | التغيير | الحالة |
|---------|--------|--------|
| 2026-02-14 | إنشاء الخطة | ✅ |
| 2026-02-14 | المرحلة 1 - اكتمال التنفيذ | ✅ |
| 2026-02-14 | المرحلة 2 - اكتمال التنفيذ | ✅ |
| 2026-02-15 | تنظيف الازدواجية - إزالة ComplaintNotification من كل الكود | ✅ |
| 2026-02-15 | المرحلة 3.1 - شكاوى تلقائية من التأخيرات | ✅ |
| 2026-02-15 | المرحلة 3.3 - KPIs في لوحة المعلومات | ✅ |
| 2026-02-15 | المرحلة 3.4 - تقارير SLA والمصدر | ✅ |
