# تقرير الفحص الأمني الشامل للمشروع
**تاريخ الفحص**: 29 نوفمبر 2025  
**نوع المشروع**: Django CRM System

---

## 📊 ملخص تنفيذي

تم فحص **جميع ملفات** المشروع (Python و HTML) بشكل شامل وتم اكتشاف:

- ⚠️ **4 مشاكل عالية الخطورة (HIGH)** - تحتاج إصلاح فوري
- ⚡ **38 مشكلة متوسطة الخطورة (MEDIUM)** - يُنصح بإصلاحها
- ✅ **الحالة العامة**: المشروع آمن بشكل عام مع بعض التحسينات المطلوبة

---

## 🔴 المشاكل عالية الخطورة (يجب إصلاحها فوراً)

### 1. استعلامات SQL غير آمنة (SQL Injection)

**الملفات المتأثرة**:
- `odoo_db_manager/advanced_sync_service.py:201`
- `crm/management/commands/sequence_manager.py:266`
- `accounts/management/commands/reset_sequence.py:14`

**المشكلة**:
```python
# ❌ كود خطير
cursor.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}')
```

**الحل**:
```python
# ✅ كود آمن
cursor.execute('SELECT COALESCE(MAX(id), 0) + 1 FROM %s', [table_name])
# أو استخدام
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(
        sql.SQL('SELECT COALESCE(MAX(id), 0) + 1 FROM {}').format(
            sql.Identifier(table_name)
        )
    )
```

**الخطورة**: يمكن للمهاجم تنفيذ أوامر SQL خطيرة على قاعدة البيانات

---

### 2. استخدام دالة خطرة `__import__()`

**الملف المتأثر**: `accounts/management/commands/update_requirements.py:114`

**المشكلة**:
```python
# ❌ استخدام __import__() خطير
module = __import__(package_name)
```

**الحل**:
```python
# ✅ استخدام importlib بدلاً
import importlib
module = importlib.import_module(package_name)
```

**الخطورة**: يمكن استخدامها لتنفيذ كود ضار

---

## 🟡 المشاكل متوسطة الخطورة

### 1. استخدام innerHTML و |safe في القوالب (204 حالة)

**الملفات المتأثرة الرئيسية**:
- `templates/barcode_scanner_modal.html`
- `templates/home_old.html`
- `templates/base_backup.html`
- وملفات أخرى كثيرة

**المشكلة**:
```html
<!-- ❌ غير آمن -->
<div>{{ user_input|safe }}</div>
<script>element.innerHTML = userContent;</script>
```

**الحل**:
```html
<!-- ✅ آمن -->
<div>{{ user_input|escape }}</div>
<script>element.textContent = userContent;</script>
```

**الخطورة**: ثغرات XSS (Cross-Site Scripting)

---

### 2. رفع الملفات بدون تحقق كافٍ (131 ملف)

**الملفات الرئيسية**:
- `inventory/views_bulk.py`
- `orders/wizard_views.py`
- `backup_system/views.py`

**التوصية**:
```python
# ✅ إضافة التحقق من نوع الملف
ALLOWED_EXTENSIONS = {'.jpg', '.png', '.pdf', '.xlsx'}

def validate_file(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('نوع الملف غير مسموح')
    
    # التحقق من الحجم (مثال: 5MB)
    if file.size > 5 * 1024 * 1024:
        raise ValidationError('حجم الملف كبير جداً')
    
    # التحقق من نوع المحتوى
    import magic
    mime = magic.from_buffer(file.read(1024), mime=True)
    if mime not in ['image/jpeg', 'image/png', 'application/pdf']:
        raise ValidationError('نوع المحتوى غير صحيح')
```

---

## ✅ النقاط الإيجابية المكتشفة

1. ✓ **SECRET_KEY** يُقرأ من متغيرات البيئة
2. ✓ **DEBUG** يُقرأ من متغيرات البيئة
3. ✓ لا توجد كلمات مرور مكشوفة في الكود
4. ✓ حماية CSRF مُفعّلة في معظم النماذج
5. ✓ استخدام Django ORM في معظم الأماكن (آمن)
6. ✓ وجود نظام تسجيل شامل (logging)

---

## 🔧 خطة الإصلاح الشاملة

### المرحلة 1: إصلاح المشاكل عالية الخطورة (أولوية قصوى)

#### 1.1 إصلاح SQL Injection

**الملفات التي تحتاج إصلاح**:

```python
# File: odoo_db_manager/advanced_sync_service.py (خط 201)
# قبل:
cursor.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}')

# بعد:
from psycopg2 import sql
cursor.execute(
    sql.SQL('SELECT COALESCE(MAX(id), 0) + 1 FROM {}').format(
        sql.Identifier(table_name)
    )
)
```

```python
# File: crm/management/commands/sequence_manager.py (خط 266)
# قبل:
cursor.execute(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}')

# بعد:
from psycopg2 import sql
cursor.execute(
    sql.SQL('SELECT COALESCE(MAX(id), 0) + 1 FROM {}').format(
        sql.Identifier(table_name)
    )
)
```

```python
# File: accounts/management/commands/reset_sequence.py (خط 14)
# قبل:
cursor.execute(f"SELECT setval('accounts_user_id_seq', {max_id + 1}, false);")

# بعد:
cursor.execute("SELECT setval('accounts_user_id_seq', %s, false);", [max_id + 1])
```

#### 1.2 إصلاح استخدام __import__()

```python
# File: accounts/management/commands/update_requirements.py (خط 114)
# قبل:
module = __import__(package_name)

# بعد:
import importlib
try:
    module = importlib.import_module(package_name)
except ImportError:
    module = None
```

---

### المرحلة 2: تحسين أمان القوالب HTML

#### 2.1 استبدال innerHTML بـ textContent

**ملف**: `templates/barcode_scanner_modal.html`

```javascript
// قبل (غير آمن)
scanResult.innerHTML = '<div class="text-center">...</div>';

// بعد (آمن)
scanResult.textContent = ''; // أو
const div = document.createElement('div');
div.className = 'text-center';
div.textContent = 'النص هنا';
scanResult.appendChild(div);
```

#### 2.2 إزالة فلتر |safe إلا عند الضرورة القصوى

```django
<!-- قبل -->
{{ content|safe }}

<!-- بعد -->
{{ content }}  <!-- Django يقوم بـ escape تلقائياً -->

<!-- إذا كنت تحتاج حقاً HTML -->
{{ content|escape }}  <!-- أو استخدم bleach library للتنقية -->
```

---

### المرحلة 3: تحسين أمان رفع الملفات

#### 3.1 إنشاء وظيفة تحقق مركزية

أنشئ ملف: `core/file_validation.py`

```python
import os
import magic
from django.core.exceptions import ValidationError
from django.conf import settings

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.xlsx'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_uploaded_file(uploaded_file, allowed_extensions=None, max_size=None):
    """
    التحقق الشامل من الملفات المرفوعة
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS
    
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    # 1. التحقق من الامتداد
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f'نوع الملف غير مسموح. الأنواع المسموحة: {", ".join(allowed_extensions)}')
    
    # 2. التحقق من الحجم
    if uploaded_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(f'حجم الملف كبير جداً. الحد الأقصى: {max_mb}MB')
    
    # 3. التحقق من نوع المحتوى الفعلي
    uploaded_file.seek(0)
    mime_type = magic.from_buffer(uploaded_file.read(1024), mime=True)
    uploaded_file.seek(0)
    
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f'نوع محتوى الملف غير صحيح: {mime_type}')
    
    # 4. فحص اسم الملف من الأحرف الخطرة
    if any(char in uploaded_file.name for char in ['..', '/', '\\']):
        raise ValidationError('اسم الملف يحتوي على أحرف غير مسموحة')
    
    return True

def sanitize_filename(filename):
    """
    تنظيف اسم الملف
    """
    import unicodedata
    import re
    
    # إزالة المسافات وتحويلها لـ underscore
    filename = filename.replace(' ', '_')
    
    # إزالة الأحرف الخاصة
    filename = unicodedata.normalize('NFKD', filename)
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    return filename
```

#### 3.2 استخدام الوظيفة في الـ Views

```python
from core.file_validation import validate_uploaded_file, sanitize_filename

def upload_file_view(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        try:
            # التحقق من الملف
            validate_uploaded_file(uploaded_file)
            
            # تنظيف اسم الملف
            uploaded_file.name = sanitize_filename(uploaded_file.name)
            
            # حفظ الملف
            # ...
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('...')
```

---

### المرحلة 4: تحسينات إعدادات Django الأمنية

#### 4.1 تحديث `crm/settings.py`

أضف الإعدادات التالية:

```python
# ======================================
# إعدادات الأمان المحسّنة للإنتاج
# ======================================

if not DEBUG:
    # 1. إجبار HTTPS
    SECURE_SSL_REDIRECT = True
    
    # 2. HTTP Strict Transport Security
    SECURE_HSTS_SECONDS = 31536000  # سنة واحدة
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # 3. Cookies آمنة
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    
    # 4. حماية من Clickjacking
    X_FRAME_OPTIONS = 'DENY'
    
    # 5. منع MIME type sniffing
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # 6. فلتر XSS في المتصفح
    SECURE_BROWSER_XSS_FILTER = True
    
    # 7. Referrer Policy
    SECURE_REFERRER_POLICY = 'same-origin'
    
    # 8. Permissions Policy
    PERMISSIONS_POLICY = {
        'geolocation': [],
        'microphone': [],
        'camera': [],
    }

# ======================================
# إعدادات CSRF المحسّنة
# ======================================
CSRF_USE_SESSIONS = True
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SAMESITE = 'Strict'

# ======================================
# إعدادات كلمات المرور القوية
# ======================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # زيادة الحد الأدنى
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ======================================
# إعدادات رفع الملفات
# ======================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# قائمة الامتدادات المسموحة
ALLOWED_UPLOAD_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif',  # صور
    '.pdf',  # مستندات
    '.xlsx', '.xls',  # إكسل
    '.docx', '.doc',  # وورد
]

# ======================================
# Content Security Policy (CSP)
# ======================================
# تثبيت: pip install django-csp
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "code.jquery.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "cdn.jsdelivr.net")

# ======================================
# Rate Limiting (حماية من هجمات DDoS)
# ======================================
# تثبيت: pip install django-ratelimit
```

---

### المرحلة 5: إضافة فحص أمني دوري

#### 5.1 إنشاء أمر Django للفحص الأمني

أنشئ: `crm/management/commands/security_check.py`

```python
from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'فحص أمني للإعدادات والكود'

    def handle(self, *args, **kwargs):
        issues = []
        
        # 1. فحص DEBUG
        if settings.DEBUG:
            issues.append('⚠️  DEBUG مفعّل - يجب تعطيله في الإنتاج')
        
        # 2. فحص SECRET_KEY
        if settings.SECRET_KEY.startswith('dev-insecure'):
            issues.append('⚠️  SECRET_KEY يستخدم مفتاح التطوير')
        
        # 3. فحص ALLOWED_HOSTS
        if '*' in settings.ALLOWED_HOSTS:
            issues.append('⚠️  ALLOWED_HOSTS يسمح بجميع النطاقات')
        
        # 4. فحص إعدادات HTTPS
        if not settings.DEBUG:
            if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
                issues.append('⚠️  SECURE_SSL_REDIRECT غير مفعّل')
            
            if not getattr(settings, 'SESSION_COOKIE_SECURE', False):
                issues.append('⚠️  SESSION_COOKIE_SECURE غير مفعّل')
        
        # طباعة النتائج
        if issues:
            self.stdout.write(self.style.ERROR(f'\n🔴 تم العثور على {len(issues)} مشكلة أمنية:\n'))
            for issue in issues:
                self.stdout.write(self.style.WARNING(f'  - {issue}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ لم يتم العثور على مشاكل أمنية\n'))
```

**الاستخدام**:
```bash
python manage.py security_check
```

---

## 📋 قائمة المراجعة النهائية

### قبل النشر للإنتاج

- [ ] إصلاح جميع استعلامات SQL غير الآمنة
- [ ] استبدال `__import__()` بـ `importlib`
- [ ] مراجعة جميع استخدامات `innerHTML` و `|safe`
- [ ] إضافة التحقق من الملفات المرفوعة
- [ ] تفعيل جميع إعدادات الأمان في settings.py
- [ ] التأكد من DEBUG = False
- [ ] تحديد ALLOWED_HOSTS بدقة
- [ ] فحص جميع Permissions و Authentication
- [ ] تفعيل HTTPS وشهادة SSL
- [ ] تفعيل HSTS
- [ ] مراجعة جميع CSRF tokens
- [ ] تشغيل `python manage.py security_check`

---

## 🛡️ أدوات مساعدة للأمان

### 1. تثبيت المكتبات الأمنية

```bash
pip install django-csp  # Content Security Policy
pip install django-ratelimit  # حماية من DDoS
pip install python-magic  # التحقق من نوع الملفات
pip install bleach  # تنظيف HTML
pip install django-defender  # حماية من brute force
```

### 2. أدوات الفحص الأمني

```bash
# Bandit - فحص الكود Python
pip install bandit
bandit -r . -f json -o security_report.json

# Safety - فحص الثغرات في المكتبات
pip install safety
safety check

# Django Check
python manage.py check --deploy
```

---

## 📞 ملاحظات إضافية

### نقاط القوة في المشروع الحالي:
1. استخدام Django Framework (آمن بطبيعته)
2. فصل SECRET_KEY و DEBUG عن الكود
3. نظام صلاحيات متقدم
4. تسجيل شامل للأحداث
5. استخدام CSRF protection

### التوصيات العامة:
1. إجراء فحص أمني دوري (شهرياً على الأقل)
2. تحديث المكتبات بانتظام
3. تدريب المطورين على الممارسات الآمنة
4. عمل نسخ احتياطية دورية
5. مراجعة الكود قبل النشر (Code Review)
6. استخدام CI/CD مع فحص أمني تلقائي

---

## ✅ الخاتمة

**الحالة العامة**: المشروع **آمن بشكل عام** ✅

**المطلوب**:
- إصلاح 4 مشاكل عالية الخطورة (سهلة الإصلاح)
- تحسين 38 نقطة متوسطة الخطورة
- تطبيق التحسينات المقترحة

**الوقت المتوقع للإصلاح الكامل**: 2-3 أيام عمل

**أولوية التنفيذ**: 
1. المرحلة 1 (فوري - بضع ساعات)
2. المرحلة 4 (يوم واحد)
3. المرحلة 2 و 3 (يومان)

---

**تم إعداد التقرير بواسطة**: نظام الفحص الأمني الآلي  
**التاريخ**: 29 نوفمبر 2025
