# تحديث نظام تخصيم الإكسسوارات من الفاتورة - الإصلاح النهائي
# Final Fix for Accessory Invoice Deduction System

## التاريخ / Date
2025-11-23 (التحديث الثاني)

## المشكلة الإضافية / Additional Problem

بعد التطبيق الأول، اكتشفنا أن:
1. الواجهة (JavaScript) لا تحسب كمية الإكسسوارات المستخدمة
2. لا يوجد حساب للكمية كـ (العدد × المقاس)
3. حقل المقاس كان نصي ويحتاج لأن يكون رقمي

After the first implementation, we discovered:
1. The frontend (JavaScript) doesn't calculate used accessory quantities
2. No calculation for quantity as (count × size)
3. Size field was text and needs to be numeric

## الحل الكامل / Complete Solution

### 1. تحديث حقول النموذج

تم تعديل نموذج `CurtainAccessory` ليحتوي على:

```python
count = models.IntegerField(
    default=1,
    verbose_name='العدد',
    help_text='عدد القطع'
)

size = models.DecimalField(
    max_digits=10,
    decimal_places=3,
    default=1,
    verbose_name='المقاس',
    help_text='المقاس لكل قطعة'
)

quantity = models.DecimalField(
    max_digits=10,
    decimal_places=3,
    default=1,
    verbose_name='الكمية الإجمالية',
    help_text='الكمية الإجمالية = العدد × المقاس'
)
```

### 2. إضافة حساب تلقائي للكمية

```python
def save(self, *args, **kwargs):
    """حساب الكمية الإجمالية تلقائياً"""
    # Calculate quantity = count × size
    if self.count and self.size:
        self.quantity = self.count * self.size
    super().save(*args, **kwargs)
```

### 3. تحديث الواجهة لحساب الإكسسوارات

#### تحديث دالة calculateUsedQuantities:

```javascript
function calculateUsedQuantities() {
    // Reset usage
    for (let key in fabricUsageTracker) {
        fabricUsageTracker[key].used = 0;
    }
    
    // Add from existing curtains on the page
    {% for curtain in curtains %}
        {% for fabric in curtain.fabrics.all %}
            {% if fabric.order_item_id %}
                if (fabricUsageTracker['{{ fabric.order_item_id }}']) {
                    fabricUsageTracker['{{ fabric.order_item_id }}'].used += parseFloat('{{ fabric.meters }}');
                }
            {% endif %}
        {% endfor %}
        
        // NEW: حساب الإكسسوارات الموجودة
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
    
    // NEW: Add from temp accessories in current modal
    tempAccessories.forEach(accessory => {
        if (accessory.item_id && fabricUsageTracker[accessory.item_id]) {
            fabricUsageTracker[accessory.item_id].used += parseFloat(accessory.quantity);
        }
    });
    
    updateFabricSelectOptions();
}
```

#### تحديث دالة addAccessoryFromInvoice:

```javascript
function addAccessoryFromInvoice() {
    const select = document.getElementById('accessory-from-invoice');
    const itemId = select.value;
    const countInput = document.getElementById('accessory-invoice-quantity');
    const count = parseFloat(countInput.value);
    const sizeInput = document.getElementById('accessory-invoice-size');
    const size = parseFloat(sizeInput.value);
    const color = document.getElementById('accessory-invoice-color').value.trim();
    
    if (!itemId) {
        alert('يرجى اختيار الإكسسوار من الفاتورة');
        return;
    }
    
    if (!count || count <= 0 || isNaN(count)) {
        alert('يرجى إدخال عدد صحيح');
        return;
    }
    
    if (!size || size <= 0 || isNaN(size)) {
        alert('يرجى إدخال مقاس صحيح');
        return;
    }
    
    // NEW: Calculate total quantity = count × size
    const totalQuantity = count * size;
    
    // Calculate remaining quantity for this item
    calculateUsedQuantities();
    const tracker = fabricUsageTracker[itemId];
    if (!tracker) {
        alert('خطأ: لم يتم العثور على بيانات العنصر');
        return;
    }
    
    const remaining = tracker.total - tracker.used;
    
    if (totalQuantity > remaining + 0.001) {
        alert(`الكمية المطلوبة (${count} × ${size} = ${totalQuantity.toFixed(3)}) أكبر من المتوفر (${remaining.toFixed(3)})`);
        return;
    }
    
    const option = select.options[select.selectedIndex];
    const accessoryName = option.dataset.name;
    
    const accessory = {
        name: accessoryName,
        quantity: totalQuantity,  // Store calculated quantity
        count: count,             // Store count separately for display
        size: size,               // Store size as number
        color: color,
        source: 'invoice',
        item_id: itemId
    };
    
    tempAccessories.push(accessory);
    updateAccessoriesList();
    
    // Clear
    select.value = '';
    countInput.value = '1';
    sizeInput.value = '1';
    document.getElementById('accessory-invoice-color').value = '';
    document.getElementById('accessory-qty-hint').style.display = 'none';
    
    // Recalculate to update available quantities
    calculateUsedQuantities();
}
```

### 4. تحديث حقول الإدخال

```html
<!-- من الفاتورة -->
<div class="col-md-2">
    <label class="form-label">العدد</label>
    <input type="number" id="accessory-invoice-quantity" class="form-control" 
           min="1" step="1" value="1">
</div>
<div class="col-md-2">
    <label class="form-label">المقاس (رقم)</label>
    <input type="number" id="accessory-invoice-size" class="form-control" 
           min="0.01" step="0.01" value="1"
           placeholder="مثال: 2، 1.5">
</div>
```

### 5. تحديث عرض القائمة

```javascript
function updateAccessoriesList() {
    const list = document.getElementById('accessoriesList');
    
    if (tempAccessories.length === 0) {
        list.innerHTML = '<div class="alert alert-info">لم يتم إضافة إكسسوارات بعد</div>';
        return;
    }
    
    let html = '';
    tempAccessories.forEach((accessory, index) => {
        const colorText = accessory.color ? ` - <span class="badge bg-info">${accessory.color}</span>` : '';
        
        // Show count × size if both available
        let quantityDisplay = '';
        if (accessory.count && accessory.size) {
            const countFormatted = parseFloat(accessory.count).toFixed(0);
            const sizeFormatted = parseFloat(accessory.size).toFixed(3).replace(/\.?0+$/, '');
            const totalFormatted = parseFloat(accessory.quantity).toFixed(3).replace(/\.?0+$/, '');
            quantityDisplay = `العدد: ${countFormatted} × المقاس: ${sizeFormatted} = <strong>${totalFormatted}</strong>`;
        } else {
            const quantityFormatted = parseFloat(accessory.quantity).toFixed(3).replace(/\.?0+$/, '');
            quantityDisplay = `الكمية: ${quantityFormatted}`;
        }
        
        html += `
            <div class="card mb-2 border-primary">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${accessory.name}</strong>${colorText}
                            <br>
                            <small class="text-muted">${quantityDisplay}</small>
                        </div>
                        <button type="button" class="btn btn-sm btn-danger" onclick="removeAccessory(${index})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    list.innerHTML = html;
}
```

### 6. تحديث wizard_views.py

```python
# في دالة wizard_add_curtain و wizard_edit_curtain:
for accessory_data in accessories_data:
    try:
        # الحصول على draft_order_item إذا كان موجوداً
        draft_order_item = None
        item_id = accessory_data.get('item_id')
        if item_id:
            try:
                draft_order_item = draft.items.get(id=item_id)
                logger.info(f"Found draft item for accessory: {draft_order_item.product.name}")
            except Exception as e:
                logger.warning(f"Could not find draft item {item_id}: {e}")
        
        # Get count and size, calculate quantity
        count = int(accessory_data.get('count', 1))
        size = Decimal(str(accessory_data.get('size', 1)))
        quantity = Decimal(str(accessory_data.get('quantity', count * size)))
        
        accessory = CurtainAccessory(
            curtain=curtain,
            draft_order_item=draft_order_item,
            accessory_name=accessory_data.get('name', ''),
            count=count,
            size=size,
            quantity=quantity,
            color=accessory_data.get('color', '')
        )
        
        # التحقق من الصحة قبل الحفظ
        try:
            accessory.full_clean()
            accessory.save()
            logger.info(f"Saved accessory: {accessory.accessory_name} - count: {count} × size: {size} = quantity: {quantity}")
        except ValidationError as ve:
            # إرجاع رسالة خطأ واضحة للمستخدم
            error_msgs = []
            for field, errors in ve.message_dict.items():
                error_msgs.extend(errors)
            return JsonResponse({
                'success': False,
                'message': 'خطأ في كمية الإكسسوار: ' + ', '.join(error_msgs)
            }, status=400)
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Error adding accessory: {e}")
        return JsonResponse({
            'success': False,
            'message': f'خطأ في إضافة الإكسسوار: {str(e)}'
        }, status=400)
```

## الملفات المعدلة / Modified Files

1. **orders/contract_models.py**
   - إضافة حقل `count`
   - تغيير `size` من `CharField` إلى `DecimalField`
   - تحديث `quantity` help_text
   - إضافة دالة `save()` لحساب الكمية تلقائياً
   - تحديث `__str__()` لعرض الحساب

2. **orders/wizard_views.py**
   - تحديث `wizard_add_curtain` لاستقبال count و size
   - تحديث `wizard_edit_curtain` بنفس الطريقة
   - تحديث إرجاع بيانات الإكسسوارات عند التعديل

3. **orders/templates/orders/wizard/step5_contract.html**
   - تحديث `calculateUsedQuantities()` لحساب الإكسسوارات
   - تحديث `addAccessoryFromInvoice()` لحساب (العدد × المقاس)
   - تحديث `addExternalAccessory()` بنفس الطريقة
   - تحديث `updateAccessoriesList()` لعرض الحساب
   - تغيير حقل المقاس من text إلى number

4. **orders/migrations/0053_update_accessory_count_size_fields.py**
   - Migration مخصصة لتنظيف البيانات قبل التحويل
   - إضافة حقل count
   - تحويل size من CharField إلى DecimalField
   - تحديث quantity

## مثال على الاستخدام / Usage Example

### مثال 1: إكسسوار من الفاتورة
- **إكسسوار متاح:** كورنيش (3 متر)
- **العدد:** 2
- **المقاس:** 1 متر
- **الكمية المحسوبة:** 2 × 1 = 2 متر
- **المتبقي:** 3 - 2 = 1 متر ✅

### مثال 2: إكسسوار آخر
- **إكسسوار متاح:** حلقات (100 قطعة)
- **العدد:** 20
- **المقاس:** 1
- **الكمية المحسوبة:** 20 × 1 = 20 قطعة
- **المتبقي:** 100 - 20 = 80 قطعة ✅

## النتيجة النهائية / Final Result

✅ يتم حساب الكمية = العدد × المقاس
✅ يتم تخصيم الكمية من الفاتورة تلقائياً
✅ تحديث الكمية المتاحة في القائمة بشكل فوري
✅ إزالة العنصر عند استنفاد الكمية
✅ رسائل خطأ واضحة توضح الحساب
✅ التحقق من عدم تجاوز الكمية المتاحة

## الاختبار / Testing

للتأكد من عمل التحديث:

1. افتح الويزارد وأضف طلب جديد
2. أضف عنصر فاتورة إكسسوار بكمية 3
3. في خطوة العقد، أضف ستارة
4. اختر الإكسسوار من القائمة
5. أدخل العدد: 2، المقاس: 1
6. تحقق من:
   - الكمية المحسوبة = 2 × 1 = 2
   - الكمية المتبقية = 3 - 2 = 1
   - العنصر مازال ظاهر في القائمة
   - الكمية المتاحة محدثة

7. أضف الإكسسوار مرة أخرى
8. أدخل العدد: 1، المقاس: 1
9. تحقق من:
   - الكمية المحسوبة = 1 × 1 = 1
   - الكمية المتبقية = 1 - 1 = 0
   - العنصر اختفى من القائمة ✅
