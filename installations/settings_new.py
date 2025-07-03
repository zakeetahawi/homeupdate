"""
إعدادات النظام الجديد للتركيبات
"""

# إعدادات التركيبات
INSTALLATION_SETTINGS = {
    # حدود النظام
    'MAX_DAILY_INSTALLATIONS': 13,
    'MAX_TECHNICIAN_WINDOWS': 20,
    'WARNING_TECHNICIAN_WINDOWS': 18,
    'MAX_TEAM_DAILY_INSTALLATIONS': 5,
    
    # أوقات العمل
    'WORK_START_TIME': '08:00',
    'WORK_END_TIME': '17:00',
    'WORK_DAYS': [5, 6, 0, 1, 2],  # السبت-الأربعاء (Python weekday)
    'LUNCH_BREAK_START': '12:00',
    'LUNCH_BREAK_END': '13:00',
    
    # إعدادات الإنذارات
    'ALERT_SETTINGS': {
        'ENABLE_EMAIL_ALERTS': True,
        'ENABLE_SMS_ALERTS': False,
        'CRITICAL_ALERT_RECIPIENTS': [],
        'ALERT_CHECK_INTERVAL': 3600,  # ثانية
        'AUTO_RESOLVE_ALERTS_DAYS': 7,
        'SEND_DAILY_SUMMARY': True,
        'SEND_WEEKLY_SUMMARY': True,
    },
    
    # إعدادات التقارير
    'REPORT_SETTINGS': {
        'DEFAULT_EXPORT_FORMAT': 'pdf',
        'INCLUDE_PHOTOS_IN_REPORTS': False,
        'AUTO_GENERATE_DAILY_REPORTS': True,
        'REPORT_RETENTION_DAYS': 365,
        'ENABLE_REPORT_SCHEDULING': True,
        'DEFAULT_REPORT_TIME': '08:00',
    },
    
    # إعدادات الجودة
    'QUALITY_SETTINGS': {
        'REQUIRE_QUALITY_RATING': True,
        'REQUIRE_CUSTOMER_SATISFACTION': True,
        'MIN_QUALITY_THRESHOLD': 3,
        'ENABLE_QUALITY_ALERTS': True,
        'QUALITY_ALERT_THRESHOLD': 2.5,
        'ENABLE_CUSTOMER_FEEDBACK': True,
    },
    
    # إعدادات التحليلات
    'ANALYTICS_SETTINGS': {
        'ENABLE_PREDICTIVE_ANALYTICS': True,
        'ANALYTICS_RETENTION_DAYS': 730,
        'ENABLE_REAL_TIME_ANALYTICS': True,
        'CACHE_ANALYTICS_MINUTES': 15,
        'ENABLE_PERFORMANCE_TRACKING': True,
        'TRACK_TECHNICIAN_EFFICIENCY': True,
    },
    
    # إعدادات التكامل
    'INTEGRATION_SETTINGS': {
        'ENABLE_LEGACY_SYNC': True,
        'SYNC_INTERVAL_MINUTES': 30,
        'ENABLE_API_ACCESS': True,
        'API_RATE_LIMIT': 1000,  # طلبات في الساعة
        'ENABLE_WEBHOOK_NOTIFICATIONS': False,
        'WEBHOOK_TIMEOUT_SECONDS': 30,
    },
    
    # إعدادات الأمان
    'SECURITY_SETTINGS': {
        'REQUIRE_INSTALLATION_APPROVAL': False,
        'ENABLE_AUDIT_LOG': True,
        'LOG_SENSITIVE_OPERATIONS': True,
        'REQUIRE_COMPLETION_CONFIRMATION': True,
        'ENABLE_DATA_ENCRYPTION': False,
    },
    
    # إعدادات الواجهة
    'UI_SETTINGS': {
        'DEFAULT_PAGE_SIZE': 20,
        'ENABLE_DARK_MODE': False,
        'SHOW_ADVANCED_FILTERS': True,
        'ENABLE_BULK_OPERATIONS': True,
        'AUTO_REFRESH_INTERVAL': 300,  # ثانية
        'ENABLE_NOTIFICATIONS': True,
    },
    
    # إعدادات الطباعة والتصدير
    'EXPORT_SETTINGS': {
        'PDF_PAGE_SIZE': 'A4',
        'PDF_ORIENTATION': 'portrait',
        'EXCEL_MAX_ROWS': 10000,
        'ENABLE_WATERMARK': False,
        'WATERMARK_TEXT': 'نظام إدارة التركيبات',
        'INCLUDE_COMPANY_LOGO': True,
    },
    
    # إعدادات الإشعارات
    'NOTIFICATION_SETTINGS': {
        'EMAIL_NOTIFICATIONS': True,
        'SMS_NOTIFICATIONS': False,
        'PUSH_NOTIFICATIONS': False,
        'NOTIFICATION_RETENTION_DAYS': 30,
        'BATCH_NOTIFICATIONS': True,
        'NOTIFICATION_FREQUENCY': 'immediate',  # immediate, hourly, daily
    },
    
    # إعدادات الأداء
    'PERFORMANCE_SETTINGS': {
        'ENABLE_CACHING': True,
        'CACHE_TIMEOUT': 900,  # 15 دقيقة
        'ENABLE_COMPRESSION': True,
        'OPTIMIZE_QUERIES': True,
        'LAZY_LOADING': True,
        'PAGINATION_SIZE': 20,
    },
    
    # إعدادات النسخ الاحتياطي
    'BACKUP_SETTINGS': {
        'AUTO_BACKUP': False,
        'BACKUP_INTERVAL_HOURS': 24,
        'BACKUP_RETENTION_DAYS': 30,
        'BACKUP_LOCATION': '/backups/installations/',
        'COMPRESS_BACKUPS': True,
        'ENCRYPT_BACKUPS': False,
    },
}

# إعدادات قاعدة البيانات المحسنة للتركيبات
INSTALLATION_DATABASE_SETTINGS = {
    'OPTIONS': {
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        'charset': 'utf8mb4',
    },
    'CONN_MAX_AGE': 600,
    'ATOMIC_REQUESTS': True,
}

# إعدادات التخزين المؤقت للتركيبات
INSTALLATION_CACHE_SETTINGS = {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'installations-cache',
    'TIMEOUT': 900,  # 15 دقيقة
    'OPTIONS': {
        'MAX_ENTRIES': 1000,
        'CULL_FREQUENCY': 3,
    }
}

# إعدادات السجلات للتركيبات
INSTALLATION_LOGGING_SETTINGS = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'installations_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/installations.log',
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'installations_error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/installations_errors.log',
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'installations': {
            'handlers': ['installations_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'installations.services': {
            'handlers': ['installations_file', 'installations_error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'installations.alerts': {
            'handlers': ['installations_error_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# إعدادات البريد الإلكتروني للتركيبات
INSTALLATION_EMAIL_SETTINGS = {
    'FROM_EMAIL': 'noreply@installations.com',
    'ADMIN_EMAILS': [],
    'MANAGER_EMAILS': [],
    'TECHNICIAN_EMAILS': [],
    'CUSTOMER_NOTIFICATIONS': False,
    'EMAIL_TEMPLATES_DIR': 'installations/email_templates/',
}

# إعدادات API للتركيبات
INSTALLATION_API_SETTINGS = {
    'ENABLE_API': True,
    'API_VERSION': 'v1',
    'RATE_LIMIT': '1000/hour',
    'AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# إعدادات الأمان المتقدمة
INSTALLATION_SECURITY_SETTINGS = {
    'ENABLE_CSRF_PROTECTION': True,
    'SECURE_COOKIES': True,
    'SESSION_TIMEOUT': 3600,  # ساعة واحدة
    'PASSWORD_REQUIREMENTS': {
        'MIN_LENGTH': 8,
        'REQUIRE_UPPERCASE': True,
        'REQUIRE_LOWERCASE': True,
        'REQUIRE_NUMBERS': True,
        'REQUIRE_SYMBOLS': False,
    },
    'FAILED_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_DURATION': 300,  # 5 دقائق
}

# إعدادات المراقبة والتشخيص
INSTALLATION_MONITORING_SETTINGS = {
    'ENABLE_PERFORMANCE_MONITORING': True,
    'SLOW_QUERY_THRESHOLD': 1.0,  # ثانية
    'MEMORY_USAGE_THRESHOLD': 80,  # نسبة مئوية
    'DISK_USAGE_THRESHOLD': 90,  # نسبة مئوية
    'ERROR_RATE_THRESHOLD': 5,  # نسبة مئوية
    'HEALTH_CHECK_INTERVAL': 300,  # ثانية
}

# دالة للحصول على إعداد محدد
def get_installation_setting(key, default=None):
    """
    الحصول على إعداد من إعدادات التركيبات
    
    Args:
        key (str): مفتاح الإعداد (يمكن استخدام النقاط للوصول للإعدادات المتداخلة)
        default: القيمة الافتراضية إذا لم يوجد الإعداد
    
    Returns:
        القيمة المطلوبة أو القيمة الافتراضية
    """
    from django.conf import settings
    
    # البحث في إعدادات Django أولاً
    django_settings = getattr(settings, 'INSTALLATION_SETTINGS', {})
    if key in django_settings:
        return django_settings[key]
    
    # البحث في الإعدادات الافتراضية
    keys = key.split('.')
    value = INSTALLATION_SETTINGS
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default

# دالة لتحديث إعداد
def update_installation_setting(key, value):
    """
    تحديث إعداد في إعدادات التركيبات
    
    Args:
        key (str): مفتاح الإعداد
        value: القيمة الجديدة
    """
    # يمكن إضافة منطق لحفظ الإعدادات في قاعدة البيانات
    # أو ملف إعدادات منفصل
    pass

# دالة للتحقق من صحة الإعدادات
def validate_installation_settings():
    """
    التحقق من صحة إعدادات التركيبات
    
    Returns:
        tuple: (is_valid, errors_list)
    """
    errors = []
    
    # التحقق من الحدود
    max_daily = get_installation_setting('MAX_DAILY_INSTALLATIONS')
    if not isinstance(max_daily, int) or max_daily <= 0:
        errors.append('MAX_DAILY_INSTALLATIONS يجب أن يكون رقم موجب')
    
    max_windows = get_installation_setting('MAX_TECHNICIAN_WINDOWS')
    if not isinstance(max_windows, int) or max_windows <= 0:
        errors.append('MAX_TECHNICIAN_WINDOWS يجب أن يكون رقم موجب')
    
    # التحقق من أوقات العمل
    work_start = get_installation_setting('WORK_START_TIME')
    work_end = get_installation_setting('WORK_END_TIME')
    
    try:
        from datetime import datetime
        start_time = datetime.strptime(work_start, '%H:%M')
        end_time = datetime.strptime(work_end, '%H:%M')
        
        if start_time >= end_time:
            errors.append('وقت بداية العمل يجب أن يكون قبل وقت النهاية')
    except ValueError:
        errors.append('تنسيق أوقات العمل غير صحيح (استخدم HH:MM)')
    
    # التحقق من إعدادات البريد الإلكتروني
    if get_installation_setting('ALERT_SETTINGS.ENABLE_EMAIL_ALERTS'):
        from_email = get_installation_setting('FROM_EMAIL', '')
        if not from_email:
            errors.append('FROM_EMAIL مطلوب عند تفعيل إنذارات البريد الإلكتروني')
    
    return len(errors) == 0, errors

# تطبيق الإعدادات على Django
def apply_installation_settings_to_django():
    """
    تطبيق إعدادات التركيبات على إعدادات Django
    """
    from django.conf import settings
    
    # تحديث إعدادات Django بإعدادات التركيبات
    if not hasattr(settings, 'INSTALLATION_SETTINGS'):
        settings.INSTALLATION_SETTINGS = INSTALLATION_SETTINGS
    
    # تحديث إعدادات قاعدة البيانات
    if hasattr(settings, 'DATABASES') and 'default' in settings.DATABASES:
        settings.DATABASES['default'].update(INSTALLATION_DATABASE_SETTINGS)
    
    # تحديث إعدادات التخزين المؤقت
    if not hasattr(settings, 'CACHES'):
        settings.CACHES = {}
    settings.CACHES['installations'] = INSTALLATION_CACHE_SETTINGS
    
    # تحديث إعدادات السجلات
    if hasattr(settings, 'LOGGING'):
        settings.LOGGING['loggers'].update(INSTALLATION_LOGGING_SETTINGS['loggers'])
        settings.LOGGING['handlers'].update(INSTALLATION_LOGGING_SETTINGS['handlers'])
        settings.LOGGING['formatters'].update(INSTALLATION_LOGGING_SETTINGS['formatters'])
