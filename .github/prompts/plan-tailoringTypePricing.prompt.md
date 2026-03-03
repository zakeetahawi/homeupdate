# خطة: نظام تسعير أنواع التفصيل (استبدال المضاعفة)

## الملخص

استبدال آلية مضاعفة الأمتار (`double_meter`) بنظام تسعير مرن لكل نوع تفصيل (`tailoring_type`). كل نوع تفصيل يحمل سعراً وطريقة حساب (بالمتر أو بالعدد). الأمتار الحقيقية تبقى كما هي، فقط التكلفة تتغير حسب التسعير. القصاص يبقى بسعره الثابت للمتر.

---

## تدفق البيانات الحالي vs الجديد

**الحالي:**
```
CurtainFabric → meters, pieces, tailoring_type, fabric_type
    ↓
calculate_total_meters():
    - excluded fabric_types → skip
    - tailoring_type in double_meter_list → meters × 2 → total_double_meters
    - else → meters × 1
    ↓
total_billable_meters (حقيقي)
total_double_meters (مضاعف) ← يُستخدم لتوزيع الخياطين
    ↓
CardMeasurementSplit: share_amount (من double_meters) × سعر_الخياط
```

**الجديد:**
```
CurtainFabric → meters, pieces, tailoring_type, fabric_type
    ↓
calculate_total_meters():
    - excluded fabric_types → skip
    - لكل قماش: ابحث عن TailoringTypePricing
      - per_meter → cost = meters × rate
      - per_piece → cost = pieces × rate
      - بدون تسعير → cost = meters × default_rate_per_meter
    ↓
total_billable_meters (حقيقي — بدون تغيير)
total_tailoring_cost (مجموع تكاليف كل الأقمشة حسب التسعير)
tailoring_cost_breakdown (JSON تفصيلي)
    ↓
CardMeasurementSplit: share_amount (أمتار حقيقية) × سعر_الخياط
    أو: نسبة من total_tailoring_cost
```

---

## المرحلة 1: نموذج `TailoringTypePricing` (جديد)

**الملف:** `factory_accounting/models.py`

```python
class TailoringTypePricing(models.Model):
    """
    تسعير مخصص لكل نوع تفصيل
    بالمتر: التكلفة = الأمتار × السعر
    بالعدد: التكلفة = عدد القطع (pieces) × السعر
    """
    CALC_METHOD_CHOICES = [
        ('per_meter', 'بالمتر'),
        ('per_piece', 'بالعدد (قطعة)'),
    ]

    tailoring_type = models.OneToOneField(
        'orders.WizardFieldOption',
        on_delete=models.CASCADE,
        limit_choices_to={'field_type': 'tailoring_type', 'is_active': True},
        related_name='factory_pricing',
        verbose_name='نوع التفصيل',
    )
    rate = models.DecimalField(
        'السعر', max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='السعر لكل متر أو لكل قطعة حسب طريقة الحساب'
    )
    calc_method = models.CharField(
        'طريقة الحساب', max_length=20,
        choices=CALC_METHOD_CHOICES, default='per_meter'
    )
    is_active = models.BooleanField('نشط', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**لماذا `OneToOneField`:** كل نوع تفصيل (`WizardFieldOption` حيث `field_type='tailoring_type'`) له تسعير واحد فقط. الأنواع بدون تسعير تسقط على السعر الإفتراضي.

---

## المرحلة 2: تعديل `FactoryAccountingSettings`

**الملف:** `factory_accounting/models.py` — أسطر 33-42

**حذف:**
```python
# إزالة هذا الحقل بالكامل:
double_meter_tailoring_types = models.ManyToManyField(
    "orders.WizardFieldOption",
    ...
    related_name="double_meter_settings",
)
```

**`default_rate_per_meter` يبقى كما هو** — يُستخدم كـ fallback لأنواع التفصيل بدون تسعير مخصص.

**تعديل `save()`:** إزالة أي منطق مرتبط بـ `double_meter_tailoring_types` من `save()`. إضافة: عند تغيير `default_rate_per_meter` → إعادة حساب `total_tailoring_cost` لكل البطاقات غير المدفوعة التي تحتوي أقمشة بدون تسعير مخصص.

---

## المرحلة 3: تعديل `FactoryCard`

**الملف:** `factory_accounting/models.py` — أسطر 360-367

**حذف:**
```python
# إزالة بالكامل:
total_double_meters = models.DecimalField(
    _("إجمالي الأمتار (مضاعف)"),
    ...
)
```

**إضافة:**
```python
total_tailoring_cost = models.DecimalField(
    _("إجمالي تكلفة التفصيل المقدّرة"),
    max_digits=15, decimal_places=2,
    default=Decimal("0.00"),
    help_text=_("مجموع تكاليف كل الأقمشة حسب تسعير نوع التفصيل"),
)

tailoring_cost_breakdown = models.JSONField(
    _("تفاصيل تكلفة التفصيل"),
    default=dict, blank=True,
    help_text=_("تفصيل التكلفة لكل نوع تفصيل: {type: {meters, pieces, rate, method, cost, display_name}}")
)
```

---

## المرحلة 4: إعادة كتابة `calculate_total_meters()` (الأهم)

**الملف:** `factory_accounting/models.py` — أسطر 464-560

**المنطق الجديد:**

```python
def calculate_total_meters(self):
    from orders.contract_models import ContractCurtain

    curtains = ContractCurtain.objects.filter(
        order=self.manufacturing_order.order
    ).prefetch_related("fabrics")

    settings = FactoryAccountingSettings.get_settings()
    
    # 1. أنواع القماش المستبعدة
    excluded = set(settings.excluded_fabric_types.values_list("value", flat=True))
    excluded.update({"belt", "accessory"})  # hardcoded
    
    # 2. تحميل كل تسعيرات التفصيل مرة واحدة (بدل query لكل قماش)
    pricing_map = {}
    for p in TailoringTypePricing.objects.filter(is_active=True).select_related('tailoring_type'):
        pricing_map[p.tailoring_type.value] = p
        pricing_map[p.tailoring_type.display_name] = p  # fallback للمطابقة

    default_rate = settings.default_rate_per_meter
    
    total_actual = Decimal("0.00")
    total_tailoring_cost = Decimal("0.00")
    breakdown = {}  # {tailoring_type_value: {display, method, rate, meters, pieces, cost}}
    
    for curtain in curtains:
        for fabric in curtain.fabrics.all():
            if fabric.fabric_type in excluded:
                continue
            
            meters = Decimal(str(fabric.meters)) if fabric.meters else Decimal("0.00")
            pieces = int(fabric.pieces) if fabric.pieces else 1
            total_actual += meters
            
            # البحث عن تسعير نوع التفصيل
            t_type = fabric.tailoring_type or ""
            t_display = fabric.get_tailoring_type_display() or t_type
            
            pricing = pricing_map.get(t_type) or pricing_map.get(t_display)
            
            if pricing:
                rate = pricing.rate
                method = pricing.calc_method
                if method == 'per_piece':
                    cost = Decimal(str(pieces)) * rate
                else:  # per_meter
                    cost = meters * rate
            else:
                # fallback: السعر الإفتراضي × الأمتار
                rate = default_rate
                method = 'per_meter'
                cost = meters * rate
            
            total_tailoring_cost += cost
            
            # تجميع في breakdown
            key = t_type or 'unspecified'
            if key not in breakdown:
                breakdown[key] = {
                    'display': t_display or 'بدون تفصيل',
                    'method': method,
                    'rate': float(rate),
                    'meters': 0.0,
                    'pieces': 0,
                    'cost': 0.0,
                }
            breakdown[key]['meters'] += float(meters)
            breakdown[key]['pieces'] += pieces
            breakdown[key]['cost'] += float(cost)
    
    # حفظ
    self.total_billable_meters = total_actual
    self.total_tailoring_cost = total_tailoring_cost
    self.tailoring_cost_breakdown = breakdown
    
    # حساب القصاص (بدون تغيير — أمتار حقيقية × سعر القصاص)
    self.cutter_price = settings.default_cutter_rate
    self.total_cutter_cost = total_actual * settings.default_cutter_rate
    
    self.save(update_fields=[
        "total_billable_meters",
        "total_tailoring_cost",
        "tailoring_cost_breakdown",
        "cutter_price",
        "total_cutter_cost",
        "updated_at",
    ])
    return total_actual
```

---

## المرحلة 5: تعديل `save_factory_card_splits` و `get_factory_card_data`

### 5A: `save_factory_card_splits`

**الملف:** `factory_accounting/views.py` — سطر 116-135

**الحالي:** يستخدم `total_double_meters` كمرجع لتوزيع الأمتار:
```python
total_double = factory_card.total_double_meters or 0
target_meters = total_double if total_double > 0 else billable
```

**الجديد:** يستخدم `total_billable_meters` فقط:
```python
target_meters = Decimal(str(factory_card.total_billable_meters or 0))
```

### 5B: `get_factory_card_data` (API)

**الملف:** `factory_accounting/views.py` — سطر 265-270

**حذف:** `"total_double_meters": float(factory_card.total_double_meters)`

**إضافة:**
```python
"total_tailoring_cost": float(factory_card.total_tailoring_cost),
"tailoring_cost_breakdown": factory_card.tailoring_cost_breakdown,
```

---

## المرحلة 6: تعديل `CardMeasurementSplit`

**الملف:** `factory_accounting/models.py` — سطر 702-715

منطق `get_current_monetary_value()` يظل: `share_amount × tailor.get_rate()`. هذا سعر الخياط وليس سعر نوع التفصيل. سعر نوع التفصيل يظهر في `total_tailoring_cost` كتكلفة مقدّرة/مرجعية.

→ **بدون تغيير** على `CardMeasurementSplit` نفسه. التسعير الجديد يؤثر فقط على `FactoryCard.total_tailoring_cost`.

---

## المرحلة 7: تعديل لوحة تحكم الأدمن

**الملف:** `factory_accounting/admin.py`

### 7A — `FactoryAccountingSettingsAdmin`:
- إزالة `"double_meter_tailoring_types"` من `filter_horizontal` (سطر 23)
- إزالة قسم `"الأمتار المضاعفة"` من `fieldsets` (أسطر 34-38)

### 7B — إضافة `TailoringTypePricingAdmin`:
```python
@admin.register(TailoringTypePricing)
class TailoringTypePricingAdmin(admin.ModelAdmin):
    list_display = ['tailoring_type', 'rate', 'get_calc_method_display', 'is_active']
    list_editable = ['rate', 'is_active']  # تعديل سريع من القائمة
    list_filter = ['calc_method', 'is_active']
    search_fields = ['tailoring_type__display_name', 'tailoring_type__value']
    
    fieldsets = (
        ('نوع التفصيل', {'fields': ('tailoring_type',)}),
        ('التسعير', {
            'fields': ('rate', 'calc_method'),
            'description': 'بالمتر: التكلفة = الأمتار × السعر | بالعدد: التكلفة = عدد القطع × السعر',
        }),
        ('إعدادات', {'fields': ('is_active', 'notes')}),
    )
    
    def get_calc_method_display(self, obj):
        return obj.get_calc_method_display()
    get_calc_method_display.short_description = 'طريقة الحساب'
```

### 7C — `FactoryCardAdmin`:
- إزالة أي مرجع لـ `total_double_meters`
- إضافة `total_tailoring_cost` في `list_display` و `fieldsets`

---

## المرحلة 8: تعديل التقارير

**الملف:** `factory_accounting/reports_views.py`

### `production_reports()`:
- بدون تغيير في الفلاتر
- إضافة حساب `total_tailoring_cost` في context:
  ```python
  total_tailoring_cost = cards.aggregate(total=Sum("total_tailoring_cost"))["total"] or Decimal("0.00")
  ```

### `export_production_report()`:
- سطر 409: إزالة عمود "مضاعف" (`total_double_meters`) فقط بدون إضافة عمود بديل

---

## المرحلة 9: تعديل قالب التقارير

**الملف:** `factory_accounting/templates/factory_accounting/reports.html`

- **سطر 170:** إزالة `<th>مضاعف</th>`
- **سطر 197-200:** إزالة عمود `total_double_meters` من `<td>`
- بدون إضافة عمود بديل — البيانات محفوظة داخلياً في `tailoring_cost_breakdown` للرجوع إليها عند الحاجة

---

## المرحلة 10: تعديل واجهة تفاصيل أمر التصنيع

**الملف:** `manufacturing/templates/manufacturing/manufacturingorder_detail.html`

**5 مواقع تستخدم `total_double_meters`:**

1. **سطر 1035:** `const totalMetersHelper = factory_card.total_double_meters > 0 ? ...`
   → **تغيير إلى:** `const totalMetersHelper = factory_card.total_billable_meters;`

2. **سطر 1045:** عرض badge "مضاعف"
   → **إزالة** badge المضاعف بدون بديل

3. **سطر 1147:** دالة `addSplitRow()` — نفس المنطق
   → **تغيير إلى:** `total_billable_meters` فقط

4. **سطر 1204:** دالة `saveFactoryCard()` — validation
   → **تغيير إلى:** `total_billable_meters` فقط

---

## المرحلة 11: Migrations

```bash
python manage.py makemigrations factory_accounting
# ستنتج:
# 0017_tailoringtypepricing.py                    (نموذج جديد)
# 0017_remove_double_meter_tailoring_types.py      (إزالة M2M)
# 0017_remove_total_double_meters.py               (إزالة حقل)
# 0017_add_tailoring_cost_fields.py                (حقول جديدة)

python manage.py migrate factory_accounting
```

---

## المرحلة 12: إعادة حساب البطاقات الحالية

**Management Command جديد** أو سكربت لمرة واحدة:
```python
# إعادة حساب كل البطاقات غير المدفوعة
for card in FactoryCard.objects.exclude(status="paid"):
    card.calculate_total_meters()
```

---

## جدول جميع الملفات المتأثرة

| # | الملف | التغيير | المرحلة |
|---|-------|---------|---------|
| 1 | `factory_accounting/models.py` | نموذج `TailoringTypePricing` جديد | 1 |
| 2 | `factory_accounting/models.py` | حذف `double_meter_tailoring_types` من Settings | 2 |
| 3 | `factory_accounting/models.py` | حذف `total_double_meters` + إضافة `total_tailoring_cost` + `tailoring_cost_breakdown` | 3 |
| 4 | `factory_accounting/models.py` | إعادة كتابة `calculate_total_meters()` بالكامل | 4 |
| 5 | `factory_accounting/views.py` | إزالة منطق `total_double` من `save_factory_card_splits` (سطر 116) | 5 |
| 6 | `factory_accounting/views.py` | تعديل `get_factory_card_data` API response (سطر 265-270) | 6 |
| 7 | `factory_accounting/admin.py` | إزالة `double_meter_tailoring_types` + إضافة `TailoringTypePricingAdmin` | 7 |
| 8 | `factory_accounting/reports_views.py` | إزالة عمود مضاعف فقط | 8 |
| 9 | `factory_accounting/templates/factory_accounting/reports.html` | إزالة عمود مضاعف فقط | 9 |
| 10 | `manufacturing/templates/manufacturing/manufacturingorder_detail.html` | 5 تعديلات: إزالة كل منطق `total_double_meters` | 10 |
| 11 | `factory_accounting/migrations/` | 1-2 migration جديدة | 11 |

---

## التحقق بعد التنفيذ

1. **Admin test:** إضافة تسعير لنوع تفصيل (كوشن = 15/قطعة، كابتونيه = 10/متر) من لوحة التحكم
2. **Signal test:** تغيير حالة أمر تصنيع لـ `completed` → التأكد أن `total_tailoring_cost` يُحسب صحيحاً
3. **API test:** فتح تفاصيل أمر تصنيع → التأكد أن `tailoring_cost_breakdown` يظهر في الواجهة
4. **Split validation:** توزيع خياطين → التأكد أن الأمتار الحقيقية هي المرجع وليست المضاعفة
5. **Reports test:** فتح `/factory-accounting/reports/` → التأكد من اختفاء عمود "مضاعف"
6. **Excel export test:** تصدير → التأكد من إزالة عمود المضاعف
7. **Paid cards:** التأكد أن البطاقات المدفوعة لا تتأثر بإعادة الحساب
