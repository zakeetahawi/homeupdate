"""
نظام فحص شامل للملفات المرفوعة
يوفر حماية من:
- رفع ملفات خبيثة
- تجاوز حجم الملف
- أنواع ملفات غير مسموحة
"""

import os
import unicodedata
import re
from django.core.exceptions import ValidationError
from django.conf import settings

# الامتدادات المسموحة
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.doc', '.xls'}
ALLOWED_ALL_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

# أنواع MIME المسموحة
ALLOWED_MIME_TYPES = {
    # صور
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    # مستندات
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/msword',
    'application/vnd.ms-excel',
}

# الحد الأقصى لحجم الملف (10 ميجابايت)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# الأحرف الخطرة في أسماء الملفات
DANGEROUS_CHARS = ['..', '/', '\\', '\0', '\n', '\r', '<', '>', ':', '"', '|', '?', '*']


def validate_uploaded_file(uploaded_file, file_type='all', max_size=None):
    """
    التحقق الشامل من الملفات المرفوعة
    
    Args:
        uploaded_file: ملف Django UploadedFile
        file_type: نوع الملف ('images', 'documents', 'all')
        max_size: الحجم الأقصى بالبايت (None = استخدام الافتراضي)
    
    Returns:
        True إذا نجح الفحص
    
    Raises:
        ValidationError: إذا فشل أي فحص
    
    Examples:
        >>> validate_uploaded_file(request.FILES['photo'], file_type='images')
        >>> validate_uploaded_file(request.FILES['document'], max_size=5*1024*1024)
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    # تحديد الامتدادات المسموحة حسب النوع
    if file_type == 'images':
        allowed_exts = ALLOWED_IMAGE_EXTENSIONS
    elif file_type == 'documents':
        allowed_exts = ALLOWED_DOCUMENT_EXTENSIONS
    else:
        allowed_exts = ALLOWED_ALL_EXTENSIONS
    
    # 1. التحقق من وجود الملف
    if not uploaded_file:
        raise ValidationError('لم يتم رفع أي ملف')
    
    # 2. التحقق من الامتداد
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed_exts:
        raise ValidationError(
            f'نوع الملف غير مسموح ({ext}). الأنواع المسموحة: {", ".join(sorted(allowed_exts))}'
        )
    
    # 3. التحقق من الحجم
    if uploaded_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        current_mb = uploaded_file.size / (1024 * 1024)
        raise ValidationError(
            f'حجم الملف كبير جداً ({current_mb:.2f} MB). الحد الأقصى: {max_mb:.0f} MB'
        )
    
    # 4. التحقق من نوع المحتوى الفعلي (Magic Number)
    # ملاحظة: يتطلب مكتبة python-magic
    # يمكن تفعيله بعد تثبيت المكتبة: pip install python-magic
    try:
        import magic
        uploaded_file.seek(0)
        mime_type = magic.from_buffer(uploaded_file.read(2048), mime=True)
        uploaded_file.seek(0)
        
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                f'نوع محتوى الملف غير صحيح ({mime_type}). '
                f'يبدو أن الملف ليس من النوع المتوقع.'
            )
    except ImportError:
        # إذا لم تكن المكتبة مثبتة، نتخطى هذا الفحص
        pass
    
    # 5. فحص اسم الملف من الأحرف الخطرة
    for char in DANGEROUS_CHARS:
        if char in uploaded_file.name:
            raise ValidationError(
                f'اسم الملف يحتوي على حرف غير مسموح ({repr(char)}). '
                f'الرجاء استخدام اسم ملف آخر.'
            )
    
    # 6. فحص إضافي للصور
    if file_type == 'images':
        try:
            from PIL import Image
            uploaded_file.seek(0)
            img = Image.open(uploaded_file)
            img.verify()
            uploaded_file.seek(0)
            
            # التحقق من أبعاد الصورة (اختياري)
            max_width = getattr(settings, 'MAX_IMAGE_WIDTH', 4096)
            max_height = getattr(settings, 'MAX_IMAGE_HEIGHT', 4096)
            
            if img.size[0] > max_width or img.size[1] > max_height:
                raise ValidationError(
                    f'حجم الصورة كبير جداً ({img.size[0]}x{img.size[1]}). '
                    f'الحد الأقصى: {max_width}x{max_height} بكسل'
                )
        except ImportError:
            # إذا لم تكن Pillow مثبتة
            pass
        except Exception as e:
            raise ValidationError(f'الملف ليس صورة صالحة: {str(e)}')
    
    return True


def sanitize_filename(filename):
    """
    تنظيف اسم الملف من الأحرف الخاصة والخطرة
    
    Args:
        filename: اسم الملف الأصلي
    
    Returns:
        اسم ملف آمن ونظيف
    
    Examples:
        >>> sanitize_filename('صورة جديدة.jpg')
        'صورة_جديدة.jpg'
        >>> sanitize_filename('../../../etc/passwd')
        'etc_passwd'
    """
    # إزالة المسافات وتحويلها لـ underscore
    filename = filename.replace(' ', '_')
    
    # تطبيع Unicode
    filename = unicodedata.normalize('NFKD', filename)
    
    # إزالة الأحرف الخاصة (الاحتفاظ بالأحرف العربية والإنجليزية والأرقام فقط)
    filename = re.sub(r'[^\w\s._-]', '', filename, flags=re.UNICODE)
    
    # إزالة النقاط المتعددة
    filename = re.sub(r'\.+', '.', filename)
    
    # إزالة الشرطات والشرطات السفلية المتعددة
    filename = re.sub(r'[-_]+', '_', filename)
    
    # تحديد الطول (الاحتفاظ بالامتداد)
    name, ext = os.path.splitext(filename)
    if len(name) > 50:
        name = name[:50]
    
    # إزالة النقاط والشرطات من البداية والنهاية
    name = name.strip('._- ')
    
    # إذا أصبح الاسم فارغاً، استخدم اسم افتراضي
    if not name:
        import uuid
        name = f'file_{uuid.uuid4().hex[:8]}'
    
    return name + ext


def get_safe_file_path(instance, filename):
    """
    توليد مسار آمن لحفظ الملف
    يستخدم في Django models مع upload_to
    
    Args:
        instance: نموذج Django
        filename: اسم الملف الأصلي
    
    Returns:
        مسار آمن للحفظ
    
    Examples:
        # في Django model:
        file = models.FileField(upload_to=get_safe_file_path)
    """
    import uuid
    from datetime import datetime
    
    # تنظيف اسم الملف
    safe_filename = sanitize_filename(filename)
    
    # إضافة UUID فريد لتجنب الكتابة فوق الملفات
    name, ext = os.path.splitext(safe_filename)
    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{name}_{unique_id}{ext}"
    
    # تنظيم الملفات حسب التاريخ
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    # المسار النهائي: uploads/2025/11/30/filename_abc123.jpg
    return os.path.join('uploads', date_path, safe_filename)


# دالة مساعدة للاستخدام السريع
def quick_validate(uploaded_file, allowed_extensions=None, max_size_mb=10):
    """
    فحص سريع للملف (مبسط)
    
    Args:
        uploaded_file: الملف المرفوع
        allowed_extensions: قائمة الامتدادات المسموحة (None = الكل)
        max_size_mb: الحد الأقصى بالميجابايت
    
    Examples:
        >>> quick_validate(file, allowed_extensions=['.jpg', '.png'], max_size_mb=5)
    """
    # التحقق من الامتداد
    if allowed_extensions:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(f'نوع الملف غير مسموح: {ext}')
    
    # التحقق من الحجم
    max_size = max_size_mb * 1024 * 1024
    if uploaded_file.size > max_size:
        raise ValidationError(f'حجم الملف كبير جداً. الحد الأقصى: {max_size_mb} MB')
    
    # التحقق من الاسم
    sanitize_filename(uploaded_file.name)
    
    return True
