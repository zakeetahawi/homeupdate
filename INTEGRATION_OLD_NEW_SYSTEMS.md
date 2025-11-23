# 🔄 دمج النظام القديم مع ويزارد العقود الإلكترونية

## نظرة عامة

هذا الدليل يشرح كيفية دمج واجهة النظام القديم لإدارة الستائر  
`http://127.0.0.1:8000/orders/order/{id}/contract/curtains/`  
مع نظام الويزارد الجديد.

---

## 🎯 الهدف

دمج كامل بين:
- ✅ النظام القديم: صفحة إدارة الستائر للطلبات المُكتملة
- ✅ الويزارد الجديد: صفحة إضافة الستائر في الخطوة 5

---

## 📊 مقارنة النظامين

| الميزة | النظام القديم | الويزارد الجديد |
|--------|---------------|-----------------|
| **الاستخدام** | طلبات مُكتملة | مسودات الطلبات |
| **المودل** | `Order` | `DraftOrder` |
| **URL** | `/order/{id}/contract/curtains/` | `/wizard/step/5/` |
| **الستائر** | `ContractCurtain` (order) | `ContractCurtain` (draft_order) |
| **الحفظ** | حذف واستبدال | إضافة تدريجية |
| **الحالة** | نهائي | قيد الإنشاء |

---

## 🔧 التعديلات المطلوبة

### 1. توحيد واجهة المستخدم ✅

**الملف:** `orders/templates/orders/wizard/step5_contract.html`

**ما تم:**
- ✅ استخدام نفس الأنماط CSS من النظام القديم
- ✅ نفس هيكل البطاقات (curtain-card)
- ✅ نفس طريقة عرض الأقمشة
- ✅ نفس نظام الألوان

**ما يُمكن تحسينه:**
```html
<!-- استيراد الأنماط من النظام القديم -->
<link rel="stylesheet" href="{% static 'css/contract-curtains.css' %}">

<!-- أو نسخ الأنماط مباشرة -->
{% include 'orders/contract_curtains_styles.html' %}
```

---

### 2. توحيد نظام الأقمشة ✅

**المودل:** `orders/contract_models.py` → `CurtainFabric`

**الحالي:**
```python
class CurtainFabric(models.Model):
    curtain = ForeignKey(ContractCurtain)
    order_item = ForeignKey(OrderItem)  # ✅ تم إضافته
    fabric_type = CharField()           # light, heavy, blackout
    meters = DecimalField()
    tailoring_type = CharField()
```

**مثالي:**
- ✅ نفس الحقول في النظامين
- ✅ نفس الخيارات (TAILORING_TYPES)
- ✅ نفس التحقق من الكميات

---

### 3. توحيد نظام الإكسسوارات ✅

**المودل:** `orders/contract_models.py` → `CurtainAccessory`

**الحالي:**
```python
class CurtainAccessory(models.Model):
    curtain = ForeignKey(ContractCurtain)
    accessory_name = CharField()
    quantity = IntegerField()
    notes = TextField()
```

**مثالي:**
- ✅ نفس البنية البسيطة
- ✅ مرونة في أسماء الإكسسوارات

---

## 🎨 دمج الواجهة

### الخطوة 1: استخراج الأنماط المشتركة

**إنشاء ملف:** `orders/templates/orders/includes/curtain_styles.html`

```html
<style>
    /* الأنماط المشتركة بين النظامين */
    .curtain-card { ... }
    .fabric-section { ... }
    .accessories-grid { ... }
    /* ... إلخ */
</style>
```

**الاستخدام:**
```django
{# في step5_contract.html #}
{% include 'orders/includes/curtain_styles.html' %}

{# في contract_curtains_manage.html #}
{% include 'orders/includes/curtain_styles.html' %}
```

---

### الخطوة 2: توحيد قوالب عرض الستائر

**إنشاء ملف:** `orders/templates/orders/includes/curtain_card.html`

```django
{# قالب قابل لإعادة الاستخدام لعرض بطاقة ستارة #}
<div class="curtain-card" data-curtain-id="{{ curtain.id }}">
    <div class="curtain-header">
        <span>{{ curtain.room_name }}</span>
        {% if show_delete_button %}
        <button type="button" class="btn btn-sm btn-danger" 
                onclick="removeCurtain({{ curtain.id }})">
            <i class="fas fa-trash"></i> حذف
        </button>
        {% endif %}
    </div>
    
    <div class="curtain-body">
        <!-- المقاسات -->
        <div class="measurements">
            {{ curtain.width }}م × {{ curtain.height }}م
        </div>
        
        <!-- الأقمشة -->
        {% if curtain.fabrics.exists %}
        <div class="fabrics-section">
            {% for fabric in curtain.fabrics.all %}
                {% include 'orders/includes/fabric_item.html' with fabric=fabric %}
            {% endfor %}
        </div>
        {% endif %}
        
        <!-- الإكسسوارات -->
        {% if curtain.accessories.exists %}
        <div class="accessories-section">
            {% for accessory in curtain.accessories.all %}
                {% include 'orders/includes/accessory_item.html' with accessory=accessory %}
            {% endfor %}
        </div>
        {% endif %}
    </div>
</div>
```

**الاستخدام:**
```django
{# في أي مكان #}
{% include 'orders/includes/curtain_card.html' with curtain=curtain show_delete_button=True %}
```

---

### الخطوة 3: توحيد JavaScript

**إنشاء ملف:** `orders/static/js/curtain-management.js`

```javascript
/**
 * مكتبة JavaScript مشتركة لإدارة الستائر
 */

class CurtainManager {
    constructor(options) {
        this.isDraft = options.isDraft || false;
        this.orderId = options.orderId;
        this.draftId = options.draftId;
        this.csrfToken = options.csrfToken;
    }
    
    async addCurtain(curtainData) {
        const url = this.isDraft 
            ? '/orders/wizard/add-curtain/'
            : `/orders/order/${this.orderId}/contract/curtains/add/`;
            
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(curtainData)
        });
        
        return await response.json();
    }
    
    async removeCurtain(curtainId) {
        const url = this.isDraft
            ? `/orders/wizard/curtain/${curtainId}/remove/`
            : `/orders/order/${this.orderId}/contract/curtains/${curtainId}/remove/`;
            
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.csrfToken
            }
        });
        
        return await response.json();
    }
    
    // ... المزيد من الدوال المشتركة
}

// الاستخدام
const manager = new CurtainManager({
    isDraft: true,  // أو false للنظام القديم
    draftId: 123,
    csrfToken: getCookie('csrftoken')
});
```

---

## 🔗 إنشاء روابط بين النظامين

### في صفحة الطلب المُكتمل:

```django
{# orders/templates/orders/order_detail.html #}

{% if order.contract_type == 'electronic' %}
<div class="contract-section">
    <h4>العقد الإلكتروني</h4>
    
    <!-- الستائر الموجودة -->
    {% for curtain in order.contract_curtains.all %}
        {% include 'orders/includes/curtain_card.html' with curtain=curtain show_delete_button=False %}
    {% endfor %}
    
    <!-- زر الإدارة -->
    <a href="{% url 'orders:contract_curtains_manage' order.id %}" 
       class="btn btn-primary">
        <i class="fas fa-edit"></i> إدارة الستائر
    </a>
    
    <!-- توليد PDF -->
    <a href="{% url 'orders:contract_pdf_view' order.id %}" 
       target="_blank" 
       class="btn btn-success">
        <i class="fas fa-file-pdf"></i> عرض العقد PDF
    </a>
</div>
{% endif %}
```

---

### في الويزارد:

```django
{# orders/templates/orders/wizard/step6_review.html #}

{% if draft.contract_type == 'electronic' %}
<div class="contract-preview">
    <h4>معاينة العقد الإلكتروني</h4>
    
    <!-- الستائر المُضافة -->
    {% for curtain in draft.contract_curtains.all %}
        {% include 'orders/includes/curtain_card.html' with curtain=curtain show_delete_button=False %}
    {% endfor %}
    
    <!-- زر التعديل -->
    <a href="{% url 'orders:wizard_step' step=5 %}" 
       class="btn btn-warning">
        <i class="fas fa-edit"></i> تعديل الستائر
    </a>
</div>
{% endif %}
```

---

## 📦 نقل البيانات عند إكمال الطلب

**الملف:** `orders/wizard_views.py` → `wizard_complete()`

**الكود الحالي:**
```python
# نقل الستائر من المسودة إلى الطلب النهائي
curtains = ContractCurtain.objects.filter(draft_order=draft)
for curtain in curtains:
    curtain.order = order
    curtain.draft_order = None
    curtain.save(update_fields=['order', 'draft_order'])
```

**تحسينات مقترحة:**
```python
# نقل مع التحقق والتسجيل
curtains = ContractCurtain.objects.filter(draft_order=draft)
logger.info(f"Transferring {curtains.count()} curtains to order {order.id}")

for curtain in curtains:
    # نقل الستارة
    curtain.order = order
    curtain.draft_order = None
    curtain.save(update_fields=['order', 'draft_order'])
    
    # التحقق من الأقمشة
    fabrics_count = curtain.fabrics.count()
    accessories_count = curtain.accessories.count()
    logger.info(f"  Curtain {curtain.id}: {fabrics_count} fabrics, {accessories_count} accessories")

# تحديث نوع العقد
if curtains.exists():
    order.contract_type = 'electronic'
    order.save(update_fields=['contract_type'])
```

---

## 🎯 خارطة طريق الدمج الكامل

### المرحلة 1: توحيد الواجهة ✅
- [x] استخدام نفس الأنماط CSS
- [x] توحيد بنية HTML
- [ ] إنشاء قوالب مشتركة

### المرحلة 2: توحيد المنطق 🔄
- [x] استخدام نفس المودلات (CurtainFabric, CurtainAccessory)
- [x] نفس التحقق من الكميات
- [ ] دوال JavaScript مشتركة

### المرحلة 3: ربط الأنظمة 📋
- [ ] روابط من صفحة الطلب إلى صفحة الإدارة
- [ ] معاينة في الويزارد
- [x] نقل تلقائي عند الإكمال

### المرحلة 4: التحسينات 🚀
- [ ] تعديل الستائر بعد إكمال الطلب
- [ ] نسخ ستائر من طلب آخر
- [ ] قوالب جاهزة للغرف الشائعة

---

## 🔍 الفرق بين النظامين

### النظام القديم (للطلبات المُكتملة):

**المميزات:**
- ✅ واجهة كاملة ومُجربة
- ✅ حفظ شامل (حذف واستبدال)
- ✅ معاينة فورية

**العيوب:**
- ❌ يتطلب طلب مُكتمل
- ❌ لا يدعم المسودات

---

### الويزارد الجديد (للمسودات):

**المميزات:**
- ✅ إضافة تدريجية
- ✅ تتبع ذكي للكميات
- ✅ منع تجاوز الكميات
- ✅ قائمة منسدلة من الفاتورة

**العيوب:**
- ❌ واجهة أقل تطوراً (حالياً)
- ❌ يتطلب إكمال الخطوات

---

## ✅ التوصيات

### للمستخدمين:
1. **للطلبات الجديدة:** استخدم الويزارد (خطوة 5)
2. **للطلبات المُكتملة:** استخدم النظام القديم

### للمطورين:
1. **توحيد تدريجي:** ابدأ بالقوالب المشتركة
2. **اختبار شامل:** تأكد من عمل النقل بشكل صحيح
3. **توثيق الاختلافات:** اذكر أي فروقات بوضوح

---

**آخر تحديث:** 2025-11-22  
**الحالة:** دمج جزئي - جاهز للتحسين ✅
