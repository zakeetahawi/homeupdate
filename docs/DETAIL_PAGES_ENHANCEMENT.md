# Detail Pages Enhancement Documentation

## نظرة عامة

تم تحسين صفحات التفاصيل الثلاث الرئيسية في النظام بتصميم حديث احترافي يعتمد على البطاقات (Cards) مع تسلسل بصري واضح.

**التاريخ**: 2026-01-04  
**النسخة**: 1.0  
**المطور**: Sisyphus (OhMyOpenCode AI Agent)

---

## الصفحات المُحسّنة

### 1. صفحة تفاصيل الطلب (`orders/order_detail.html`)
- **Hero Header** مع أيقونة الطلب وحالة الطلب
- **KPI Tiles**: المبلغ الإجمالي، المدفوع، المتبقي، عدد العناصر
- **Info Cards** محسّنة: معلومات العميل، ملاحظات الطلب، ملاحظات العميل
- استخدام `kv-grid` بدلاً من الجداول في بعض البطاقات

### 2. صفحة تفاصيل العميل (`customers/customer_detail.html`)
- تحتفظ بالـ Header Card الموجود (ممتاز بالفعل)
- **KPI Tiles جديد**: إجمالي الطلبات، إجمالي المبيعات، الشكاوى، آخر طلب
- CSS محسّن للبطاقات الموجودة

### 3. صفحة تفاصيل المعاينة (`inspections/inspection_detail.html`)
- **Hero Header** مع أيقونة المعاينة ورقم العقد
- **KPI Tiles**: النتيجة، عدد الشبابيك، تاريخ الطلب، التسليم المتوقع
- ألوان ديناميكية حسب حالة المعاينة

---

## الملفات الجديدة المُنشأة

### 1. ملف CSS المشترك

**المسار**: `static/css/detail-pages.css`  
**الحجم**: 16 KB  
**الأسطر**: 670 سطر

#### المكونات الرئيسية:
- **Design Tokens**: متغيرات CSS للألوان، الأبعاد، الظلال
- **Hero Header**: قسم رأسي بتدرج لوني وأزرار إجراءات
- **KPI Tiles**: بطاقات إحصائية بـ 4 أنماط ألوان
- **Info Cards**: بطاقات معلومات مع رأس وأيقونة
- **Status Cards**: بطاقات مع حدود ملونة (6px) حسب الحالة
- **Key-Value Grid**: شبكة عرض البيانات (بدلاً من الجداول)
- **Timeline Component**: خط زمني للأحداث
- **Related Entities List**: قوائم العناصر المرتبطة
- **Sticky Action Bar**: شريط إجراءات ثابت
- **Mobile Responsive**: تصميم متجاوب للشاشات الصغيرة
- **Print Styles**: أنماط طباعة محسّنة
- **RTL Support**: دعم كامل للعربية (Right-to-Left)

---

### 2. المكونات القابلة لإعادة الاستخدام

#### `templates/components/detail_header.html`
**الغرض**: رأس Hero قابل لإعادة الاستخدام

**المعاملات**:
- `title`: العنوان الرئيسي (مطلوب)
- `subtitle`: عنوان فرعي (اختياري)
- `avatar_url`: رابط صورة (اختياري)
- `icon`: أيقونة Font Awesome (اختياري)
- `gradient`: تدرج لوني مخصص (اختياري)
- `status_badge`: شارة الحالة (اختياري)
- `actions`: أزرار الإجراءات (اختياري)

**مثال استخدام**:
```django
{% include 'components/detail_header.html' with icon='fas fa-shopping-cart' title='طلب رقم 12345' subtitle='العميل: أحمد محمد' status_badge=order_status %}
```

---

#### `templates/components/info_card.html`
**الغرض**: بطاقة معلومات قابلة لإعادة الاستخدام

**المعاملات**:
- `title`: عنوان البطاقة (اختياري)
- `icon`: أيقونة Font Awesome (اختياري)
- `card_class`: فئات CSS إضافية (اختياري)
- `content`: محتوى البطاقة (مطلوب)

**مثال استخدام**:
```django
{% include 'components/info_card.html' with icon='fas fa-user' title='معلومات العميل' content=customer_info_html %}
```

---

#### `templates/components/kv_list.html`
**الغرض**: قائمة مفتاح-قيمة باستخدام `<dl>`

**المعاملات**:
- `items`: قائمة من القواميس `[{'label': '...', 'value': '...'}]`
- `grid_class`: فئة شبكة CSS (اختياري: `kv-single-col`, `kv-two-col`)

**مثال استخدام**:
```django
{% include 'components/kv_list.html' with items=customer_data grid_class='kv-two-col' %}
```

---

## فئات CSS الرئيسية

### Hero Header Classes
```css
.detail-hero              /* حاوية Hero الرئيسية */
.detail-hero-content      /* محتوى Hero */
.detail-avatar            /* صورة أو أيقونة دائرية (44x44px) */
.actions                  /* حاوية الأزرار */
```

### KPI Tiles Classes
```css
.kpi-strip                /* حاوية الشريط الكامل */
.kpi-tile                 /* بطاقة KPI واحدة */
.kpi-tile.kpi-primary     /* نمط أزرق */
.kpi-tile.kpi-success     /* نمط أخضر */
.kpi-tile.kpi-warning     /* نمط أصفر */
.kpi-tile.kpi-danger      /* نمط أحمر */
.kpi-tile.kpi-info        /* نمط سماوي */
```

### Info Card Classes
```css
.info-card                /* بطاقة معلومات */
.info-card-header         /* رأس البطاقة */
.icon                     /* أيقونة */
```

### Status Card Classes
```css
.status-card              /* بطاقة مع حد ملون */
.status-card.status-success    /* حد أخضر */
.status-card.status-warning    /* حد أصفر */
.status-card.status-danger     /* حد أحمر */
.status-card.status-info       /* حد سماوي */
.status-card.status-pending    /* حد رمادي */
```

### Key-Value Grid Classes
```css
.kv-grid                  /* شبكة عرض البيانات */
.kv-grid.kv-single-col    /* عمود واحد */
.kv-grid.kv-two-col       /* عمودين */
dt                        /* مفتاح (Label) */
dd                        /* قيمة (Value) */
```

### Timeline Classes
```css
.timeline                 /* حاوية الخط الزمني */
.timeline-item            /* عنصر في الخط الزمني */
.time                     /* الوقت */
.event                    /* اسم الحدث */
.description              /* وصف الحدث */
```

### Utility Classes
```css
.detail-spacer-sm         /* مسافة صغيرة (0.75rem) */
.detail-spacer-md         /* مسافة متوسطة (1rem) */
.detail-spacer-lg         /* مسافة كبيرة (1.5rem) */
.detail-spacer-xl         /* مسافة كبيرة جداً (2rem) */
.detail-text-muted        /* نص رمادي */
.detail-text-primary      /* نص أزرق */
.detail-text-success      /* نص أخضر */
.detail-divider           /* خط فاصل مع تدرج */
```

---

## Design Tokens (متغيرات CSS)

### الأبعاد والمسافات
```css
--detail-spacing-xs: 0.5rem;
--detail-spacing-sm: 0.75rem;
--detail-spacing-md: 1rem;
--detail-spacing-lg: 1.5rem;
--detail-spacing-xl: 2rem;
```

### Border Radius
```css
--detail-radius-sm: 8px;
--detail-radius-md: 12px;
--detail-radius-lg: 16px;
--detail-radius-xl: 20px;
```

### Shadows
```css
--detail-shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.05);
--detail-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
--detail-shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.08);
--detail-shadow-card: 0 2px 12px rgba(0, 0, 0, 0.04);
```

### Status Colors
```css
--status-success: #28a745;
--status-warning: #ffc107;
--status-danger: #dc3545;
--status-info: #17a2b8;
--status-pending: #6c757d;
```

---

## دعم RTL (العربية)

جميع المكونات تدعم RTL بالكامل:

- استخدام `inline-start` و `inline-end` بدلاً من `left` و `right`
- `flex-direction: row-reverse` للعناصر في RTL
- اتجاه التدرجات اللونية يتكيف مع الاتجاه
- الحدود الملونة تظهر على الجانب الصحيح

---

## التوافق مع الشاشات

### Desktop (> 768px)
- KPI Tiles: 4 أعمدة
- Info Cards: عمودين
- Key-Value Grid: عمودين

### Tablet (481px - 768px)
- KPI Tiles: عمودين
- Info Cards: عمود واحد
- Key-Value Grid: عمود واحد

### Mobile (< 480px)
- KPI Tiles: عمود واحد
- Info Cards: عمود واحد
- Key-Value Grid: عمود واحد

---

## التوافق مع الطباعة

عند طباعة الصفحة:
- Hero Header يصبح خلفية بيضاء
- إخفاء أزرار الإجراءات
- إزالة الظلال
- تجنب تقسيم البطاقات عبر الصفحات

---

## كيفية الاستخدام في صفحات جديدة

### الخطوة 1: إضافة CSS
```django
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/detail-pages.css' %}">
{% endblock %}
```

### الخطوة 2: إضافة Hero Header
```django
<div class="detail-hero">
    <div class="detail-hero-content">
        <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
            <div class="d-flex align-items-center gap-3">
                <div class="detail-avatar d-flex align-items-center justify-content-center bg-white text-primary">
                    <i class="fas fa-icon-name fs-3"></i>
                </div>
                <div>
                    <h1 class="mb-1">العنوان</h1>
                    <p class="subtitle mb-0">العنوان الفرعي</p>
                </div>
            </div>
            <div>
                {% get_status_badge object.status "type" %}
            </div>
        </div>
        
        <div class="actions mt-3">
            <!-- الأزرار هنا -->
        </div>
    </div>
</div>
```

### الخطوة 3: إضافة KPI Tiles
```django
<div class="kpi-strip">
    <div class="kpi-tile kpi-primary">
        <div class="icon"><i class="fas fa-icon"></i></div>
        <div class="value">{{ value }}</div>
        <div class="label">التسمية</div>
    </div>
    <!-- كرر حسب الحاجة -->
</div>
```

### الخطوة 4: إضافة Info Cards
```django
<div class="info-card">
    <div class="info-card-header">
        <i class="fas fa-icon icon"></i>
        <h3>العنوان</h3>
    </div>
    <dl class="kv-grid kv-two-col">
        <div>
            <dt>المفتاح</dt>
            <dd>القيمة</dd>
        </div>
    </dl>
</div>
```

---

## أفضل الممارسات

### ✅ افعل:
- استخدم `<dl>` للبيانات المهيكلة بدلاً من `<table>`
- أضف أيقونات Font Awesome للوضوح البصري
- استخدم `detail-text-muted` للقيم الفارغة (—)
- حافظ على 4 KPI tiles كحد أقصى للوضوح
- استخدم status-card للبطاقات ذات الأولوية/الحالة

### ❌ لا تفعل:
- لا تستخدم `as any` أو `@ts-ignore`
- لا تستخدم `left`/`right` مباشرة (استخدم logical properties)
- لا تنسخ البطاقات الكبيرة المعقدة (استخدم المكونات)
- لا تضع أكثر من 6 أقسام رئيسية في صفحة واحدة
- لا تستخدم ظلال ثقيلة أو تدرجات متعددة

---

## الاختبار

### اختبارات يدوية مطلوبة:
1. ✅ عرض الصفحة على Desktop
2. ✅ عرض الصفحة على Tablet
3. ✅ عرض الصفحة على Mobile
4. ✅ اختبار اتجاه RTL
5. ✅ اختبار الطباعة
6. ✅ اختبار الأزرار والروابط
7. ✅ اختبار الألوان مع الحالات المختلفة

### الأوامر:
```bash
# تشغيل الخادم
python manage.py runserver

# فتح الصفحات في المتصفح
# http://127.0.0.1:8000/orders/<order_id>/
# http://127.0.0.1:8000/customers/<customer_id>/
# http://127.0.0.1:8000/inspections/<inspection_id>/
```

---

## الصيانة المستقبلية

### إضافة صفحات جديدة:
1. اتبع نفس البنية (Hero → KPI → Cards)
2. استخدم المكونات القابلة لإعادة الاستخدام
3. التزم بـ Design Tokens الموجودة
4. حافظ على دعم RTL

### تعديل الألوان:
عدّل المتغيرات في `detail-pages.css`:
```css
:root {
  --status-success: #your-color;
}
```

### إضافة مكونات جديدة:
1. أنشئ ملف في `templates/components/`
2. اتبع نفس نمط المكونات الموجودة
3. وثّق المعاملات والاستخدام

---

## المراجع

- **Oracle Recommendations**: توصيات معمارية من GPT-5.2
- **Bootstrap 5**: الإطار الأساسي المُستخدم
- **Font Awesome**: الأيقونات المُستخدمة
- **Google Fonts**: خط Tajawal للعربية

---

## الترخيص

جزء من نظام الخواجه ERP - 2026

---

**آخر تحديث**: 2026-01-04  
**الإصدار**: 1.0.0
