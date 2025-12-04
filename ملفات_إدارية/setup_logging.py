#!/usr/bin/env python
"""
سكريبت لإعداد وتفعيل نظام Logging الكامل
"""

import os
import sys
from pathlib import Path

# إضافة المشروع إلى المسار
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
import django
django.setup()

from django.conf import settings
import logging.config

def create_log_directories():
    """إنشاء مجلدات Log المطلوبة"""
    log_dirs = [
        os.path.join(settings.BASE_DIR, 'logs'),
        os.path.join(settings.BASE_DIR, 'logs', 'archive'),
    ]
    
    for log_dir in log_dirs:
        os.makedirs(log_dir, exist_ok=True)
        print(f'✅ تم إنشاء/التحقق من المجلد: {log_dir}')

def create_log_files():
    """إنشاء ملفات Log الأساسية"""
    log_files = [
        'logs/django.log',
        'logs/errors.log',
        'logs/security.log',
        'logs/performance.log',
        'logs/advanced_sync.log',
        'logs/sequence_checker.log',
        'logs/database.log',
        'logs/api.log',
    ]
    
    for log_file in log_files:
        log_path = os.path.join(settings.BASE_DIR, log_file)
        if not os.path.exists(log_path):
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f'# Log file created at {os.path.basename(log_file)}\n')
            print(f'✅ تم إنشاء ملف: {log_file}')
        else:
            print(f'ℹ️  الملف موجود: {log_file}')

def setup_enhanced_logging():
    """إعداد نظام Logging محسّن"""
    
    ENHANCED_LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} - {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'simple': {
                'format': '[{asctime}] {levelname} - {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'colored': {
                'format': '🔵 [{asctime}] {levelname} {name} - {message}',
                'style': '{',
                'datefmt': '%H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'colored',
            },
            'django_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'django.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'errors.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 10,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            'security_file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'security.log'),
                'maxBytes': 1024 * 1024 * 5,  # 5 MB
                'backupCount': 10,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            'performance_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'performance.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            'database_file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'database.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            'api_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(settings.BASE_DIR, 'logs', 'api.log'),
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 5,
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'django_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['error_file', 'console'],
                'level': 'ERROR',
                'propagate': False,
            },
            'django.security': {
                'handlers': ['security_file', 'console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['database_file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'performance': {
                'handlers': ['performance_file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
            'crm': {
                'handlers': ['console', 'django_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'accounts': {
                'handlers': ['console', 'django_file', 'security_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'orders': {
                'handlers': ['console', 'django_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'api': {
                'handlers': ['api_file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console', 'django_file'],
            'level': 'INFO',
        },
    }
    
    # تطبيق الإعدادات
    logging.config.dictConfig(ENHANCED_LOGGING)
    print('✅ تم تطبيق إعدادات Logging المحسّنة')
    
    return ENHANCED_LOGGING

def test_logging():
    """اختبار نظام Logging"""
    print('\n🧪 اختبار نظام Logging...\n')
    
    # الحصول على loggers مختلفة
    loggers = {
        'django': logging.getLogger('django'),
        'crm': logging.getLogger('crm'),
        'accounts': logging.getLogger('accounts'),
        'orders': logging.getLogger('orders'),
        'performance': logging.getLogger('performance'),
        'api': logging.getLogger('api'),
    }
    
    # اختبار كل logger
    for name, logger in loggers.items():
        logger.info(f'✅ اختبار {name} logger - INFO level')
        logger.warning(f'⚠️  اختبار {name} logger - WARNING level')
        logger.error(f'❌ اختبار {name} logger - ERROR level')
    
    print('\n✅ تم اختبار جميع Loggers بنجاح!')

def show_log_status():
    """عرض حالة ملفات Log"""
    print('\n📊 حالة ملفات Log:\n')
    print(f'{'الملف':<30} {'الحجم':<15} {'الحالة':<10}')
    print('=' * 60)
    
    logs_dir = os.path.join(settings.BASE_DIR, 'logs')
    
    if os.path.exists(logs_dir):
        for filename in sorted(os.listdir(logs_dir)):
            if filename.endswith('.log'):
                filepath = os.path.join(logs_dir, filename)
                size = os.path.getsize(filepath)
                
                # تحويل الحجم إلى وحدة مناسبة
                if size < 1024:
                    size_str = f'{size} B'
                elif size < 1024 * 1024:
                    size_str = f'{size / 1024:.2f} KB'
                else:
                    size_str = f'{size / (1024 * 1024):.2f} MB'
                
                status = '✅ موجود'
                print(f'{filename:<30} {size_str:<15} {status:<10}')
    else:
        print('❌ مجلد logs غير موجود')

def main():
    """الدالة الرئيسية"""
    print('🚀 بدء إعداد نظام Logging...\n')
    
    try:
        # 1. إنشاء المجلدات
        print('📁 إنشاء مجلدات Log...')
        create_log_directories()
        
        # 2. إنشاء ملفات Log
        print('\n📄 إنشاء ملفات Log...')
        create_log_files()
        
        # 3. إعداد نظام Logging
        print('\n⚙️  إعداد نظام Logging...')
        setup_enhanced_logging()
        
        # 4. اختبار النظام
        test_logging()
        
        # 5. عرض الحالة
        show_log_status()
        
        print('\n' + '=' * 60)
        print('✅ تم إعداد نظام Logging بنجاح!')
        print('=' * 60)
        
        print('\n📋 الأوامر المفيدة:')
        print('  - عرض آخر 50 سطر: tail -n 50 logs/django.log')
        print('  - متابعة Log مباشرة: tail -f logs/django.log')
        print('  - عرض الأخطاء فقط: tail -f logs/errors.log')
        print('  - عرض جميع الملفات: ls -lh logs/')
        
    except Exception as e:
        print(f'\n❌ حدث خطأ: {e}')
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

