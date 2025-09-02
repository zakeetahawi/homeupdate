"""
ملف إعدادات قاعدة البيانات
"""

import os
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

logger = logging.getLogger(__name__)

# الحصول على مسار المشروع
BASE_DIR = Path(__file__).resolve().parent.parent

# مسار ملف إعدادات قاعدة البيانات
DB_SETTINGS_FILE = os.path.join(BASE_DIR, 'db_settings.json')

# Database connection settings
DB_SETTINGS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'crm_system',
    'user': 'postgres',
    'password': '5525',
    'timezone': 'Asia/Riyadh'
}

# Time zone settings
TIME_ZONE = 'Asia/Riyadh'
USE_TZ = True

# Default datetime settings
def get_current_time():
    return datetime.now(ZoneInfo(TIME_ZONE))

# Backup settings
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Additional database configurations
MAX_CONNECTIONS = 20
CONNECT_TIMEOUT = 30

def get_active_database_settings():
    """
    الحصول على إعدادات قاعدة البيانات النشطة
    
    Returns:
        dict: إعدادات قاعدة البيانات النشطة
    """
    try:
        # قراءة ملف الإعدادات
        with open(DB_SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            
        # التحقق من صحة الإعدادات
        if not settings.get('active_db') or not settings.get('databases'):
            raise ValueError("الملف يفتقد البيانات المطلوبة")
            
        return settings

    except FileNotFoundError:
        logger.warning("ملف الإعدادات غير موجود. إنشاء ملف جديد بالإعدادات الافتراضية.")
        return _create_default_settings()
        
    except json.JSONDecodeError:
        logger.error("تنسيق ملف الإعدادات غير صحيح. إنشاء ملف جديد.")
        return _create_default_settings()
        
    except Exception as e:
        logger.error(f"حدث خطأ أثناء قراءة إعدادات قاعدة البيانات: {str(e)}")
        return _create_default_settings()

def save_database_settings(settings):
    """
    حفظ إعدادات قاعدة البيانات
    
    Args:
        settings (dict): إعدادات قاعدة البيانات
    """
    try:
        # التحقق من صحة الإعدادات قبل الحفظ
        if not isinstance(settings, dict):
            raise ValueError("الإعدادات يجب أن تكون قاموساً")
            
        if 'active_db' not in settings or 'databases' not in settings:
            raise ValueError("الإعدادات يجب أن تحتوي على active_db و databases")
            
        # حفظ الإعدادات
        with open(DB_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
            
        logger.info("تم حفظ إعدادات قاعدة البيانات بنجاح")
        
    except Exception as e:
        logger.error(f"حدث خطأ أثناء حفظ إعدادات قاعدة البيانات: {str(e)}")
        raise

def _create_default_settings():
    """
    إنشاء ملف إعدادات افتراضي
    
    Returns:
        dict: الإعدادات الافتراضية
    """
    default_settings = {
        'active_db': 13,
        'databases': {
            '13': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'crm_system',
                'USER': 'postgres',
                'PASSWORD': '5525',
                'HOST': 'localhost',
                'PORT': '5432'
            }
        }
    }
    
    try:
        save_database_settings(default_settings)
        logger.info("تم إنشاء ملف إعدادات افتراضي")
    except:
        logger.error("فشل إنشاء ملف الإعدادات الافتراضي")
        
    return default_settings
