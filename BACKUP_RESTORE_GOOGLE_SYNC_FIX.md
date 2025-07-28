# إصلاح مشكلة عدم استعادة تعيينات Google للمزامنة المتقدمة

## المشكلة المكتشفة

عند فحص نظام النسخ الاحتياطي والاستعادة، تم اكتشاف أن **تعيينات Google للمزامنة المتقدمة لا يتم استعادتها** عند استعادة نسخة احتياطية. السبب في ذلك أن نظام النسخ الاحتياطي كان **لا يشمل تطبيق `odoo_db_manager`** في قائمة التطبيقات الافتراضية للنسخ الاحتياطي.

## التطبيقات المفقودة

كان نظام النسخ الاحتياطي يشمل فقط:
- `contenttypes`
- `auth`
- `accounts`
- `customers`
- `orders`
- `inspections`
- `installations`
- `manufacturing`
- `inventory`
- `reports`

**ولكن كان يفتقد إلى `odoo_db_manager`** الذي يحتوي على:

### نماذج Google Sync المتقدمة المفقودة:
1. **GoogleSheetMapping** - تعيينات أوراق Google Sheets
2. **GoogleSyncTask** - مهام المزامنة
3. **GoogleSyncConflict** - تعارضات المزامنة
4. **GoogleSyncSchedule** - جدولة المزامنة
5. **GoogleSheetsConfig** - إعدادات Google Sheets
6. **GoogleDriveConfig** - إعدادات Google Drive
7. **Database** - إعدادات قواعد البيانات
8. **BackupSchedule** - جدولة النسخ الاحتياطية

## الإصلاحات المطبقة

### 1. إضافة تطبيق odoo_db_manager للنسخ الاحتياطي

```python
def _get_default_apps(self) -> List[str]:
    """الحصول على قائمة التطبيقات الافتراضية للنسخ الاحتياطي"""
    return [
        'contenttypes',
        'auth',
        'accounts',
        'customers',
        'orders',
        'inspections',
        'installations',
        'manufacturing',
        'inventory',
        'reports',
        'odoo_db_manager',  # إضافة تطبيق إدارة قاعدة البيانات ومزامنة Google
    ]
```

### 2. تحديث ترتيب التبعيات للاستعادة

تم إضافة نماذج Google Sync إلى ترتيب الأولوية في الاستعادة:

```python
priority_order = [
    # ... النماذج الأساسية
    'customers.customercategory',  # إضافة تصنيفات العملاء قبل العملاء
    'customers.customer',
    # ... باقي النماذج
    # إضافة نماذج Google Sync المتقدمة
    'odoo_db_manager.googlesheetsconfig',
    'odoo_db_manager.googledriveconfig',
    'odoo_db_manager.googlesheetmapping',
    'odoo_db_manager.googlesynctask',
    'odoo_db_manager.googlesyncconflict',
    'odoo_db_manager.googlesyncschedule',
    'odoo_db_manager.database',
    'odoo_db_manager.backupschedule',
]
```

## ما يشمله النسخ الاحتياطي الآن

### بيانات Google Sync المتقدمة:
- **تعيينات الأعمدة** - كيفية ربط أعمدة Google Sheets بحقول النظام
- **إعدادات المزامنة** - تكرار المزامنة، الخيارات المتقدمة
- **جدولة المزامنة** - المواعيد المحددة للمزامنة التلقائية
- **سجل المهام** - تاريخ عمليات المزامنة السابقة
- **حل التعارضات** - إعدادات التعامل مع التعارضات
- **المزامنة العكسية** - إعدادات المزامنة من النظام إلى Google Sheets

### إعدادات Google Drive:
- **اعتمادات الخدمة** - ملفات الاعتماد للوصول إلى Google Drive
- **مجلدات التخزين** - إعدادات مجلدات رفع الملفات
- **إعدادات الرفع** - خيارات رفع ملفات العقود والمستندات

### إعدادات قاعدة البيانات:
- **اتصالات قواعد البيانات** - إعدادات الاتصال بقواعد البيانات الخارجية
- **جدولة النسخ الاحتياطية** - المواعيد المحددة للنسخ الاحتياطية التلقائية

## التحقق من الإصلاح

### للتأكد من أن النسخة الاحتياطية تشمل بيانات Google Sync:

1. **إنشاء نسخة احتياطية جديدة** بعد هذا الإصلاح
2. **فحص محتويات النسخة الاحتياطية** للتأكد من وجود:
   - `odoo_db_manager.googlesheetmapping`
   - `odoo_db_manager.googlesheetsconfig`
   - `odoo_db_manager.googledriveconfig`

3. **اختبار الاستعادة** على نظام تجريبي للتأكد من استعادة جميع التعيينات

### أوامر التحقق:

```bash
# فحص تعيينات Google Sheets الموجودة
python manage.py shell -c "
from odoo_db_manager.google_sync_advanced import GoogleSheetMapping
print(f'عدد تعيينات Google Sheets: {GoogleSheetMapping.objects.count()}')
for mapping in GoogleSheetMapping.objects.all():
    print(f'- {mapping.name}: {mapping.spreadsheet_id}')
"

# فحص إعدادات Google Drive
python manage.py shell -c "
from odoo_db_manager.models import GoogleDriveConfig
config = GoogleDriveConfig.get_active_config()
if config:
    print(f'إعدادات Google Drive موجودة: {config.name}')
else:
    print('لا توجد إعدادات Google Drive')
"
```

## الخلاصة

تم إصلاح المشكلة بنجاح من خلال:

1. ✅ **إضافة تطبيق `odoo_db_manager`** إلى قائمة التطبيقات الافتراضية للنسخ الاحتياطي
2. ✅ **تحديث ترتيب التبعيات** لضمان الاستعادة الصحيحة لنماذج Google Sync
3. ✅ **إضافة تصنيفات العملاء** إلى ترتيب الأولوية لتجنب أخطاء المفاتيح الخارجية

**النتيجة**: النسخ الاحتياطية الجديدة ستشمل الآن **جميع تعيينات وإعدادات Google للمزامنة المتقدمة** وستتم استعادتها بشكل كامل عند الحاجة.

## ملاحظة مهمة

**النسخ الاحتياطية القديمة** (التي تم إنشاؤها قبل هذا الإصلاح) **لن تحتوي على بيانات Google Sync**. لذلك يُنصح بـ:

1. إنشاء نسخة احتياطية جديدة فوراً بعد هذا الإصلاح
2. الاحتفاظ بالنسخ الاحتياطية الجديدة كمرجع أساسي
3. عدم الاعتماد على النسخ الاحتياطية القديمة لاستعادة إعدادات Google Sync