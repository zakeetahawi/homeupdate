# نظام الإشعارات المتكامل

نظام إشعارات شامل ومتطور لمشروع Django يوفر إشعارات فورية للمستخدمين حول جميع الأحداث المهمة في النظام.

## المميزات الرئيسية

### 🔔 أنواع الإشعارات المدعومة
- **إشعارات العملاء**: عند إنشاء عميل جديد
- **إشعارات الطلبات**: إنشاء، تعديل، تغيير حالة، تسليم الطلبات
- **إشعارات المعاينات**: إنشاء وتغيير حالة المعاينات
- **إشعارات التركيبات**: جدولة وإكمال التركيبات
- **إشعارات الشكاوى**: تسجيل شكاوى جديدة

### 🎯 نظام الصلاحيات الذكي
- **مديرو النظام**: يرون جميع الإشعارات
- **مديرو الفروع/المناطق**: يرون إشعارات فروعهم فقط
- **البائعون**: يرون إشعاراتهم الشخصية وإشعارات عملائهم
- **الأقسام المختصة**: تستقبل إشعارات حسب نوع الطلب/الحدث

### 🎨 واجهة مستخدم متطورة
- **أيقونة جرس** في شريط التنقل مع عداد الإشعارات غير المقروءة
- **قائمة منسدلة** تعرض آخر الإشعارات
- **صفحة إشعارات كاملة** مع فلترة وبحث متقدم
- **تصميم Bootstrap** متجاوب وأنيق

### ⚡ API متكامل
- **REST API** كامل باستخدام Django REST Framework
- **دعم JWT** للمصادقة
- **endpoints** لقراءة وتحديث حالة الإشعارات
- **تحديث فوري** للعدادات والقوائم

## التثبيت والإعداد

### 1. إضافة التطبيق
```python
# في settings.py
INSTALLED_APPS = [
    # ... التطبيقات الأخرى
    'notifications.apps.NotificationsConfig',
]

# إضافة context processor
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... المعالجات الأخرى
                'notifications.context_processors.notifications_context',
            ],
        },
    },
]
```

### 2. إضافة URLs
```python
# في urls.py الرئيسي
urlpatterns = [
    # ... المسارات الأخرى
    path('notifications/', include('notifications.urls', namespace='notifications')),
]
```

### 3. تطبيق Migrations
```bash
python manage.py makemigrations notifications
python manage.py migrate notifications
```

## الاستخدام

### إنشاء إشعار برمجياً
```python
from notifications.signals import create_notification

notification = create_notification(
    title="عنوان الإشعار",
    message="نص الإشعار التفصيلي",
    notification_type="order_created",
    related_object=order_instance,  # اختياري
    created_by=user,  # اختياري
    priority="normal",  # low, normal, high, urgent
    recipients=[user1, user2]  # اختياري - سيتم تحديدهم تلقائياً
)
```

### استخدام API
```javascript
// الحصول على عدد الإشعارات غير المقروءة
fetch('/notifications/api/count/')
    .then(response => response.json())
    .then(data => console.log('Unread count:', data.unread_count));

// تحديد إشعار كمقروء
fetch('/notifications/api/1/mark_read/', {method: 'POST'})
    .then(response => response.json())
    .then(data => console.log('Marked as read:', data.success));
```

## بنية النماذج

### Notification
- `title`: عنوان الإشعار
- `message`: نص الإشعار
- `notification_type`: نوع الإشعار
- `priority`: مستوى الأولوية
- `related_object`: الكائن المرتبط (Generic Foreign Key)
- `created_by`: المستخدم المنشئ
- `extra_data`: بيانات إضافية (JSON)

### NotificationVisibility
- `notification`: الإشعار
- `user`: المستخدم
- `is_read`: حالة القراءة
- `read_at`: تاريخ القراءة

### NotificationSettings
- `user`: المستخدم
- `enable_*_notifications`: تفعيل/إلغاء أنواع الإشعارات
- `min_priority_level`: الحد الأدنى لمستوى الأولوية

## الأحداث المدعومة

### العملاء
- إنشاء عميل جديد → إشعار للبائعين ومديري الفرع

### الطلبات
- إنشاء طلب جديد → إشعار للأقسام المسؤولة
- تعديل طلب → إشعار مميز بالتغييرات
- تغيير حالة طلب → إشعار للمنشئ ومديريه
- تسليم طلب → إشعار بتفاصيل التسليم

### المعاينات
- إنشاء معاينة → إشعار لقسم المعاينات
- تغيير حالة معاينة → إشعار للمنشئ ومديريه

### التركيبات
- جدولة تركيب → إشعار بتفاصيل الجدولة
- إكمال تركيب → إشعار بالإنجاز

### الشكاوى
- تسجيل شكوى → إشعار للمستخدم المستهدف والمديرين

## التخصيص

### إضافة نوع إشعار جديد
1. أضف النوع إلى `NOTIFICATION_TYPES` في `models.py`
2. أضف أيقونة في `get_icon_class()`
3. أضف signal handler في `signals.py`
4. أضف منطق الصلاحيات في `utils.py`

### تخصيص الواجهة
- عدل القوالب في `templates/notifications/`
- أضف CSS مخصص في `static/notifications/`
- استخدم Bootstrap classes للتصميم

## الأمان والأداء

- **فلترة الصلاحيات**: كل مستخدم يرى إشعاراته فقط
- **Indexes محسنة**: للبحث السريع
- **Lazy Loading**: تحميل البيانات عند الحاجة
- **Caching**: إمكانية إضافة cache للعدادات

## الاختبار

```bash
# تشغيل اختبار النظام
python test_notifications.py

# إنشاء إشعارات تجريبية
python manage.py shell
>>> from notifications.signals import create_notification
>>> # ... إنشاء إشعارات
```

## المساهمة

1. Fork المشروع
2. إنشاء branch للميزة الجديدة
3. Commit التغييرات
4. Push إلى Branch
5. إنشاء Pull Request

## الترخيص

هذا المشروع مرخص تحت رخصة MIT - راجع ملف LICENSE للتفاصيل.

## الدعم

للحصول على الدعم أو الإبلاغ عن مشاكل، يرجى إنشاء issue في المستودع.
