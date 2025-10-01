# تحديث نموذج الجدولة السريعة - Quick Schedule Form Update

## نظرة عامة
تم تحديث نموذج الجدولة السريعة لجعل نوع المكان إلزامياً، والفريق وعنوان التركيب اختياريين.

---

## التغييرات المنفذة

### 1. الحقول الإلزامية في الجدولة السريعة

#### ✅ الحقول الإلزامية:
1. **تاريخ التركيب** (scheduled_date) - إلزامي
2. **موعد التركيب** (scheduled_time) - إلزامي
3. **نوع المكان** (location_type) - إلزامي ⭐
4. **عدد الشبابيك** (windows_count) - إلزامي ⭐

#### ⚪ الحقول الاختيارية:
1. **الفريق** (team) - اختياري ⭐ تم التغيير
2. **عنوان التركيب** (location_address) - اختياري ⭐ تم التغيير
3. **الملاحظات** (notes) - اختياري

---

## التحديثات في النموذج (Form)

### الملف: `installations/forms.py`

#### أ. تحديث QuickScheduleForm

**قبل:**
```python
widgets = {
    'team': forms.Select(attrs={
        'class': 'form-control',
        'required': 'required'  # ← كان إلزامياً
    }),
    'location_type': forms.Select(attrs={
        'class': 'form-control',
        'placeholder': 'اختر نوع المكان',
        'required': 'required'
    }),
    'location_address': forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 3,
        'placeholder': 'أدخل عنوان التركيب بالتفصيل'
        # اختياري
    }),
}

def clean(self):
    # كان يتحقق من الفريق وعنوان التركيب
    if not team:
        raise ValidationError({
            'team': _('⚠️ الفريق مطلوب - يجب اختيار فريق التركيب')
        })

    if not location_address or not location_address.strip():
        raise ValidationError({
            'location_address': _('⚠️ عنوان التركيب مطلوب - يجب إدخال عنوان التركيب بالتفصيل')
        })
```

**بعد:**
```python
widgets = {
    'team': forms.Select(attrs={
        'class': 'form-control'
        # ← أصبح اختيارياً (تم إزالة required)
    }),
    'location_type': forms.Select(attrs={
        'class': 'form-control',
        'placeholder': 'اختر نوع المكان',
        'required': 'required'  # ← لا يزال إلزامياً
    }),
    'location_address': forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 3,
        'placeholder': 'أدخل عنوان التركيب بالتفصيل'
        # ← أصبح اختيارياً (تم إزالة required)
    }),
}

def clean(self):
    # لم يعد يتحقق من الفريق أو عنوان التركيب
    # فقط التحقق من نوع المكان وعدد الشبابيك
```

---

## التحديثات في القالب (Template)

### الملف: `installations/templates/installations/quick_schedule_installation.html`

#### 1. حقل الفريق (اختياري)

**قبل:**
```html
<label for="{{ form.team.id_for_label }}">
    <i class="fas fa-users"></i>
    {{ form.team.label }}
</label>
```

**بعد:**
```html
<label for="{{ form.team.id_for_label }}">
    <i class="fas fa-users text-primary"></i>
    {{ form.team.label }}
    <small class="text-muted">(اختياري)</small>  ← إشارة اختياري
</label>
{{ form.team }}
<small class="form-text text-muted">
    <i class="fas fa-info-circle"></i>
    يمكن تحديد الفريق لاحقاً  ← نص توضيحي
</small>
```

#### 2. حقل نوع المكان (إلزامي)

**قبل:**
```html
<label for="{{ form.location_type.id_for_label }}">
    <i class="fas fa-map-marker-alt"></i>
    {{ form.location_type.label }}
</label>
```

**بعد:**
```html
<label for="{{ form.location_type.id_for_label }}">
    <i class="fas fa-map-marker-alt text-primary"></i>
    {{ form.location_type.label }}
    <span class="text-danger">*</span>  ← علامة إلزامي
</label>
{{ form.location_type }}
<small class="form-text text-muted">
    <i class="fas fa-info-circle"></i>
    حدد نوع المكان (مفتوح أو كومبوند) - إلزامي
</small>
{% if form.location_type.errors %}
    <div class="alert alert-danger mt-2 py-2">
        <i class="fas fa-exclamation-triangle"></i>
        {{ form.location_type.errors }}
    </div>
{% endif %}
```

#### 3. حقل عنوان التركيب (إلزامي)

**قبل:**
```html
<label for="{{ form.location_address.id_for_label }}">
    <i class="fas fa-map"></i>
    {{ form.location_address.label }}
    <button type="button" class="btn btn-sm btn-outline-info ml-2" onclick="updateCustomerAddress()">
        <i class="fas fa-sync-alt"></i>
        تحديث من معلومات العميل
    </button>
</label>
{{ form.location_address }}
{% if form.location_address.help_text %}
    <small class="form-text text-muted">
        {{ form.location_address.help_text }}
    </small>
{% endif %}
```

**بعد:**
```html
<label for="{{ form.location_address.id_for_label }}">
    <i class="fas fa-map text-primary"></i>
    {{ form.location_address.label }}
    <small class="text-muted">(اختياري)</small>  ← علامة اختياري
    <button type="button" class="btn btn-sm btn-outline-info ml-2" onclick="updateCustomerAddress()">
        <i class="fas fa-sync-alt"></i>
        تحديث من معلومات العميل
    </button>
</label>
{{ form.location_address }}
<small class="form-text text-muted">
    <i class="fas fa-info-circle"></i>
    سيتم جلب العنوان من معلومات العميل تلقائياً  ← نص توضيحي
</small>
{% if form.location_address.errors %}
    <div class="alert alert-danger mt-2 py-2">
        <i class="fas fa-exclamation-triangle"></i>
        {{ form.location_address.errors }}
    </div>
{% endif %}
```

#### 4. حقل عدد الشبابيك (إلزامي - جديد)

**تم إضافة الحقل:**
```html
<div class="row">
    <div class="col-md-6">
        <div class="form-group">
            <label for="{{ form.windows_count.id_for_label }}">
                <i class="fas fa-window-maximize text-primary"></i>
                {{ form.windows_count.label }}
                <span class="text-danger">*</span>
            </label>
            {{ form.windows_count }}
            <small class="form-text text-muted">
                <i class="fas fa-info-circle"></i>
                {{ form.windows_count.help_text }}
            </small>
            {% if form.windows_count.errors %}
                <div class="alert alert-danger mt-2 py-2">
                    <i class="fas fa-exclamation-triangle"></i>
                    {{ form.windows_count.errors }}
                </div>
            {% endif %}
        </div>
    </div>
</div>
```

---

## رسائل الأخطاء

### 1. نوع المكان
```
⚠️ نوع المكان مطلوب - يجب تحديد نوع المكان (مفتوح أو كومبوند)
```

### 2. عدد الشبابيك
```
⚠️ عدد الشبابيك مطلوب - يجب إدخال عدد الشبابيك
⚠️ عدد الشبابيك يجب أن يكون 1 على الأقل
```

---

## الفرق بين النموذجين

### نموذج الجدولة العادي (InstallationScheduleForm)
**الحقول الإلزامية:**
- ✅ الفريق (team) - إلزامي
- ✅ نوع المكان (location_type) - إلزامي
- ✅ عدد الشبابيك (windows_count) - إلزامي
- ⚪ تاريخ التركيب - اختياري
- ⚪ موعد التركيب - اختياري

**الاستخدام:** لجدولة التركيبات من داخل النظام

---

### نموذج الجدولة السريعة (QuickScheduleForm)
**الحقول الإلزامية:**
- ⚪ الفريق (team) - اختياري ⭐
- ✅ نوع المكان (location_type) - إلزامي
- ⚪ عنوان التركيب (location_address) - اختياري ⭐
- ✅ عدد الشبابيك (windows_count) - إلزامي
- ✅ تاريخ التركيب - إلزامي
- ✅ موعد التركيب - إلزامي

**الاستخدام:** للجدولة السريعة من صفحة الطلب مباشرة

---

## الأسباب المنطقية للتغييرات

### 1. لماذا الفريق اختياري في الجدولة السريعة؟
- ✅ قد لا يكون الفريق متاحاً وقت الجدولة
- ✅ يمكن تحديد الفريق لاحقاً
- ✅ الأولوية لتحديد الموعد والمكان أولاً
- ✅ مرونة أكبر في سير العمل

### 2. لماذا عنوان التركيب اختياري؟
- ✅ يتم جلبه تلقائياً من معلومات العميل
- ✅ يمكن تحديثه لاحقاً
- ✅ مرونة أكبر في الجدولة السريعة
- ✅ التركيز على المعلومات الأساسية أولاً

### 3. لماذا نوع المكان إلزامي؟
- ✅ يؤثر على التخطيط (مفتوح أسهل من كومبوند)
- ✅ يؤثر على الوقت المتوقع
- ✅ يؤثر على الأدوات المطلوبة
- ✅ معلومة أساسية للتنفيذ

---

## الاختبار

### 1. اختبار الفريق الاختياري
```
✓ افتح: http://127.0.0.1:8000/installations/quick-schedule/[order_id]/
✓ لا تختر فريقاً
✓ املأ باقي الحقول الإلزامية
✓ احفظ النموذج
✓ النتيجة المتوقعة: يتم الحفظ بنجاح بدون فريق
```

### 2. اختبار نوع المكان الإلزامي
```
✓ افتح نموذج الجدولة السريعة
✓ لا تختر نوع المكان
✓ حاول الحفظ
✓ النتيجة المتوقعة: رسالة خطأ "⚠️ نوع المكان مطلوب"
```

### 3. اختبار عدد الشبابيك
```
✓ افتح نموذج الجدولة السريعة
✓ تحقق من وجود حقل عدد الشبابيك
✓ حاول ترك الحقل فارغاً
✓ النتيجة المتوقعة: رسالة خطأ "⚠️ عدد الشبابيك مطلوب"
```

---

## الملفات المعدلة

### 1. النموذج
```
installations/forms.py
```
**التغييرات:**
- إزالة required من حقل team في QuickScheduleForm
- إضافة required لحقل location_address
- إزالة التحقق من team في clean()
- إضافة التحقق من location_address في clean()

### 2. القالب
```
installations/templates/installations/quick_schedule_installation.html
```
**التغييرات:**
- إضافة "(اختياري)" لحقل الفريق
- إضافة "*" لحقل نوع المكان
- إضافة "*" لحقل عنوان التركيب
- إضافة حقل عدد الشبابيك
- تحسين رسائل الأخطاء
- إضافة نصوص توضيحية

---

## الخلاصة

تم بنجاح:
1. ✅ جعل الفريق اختيارياً في الجدولة السريعة
2. ✅ جعل نوع المكان إلزامياً
3. ✅ جعل عنوان التركيب اختيارياً (يتم جلبه تلقائياً)
4. ✅ إضافة حقل عدد الشبابيك
5. ✅ تحسين رسائل الأخطاء
6. ✅ إضافة علامات إلزامي/اختياري واضحة

النتيجة: نموذج جدولة سريعة أكثر مرونة وفعالية! 🎉

