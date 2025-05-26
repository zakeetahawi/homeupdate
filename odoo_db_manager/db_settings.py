"""
ملف إعدادات قاعدة البيانات الخارجي
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# الحصول على مسار المشروع
BASE_DIR = Path(__file__).resolve().parent.parent

# مسار ملف إعدادات قاعدة البيانات
DB_SETTINGS_FILE = os.path.join(BASE_DIR, 'db_settings.json')

def get_active_database_settings():
    """
    الحصول على إعدادات قاعدة البيانات النشطة

    Returns:
        dict: إعدادات قاعدة البيانات النشطة
    """
    try:
        # التحقق من وجود متغيرات البيئة الخاصة بقاعدة البيانات
        if 'DATABASE_URL' in os.environ:
            # استخدام إعدادات قاعدة البيانات من متغيرات البيئة
            logger.info("تم اكتشاف DATABASE_URL، استخدام إعدادات قاعدة البيانات من متغيرات البيئة")
            print("تم اكتشاف DATABASE_URL، استخدام إعدادات قاعدة البيانات من متغيرات البيئة")

            # إنشاء معرف فريد لقاعدة البيانات
            external_db_id = 'external_db'

            # طباعة معلومات متغيرات البيئة للتشخيص
            print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")

            # تحليل DATABASE_URL
            import dj_database_url
            db_config = dj_database_url.parse(os.environ.get('DATABASE_URL'))

            # إنشاء إعدادات قاعدة البيانات الخارجية
            external_settings = {
                'active_db': external_db_id,
                'databases': {
                    external_db_id: {
                        'ENGINE': db_config.get('ENGINE', 'django.db.backends.postgresql'),
                        'NAME': db_config.get('NAME', 'external_db'),
                        'USER': db_config.get('USER', 'postgres'),
                        'PASSWORD': db_config.get('PASSWORD', ''),
                        'HOST': db_config.get('HOST', 'localhost'),
                        'PORT': db_config.get('PORT', '5432'),
                    }
                }
            }

            # طباعة معلومات قاعدة البيانات للتشخيص
            print(f"معلومات قاعدة البيانات:")
            print(f"ENGINE: {db_config.get('ENGINE')}")
            print(f"NAME: {db_config.get('NAME')}")
            print(f"USER: {db_config.get('USER')}")
            print(f"HOST: {db_config.get('HOST')}")
            print(f"PORT: {db_config.get('PORT')}")

            # حفظ إعدادات قاعدة البيانات الخارجية
            save_database_settings(external_settings)

            return external_settings

        # التحقق من وجود ملف الإعدادات
        if not os.path.exists(DB_SETTINGS_FILE):
            # إنشاء ملف إعدادات افتراضي
            default_settings = {
                'active_db': 7,  # استخدام SQLite كقاعدة بيانات افتراضية
                'databases': {
                    '7': {
                        'ENGINE': 'django.db.backends.sqlite3',
                        'NAME': 'db.sqlite3',
                    }
                }
            }
            save_database_settings(default_settings)
            return default_settings

        # قراءة ملف الإعدادات
        with open(DB_SETTINGS_FILE, 'r') as f:
            settings = json.load(f)

        return settings
    except Exception as e:
        logger.error(f"حدث خطأ أثناء قراءة إعدادات قاعدة البيانات: {str(e)}")
        # إرجاع إعدادات SQLite الافتراضية في حالة حدوث خطأ
        return {
            'active_db': 7,
            'databases': {
                '7': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': 'db.sqlite3',
                }
            }
        }

def save_database_settings(settings):
    """
    حفظ إعدادات قاعدة البيانات

    Args:
        settings (dict): إعدادات قاعدة البيانات
    """
    try:
        # حفظ ملف الإعدادات
        with open(DB_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        logger.info("تم حفظ إعدادات قاعدة البيانات")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء حفظ إعدادات قاعدة البيانات: {str(e)}")

def reset_to_default_settings():
    """
    إعادة تعيين إعدادات قاعدة البيانات إلى الإعدادات الافتراضية
    """
    try:
        # إنشاء ملف إعدادات افتراضي
        default_settings = {
            'active_db': 7,  # استخدام SQLite كقاعدة بيانات افتراضية
            'databases': {
                '7': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': 'db.sqlite3',
                }
            }
        }

        # حفظ الإعدادات
        save_database_settings(default_settings)

        logger.info("تم إعادة تعيين إعدادات قاعدة البيانات إلى الإعدادات الافتراضية")
        return True
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إعادة تعيين إعدادات قاعدة البيانات: {str(e)}")
        return False
