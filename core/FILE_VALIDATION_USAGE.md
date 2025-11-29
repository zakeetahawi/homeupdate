# دليل استخدام نظام فحص الملفات المرفوعة

## 📦 التثبيت

### المكتبات المطلوبة (اختيارية للفحص المتقدم):

```bash
pip install python-magic  # للفحص المتقدم لنوع الملف
pip install Pillow        # للتحقق من الصور
```

---

## 📖 الاستخدام

### 1. الاستخدام الأساسي في Django Views

```python
from django.shortcuts import render, redirect
from django.contrib import messages
from core.file_validation import validate_uploaded_file, sanitize_filename

def upload_file_view(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        try:
            # فحص الملف
            validate_uploaded_file(uploaded_file, file_type='all')
            
            # تنظيف اسم الملف
            uploaded_file.name = sanitize_filename(uploaded_file.name)
            
            # حفظ الملف
            instance = MyModel()
            instance.file = uploaded_file
            instance.save()
            
            messages.success(request, 'تم رفع الملف بنجاح!')
            return redirect('success_page')
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('upload_page')
    
    return render(request, 'upload.html')
```

---

### 2. فحص الصور فقط

```python
from core.file_validation import validate_uploaded_file

def upload_profile_picture(request):
    if request.FILES.get('photo'):
        photo = request.FILES['photo']
        
        try:
            # فحص أن الملف صورة فقط
            validate_uploaded_file(photo, file_type='images', max_size=5*1024*1024)  # 5MB
            
            # حفظ الصورة
            user.profile_picture = photo
            user.save()
            
            messages.success(request, 'تم تحديث صورة الملف الشخصي!')
            
        except ValidationError as e:
            messages.error(request, f'خطأ في الصورة: {e}')
```

---

### 3. فحص المستندات فقط

```python
def upload_document(request):
    if request.FILES.get('document'):
        doc = request.FILES['document']
        
        try:
            # فحص المستندات فقط (PDF, Word, Excel)
            validate_uploaded_file(doc, file_type='documents', max_size=10*1024*1024)
            
            # حفظ المستند
            order.contract_file = doc
            order.save()
            
        except ValidationError as e:
            messages.error(request, str(e))
```

---

### 4. الاستخدام في Django Forms

```python
from django import forms
from core.file_validation import validate_uploaded_file

class UploadForm(forms.Form):
    file = forms.FileField()
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # فحص الملف
            validate_uploaded_file(file, file_type='images', max_size=5*1024*1024)
        
        return file

# في View
def upload_view(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            # الملف آمن الآن
            file = form.cleaned_data['file']
            # حفظ...
    else:
        form = UploadForm()
    
    return render(request, 'upload.html', {'form': form})
```

---

### 5. الاستخدام في Django Models

```python
from django.db import models
from core.file_validation import get_safe_file_path

class Document(models.Model):
    # استخدام get_safe_file_path لتوليد مسار آمن تلقائياً
    file = models.FileField(upload_to=get_safe_file_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # فحص إضافي عند الحفظ
        if self.file:
            from core.file_validation import validate_uploaded_file
            validate_uploaded_file(self.file)
```

---

### 6. الفحص السريع (مبسط)

```python
from core.file_validation import quick_validate

def simple_upload(request):
    if request.FILES.get('file'):
        file = request.FILES['file']
        
        try:
            # فحص سريع
            quick_validate(file, allowed_extensions=['.jpg', '.png'], max_size_mb=5)
            
            # حفظ...
            
        except ValidationError as e:
            messages.error(request, str(e))
```

---

## 🎨 أمثلة متقدمة

### مثال 1: رفع صورة المنتج

```python
from django.views.generic import CreateView
from core.file_validation import validate_uploaded_file, sanitize_filename

class ProductCreateView(CreateView):
    model = Product
    fields = ['name', 'image', 'price']
    
    def form_valid(self, form):
        # فحص الصورة قبل الحفظ
        if 'image' in self.request.FILES:
            image = self.request.FILES['image']
            
            try:
                validate_uploaded_file(image, file_type='images', max_size=2*1024*1024)
                form.instance.image.name = sanitize_filename(image.name)
            except ValidationError as e:
                form.add_error('image', str(e))
                return self.form_invalid(form)
        
        return super().form_valid(form)
```

---

### مثال 2: رفع ملف العقد

```python
from orders.models import Order
from core.file_validation import validate_uploaded_file

def upload_contract(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST' and request.FILES.get('contract'):
        contract_file = request.FILES['contract']
        
        try:
            # التحقق أن الملف PDF فقط
            if not contract_file.name.lower().endswith('.pdf'):
                raise ValidationError('يجب أن يكون الملف PDF')
            
            validate_uploaded_file(contract_file, file_type='documents', max_size=5*1024*1024)
            
            # حفظ العقد
            order.contract_file = contract_file
            order.save()
            
            messages.success(request, 'تم رفع ملف العقد بنجاح!')
            
        except ValidationError as e:
            messages.error(request, f'خطأ: {e}')
    
    return redirect('order_detail', order_id=order_id)
```

---

### مثال 3: رفع متعدد للملفات

```python
def upload_multiple_images(request):
    if request.method == 'POST':
        files = request.FILES.getlist('images')  # multiple files
        
        uploaded_count = 0
        errors = []
        
        for file in files:
            try:
                validate_uploaded_file(file, file_type='images', max_size=3*1024*1024)
                
                # حفظ الصورة
                Image.objects.create(file=file, name=sanitize_filename(file.name))
                uploaded_count += 1
                
            except ValidationError as e:
                errors.append(f'{file.name}: {e}')
        
        if uploaded_count:
            messages.success(request, f'تم رفع {uploaded_count} صورة بنجاح!')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        
        return redirect('gallery')
    
    return render(request, 'upload_multiple.html')
```

---

## 🔧 التخصيص

### تخصيص الامتدادات المسموحة

```python
# في settings.py
ALLOWED_UPLOAD_EXTENSIONS = [
    '.jpg', '.jpeg', '.png',  # صور فقط
    '.pdf',                    # PDF فقط
]

# في الكود
from django.conf import settings

def upload_custom(request):
    file = request.FILES.get('file')
    ext = os.path.splitext(file.name)[1].lower()
    
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        messages.error(request, f'نوع الملف غير مسموح: {ext}')
        return redirect('upload')
```

---

### تخصيص الحد الأقصى للحجم

```python
# في settings.py
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
MAX_IMAGE_WIDTH = 2048
MAX_IMAGE_HEIGHT = 2048

# في الكود
max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 5*1024*1024)
validate_uploaded_file(file, max_size=max_size)
```

---

## ⚠️ رسائل الخطأ

الأخطاء الشائعة ورسائلها:

```python
# نوع ملف غير مسموح
ValidationError: نوع الملف غير مسموح (.exe). الأنواع المسموحة: .jpg, .png, .pdf

# حجم كبير جداً
ValidationError: حجم الملف كبير جداً (15.50 MB). الحد الأقصى: 10 MB

# نوع محتوى غير صحيح
ValidationError: نوع محتوى الملف غير صحيح (text/html). يبدو أن الملف ليس من النوع المتوقع.

# اسم ملف خطير
ValidationError: اسم الملف يحتوي على حرف غير مسموح ('..'). الرجاء استخدام اسم ملف آخر.

# صورة غير صالحة
ValidationError: الملف ليس صورة صالحة: cannot identify image file
```

---

## 📊 الاختبار

```python
# tests.py
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from core.file_validation import validate_uploaded_file, sanitize_filename

class FileValidationTests(TestCase):
    
    def test_valid_image(self):
        # ملف صورة صحيح
        file = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
        self.assertTrue(validate_uploaded_file(file, file_type='images'))
    
    def test_invalid_extension(self):
        # امتداد غير مسموح
        file = SimpleUploadedFile("test.exe", b"file_content")
        with self.assertRaises(ValidationError):
            validate_uploaded_file(file, file_type='images')
    
    def test_file_too_large(self):
        # ملف كبير جداً
        large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        file = SimpleUploadedFile("large.jpg", large_content)
        with self.assertRaises(ValidationError):
            validate_uploaded_file(file, max_size=10*1024*1024)
    
    def test_sanitize_filename(self):
        # تنظيف اسم الملف
        self.assertEqual(sanitize_filename("test file.jpg"), "test_file.jpg")
        self.assertEqual(sanitize_filename("../../../etc/passwd"), "etc_passwd")
```

---

## ✅ أفضل الممارسات

1. **استخدم الفحص دائماً** قبل حفظ أي ملف
2. **نظّف أسماء الملفات** باستخدام `sanitize_filename()`
3. **حدّد نوع الملف** المتوقع (`images`, `documents`, أو `all`)
4. **ضع حد أقصى للحجم** مناسب لكل نوع ملف
5. **اختبر رفع الملفات** في بيئة التطوير أولاً
6. **راقب السجلات** للملفات المرفوعة
7. **احذف الملفات القديمة** بانتظام

---

## 🎯 ملاحظات هامة

- ✅ النظام يعمل مع جميع أنواع الملفات
- ✅ يدعم العربية في أسماء الملفات
- ✅ آمن ضد Path Traversal
- ✅ يفحص المحتوى الفعلي للملف
- ⚠️ يتطلب `python-magic` للفحص المتقدم
- ⚠️ يتطلب `Pillow` للتحقق من الصور

---

تم إنشاء الدليل بواسطة فريق الأمان
