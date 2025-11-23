# إصلاح تخصيم الإكسسوارات من الفاتورة
# Accessory Invoice Deduction Fix

## التاريخ / Date
2025-11-23

## المشكلة / Problem

في الويزارد، كان يتم تخصيم الكمية من عناصر الفاتورة بشكل ممتاز في قسم الأقمشة، لكن الإكسسوارات لم يكن يتم تخصيمها من الفاتورة ولا إزالة العنصر عند اختياره.

In the wizard, fabric quantities were being deducted from invoice items perfectly, but accessories were not being deducted from the invoice nor removed when selected.

## الحل / Solution

### 1. تحديث نموذج CurtainAccessory

تم إضافة الحقول التالية لربط الإكسسوارات بعناصر الفاتورة:

**Added fields to link accessories to invoice items:**

```python
# ربط بعنصر الفاتورة النهائي
order_item = models.ForeignKey(
    'OrderItem',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='curtain_accessories',
    verbose_name='عنصر الفاتورة (النهائي)'
)

# ربط بعنصر المسودة
draft_order_item = models.ForeignKey(
    'DraftOrderItem',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='curtain_accessories',
    verbose_name='عنصر المسودة'
)
```

### 2. تحديث نوع حقل الكمية

تم تغيير حقل `quantity` من `IntegerField` إلى `DecimalField` لدعم الكميات العشرية:

**Changed quantity field type:**

```python
quantity = models.DecimalField(
    max_digits=10,
    decimal_places=3,
    default=1,
    verbose_name='الكمية',
    help_text='الكمية الإجمالية (العدد × المقاس إن وُجد)'
)
```

### 3. إضافة التحقق من الكمية

تم إضافة دالة `clean()` للتحقق من عدم تجاوز الكمية المتاحة في الفاتورة:

**Added validation method:**

```python
def clean(self):
    """التحقق من صحة البيانات"""
    from django.core.exceptions import ValidationError
    errors = {}
    
    # التحقق من عدم تجاوز الكمية المتاحة للطلبات النهائية
    if self.order_item and self.quantity:
        used_total = CurtainAccessory.objects.filter(
            order_item=self.order_item
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        available = self.order_item.quantity - used_total
        
        if self.quantity > available:
            errors['quantity'] = f'الكمية المطلوبة ({self.quantity}) أكبر من المتاح ({available} من {self.order_item.quantity})'
    
    # التحقق من عدم تجاوز الكمية المتاحة للمسودات
    if self.draft_order_item and self.quantity:
        used_total = CurtainAccessory.objects.filter(
            draft_order_item=self.draft_order_item
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        available = self.draft_order_item.quantity - used_total
        
        if self.quantity > available:
            errors['quantity'] = f'الكمية المطلوبة ({self.quantity}) أكبر من المتاح ({available} من {self.draft_order_item.quantity})'
    
    if errors:
        raise ValidationError(errors)
```

### 4. تحديث wizard_views.py

تم تحديث الكود لربط الإكسسوارات بعناصر الفاتورة عند الإضافة:

**Updated wizard views to link accessories to invoice items:**

#### في دالة wizard_add_curtain:
```python
# إضافة الإكسسوارات
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
        
        accessory = CurtainAccessory(
            curtain=curtain,
            draft_order_item=draft_order_item,  # ربط بعنصر الفاتورة
            accessory_name=accessory_data.get('name', ''),
            quantity=Decimal(str(accessory_data.get('quantity', 1))),
            size=accessory_data.get('size', ''),
            color=accessory_data.get('color', '')
        )
        
        # التحقق من الصحة قبل الحفظ
        try:
            accessory.full_clean()
            accessory.save()
            logger.info(f"Saved accessory: {accessory.accessory_name} - quantity: {accessory.quantity}")
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

#### نفس التحديث في دالة wizard_edit_curtain

## الملفات المعدلة / Modified Files

1. **orders/contract_models.py**
   - إضافة حقول `order_item` و `draft_order_item` لنموذج `CurtainAccessory`
   - تغيير نوع حقل `quantity` إلى `DecimalField`
   - إضافة دالة `clean()` للتحقق من الكمية

2. **orders/wizard_views.py**
   - تحديث دالة `wizard_add_curtain` لربط الإكسسوارات بعناصر الفاتورة
   - تحديث دالة `wizard_edit_curtain` بنفس التحديث
   - إضافة التحقق من الصحة (`full_clean()`) قبل الحفظ
   - إضافة رسائل خطأ واضحة عند تجاوز الكمية

3. **orders/migrations/0052_add_invoice_item_link_to_accessories.py**
   - ترحيل قاعدة البيانات الجديد

## الميزات الجديدة / New Features

### ✅ تخصيم تلقائي من الفاتورة
- يتم الآن تخصيم كمية الإكسسوارات من عناصر الفاتورة تلقائياً
- Accessories quantities are now automatically deducted from invoice items

### ✅ التحقق من الكمية المتاحة
- يتم التحقق من عدم تجاوز الكمية المتاحة قبل الحفظ
- Validates that requested quantity doesn't exceed available quantity

### ✅ رسائل خطأ واضحة
- رسائل خطأ واضحة توضح الكمية المطلوبة والمتاحة
- Clear error messages showing requested vs. available quantity

### ✅ إزالة العنصر عند استنفاد الكمية
- يتم إزالة العنصر من القائمة المتاحة عند استخدام كامل الكمية (في الواجهة)
- Item is removed from available list when quantity is fully used (in frontend)

### ✅ دعم الكميات العشرية
- دعم الكميات العشرية للإكسسوارات (مثل 1.5، 2.25)
- Support for decimal quantities (e.g., 1.5, 2.25)

## ملاحظات / Notes

### حساب الكمية
حالياً، يتم استخدام حقل `quantity` مباشرة للتخصيم من الفاتورة. إذا كنت ترغب في حساب الكمية كـ (العدد × المقاس)، يمكن إضافة هذا المنطق لاحقاً.

Currently, the `quantity` field is used directly for deduction. If you want to calculate quantity as (count × size), this logic can be added later.

### التوافق مع الأقمشة
الآن الإكسسوارات تعمل بنفس طريقة الأقمشة تماماً من حيث:
- الربط بعناصر الفاتورة
- التحقق من الكمية
- التخصيم التلقائي

Accessories now work exactly like fabrics in terms of:
- Linking to invoice items
- Quantity validation
- Automatic deduction

## الاختبار / Testing

للتأكد من عمل التحديث بشكل صحيح:

1. افتح الويزارد لإنشاء طلب جديد
2. أضف عناصر فاتورة تحتوي على إكسسوارات
3. في خطوة العقد، أضف ستارة
4. أضف إكسسوار من الفاتورة
5. تحقق من:
   - عدم السماح بتجاوز الكمية المتاحة
   - تحديث الكمية المتاحة بعد الإضافة
   - إزالة العنصر من القائمة عند استنفاد الكمية

To verify the update works correctly:

1. Open wizard to create new order
2. Add invoice items with accessories
3. In contract step, add a curtain
4. Add an accessory from the invoice
5. Verify:
   - Cannot exceed available quantity
   - Available quantity updates after adding
   - Item removed from list when quantity exhausted

## الترحيل / Migration

تم تطبيق الترحيل بنجاح:
```bash
python manage.py migrate orders
```

Migration applied successfully.
