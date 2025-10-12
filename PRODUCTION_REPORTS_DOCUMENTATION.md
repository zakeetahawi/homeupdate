# نظام تقارير إنتاج المصنع
# Factory Production Reports System

## نظرة عامة | Overview

تم تنفيذ نظام شامل لتقارير إنتاج المصنع يتضمن جميع الميزات المطلوبة:

A comprehensive Factory Production Reports system has been implemented with all requested features:

## الميزات المنفذة | Implemented Features

### 1. تتبع تحولات الحالة | Status Transition Tracking ✅

- **نموذج ManufacturingStatusLog**: يسجل تلقائياً كل تغيير في حالة أمر التصنيع
- **تتبع المستخدم**: يحفظ المستخدم المسؤول عن كل تغيير حالة
- **التواريخ**: يسجل تاريخ ووقت كل تحول
- **معلومات إضافية**: نوع الطلب، خط الإنتاج، ملاحظات

**الملفات المعنية:**
- `manufacturing/models.py` - نموذج ManufacturingStatusLog
- `manufacturing/signals.py` - معالجات الإشارات للتتبع التلقائي
- `manufacturing/views.py` - تم تعديل update_order_status لتمرير معلومات المستخدم

### 2. تصدير التقارير | Report Export ✅

#### تصدير Excel
- **الملف**: `manufacturing/views_production_reports.py` - دالة `export_production_report_excel`
- **المميزات**:
  - دعم كامل للغة العربية
  - تنسيق احترافي مع ألوان وحدود
  - جميع أعمدة بيانات العملاء والمصنع
  - تصدير حتى 10,000 سجل
  
#### تصدير PDF (جاهز للتنفيذ)
- **الملف**: `manufacturing/views_production_reports.py` - دالة `export_production_report_pdf`
- **المميزات**:
  - دعم RTL للعربية
  - تنسيق أفقي (Landscape)
  - يتطلب تثبيت WeasyPrint

### 3. لوحة تحكم التقارير | Reports Dashboard ✅

**الملفات:**
- `manufacturing/views_production_reports.py` - ProductionReportDashboardView
- `manufacturing/templates/manufacturing/production_reports/dashboard.html`

**المميزات:**
- إحصائيات عامة (إجمالي التحولات، عدد الطلبات، إجمالي الأمتار)
- فلاتر متقدمة (نطاق التاريخ، الحالات، خط الإنتاج، نوع الطلب)
- رسوم بيانية تفاعلية (Chart.js)
- قائمة المستخدمين الأكثر نشاطاً

### 4. عرض التفاصيل | Detail View ✅

**الملفات:**
- `manufacturing/views_production_reports.py` - ProductionReportDetailView
- `manufacturing/templates/manufacturing/production_reports/detail.html`

**المميزات:**
- جدول تفصيلي لجميع تحولات الحالة
- ترقيم الصفحات (50 سجل لكل صفحة)
- روابط مباشرة لأوامر التصنيع والطلبات
- فلاتر قابلة للتخصيص

### 5. التتبع اليومي | Daily Tracking ✅

**الملفات:**
- `manufacturing/views_production_reports.py` - DailyProductionTrackingView
- `manufacturing/templates/manufacturing/production_reports/daily_tracking.html` (يحتاج إنشاء)

**المميزات:**
- عرض إنتاج يوم محدد
- إحصائيات يومية (مكتمل، قيد التصنيع، تم التسليم)
- توزيع حسب خط الإنتاج ونوع الطلب

### 6. نماذج الفلترة | Filter Forms ✅

**الملف**: `manufacturing/forms_production_reports.py`

**النماذج المتاحة:**
- `ProductionReportFilterForm` - فلترة التقارير
- `ProductionForecastForm` - إنشاء توقعات الإنتاج
- `ExportColumnsForm` - اختيار الأعمدة للتصدير
- `DateRangeForm` - اختيار نطاق التاريخ

### 7. واجهة الإدارة | Admin Interface ✅

**الملف**: `manufacturing/admin.py`

**الفئات المضافة:**
- `ManufacturingStatusLogAdmin` - إدارة سجلات الحالة
- `ProductionForecastAdmin` - إدارة توقعات الإنتاج

**المميزات:**
- عرض منظم للبيانات
- فلاتر متقدمة
- بحث شامل
- حقول للقراءة فقط للحفاظ على سلامة البيانات

### 8. نموذج التوقعات | Forecast Model ✅

**الملف**: `manufacturing/models.py` - ProductionForecast

**الحقول:**
- تاريخ التوقع ونوع الفترة (يومي، أسبوعي، شهري، ربع سنوي، سنوي)
- عدد الطلبات المتوقع والفعلي
- الأمتار المتوقعة والفعلية
- مستوى الثقة
- خط الإنتاج ونوع الطلب (اختياري)

**الخصائص المحسوبة:**
- `accuracy_percentage` - دقة توقع عدد الطلبات
- `meters_accuracy_percentage` - دقة توقع الأمتار

## المسارات | URL Routes

```python
# في manufacturing/urls.py
path('production-reports/', ..., name='production_reports_dashboard')
path('production-reports/detail/', ..., name='production_reports_detail')
path('production-reports/daily-tracking/', ..., name='production_reports_daily_tracking')
path('production-reports/export/excel/', ..., name='production_reports_export_excel')
```

## الاستخدام | Usage

### 1. الوصول إلى التقارير

```
http://your-domain/manufacturing/production-reports/
```

### 2. فلترة التقارير

استخدم النموذج في لوحة التحكم لتحديد:
- نطاق التاريخ (من - إلى)
- الحالة الأصلية والحالة الجديدة
- خط الإنتاج
- نوع الطلب

### 3. تصدير البيانات

- **Excel**: انقر على زر "تصدير Excel" في لوحة التحكم
- **PDF**: (يتطلب تثبيت WeasyPrint أولاً)

### 4. عرض التفاصيل

انقر على "عرض التفاصيل" لرؤية جدول كامل بجميع التحولات

## المتطلبات | Requirements

### مكتبات Python المطلوبة:

```bash
pip install xlsxwriter  # للتصدير إلى Excel
pip install weasyprint  # للتصدير إلى PDF (اختياري)
```

### تثبيت WeasyPrint (للـ PDF):

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

# macOS
brew install cairo pango gdk-pixbuf libffi

# ثم
pip install weasyprint
```

## الميزات المتبقية | Remaining Features

### 1. محرك التنبؤ | Forecasting Engine ⏳

**ما يجب تنفيذه:**
- دالة لحساب التوقعات بناءً على البيانات التاريخية
- خوارزمية للتنبؤ بعدد الطلبات والأمتار
- واجهة لإنشاء وعرض التوقعات

**الملف المقترح**: `manufacturing/forecasting.py`

### 2. قالب PDF | PDF Template ⏳

**ما يجب تنفيذه:**
- إنشاء `manufacturing/templates/manufacturing/production_reports/pdf_template.html`
- تصميم مناسب للطباعة
- دعم RTL للعربية

### 3. قالب التتبع اليومي | Daily Tracking Template ⏳

**ما يجب تنفيذه:**
- إنشاء `manufacturing/templates/manufacturing/production_reports/daily_tracking.html`
- عرض إحصائيات اليوم
- رسوم بيانية للإنتاج اليومي

### 4. الرسوم البيانية المتقدمة | Advanced Charts ⏳

**ما يجب تنفيذه:**
- مقارنة التوقعات بالبيانات الفعلية
- اتجاهات الإنتاج الشهرية
- تحليل الأداء حسب خط الإنتاج

## الاختبار | Testing

### اختبار تتبع الحالة:

1. قم بتغيير حالة أمر تصنيع
2. تحقق من إنشاء سجل في ManufacturingStatusLog
3. تأكد من حفظ معلومات المستخدم

### اختبار التقارير:

1. افتح لوحة تحكم التقارير
2. جرب الفلاتر المختلفة
3. تحقق من دقة الإحصائيات
4. اختبر التصدير إلى Excel

### اختبار واجهة الإدارة:

1. افتح `/admin/manufacturing/manufacturingstatuslog/`
2. تحقق من عرض البيانات بشكل صحيح
3. جرب الفلاتر والبحث

## الأمان | Security

- جميع العروض محمية بـ `LoginRequiredMixin`
- الصلاحيات المطلوبة: `manufacturing.view_manufacturingorder`
- سجلات الحالة للقراءة فقط (لا يمكن التعديل أو الحذف إلا للمدير)
- التوقعات تحفظ معلومات المستخدم الذي أنشأها

## الصيانة | Maintenance

### تنظيف السجلات القديمة:

```python
# حذف سجلات أقدم من سنة
from datetime import timedelta
from django.utils import timezone
from manufacturing.models import ManufacturingStatusLog

old_date = timezone.now() - timedelta(days=365)
ManufacturingStatusLog.objects.filter(changed_at__lt=old_date).delete()
```

### تحديث التوقعات:

```python
# تحديث البيانات الفعلية للتوقعات
from manufacturing.models import ProductionForecast, ManufacturingStatusLog

# مثال: تحديث توقع يوم معين
forecast = ProductionForecast.objects.get(forecast_date='2025-10-08', period_type='daily')
actual_count = ManufacturingStatusLog.objects.filter(
    changed_at__date=forecast.forecast_date,
    to_status='completed'
).count()
forecast.actual_orders_count = actual_count
forecast.save()
```

## الدعم | Support

للمساعدة أو الإبلاغ عن مشاكل، يرجى التواصل مع فريق التطوير.

---

**تاريخ الإنشاء**: 2025-10-08
**الإصدار**: 1.0
**الحالة**: جاهز للاستخدام (مع ميزات إضافية قيد التطوير)

