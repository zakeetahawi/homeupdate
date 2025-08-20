# قائمة التحقق لتنفيذ تحسينات الأداء
## Implementation Checklist for Database Performance Optimization

> **هذه القائمة يجب اتباعها حرفياً خطوة بخطوة**

---

## ✅ قائمة التحقق السريعة (Quick Checklist)

### قبل البدء (Pre-Implementation)
- [ ] إنشاء نسخة احتياطية كاملة من قاعدة البيانات
- [ ] التأكد من عمل بيئة التطوير
- [ ] تثبيت Django Debug Toolbar
- [ ] إنشاء branch جديد في Git: `git checkout -b database-optimization`

### المرحلة الأولى - الأسبوع الأول
- [ ] **يوم 1-2**: إصلاح N+1 في المندوبين ✅/❌
- [ ] **يوم 3-4**: تحسين قائمة الطلبات ✅/❌
- [ ] **يوم 5-6**: إضافة الفهارس الحرجة ✅/❌
- [ ] **يوم 7**: اختبار المرحلة الأولى ✅/❌

### المرحلة الثانية - الأسبوع الثاني
- [ ] **يوم 8-9**: تحسين تقارير المخزون ✅/❌
- [ ] **يوم 10-11**: دوال البحث والتخزين ا��مؤقت ✅/❌
- [ ] **يوم 12-13**: الفهارس المتبقية ✅/❌
- [ ] **يوم 14**: اختبار المرحلة الثانية ✅/❌

### المرحلة الثالثة - الأسبوع الثالث
- [ ] **يوم 15-16**: مراقبة الأداء ✅/❌
- [ ] **يوم 17-18**: تحسينات إضافية ✅/❌
- [ ] **يوم 19-20**: اختبار شامل ✅/❌
- [ ] **يوم 21**: توثيق وتسليم ✅/❌

---

## 📋 التعليمات التفصيلية خطوة بخطوة

### الخطوة 1: إعداد البيئة
```bash
# 1. إنشاء نسخة احتياطية
pg_dump -h localhost -U postgres -d crm_system > backup_before_optimization.sql

# 2. إنشاء branch جديد
git checkout -b database-optimization

# 3. تثبيت أدوات المراقبة
pip install django-debug-toolbar

# 4. إضافة Debug Toolbar إلى settings.py
```

### الخطوة 2: إصلاح N+1 في المندوبين
**الملف**: `/home/zakee/homeupdate/orders/views.py`

1. **افتح الملف**:
```bash
nano /home/zakee/homeupdate/orders/views.py
```

2. **ابحث عن السطر** (Ctrl+W في nano):
```python
def salesperson_list(request):
```

3. **استبدل الكود التالي**:
```python
# الكود القديم (احذفه):
for sp in salespersons:
    sp.total_orders = Order.objects.filter(salesperson=sp).count()
    sp.completed_orders = Order.objects.filter(salesperson=sp, status='completed').count()
    sp.pending_orders = Order.objects.filter(salesperson=sp, status='pending').count()
    sp.total_sales = Order.objects.filter(salesperson=sp, status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
```

4. **بهذا الكود الجديد**:
```python
# الكود الجديد (أضفه):
from django.db.models import Count, Sum, Case, When, Q, DecimalField
from django.db.models.functions import Coalesce

salespersons = Salesperson.objects.select_related('branch').annotate(
    total_orders=Count('orders', distinct=True),
    completed_orders=Count('orders', filter=Q(orders__status='completed'), distinct=True),
    pending_orders=Count('orders', filter=Q(orders__status='pending'), distinct=True),
    total_sales=Coalesce(
        Sum('orders__total_amount', filter=Q(orders__status='completed'), 
            output_field=DecimalField(max_digits=10, decimal_places=2)),
        0
    ),
    avg_order_value=Coalesce(
        Sum('orders__total_amount', filter=Q(orders__status='completed')) / 
        Count('orders', filter=Q(orders__status='completed')),
        0,
        output_field=DecimalField(max_digits=10, decimal_places=2)
    )
).order_by('-total_sales')
```

5. **احفظ الملف**: Ctrl+X ثم Y ثم Enter

6. **اختبر التغيير**:
```bash
python manage.py runserver
# اذهب إلى صفحة المندوبين وتحقق من عملها
```

### الخطوة 3: تحسين قائمة الطلبات
**الملف**: `/home/zakee/homeupdate/orders/views.py`

1. **ابحث عن دالة**:
```python
def order_list(request):
```

2. **استبدل الكود الحالي بالكود المحسّن** (انظر الكود الكامل في TODO.md)

3. **احفظ واختبر**

### الخطوة 4: إضافة الفهارس
**الملف**: `/home/zakee/homeupdate/orders/models.py`

1. **افتح الملف**:
```bash
nano /home/zakee/homeupdate/orders/models.py
```

2. **ابحث عن**:
```python
class Meta:
    verbose_name = 'طلب'
    verbose_name_plural = 'الطلبات'
    ordering = ['-created_at']
    indexes = [
```

3. **أضف الفهارس الجديدة** قبل إغلاق القوس:
```python
# أضف هذه الفهارس:
models.Index(fields=['order_status', 'order_date'], name='order_status_date_idx'),
models.Index(fields=['branch', 'order_date', 'order_status'], name='order_branch_date_status_idx'),
models.Index(fields=['customer', 'created_at'], name='order_customer_created_idx'),
models.Index(fields=['payment_verified', 'order_status'], name='order_payment_status_idx'),
```

4. **إنشاء وتطبيق Migration**:
```bash
python manage.py makemigrations orders --name add_performance_indexes
python manage.py migrate
```

### الخطوة 5: قياس التحسن
```bash
# قبل التحسين - سجل عدد الاستعلامات
# بعد التحسين - قارن النتائج
```

---

## 🔍 نقاط التحقق المهمة

### بعد كل تغيير:
1. **تشغيل الخادم**: `python manage.py runserver`
2. **اختبار الصفحة المتأثرة**
3. **التحقق من Django Debug Toolbar**
4. **تسجيل عدد الاستعلامات**

### علامات النجاح:
- ✅ تقليل عدد الاستعلامات بنسبة 80%+
- ✅ تحسن وقت تحميل الصفحة
- ✅ عدم ظهور أخطاء
- ✅ عمل جميع الوظائف بشكل طبيعي

### علامات المشاكل:
- ❌ زيادة في عدد الاستعلامات
- ❌ بطء في تحميل الصفحة
- ❌ ظهور أخطاء في الكونسول
- ❌ عدم عمل بعض الوظائف

---

## 📞 جهات الاتصال في حالة المشاكل

### المشاكل التقنية:
- **مطور Django**: [اسم المطور]
- **مدير قاعدة البيانات**: [اسم ��دير قاعدة البيانات]

### المشاكل التشغيلية:
- **مدير المشروع**: [اسم مدير المشروع]
- **مدير النظام**: [اسم مدير النظام]

---

## 📊 نموذج تقرير التقدم اليومي

```
التاريخ: ___/___/___
المهمة المنجزة: ________________
الوقت المستغرق: ___ ساعات
عدد الاستعلامات قبل: ___
عدد الاستعلامات بعد: ___
نسبة التحسن: ___%
المشاكل المواجهة: ________________
الحلول المطبقة: ________________
الخطوة التالية: ________________
```

---

## 🚨 إجراءات الطوارئ

### في حالة فشل التحسين:
1. **إيقاف الخادم فوراً**
2. **العودة إلى النسخة الاحتياطية**:
```bash
psql -h localhost -U postgres -d crm_system < backup_before_optimization.sql
```
3. **العودة إلى الكود السابق**:
```bash
git checkout main
```
4. **إعادة تشغيل الخادم**
5. **الاتصال بالفريق التقني**

### في حالة مشاكل الأداء:
1. **تفعيل Django Debug Toolbar**
2. **فحص الاستعلامات البطيئة**
3. **مراجعة الفهارس**
4. **التحقق من استهلاك الذاكرة**

---

**��اريخ الإنشاء**: يناير 2025  
**آخر تحديث**: يناير 2025  
**الحالة**: جاهز للتنفيذ ✅