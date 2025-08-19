# المزامنة المتقدمة مع Google Sheets

## نظرة عامة

نظام المزامنة المتقدمة مع Google Sheets هو حل شامل لمزامنة البيانات بين نظام إدارة علاقات العملاء (CRM) وجداول Google Sheets. يوفر النظام مزامنة ثنائية الاتجاه، إدارة التعارضات، والجدولة التلقائية.

## الميزات الرئيسية

### 🔄 المزامنة الذكية
- **مزامنة ثنائية الاتجاه**: من Google Sheets إلى النظام والعكس
- **تعيين الأعمدة المرن**: ربط أعمدة Google Sheets بحقول النظام
- **المعالجة المجمعة**: معالجة آلاف الصفوف بكفاءة
- **التحقق من البيانات**: التأكد من صحة البيانات قبل المزامنة

### ⚡ الأداء المحسن
- **المعالجة غير المتزامنة**: استخدام Celery للمهام الطويلة
- **التخزين المؤقت**: تخزين مؤقت ذكي لتحسين الأداء
- **الاستعلامات المحسنة**: استخدام bulk operations
- **إدارة الذاكرة**: مراقبة استخدام الذاكرة

### 🛡️ إدارة التعارضات
- **كشف التعارضات التلقائي**: تحديد التعارضات في البيانات
- **حل التعارضات المرن**: خيارات متعددة لحل التعارضات
- **سجل التعارضات**: تتبع جميع التعارضات وحلولها
- **الإشعارات**: تنبيهات فورية عند حدوث تعارضات

### 📅 الجدولة التلقائية
- **مزامنة مجدولة**: تشغيل المزامنة تلقائياً في أوقات محددة
- **تكرار مرن**: من كل دقيقة إلى يومياً
- **مراقبة الجدولة**: تتبع نجاح وفشل المهام المجدولة
- **إعادة المحاولة الذكية**: إعادة تشغيل المهام الفاشلة

## البنية التقنية

### النماذج (Models)

#### GoogleSheetMapping
```python
# تعيين Google Sheets إلى حقول النظام
- name: اسم التعيين
- spreadsheet_id: معرف جدول البيانات
- sheet_name: اسم الصفحة
- column_mappings: تعيين الأعمدة (JSON)
- auto_create_*: إعدادات الإنشاء التلقائي
- enable_reverse_sync: تفعيل المزامنة العكسية
```

#### GoogleSyncTask
```python
# مهام المزامنة
- mapping: التعيين المرتبط
- task_type: نوع المهمة (import/export/sync)
- status: حالة المهمة
- results: نتائج التنفيذ (JSON)
- statistics: إحصائيات المعالجة
```

#### GoogleSyncConflict
```python
# تعارضات المزامنة
- task: المهمة المرتبطة
- conflict_type: نوع التعارض
- system_data: بيانات النظام (JSON)
- sheet_data: بيانات Google Sheets (JSON)
- resolution_status: حالة الحل
```

#### GoogleSyncSchedule
```python
# جدولة المزامنة
- mapping: التعيين المرتبط
- frequency_minutes: تكرار المزامنة
- next_run: موعد التشغيل القادم
- statistics: إحصائيات التشغيل
```

### الخدمات (Services)

#### AdvancedSyncService
الخدمة الرئيسية للمزامنة:
- `sync_from_sheets()`: مزامنة من Google Sheets
- `sync_to_sheets()`: مزامنة إلى Google Sheets
- `_process_row()`: معالجة صف واحد
- `_create_conflict()`: إنشاء تعارض

#### SyncScheduler
مجدول المزامنة التلقائية:
- `run_scheduled_syncs()`: تشغيل المزامنة المجدولة

## التثبيت والإعداد

### 1. إضافة النماذج إلى قاعدة البيانات

```bash
python manage.py makemigrations odoo_db_manager
python manage.py migrate
```

### 2. إعداد Celery

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'run-scheduled-syncs': {
        'task': 'odoo_db_manager.tasks.run_scheduled_syncs',
        'schedule': crontab(minute='*/5'),
    },
}
```

### 3. تشغيل Celery

```bash
# تشغيل العامل
celery -A your_project worker -l info

# تشغيل المجدول
celery -A your_project beat -l info
```

### 4. إعداد Google Sheets API

تأكد من إعداد Google Sheets API credentials في النظام الحالي.

## الاستخدام

### 1. إنشاء تعيين جديد

1. انتقل إلى لوحة تحكم المزامنة المتقدمة
2. اضغط "إنشاء تعيين جديد"
3. أدخل معلومات الجدول
4. قم بتعيين الأعمدة
5. اختر الإعدادات المناسبة

### 2. تشغيل المزامنة يدوياً

```python
from odoo_db_manager.advanced_sync_service import AdvancedSyncService
from odoo_db_manager.google_sync_advanced import GoogleSheetMapping

mapping = GoogleSheetMapping.objects.get(name="اسم التعيين")
service = AdvancedSyncService(mapping)
result = service.sync_from_sheets()
```

### 3. استخدام أوامر Django

```bash
# مزامنة تعيين محدد
python manage.py sync_google_sheets --mapping-name "اسم التعيين"

# مزامنة جميع التعيينات
python manage.py sync_google_sheets --all

# تشغيل المزامنة المجدولة
python manage.py sync_google_sheets --scheduled

# التحقق من صحة التعيينات
python manage.py sync_google_sheets --validate
```

### 4. جدولة المزامنة

1. انتقل إلى تفاصيل التعيين
2. اضغط "جدولة المزامنة"
3. اختر التكرار المناسب
4. فعل الجدولة

## تعيين الأعمدة

### الحقول المدعومة

| نوع الحقل | الوصف | مطلوب |
|-----------|--------|--------|
| `customer_name` | اسم العميل | ✅ |
| `customer_phone` | رقم الهاتف | ❌ |
| `customer_email` | البريد الإلكتروني | ❌ |
| `customer_address` | العنوان | ❌ |
| `order_number` | رقم الطلب | ❌ |
| `invoice_number` | رقم الفاتورة | ❌ |
| `total_amount` | المبلغ الإجمالي | ❌ |
| `order_status` | حالة الطلب | ❌ |
| `notes` | ملاحظات | ❌ |

### التعيين التلقائي

النظام يدعم التعيين التلقائي للأعمدة بناءً على أسماء الأعمدة:
- أعمدة تحتوي على "اسم" أو "name" → `customer_name`
- أعمدة تحتوي على "هاتف" أو "phone" → `customer_phone`
- أعمدة تحتوي على "ايميل" أو "email" → `customer_email`

## إدارة التعارضات

### أنواع التعارضات

1. **عدم تطابق البيانات**: بيانات مختلفة للسجل نفسه
2. **تعديل متزامن**: تعديل السجل في النظام و Google Sheets
3. **سجل مفقود**: سجل موجود في مكان وغير موجود في آخر
4. **خطأ في التحقق**: بيانات لا تمر التحقق من الصحة

### استراتيجيات الحل

1. **يدوي**: المستخدم يحل التعارض
2. **النظام يفوز**: استخدام بيانات النظام
3. **Google Sheets يفوز**: استخدام بيانات Google Sheets

## المراقبة والتقارير

### لوحة التحكم

- إحصائيات المزامنة
- آخر المهام
- التعارضات المعلقة
- المزامنة المجدولة

### السجلات

```python
import logging
logger = logging.getLogger('odoo_db_manager.advanced_sync')
```

### التقارير

- تقارير نجاح/فشل المزامنة
- إحصائيات مفصلة
- تقارير التعارضات

## الأمان

### حماية البيانات
- التحقق من صحة البيانات
- تشفير البيانات الحساسة
- سجلات الوصول

### التحكم في الوصول
- صلاحيات المستخدمين
- تسجيل العمليات
- مراجعة الأنشطة

## استكشاف الأخطاء

### الأخطاء الشائعة

1. **خطأ في الاتصال بـ Google Sheets**
   ```
   الحل: تحقق من إعدادات API وصلاحيات الوصول
   ```

2. **تعارضات في البيانات**
   ```
   الحل: راجع تعيين الأعمدة وحل التعارضات يدوياً
   ```

3. **فشل المزامنة المجدولة**
   ```
   الحل: تحقق من تشغيل Celery وإعدادات الجدولة
   ```

### السجلات المفيدة

```bash
# عرض سجلات المزامنة
tail -f logs/advanced_sync.log

# عرض سجلات Celery
celery -A your_project events
```

## الأداء والتحسين

### نصائح الأداء

1. **استخدم المعالجة المجمعة**
2. **فعل التخزين المؤقت**
3. **حدد حجم الدفعة المناسب**
4. **راقب استخدام الذاكرة**

### مراقبة الأداء

```python
# إعدادات المراقبة
ADVANCED_SYNC_SETTINGS = {
    'MONITOR_PERFORMANCE': True,
    'PERFORMANCE_THRESHOLD_SECONDS': 300,
}
```

## التطوير والتخصيص

### إضافة حقول جديدة

1. أضف الحقل إلى `FIELD_TYPES` في `GoogleSheetMapping`
2. أضف منطق المعالجة في `AdvancedSyncService`
3. حدث القوالب والواجهات

### إضافة نوع تعارض جديد

1. أضف النوع إلى `CONFLICT_TYPES` في `GoogleSyncConflict`
2. أضف منطق الكشف في `AdvancedSyncService`
3. أضف منطق الحل في الواجهة

## الدعم والمساعدة

### الوثائق
- [دليل المستخدم](user_guide.md)
- [دليل المطور](developer_guide.md)
- [API Reference](api_reference.md)

### المجتمع
- [GitHub Issues](https://github.com/your-repo/issues)
- [المنتدى](https://forum.example.com)
- [Discord](https://discord.gg/example)

## الترخيص

هذا المشروع مرخص تحت رخصة MIT. راجع ملف [LICENSE](LICENSE) للتفاصيل.

---

**ملاحظة**: هذا النظام جزء من مشروع HomeUpdate CRM وتم تطويره خصيصاً لشركة الخواجة للستائر والمفروشات.
