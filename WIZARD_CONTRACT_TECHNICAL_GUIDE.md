# دليل التكامل الفني - نظام الويزارد والعقود
**Technical Integration Guide**

---

## 🏗️ البنية التقنية

### Database Schema

```sql
-- مسودات الطلبات
orders_draftorder
  ├── created_by_id (FK -> auth_user)
  ├── customer_id (FK -> customers_customer)
  ├── branch_id (FK -> accounts_branch)
  ├── salesperson_id (FK -> accounts_salesperson)
  ├── related_inspection_id (FK -> inspections_inspection)
  ├── final_order_id (FK -> orders_order)
  └── fields: current_step, completed_steps (JSON), contract_type, etc.

-- عناصر المسودات
orders_draftorderitem
  ├── draft_order_id (FK -> orders_draftorder)
  ├── product_id (FK -> inventory_product)
  └── fields: quantity, unit_price, discount_percentage, item_type, notes

-- ستائر العقود
orders_contractcurtain
  ├── order_id (FK -> orders_order, nullable)
  ├── draft_order_id (FK -> orders_draftorder, nullable)  ⭐ للويزارد
  └── fields: room_name, width, height, installation_type, etc.

-- أقمشة الستائر ⭐ نموذج جديد
orders_curtainfabric
  ├── curtain_id (FK -> orders_contractcurtain)
  ├── order_item_id (FK -> orders_orderitem, nullable)
  ├── draft_order_item_id (FK -> orders_draftorderitem, nullable)  ⭐ للويزارد
  └── fields: fabric_type, fabric_name, pieces, meters, tailoring_type, notes ⭐, sequence

-- إكسسوارات الستائر
orders_curtainaccessory
  ├── curtain_id (FK -> orders_contractcurtain)
  └── fields: accessory_name, quantity, color, notes ✅
```

---

## 🔄 APIs التقنية

### Wizard Item Management

#### إضافة عنصر
```python
POST /orders/wizard/item/add/
Content-Type: application/json

{
    "product_id": 123,
    "quantity": 4.5,
    "unit_price": 150.00,
    "discount_percentage": 10.0,
    "item_type": "fabric",
    "notes": "ملاحظات"
}

Response:
{
    "success": true,
    "item": {
        "id": 456,
        "product_name": "قماش شيفون",
        "quantity": 4.5,
        "unit_price": 150.00,
        "total_price": 675.00,
        "discount_amount": 67.50,
        "final_price": 607.50
    },
    "totals": {
        "subtotal": 675.00,
        "total_discount": 67.50,
        "final_total": 607.50,
        "remaining": 607.50
    }
}
```

### Contract Curtain Management

#### إضافة ستارة مع أقمشة وإكسسوارات
```python
POST /orders/wizard/curtain/add/
Content-Type: application/json

{
    "room_name": "غرفة المعيشة",
    "width": 3.5,
    "height": 2.8,
    "installation_type": "wall_gypsum",
    "curtain_box_width": 30,      # optional
    "curtain_box_depth": 25,      # optional
    "fabrics": [
        {
            "type": "light",          # light/heavy/blackout/additional
            "name": "شيفون أبيض",
            "item_id": 123,          # DraftOrderItem.id
            "meters": 10.5,
            "pieces": 2,
            "tailoring": "tape",      # rings/tape/snap/etc.
            "notes": "ملاحظات القماش"  ⭐ جديد
        },
        {
            "type": "heavy",
            "name": "قماش مخمل",
            "item_id": 124,
            "meters": 8.0,
            "pieces": 1,
            "tailoring": "rings",
            "notes": "لون غامق"  ⭐
        }
    ],
    "accessories": [
        {
            "name": "مجرى ألومنيوم",
            "quantity": 2,
            "color": "فضي",
            "notes": "ملاحظات الإكسسوار"  ✅
        },
        {
            "name": "كوابل حديد",
            "quantity": 6,
            "color": "أسود",
            "notes": "مقاومة للصدأ"  ✅
        }
    ]
}

Response:
{
    "success": true,
    "message": "تم إضافة الستارة بنجاح",
    "curtain": {
        "id": 789,
        "room_name": "غرفة المعيشة",
        "width": 3.5,
        "height": 2.8,
        "fabrics_count": 2,
        "accessories_count": 2
    }
}
```

#### جلب بيانات ستارة للتعديل
```python
GET /orders/wizard/curtain/789/edit/

Response:
{
    "success": true,
    "curtain": {
        "id": 789,
        "room_name": "غرفة المعيشة",
        "width": 3.5,
        "height": 2.8,
        "installation_type": "wall_gypsum",
        "curtain_box_width": 30,
        "curtain_box_depth": 25,
        "fabrics": [
            {
                "type": "light",
                "type_display": "خفيف",
                "name": "شيفون أبيض",
                "item_id": "123",
                "meters": 10.5,
                "pieces": 2,
                "tailoring": "tape",
                "tailoring_display": "شريط",
                "notes": "ملاحظات القماش"  ⭐
            }
        ],
        "accessories": [
            {
                "name": "مجرى ألومنيوم",
                "quantity": 2,
                "color": "فضي",
                "notes": "ملاحظات الإكسسوار"  ✅
            }
        ]
    }
}
```

#### تعديل ستارة
```python
POST /orders/wizard/curtain/789/edit/
Content-Type: application/json

{
    "room_name": "غرفة النوم الرئيسية",
    "width": 4.0,
    "height": 3.0,
    "installation_type": "ceiling_concrete",
    "fabrics": [...],  # نفس تنسيق الإضافة
    "accessories": [...]
}

Response:
{
    "success": true,
    "message": "تم تعديل الستارة بنجاح",
    "curtain": {...}
}
```

#### حذف ستارة
```python
POST /orders/wizard/curtain/789/remove/

Response:
{
    "success": true,
    "message": "تم حذف الستارة بنجاح"
}
```

### Wizard Finalization

#### تحويل المسودة لطلب نهائي
```python
POST /orders/wizard/finalize/

Response:
{
    "success": true,
    "message": "تم إنشاء الطلب بنجاح",
    "order_id": 1234,
    "order_number": "ORD-2025-001234",
    "redirect_url": "/orders/order/ORD-2025-001234/"
}
```

**العملية التلقائية:**
1. إنشاء `Order` من `DraftOrder`
2. نسخ `DraftOrderItem` إلى `OrderItem`
3. تحديث `ContractCurtain.order` ومسح `draft_order`
4. تحديث `CurtainFabric.order_item` ومسح `draft_order_item`
5. نسخ ملف العقد (إن وجد)
6. إنشاء `Payment` إذا كان `paid_amount > 0`
7. تحديد `draft.is_completed = True`

---

## 🔍 Data Validation

### في CurtainFabric.clean()

```python
def clean(self):
    """التحقق من صحة البيانات"""
    from django.core.exceptions import ValidationError
    errors = {}
    
    # للطلبات النهائية
    if self.order_item and self.meters:
        used_total = CurtainFabric.objects.filter(
            order_item=self.order_item
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('meters')
        )['total'] or 0
        
        available = self.order_item.quantity - used_total
        
        if self.meters > available:
            errors['meters'] = f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح ({available}م)'
    
    # للمسودات
    if self.draft_order_item and self.meters:
        used_total = CurtainFabric.objects.filter(
            draft_order_item=self.draft_order_item
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('meters')
        )['total'] or 0
        
        available = self.draft_order_item.quantity - used_total
        
        if self.meters > available:
            errors['meters'] = f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح ({available}م)'
    
    if errors:
        raise ValidationError(errors)
```

---

## 📊 Query Optimization

### في Wizard Views

```python
# wizard_step_5_contract
def wizard_step_5_contract(request, draft):
    # جلب الستائر مع العلاقات
    curtains = ContractCurtain.objects.filter(
        draft_order=draft
    ).prefetch_related(
        'fabrics',
        'accessories'
    ).order_by('sequence')
    
    # جلب عناصر الفاتورة مع المنتجات
    order_items = draft.items.filter(
        item_type__in=['fabric', 'product']
    ).select_related('product')
    
    # حساب الكميات المستخدمة
    items_with_usage = []
    for item in order_items:
        used = CurtainFabric.objects.filter(
            curtain__draft_order=draft,
            draft_order_item=item
        ).aggregate(total=models.Sum('meters'))['total'] or 0
        
        items_with_usage.append({
            'id': item.id,
            'name': item.product.name,
            'total_quantity': float(item.quantity),
            'used_quantity': float(used),
            'available_quantity': float(item.quantity - used),
        })
```

### في Contract Views

```python
# view_contract_template
def view_contract_template(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # جلب الستائر مع جميع العلاقات
    curtains = ContractCurtain.objects.filter(
        order=order
    ).prefetch_related(
        'fabrics__order_item__product',
        'fabrics__draft_order_item__product',
        'accessories'
    ).order_by('sequence')
    
    return render(request, 'orders/contract_template.html', {
        'order': order,
        'curtains': curtains
    })
```

---

## 🎨 Frontend Integration

### JavaScript لإضافة ستارة (من step5_contract.html)

```javascript
function addCurtain() {
    const formData = {
        room_name: $('#room_name').val(),
        width: parseFloat($('#width').val()),
        height: parseFloat($('#height').val()),
        installation_type: $('#installation_type').val(),
        curtain_box_width: $('#curtain_box_width').val() || null,
        curtain_box_depth: $('#curtain_box_depth').val() || null,
        fabrics: getFabricsData(),  // قائمة الأقمشة مع الملاحظات
        accessories: getAccessoriesData()  // قائمة الإكسسوارات مع الملاحظات
    };
    
    $.ajax({
        url: '/orders/wizard/curtain/add/',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.success) {
                showSuccess(response.message);
                loadCurtains();  // إعادة تحميل قائمة الستائر
                resetForm();
            }
        },
        error: function(xhr) {
            const response = xhr.responseJSON;
            showError(response.message || 'حدث خطأ');
        }
    });
}

function getFabricsData() {
    const fabrics = [];
    $('.fabric-row').each(function() {
        fabrics.push({
            type: $(this).find('.fabric-type').val(),
            name: $(this).find('.fabric-name').val(),
            item_id: $(this).find('.fabric-item').val(),
            meters: parseFloat($(this).find('.fabric-meters').val()),
            pieces: parseInt($(this).find('.fabric-pieces').val()),
            tailoring: $(this).find('.fabric-tailoring').val(),
            notes: $(this).find('.fabric-notes').val()  // ⭐ جديد
        });
    });
    return fabrics;
}

function getAccessoriesData() {
    const accessories = [];
    $('.accessory-row').each(function() {
        accessories.push({
            name: $(this).find('.acc-name').val(),
            quantity: parseInt($(this).find('.acc-qty').val()),
            color: $(this).find('.acc-color').val(),
            notes: $(this).find('.acc-notes').val()  // ✅
        });
    });
    return accessories;
}
```

---

## 🔒 Permissions & Security

### في wizard_views.py

```python
@login_required
def wizard_step(request, step):
    """التحقق من الصلاحيات والوصول"""
    
    # الحصول على المسودة
    draft = DraftOrder.objects.filter(
        created_by=request.user,
        is_completed=False
    ).order_by('-updated_at').first()
    
    # التحقق من إمكانية الوصول للخطوة
    if not draft.can_access_step(step):
        messages.warning(request, 'يجب إكمال الخطوات السابقة أولاً')
        return redirect('orders:wizard_step', step=draft.current_step)
    
    # توجيه للدالة المناسبة
    return wizard_step_X(request, draft)

def can_access_step(self, step_number):
    """التحقق من إمكانية الوصول لخطوة معينة"""
    if step_number == 1:
        return True
    return (step_number - 1) in self.completed_steps
```

### في wizard_delete_draft

```python
@login_required
@require_http_methods(["POST"])
def wizard_delete_draft(request, draft_id):
    """حذف مسودة - مع التحقق من الصلاحيات"""
    draft = get_object_or_404(DraftOrder, id=draft_id)
    
    # التحقق من الصلاحيات
    if not (request.user == draft.created_by or 
            request.user.is_superuser or 
            request.user.groups.filter(name__in=['مدير نظام', 'مدير عام']).exists()):
        messages.error(request, 'ليس لديك صلاحية لحذف هذه المسودة')
        return redirect('orders:wizard_drafts_list')
    
    draft.delete()
    messages.success(request, 'تم حذف المسودة بنجاح')
    return redirect('orders:wizard_drafts_list')
```

---

## 🧪 Testing Guide

### Test Cases الرئيسية

#### 1. إضافة قماش بملاحظات
```python
def test_add_fabric_with_notes():
    curtain = ContractCurtain.objects.create(
        draft_order=draft,
        room_name="غرفة النوم",
        width=3.5,
        height=2.8
    )
    
    fabric = CurtainFabric.objects.create(
        curtain=curtain,
        draft_order_item=draft_item,
        fabric_type='light',
        fabric_name='شيفون',
        meters=10,
        pieces=2,
        notes='ملاحظات اختبارية'
    )
    
    assert fabric.notes == 'ملاحظات اختبارية'
    assert curtain.fabrics.count() == 1
```

#### 2. التحقق من الكميات
```python
def test_fabric_quantity_validation():
    # إضافة عنصر بكمية 10 متر
    draft_item = DraftOrderItem.objects.create(
        draft_order=draft,
        product=fabric_product,
        quantity=10
    )
    
    curtain = ContractCurtain.objects.create(draft_order=draft, ...)
    
    # إضافة قماش بكمية 12 متر (أكثر من المتاح)
    fabric = CurtainFabric(
        curtain=curtain,
        draft_order_item=draft_item,
        meters=12
    )
    
    with pytest.raises(ValidationError):
        fabric.full_clean()
```

#### 3. نقل الستائر عند الإنهاء
```python
def test_wizard_finalize_transfers_curtains():
    # إضافة ستارة للمسودة
    curtain = ContractCurtain.objects.create(
        draft_order=draft,
        room_name="صالة",
        width=4,
        height=3
    )
    
    # إنهاء الويزارد
    response = client.post('/orders/wizard/finalize/')
    
    # التحقق
    order = Order.objects.get(id=response.json()['order_id'])
    curtain.refresh_from_db()
    
    assert curtain.order == order
    assert curtain.draft_order is None
```

---

## 📦 Dependencies

```python
# requirements.txt (relevant parts)
Django>=5.2.6
Pillow>=10.0.0  # للصور
reportlab>=4.0.0  # لتوليد PDF
weasyprint>=60.0  # بديل لتوليد PDF
django-crispy-forms>=2.0  # للنماذج
```

---

## 🔧 Configuration

### settings.py

```python
# Media Files للعقود والصور
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Contract Template Settings (optional)
CONTRACT_TEMPLATE_SETTINGS = {
    'DEFAULT_TEMPLATE_ID': 1,
    'COMPANY_NAME': 'شركتك',
    'COMPANY_LOGO': '/static/images/logo.png',
    'DEFAULT_COLORS': {
        'primary': '#a67c52',
        'secondary': '#2980b9',
        'accent': '#f39c12'
    }
}
```

---

## 🐛 Common Issues & Solutions

### Issue 1: الكمية المستخدمة أكبر من المتاحة
**Error**: `الكمية المطلوبة (15م) أكبر من المتاح (10م)`

**Solution**:
- التحقق من `DraftOrderItem.quantity`
- حساب إجمالي الكميات المستخدمة في جميع الستائر
- تعديل الكمية في الفاتورة أو تقليل الكمية في القماش

### Issue 2: الستائر لا تظهر في العقد النهائي
**Cause**: لم يتم نقل الستائر بشكل صحيح في `wizard_finalize`

**Solution**:
```python
# في wizard_finalize
curtains = ContractCurtain.objects.filter(draft_order=draft)
for curtain in curtains:
    curtain.order = order
    curtain.draft_order = None
    curtain.save(update_fields=['order', 'draft_order'])
```

### Issue 3: الملاحظات لا تظهر في القالب
**Cause**: القالب لا يحتوي على `{{ fabric.notes }}`

**Solution**: التحقق من وجود:
```html
{% if fabric.notes %}
<div class="fabric-notes">
    <strong>ملاحظات:</strong> {{ fabric.notes }}
</div>
{% endif %}
```

---

## 📝 Code Examples

### مثال: إنشاء طلب كامل برمجياً

```python
from orders.wizard_models import DraftOrder, DraftOrderItem
from orders.contract_models import ContractCurtain, CurtainFabric, CurtainAccessory
from decimal import Decimal

# إنشاء مسودة
draft = DraftOrder.objects.create(
    created_by=user,
    customer=customer,
    branch=branch,
    salesperson=salesperson,
    selected_type='installation',
    current_step=1
)

# إضافة عناصر
item1 = DraftOrderItem.objects.create(
    draft_order=draft,
    product=fabric_product,
    quantity=Decimal('20.0'),
    unit_price=Decimal('150.00'),
    item_type='fabric'
)

item2 = DraftOrderItem.objects.create(
    draft_order=draft,
    product=accessory_product,
    quantity=Decimal('5'),
    unit_price=Decimal('80.00'),
    item_type='accessory'
)

# حساب المجاميع
draft.calculate_totals()

# إنشاء ستارة
curtain = ContractCurtain.objects.create(
    draft_order=draft,
    sequence=1,
    room_name='غرفة المعيشة',
    width=Decimal('3.5'),
    height=Decimal('2.8'),
    installation_type='wall_gypsum'
)

# إضافة أقمشة
CurtainFabric.objects.create(
    curtain=curtain,
    draft_order_item=item1,
    fabric_type='light',
    fabric_name='شيفون أبيض',
    pieces=2,
    meters=Decimal('10.0'),
    tailoring_type='tape',
    notes='قماش خفيف شفاف',
    sequence=1
)

CurtainFabric.objects.create(
    curtain=curtain,
    draft_order_item=item1,
    fabric_type='heavy',
    fabric_name='مخمل بني',
    pieces=1,
    meters=Decimal('8.0'),
    tailoring_type='rings',
    notes='قماش ثقيل عازل للضوء',
    sequence=2
)

# إضافة إكسسوارات
CurtainAccessory.objects.create(
    curtain=curtain,
    accessory_name='مجرى ألومنيوم مزدوج',
    quantity=1,
    color='فضي',
    notes='طول 3.5 متر'
)

CurtainAccessory.objects.create(
    curtain=curtain,
    accessory_name='كوابل حديد',
    quantity=4,
    color='أسود',
    notes='مع قواعد تثبيت'
)

# تحديد الخطوات كمكتملة
for step in [1, 2, 3, 4, 5]:
    draft.mark_step_complete(step)

draft.current_step = 6
draft.save()

# تحويل لطلب نهائي (programmatically)
order = Order.objects.create(
    customer=draft.customer,
    salesperson=draft.salesperson,
    branch=draft.branch,
    # ... باقي الحقول
)

# نقل الستائر
curtain.order = order
curtain.draft_order = None
curtain.save()

# تحديد المسودة كمكتملة
draft.is_completed = True
draft.final_order = order
draft.save()

print(f'تم إنشاء الطلب: {order.order_number}')
```

---

## 🚀 Performance Tips

1. **استخدم select_related و prefetch_related**:
```python
curtains = ContractCurtain.objects.filter(
    order=order
).select_related(
    'order', 'draft_order'
).prefetch_related(
    'fabrics__order_item__product',
    'fabrics__draft_order_item__product',
    'accessories'
)
```

2. **استخدم only() للحقول المطلوبة فقط**:
```python
drafts = DraftOrder.objects.filter(
    is_completed=False
).only(
    'id', 'order_number', 'customer__name', 'current_step'
)
```

3. **استخدم defer() لتأجيل الحقول الكبيرة**:
```python
drafts = DraftOrder.objects.all().defer('wizard_state', 'notes')
```

---

## 📊 Monitoring & Logging

```python
import logging

logger = logging.getLogger(__name__)

def wizard_add_curtain(request):
    try:
        # ... كود الإضافة
        logger.info(f"Curtain added: {curtain.id} - {curtain.room_name}")
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error adding curtain: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
```

---

**آخر تحديث**: 2025-11-22  
**للاستفسارات الفنية**: راجع الملفات المصدرية أو التوثيق الشامل
