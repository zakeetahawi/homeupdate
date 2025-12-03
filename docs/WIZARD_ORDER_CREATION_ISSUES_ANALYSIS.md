# تحليل شامل لمشاكل ويزارد إنشاء الطلبات

**التاريخ:** 2025-11-28  
**الحالة:** تحليل مفصّل للمشاكل وخطة الإصلاح

---

## 📋 فهم النظام الكامل

### البنية العامة لويزارد إنشاء الطلبات

#### الخطوات الرئيسية:
1. **الخطوة 1:** البيانات الأساسية (العميل، الفرع، البائع)
2. **الخطوة 2:** نوع الطلب
3. **الخطوة 3:** عناصر الفاتورة (أقمشة، إكسسوارات، منتجات)
4. **الخطوة 4:** الفاتورة والدفع
5. **الخطوة 5:** العقد الإلكتروني (إضافة الستائر مع تفاصيلها)
6. **الخطوة 6:** المراجعة والتأكيد النهائي

#### النماذج المستخدمة:

```
DraftOrder (المسودة الرئيسية)
  ├── DraftOrderItem[] (عناصر الفاتورة)
  │     ├── product (المنتج)
  │     ├── quantity (الكمية)
  │     └── item_type (fabric/accessory/product)
  │
  └── ContractCurtain[] (ستائر العقد)
        ├── room_name, width, height
        ├── installation_type
        ├── curtain_box_width, curtain_box_depth
        │
        ├── CurtainFabric[] (الأقمشة)
        │     ├── draft_order_item (FK → DraftOrderItem)
        │     ├── fabric_type (light/heavy/blackout/additional)
        │     ├── meters, pieces
        │     └── tailoring_type
        │
        └── CurtainAccessory[] (الإكسسوارات)
              ├── draft_order_item (FK → DraftOrderItem)
              ├── accessory_name
              ├── quantity, count, size
              └── color
```

---

## 🔴 المشاكل المكتشفة

### **المشكلة 1: عرض الكمية المتبقية من القماش بشكل خاطئ**

#### الوصف:
عند إضافة قماش للستارة من الفاتورة:
- إذا كانت الكمية المطلوبة **10.5 متر**
- يعرض النظام أن المتبقي **10 متر** فقط (يتجاهل الجزء العشري)
- عند كتابة 10.5 يدوياً، لا يتم قبولها

#### السبب الجذري:

**1. مشكلة في حساب الكمية المستخدمة (Backend):**

في `/home/zakee/homeupdate/orders/wizard_views.py` - السطر 644-650:

```python
# حساب الكميات المتاحة لكل عنصر
items_with_usage = []
for item in order_items:
    used = CurtainFabric.objects.filter(
        order_item__isnull=False,  # ❌ خطأ: يبحث عن order_item بدلاً من draft_order_item
        curtain__draft_order=draft,
        order_item__product=item.product  # ❌ خطأ: يستخدم order_item
    ).aggregate(total=models.Sum('meters'))['total'] or 0
```

**المشكلة:** الاستعلام يبحث عن `order_item` (الطلبات النهائية) بدلاً من `draft_order_item` (المسودات)!

**النتيجة:** لا يتم احتساب الكميات المستخدمة في الستائر المضافة في المسودة، لذلك يعرض دائماً الكمية الكاملة.

**2. مشكلة في عرض الكمية (Frontend):**

في `/home/zakee/homeupdate/orders/templates/orders/wizard/step5_contract.html` - السطر 322:

```html
<option value="{{ item.id }}" data-available="{{ item.quantity }}" data-name="{{ item.product.name }}">
    {{ item.product.name }} - متوفر: <span class="available-qty-{{ item.id }}">{{ item.quantity }}</span> متر
</option>
```

**المشكلة:** يعرض `item.quantity` مباشرة من قاعدة البيانات دون تنسيق.

**3. مشكلة في التنسيق (JavaScript):**

في السطر 632:

```javascript
const qtySpan = document.querySelector(`.available-qty-${itemId}`);
if (qtySpan) {
    qtySpan.textContent = remaining.toFixed(3).replace(/\.?0+$/, '');  // ✅ هذا صحيح
}
```

الكود صحيح، لكن المشكلة في البيانات القادمة من السيرفر.

**4. مشكلة في التحقق من الصحة:**

في `contract_models.py` - السطر 764-782:

```python
if self.draft_order_item and self.meters:
    used_total = CurtainFabric.objects.filter(
        draft_order_item=self.draft_order_item
    ).exclude(pk=self.pk).aggregate(
        total=models.Sum('meters')
    )['total'] or 0
    
    available = self.draft_order_item.quantity - used_total
    
    # تحذير فقط، لا نمنع الحفظ في وضع المسودة ❌
    if self.meters > available:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح...')
        # لا نضيف للـ errors في وضع المسودة - فقط تحذير ❌
```

**المشكلة:** النظام يسمح بتجاوز الكميات في المسودات! يجب أن يمنع الحفظ.

---

### **المشكلة 2: عدم حفظ تفاصيل الستائر عند العودة للدرافت**

#### الوصف:
- عند ترك الويزارد في مرحلة إنشاء العقد (الخطوة 5)
- وإضافة ستارة وتفاصيلها
- ثم الخروج من الويزارد
- عند العودة: **تفاصيل الستائر لا تبقى محفوظة**

#### السبب الجذري:

**1. آلية الحفظ:**

عند إضافة ستارة، يتم الحفظ فوراً في قاعدة البيانات عبر:
- `wizard_add_curtain` → يحفظ `ContractCurtain` + `CurtainFabric` + `CurtainAccessory`

**2. الستائر تُحفظ بالفعل!**

الكود في `wizard_views.py` - السطر 1023-1200 يحفظ البيانات مباشرة في قاعدة البيانات.

**3. المشكلة المحتملة:**

عند العودة للويزارد:
- في `wizard_step` - السطر 143-172
- يتم جلب المسودة من قاعدة البيانات
- **يجب** أن تظهر الستائر المحفوظة

**التحقق المطلوب:**
- هل هناك مشكلة في جلب المسودة الصحيحة؟
- هل يتم إنشاء مسودة جديدة بدلاً من استخدام القديمة؟
- هل هناك مشكلة في العلاقة بين `ContractCurtain` و `DraftOrder`؟

**الاحتمال الأكبر:**
قد يكون هناك تضارب في `wizard_draft_id` في الجلسة، أو يتم إنشاء مسودة جديدة عن طريق الخطأ.

---

### **المشكلة 3: عدم إعادة توفر الكميات عند إزالة وإعادة إضافة الستارة**

#### الوصف:
- عند إزالة ستارة تحتوي على أقمشة وإكسسوارات
- ثم إعادة إضافة ستارة جديدة بشكل صحيح
- الكميات لا تعود متاحة للاستهلاك

#### السبب الجذري:

**1. آلية الحذف:**

في `wizard_views.py` - السطر 1519-1549:

```python
@login_required
@require_http_methods(["POST"])
@transaction.atomic
def wizard_remove_curtain(request, curtain_id):
    """حذف ستارة من العقد الإلكتروني"""
    curtain = get_object_or_404(
        ContractCurtain,
        id=curtain_id,
        draft_order=draft
    )
    curtain.delete()  # ✅ الحذف cascade - يحذف الأقمشة والإكسسوارات
```

الحذف يعمل بشكل صحيح - يحذف الستارة وكل ما يرتبط بها (cascade delete).

**2. مشكلة في إعادة الحساب (Frontend):**

في `step5_contract.html` - السطر 1407-1442:

```javascript
function removeCurtain(curtainId) {
    fetch(`{% url 'orders:wizard_remove_curtain' 0 %}`.replace('0', curtainId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.querySelector(`[data-curtain-id="${curtainId}"]`).remove();
            
            // ❌ المشكلة: لا يتم إعادة تحميل الصفحة!
            // ❌ البيانات في fabricUsageTracker تبقى قديمة
            
            if (document.querySelectorAll('.curtain-card').length === 0) {
                document.getElementById('curtains-list').innerHTML = `...`;
            }
        }
    });
}
```

**المشكلة:**
- عند حذف الستارة، يتم إزالتها من DOM فقط
- `fabricUsageTracker` في JavaScript لا يتم تحديثه
- الكميات المستخدمة تبقى محسوبة رغم حذف الستارة

**الحل المطلوب:**
إعادة تحميل الصفحة بعد الحذف، أو إعادة حساب `fabricUsageTracker`.

**3. مشكلة إضافية في حساب الكميات عند تحميل الصفحة:**

في السطر 543-574:

```javascript
// Calculate used quantities from existing curtain fabrics
function calculateUsedQuantities() {
    // Reset usage
    for (let key in fabricUsageTracker) {
        fabricUsageTracker[key].used = 0;
    }
    
    // Add from existing curtains on the page
    {% for curtain in curtains %}
        {% for fabric in curtain.fabrics.all %}
            {% if fabric.draft_order_item_id %}
                if (fabricUsageTracker['{{ fabric.draft_order_item_id }}']) {
                    fabricUsageTracker['{{ fabric.draft_order_item_id }}'].used += parseFloat('{{ fabric.meters }}');
                }
            {% endif %}
        {% endfor %}
        
        {% for accessory in curtain.accessories.all %}
            {% if accessory.draft_order_item_id %}
                if (fabricUsageTracker['{{ accessory.draft_order_item_id }}']) {
                    fabricUsageTracker['{{ accessory.draft_order_item_id }}'].used += parseFloat('{{ accessory.quantity }}');
                }
            {% endif %}
        {% endfor %}
    {% endfor %}
```

**هذا الكود صحيح!** يحسب من البيانات الموجودة على الصفحة.

**المشكلة:** عند حذف الستارة من DOM، Django template tags لا تتغير (لأنها server-side).

---

## 🛠️ خطة الإصلاح الشاملة

### **الإصلاح 1: تصحيح حساب الكميات المستخدمة في Backend**

**الملف:** `orders/wizard_views.py`  
**الدالة:** `wizard_step_5_contract`  
**السطور:** 644-656

**التغيير:**

```python
# ❌ الكود القديم (خطأ):
for item in order_items:
    used = CurtainFabric.objects.filter(
        order_item__isnull=False,  # يبحث في الطلبات النهائية
        curtain__draft_order=draft,
        order_item__product=item.product
    ).aggregate(total=models.Sum('meters'))['total'] or 0

# ✅ الكود الجديد (صحيح):
for item in order_items:
    # حساب الكمية المستخدمة من الأقمشة
    used_fabrics = CurtainFabric.objects.filter(
        draft_order_item=item,  # البحث في عناصر المسودة
        curtain__draft_order=draft
    ).aggregate(total=models.Sum('meters'))['total'] or Decimal('0')
    
    # حساب الكمية المستخدمة من الإكسسوارات
    used_accessories = CurtainAccessory.objects.filter(
        draft_order_item=item,
        curtain__draft_order=draft
    ).aggregate(total=models.Sum('quantity'))['total'] or Decimal('0')
    
    # إجمالي المستخدم
    used = used_fabrics + used_accessories
    
    items_with_usage.append({
        'id': item.id,
        'name': item.product.name,
        'total_quantity': float(item.quantity),
        'used_quantity': float(used),
        'available_quantity': float(item.quantity - used),
    })
```

---

### **الإصلاح 2: منع تجاوز الكميات في المسودات**

**الملف:** `orders/contract_models.py`  
**الدالة:** `CurtainFabric.clean()`  
**السطور:** 764-782

**التغيير:**

```python
# ❌ الكود القديم:
if self.draft_order_item and self.meters:
    used_total = CurtainFabric.objects.filter(
        draft_order_item=self.draft_order_item
    ).exclude(pk=self.pk).aggregate(
        total=models.Sum('meters')
    )['total'] or 0
    
    available = self.draft_order_item.quantity - used_total
    
    # تحذير فقط، لا نمنع الحفظ
    if self.meters > available:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'الكمية المطلوبة...')
        # لا نضيف للـ errors - فقط تحذير ❌

# ✅ الكود الجديد:
if self.draft_order_item and self.meters:
    from django.db.models import Sum
    from decimal import Decimal
    
    # حساب ما تم استخدامه من الأقمشة
    used_in_fabrics = CurtainFabric.objects.filter(
        draft_order_item=self.draft_order_item
    ).exclude(pk=self.pk).aggregate(
        total=Sum('meters')
    )['total'] or Decimal('0')
    
    # حساب ما تم استخدامه من الإكسسوارات (من نفس العنصر)
    used_in_accessories = CurtainAccessory.objects.filter(
        draft_order_item=self.draft_order_item
    ).aggregate(
        total=Sum('quantity')
    )['total'] or Decimal('0')
    
    # إجمالي المستخدم
    used_total = used_in_fabrics + used_in_accessories
    available = self.draft_order_item.quantity - used_total
    
    # منع الحفظ إذا تجاوز الكمية المتاحة
    if self.meters > available:
        errors['meters'] = (
            f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح '
            f'({available}م من أصل {self.draft_order_item.quantity}م)'
        )
```

**نفس التغيير في:** `CurtainAccessory.clean()`

---

### **الإصلاح 3: إعادة تحميل الصفحة بعد حذف الستارة**

**الملف:** `orders/templates/orders/wizard/step5_contract.html`  
**الدالة:** `removeCurtain()`  
**السطور:** 1407-1442

**التغيير:**

```javascript
// ❌ الكود القديم:
.then(data => {
    if (data.success) {
        document.querySelector(`[data-curtain-id="${curtainId}"]`).remove();
        
        if (document.querySelectorAll('.curtain-card').length === 0) {
            document.getElementById('curtains-list').innerHTML = `...`;
        }
    }
});

// ✅ الكود الجديد:
.then(data => {
    if (data.success) {
        // إعادة تحميل الصفحة لتحديث الكميات المتاحة
        location.reload();
    } else {
        alert(data.message || 'حدث خطأ أثناء حذف الستارة');
    }
});
```

---

### **الإصلاح 4: تحسين عرض الأرقام العشرية**

**الملف:** `orders/templates/orders/wizard/step5_contract.html`  
**السطر:** 322

**التغيير:**

```django-html
<!-- ❌ الكود القديم: -->
<option value="{{ item.id }}" data-available="{{ item.quantity }}" data-name="{{ item.product.name }}">
    {{ item.product.name }} - متوفر: <span class="available-qty-{{ item.id }}">{{ item.quantity }}</span> متر
</option>

<!-- ✅ الكود الجديد: -->
<option value="{{ item.id }}" data-available="{{ item.quantity }}" data-name="{{ item.product.name }}">
    {{ item.product.name }} - متوفر: <span class="available-qty-{{ item.id }}">{{ item.quantity|floatformat:"-3" }}</span> متر
</option>
```

**ملاحظة:** `floatformat:"-3"` يعرض حتى 3 خانات عشرية ويزيل الأصفار الزائدة.

---

### **الإصلاح 5: التحقق من آلية حفظ المسودات**

**الملف:** `orders/wizard_views.py`  
**الدالة:** `wizard_step`

**التحقق المطلوب:**

1. عند العودة للويزارد، هل يتم جلب المسودة الصحيحة؟
2. هل `session['wizard_draft_id']` محفوظ بشكل صحيح؟
3. هل هناك حالة يتم فيها إنشاء مسودة جديدة بدلاً من استخدام القديمة؟

**الكود الحالي (السطر 143-172):**

```python
draft_id = request.session.get('wizard_draft_id')

if draft_id:
    try:
        draft = DraftOrder.objects.get(pk=draft_id, created_by=request.user)
    except DraftOrder.DoesNotExist:
        draft = None

if not draft:
    draft = DraftOrder.objects.filter(
        created_by=request.user,
        is_completed=False
    ).order_by('-updated_at').first()
    
    if draft:
        request.session['wizard_draft_id'] = draft.pk
```

**هذا الكود صحيح!** لكن قد تكون المشكلة في:
- المستخدم يستخدم متصفح مختلف
- تم حذف الجلسة (session timeout)
- المستخدم يفتح الويزارد من رابط مباشر بدلاً من الاستمرار

**الحل المقترح:**
إضافة رسالة تنبيه للمستخدم عند فتح الويزارد إذا كان لديه مسودات غير مكتملة:

```python
# في wizard_start
existing_drafts = DraftOrder.objects.filter(
    created_by=request.user,
    is_completed=False
).order_by('-updated_at')

if existing_drafts.exists():
    # عرض رسالة: "لديك مسودات غير مكتملة، هل تريد الاستمرار؟"
    pass
```

---

## 📊 ملخص الإصلاحات

### الأولويات:

| # | المشكلة | الخطورة | الإصلاح | الملف |
|---|---------|---------|---------|-------|
| 1 | حساب الكميات خطأ في Backend | 🔴 عالية | تغيير الاستعلام من `order_item` إلى `draft_order_item` | `wizard_views.py` |
| 2 | السماح بتجاوز الكميات في المسودات | 🔴 عالية | تغيير من تحذير إلى خطأ يمنع الحفظ | `contract_models.py` |
| 3 | عدم تحديث الكميات بعد حذف الستارة | 🟠 متوسطة | إعادة تحميل الصفحة بعد الحذف | `step5_contract.html` |
| 4 | عرض الأرقام العشرية | 🟡 منخفضة | استخدام `floatformat` | `step5_contract.html` |
| 5 | مشكلة حفظ الدرافت (تحتاج تحقق) | 🟠 متوسطة | فحص وإضافة رسائل تنبيه | `wizard_views.py` |

---

## ✅ خطوات التنفيذ

1. **النسخ الاحتياطي:**
   ```bash
   cp orders/wizard_views.py orders/wizard_views.py.backup
   cp orders/contract_models.py orders/contract_models.py.backup
   cp orders/templates/orders/wizard/step5_contract.html orders/templates/orders/wizard/step5_contract.html.backup
   ```

2. **تطبيق الإصلاحات بالترتيب:**
   - الإصلاح 1 (Backend - حساب الكميات)
   - الإصلاح 2 (Validation - منع التجاوز)
   - الإصلاح 3 (Frontend - إعادة التحميل)
   - الإصلاح 4 (عرض الأرقام)

3. **الاختبار:**
   - اختبار إضافة قماش بكمية عشرية (10.5)
   - اختبار تجاوز الكمية المتاحة (يجب أن يرفض)
   - اختبار حذف ستارة (يجب أن تعود الكميات)
   - اختبار حفظ درافت والعودة (يجب أن تبقى البيانات)

4. **التوثيق:**
   - تحديث `WIZARD_ORDER_CREATION_README.md`
   - إضافة ملاحظات للمطورين

---

## 🧪 سيناريوهات الاختبار

### **اختبار 1: الكميات العشرية**
```
1. إضافة قماش بكمية 10.5 متر في الفاتورة (الخطوة 3)
2. الانتقال لخطوة العقد (الخطوة 5)
3. إضافة ستارة واختيار القماش
4. التحقق من عرض "متوفر: 10.5 متر" (وليس 10)
5. إضافة 5.5 متر للقماش الخفيف
6. التحقق من عرض "متوفر: 5 متر" المتبقي
7. محاولة إضافة 5.5 متر أخرى (يجب أن يرفض)
```

### **اختبار 2: حذف الستارة**
```
1. إضافة ستارة تستهلك 5 متر من قماش
2. التحقق من عرض "متوفر: 5.5 متر"
3. حذف الستارة
4. التحقق من عودة العرض إلى "متوفر: 10.5 متر"
```

### **اختبار 3: حفظ الدرافت**
```
1. إنشاء طلب جديد حتى الخطوة 5
2. إضافة ستارة كاملة مع أقمشة وإكسسوارات
3. الخروج من الويزارد (إلغاء أو إغلاق)
4. العودة للويزارد (عبر قائمة المسودات)
5. التحقق من وجود الستارة وتفاصيلها
```

---

## 📝 ملاحظات إضافية

### **تحسينات مستقبلية:**

1. **رسائل خطأ أفضل:**
   - عرض رسالة واضحة عند تجاوز الكمية
   - تضمين اسم المنتج والكمية المتاحة

2. **واجهة مستخدم محسّنة:**
   - تلوين العناصر المستنفذة بالأحمر
   - إخفاء الخيارات غير المتاحة

3. **أداء أفضل:**
   - استخدام `select_related` و `prefetch_related`
   - تقليل عدد الاستعلامات

4. **تجربة مستخدم:**
   - حفظ تلقائي للمسودة كل فترة
   - رسالة تأكيد قبل الخروج مع وجود بيانات غير محفوظة

---

**انتهى التحليل** ✅
