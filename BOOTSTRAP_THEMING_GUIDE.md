# دليل تنسيق Bootstrap وتطبيق الثيمات

هذا الدليل يشرح كيفية عمل نظام الثيمات في التطبيق وكيفية التعامل مع مكونات Bootstrap بشكل يضمن التناسق في جميع أنحاء النظام.

## هيكل نظام الثيمات

### ملفات التنسيق الرئيسية

- **style.css** - يحتوي على تعريف متغيرات CSS لجميع الثيمات وتطبيق التنسيقات الأساسية
- **modern-black-theme.css** - تنسيقات خاصة بالثيم الأسود العصري
- **modern-black-fixes.css** - إصلاحات إضافية للتوافق مع الثيم الأسود العصري
- **extra-dark-fixes.css** - إصلاحات إضافية للنماذج والقوائم في الثيم الأسود

### الثيمات المتاحة

1. **الثيم الافتراضي (Default)** - ثيم بني دافئ
2. **الثيم الأسود العصري (Modern Black)** - ثيم داكن بألوان زاهية

## متغيرات CSS المستخدمة

### متغيرات CSS الرئيسية

```css
/* الألوان الأساسية */
--primary      /* اللون الرئيسي للثيم */
--secondary    /* لون ثانوي للثيم */
--accent       /* لون إبراز */
--background   /* لون خلفية الصفحة */
--surface      /* لون الأسطح مثل البطاقات والعناصر البارزة */
--card-bg      /* لون خلفية البطاقات */
--elevated-bg  /* لون خلفية العناصر البارزة */

/* ألوان النصوص */
--text-primary   /* لون النص الرئيسي */
--text-secondary /* لون النص الثانوي */
--text-tertiary  /* لون النص الأقل أهمية */

/* ألوان الحالة */
--success      /* لون النجاح - أخضر */
--warning      /* لون التحذير - أصفر/برتقالي */
--error        /* لون الخطأ - أحمر */
--info         /* لون المعلومات - أزرق */

/* الحدود والفواصل */
--border       /* لون الحدود العام */
--separator    /* لون الفواصل والخطوط */
--neutral      /* لون محايد للعناصر العامة */

/* التأثيرات */
--shadow       /* ظل عميق */
--shadow-light /* ظل خفيف */
--blur         /* تأثير الضبابية */
--radius       /* تقوس الحواف العادي */
--radius-large /* تقوس الحواف الكبير */
--transition   /* تأثير الانتقال الحركي */
```

## كيفية تطبيق الثيم

يتم تطبيق الثيم باستخدام خاصية `data-theme` على عنصر `body`. هناك وظيفة JavaScript `applyTheme(theme)` في ملف `main.js` تقوم بتطبيق الثيم المحدد وحفظه في `localStorage`.

```javascript
// تطبيق الثيم
function applyTheme(theme) {
    document.body.setAttribute('data-theme', theme);
}
```

## قواعد استخدام Bootstrap

لضمان توافق مكونات Bootstrap مع نظام الثيمات، اتبع هذه القواعد:

### 1. استخدم فئات Bootstrap الأساسية

استخدم فئات Bootstrap الأساسية دون تعديل:

```html
<button class="btn btn-primary">زر أساسي</button>
<div class="card">...</div>
<form class="form">...</form>
```

### 2. استخدم متغيرات CSS عند إنشاء أنماط مخصصة

```css
.custom-element {
    color: var(--text-primary);
    background-color: var(--surface);
    border: 1px solid var(--border);
}
```

### 3. تجنب تحديد الألوان المباشرة

بدلاً من:

```css
.element {
    color: #ffffff;
    background-color: #000000;
}
```

استخدم:

```css
.element {
    color: var(--text-primary);
    background-color: var(--background);
}
```

### 4. الاستثناءات

في بعض الحالات قد تحتاج إلى تطبيق أنماط خاصة بثيم معين، في هذه الحالة استخدم سمة data-theme:

```css
[data-theme="modern-black"] .special-element {
    /* تنسيقات خاصة بالثيم الأسود */
}
```

## ضمان تناسق التصميم

1. استخدم فقط الفئات المعتمدة من Bootstrap والمتغيرات المعرفة مسبقًا
2. تجنب إضافة أنماط مخصصة مباشرة على عناصر HTML
3. إذا كنت بحاجة لإضافة أنماط جديدة، أضفها إلى CSS الخاص بالمكون أو الصفحة
4. تجنب تجاوز أنماط Bootstrap الأساسية إلا عند الضرورة القصوى
5. استخدم `!important` فقط عندما يكون ضروريًا للتغلب على تسلسل CSS

## إضافة ثيم جديد

لإضافة ثيم جديد:

1. أضف تعريف متغيرات CSS للثيم الجديد في `style.css`:

```css
[data-theme="new-theme"] {
    --primary: #your-color;
    /* باقي المتغيرات */
}
```

2. أضف خيار الثيم الجديد في القائمة المنسدلة في `base.html`:

```html
<select id="themeSelector" class="form-select">
    <option value="default">الثيم الإفتراضي</option>
    <option value="modern-black">الثيم الأسود العصري</option>
    <option value="new-theme">الثيم الجديد</option>
</select>
```

3. أضف أي تنسيقات خاصة ضرورية للثيم الجديد في ملف CSS منفصل وقم بتضمينه في `base.html`.
