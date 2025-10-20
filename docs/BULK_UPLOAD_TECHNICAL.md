# نظام رفع المنتجات - توثيق تقني

## 📋 نظرة عامة تقنية

هذا المستند يشرح التفاصيل التقنية لنظام رفع المنتجات بالجملة مع الأوضاع الثلاثة.

---

## 🏗️ البنية التقنية

### 1. النماذج (Forms)

**الملف:** `inventory/forms.py`

```python
class ProductExcelUploadForm(forms.Form):
    UPLOAD_MODE_CHOICES = [
        ('add_to_existing', _('إضافة للكميات الموجودة')),
        ('replace_quantity', _('استبدال الكميات')),
        ('new_only', _('المنتجات الجديدة فقط'))
    ]
    
    upload_mode = forms.ChoiceField(
        choices=UPLOAD_MODE_CHOICES,
        initial='add_to_existing',
        widget=forms.RadioSelect(...)
    )
```

**التغييرات:**
- ❌ إزالة: `overwrite_existing = BooleanField(...)`
- ✅ إضافة: `upload_mode = ChoiceField(...)`

---

### 2. المعالجة (Views)

**الملف:** `inventory/views_bulk.py`

#### دالة process_excel_upload()

**التوقيع:**
```python
def process_excel_upload(excel_file, default_warehouse, upload_mode, user):
```

**المعاملات:**
- `excel_file`: ملف Excel المرفوع
- `default_warehouse`: المستودع الافتراضي (optional)
- `upload_mode`: أحد القيم الثلاث ('add_to_existing', 'replace_quantity', 'new_only')
- `user`: المستخدم الذي يرفع الملف

---

### 3. منطق المعالجة

#### أ. منطق المنتج الموجود

```python
if code:
    try:
        product = Product.objects.get(code=code)
        product_exists = True
        
        # وضع: المنتجات الجديدة فقط - تجاهل الموجود
        if upload_mode == 'new_only':
            # تخطي
            continue
        
        # وضع: إضافة أو استبدال - تحديث البيانات
        elif upload_mode in ['add_to_existing', 'replace_quantity']:
            product.name = name
            product.price = price
            # ... تحديث باقي الحقول
            product.save()
            
    except Product.DoesNotExist:
        # منتج جديد - إنشاء في جميع الأوضاع
        product = Product.objects.create(...)
```

---

#### ب. منطق الكميات

##### 1. وضع "إضافة للموجود" (add_to_existing)

```python
# السلوك: إضافة الكمية مباشرة
StockTransaction.objects.create(
    product=product,
    warehouse=target_warehouse,
    transaction_type='in',
    quantity=quantity,  # الكمية من الملف
    ...
)

# النتيجة: running_balance يُحسب تلقائياً في Signal
# running_balance = previous_balance + quantity
```

---

##### 2. وضع "استبدال الكميات" (replace_quantity)

```python
if upload_mode == 'replace_quantity' and product_exists:
    # 1. الحصول على الرصيد الحالي
    last_transaction = StockTransaction.objects.filter(
        product=product,
        warehouse=target_warehouse
    ).order_by('-transaction_date').first()
    
    if last_transaction and last_transaction.running_balance > 0:
        current_balance = Decimal(str(last_transaction.running_balance))
        
        # 2. إنشاء معاملة خروج لتصفير الرصيد
        StockTransaction.objects.create(
            transaction_type='out',
            quantity=current_balance,  # كل الرصيد
            reason='adjustment',
            notes='تصفير الرصيد قبل استبدال الكمية'
        )

# 3. إنشاء معاملة دخول بالكمية الجديدة
StockTransaction.objects.create(
    transaction_type='in',
    quantity=quantity,  # الكمية الجديدة من الملف
    ...
)

# النتيجة:
# - معاملة خروج: running_balance = 0
# - معاملة دخول: running_balance = quantity (جديدة)
```

**مثال بالأرقام:**
```
الوضع الحالي:
  - running_balance = 70

معاملة 1 (out):
  - quantity = 70
  - running_balance = 70 - 70 = 0

معاملة 2 (in):
  - quantity = 35 (من الملف)
  - running_balance = 0 + 35 = 35

النتيجة النهائية: 35
```

---

##### 3. وضع "جديد فقط" (new_only)

```python
if upload_mode == 'new_only':
    if product_exists:
        # تخطي - لا يُنشأ StockTransaction
        continue
    else:
        # منتج جديد - معاملة دخول عادية
        StockTransaction.objects.create(...)
```

---

### 4. حساب الرصيد المتحرك (Running Balance)

**الآلية:**  
يتم حساب `running_balance` تلقائياً عبر **Django Signal** في `inventory/signals.py`.

```python
@receiver(post_save, sender=StockTransaction)
def update_running_balance(sender, instance, created, **kwargs):
    if created:
        def update_balances():
            from decimal import Decimal
            
            # 1. الحصول على الرصيد السابق
            previous_balance = StockTransaction.objects.filter(
                product=instance.product,
                transaction_date__lt=instance.transaction_date
            ).exclude(id=instance.id).order_by('-transaction_date').first()
            
            # 2. تحويل إلى Decimal لتجنب خطأ الجمع
            if previous_balance and previous_balance.running_balance:
                current_balance = Decimal(str(previous_balance.running_balance))
            else:
                current_balance = Decimal('0')
            
            quantity_decimal = Decimal(str(instance.quantity))
            
            # 3. حساب الرصيد الجديد
            if instance.transaction_type == 'in':
                instance.running_balance = current_balance + quantity_decimal
            else:
                instance.running_balance = current_balance - quantity_decimal
            
            # 4. حفظ بدون استدعاء Signal مرة أخرى
            StockTransaction.objects.filter(id=instance.id).update(
                running_balance=instance.running_balance
            )
            
            # 5. تحديث المعاملات اللاحقة
            # ...
        
        transaction.on_commit(update_balances)
```

**لماذا Signal؟**
- ✅ فصل المسؤوليات (separation of concerns)
- ✅ يعمل تلقائياً مع أي StockTransaction جديد
- ✅ يضمن صحة الحسابات دائماً
- ✅ لا حاجة لحسابات يدوية في views

---

## 🔄 تدفق البيانات (Data Flow)

### 1. رفع الملف

```
User → Form → View
  ↓
process_excel_upload(excel_file, warehouse, upload_mode, user)
```

### 2. إنشاء BulkUploadLog

```python
upload_log = BulkUploadLog.objects.create(
    upload_type='product_upload',
    file_name=excel_file.name,
    warehouse=default_warehouse,
    options={'upload_mode': upload_mode},
    created_by=user
)
```

### 3. قراءة Excel

```python
df = pd.read_excel(file_data, ...)
for index, row in df.iterrows():
    # معالجة كل صف
```

### 4. معالجة كل منتج

```
check if product exists (by code)
  ↓
├── exists & mode = 'new_only' → skip
├── exists & mode ∈ ['add_to_existing', 'replace_quantity'] → update
└── not exists → create

if quantity > 0:
    ↓
    if mode = 'replace_quantity' and exists:
        create StockTransaction (out) to zero balance
    
    create StockTransaction (in) with new quantity
```

### 5. Signal تلقائي

```
StockTransaction created
  ↓
post_save signal triggered
  ↓
update_running_balance() called
  ↓
calculate & save running_balance
```

### 6. إكمال الرفع

```python
upload_log.status = 'completed'
upload_log.statistics = {
    'total_rows': total,
    'created_count': created,
    'updated_count': updated,
    'skipped_count': skipped,
    'error_count': errors
}
upload_log.completed_at = timezone.now()
upload_log.save()
```

---

## 🗄️ قاعدة البيانات

### جداول ذات صلة

#### 1. Product
```sql
CREATE TABLE inventory_product (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE,
    name VARCHAR(255),
    price DECIMAL(10, 2),
    ...
);
```

#### 2. StockTransaction
```sql
CREATE TABLE inventory_stocktransaction (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES inventory_product(id),
    warehouse_id INTEGER REFERENCES inventory_warehouse(id),
    transaction_type VARCHAR(10),  -- 'in', 'out', 'transfer', 'adjustment'
    quantity DECIMAL(10, 2),
    running_balance DECIMAL(10, 2),  -- يُحسب تلقائياً
    transaction_date TIMESTAMP,
    ...
);
```

#### 3. BulkUploadLog
```sql
CREATE TABLE inventory_bulkuploadlog (
    id SERIAL PRIMARY KEY,
    upload_type VARCHAR(50),
    status VARCHAR(20),
    file_name VARCHAR(255),
    options JSONB,  -- {'upload_mode': '...'}
    statistics JSONB,  -- {'created_count': 10, ...}
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    ...
);
```

#### 4. BulkUploadError
```sql
CREATE TABLE inventory_bulkuploaderror (
    id SERIAL PRIMARY KEY,
    upload_log_id INTEGER REFERENCES inventory_bulkuploadlog(id),
    row_number INTEGER,
    error_type VARCHAR(50),
    result_status VARCHAR(20),  -- 'created', 'updated', 'skipped', 'failed'
    error_message TEXT,
    row_data JSONB,
    ...
);
```

---

## ⚡ تحسينات الأداء

### 1. إزالة الحسابات المتكررة

**قبل:**
```python
# كان يُحسب running_balance يدوياً في views
previous_transactions = StockTransaction.objects.filter(...)
previous_balance = ...
new_balance = previous_balance + quantity
transaction.running_balance = new_balance
transaction.save()
```

**بعد:**
```python
# فقط إنشاء المعاملة - Signal يتولى الحساب
StockTransaction.objects.create(...)
# running_balance يُحسب تلقائياً في Signal
```

**الفائدة:**
- ✅ تقليل الكود بمقدار ~30 سطر
- ✅ أسرع (لا استعلامات إضافية)
- ✅ أقل عرضة للأخطاء

---

### 2. Bulk Create للأخطاء

```python
errors_to_create = []
for row in df.iterrows():
    if error:
        errors_to_create.append(BulkUploadError(...))

# حفظ جميع الأخطاء دفعة واحدة
BulkUploadError.objects.bulk_create(errors_to_create)
```

**الفائدة:**
- ✅ استعلام واحد بدلاً من N استعلام
- ✅ أسرع بكثير مع ملفات كبيرة

---

### 3. تقليل Logging

```python
# إزالة print() غير ضرورية
# فقط logging للأخطاء والأحداث المهمة
```

---

## 🧪 الاختبار

### اختبار وضع "إضافة"

```python
# Setup
product = Product.objects.create(code='TEST-001', name='Test')
StockTransaction.objects.create(
    product=product,
    warehouse=warehouse,
    transaction_type='in',
    quantity=50
)

# Action
upload_file_with_mode(
    products=[{'code': 'TEST-001', 'quantity': 30}],
    mode='add_to_existing'
)

# Assert
assert product.get_stock(warehouse) == 80  # 50 + 30
```

---

### اختبار وضع "استبدال"

```python
# Setup
product = Product.objects.create(code='TEST-002', name='Test')
StockTransaction.objects.create(
    product=product,
    warehouse=warehouse,
    transaction_type='in',
    quantity=50
)

# Action
upload_file_with_mode(
    products=[{'code': 'TEST-002', 'quantity': 30}],
    mode='replace_quantity'
)

# Assert
transactions = StockTransaction.objects.filter(
    product=product,
    warehouse=warehouse
).order_by('transaction_date')

assert transactions.count() == 3  # original + out + in
assert transactions[1].transaction_type == 'out'
assert transactions[1].quantity == 50  # تصفير
assert transactions[2].transaction_type == 'in'
assert transactions[2].quantity == 30  # جديد
assert product.get_stock(warehouse) == 30  # النتيجة النهائية
```

---

### اختبار وضع "جديد فقط"

```python
# Setup
existing = Product.objects.create(code='TEST-003', name='Existing')

# Action
upload_file_with_mode(
    products=[
        {'code': 'TEST-003', 'quantity': 50},  # موجود
        {'code': 'TEST-004', 'quantity': 30}   # جديد
    ],
    mode='new_only'
)

# Assert
assert Product.objects.filter(code='TEST-003').exists()  # لم يُحدث
assert existing.get_stock(warehouse) == 0  # لم تُضف كمية

new_product = Product.objects.get(code='TEST-004')
assert new_product.get_stock(warehouse) == 30  # تم الإضافة
```

---

## 🐛 معالجة الأخطاء

### 1. أخطاء Decimal

```python
from decimal import Decimal

# تحويل آمن
try:
    quantity = Decimal(str(float(value)))
except (ValueError, TypeError):
    quantity = Decimal('0')
```

### 2. أخطاء المنتج غير موجود

```python
try:
    product = Product.objects.get(code=code)
except Product.DoesNotExist:
    # إنشاء منتج جديد
    product = Product.objects.create(...)
```

### 3. أخطاء المستودع

```python
if not target_warehouse:
    errors_to_create.append(BulkUploadError(
        error_type='invalid_data',
        error_message='لا يمكن تحديد المستودع'
    ))
    continue
```

---

## 📊 مراقبة الأداء

### Queries المتوقعة

لملف بـ 100 منتج:

| الوضع | Queries |
|-------|---------|
| **جديد فقط** (كل المنتجات جديدة) | ~300 |
| **إضافة** (50 موجود + 50 جديد) | ~400 |
| **استبدال** (كل المنتجات موجودة) | ~500 |

**لماذا الأعداد هذه؟**
- 1 query لكل منتج (get or create)
- 1-2 queries لكل StockTransaction
- 1 query لحفظ BulkUploadLog
- bulk_create للأخطاء (query واحد)

---

## 🔒 الأمان

### 1. التحقق من الصلاحيات

```python
@login_required
@permission_required('inventory.add_product')
def product_bulk_upload(request):
    ...
```

### 2. التحقق من الملف

```python
# حجم الملف
if file.size > 10 * 1024 * 1024:
    raise ValidationError('ملف كبير جداً')

# نوع الملف
if not file.name.endswith(('.xlsx', '.xls')):
    raise ValidationError('نوع ملف غير مدعوم')
```

### 3. SQL Injection

```python
# استخدام ORM دائماً - لا SQL مباشر
Product.objects.filter(code=code)  # ✅ آمن
```

---

## 📝 التوثيق للمطورين

### إضافة وضع جديد

لإضافة وضع رابع (مثل "تحديث الأسعار فقط"):

1. **أضف الخيار في forms.py:**
```python
UPLOAD_MODE_CHOICES = [
    # ... الأوضاع الموجودة
    ('update_prices_only', _('تحديث الأسعار فقط')),
]
```

2. **أضف المنطق في views_bulk.py:**
```python
elif upload_mode == 'update_prices_only':
    if product_exists:
        product.price = price
        product.save()
        # لا تُنشئ StockTransaction
    # تجاهل المنتجات الجديدة
```

3. **أضف اختبارات:**
```python
def test_update_prices_only_mode():
    # ...
```

---

## 🔄 تحديثات مستقبلية

### اقتراحات للتحسين:

1. **معالجة متزامنة (Async):**
   ```python
   # استخدام Celery لمعالجة الملفات الضخمة
   @shared_task
   def process_excel_upload_async(file_path, ...):
       ...
   ```

2. **Progress Bar:**
   ```python
   # WebSocket لعرض تقدم الرفع مباشرة
   channel_layer.group_send('upload_progress', {
       'type': 'upload.progress',
       'progress': percentage
   })
   ```

3. **Validation أفضل:**
   ```python
   # التحقق من البيانات قبل الرفع الفعلي
   def validate_excel_data(df):
       errors = []
       for index, row in df.iterrows():
           if not is_valid_price(row['السعر']):
               errors.append(...)
       return errors
   ```

---

**آخر تحديث:** 2025-10-20  
**المطور:** Factory Droid  
**الحالة:** ✅ Production Ready
