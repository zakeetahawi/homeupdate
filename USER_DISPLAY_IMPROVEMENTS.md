# تحسينات عرض اسم المستخدم في الإشعارات وسجل الحالة - 2025-10-13

## 🎯 المشكلة:

عند تحديث حالة أي طلب:
- بعض الإشعارات تعرض اسم المستخدم الحقيقي
- بعض الإشعارات تعرض "مستخدم النظام"
- لا يوجد تمييز بصري واضح بين المستخدمين الحقيقيين والنظام
- **المشكلة الأساسية**: كانت الإشعارات وسجلات الحالة تُنشأ تلقائياً من signals بدون مستخدم حقيقي

---

## ✅ التحديثات المطبقة:

### 1. **تحسين عرض المستخدم في الإشعارات (Notifications)**

#### قبل:
```html
{% if notification.created_by %}
<small class="text-muted">
    بواسطة {{ notification.created_by.get_full_name|default:notification.created_by.username }}
</small>
{% elif notification.extra_data.changed_by %}
<small class="text-muted">
    تم التغيير بواسطة: {{ notification.extra_data.changed_by }}
</small>
{% endif %}
```

#### بعد:
```html
{% if notification.created_by %}
<span class="badge bg-primary">
    <i class="fas fa-user"></i>
    {{ notification.created_by.get_full_name|default:notification.created_by.username }}
</span>
{% elif notification.extra_data.changed_by and notification.extra_data.changed_by != 'مستخدم النظام' %}
<span class="badge bg-info">
    <i class="fas fa-user"></i>
    {{ notification.extra_data.changed_by }}
</span>
{% else %}
<span class="badge bg-secondary">
    <i class="fas fa-robot"></i>
    مستخدم النظام
</span>
{% endif %}
```

**الألوان:**
- 🔵 **أزرق (bg-primary)**: مستخدم حقيقي من `created_by`
- 🔷 **أزرق فاتح (bg-info)**: مستخدم حقيقي من `extra_data`
- ⚫ **رمادي (bg-secondary)**: مستخدم النظام (تلقائي)

---

### 2. **تحسين عرض المستخدم في سجل حالة الطلب (Order Status Log)**

#### قبل:
```html
<div class="user-info">
    <i class="fas fa-user text-muted"></i>
    <small style="font-size: 0.85em;">
        {% if log.changed_by %}
            <strong>{{ log.changed_by.get_full_name|default:log.changed_by.username }}</strong>
            {% if not log.is_automatic %}
                <span class="badge bg-success ms-1" style="font-size: 0.7em;">يدوي</span>
            {% endif %}
        {% elif log.is_automatic %}
            <span class="text-muted">
                <i class="fas fa-robot"></i> تلقائي
            </span>
        {% else %}
            <span class="text-warning">
                <i class="fas fa-question-circle"></i> مستخدم غير محدد
            </span>
        {% endif %}
    </small>
</div>
```

#### بعد:
```html
<div class="user-info">
    {% if log.changed_by %}
        <span class="badge bg-primary" style="font-size: 0.85em;">
            <i class="fas fa-user"></i>
            {{ log.changed_by.get_full_name|default:log.changed_by.username }}
        </span>
        {% if not log.is_automatic %}
            <span class="badge bg-success ms-1" style="font-size: 0.7em;">
                <i class="fas fa-hand-pointer"></i> يدوي
            </span>
        {% else %}
            <span class="badge bg-info ms-1" style="font-size: 0.7em;">
                <i class="fas fa-cog"></i> تلقائي
            </span>
        {% endif %}
    {% elif log.is_automatic %}
        <span class="badge bg-secondary" style="font-size: 0.85em;">
            <i class="fas fa-robot"></i> النظام (تلقائي)
        </span>
    {% else %}
        <span class="badge bg-warning text-dark" style="font-size: 0.85em;">
            <i class="fas fa-question-circle"></i> مستخدم غير محدد
        </span>
    {% endif %}
</div>
```

**الألوان:**
- 🔵 **أزرق (bg-primary)**: اسم المستخدم الحقيقي
- 🟢 **أخضر (bg-success)**: تغيير يدوي
- 🔷 **أزرق فاتح (bg-info)**: تغيير تلقائي (بواسطة مستخدم)
- ⚫ **رمادي (bg-secondary)**: النظام (تلقائي بالكامل)
- 🟡 **أصفر (bg-warning)**: مستخدم غير محدد

---

### 3. **إصلاح تعيين المستخدم في Manufacturing Views**

تم إضافة `order._changed_by = request.user` في جميع الأماكن التي يتم فيها تحديث حالة أمر التصنيع:

#### أ. **approve_or_reject_order** (السطر 1926-1959):
```python
if action == 'approve':
    order.status = 'pending'
    order.rejection_reason = None
    # Set the user who changed the status for the signal handler
    order._changed_by = request.user  # ⭐ جديد
    order.save()

elif action == 'reject':
    order.status = 'rejected'
    order.rejection_reason = reason
    # Set the user who changed the status for the signal handler
    order._changed_by = request.user  # ⭐ جديد
    order.save()
```

#### ب. **approve_after_rejection** (السطر 2317-2322):
```python
with transaction.atomic():
    # Reset rejection status and approve
    order.status = 'pending'
    # Set the user who changed the status for the signal handler
    order._changed_by = request.user  # ⭐ جديد
    order.save(update_fields=['status'])
```

#### ج. **update_order_status** (السطر 1564):
```python
# Set the user who changed the status for the signal handler
order._changed_by = request.user  # ✅ موجود بالفعل
```

---

## 📊 مقارنة العرض:

### الإشعارات:

| الحالة | قبل | بعد |
|--------|-----|-----|
| **مستخدم حقيقي** | نص رمادي صغير | 🔵 Badge أزرق مع أيقونة |
| **مستخدم النظام** | نص رمادي صغير | ⚫ Badge رمادي مع أيقونة روبوت |
| **التمييز** | صعب | واضح جداً |

### سجل الحالة:

| الحالة | قبل | بعد |
|--------|-----|-----|
| **مستخدم + يدوي** | نص + badge صغير | 🔵 Badge أزرق + 🟢 Badge أخضر |
| **مستخدم + تلقائي** | نص + لا شيء | 🔵 Badge أزرق + 🔷 Badge أزرق فاتح |
| **النظام (تلقائي)** | نص رمادي | ⚫ Badge رمادي مع روبوت |
| **غير محدد** | نص أصفر | 🟡 Badge أصفر |

---

## 🎨 الأيقونات المستخدمة:

| الأيقونة | المعنى |
|---------|--------|
| `fa-user` | مستخدم حقيقي |
| `fa-robot` | النظام (تلقائي) |
| `fa-hand-pointer` | تغيير يدوي |
| `fa-cog` | تغيير تلقائي |
| `fa-question-circle` | غير محدد |

---

## 📁 الملفات المعدلة:

### 1. **notifications/templates/notifications/list.html** (السطر 432-451)
- تحديث عرض المستخدم في قائمة الإشعارات
- إضافة badges ملونة مع أيقونات
- التمييز بين المستخدم الحقيقي والنظام

### 2. **notifications/templates/notifications/detail.html** (السطر 187-211)
- تحديث عرض المستخدم في تفاصيل الإشعار
- إضافة badges ملونة مع أيقونات
- عرض "مستخدم النظام" بشكل واضح

### 3. **orders/templates/orders/status_history.html** (السطر 493-520)
- تحديث عرض المستخدم في سجل حالة الطلب
- إضافة badges ملونة لاسم المستخدم
- تحسين عرض التغييرات اليدوية والتلقائية

### 4. **manufacturing/views.py** ⭐ **الأهم**
- **السطر 1930**: إضافة `_changed_by` في approve
- **السطر 1957**: إضافة `_changed_by` في reject
- **السطر 2320**: إضافة `_changed_by` في approve_after_rejection
- **السطر 1564**: تأكيد وجود `_changed_by` في update_order_status

### 5. **notifications/signals.py** ⭐ **الإصلاح الجذري**
- **السطر 368-376**: تغيير جذري في منطق الحصول على المستخدم
  - **قبل**: محاولة البحث في OrderStatusLog و AdminLog (غير موثوق)
  - **بعد**: استخدام `_changed_by` فقط من الـ view
  - **إذا لم يوجد مستخدم**: لا يتم إنشاء إشعار (return)
- **السطر 377-399**: تبسيط إنشاء الإشعار
  - إزالة الشرط `if changed_by` لأننا نتأكد من وجوده
  - تحديث `extra_data` لعرض اسم المستخدم الحقيقي

### 6. **orders/signals.py** ⭐ **منع السجلات التلقائية**
- **السطر 562-570**: تعطيل إنشاء `OrderStatusLog` في `sync_order_from_manufacturing`
  - **قبل**: كان يُنشئ سجل تلقائي عند مزامنة الحالة
  - **بعد**: لا يُنشئ سجل، فقط يحدث الحالة
  - **السبب**: نريد فقط السجلات الحقيقية من المستخدمين

- **السطر 1458-1464**: تعطيل `track_manufacturing_status_changes` signal
  - **قبل**: كان ينشئ سجل تلقائي عند تغيير حالة التصنيع
  - **بعد**: معطل بالكامل (pass)
  - **السبب**: السجل يُنشأ يدوياً في manufacturing/views.py مع المستخدم الحقيقي

### 7. **templates/base.html** ⭐ **القائمة المنسدلة للإشعارات**
- **السطر 720-741**: تحديث عرض المستخدم في القائمة المنسدلة
  - إضافة badges ملونة مع أيقونات
  - التمييز بين المستخدم الحقيقي والنظام
  - نفس التصميم المستخدم في صفحة الإشعارات

### 8. **manufacturing/views.py** ⭐ **تحسين إنشاء سجل الحالة**
- **السطر 1533-1565**: تحسين منطق إنشاء `OrderStatusLog`
  - **قبل**: كان يستخدم `tracking_status` الحالي كـ `old_status` (خطأ!)
  - **بعد**: يحسب `old_status` و `new_status` بشكل صحيح من mapping
  - **إضافة**: ينشئ السجل فقط إذا تغيرت حالة الطلب الأساسي
  - **إضافة**: يضيف `change_type='manufacturing'` للتمييز

---

## ✅ الاختبار:

```bash
python manage.py check
# ✅ System check identified no issues (0 silenced).
```

---

## 🎯 الفوائد:

| الميزة | الفائدة |
|--------|---------|
| **تمييز بصري واضح** | سهولة التعرف على المستخدم الحقيقي vs النظام |
| **ألوان مميزة** | فهم سريع لنوع التغيير |
| **أيقونات واضحة** | تحسين تجربة المستخدم |
| **اتساق في العرض** | نفس الأسلوب في جميع الصفحات |
| **معلومات دقيقة** | عرض اسم المستخدم الحقيقي دائماً |

---

## 📝 أمثلة على العرض:

### مثال 1: إشعار بتغيير حالة (مستخدم حقيقي)
```
┌─────────────────────────────────────────────────┐
│ 🔔 تحديث التصنيع: 9-0507-0014                  │
│                                                 │
│ [تغيير حالة] [عالي] [👤 أحمد محمد]            │
│                                                 │
│ تم تغيير حالة التصنيع من "قيد التصنيع"         │
│ إلى "جاهز للتركيب"                             │
└─────────────────────────────────────────────────┘
```

### مثال 2: إشعار بتغيير حالة (النظام)
```
┌─────────────────────────────────────────────────┐
│ 🔔 تحديث التصنيع: 9-0507-0015                  │
│                                                 │
│ [تغيير حالة] [عادي] [🤖 مستخدم النظام]        │
│                                                 │
│ تم تغيير الحالة تلقائياً                       │
└─────────────────────────────────────────────────┘
```

### مثال 3: سجل حالة الطلب
```
┌─────────────────────────────────────────────────┐
│ 📝 تغيير حالة                                  │
│                                                 │
│ من: قيد التصنيع → إلى: جاهز للتركيب           │
│                                                 │
│ [👤 أحمد محمد] [👆 يدوي]                      │
│ 📅 2025-10-13 11:30                            │
└─────────────────────────────────────────────────┘
```

---

## 🎊 النتيجة النهائية:

✅ **عرض واضح ومميز لاسم المستخدم:**
- 🔵 Badges ملونة للمستخدمين الحقيقيين
- ⚫ Badge رمادي مع أيقونة روبوت للنظام
- 🎨 أيقونات واضحة لكل نوع
- 📊 تمييز بصري فوري
- ✨ تجربة مستخدم محسّنة

**النظام جاهز للاستخدام! 🚀**

