#!/usr/bin/env python3
"""
إعدادات خاصة للعمليات الكبيرة والرفع والمزامنة
Configuration for large operations, uploads, and synchronization
"""

# إعدادات خاصة بالرفع والمزامنة
LARGE_OPERATION_SETTINGS = {
    # أقصى وقت انتظار للعمليات الكبيرة (بالثواني)
    'MAX_OPERATION_TIMEOUT': 7200,  # 2 ساعة
    
    # أقصى حجم ملف للرفع (بالبايت)
    'MAX_FILE_SIZE': 1024 * 1024 * 1000,  # 1 جيجابايت
    
    # عدد محاولات إعادة المحاولة
    'MAX_RETRIES': 5,
    
    # وقت الانتظار بين المحاولات (بالثواني)
    'RETRY_DELAY': 30,
    
    # إعدادات الـ chunking للملفات الكبيرة
    'CHUNK_SIZE': 5 * 1024 * 1024,  # 5 ميجابايت
    
    # إعدادات Connection Pool
    'CONNECTION_POOL_SIZE': 20,
    'CONNECTION_POOL_MAXSIZE': 50,
    
    # إعدادات خاصة بـ Google Drive
    'GOOGLE_DRIVE_SETTINGS': {
        'chunk_size': 5 * 1024 * 1024,  # 5 ميجابايت
        'resumable_threshold': 10 * 1024 * 1024,  # 10 ميجابايت
        'max_retries': 10,
        'retry_delay': 5,
        'timeout': 1800,  # 30 دقيقة
    },
    
    # إعدادات خاصة بمزامنة الجداول
    'TABLE_SYNC_SETTINGS': {
        'batch_size': 500,  # عدد الصفوف في كل دفعة
        'max_rows_per_sync': 50000,  # أقصى عدد صفوف في المزامنة الواحدة
        'timeout_per_batch': 300,  # 5 دقائق لكل دفعة
        'total_timeout': 3600,  # ساعة واحدة للمزامنة الكاملة
    },
    
    # إعدادات Memory Management
    'MEMORY_SETTINGS': {
        'max_memory_per_task': 1024 * 1024 * 512,  # 512 ميجابايت
        'garbage_collection_threshold': 0.8,  # تنظيف الذاكرة عند 80%
        'memory_monitoring_interval': 60,  # فحص الذاكرة كل دقيقة
    }
}

# إعدادات Celery خاصة بالعمليات الكبيرة
CELERY_LARGE_OPERATIONS = {
    'task_time_limit': 7200,  # 2 ساعة
    'task_soft_time_limit': 6600,  # ساعة و 50 دقيقة
    'worker_prefetch_multiplier': 1,  # تقليل التحميل المسبق
    'task_acks_late': True,  # تأكيد المهمة بعد الانتهاء
    'worker_disable_rate_limits': True,  # إلغاء حدود المعدل
}

# إعدادات Database Connection للعمليات الكبيرة
DATABASE_LARGE_OPERATIONS = {
    'CONN_MAX_AGE': 600,  # 10 دقائق
    'CONN_HEALTH_CHECKS': True,
    'OPTIONS': {
        'MAX_CONNS': 50,
        'MIN_CONNS': 10,
        'CONNECT_TIMEOUT': 60,
        'COMMAND_TIMEOUT': 300,  # 5 دقائق
    }
}

# دالة لتطبيق الإعدادات على Django
def apply_large_operation_settings(settings_module):
    """
    تطبيق الإعدادات على ملف settings.py
    Apply settings to Django settings module
    """
    # تحديث إعدادات الملفات
    settings_module.FILE_UPLOAD_MAX_MEMORY_SIZE = LARGE_OPERATION_SETTINGS['MAX_FILE_SIZE']
    settings_module.DATA_UPLOAD_MAX_MEMORY_SIZE = LARGE_OPERATION_SETTINGS['MAX_FILE_SIZE']
    
    # تحديث إعدادات Celery
    for key, value in CELERY_LARGE_OPERATIONS.items():
        setattr(settings_module, f'CELERY_{key.upper()}', value)
    
    # تحديث إعدادات قاعدة البيانات
    if hasattr(settings_module, 'DATABASES'):
        for db_config in settings_module.DATABASES.values():
            db_config.update(DATABASE_LARGE_OPERATIONS)
    
    return settings_module

# دالة للحصول على إعدادات مخصصة لنوع العملية
def get_operation_config(operation_type):
    """
    الحصول على إعدادات مخصصة حسب نوع العملية
    Get custom configuration based on operation type
    """
    configs = {
        'file_upload': {
            'timeout': LARGE_OPERATION_SETTINGS['MAX_OPERATION_TIMEOUT'],
            'chunk_size': LARGE_OPERATION_SETTINGS['CHUNK_SIZE'],
            'max_retries': LARGE_OPERATION_SETTINGS['MAX_RETRIES'],
        },
        'google_sync': LARGE_OPERATION_SETTINGS['GOOGLE_DRIVE_SETTINGS'],
        'table_sync': LARGE_OPERATION_SETTINGS['TABLE_SYNC_SETTINGS'],
        'bulk_update': {
            'batch_size': 1000,
            'timeout': 1800,  # 30 دقيقة
            'memory_limit': 512 * 1024 * 1024,  # 512 ميجابايت
        }
    }
    
    return configs.get(operation_type, LARGE_OPERATION_SETTINGS)

# دالة لمراقبة العمليات الكبيرة
def monitor_large_operation(operation_id, operation_type):
    """
    مراقبة العمليات الكبيرة وتسجيل التقدم
    Monitor large operations and log progress
    """
    import time
    import psutil
    import logging
    
    logger = logging.getLogger(f'large_operations.{operation_type}')
    
    start_time = time.time()
    process = psutil.Process()
    
    config = get_operation_config(operation_type)
    
    def log_status():
        elapsed = time.time() - start_time
        memory_usage = process.memory_info().rss / 1024 / 1024  # ميجابايت
        cpu_percent = process.cpu_percent()
        
        logger.info(f"Operation {operation_id}: Elapsed={elapsed:.1f}s, Memory={memory_usage:.1f}MB, CPU={cpu_percent:.1f}%")
        
        # تحذير إذا تجاوز الحد المسموح
        if memory_usage > config.get('memory_limit', 512):
            logger.warning(f"High memory usage: {memory_usage:.1f}MB")
        
        if elapsed > config.get('timeout', 3600):
            logger.error(f"Operation timeout: {elapsed:.1f}s")
            return False
        
        return True
    
    return log_status

if __name__ == "__main__":
    print("إعدادات العمليات الكبيرة:")
    print("========================")
    for key, value in LARGE_OPERATION_SETTINGS.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")
