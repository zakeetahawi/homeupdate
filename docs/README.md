# قسم التركيبات (Installations Department)

## نظرة عامة

قسم التركيبات هو نظام متكامل لإدارة عملية تركيب الطلبات بعد اكتمالها في قسم التصنيع. يوفر النظام إدارة شاملة لجدولة المواعيد، تخصيص الفنيين والسائقين، متابعة حالة التركيب، واستلام الدفعات المتبقية.

## الميزات الرئيسية

### 1. لوحة التحكم والإحصائيات
- عرض إحصائيات فورية لطلبات التركيب
- إجمالي طلبات التركيب المكتملة
- طلبات التركيب المجدولة
- طلبات التركيب غير المجدولة
- طلبات التركيب في انتظار الإرسال

### 2. إدارة الطلبات
- عرض جميع الطلبات المتاحة للتركيب
- معلومات العميل والطلب
- حالة التركيب والتقدم
- إمكانية الوصول لتفاصيل الطلب الكاملة

### 3. جدولة المواعيد
- واجهة تفاعلية لجدولة المواعيد
- تحديد الفنيين والسائقين
- تحديد الموعد المحدد
- تغيير حالة التركيب ديناميكياً

### 4. الجدول اليومي
- عرض تقرير يومي بالمواعيد
- إمكانية الطباعة
- تحديد الفنيين والسائقين المخصصين

### 5. إدارة العمليات
- تحديث حالة التركيب
- إلغاء العمليات وإعادة الجدولة
- رفع تقارير التعديل
- استلام المبالغ المتبقية
- إغلاق عملية التركيب

## النماذج (Models)

### Technician
```python
- name: اسم الفني
- phone: رقم الهاتف
- specialization: التخصص
- is_active: نشط/غير نشط
```

### Driver
```python
- name: اسم السائق
- phone: رقم الهاتف
- license_number: رقم الرخصة
- vehicle_number: رقم المركبة
- is_active: نشط/غير نشط
```

### InstallationTeam
```python
- name: اسم الفريق
- technicians: الفنيين (ManyToMany)
- driver: السائق (ForeignKey)
- is_active: نشط/غير نشط
```

### InstallationSchedule
```python
- order: الطلب (ForeignKey)
- team: الفريق (ForeignKey)
- scheduled_date: تاريخ التركيب
- scheduled_time: موعد التركيب
- status: حالة التركيب
- notes: ملاحظات
```

### InstallationPayment
```python
- installation: التركيب (ForeignKey)
- payment_type: نوع الدفع
- amount: المبلغ
- payment_method: طريقة الدفع
- receipt_number: رقم الإيصال
- notes: ملاحظات
```

### ModificationReport
```python
- installation: التركيب (ForeignKey)
- report_file: ملف التقرير
- description: وصف التعديل
```

### ReceiptMemo
```python
- installation: التركيب (OneToOne)
- receipt_image: صورة مذكرة الاستلام
- customer_signature: توقيع العميل
- amount_received: المبلغ المستلم
- notes: ملاحظات
```

### InstallationArchive
```python
- installation: التركيب (OneToOne)
- completion_date: تاريخ الإكمال
- archived_by: تم الأرشفة بواسطة
- archive_notes: ملاحظات الأرشفة
```

## الواجهات (Views)

### Dashboard
- عرض الإحصائيات العامة
- التركيبات المجدولة اليوم
- التركيبات القادمة
- إحصائيات الفرق

### Installation List
- قائمة جميع التركيبات
- فلترة وبحث متقدم
- تحديث الحالة
- إجراءات سريعة

### Installation Detail
- تفاصيل كاملة للتركيب
- معلومات الطلب والعميل
- المدفوعات والتقارير
- مذكرة الاستلام

### Daily Schedule
- الجدول اليومي
- إمكانية الطباعة
- معلومات الفرق

### Team Management
- إدارة الفرق
- إضافة فنيين وسائقين
- تعديل وحذف الفرق

## المسارات (URLs)

```python
# لوحة التحكم
path('', views.dashboard, name='dashboard')

# إدارة التركيبات
path('list/', views.installation_list, name='installation_list')
path('detail/<int:installation_id>/', views.installation_detail, name='installation_detail')
path('schedule/<int:installation_id>/', views.schedule_installation, name='schedule_installation')
path('update-status/<int:installation_id>/', views.update_status, name='update_status')

# الجدول اليومي
path('daily-schedule/', views.daily_schedule, name='daily_schedule')
path('print-daily-schedule/', views.print_daily_schedule, name='print_daily_schedule')

# المدفوعات والتقارير
path('add-payment/<int:installation_id>/', views.add_payment, name='add_payment')
path('add-modification-report/<int:installation_id>/', views.add_modification_report, name='add_modification_report')
path('add-receipt-memo/<int:installation_id>/', views.add_receipt_memo, name='add_receipt_memo')

# إدارة الفرق
path('team-management/', views.team_management, name='team_management')
path('add-team/', views.add_team, name='add_team')
path('add-technician/', views.add_technician, name='add_technician')
path('add-driver/', views.add_driver, name='add_driver')

# الأرشيف
path('archive/', views.archive_list, name='archive_list')

# APIs
path('stats-api/', views.installation_stats_api, name='installation_stats_api')
path('complete/<int:installation_id>/', views.complete_installation, name='complete_installation')
```

## النماذج (Forms)

### InstallationScheduleForm
- جدولة التركيب
- اختيار الفريق والتاريخ والوقت
- إضافة ملاحظات

### InstallationPaymentForm
- إضافة دفعة
- نوع الدفع والمبلغ
- طريقة الدفع ورقم الإيصال

### ModificationReportForm
- رفع تقرير تعديل
- وصف التعديل
- ملف التقرير

### ReceiptMemoForm
- رفع مذكرة استلام
- المبلغ المستلم
- توقيع العميل
- صورة المذكرة

## الخدمات (Services)

### InstallationService
- إحصائيات لوحة التحكم
- الجدولة التلقائية
- البحث والفلترة
- إدارة الأرشيف

## الإعدادات

### إضافة التطبيق إلى INSTALLED_APPS
```python
INSTALLED_APPS = [
    ...
    'installations',
    ...
]
```

### إضافة المسارات إلى URLs الرئيسي
```python
urlpatterns = [
    ...
    path('installations/', include('installations.urls')),
    ...
]
```

### إعدادات الوسائط
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## الاستخدام

### 1. إنشاء الفرق
- إضافة فنيين وسائقين
- إنشاء فرق تركيب
- تحديد التخصصات

### 2. استقبال الطلبات
- الطلبات المكتملة من التصنيع
- إضافة للقائمة غير المجدولة
- مراجعة تفاصيل الطلب

### 3. جدولة التركيبات
- اختيار الفريق المناسب
- تحديد التاريخ والوقت
- إضافة ملاحظات

### 4. متابعة العمليات
- تحديث حالة التركيب
- إضافة مدفوعات
- رفع تقارير تعديل

### 5. إكمال التركيب
- رفع مذكرة استلام
- تأكيد توقيع العميل
- نقل للأرشيف

## الأمان

- التحقق من الصلاحيات
- حماية الملفات المرفوعة
- التحقق من صحة البيانات
- تسجيل جميع العمليات

## الدعم

للحصول على الدعم أو الإبلاغ عن مشاكل:
- إنشاء issue في GitHub
- التواصل مع فريق التطوير
- مراجعة الوثائق

## التطوير المستقبلي

- تطبيق الجوال
- إشعارات فورية
- تقارير متقدمة
- تكامل مع أنظمة خارجية 