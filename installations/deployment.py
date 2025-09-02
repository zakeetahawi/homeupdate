# إعدادات النشر لقسم التركيبات

import os
from pathlib import Path

# إعدادات البيئة
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = ENVIRONMENT == 'development'

# إعدادات قاعدة البيانات
DATABASE_CONFIG = {
    'development': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'production': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'installations_db'),
        'USER': os.getenv('DB_USER', 'installations_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    },
    'staging': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'installations_staging'),
        'USER': os.getenv('DB_USER', 'installations_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
    }
}

# إعدادات الوسائط
MEDIA_CONFIG = {
    'development': {
        'MEDIA_URL': '/media/',
        'MEDIA_ROOT': BASE_DIR / 'media',
    },
    'production': {
        'MEDIA_URL': os.getenv('MEDIA_URL', '/media/'),
        'MEDIA_ROOT': os.getenv('MEDIA_ROOT', '/var/www/media'),
    },
    'staging': {
        'MEDIA_URL': os.getenv('MEDIA_URL', '/media/'),
        'MEDIA_ROOT': os.getenv('MEDIA_ROOT', '/var/www/media'),
    }
}

# إعدادات التخزين المؤقت
CACHE_CONFIG = {
    'development': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
    'production': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    },
    'staging': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# إعدادات البريد الإلكتروني
EMAIL_CONFIG = {
    'development': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
    'production': {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'HOST': os.getenv('EMAIL_HOST', 'smtp.gmail.com'),
        'PORT': int(os.getenv('EMAIL_PORT', 587)),
        'USE_TLS': True,
        'USERNAME': os.getenv('EMAIL_USERNAME', ''),
        'PASSWORD': os.getenv('EMAIL_PASSWORD', ''),
    },
    'staging': {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'HOST': os.getenv('EMAIL_HOST', 'smtp.gmail.com'),
        'PORT': int(os.getenv('EMAIL_PORT', 587)),
        'USE_TLS': True,
        'USERNAME': os.getenv('EMAIL_USERNAME', ''),
        'PASSWORD': os.getenv('EMAIL_PASSWORD', ''),
    }
}

# إعدادات الأمان
SECURITY_CONFIG = {
    'development': {
        'SECRET_KEY': 'django-insecure-development-key',
        'ALLOWED_HOSTS': ['localhost', '127.0.0.1'],
        'CORS_ALLOWED_ORIGINS': ['http://localhost:3000'],
    },
    'production': {
        'SECRET_KEY': os.getenv('SECRET_KEY', ''),
        'ALLOWED_HOSTS': os.getenv('ALLOWED_HOSTS', '').split(','),
        'CORS_ALLOWED_ORIGINS': os.getenv('CORS_ALLOWED_ORIGINS', '').split(','),
        'SECURE_SSL_REDIRECT': True,
        'SESSION_COOKIE_SECURE': True,
        'CSRF_COOKIE_SECURE': True,
    },
    'staging': {
        'SECRET_KEY': os.getenv('SECRET_KEY', ''),
        'ALLOWED_HOSTS': os.getenv('ALLOWED_HOSTS', '').split(','),
        'CORS_ALLOWED_ORIGINS': os.getenv('CORS_ALLOWED_ORIGINS', '').split(','),
        'SECURE_SSL_REDIRECT': False,
        'SESSION_COOKIE_SECURE': False,
        'CSRF_COOKIE_SECURE': False,
    }
}

# إعدادات Celery
CELERY_CONFIG = {
    'development': {
        'BROKER_URL': 'redis://localhost:6379/0',
        'RESULT_BACKEND': 'redis://localhost:6379/0',
    },
    'production': {
        'BROKER_URL': os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        'RESULT_BACKEND': os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    },
    'staging': {
        'BROKER_URL': os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        'RESULT_BACKEND': os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    }
}

# إعدادات المراقبة
MONITORING_CONFIG = {
    'development': {
        'SENTRY_DSN': None,
        'LOGGING_LEVEL': 'DEBUG',
    },
    'production': {
        'SENTRY_DSN': os.getenv('SENTRY_DSN', ''),
        'LOGGING_LEVEL': 'INFO',
    },
    'staging': {
        'SENTRY_DSN': os.getenv('SENTRY_DSN', ''),
        'LOGGING_LEVEL': 'DEBUG',
    }
}

# إعدادات التطبيق
APP_CONFIG = {
    'development': {
        'DEBUG': True,
        'INSTALLED_APPS': [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'installations',
            'debug_toolbar',
        ],
        'MIDDLEWARE': [
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            'debug_toolbar.middleware.DebugToolbarMiddleware',
        ],
    },
    'production': {
        'DEBUG': False,
        'INSTALLED_APPS': [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'installations',
            'corsheaders',
            'rest_framework',
            'channels',
        ],
        'MIDDLEWARE': [
            'corsheaders.middleware.CorsMiddleware',
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ],
    },
    'staging': {
        'DEBUG': True,
        'INSTALLED_APPS': [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'installations',
            'corsheaders',
            'rest_framework',
            'channels',
        ],
        'MIDDLEWARE': [
            'corsheaders.middleware.CorsMiddleware',
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ],
    }
}

# دالة للحصول على الإعدادات
def get_settings(environment=None):
    """الحصول على إعدادات البيئة المحددة"""
    if environment is None:
        environment = ENVIRONMENT
    
    return {
        'DATABASES': {
            'default': DATABASE_CONFIG[environment]
        },
        'CACHES': {
            'default': CACHE_CONFIG[environment]
        },
        'EMAIL': EMAIL_CONFIG[environment],
        'SECURITY': SECURITY_CONFIG[environment],
        'CELERY': CELERY_CONFIG[environment],
        'MONITORING': MONITORING_CONFIG[environment],
        'APP': APP_CONFIG[environment],
        'MEDIA': MEDIA_CONFIG[environment],
    }

# إعدادات التطبيق الافتراضية
DEFAULT_SETTINGS = get_settings()

# دالة لتطبيق الإعدادات
def apply_settings(settings_module):
    """تطبيق الإعدادات على وحدة الإعدادات"""
    settings = get_settings()
    
    # تطبيق إعدادات قاعدة البيانات
    settings_module.DATABASES = settings['DATABASES']
    
    # تطبيق إعدادات التخزين المؤقت
    settings_module.CACHES = settings['CACHES']
    
    # تطبيق إعدادات البريد الإلكتروني
    for key, value in settings['EMAIL'].items():
        setattr(settings_module, f'EMAIL_{key}', value)
    
    # تطبيق إعدادات الأمان
    for key, value in settings['SECURITY'].items():
        setattr(settings_module, key, value)
    
    # تطبيق إعدادات التطبيق
    for key, value in settings['APP'].items():
        setattr(settings_module, key, value)
    
    # تطبيق إعدادات الوسائط
    for key, value in settings['MEDIA'].items():
        setattr(settings_module, key, value)
    
    # تطبيق إعدادات Celery
    settings_module.CELERY_BROKER_URL = settings['CELERY']['BROKER_URL']
    settings_module.CELERY_RESULT_BACKEND = settings['CELERY']['RESULT_BACKEND']
    
    # تطبيق إعدادات المراقبة
    if settings['MONITORING']['SENTRY_DSN']:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        
        sentry_sdk.init(
            dsn=settings['MONITORING']['SENTRY_DSN'],
            integrations=[DjangoIntegration()],
            traces_sample_rate=1.0,
            send_default_pii=True,
        )
    
    return settings_module 