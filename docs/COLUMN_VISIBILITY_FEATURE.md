# ميزة إخفاء/إظهار الأعمدة الديناميكية
## Dynamic Column Visibility Feature

## 📋 نظرة عامة (Overview)

تم إضافة ميزة إدارة ظهور الأعمدة في جدول أوامر التصنيع، والتي تتيح للمستخدم:
- إخفاء أو إظهار أي عمود في الجدول ديناميكياً
- حفظ الإعدادات في المتصفح (localStorage)
- استرجاع الإعدادات تلقائياً عند العودة للصفحة
- إعادة تعيين الإعدادات للافتراضية

---

## 🎯 الموقع (Location)

**الملف المُحدَّث:**
```
manufacturing/templates/manufacturing/manufacturingorder_list.html
```

**موقع الزر:**
شريط الفلاتر الأفقي → زر "الأعمدة" (بجانب زر "متأخرة")

---

## ⚙️ المكونات الرئيسية (Main Components)

### 1. زر الأعمدة (Columns Button)
```html
<button type="button" class="hf-filter-btn" data-filter="columns" id="columnsBtn">
    <i class="fas fa-columns"></i>
    <span>الأعمدة</span>
    <i class="fas fa-chevron-down hf-chevron"></i>
</button>
```

**الموقع:** السطر 777

---

### 2. قائمة إعدادات الأعمدة (Columns Dropdown)
```html
<div class="hf-dropdown-panel" id="columnsDropdown">
    <!-- 17 checkbox للأعمدة المختلفة -->
</div>
```

**الموقع:** السطر 1016
**عدد الأعمدة المتاحة:** 17 عمود

---

### 3. الأعمدة المدعومة (Supported Columns)

| العمود (Column) | المعرّف (ID) | قابل للإخفاء |
|-----------------|--------------|--------------|
| # | `id` | ✅ نعم |
| رقم الطلب | `order_number` | ✅ نعم |
| النوع | `order_type` | ✅ نعم |
| رقم العقد | `contract_number` | ✅ نعم |
| خط الإنتاج | `production_line` | ✅ نعم |
| رقم الفاتورة | `invoice_number` | ✅ نعم |
| العميل | `customer` | ✅ نعم |
| البائع | `salesperson` | ✅ نعم |
| الفرع | `branch` | ✅ نعم |
| تاريخ الطلب | `order_date` | ✅ نعم |
| تاريخ التسليم | `expected_delivery_date` | ✅ نعم |
| مؤشر التسليم | `delivery_indicator` | ✅ نعم |
| الحالة | `status` | ✅ نعم |
| العناصر | `items` | ✅ نعم |
| معلومات التسليم | `delivery_info` | ✅ نعم |
| موافقة العقد | `contract_approval` | ✅ نعم |
| الإجراءات | `actions` | ✅ نعم |

---

## 🔧 الوظائف البرمجية (JavaScript Functions)

### 1. `loadColumnSettings()`
**الوظيفة:** تحميل إعدادات الأعمدة من localStorage

```javascript
const COLUMN_SETTINGS_KEY = 'manufacturing_orders_column_settings';

function loadColumnSettings() {
    const saved = localStorage.getItem(COLUMN_SETTINGS_KEY);
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            console.error('Failed to parse column settings:', e);
        }
    }
    return null;
}
```

---

### 2. `saveColumnSettings(settings)`
**الوظيفة:** حفظ إعدادات الأعمدة إلى localStorage

```javascript
function saveColumnSettings(settings) {
    localStorage.setItem(COLUMN_SETTINGS_KEY, JSON.stringify(settings));
}
```

**مثال البيانات المحفوظة:**
```json
{
  "id": true,
  "order_number": true,
  "customer": false,
  "salesperson": false,
  "branch": true
}
```

---

### 3. `applyColumnVisibility()`
**الوظيفة:** تطبيق إعدادات الظهور على الأعمدة

**آلية العمل:**
1. قراءة الإعدادات من localStorage
2. البحث عن جميع العناصر بـ `data-column="column_name"`
3. إخفاء أو إظهار العناصر باستخدام `display: none/''`
4. تحديث حالة الـ checkboxes

---

### 4. `initializeColumnToggles()`
**الوظيفة:** ربط أحداث التغيير بـ checkboxes

**يتم تنفيذها عند:**
- تحميل الصفحة (DOMContentLoaded)
- تغيير أي checkbox

**السلوك:**
```javascript
checkbox.addEventListener('change', function() {
    const column = this.dataset.column;
    const visible = this.checked;
    
    // Update UI
    const elements = document.querySelectorAll(`[data-column="${column}"]`);
    elements.forEach(el => {
        el.style.display = visible ? '' : 'none';
    });
    
    // Save to localStorage
    const settings = loadColumnSettings() || {};
    settings[column] = visible;
    saveColumnSettings(settings);
});
```

---

### 5. `selectAllColumns()`
**الوظيفة:** تحديد جميع الأعمدة (إظهار الكل)

```javascript
function selectAllColumns() {
    const checkboxes = document.querySelectorAll('.column-toggle');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change'));
    });
}
```

---

### 6. `resetColumnSettings()`
**الوظيفة:** إعادة تعيين الإعدادات للافتراضية

```javascript
function resetColumnSettings() {
    localStorage.removeItem(COLUMN_SETTINGS_KEY);
    // تحديد جميع الأعمدة
    selectAllColumns();
    // إغلاق القائمة
    document.getElementById('columnsBtn').click();
}
```

---

## 🎨 البنية HTML (HTML Structure)

### بنية الـ Table Header
```html
<th class="text-center sortable-header column-{column_name}" 
    data-sort="{sort_field}" 
    data-column="{column_name}">
    <span class="sort-icon none"></span>
    {Column Title}
</th>
```

### بنية الـ Table Body Cell
```html
<td class="column-{column_name}" data-column="{column_name}">
    {Cell Content}
</td>
```

**مثال واقعي:**
```html
<!-- Header -->
<th class="text-center sortable-header column-customer" 
    data-sort="customer" 
    data-column="customer">
    <span class="sort-icon none"></span>
    العميل
</th>

<!-- Body -->
<td class="column-customer" data-column="customer">
    <a href="...">محمد أحمد</a>
</td>
```

---

## 💾 التخزين المحلي (localStorage)

### المفتاح (Key)
```
manufacturing_orders_column_settings
```

### هيكل البيانات (Data Structure)
```json
{
  "id": true,
  "order_number": true,
  "order_type": false,
  "contract_number": true,
  "production_line": true,
  "invoice_number": false,
  "customer": true,
  "salesperson": false,
  "branch": true,
  "order_date": true,
  "expected_delivery_date": true,
  "delivery_indicator": false,
  "status": true,
  "items": true,
  "delivery_info": false,
  "contract_approval": false,
  "actions": true
}
```

**ملاحظة:** `true` = ظاهر، `false` = مخفي

---

## 🔄 تدفق العمل (Workflow)

### عند تحميل الصفحة
```
1. DOMContentLoaded Event
   ↓
2. initializeColumnToggles() - ربط الأحداث
   ↓
3. applyColumnVisibility() - تطبيق الإعدادات المحفوظة
   ↓
4. الجدول يظهر حسب الإعدادات المحفوظة
```

### عند تغيير إعداد عمود
```
1. المستخدم ينقر checkbox
   ↓
2. Change Event يُطلق
   ↓
3. تحديث UI (إخفاء/إظهار العمود)
   ↓
4. حفظ الإعداد في localStorage
   ↓
5. تحديث badge الـ label
```

### عند الضغط على "إعادة تعيين"
```
1. المستخدم ينقر "إعادة تعيين"
   ↓
2. حذف البيانات من localStorage
   ↓
3. تحديد جميع الـ checkboxes
   ↓
4. تطبيق التغييرات (إظهار كل الأعمدة)
   ↓
5. إغلاق القائمة المنسدلة
```

---

## 🎯 حالات الاستخدام (Use Cases)

### 1. إخفاء الأعمدة غير المهمة
**السيناريو:** مستخدم يركز فقط على رقم الطلب والحالة
```
الإجراء:
1. فتح قائمة "الأعمدة"
2. إلغاء تحديد جميع الأعمدة ما عدا:
   - رقم الطلب
   - الحالة
   - الإجراءات
3. إغلاق القائمة
النتيجة: جدول بسيط يعرض 3 أعمدة فقط
```

### 2. عرض مخصص للمحاسبة
```
الإجراء:
- إظهار: رقم الفاتورة، رقم العقد، العميل، معلومات التسليم
- إخفاء: البائع، خط الإنتاج، العناصر
النتيجة: عرض محاسبي مركّز
```

### 3. عرض مخصص للإنتاج
```
الإجراء:
- إظهار: خط الإنتاج، العناصر، تاريخ التسليم، مؤشر التسليم
- إخفاء: معلومات التسليم، موافقة العقد، رقم الفاتورة
النتيجة: عرض إنتاجي مركّز
```

---

## 🛠️ الصيانة والتطوير (Maintenance)

### إضافة عمود جديد

**1. في HTML - Table Header:**
```html
<th class="text-center column-new_column" data-column="new_column">
    عمود جديد
</th>
```

**2. في HTML - Table Body:**
```html
<td class="column-new_column" data-column="new_column">
    {محتوى العمود}
</td>
```

**3. في Columns Dropdown:**
```html
<label class="hf-checkbox-item column-toggle-item" data-column="new_column">
    <input type="checkbox" class="column-toggle" data-column="new_column" checked>
    عمود جديد
</label>
```

**ملاحظة:** لا حاجة لتعديل JavaScript - يعمل تلقائياً!

---

### إزالة عمود من التحكم

**الإجراء:**
1. احذف الـ checkbox من `columnsDropdown`
2. اترك `data-column` في الجدول (للتوافقية)
3. العمود سيبقى ظاهراً دائماً

---

## 🐛 استكشاف الأخطاء (Troubleshooting)

### المشكلة: الإعدادات لا تُحفظ
**الحل:**
```javascript
// تحقق من دعم localStorage
if (typeof(Storage) !== "undefined") {
    console.log("localStorage supported");
} else {
    console.error("localStorage NOT supported");
}
```

### المشكلة: عمود لا يختفي عند إلغاء تحديده
**الحل:**
```javascript
// تحقق من وجود data-column في كل من <th> و <td>
const column = 'customer';
const elements = document.querySelectorAll(`[data-column="${column}"]`);
console.log(`Found ${elements.length} elements for column: ${column}`);
// يجب أن يساوي: عدد الصفوف + 1 (header)
```

### المشكلة: الإعدادات تتداخل مع صفحات أخرى
**الحل:**
استخدم مفتاح localStorage مخصص لكل صفحة:
```javascript
// ✅ جيد
const COLUMN_SETTINGS_KEY = 'manufacturing_orders_column_settings';

// ❌ سيء (سيتداخل مع صفحات أخرى)
const COLUMN_SETTINGS_KEY = 'column_settings';
```

---

## 📊 الإحصائيات (Statistics)

- **عدد الأعمدة المدعومة:** 17 عمود
- **عدد الوظائف البرمجية:** 6 وظائف
- **حجم التعديلات:**
  - HTML: ~100 سطر (dropdown + data attributes)
  - JavaScript: ~110 سطر
  - CSS: يستخدم الأنماط الموجودة مسبقاً
- **التوافقية:** جميع المتصفحات الحديثة (Chrome, Firefox, Safari, Edge)

---

## ✅ الاختبارات (Testing)

### اختبار يدوي

**1. اختبار الحفظ:**
```
1. إخفاء 3 أعمدة
2. تحديث الصفحة (F5)
3. تحقق: الأعمدة الـ3 لا تزال مخفية ✅
```

**2. اختبار الإعادة:**
```
1. إخفاء عدة أعمدة
2. اضغط "إعادة تعيين"
3. تحقق: جميع الأعمدة ظاهرة ✅
```

**3. اختبار "تحديد الكل":**
```
1. إلغاء تحديد عدة أعمدة
2. اضغط "تحديد الكل"
3. تحقق: جميع الـ checkboxes محددة ✅
4. تحقق: جميع الأعمدة ظاهرة ✅
```

### اختبار برمجي (Console)

```javascript
// Test 1: Check localStorage
console.log(localStorage.getItem('manufacturing_orders_column_settings'));

// Test 2: Count visible columns
const visibleColumns = document.querySelectorAll('thead th:not([style*="display: none"])');
console.log(`Visible columns: ${visibleColumns.length}`);

// Test 3: Test hide/show programmatically
const checkbox = document.querySelector('.column-toggle[data-column="customer"]');
checkbox.checked = false;
checkbox.dispatchEvent(new Event('change'));
console.log('Customer column should be hidden now');
```

---

## 🔮 التحسينات المستقبلية (Future Enhancements)

1. **Presets (إعدادات جاهزة):**
   - عرض المحاسبة
   - عرض الإنتاج
   - عرض المبيعات
   
2. **Drag & Drop (إعادة ترتيب الأعمدة):**
   - السحب والإفلات لتغيير ترتيب الأعمدة

3. **Export/Import Settings:**
   - تصدير واستيراد الإعدادات كـ JSON

4. **Multi-user Sync:**
   - مزامنة الإعدادات عبر حسابات المستخدمين

---

## 📝 الملاحظات (Notes)

- **الأداء:** التطبيق سريع جداً حتى مع مئات الصفوف
- **التوافقية:** يعمل مع نظام الفرز (sorting) الموجود
- **RTL Support:** يدعم العربية بالكامل
- **Mobile Friendly:** يعمل على الهواتف المحمولة

---

## 👨‍💻 الكود المرجعي (Reference Code)

**الموقع الكامل للكود:**
```
manufacturing/templates/manufacturing/manufacturingorder_list.html
  - الأسطر 777-780: زر الأعمدة
  - الأسطر 1016-1092: قائمة الأعمدة
  - الأسطر 3057-3151: JavaScript Functions
```

**التبعيات (Dependencies):**
- Bootstrap 5 (للأنماط)
- Font Awesome (للأيقونات)
- jQuery (اختياري - لا يستخدمه الكود الجديد)

---

## 📞 الدعم (Support)

للمساعدة أو الإبلاغ عن مشاكل:
1. راجع قسم "استكشاف الأخطاء"
2. تحقق من console للأخطاء
3. تأكد من دعم المتصفح لـ localStorage

---

**آخر تحديث:** 2026-01-04  
**الإصدار:** 1.0  
**الحالة:** ✅ مستقر وجاهز للإنتاج
