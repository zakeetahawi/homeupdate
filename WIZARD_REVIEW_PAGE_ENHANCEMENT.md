# تحسين صفحة المراجعة النهائية - الويزارد
# Wizard Review Page Enhancement

## التاريخ / Date
2025-11-23

## الهدف / Objective

تحسين صفحة المراجعة النهائية (الخطوة 6) في الويزارد لتوفير عرض شامل قبل إنشاء الطلب، مع إمكانية عرض ملف العقد وملف المعاينة وإمكانية التعديل.

Enhance the final review page (Step 6) in the wizard to provide a comprehensive preview before creating the order, with the ability to view contract and inspection files and make edits.

## الميزات الجديدة / New Features

### 1. عرض ملف العقد (PDF Viewer)

إذا كان هناك عقد إلكتروني أو ملف PDF مرفوع:
- **عرض مدمج** للملف باستخدام iframe
- **زر فتح في نافذة جديدة** للعرض الكامل
- **زر تحميل** لحفظ الملف
- عرض **رقم العقد** بشكل بارز

```html
<div class="card mb-4">
    <div class="card-header bg-light d-flex justify-content-between align-items-center">
        <h5 class="mb-0">
            <i class="fas fa-file-contract me-2"></i>ملف العقد
            {% if draft.contract_number %}
                <span class="text-primary">({{ draft.contract_number }})</span>
            {% endif %}
        </h5>
        <div>
            <a href="{{ contract_file_url }}" target="_blank" class="btn btn-primary btn-sm me-2">
                <i class="fas fa-external-link-alt me-1"></i>فتح في نافذة جديدة
            </a>
            <a href="{{ contract_file_url }}" download class="btn btn-success btn-sm">
                <i class="fas fa-download me-1"></i>تحميل
            </a>
        </div>
    </div>
    <div class="card-body p-0">
        <div class="ratio ratio-16x9" style="height: 600px;">
            <iframe src="{{ contract_file_url }}" frameborder="0"></iframe>
        </div>
    </div>
</div>
```

### 2. عرض ملف المعاينة

إذا كان الطلب مرتبط بمعاينة:
- عرض **معلومات المعاينة** (الرقم، التاريخ، الملاحظات)
- **زر عرض ملف المعاينة** إن وُجد
- يفتح في نافذة جديدة للمراجعة

```html
<div class="card mb-4">
    <div class="card-header bg-light">
        <h5 class="mb-0">
            <i class="fas fa-clipboard-check me-2"></i>المعاينة المرتبطة
        </h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-8">
                <table class="table table-borderless table-sm">
                    <tr>
                        <th>رقم المعاينة:</th>
                        <td>{{ inspection.id }}</td>
                    </tr>
                    <tr>
                        <th>التاريخ:</th>
                        <td>{{ inspection.created_at|date:"Y-m-d H:i" }}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-4 text-end">
                <a href="{{ inspection_file_url }}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-file-pdf me-2"></i>عرض ملف المعاينة
                </a>
            </div>
        </div>
    </div>
</div>
```

### 3. عرض تفاصيل العقد الإلكتروني بشكل مفصّل

لكل ستارة في العقد:
- **القياسات** (العرض، الارتفاع، المساحة)
- **نوع التركيب**
- **بيت الستارة** (إن وُجد)
- **قائمة الأقمشة** بالتفصيل (النوع، الاسم، الكمية، التفصيل)
- **قائمة الإكسسوارات** بالتفصيل (الاسم، العدد × المقاس = الكمية، اللون)
- **الملاحظات**

```html
<div class="col-md-6 mb-3">
    <div class="border rounded p-3 h-100">
        <h6 class="text-primary border-bottom pb-2 mb-3">
            <i class="fas fa-th me-2"></i>{{ curtain.room_name }}
        </h6>
        
        <!-- القياسات -->
        <div class="mb-3">
            <strong><i class="fas fa-ruler-combined me-2"></i>القياسات:</strong>
            <div class="ms-3">
                <p class="mb-1"><small>العرض: {{ curtain.width }} م</small></p>
                <p class="mb-1"><small>الارتفاع: {{ curtain.height }} م</small></p>
                <p class="mb-1"><small class="text-success">المساحة: {{ curtain.area }} م²</small></p>
            </div>
        </div>
        
        <!-- الأقمشة -->
        <div class="mb-3">
            <strong><i class="fas fa-scroll me-2"></i>الأقمشة:</strong>
            {% for fabric in curtain.fabrics.all %}
            <div class="border-start border-3 border-info ps-2 mb-2">
                <p class="mb-0"><small><strong>{{ fabric.get_fabric_type_display }}:</strong> {{ fabric.fabric_name }}</small></p>
                <p class="mb-0"><small class="text-muted">{{ fabric.meters }} متر - {{ fabric.pieces }} قطعة</small></p>
            </div>
            {% endfor %}
        </div>
        
        <!-- الإكسسوارات -->
        <div class="mb-3">
            <strong><i class="fas fa-shapes me-2"></i>الإكسسوارات:</strong>
            {% for accessory in curtain.accessories.all %}
            <div class="border-start border-3 border-warning ps-2 mb-2">
                <p class="mb-0"><small><strong>{{ accessory.accessory_name }}</strong></small></p>
                <p class="mb-0">
                    <small class="text-muted">
                        العدد: {{ accessory.count }} × المقاس: {{ accessory.size }} = {{ accessory.quantity }}
                    </small>
                </p>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
```

### 4. أزرار تعديل سريعة

في كل قسم، يوجد زر "تعديل" ينقل للخطوة المناسبة:
- **معلومات الطلب** → الخطوة 1
- **عناصر الطلب** → الخطوة 3
- **الفاتورة والدفع** → الخطوة 4
- **العقد** → الخطوة 5

```html
<div class="card-header bg-light d-flex justify-content-between align-items-center">
    <h5 class="mb-0">
        <i class="fas fa-info-circle me-2"></i>معلومات الطلب الأساسية
    </h5>
    <a href="{% url 'orders:wizard_step' step=1 %}" class="btn btn-sm btn-outline-primary">
        <i class="fas fa-edit me-1"></i>تعديل
    </a>
</div>
```

### 5. ملخص شامل

صندوق ملخص يعرض:
- **معلومات العميل والطلب**
  - اسم العميل
  - الفرع
  - البائع
  - نوع الطلب
  - رقم العقد

- **الملخص المالي**
  - عدد المنتجات
  - عدد الستائر (إن وُجدت)
  - الإجمالي
  - الخصم
  - المبلغ النهائي
  - المدفوع
  - المتبقي

```html
<div class="card mb-4 border-success">
    <div class="card-header bg-success text-white">
        <h5 class="mb-0">
            <i class="fas fa-clipboard-list me-2"></i>ملخص الطلب النهائي
        </h5>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-primary mb-3">معلومات العميل والطلب</h6>
                <!-- ... -->
            </div>
            <div class="col-md-6">
                <h6 class="text-primary mb-3">الملخص المالي</h6>
                <!-- ... -->
            </div>
        </div>
    </div>
</div>
```

### 6. رسائل توضيحية

- رسالة تحذيرية للمراجعة قبل الحفظ
- إشعار بإمكانية التعديل
- تنبيه لمراجعة ملف العقد

```html
<div class="alert alert-warning mb-0">
    <i class="fas fa-exclamation-triangle me-2"></i>
    يرجى مراجعة تفاصيل العقد بعناية. يمكنك العودة لتعديل أي معلومات قبل الحفظ النهائي.
</div>
```

## التعديلات على الكود / Code Changes

### 1. wizard_views.py

```python
def wizard_step_6_review(request, draft):
    """الخطوة 6: المراجعة والتأكيد"""
    items = draft.items.all()
    totals = draft.calculate_totals()
    
    # الحصول على الستائر إن وجدت
    curtains = ContractCurtain.objects.filter(draft_order=draft).order_by('sequence')
    
    # الحصول على ملف العقد إذا كان موجوداً
    contract_file_url = None
    if draft.contract_file:
        contract_file_url = draft.contract_file.url
    
    # الحصول على المعاينة المرتبطة إن وُجدت
    inspection = None
    inspection_file_url = None
    if draft.related_inspection:
        inspection = draft.related_inspection
        if hasattr(inspection, 'inspection_file') and inspection.inspection_file:
            inspection_file_url = inspection.inspection_file.url
    
    context = {
        'draft': draft,
        'items': items,
        'curtains': curtains,
        'totals': totals,
        'contract_file_url': contract_file_url,
        'inspection': inspection,
        'inspection_file_url': inspection_file_url,
        'current_step': 6,
        'total_steps': 6,
        'step_title': 'المراجعة والتأكيد',
        'progress_percentage': 100,
    }
    
    return render(request, 'orders/wizard/step6_review.html', context)
```

### 2. step6_review.html

تم إضافة الأقسام التالية:
1. عرض رقم العقد في قسم الفاتورة
2. قسم عرض المعاينة المرتبطة
3. قسم عرض ملف العقد بـ iframe
4. تفاصيل العقد الإلكتروني المحسّنة
5. أزرار التعديل في كل قسم
6. ملخص شامل قبل الحفظ النهائي

## فوائد التحديث / Benefits

### ✅ للمستخدم
1. **مراجعة شاملة** قبل إنشاء الطلب
2. **عرض مباشر** لملف العقد دون الحاجة لتحميله
3. **إمكانية التعديل** السريع لأي قسم
4. **تأكيد مرئي** لجميع التفاصيل

### ✅ للعمل
1. **تقليل الأخطاء** من خلال المراجعة الدقيقة
2. **عرض احترافي** يشبه تقديم عرض للعميل
3. **سهولة التدقيق** قبل الحفظ النهائي
4. **توثيق كامل** لجميع جوانب الطلب

### ✅ للنظام
1. **UX محسّن** بشكل كبير
2. **عرض منظم** لجميع البيانات
3. **تنقل سلس** بين الخطوات
4. **معلومات واضحة** ومرتبة

## حالات الاستخدام / Use Cases

### حالة 1: طلب مع عقد إلكتروني
1. المستخدم يكمل جميع الخطوات
2. يضيف ستائر في الخطوة 5
3. في الخطوة 6، يرى:
   - تفاصيل كل ستارة بالتفصيل
   - رقم العقد
   - أزرار تعديل لكل قسم
4. يراجع ويؤكد

### حالة 2: طلب مع عقد PDF مرفوع
1. المستخدم يرفع ملف PDF في الخطوة 5
2. في الخطوة 6، يرى:
   - عارض PDF مدمج
   - زر فتح في نافذة جديدة
   - زر تحميل
3. يراجع الملف ويؤكد

### حالة 3: طلب مرتبط بمعاينة
1. الطلب مربوط بمعاينة سابقة
2. في الخطوة 6، يرى:
   - معلومات المعاينة
   - زر عرض ملف المعاينة
3. يراجع كلا الملفين ويؤكد

### حالة 4: اكتشاف خطأ قبل الحفظ
1. المستخدم يراجع في الخطوة 6
2. يجد خطأ في كمية منتج
3. يضغط زر "تعديل" بجانب عناصر الطلب
4. يعود للخطوة 3
5. يعدل الكمية
6. يعود للخطوة 6 للمراجعة النهائية

## الملفات المعدلة / Modified Files

1. **orders/wizard_views.py**
   - تحديث دالة `wizard_step_6_review()`
   - إضافة `contract_file_url`
   - إضافة `inspection` و `inspection_file_url`

2. **orders/templates/orders/wizard/step6_review.html**
   - إضافة قسم عرض ملف العقد
   - إضافة قسم عرض المعاينة
   - تحسين عرض تفاصيل العقد الإلكتروني
   - إضافة أزرار التعديل
   - إضافة ملخص شامل
   - إضافة رسائل توضيحية

## الاختبار / Testing

للتأكد من عمل التحديث:

1. **طلب عادي:**
   - أنشئ طلب بدون عقد
   - تأكد من ظهور جميع الأقسام الأساسية

2. **طلب مع عقد إلكتروني:**
   - أنشئ طلب وأضف ستائر
   - تحقق من ظهور تفاصيل الستائر بالكامل
   - تأكد من ظهور رقم العقد

3. **طلب مع عقد PDF:**
   - ارفع ملف PDF في الخطوة 5
   - تحقق من عرض الملف في iframe
   - اختبر أزرار الفتح والتحميل

4. **طلب مع معاينة:**
   - أنشئ طلب مرتبط بمعاينة
   - تحقق من ظهور معلومات المعاينة
   - اختبر زر عرض الملف

5. **اختبار التعديل:**
   - اضغط زر تعديل في أي قسم
   - تأكد من الانتقال للخطوة الصحيحة
   - عدّل البيانات
   - تأكد من التحديث في صفحة المراجعة

## ملاحظات / Notes

- يتم عرض ملف PDF مباشرة في الصفحة باستخدام iframe
- الأزرار تحترم navigation flow للويزارد
- جميع الروابط تفتح الملفات في نافذة جديدة
- التصميم responsive ويعمل على جميع الأجهزة
- الألوان والأيقونات متسقة مع باقي النظام

## مستقبلاً / Future Enhancements

يمكن إضافة:
1. **طباعة مباشرة** من صفحة المراجعة
2. **إرسال بالبريد الإلكتروني** للعميل
3. **حفظ كـ PDF** لصفحة المراجعة نفسها
4. **مقارنة** بين المسودة والعقد السابق (إن وُجد)
5. **تعليقات** أو ملاحظات إضافية
