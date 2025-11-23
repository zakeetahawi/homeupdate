# نظام الويزارد لإنشاء الطلبات - دليل شامل

## نظرة عامة

تم تنفيذ نظام ويزارد متعدد المراحل (Multi-Step Wizard) لإنشاء الطلبات بطريقة احترافية ومنظمة. يتكون الويزارد من 6 خطوات رئيسية تسهّل عملية إنشاء الطلبات المعقدة.

---

## المراحل الستة للويزارد

### المرحلة 1: البيانات الأساسية
- **الحقول المطلوبة:**
  - العميل (Customer) - اختيار مع Select2
  - الفرع (Branch)
  - البائع (Salesperson)
  - وضع العميل (VIP/عادي)
  - ملاحظات (اختياري)

- **التحقق:**
  - جميع الحقول الأساسية مطلوبة
  - يتم حفظ البيانات في DraftOrder

### المرحلة 2: نوع الطلب
- **أنواع الطلبات المتاحة:**
  1. إكسسوار (Accessory)
  2. تركيب (Installation)
  3. معاينة (Inspection)
  4. تسليم (Tailoring)
  5. منتجات (Products)

- **ميزات:**
  - اختيار نوع واحد فقط
  - واجهة بطاقات تفاعلية (Cards)
  - إظهار/إخفاء حقل المعاينة المرتبطة حسب النوع

### المرحلة 3: عناصر الطلب
- **الوظائف:**
  - إضافة منتجات بالبحث (Select2 + AJAX)
  - تحديد الكمية والسعر
  - إضافة خصم لكل عنصر
  - حساب المجاميع الفورية
  - حذف عناصر

- **المجاميع المحسوبة:**
  - المجموع قبل الخصم (Subtotal)
  - إجمالي الخصم (Total Discount)
  - المجموع النهائي (Final Total)

### المرحلة 4: الفاتورة والدفع
- **تفاصيل الفاتورة:**
  - رقم الفاتورة الرئيسي + 2 إضافية
  - رقم العقد الرئيسي + 2 إضافية

- **معلومات الدفع:**
  - طريقة الدفع (نقدي، بطاقة، تحويل بنكي، تقسيط)
  - المبلغ المدفوع
  - حساب المتبقي تلقائياً
  - ملاحظات الدفع

- **التحقق:**
  - المبلغ المدفوع لا يتجاوز الإجمالي

### المرحلة 5: العقد الإلكتروني (اختياري)
- **إضافة ستائر:**
  - اسم الغرفة
  - العرض والارتفاع (متر)
  - حساب المساحة تلقائياً
  - إضافة أقمشة لكل ستارة
  - إضافة إكسسوارات

- **ميزات:**
  - يمكن تخطي هذه المرحلة
  - مودال لإضافة الستائر
  - حذف وتعديل الستائر

### المرحلة 6: المراجعة والتأكيد
- **عرض شامل:**
  - معلومات العميل والطلب
  - جدول العناصر مع المجاميع
  - تفاصيل الفاتورة والدفع
  - تفاصيل العقد (إن وجد)

- **التأكيد النهائي:**
  - رسالة تأكيد (SweetAlert2)
  - تحويل المسودة إلى طلب نهائي
  - توليد رقم الطلب
  - إنشاء الدفعة (Payment)
  - توجيه لصفحة الطلب

---

## البنية التقنية

### 1. النماذج (Models)

**DraftOrder** - مسودة الطلب الرئيسية
```python
- created_by: المستخدم المنشئ
- current_step: الخطوة الحالية
- completed_steps: الخطوات المكتملة (JSON)
- customer, branch, salesperson, status, notes
- selected_type: نوع الطلب
- invoice_number(s), contract_number(s)
- payment_method, paid_amount, payment_notes
- subtotal, total_discount, final_total
- is_completed: تم التحويل للطلب النهائي؟
- final_order: رابط للطلب النهائي
```

**DraftOrderItem** - عناصر المسودة
```python
- draft_order: FK إلى DraftOrder
- product, quantity, unit_price
- discount_percentage
- item_type: (product/fabric/accessory)
- Properties: total_price, discount_amount, final_price
```

**DraftContract** - العقد الإلكتروني
```python
- draft_order: OneToOne إلى DraftOrder
- additional_terms, notes
```

**DraftCurtain** - ستائر العقد
```python
- draft_contract: FK إلى DraftContract
- room_name, width, height
- Property: area (المساحة)
```

**DraftFabric** - أقمشة الستارة
```python
- draft_curtain: FK إلى DraftCurtain
- fabric_type: (light/heavy/blackout)
- fabric_name, pieces, meters
- tailoring_type: (rings/tape/snap)
```

**DraftAccessory** - إكسسوارات الستارة
```python
- draft_curtain: FK إلى DraftCurtain
- accessory_name, quantity, notes
```

### 2. المسارات (URLs)

```python
/orders/wizard/                      # بداية الويزارد
/orders/wizard/step/<int:step>/      # خطوة معينة
/orders/wizard/add-item/             # إضافة عنصر (AJAX)
/orders/wizard/remove-item/<id>/     # حذف عنصر (AJAX)
/orders/wizard/complete-step-3/      # إكمال مرحلة العناصر
/orders/wizard/finalize/             # التحويل للطلب النهائي
/orders/wizard/cancel/               # إلغاء الويزارد
```

### 3. الـ Views الرئيسية

**wizard_start**
- البحث عن مسودة غير مكتملة
- إنشاء مسودة جديدة إذا لم توجد
- توجيه للخطوة الحالية

**wizard_step**
- التحقق من الوصول للخطوة
- توجيه للدالة المناسبة (step_1 إلى step_6)

**wizard_step_1_basic_info**
- عرض/حفظ البيانات الأساسية
- تحديد الخطوة كمكتملة
- الانتقال للخطوة 2

**wizard_step_3_order_items**
- عرض العناصر الحالية
- حساب المجاميع

**wizard_add_item** (AJAX)
- إضافة عنصر للمسودة
- إعادة حساب المجاميع
- إرجاع JSON response

**wizard_finalize**
- التحقق من اكتمال الخطوات المطلوبة
- إنشاء Order نهائي
- نقل العناصر (DraftOrderItem → OrderItem)
- إنشاء Payment إذا وجد مبلغ مدفوع
- تحديد المسودة كمكتملة

### 4. النماذج (Forms)

**Step1BasicInfoForm**
- يربط بـ DraftOrder
- يحمل البائعين النشطين فقط
- يعين الفرع الافتراضي من المستخدم

**Step2OrderTypeForm**
- اختيار نوع الطلب (RadioSelect)
- تحميل المعاينات المرتبطة بالعميل

**Step4InvoicePaymentForm**
- التحقق من عدم تجاوز المبلغ المدفوع للإجمالي

### 5. القوالب (Templates)

**base_wizard.html**
- قالب أساسي للويزارد
- شريط التقدم (Progress Bar)
- مؤشر الخطوات (Steps Indicator)
- تصميم موحد للبطاقات

**step1_basic_info.html**
- نموذج البيانات الأساسية
- Select2 للعملاء
- أزرار (إلغاء / التالي)

**step3_order_items.html**
- قسم إضافة العناصر
- جدول العناصر المضافة
- شريط جانبي بالملخص
- AJAX لإضافة/حذف العناصر

**step6_review.html**
- مراجعة شاملة لجميع البيانات
- جداول منسقة
- زر التأكيد النهائي مع SweetAlert2

---

## آلية العمل (Workflow)

1. **البداية:**
   - المستخدم يضغط "إنشاء طلب جديد (ويزارد)"
   - إنشاء DraftOrder جديد
   - الانتقال للخطوة 1

2. **التقدم عبر الخطوات:**
   - كل خطوة تحفظ البيانات في المسودة
   - تحديد الخطوة كمكتملة في `completed_steps`
   - التحقق من إمكانية الوصول للخطوة التالية

3. **المرحلة الحرجة (الخطوة 3):**
   - إضافة العناصر عبر AJAX
   - حساب المجاميع فوراً
   - حفظ في DraftOrderItem

4. **التحويل النهائي:**
   - التحقق من جميع البيانات
   - معاملة ذرية (Transaction)
   - إنشاء Order + OrderItem + Payment
   - ربط المسودة بالطلب النهائي
   - حذف المسودة (أو وسمها completed)

---

## الميزات البارزة

### 1. الحفظ التدريجي
- كل خطوة تُحفظ في قاعدة البيانات
- يمكن استئناف الويزارد لاحقاً
- لا فقدان للبيانات عند إغلاق المتصفح

### 2. التحقق الذكي
- التحقق من إكمال الخطوة قبل الانتقال
- منع الوصول لخطوات غير مكتملة
- تحقق من صحة البيانات (Validation)

### 3. حساب فوري
- المجاميع تُحسب تلقائياً
- المبلغ المتبقي يُحدّث فوراً
- مساحة الستارة تُحسب من المقاسات

### 4. واجهة مستخدم احترافية
- شريط تقدم ديناميكي
- مؤشر خطوات واضح
- بطاقات تفاعلية
- رسائل تأكيد جميلة (SweetAlert2)

### 5. AJAX للأداء
- إضافة/حذف عناصر بدون تحديث الصفحة
- استجابة سريعة
- تجربة مستخدم سلسة

---

## التكامل مع النظام الحالي

### الطلب النهائي (Order)
- يتم إنشاؤه فقط عند التأكيد النهائي
- رقم الطلب (order_number) يُولّد تلقائياً
- ربط بـ DraftOrder عبر `source_draft`

### الدفعات (Payments)
- تُنشأ تلقائياً إذا المبلغ المدفوع > 0
- ربط بـ Order
- verified = True

### العقود الإلكترونية
- نظام منفصل لتفاصيل العقد
- يمكن تخطيه (اختياري)
- بيانات مخزنة في DraftContract/Curtain/Fabric/Accessory

---

## الأمان والصلاحيات

- **@login_required:** جميع الـ views محمية
- **المستخدم فقط:** كل مستخدم يرى مسوداته فقط
- **CSRF Protection:** جميع النماذج محمية
- **Validation:** تحقق من البيانات في الـ backend

---

## قاعدة البيانات

### Indexes المُنشأة
```python
# DraftOrder indexes:
- (created_by, is_completed)
- created_at
- current_step
```

### العلاقات
```
DraftOrder
  ├─ DraftOrderItem (Many)
  ├─ DraftContract (One)
  │    └─ DraftCurtain (Many)
  │         ├─ DraftFabric (Many)
  │         └─ DraftAccessory (Many)
  └─ Order (final_order FK)
```

---

## التطوير المستقبلي

### 1. تحسينات مقترحة:
- [ ] حفظ تلقائي (Auto-save) كل 30 ثانية
- [ ] localStorage backup للبيانات
- [ ] تصدير المسودة كـ JSON
- [ ] استيراد مسودة من JSON
- [ ] إحصائيات الويزارد (متوسط الوقت، معدل الإكمال)

### 2. ميزات إضافية:
- [ ] إضافة منتجات بالباركود في الخطوة 3
- [ ] معاينة العقد PDF قبل التأكيد
- [ ] إرسال نسخة Email للعميل
- [ ] تكرار طلب سابق

### 3. تحسينات الأداء:
- [ ] Lazy loading للمنتجات
- [ ] Pagination لقائمة العناصر
- [ ] Cache للأسعار
- [ ] Debounce للبحث

---

## كيفية الاستخدام

### للمستخدم النهائي:

1. من قائمة الطلبات، اضغط "إنشاء طلب جديد (ويزارد)"
2. املأ البيانات الأساسية واضغط "التالي"
3. اختر نوع الطلب واضغط "التالي"
4. أضف العناصر واحداً تلو الآخر
5. املأ تفاصيل الفاتورة والدفع
6. (اختياري) أضف تفاصيل العقد الإلكتروني
7. راجع جميع البيانات واضغط "تأكيد وإنشاء الطلب"

### للمطور:

```python
# إضافة endpoint جديد للويزارد
# في wizard_views.py:

@login_required
@require_http_methods(["POST"])
def wizard_custom_action(request):
    draft = get_object_or_404(
        DraftOrder,
        created_by=request.user,
        is_completed=False
    )
    
    # معالجة البيانات
    # ...
    
    return JsonResponse({'success': True})

# في urls.py:
path('wizard/custom-action/', wizard_views.wizard_custom_action, name='wizard_custom_action'),
```

---

## الملفات المُنشأة

### Models:
- `orders/wizard_models.py` - جميع النماذج

### Forms:
- `orders/wizard_forms.py` - جميع النماذج

### Views:
- `orders/wizard_views.py` - جميع الـ views

### Templates:
- `orders/templates/orders/wizard/base_wizard.html`
- `orders/templates/orders/wizard/step1_basic_info.html`
- `orders/templates/orders/wizard/step2_order_type.html`
- `orders/templates/orders/wizard/step3_order_items.html`
- `orders/templates/orders/wizard/step4_invoice_payment.html`
- `orders/templates/orders/wizard/step5_contract.html`
- `orders/templates/orders/wizard/step6_review.html`

### URLs:
- تم إضافة 7 مسارات جديدة في `orders/urls.py`

### Migrations:
- `orders/migrations/0040_draftcontract_draftcurtain_draftaccessory_and_more.py`

---

## الملاحظات الهامة

1. **المسودات غير المكتملة:** يتم البحث عنها تلقائياً عند بدء الويزارد
2. **الإلغاء:** حذف المسودة نهائياً (لا استرجاع)
3. **التحويل النهائي:** عملية ذرية (إما تكتمل أو تفشل بالكامل)
4. **رقم الطلب:** يُولّد بصيغة `ORD-YYYYMMDDHHmmss`

---

## الدعم والمساعدة

للاستفسارات أو المشاكل:
1. تحقق من الـ logs: `logs/`
2. راجع الـ console في المتصفح
3. استخدم Django Debug Toolbar للتحقق من الاستعلامات

---

**تم التنفيذ بنجاح ✅**
**تاريخ الإنشاء:** 2025-11-20
**الإصدار:** 1.0.0
