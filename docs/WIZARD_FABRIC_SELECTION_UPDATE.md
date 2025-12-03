# تحديث نظام اختيار الأقمشة في ويزارد العقود
## Wizard Fabric Selection from Invoice Update

### التاريخ: 2025-11-20

## نظرة عامة

تم تحديث نظام الويزارد الخاص بإنشاء الطلبات والعقود الإلكترونية ليتوافق مع النظام القديم في طريقة اختيار الأقمشة. الآن يتم اختيار الأقمشة من قائمة منسدلة تحتوي على عناصر الفاتورة فقط، مع التحقق من عدم تجاوز الكمية المتاحة.

## التغييرات الرئيسية

### 1. واجهة اختيار القماش (Step 5 Contract Template)
**الملف:** `/home/zakee/homeupdate/orders/templates/orders/wizard/step5_contract.html`

#### التغييرات:
- **قبل:** حقل نصي حر لإدخال اسم القماش
- **بعد:** قائمة منسدلة تحتوي على عناصر الفاتورة فقط

#### الميزات الجديدة:
1. **اختيار من الفاتورة فقط:**
   ```html
   <select id="fabric-name" class="form-select" onchange="updateFabricQuantityInfo(this)">
       <option value="">اختر القماش من الفاتورة</option>
       {% for item in draft.items.all %}
       <option value="{{ item.id }}" data-available="{{ item.quantity }}" data-name="{{ item.product.name }}">
           {{ item.product.name }} - متوفر: {{ item.quantity }} متر
       </option>
       {% endfor %}
   </select>
   ```

2. **عرض الكمية المتبقية:**
   - يظهر تلميح (hint) يوضح الكمية المتبقية للاختيار
   - يتم تحديث التلميح تلقائياً عند اختيار قماش
   ```html
   <small class="text-muted mt-1" id="fabric-qty-hint" style="display:none;">
       <i class="fas fa-info-circle"></i> المتبقي للاختيار: <span id="remaining-qty">0</span> متر
   </small>
   ```

### 2. نظام تتبع الكميات (JavaScript)

#### متتبع الاستخدام (fabricUsageTracker):
```javascript
let fabricUsageTracker = {
    'item_id': {
        total: 100,      // الكمية الإجمالية من الفاتورة
        used: 45,        // الكمية المستخدمة في الستائر
        name: 'قماش شانيل'
    }
};
```

#### التهيئة الأولية:
```javascript
// تهيئة المتتبع من عناصر الفاتورة
{% for item in draft.items.all %}
fabricUsageTracker['{{ item.id }}'] = {
    total: parseFloat('{{ item.quantity }}'),
    used: 0,
    name: '{{ item.product.name|escapejs }}'
};
{% endfor %}
```

#### حساب الكميات المستخدمة:
```javascript
function calculateUsedQuantities() {
    // إعادة تعيين الاستخدام
    for (let key in fabricUsageTracker) {
        fabricUsageTracker[key].used = 0;
    }
    
    // إضافة من الستائر الموجودة
    {% for curtain in curtains %}
        {% for fabric in curtain.fabrics.all %}
            {% if fabric.order_item_id %}
                fabricUsageTracker['{{ fabric.order_item_id }}'].used += {{ fabric.meters }};
            {% endif %}
        {% endfor %}
    {% endfor %}
    
    // إضافة من الستائر المؤقتة في النافذة المنبثقة
    tempFabrics.forEach(fabric => {
        if (fabric.item_id && fabricUsageTracker[fabric.item_id]) {
            fabricUsageTracker[fabric.item_id].used += parseFloat(fabric.meters);
        }
    });
}
```

#### التحقق من الكمية عند الإضافة:
```javascript
function addFabricToList() {
    // ... التحقق من البيانات ...
    
    // التحقق من عدم تجاوز الكمية المتاحة
    calculateUsedQuantities();
    const tracker = fabricUsageTracker[fabricItemId];
    const remaining = tracker.total - tracker.used;
    
    if (meters > remaining) {
        alert(`الكمية المطلوبة (${meters} متر) أكبر من المتوفر (${remaining.toFixed(3)} متر)
المتبقي من ${tracker.name}: ${remaining.toFixed(3)} متر`);
        return;
    }
    
    // حفظ القماش مع item_id
    const fabric = {
        type: fabricType,
        name: fabricName,
        item_id: fabricItemId,  // ربط بعنصر الفاتورة
        meters: meters,
        pieces: pieces,
        tailoring: tailoring
    };
    
    tempFabrics.push(fabric);
}
```

### 3. التحديثات على الخادم (wizard_views.py)
**الملف:** `/home/zakee/homeupdate/orders/wizard_views.py`

#### التحقق من الكمية المتاحة:
```python
# إضافة الأقمشة
for idx, fabric_data in enumerate(fabrics_data):
    try:
        # الحصول على order_item إذا كان موجوداً
        order_item = None
        item_id = fabric_data.get('item_id')
        if item_id:
            try:
                order_item = draft.items.get(id=item_id)
            except Exception:
                pass
        
        fabric = CurtainFabric(
            curtain=curtain,
            order_item=order_item,  # ربط بعنصر الفاتورة
            fabric_type=fabric_data.get('type', 'light'),
            fabric_name=fabric_data.get('name', ''),
            pieces=int(fabric_data.get('pieces', 1)),
            meters=Decimal(str(fabric_data.get('meters', 0))),
            tailoring_type=fabric_data.get('tailoring', ''),
            sequence=idx + 1
        )
        
        # التحقق من الصحة قبل الحفظ
        try:
            fabric.full_clean()  # يتحقق من عدم تجاوز الكمية
            fabric.save()
        except ValidationError as ve:
            # إرجاع رسالة خطأ واضحة للمستخدم
            error_msgs = []
            for field, errors in ve.message_dict.items():
                error_msgs.extend(errors)
            return JsonResponse({
                'success': False,
                'message': 'خطأ في الكمية: ' + ', '.join(error_msgs)
            }, status=400)
```

### 4. نموذج CurtainFabric
**الملف:** `/home/zakee/homeupdate/orders/contract_models.py`

النموذج يحتوي بالفعل على:
- حقل `order_item` لربط القماش بعنصر الفاتورة
- دالة `clean()` للتحقق من عدم تجاوز الكمية المتاحة

```python
def clean(self):
    """التحقق من صحة البيانات"""
    from django.core.exceptions import ValidationError
    errors = {}
    
    # التحقق من عدم تجاوز الكمية المتاحة
    if self.order_item and self.meters:
        # حساب إجمالي ما تم استخدامه من هذا العنصر
        used_total = CurtainFabric.objects.filter(
            order_item=self.order_item
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('meters')
        )['total'] or 0
        
        available = self.order_item.quantity - used_total
        
        if self.meters > available:
            errors['meters'] = f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح ({available}م من {self.order_item.quantity}م)'
    
    if errors:
        raise ValidationError(errors)
```

### 5. تحديث قالب PDF للعقد
**الملف:** `/home/zakee/homeupdate/orders/templates/orders/contract_pdf_template.html`

تم تحديث القالب لدعم كلا النظامين:

#### عرض الأقمشة:
```django
{# New format: CurtainFabric model #}
{% if curtain.fabrics.exists %}
    {% for fabric in curtain.fabrics.all %}
    <div class="fabric-item">
        <span class="fabric-type">{{ fabric.get_fabric_type_display }}:</span>
        {% if fabric.order_item %}
            {{ fabric.order_item.product.name|truncatewords:3 }}
        {% else %}
            {{ fabric.fabric_name|truncatewords:3 }}
        {% endif %}
        - {{ fabric.meters }}م × {{ fabric.pieces }} قطعة
    </div>
    {% endfor %}
{% else %}
{# Old format: Direct foreign keys #}
    {# يعرض light_fabric, heavy_fabric, blackout_fabric #}
{% endif %}
```

## كيفية الاستخدام

### للمستخدم النهائي:

1. **في خطوة العقد (Step 5):**
   - اختر "عقد إلكتروني"
   - اضغط "إضافة ستارة جديدة"

2. **إضافة قماش:**
   - اختر نوع القماش (خفيف/ثقيل/بلاك أوت)
   - **اختر القماش من القائمة المنسدلة** (تحتوي على عناصر الفاتورة فقط)
   - سيظهر تلميح يوضح الكمية المتبقية للاختيار
   - أدخل الكمية المطلوبة (لن تتمكن من إدخال كمية أكبر من المتوفر)
   - اختر طريقة التفصيل وعدد القطع
   - اضغط "إضافة القماش"

3. **التحقق التلقائي:**
   - إذا حاولت إدخال كمية أكبر من المتوفر، سيظهر تنبيه
   - التنبيه يوضح الكمية المطلوبة والمتوفرة واسم القماش
   - مثال: "الكمية المطلوبة (50 متر) أكبر من المتوفر (30.000 متر). المتبقي من قماش شانيل: 30.000 متر"

## الفوائد

1. **دقة البيانات:** 
   - منع الأخطاء في إدخال أسماء الأقمشة
   - ربط مباشر بين الأقمشة المستخدمة وعناصر الفاتورة

2. **منع تجاوز الكميات:**
   - التحقق التلقائي من الكميات على مستوى الواجهة والخادم
   - عرض واضح للكميات المتبقية

3. **تتبع استخدام الأقمشة:**
   - معرفة كمية القماش المستخدمة من كل عنصر فاتورة
   - سهولة التدقيق والمراجعة

4. **توافق مع النظام القديم:**
   - قالب PDF يدعم كلا النظامين
   - إمكانية عرض العقود القديمة والجديدة بنفس التنسيق

## الملفات المعدلة

1. `/home/zakee/homeupdate/orders/templates/orders/wizard/step5_contract.html`
   - تحديث واجهة اختيار القماش
   - إضافة نظام تتبع الكميات
   - إضافة التحقق من الكميات المتاحة

2. `/home/zakee/homeupdate/orders/wizard_views.py`
   - تحديث `wizard_add_curtain` لاستخدام `order_item`
   - إضافة التحقق من الكميات على الخادم

3. `/home/zakee/homeupdate/orders/templates/orders/contract_pdf_template.html`
   - دعم عرض الأقمشة من CurtainFabric model
   - الحفاظ على التوافق مع النظام القديم

## ملاحظات تقنية

### نموذج البيانات:
```
DraftOrder (مسودة الطلب)
    ├── DraftOrderItem[] (عناصر الفاتورة)
    │       ├── Product (المنتج)
    │       └── quantity (الكمية)
    └── ContractCurtain[] (الستائر)
            ├── room_name, width, height
            ├── CurtainFabric[] (الأقمشة)
            │       ├── order_item → DraftOrderItem (الربط بالفاتورة)
            │       ├── fabric_type (خفيف/ثقيل/بلاك أوت)
            │       ├── meters (الأمتار)
            │       └── tailoring_type (طريقة التفصيل)
            └── CurtainAccessory[] (الإكسسوارات)
```

### التحقق متعدد المستويات:
1. **JavaScript (الواجهة):** تحقق فوري عند إضافة القماش
2. **Django Model (clean):** تحقق عند حفظ البيانات
3. **Django View:** تحقق إضافي وإرجاع رسائل خطأ واضحة

## الاختبار

للتأكد من عمل النظام بشكل صحيح:

1. أنشئ مسودة طلب جديدة
2. أضف عناصر للفاتورة (أقمشة) بكميات محددة
3. في خطوة العقد، حاول إضافة ستارة
4. جرب إضافة قماش بكمية تتجاوز المتوفر
5. تأكد من ظهور رسالة الخطأ
6. أضف قماشاً بكمية صحيحة
7. أضف ستارة ثانية واستخدم نفس القماش
8. تأكد من تحديث الكميات المتبقية تلقائياً

## التطويرات المستقبلية المقترحة

1. **عرض مرئي للكميات:**
   - شريط تقدم (progress bar) يوضح نسبة الاستخدام
   - ألوان تحذيرية عند اقتراب الكمية من النفاد

2. **اقتراحات ذكية:**
   - اقتراح القماش الأنسب بناءً على نوع الستارة
   - حساب تلقائي للكمية المطلوبة بناءً على المقاسات

3. **تقارير استخدام الأقمشة:**
   - تقرير يوضح استخدام كل قماش في الطلب
   - تنبيهات عند وجود أقمشة غير مستخدمة

## الدعم والمساعدة

في حالة وجود مشاكل:
1. تأكد من أن عناصر الفاتورة تم إضافتها في الخطوة 3
2. تحقق من أن الكميات في الفاتورة صحيحة
3. راجع سجلات الأخطاء في Django logs

---
**آخر تحديث:** 2025-11-20
**الإصدار:** 1.0
