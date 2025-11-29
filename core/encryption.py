"""
نظام تشفير متقدم للبيانات الحساسة
يستخدم Fernet (AES-128) للتشفير القوي
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from django.conf import settings
import base64
import os


class DataEncryption:
    """
    نظام تشفير البيانات الحساسة
    """
    
    def __init__(self):
        self.cipher = self._get_cipher()
    
    def _get_cipher(self):
        """إنشاء cipher من المفتاح"""
        # الحصول على المفتاح من البيئة أو إنشاء واحد
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        
        if not encryption_key:
            # إنشاء مفتاح من SECRET_KEY
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=settings.SECRET_KEY[:16].encode(),
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(
                kdf.derive(settings.SECRET_KEY.encode())
            )
        else:
            key = encryption_key.encode()
        
        return Fernet(key)
    
    def encrypt(self, data):
        """
        تشفير البيانات
        
        Args:
            data: البيانات النصية للتشفير
            
        Returns:
            البيانات المشفرة كنص
        """
        if not data:
            return data
        
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.cipher.encrypt(data)
        return encrypted.decode()
    
    def decrypt(self, encrypted_data):
        """
        فك تشفير البيانات
        
        Args:
            encrypted_data: البيانات المشفرة
            
        Returns:
            البيانات الأصلية كنص
        """
        if not encrypted_data:
            return encrypted_data
        
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        
        try:
            decrypted = self.cipher.decrypt(encrypted_data)
            return decrypted.decode()
        except:
            # إذا فشل فك التشفير، إرجاع البيانات كما هي
            return encrypted_data.decode() if isinstance(encrypted_data, bytes) else encrypted_data
    
    def hash_data(self, data):
        """
        إنشاء hash للبيانات (لا يمكن عكسه)
        يستخدم للبيانات التي لا تحتاج فك تشفير
        
        Args:
            data: البيانات للـ hash
            
        Returns:
            hash البيانات
        """
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()


# مثيل عام للاستخدام
encryption = DataEncryption()


# Django Model Fields للتشفير التلقائي
from django.db import models

class EncryptedTextField(models.TextField):
    """
    حقل نصي مشفر تلقائياً
    """
    
    def from_db_value(self, value, expression, connection):
        """فك تشفير عند القراءة من DB"""
        if value is None:
            return value
        return encryption.decrypt(value)
    
    def to_python(self, value):
        """تحويل للبايثون"""
        if isinstance(value, str) or value is None:
            return value
        return encryption.decrypt(value)
    
    def get_prep_value(self, value):
        """تشفير قبل الحفظ في DB"""
        if value is None:
            return value
        return encryption.encrypt(value)


class EncryptedCharField(models.CharField):
    """
    حقل CharField مشفر تلقائياً
    """
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return encryption.decrypt(value)
    
    def to_python(self, value):
        if isinstance(value, str) or value is None:
            return value
        return encryption.decrypt(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        encrypted = encryption.encrypt(value)
        # التأكد من أن الطول لا يتجاوز max_length
        if hasattr(self, 'max_length') and self.max_length:
            return encrypted[:self.max_length]
        return encrypted


class EncryptedEmailField(models.EmailField):
    """
    حقل Email مشفر تلقائياً
    """
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return encryption.decrypt(value)
    
    def to_python(self, value):
        if isinstance(value, str) or value is None:
            return value
        return encryption.decrypt(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return encryption.encrypt(value)


# دوال مساعدة
def encrypt_sensitive_data(data_dict):
    """
    تشفير قاموس من البيانات الحساسة
    
    Args:
        data_dict: قاموس البيانات
        
    Returns:
        قاموس مشفر
    """
    encrypted = {}
    for key, value in data_dict.items():
        if value and isinstance(value, str):
            encrypted[key] = encryption.encrypt(value)
        else:
            encrypted[key] = value
    return encrypted


def decrypt_sensitive_data(encrypted_dict):
    """
    فك تشفير قاموس من البيانات المشفرة
    
    Args:
        encrypted_dict: قاموس البيانات المشفرة
        
    Returns:
        قاموس مفكوك التشفير
    """
    decrypted = {}
    for key, value in encrypted_dict.items():
        if value and isinstance(value, str):
            decrypted[key] = encryption.decrypt(value)
        else:
            decrypted[key] = value
    return decrypted


# استخدام في Models
"""
مثال:

from core.encryption import EncryptedTextField, EncryptedCharField

class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = EncryptedCharField(max_length=500)  # مشفر
    email = EncryptedEmailField(max_length=500)  # مشفر
    national_id = EncryptedCharField(max_length=500)  # مشفر
    address = EncryptedTextField()  # مشفر
    
    # البيانات تُشفر تلقائياً عند الحفظ
    # وتُفك تلقائياً عند القراءة
"""
