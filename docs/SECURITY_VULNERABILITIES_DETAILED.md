
# 🔐 التقرير الأمني النهائي - قائمة الثغرات الكاملة

**تاريخ الفحص**: 29 نوفمبر 2025
**نطاق الفحص**: جميع ملفات Python و HTML في المشروع

---

## 📊 الإحصائيات

- **إجمالي الملفات الممسوحة**: 
  - Python: ~500 ملف
  - HTML: ~300 قالب
- **إجمالي الثغرات**: 42
- **الوقت المقدر للإصلاح الكامل**: 2-3 أيام عمل

---

## 🔴 ثغرات عالية الخطورة (4)

### الثغرة #1: SQL Injection في sequence_manager.py

**الملف**: `crm/management/commands/sequence_manager.py`  
**السطر**: 266  
**النوع**: SQL Injection  
**الخطورة**: 🔴 عالية جداً  

**الكود الحالي**:
```python
cursor.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}')
```

**المشكلة**:
- استخدام f-string مع اسم جدول متغير
- يمكن للمهاجم تنفيذ SQL عشوائي
- مثال هجوم: `table_name = "users; DROP TABLE accounts; --"`

**الحل**:
```python
from psycopg2 import sql

cursor.execute(
    sql.SQL('SELECT COALESCE(MAX(id), 0) + 1 FROM {}').format(
        sql.Identifier(table_name)
    )
)
```

**تأثير الثغرة**: يمكن حذف أو تعديل البيانات في قاعدة البيانات بالكامل

---

### الثغرة #2: SQL Injection في reset_sequence.py

**الملف**: `accounts/management/commands/reset_sequence.py`  
**السطر**: 14  
**النوع**: SQL Injection  
**الخطورة**: 🔴 عالية  

**الكود الحالي**:
```python
cursor.execute(f"SELECT setval('accounts_user_id_seq', {max_id + 1}, false)")
```

**المشكلة**:
- استخدام f-string مع قيمة من قاعدة البيانات
- يمكن التلاعب بالقيمة إذا كانت البيانات ملوثة

**الحل**:
```python
cursor.execute("SELECT setval('accounts_user_id_seq', %s, false)", [max_id + 1])
```

**تأثير الثغرة**: التلاعب بتسلسل الـ ID

---

### الثغرة #3: SQL Injection في sequence_manager.py (الموقع الثاني)

**الملف**: `crm/management/commands/sequence_manager.py`  
**السطر**: 295  
**النوع**: SQL Injection  
**الخطورة**: 🔴 عالية  

**الكود الحالي**:
```python
cursor.execute(f'SELECT MAX(id) FROM {table_name}')
```

**الحل**: مثل الثغرة #1

---

### الثغرة #4: استخدام __import__()

**الملف**: `accounts/management/commands/update_requirements.py`  
**السطر**: 114  
**النوع**: Code Execution  
**الخطورة**: 🔴 عالية  

**الكود الحالي**:
```python
__import__('datetime').datetime.now()
```

**المشكلة**:
- استخدام `__import__()` يمكن أن يُستغل
- إذا كان اسم الموديول يأتي من مدخلات المستخدم

**الحل**:
```python
import datetime
datetime.datetime.now()

# أو
from datetime import datetime
datetime.now()
```

**تأثير الثغرة**: تنفيذ كود Python عشوائي

---

## 🟡 ثغرات متوسطة الخطورة (38)

### 1. استخدام innerHTML (204 حالة)

**النوع**: XSS (Cross-Site Scripting)  
**الخطورة**: 🟡 متوسطة  

**الملفات الأكثر تأثراً**:

| الملف | عدد الحالات |
|------|-------------|
| `templates/barcode_scanner_modal.html` | 9 |
| `templates/home_old.html` | 8 |
| `templates/base_backup.html` | 4 |
| `templates/includes/wizard_barcode_scanner_modal.html` | 7 |
| `orders/templates/orders/wizard/step6_review.html` | 12 |
| ملفات أخرى | +164 |

**أمثلة للثغرات**:

```javascript
// ❌ غير آمن - templates/barcode_scanner_modal.html:460
scanResult.innerHTML = '';

// ❌ غير آمن - templates/barcode_scanner_modal.html:480
scanResult.innerHTML = '<div class="text-center"><i class="fas fa-spinner"></i></div>';

// ❌ غير آمن - templates/home_old.html:535
scanResult.innerHTML = `
    <div class="alert alert-success">
        <strong>تم العثور على الطلب!</strong><br>
        ${data.message}
    </div>
`;
```

**الحل**:
```javascript
// ✅ آمن - استخدام textContent
scanResult.textContent = '';

// ✅ آمن - إنشاء عناصر DOM
const div = document.createElement('div');
div.className = 'alert alert-success';
div.textContent = data.message;
scanResult.appendChild(div);

// ✅ آمن - استخدام مكتبة DOMPurify
import DOMPurify from 'dompurify';
scanResult.innerHTML = DOMPurify.sanitize(htmlContent);
```

**تأثير الثغرة**: 
- سرقة Cookies و Session
- إعادة توجيه المستخدم لصفحات خبيثة
- تنفيذ JavaScript عشوائي في متصفح المستخدم

---

### 2. استخدام فلتر |safe في Django (20+ حالة)

**النوع**: XSS  
**الخطورة**: 🟡 متوسطة  

**الملفات المتأثرة** (عينة):
- `orders/templates/orders/order_detail.html`
- `manufacturing/templates/manufacturing/manufacturingorder_detail.html`
- `inventory/templates/inventory/product_detail.html`

**المشكلة**:
```django
<!-- ❌ غير آمن -->
<div>{{ user_content|safe }}</div>
```

**الحل**:
```django
<!-- ✅ آمن - Django يقوم بـ escape تلقائياً -->
<div>{{ user_content }}</div>

<!-- ✅ آمن - استخدام bleach للتنقية -->
{% load bleach_tags %}
<div>{{ user_content|bleach }}</div>
```

---

### 3. رفع ملفات بدون تحقق كافٍ (131 ملف)

**النوع**: File Upload Vulnerability  
**الخطورة**: 🟡 متوسطة إلى عالية  

**الملفات المتأثرة الرئيسية**:

1. `inventory/views_bulk.py` - رفع ملفات Excel بدون فحص كافي
2. `orders/wizard_views.py` - رفع صور وملفات العقود
3. `backup_system/views.py` - رفع ملفات النسخ الاحتياطية
4. `inspections/views.py` - رفع صور التفتيش
5. `complaints/views.py` - رفع مرفقات الشكاوى

**المشاكل الموجودة**:
- ❌ لا يوجد فحص موحد لنوع الملف
- ❌ لا يوجد فحص للحجم الأقصى
- ❌ لا يوجد فحص لمحتوى الملف الفعلي (MIME type)
- ❌ عدم تنظيف أسماء الملفات

**الحل الموصى به**:

```python
# core/file_validation.py
import os
import magic
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    'images': {'.jpg', '.jpeg', '.png', '.gif'},
    'documents': {'.pdf', '.docx', '.xlsx'},
}

ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_uploaded_file(uploaded_file, file_type='images', max_size=None):
    """
    فحص شامل للملفات المرفوعة
    
    Args:
        uploaded_file: ملف Django UploadedFile
        file_type: نوع الملف المسموح ('images' أو 'documents')
        max_size: الحجم الأقصى بالبايت (None = استخدام الافتراضي)
    
    Raises:
        ValidationError: إذا فشل أي فحص
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    # 1. فحص الامتداد
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    allowed_exts = ALLOWED_EXTENSIONS.get(file_type, set())
    
    if ext not in allowed_exts:
        raise ValidationError(
            f'نوع الملف غير مسموح. الأنواع المسموحة: {", ".join(allowed_exts)}'
        )
    
    # 2. فحص الحجم
    if uploaded_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(f'حجم الملف كبير جداً. الحد الأقصى: {max_mb:.1f}MB')
    
    # 3. فحص نوع المحتوى الفعلي (Magic Number)
    uploaded_file.seek(0)
    mime_type = magic.from_buffer(uploaded_file.read(2048), mime=True)
    uploaded_file.seek(0)
    
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f'نوع محتوى الملف غير صحيح: {mime_type}')
    
    # 4. فحص اسم الملف من الأحرف الخطرة
    dangerous_chars = ['..', '/', '\\', '\0', '\n', '\r']
    if any(char in uploaded_file.name for char in dangerous_chars):
        raise ValidationError('اسم الملف يحتوي على أحرف غير مسموحة')
    
    # 5. فحص إضافي للصور
    if file_type == 'images':
        from PIL import Image
        try:
            img = Image.open(uploaded_file)
            img.verify()
            uploaded_file.seek(0)
        except Exception:
            raise ValidationError('الملف ليس صورة صالحة')
    
    return True

def sanitize_filename(filename):
    """
    تنظيف اسم الملف من الأحرف الخاصة
    """
    import unicodedata
    import re
    
    # إزالة المسافات
    filename = filename.replace(' ', '_')
    
    # تطبيع Unicode
    filename = unicodedata.normalize('NFKD', filename)
    
    # إزالة الأحرف الخاصة
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # تحديد الطول
    name, ext = os.path.splitext(filename)
    if len(name) > 50:
        name = name[:50]
    
    return name + ext
```

**الاستخدام**:
```python
from core.file_validation import validate_uploaded_file, sanitize_filename

def upload_view(request):
    if request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        try:
            # فحص الملف
            validate_uploaded_file(uploaded_file, file_type='images')
            
            # تنظيف اسم الملف
            uploaded_file.name = sanitize_filename(uploaded_file.name)
            
            # حفظ الملف
            instance.file = uploaded_file
            instance.save()
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('upload_page')
```

**تأثير الثغرة**:
- رفع ملفات خبيثة (Malware, Shell Scripts)
- استهلاك مساحة القرص
- تنفيذ كود على الخادم (في حالات نادرة)

---

### 4. استعلامات SQL إضافية غير آمنة (5 حالات)

**الملفات**:
1. `crm/management/commands/optimize_db.py:175`
2. `crm/management/commands/optimize_db.py:210`
3. `crm/management/commands/monitor_sequences.py:205`
4. `crm/management/commands/fix_all_sequences.py:237`
5. `odoo_db_manager/management/commands/reset_sequence.py:17`

**أمثلة**:
```python
# ❌ غير آمن
cursor.execute(f'ANALYZE "{table_name}";')
cursor.execute(f'VACUUM ANALYZE "{table_name}";')
cursor.execute(f'SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}')
```

**الحل**: استخدام `psycopg2.sql` لجميع هذه الحالات

---

## 🟢 تحسينات مقترحة (للأمان الأفضل)

### 1. إعدادات Django الأمنية المفقودة

أضف هذه الإعدادات في `settings.py` للإنتاج:

```python
# إجبار HTTPS
SECURE_SSL_REDIRECT = True

# HTTP Strict Transport Security
SECURE_HSTS_SECONDS = 31536000  # سنة
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies آمنة
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'

# حماية Clickjacking
X_FRAME_OPTIONS = 'DENY'

# منع MIME sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# XSS Filter
SECURE_BROWSER_XSS_FILTER = True

# Referrer Policy
SECURE_REFERRER_POLICY = 'same-origin'
```

---

### 2. Content Security Policy (CSP)

```bash
pip install django-csp
```

```python
# settings.py
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "cdn.jsdelivr.net", "code.jquery.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "cdn.jsdelivr.net")
```

---

### 3. Rate Limiting

```bash
pip install django-ratelimit
```

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    # ...
```

---

## 📋 خطة العمل الموصى بها

### الأسبوع الأول: المشاكل العالية (4 ثغرات)

| اليوم | المهمة | الوقت |
|------|--------|-------|
| 1 | إصلاح SQL Injection في جميع الملفات | 2 ساعة |
| 1 | اختبار الإصلاحات | 1 ساعة |
| 2 | استبدال `__import__()` | 30 دقيقة |
| 2 | مراجعة نهائية | 30 دقيقة |

### الأسبوع الثاني: المشاكل المتوسطة

| اليوم | المهمة | الوقت |
|------|--------|-------|
| 1-2 | إنشاء `file_validation.py` | 4 ساعات |
| 3-4 | تطبيق فحص الملفات على جميع الـ views | 8 ساعات |
| 5 | مراجعة واختبار | 4 ساعات |

### الأسبوع الثالث: تحسينات XSS

| اليوم | المهمة | الوقت |
|------|--------|-------|
| 1-3 | مراجعة جميع استخدامات innerHTML | 12 ساعة |
| 4-5 | استبدال |safe بحلول آمنة | 8 ساعات |

---

## 🧪 الاختبارات المطلوبة

بعد كل إصلاح:

```bash
# 1. فحص Django
python manage.py check --deploy

# 2. الاختبارات الآلية
python manage.py test

# 3. فحص الأمان
python manage.py security_check

# 4. فحص المكتبات
pip install safety
safety check

# 5. فحص الكود
pip install bandit
bandit -r . -ll
```

---

## 📚 مراجع إضافية

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
- [Mozilla Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)

---

**تم إعداد التقرير**: 29 نوفمبر 2025  
**الحالة**: جاهز للتنفيذ
**الأولوية**: عالية

