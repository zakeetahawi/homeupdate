# إصلاح مشكلة عرض الأقمشة المستهلكة
# Fix for Showing Used Fabrics Issue

## التاريخ / Date
2025-11-23

## المشكلة / Problem

عند إضافة ستارة ثانية في الويزارد، كانت الأقمشة المستهلكة من الستارة الأولى **تظهر متاحة للاختيار**، بينما الإكسسوارات المستهلكة **لا تظهر** (وهذا هو السلوك الصحيح).

When adding a second curtain in the wizard, used fabrics from the first curtain were **still showing as available**, while used accessories were correctly **hidden**.

## السبب / Root Cause

في دالة `calculateUsedQuantities()` في ملف `step5_contract.html`:

- الأقمشة كانت تستخدم `fabric.order_item_id`
- الإكسسوارات كانت تستخدم `accessory.draft_order_item_id`

المشكلة: في الويزارد نحن نعمل مع **DraftOrder** وليس **Order**، لذلك:
- الأقمشة المحفوظة لها `draft_order_item_id` وليس `order_item_id`
- لذلك لم تُحسب في `fabricUsageTracker`
- وظلت تظهر كأنها متاحة

The issue: In the wizard we work with **DraftOrder** not **Order**, so:
- Saved fabrics have `draft_order_item_id` not `order_item_id`
- Therefore they weren't counted in `fabricUsageTracker`
- And remained showing as available

## الحل / Solution

تغيير الكود ليستخدم `draft_order_item_id` للأقمشة مثل الإكسسوارات تماماً:

### قبل (Before):
```javascript
{% for fabric in curtain.fabrics.all %}
    {% if fabric.order_item_id %}
        if (fabricUsageTracker['{{ fabric.order_item_id }}']) {
            fabricUsageTracker['{{ fabric.order_item_id }}'].used += parseFloat('{{ fabric.meters }}');
        }
    {% endif %}
{% endfor %}
```

### بعد (After):
```javascript
{% for fabric in curtain.fabrics.all %}
    {% if fabric.draft_order_item_id %}
        if (fabricUsageTracker['{{ fabric.draft_order_item_id }}']) {
            fabricUsageTracker['{{ fabric.draft_order_item_id }}'].used += parseFloat('{{ fabric.meters }}');
        }
    {% endif %}
{% endfor %}
```

## الكود الكامل / Complete Code

```javascript
function calculateUsedQuantities() {
    // Reset usage
    for (let key in fabricUsageTracker) {
        fabricUsageTracker[key].used = 0;
    }
    
    // Add from existing curtains on the page
    {% for curtain in curtains %}
        // حساب الأقمشة المستخدمة
        {% for fabric in curtain.fabrics.all %}
            {% if fabric.draft_order_item_id %}
                if (fabricUsageTracker['{{ fabric.draft_order_item_id }}']) {
                    fabricUsageTracker['{{ fabric.draft_order_item_id }}'].used += parseFloat('{{ fabric.meters }}');
                }
            {% endif %}
        {% endfor %}
        
        // حساب الإكسسوارات المستخدمة
        {% for accessory in curtain.accessories.all %}
            {% if accessory.draft_order_item_id %}
                if (fabricUsageTracker['{{ accessory.draft_order_item_id }}']) {
                    fabricUsageTracker['{{ accessory.draft_order_item_id }}'].used += parseFloat('{{ accessory.quantity }}');
                }
            {% endif %}
        {% endfor %}
    {% endfor %}
    
    // Add from temp fabrics in current modal
    tempFabrics.forEach(fabric => {
        if (fabric.item_id && fabricUsageTracker[fabric.item_id]) {
            fabricUsageTracker[fabric.item_id].used += parseFloat(fabric.meters);
        }
    });
    
    // Add from temp accessories in current modal
    tempAccessories.forEach(accessory => {
        if (accessory.item_id && fabricUsageTracker[accessory.item_id]) {
            fabricUsageTracker[accessory.item_id].used += parseFloat(accessory.quantity);
        }
    });
    
    // Update the select options to show remaining quantities and hide fully used items
    updateFabricSelectOptions();
}
```

## الاختبار / Testing

### السيناريو:
1. إنشاء طلب جديد في الويزارد
2. إضافة منتج قماش بكمية 10 متر
3. إضافة منتج إكسسوار بكمية 5
4. في خطوة العقد، إضافة ستارة أولى:
   - قماش: 8 متر
   - إكسسوار: 3
5. حفظ الستارة
6. محاولة إضافة ستارة ثانية

### النتيجة المتوقعة:
- ✅ القماش يظهر متاح: 2 متر فقط (10 - 8 = 2)
- ✅ الإكسسوار يظهر متاح: 2 فقط (5 - 3 = 2)
- ✅ عند استخدام كامل الكمية، يختفي العنصر من القائمة

### قبل الإصلاح:
- ❌ القماش كان يظهر: 10 متر (الكمية الأصلية - لم يخصم المستخدم)
- ✅ الإكسسوار كان يظهر: 2 فقط (صحيح)

### بعد الإصلاح:
- ✅ القماش يظهر: 2 متر (صحيح)
- ✅ الإكسسوار يظهر: 2 فقط (صحيح)

## الملفات المعدلة / Modified Files

1. **orders/templates/orders/wizard/step5_contract.html**
   - تغيير `fabric.order_item_id` إلى `fabric.draft_order_item_id`
   - في دالة `calculateUsedQuantities()`
   - السطر 539-541

## الفائدة / Benefit

الآن الأقمشة والإكسسوارات تعمل بنفس الطريقة تماماً:
- ✅ تخصيم تلقائي من الكمية المتاحة
- ✅ تحديث فوري للكمية المتبقية
- ✅ إخفاء العنصر عند استنفاد الكمية
- ✅ منع إضافة كميات أكبر من المتاح
- ✅ عرض رسالة خطأ واضحة

Now fabrics and accessories work the same way:
- ✅ Automatic deduction from available quantity
- ✅ Instant update of remaining quantity
- ✅ Hide item when quantity exhausted
- ✅ Prevent adding more than available
- ✅ Clear error message display

## ملاحظة مهمة / Important Note

هذا الإصلاح يؤثر فقط على **الويزارد** (DraftOrder)، أما في العقود النهائية (Order) فتستخدم `order_item_id` كما هو مطلوب.

This fix only affects the **wizard** (DraftOrder), while in final contracts (Order) it uses `order_item_id` as required.

## التحقق / Verification

للتحقق من أن الإصلاح يعمل:

```bash
# ابحث عن جميع استخدامات fabric في calculateUsedQuantities
grep -A5 "for fabric in curtain.fabrics" orders/templates/orders/wizard/step5_contract.html

# يجب أن تجد: draft_order_item_id وليس order_item_id
```

Expected output:
```javascript
{% if fabric.draft_order_item_id %}  ✅ صحيح
```

Not:
```javascript
{% if fabric.order_item_id %}  ❌ خطأ
```
