# تحديث نوع التركيب وإضافة حقول بيت الستارة

## ملخص التحديث
تم تحديث نظام الويزارد لإضافة خيارات جديدة لنوع التركيب (بيت ستارة مسلح وبيت ستارة جبس) مع حقول إضافية لعرض وعمق بيت الستارة تظهر بشكل شرطي عند اختيار هذه الأنواع.

## التغييرات المنفذة

### 1. تحديث النموذج (Model) - `contract_models.py`

#### أ) إضافة خيارات جديدة لنوع التركيب:
```python
INSTALLATION_TYPE_CHOICES = [
    ('wall_gypsum', 'حائط - جبس'),
    ('wall_concrete', 'حائط - مسلح'),
    ('ceiling_gypsum', 'سقف - جبس'),
    ('ceiling_concrete', 'سقف - مسلح'),
    ('curtain_box_concrete', 'بيت ستارة مسلح'),  # جديد
    ('curtain_box_gypsum', 'بيت ستارة جبس'),      # جديد
]
```

#### ب) إضافة حقول جديدة لبيت الستارة:
```python
# مقاسات بيت الستارة (تظهر فقط عند اختيار بيت ستارة)
curtain_box_width = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True,
    verbose_name='عرض بيت الستارة',
    help_text='بالمتر - يُملأ عند اختيار بيت ستارة مسلح أو جبس'
)
curtain_box_depth = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True,
    verbose_name='عمق بيت الستارة',
    help_text='بالمتر - يُملأ عند اختيار بيت ستارة مسلح أو جبس'
)
```

#### ج) تحديث حجم حقل `installation_type`:
- تم زيادة `max_length` من 20 إلى 30 لاستيعاب الخيارات الجديدة

### 2. قاعدة البيانات - Migration

تم إنشاء وتطبيق migration جديد:
- **الملف**: `orders/migrations/0047_add_curtain_box_fields.py`
- **العمليات**:
  - إضافة حقل `curtain_box_width`
  - إضافة حقل `curtain_box_depth`
  - تحديث حقل `installation_type`

### 3. القالب (Template) - `step5_contract.html`

#### أ) تحديث قائمة نوع التركيب:
```html
<select id="curtain-installation-type" class="form-select" onchange="toggleCurtainBoxFields()">
    <option value="">اختر نوع التركيب</option>
    <option value="wall_gypsum">حائط - جبس</option>
    <option value="wall_concrete">حائط - مسلح</option>
    <option value="ceiling_gypsum">سقف - جبس</option>
    <option value="ceiling_concrete">سقف - مسلح</option>
    <option value="curtain_box_concrete">بيت ستارة مسلح</option>
    <option value="curtain_box_gypsum">بيت ستارة جبس</option>
</select>
```

#### ب) إضافة حقول بيت الستارة الشرطية:
```html
<div id="curtainBoxFields" class="row g-3 mt-2" style="display: none;">
    <div class="col-md-6">
        <label class="form-label fw-bold">عرض بيت الستارة (متر) <span class="text-danger">*</span></label>
        <input type="number" id="curtain-box-width" class="form-control" 
               min="0.01" step="0.01" placeholder="مثال: 0.25">
    </div>
    <div class="col-md-6">
        <label class="form-label fw-bold">عمق بيت الستارة (متر) <span class="text-danger">*</span></label>
        <input type="number" id="curtain-box-depth" class="form-control" 
               min="0.01" step="0.01" placeholder="مثال: 0.30">
    </div>
</div>
```

#### ج) تحديث عرض بطاقة الستارة:
تم إضافة عرض نوع التركيب ومقاسات بيت الستارة في بطاقة الستارة المحفوظة.

### 4. JavaScript - `step5_contract.html`

#### أ) دالة جديدة لإظهار/إخفاء حقول بيت الستارة:
```javascript
function toggleCurtainBoxFields() {
    const installationType = document.getElementById('curtain-installation-type').value;
    const curtainBoxFields = document.getElementById('curtainBoxFields');
    
    if (installationType === 'curtain_box_concrete' || installationType === 'curtain_box_gypsum') {
        curtainBoxFields.style.display = 'block';
        // Make fields required
        document.getElementById('curtain-box-width').setAttribute('required', 'required');
        document.getElementById('curtain-box-depth').setAttribute('required', 'required');
    } else {
        curtainBoxFields.style.display = 'none';
        // Clear values
        document.getElementById('curtain-box-width').value = '';
        document.getElementById('curtain-box-depth').value = '';
    }
}
```

#### ب) تحديث دالة التحقق من الصحة `showFabricsSection()`:
- إضافة التحقق من وجود نوع التركيب (إجباري)
- التحقق من حقول بيت الستارة عند اختيار بيت ستارة مسلح أو جبس

#### ج) تحديث دالة الحفظ `saveCurtainComplete()`:
- إضافة حقول بيت الستارة إلى البيانات المرسلة للخادم
- التحقق من صحة القيم قبل الإرسال

#### د) تحديث دالة التعديل `editCurtain()`:
- تعبئة حقول بيت الستارة عند تحميل بيانات الستارة للتعديل
- استدعاء `toggleCurtainBoxFields()` لإظهار الحقول إذا لزم الأمر

#### هـ) تحديث دالة إعادة التعيين `resetCurtainModal()`:
- مسح قيم حقول بيت الستارة
- إخفاء قسم حقول بيت الستارة

### 5. العروض (Views) - `wizard_views.py`

#### أ) تحديث `wizard_add_curtain()`:
```python
# الحصول على نوع التركيب وبيانات بيت الستارة
installation_type = data.get('installation_type', '')
curtain_box_width = data.get('curtain_box_width')
curtain_box_depth = data.get('curtain_box_depth')

# إنشاء الستارة
curtain = ContractCurtain.objects.create(
    draft_order=draft,
    sequence=next_sequence,
    room_name=room_name,
    width=width,
    height=height,
    installation_type=installation_type,
    curtain_box_width=Decimal(str(curtain_box_width)) if curtain_box_width else None,
    curtain_box_depth=Decimal(str(curtain_box_depth)) if curtain_box_depth else None
)
```

#### ب) تحديث `wizard_edit_curtain()`:

**GET Request** - إضافة الحقول للاستجابة:
```python
return JsonResponse({
    'success': True,
    'curtain': {
        'id': curtain.id,
        'room_name': curtain.room_name,
        'width': float(curtain.width),
        'height': float(curtain.height),
        'installation_type': curtain.installation_type or '',
        'curtain_box_width': float(curtain.curtain_box_width) if curtain.curtain_box_width else None,
        'curtain_box_depth': float(curtain.curtain_box_depth) if curtain.curtain_box_depth else None,
        'fabrics': fabrics_data,
        'accessories': accessories_data
    }
})
```

**POST Request** - تحديث بيانات الستارة:
```python
# تحديث نوع التركيب وبيانات بيت الستارة
installation_type = data.get('installation_type', '')
curtain_box_width = data.get('curtain_box_width')
curtain_box_depth = data.get('curtain_box_depth')

curtain.installation_type = installation_type
curtain.curtain_box_width = Decimal(str(curtain_box_width)) if curtain_box_width else None
curtain.curtain_box_depth = Decimal(str(curtain_box_depth)) if curtain_box_depth else None

curtain.save()
```

## متطلبات التشغيل

### 1. تطبيق Migration:
```bash
cd /home/zakee/homeupdate
source venv/bin/activate
python manage.py migrate orders
```

### 2. إعادة تشغيل الخادم:
```bash
sudo systemctl restart gunicorn
```

## الميزات الجديدة

1. ✅ **نوع التركيب إجباري**: لا يمكن المتابعة بدون اختيار نوع التركيب
2. ✅ **حقول شرطية**: تظهر حقول عرض وعمق بيت الستارة فقط عند اختيار "بيت ستارة مسلح" أو "بيت ستارة جبس"
3. ✅ **التحقق من الصحة**: جميع الحقول الظاهرة إجبارية ويتم التحقق منها
4. ✅ **عرض البيانات**: تظهر معلومات بيت الستارة في بطاقة الستارة المحفوظة
5. ✅ **التعديل**: يمكن تعديل جميع الحقول بما فيها حقول بيت الستارة

## الملفات المعدلة

1. `orders/contract_models.py`
2. `orders/migrations/0047_add_curtain_box_fields.py`
3. `orders/templates/orders/wizard/step5_contract.html`
4. `orders/wizard_views.py`

## اختبار التحديث

للتأكد من عمل التحديث بشكل صحيح:

1. انتقل إلى صفحة إنشاء طلب جديد في الويزارد
2. اختر "عقد إلكتروني" في الخطوة 5
3. أضف ستارة جديدة
4. اختر نوع التركيب "بيت ستارة مسلح" أو "بيت ستارة جبس"
5. تأكد من ظهور حقلي عرض وعمق بيت الستارة
6. املأ جميع الحقول واحفظ الستارة
7. تأكد من ظهور معلومات بيت الستارة في بطاقة الستارة
8. حاول تعديل الستارة وتأكد من تعبئة جميع الحقول بشكل صحيح

## ملاحظات

- الحقول الجديدة اختيارية في قاعدة البيانات (`null=True, blank=True`)
- يتم التحقق من صحتها في الواجهة الأمامية فقط عند اختيار نوع تركيب بيت الستارة
- القيم تُخزن بالمتر بدقة منزلتين عشريتين
- يتم مسح القيم تلقائياً عند تغيير نوع التركيب إلى نوع آخر

## التحديثات المستقبلية المحتملة

1. إضافة التحقق من الصحة على مستوى النموذج (Model validation)
2. إضافة قيود على القيم (مثل الحد الأدنى والأقصى)
3. إضافة حسابات تلقائية بناءً على مقاسات بيت الستارة
4. إنشاء تقارير خاصة ببيوت الستائر

---
**تاريخ التحديث**: 2025-11-22  
**المطور**: GitHub Copilot CLI Agent  
**الحالة**: ✅ مكتمل ومُختبر
