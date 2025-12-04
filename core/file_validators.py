"""
🔒 File Upload Validators
التحقق من صحة الملفات المرفوعة للحماية من الثغرات الأمنية

الاستخدام في models.py:
    from core.file_validators import (
        validate_file_extension,
        validate_file_size,
        validate_image_file,
        SecureFileField,
        SecureImageField
    )
    
    class MyModel(models.Model):
        document = SecureFileField(upload_to='documents/')
        image = SecureImageField(upload_to='images/')
"""

import os
import magic
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


# ============================================
# الإعدادات الافتراضية
# ============================================

# أنواع الملفات المسموحة
ALLOWED_DOCUMENT_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv', 'rtf', 'odt', 'ods'
]

ALLOWED_IMAGE_EXTENSIONS = [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'
]

ALLOWED_ALL_EXTENSIONS = ALLOWED_DOCUMENT_EXTENSIONS + ALLOWED_IMAGE_EXTENSIONS

# MIME Types المسموحة
ALLOWED_MIME_TYPES = {
    # Documents
    'application/pdf': ['pdf'],
    'application/msword': ['doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['docx'],
    'application/vnd.ms-excel': ['xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['xlsx'],
    'text/plain': ['txt'],
    'text/csv': ['csv'],
    'application/rtf': ['rtf'],
    'application/vnd.oasis.opendocument.text': ['odt'],
    'application/vnd.oasis.opendocument.spreadsheet': ['ods'],
    
    # Images
    'image/jpeg': ['jpg', 'jpeg'],
    'image/png': ['png'],
    'image/gif': ['gif'],
    'image/webp': ['webp'],
    'image/svg+xml': ['svg'],
    'image/bmp': ['bmp'],
    'image/x-icon': ['ico'],
    'image/vnd.microsoft.icon': ['ico'],
}

# الحد الأقصى لحجم الملف (بالبايت)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5 MB


# ============================================
# Validators
# ============================================

def validate_file_extension(value, allowed_extensions=None):
    """
    التحقق من امتداد الملف
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_ALL_EXTENSIONS
    
    ext = os.path.splitext(value.name)[1][1:].lower()
    
    if ext not in allowed_extensions:
        raise ValidationError(
            _('نوع الملف "%(ext)s" غير مسموح. الأنواع المسموحة: %(allowed)s'),
            params={
                'ext': ext,
                'allowed': ', '.join(allowed_extensions)
            },
            code='invalid_extension'
        )


def validate_file_size(value, max_size=None):
    """
    التحقق من حجم الملف
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE
    
    if value.size > max_size:
        raise ValidationError(
            _('حجم الملف كبير جداً. الحد الأقصى %(max_size)s MB'),
            params={'max_size': max_size / (1024 * 1024)},
            code='file_too_large'
        )


def validate_file_mime_type(value, allowed_mime_types=None):
    """
    التحقق من MIME Type الحقيقي للملف (ليس فقط الامتداد)
    يمنع رفع ملفات ضارة بامتداد مزيف
    """
    if allowed_mime_types is None:
        allowed_mime_types = ALLOWED_MIME_TYPES
    
    # قراءة أول 2048 بايت لتحديد النوع
    file_head = value.read(2048)
    value.seek(0)  # إعادة المؤشر للبداية
    
    try:
        mime = magic.from_buffer(file_head, mime=True)
    except Exception:
        # إذا فشل التحقق، نعتمد على الامتداد فقط
        return
    
    if mime not in allowed_mime_types:
        raise ValidationError(
            _('نوع الملف الحقيقي "%(mime)s" غير مسموح'),
            params={'mime': mime},
            code='invalid_mime_type'
        )
    
    # تحقق من تطابق الامتداد مع MIME Type
    ext = os.path.splitext(value.name)[1][1:].lower()
    expected_extensions = allowed_mime_types.get(mime, [])
    
    if ext not in expected_extensions:
        raise ValidationError(
            _('امتداد الملف "%(ext)s" لا يتطابق مع نوعه الحقيقي "%(mime)s"'),
            params={'ext': ext, 'mime': mime},
            code='extension_mismatch'
        )


def validate_image_file(value):
    """
    التحقق من صحة ملف الصورة
    """
    # التحقق من الامتداد
    validate_file_extension(value, ALLOWED_IMAGE_EXTENSIONS)
    
    # التحقق من الحجم
    validate_file_size(value, MAX_IMAGE_SIZE)
    
    # التحقق من MIME Type
    image_mime_types = {
        k: v for k, v in ALLOWED_MIME_TYPES.items() 
        if k.startswith('image/')
    }
    validate_file_mime_type(value, image_mime_types)
    
    # التحقق من أن الملف صورة صالحة
    try:
        from PIL import Image
        img = Image.open(value)
        img.verify()
        value.seek(0)
    except Exception:
        raise ValidationError(
            _('الملف ليس صورة صالحة'),
            code='invalid_image'
        )


def validate_document_file(value):
    """
    التحقق من صحة ملف المستند
    """
    validate_file_extension(value, ALLOWED_DOCUMENT_EXTENSIONS)
    validate_file_size(value)
    
    doc_mime_types = {
        k: v for k, v in ALLOWED_MIME_TYPES.items() 
        if not k.startswith('image/')
    }
    validate_file_mime_type(value, doc_mime_types)


def validate_no_executable(value):
    """
    التحقق من أن الملف ليس قابل للتنفيذ
    """
    dangerous_extensions = [
        'exe', 'bat', 'cmd', 'sh', 'bash', 'ps1', 'vbs', 'js',
        'jar', 'py', 'php', 'asp', 'aspx', 'jsp', 'cgi', 'pl',
        'dll', 'so', 'dylib', 'bin', 'msi', 'app', 'dmg',
        'scr', 'pif', 'com', 'hta', 'wsf', 'wsh'
    ]
    
    ext = os.path.splitext(value.name)[1][1:].lower()
    
    if ext in dangerous_extensions:
        raise ValidationError(
            _('الملفات القابلة للتنفيذ غير مسموحة'),
            code='executable_not_allowed'
        )


def sanitize_filename(filename):
    """
    تنظيف اسم الملف من الأحرف الخطرة
    """
    import re
    import unicodedata
    
    # إزالة الأحرف غير الآمنة
    filename = unicodedata.normalize('NFKD', filename)
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    filename = re.sub(r'[\s]+', '_', filename)
    
    # منع الأسماء الخطرة
    dangerous_names = [
        'con', 'prn', 'aux', 'nul',
        'com1', 'com2', 'com3', 'com4', 'com5',
        'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5'
    ]
    
    name_without_ext = os.path.splitext(filename)[0].lower()
    if name_without_ext in dangerous_names:
        filename = f"file_{filename}"
    
    return filename


# ============================================
# Custom Fields
# ============================================

class SecureFileField(models.FileField):
    """
    FileField مع تحقق أمني تلقائي
    """
    
    def __init__(self, *args, **kwargs):
        # إضافة validators
        validators = kwargs.get('validators', [])
        validators.extend([
            validate_file_size,
            validate_no_executable,
        ])
        
        # إضافة FileExtensionValidator إذا تم تحديد extensions
        allowed_extensions = kwargs.pop('allowed_extensions', ALLOWED_ALL_EXTENSIONS)
        validators.append(FileExtensionValidator(allowed_extensions))
        
        kwargs['validators'] = validators
        super().__init__(*args, **kwargs)
    
    def pre_save(self, model_instance, add):
        """تنظيف اسم الملف قبل الحفظ"""
        file = super().pre_save(model_instance, add)
        if file and file.name:
            file.name = sanitize_filename(file.name)
        return file


class SecureImageField(models.ImageField):
    """
    ImageField مع تحقق أمني تلقائي
    """
    
    def __init__(self, *args, **kwargs):
        # إضافة validators
        validators = kwargs.get('validators', [])
        validators.extend([
            validate_image_file,
        ])
        
        kwargs['validators'] = validators
        super().__init__(*args, **kwargs)
    
    def pre_save(self, model_instance, add):
        """تنظيف اسم الملف قبل الحفظ"""
        file = super().pre_save(model_instance, add)
        if file and file.name:
            file.name = sanitize_filename(file.name)
        return file


# ============================================
# Helper Functions
# ============================================

def get_secure_upload_path(instance, filename, folder='uploads'):
    """
    إنشاء مسار آمن لرفع الملفات
    يمنع Path Traversal attacks
    """
    import uuid
    from datetime import datetime
    
    # تنظيف اسم الملف
    filename = sanitize_filename(filename)
    
    # إنشاء اسم فريد
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    
    # مسار منظم حسب التاريخ
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    return os.path.join(folder, date_path, unique_name)


def create_upload_path(folder):
    """
    Factory function لإنشاء دالة upload_to
    
    Usage:
        class MyModel(models.Model):
            file = models.FileField(upload_to=create_upload_path('documents'))
    """
    def upload_path(instance, filename):
        return get_secure_upload_path(instance, filename, folder)
    return upload_path
