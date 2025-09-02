import os
# ======================================
# Slow Query & Performance Logging
# ======================================
import logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'slow_queries_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/tmp/slow_queries.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['slow_queries_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'performance': {
            'handlers': ['slow_queries_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# تسجيل الاستعلامات البطيئة فقط (أكبر من 500ms)
import time
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

class QueryPerformanceLoggingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        request._start_time = time.time()

    def process_response(self, request, response):
        total_time = (time.time() - getattr(request, '_start_time', time.time())) * 1000
        if total_time > 500:
            logger = logging.getLogger('performance')
            logger.info(f"SLOW PAGE: {request.path} | {int(total_time)}ms | user={getattr(request, 'user', None)}")
        for q in getattr(connection, 'queries', []):
            duration = float(q.get('time', 0)) * 1000
            if duration > 500:
                logger = logging.getLogger('performance')
                logger.info(f"SLOW QUERY: {q['sql']} | {duration:.0f}ms | path={getattr(request, 'path', '')}")
        return response

# أضف هذا الميدل وير في أعلى قائمة MIDDLEWARE
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
# تحديد ما إذا كان النظام في وضع الاختبار
TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# إعدادات المطورين لعرض الأخطاء
ADMINS = [
    ('Admin', 'admin@localhost'),
]
MANAGERS = ADMINS

# --- إعدادات الأمان ---
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-development-key-for-jazzmin-testing-only-change-in-production-123456789')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# قراءة ALLOWED_HOSTS من متغيرات البيئة. يجب أن تكون سلسلة نصية مفصولة بفاصلة.
# مثال: ALLOWED_HOSTS="localhost,127.0.0.1,mydomain.com"
allowed_hosts_str = os.environ.get('ALLOWED_HOSTS')
if not allowed_hosts_str:
    ALLOWED_HOSTS = []
else:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',')]

# في وضع التطوير، يمكن إضافة نطاقات إضافية لتسهيل الاختبار
if DEBUG:
    ALLOWED_HOSTS.extend([
    'localhost',
    '127.0.0.1',
    '192.168.2.25',  # عنوان الشبكة المحلية
    '*.trycloudflare.com',
    '*.ngrok-free.app',
    'testserver',  # للاختبارات
    ])

# إضافة دومين elkhawaga.uk وجميع النطاقات الفرعية
ALLOWED_HOSTS.extend([
    'elkhawaga.uk',
    'www.elkhawaga.uk',
    'crm.elkhawaga.uk',
    'admin.elkhawaga.uk',
    'api.elkhawaga.uk',
    '*.elkhawaga.uk',
])

# إضافة عناوين الشبكة المحلية الشائعة
ALLOWED_HOSTS.extend([
    '192.168.1.*',  # نطاق الشبكة المحلية الشائع
    '192.168.2.*',  # نطاق الشبكة المحلية الشائع
    '10.0.0.*',     # نطاق الشبكة المحلية الشائع
    '172.16.*',     # نطاق الشبكة المحلية الشائع
    '172.17.*',     # نطاق الشبكة المحلية الشائع
    '172.18.*',     # نطاق الشبكة المحلية الشائع
    '172.19.*',     # نطاق الشبكة المحلية الشائع
    '172.20.*',     # نطاق الشبكة المحلية الشائع
    '172.21.*',     # نطاق الشبكة المحلية الشائع
    '172.22.*',     # نطاق الشبكة المحلية الشائع
    '172.23.*',     # نطاق الشبكة المحلية الشائع
    '172.24.*',     # نطاق الشبكة المحلية الشائع
    '172.25.*',     # نطاق الشبكة المحلية الشائع
    '172.26.*',     # نطاق الشبكة المحلية الشائع
    '172.27.*',     # نطاق الشبكة المحلية الشائع
    '172.28.*',     # نطاق الشبكة المحلية الشائع
    '172.29.*',     # نطاق الشبكة المحلية الشائع
    '172.30.*',     # نطاق الشبكة المحلية الشائع
    '172.31.*',     # نطاق الشبكة المحلية الشائع
])

# Application definition
INSTALLED_APPS = [
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crm.apps.CrmConfig',
    'accounts',
    'user_activity.apps.UserActivityConfig',  # تطبيق نشاط المستخدمين
    'customers',
    'inspections',
    'inventory',
    'orders',
    'manufacturing',
    'cutting.apps.CuttingConfig',  # نظام التقطيع الجديد
    'reports',
    'installations',
    'complaints.apps.ComplaintsConfig',  # نظام إدارة الشكاوى
    'notifications.apps.NotificationsConfig',  # نظام الإشعارات المتكامل
    'odoo_db_manager.apps.OdooDbManagerConfig',
    'backup_system.apps.BackupSystemConfig',  # نظام النسخ الاحتياطي والاستعادة الجديد
    'corsheaders',
    'django_apscheduler',
    'dbbackup',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'widget_tweaks',
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'accounts.backends.CustomModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# قائمة الوسطاء الأساسية (تم تعطيل الوسطاء المخصصة مؤقتاً)
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # إذا كنت تستخدم Whitenoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.log_terminal_activity.AdvancedActivityLoggerMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'crm.middleware.permission_handler.PermissionDeniedMiddleware',
    'odoo_db_manager.middleware.default_user.DefaultUserMiddleware',  # إنشاء مستخدم افتراضي
    # 'crm.middleware.PerformanceMiddleware',  # تم تعطيل مؤقتاً
    # 'crm.middleware.LazyLoadMiddleware',  # تم تعطيل مؤقتاً
]

# Debug toolbar configuration for performance monitoring
# تم تعطيل Debug Toolbar نهائياً بناءً على طلب المستخدم

AUTH_USER_MODEL = 'accounts.User'

# تم تعطيل middleware إضافي مؤقتاً لحل مشكلة التحميل
# if DEBUG:
#     MIDDLEWARE.extend([
#         'crm.middleware.QueryPerformanceMiddleware',
#         'crm.middleware.PerformanceCookiesMiddleware',
#     ])

ROOT_URLCONF = 'crm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.departments',
                'accounts.context_processors.company_info',
                'accounts.context_processors.footer_settings',
                'accounts.context_processors.system_settings',
                'accounts.context_processors.branch_messages',
                'accounts.context_processors.notifications_context',
                'accounts.context_processors.admin_notifications_context',
                'notifications.context_processors.notifications_context',
                'crm.context_processors.admin_stats',
                'crm.context_processors.jazzmin_extras',
            ],
        },
    },
]

WSGI_APPLICATION = 'crm.wsgi.application'

# تم إزالة إعدادات Channels و Redis لأنها غير مستخدمة
# ASGI_APPLICATION = 'crm.asgi.application'
# CHANNEL_LAYERS = {...}

# --- قاعدة البيانات ---
# استخدام dj_database_url لتبسيط تكوين قاعدة البيانات من متغير بيئة واحد.
# مثال: DATABASE_URL="postgres://user:password@host:port/dbname"
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ImproperlyConfigured("يجب تعيين رابط قاعدة البيانات (DATABASE_URL) في متغيرات البيئة.")

# Cache Configuration - استخدام Redis للأداء الأفضل
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'TIMEOUT': 300,  # 5 minutes
        'KEY_PREFIX': 'homeupdate',
        'VERSION': 1,
    },
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            },
            'IGNORE_EXCEPTIONS': True,
        },
        'TIMEOUT': 1800,  # 30 minutes
        'KEY_PREFIX': 'homeupdate_session',
    },
    'query': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/3',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 30,
                'retry_on_timeout': True,
            },
            'IGNORE_EXCEPTIONS': True,
        },
        'TIMEOUT': 600,  # 10 minutes
        'KEY_PREFIX': 'homeupdate_query',
    }
}

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'crm_system',
        'USER': 'postgres',
        'PASSWORD': '5525',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 300,  # إعادة استخدام الاتصالات لمدة 5 دقائق
        'OPTIONS': {
            'client_encoding': 'UTF8',
            'sslmode': 'prefer',
            'connect_timeout': 10,
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# استخدام تخزين أبسط لتجنب مشاكل ملفات source map
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# إعدادات النسخ الاحتياطي المحسنة مع الضغط
BACKUP_ROOT = os.path.join(BASE_DIR, 'backups')
os.makedirs(BACKUP_ROOT, exist_ok=True)

# استخدام نفس المجلد للملفات المؤقتة والنسخ الاحتياطية
DBBACKUP_TMP_DIR = BACKUP_ROOT
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': BACKUP_ROOT}
DBBACKUP_CLEANUP_KEEP = 10  # الاحتفاظ بآخر 10 نسخ احتياطية

# إعدادات الضغط للنسخ الاحتياطية
BACKUP_COMPRESSION = {
    'ENABLED': True,
    'COMPRESSION_LEVEL': 9,  # أقصى مستوى ضغط (0-9)
    'FILE_EXTENSION': '.gz',
    'AUTO_COMPRESS_ON_CREATE': True,
    'AUTO_COMPRESS_ON_DOWNLOAD': True,
    'CHUNK_SIZE': 1024 * 1024,  # 1MB chunks للنسخ
}

# أنواع الملفات المدعومة للضغط
BACKUP_SUPPORTED_FORMATS = [
    'json', 'sqlite3', 'sql', 'csv', 'txt'
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Cache settings
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#         'LOCATION': 'unique-snowflake',
#         'TIMEOUT': 300,  # 5 minutes
#         'OPTIONS': {
#             'MAX_ENTRIES': 500,  # تقليل عدد العناصر المخزنة لتوفير الذاكرة
#             'CULL_FREQUENCY': 2,  # زيادة تكرار التنظيف
#         }
#     }
# }

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'crm.auth.CustomJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# إعدادات JWT (Simple JWT)
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),  # زيادة مدة صلاحية التوكن إلى 7 أيام
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),  # زيادة مدة صلاحية توكن التحديث إلى 30 يوم
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
    'AUTH_COOKIE_SECURE': False,  # تعطيل في جميع البيئات لتجنب مشاكل المصادقة
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Security Settings for Production
if not DEBUG and os.environ.get('ENABLE_SSL_SECURITY', 'false').lower() == 'true':
    # HTTPS/SSL Settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Session and CSRF Settings
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

    # HSTS Settings
    SECURE_HSTS_SECONDS = 31536000  # سنة واحدة
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Content Security Settings
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

    # Referrer Policy
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

    # Cross-Origin Opener Policy
    # COOP header commented out - was causing issues in development

    # Additional Security Headers
    CSRF_TRUSTED_ORIGINS = [
        'https://localhost',
        'https://127.0.0.1',
    ]

# Cross-Origin Opener Policy - explicitly disabled for HTTP development
# Django 4.2+ sets this to 'same-origin' by default, which causes browser warnings on HTTP
# We explicitly set it to None to disable the header in development
if DEBUG:
    # Disable COOP header in development to prevent browser warnings on HTTP
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None
elif os.environ.get('ENABLE_SSL_SECURITY', 'false').lower() == 'true':
    # Enable COOP header only in production with HTTPS
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
else:
    # Default: disable COOP header
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# CORS settings (تم دمج الإعدادات المكررة)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',  # منفذ Vite الافتراضي
    'http://127.0.0.1:5173',  # منفذ Vite الافتراضي
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # نطاقات الإنتاج
    'https://elkhawaga.uk',
    'https://www.elkhawaga.uk',
    'https://crm.elkhawaga.uk',
    'https://api.elkhawaga.uk',
    'https://admin.elkhawaga.uk',
    'http://elkhawaga.uk',
    'http://www.elkhawaga.uk',
    'http://crm.elkhawaga.uk',
    'http://api.elkhawaga.uk',
    'http://admin.elkhawaga.uk',
]

CORS_ORIGIN_WHITELIST = CORS_ALLOWED_ORIGINS  # استخدام نفس القائمة

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['*']

CORS_ALLOW_HEADERS = [
    'Authorization',
    'Content-Type',
    'X-CSRFToken',
    'accept',
    'accept-encoding',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-requested-with',
    'x-request-id',
]

# Disable CSRF for /api/ endpoints in development
if DEBUG:

    class DisableCSRFMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            if request.path.startswith('/api/'):
                setattr(request, '_dont_enforce_csrf_checks', True)
            return self.get_response(request)

    MIDDLEWARE.insert(0, 'crm.settings.DisableCSRFMiddleware')

# Security and Session Settings - CSRF Trusted Origins محسن
CSRF_TRUSTED_ORIGINS = [
    # نطاقات التطوير المحلي
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost',
    'http://127.0.0.1',

    # نطاقات الإنتاج
    'https://elkhawaga.uk',
    'https://www.elkhawaga.uk',
    'https://crm.elkhawaga.uk',
    'https://api.elkhawaga.uk',
    'https://admin.elkhawaga.uk',
] + CORS_ALLOWED_ORIGINS

# إعدادات CSRF موحدة ومحسنة
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # يجب أن يكون False للسماح لـ JavaScript بالوصول
CSRF_COOKIE_SECURE = False if DEBUG else True  # آمن في الإنتاج فقط
CSRF_USE_SESSIONS = False
CSRF_FAILURE_VIEW = 'crm.csrf_views.csrf_failure'  # صفحة خطأ CSRF مخصصة

# إعدادات Session موحدة
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_AGE = 86400 * 7  # 7 أيام
SESSION_COOKIE_SECURE = False  # اجعلها True إذا كنت تستخدم HTTPS فقط
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # يبقى المستخدم مسجلاً حتى بعد إغلاق المتصفح

# إعدادات جدولة المهام
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # Seconds

# تكوين المهام المجدولة
SCHEDULER_CONFIG = {
    "apscheduler.jobstores.default": {
        "class": "django_apscheduler.jobstores:DjangoJobStore"
    },
    "apscheduler.executors.processpool": {
        "type": "threadpool",
        "max_workers": 5
    },
    "apscheduler.job_defaults.coalesce": "false",
    "apscheduler.job_defaults.max_instances": "3",
    "apscheduler.timezone": TIME_ZONE,
}

# تكوين مهمة تنظيف الجلسات
SESSION_CLEANUP_SCHEDULE = {
    'days': 1,  # تنظيف الجلسات الأقدم من يوم واحد
    'fix_users': True,  # إصلاح المستخدمين المكررين أيضًا
    'frequency': 'daily',  # تنفيذ المهمة يوميًا
    'hour': 3,  # تنفيذ المهمة في الساعة 3 صباحًا
    'minute': 0,  # تنفيذ المهمة في الدقيقة 0
}

# إعدادات تحسين الأداء
# تقليل عدد الاستعلامات المسموح بها في صفحة واحدة
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# إعدادات نظام تتبع النشاط
ACTIVITY_TRACKING = {
    'ENABLED': True,
    'LOG_ANONYMOUS_USERS': False,
    'LOG_STATIC_FILES': False,
    'LOG_MEDIA_FILES': False,
    'CLEANUP_DAYS': 30,  # حذف السجلات الأقدم من 30 يوم
    'ONLINE_TIMEOUT_MINUTES': 5,  # اعتبار المستخدم غير متصل بعد 5 دقائق من عدم النشاط
    'AUTO_CLEANUP_ENABLED': True,
    'MAX_ACTIVITY_LOGS_PER_USER': 1000,  # الحد الأقصى لسجلات النشاط لكل مستخدم
}

# تعطيل التسجيل المفصل في الإنتاج
# if not DEBUG:
#     LOGGING = {
#         'version': 1,
#         'disable_existing_loggers': False,
#         'handlers': {
#             'console': {
#                 'class': 'logging.StreamHandler',
#                 'level': 'INFO',  # تغيير مستوى التسجيل إلى INFO للحصول على مزيد من المعلومات
#             },
#         },
#         'loggers': {
#             'django': {
#                 'handlers': ['console'],
#                 'level': 'INFO',
#                 'propagate': True,
#             },
#             'django.db.backends': {
#                 'handlers': ['console'],
#                 'level': 'WARNING',
#                 'propagate': False,
#             },
#             'data_management': {  # إضافة تسجيل خاص لتطبيق data_management
#                 'handlers': ['console'],
#                 'level': 'INFO',
#                 'propagate': True,
#             },
#         },
#         'root': {
#             'handlers': ['console'],
#             'level': 'INFO',
#         },
#     }

#     # تقليل عدد الاتصالات المتزامنة بقاعدة البيانات
#     DATABASES['default']['CONN_MAX_AGE'] = 300  # 5 دقائق

#     # تعطيل التصحيح التلقائي للمخطط
#     DATABASES['default']['AUTOCOMMIT'] = True  # تمكين AUTOCOMMIT لتجنب مشاكل الاتصال

#     # تم نقل إعدادات قاعدة بيانات Railway إلى بداية الملف

# Advanced Logging Configuration
LOGGING = {
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
        'colored': {
            'format': '\033[1;36m{asctime}\033[0m \033[1;32m{levelname}\033[0m \033[1;33m{module}\033[0m {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'filters': {
        'exclude_unwanted_requests': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not any(path in record.getMessage() for path in [
                '/accounts/notifications/data/',
                '/accounts/api/online-users/',
                '/media/users/',
                '/static/',
                'favicon.ico'
            ])
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
            'filters': ['exclude_unwanted_requests'],
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'performance_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'performance.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['performance_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'crm': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'orders': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'customers': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'manufacturing': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'inspections': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Performance Settings
PERFORMANCE_SETTINGS = {
    'QUERY_TIMEOUT': 30,  # seconds
    'CACHE_TIMEOUT': 300,  # seconds
    'PAGINATION_SIZE': 20,
    'MAX_UPLOAD_SIZE': 10 * 1024 * 1024,  # 10MB
    'COMPRESSION_ENABLED': True,
    'LAZY_LOADING_ENABLED': True,
    'VIRTUAL_SCROLLING_ENABLED': True,
    'QUERY_DEBUG_ENABLED': DEBUG,  # تمكين تحليل الاستعلامات في وضع التطوير
    'SLOW_QUERY_THRESHOLD': 0.1,  # تسجيل الاستعلامات التي تستغرق أكثر من 100ms
}

# Security Settings
SECURITY_SETTINGS = {
    'PASSWORD_MIN_LENGTH': 8,
    'PASSWORD_COMPLEXITY': True,
    'PASSWORD_EXPIRY_DAYS': 90,
    'SESSION_TIMEOUT': 30,  # minutes
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_DURATION': 30,  # minutes
    'TWO_FACTOR_ENABLED': True,
    'AUDIT_LOGGING_ENABLED': True,
}

# Advanced Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF Protection - تم نقل الإعدادات إلى الأعلى لتجنب التكرار

# Password Security
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Rate Limiting (if using django-ratelimit)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Security Headers
SECURE_HSTS_SECONDS = 0  # Set to 31536000 in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # Set to True in production
SECURE_HSTS_PRELOAD = False  # Set to True in production

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")

# File Upload Security
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 10MB
FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# Database Security
DATABASES['default']['OPTIONS'].update({
    'sslmode': 'prefer',  # Use SSL if available
})

# Cache Security
CACHES['default']['OPTIONS'].update({
    'KEY_PREFIX': 'crm_',
    'VERSION': 1,
})

# Email Security (if using email)
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

# Admin Security
ADMIN_URL = 'admin/'
ADMIN_SITE_HEADER = "نظام إدارة الخواجة"
ADMIN_SITE_TITLE = "لوحة الإدارة"
ADMIN_INDEX_TITLE = "مرحباً بك في نظام إدارة الخواجة"

# Django Jazzmin Configuration
JAZZMIN_SETTINGS = {
    # العناوين الأساسية
    "site_title": "نظام إدارة الخواجة",
    "site_header": "نظام إدارة الخواجة",
    "site_brand": "الخواجة",
    "site_logo": "img/logo.png",
    "login_logo": "img/logo.png",
    "login_logo_dark": "img/logo.png",
    "site_logo_classes": "img-circle",
    "site_icon": "img/logo.png",
    "welcome_sign": "مرحباً بك في نظام إدارة الخواجة",
    "copyright": "نظام إدارة الخواجة",
    "search_model": ["auth.User", "customers.Customer", "orders.Order"],
    "user_avatar": "accounts.User.image",

    # القوائم العلوية
    "topmenu_links": [
        {"name": "الرئيسية", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "الموقع الرئيسي", "url": "/", "new_window": True},
        {"name": "العملاء", "url": "admin:customers_customer_changelist", "permissions": ["customers.view_customer"]},
        {"name": "الطلبات", "url": "admin:orders_order_changelist", "permissions": ["orders.view_order"]},
        {"name": "المعاينات", "url": "admin:inspections_inspection_changelist", "permissions": ["inspections.view_inspection"]},
        {"name": "التصنيع", "url": "admin:manufacturing_manufacturingorder_changelist", "permissions": ["manufacturing.view_manufacturingorder"]},
        {"name": "التركيبات", "url": "admin:installations_installationschedule_changelist", "permissions": ["installations.view_installationschedule"]},
        {"name": "المخزون", "url": "admin:inventory_product_changelist", "permissions": ["inventory.view_product"]},
        {"name": "التقارير", "url": "admin:reports_report_changelist", "permissions": ["reports.view_report"]},
        {"name": "النسخ الاحتياطي", "url": "admin:backup_system_backupjob_changelist", "permissions": ["backup_system.view_backupjob"]},
    ],

    # القوائم الجانبية للمستخدم
    "usermenu_links": [
        {"name": "إعدادات الشركة", "url": "/accounts/company_info/", "icon": "fas fa-building"},
        {"model": "auth.user"},
    ],

    # إظهار/إخفاء عناصر
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [
        "accounts", "customers", "orders", "inspections",
        "manufacturing", "installations", "inventory",
        "reports", "complaints", "backup_system", "odoo_db_manager"
    ],

    # الأيقونات المخصصة
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "accounts.User": "fas fa-user-tie",
        "accounts.CompanyInfo": "fas fa-building",
        "accounts.Branch": "fas fa-map-marker-alt",
        "accounts.Department": "fas fa-sitemap",
        "accounts.Salesperson": "fas fa-user-tag",
        "customers.Customer": "fas fa-user-friends",
        "customers.CustomerCategory": "fas fa-tags",
        "orders.Order": "fas fa-shopping-cart",
        "orders.Payment": "fas fa-credit-card",
        "inspections.Inspection": "fas fa-search",
        "manufacturing.ManufacturingOrder": "fas fa-industry",
        "installations.InstallationSchedule": "fas fa-tools",
        "installations.Technician": "fas fa-hard-hat",
        "inventory.Product": "fas fa-box",
        "inventory.Category": "fas fa-list",
        "inventory.Warehouse": "fas fa-warehouse",
        "reports.Report": "fas fa-chart-bar",
        "complaints.Complaint": "fas fa-exclamation-triangle",
        "backup_system.BackupJob": "fas fa-save",
        "backup_system.RestoreJob": "fas fa-undo",
        "odoo_db_manager.Database": "fas fa-database",
    },

    # الألوان والثيم
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": "admin/css/sidebar_left.css",
    "custom_js": "admin/js/custom_admin.js",
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,

    # إعدادات الثيم
    "theme": "flatly",
    "dark_mode_theme": "darkly",

    # إعدادات الجدول
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs"
    },

    # اللغة والاتجاه
    "language_chooser": False,

    # تخصيص الصفحة الرئيسية
    "show_ui_builder": False,

    # إضافة context processors مخصص
    "custom_links": {
        "customers": [
            {
                "name": "إضافة عميل جديد",
                "url": "admin:customers_customer_add",
                "icon": "fas fa-plus",
                "permissions": ["customers.add_customer"]
            }
        ],
        "orders": [
            {
                "name": "إنشاء طلب جديد",
                "url": "admin:orders_order_add",
                "icon": "fas fa-plus",
                "permissions": ["orders.add_order"]
            }
        ]
    },
}

# إعدادات واجهة المستخدم لـ Jazzmin
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-primary navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": False
}

# ======================================
# Django Admin Interface Configuration
# ======================================
X_FRAME_OPTIONS = 'SAMEORIGIN'
SILENCED_SYSTEM_CHECKS = ['security.W019']

# ======================================
# Company Settings
# ======================================
COMPANY_NAME = "شركة الخواجة للألمنيوم والزجاج"

# ======================================
# Celery Configuration
# ======================================

# إعدادات Celery الأساسية
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# إعدادات التسلسل
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'

# إعدادات المنطقة الزمنية
CELERY_TIMEZONE = 'Africa/Cairo'
CELERY_ENABLE_UTC = True

# إعدادات الأداء
CELERY_TASK_COMPRESSION = 'gzip'
CELERY_RESULT_COMPRESSION = 'gzip'
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# إعدادات انتهاء الصلاحية
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 دقائق
CELERY_TASK_TIME_LIMIT = 600       # 10 دقائق
CELERY_RESULT_EXPIRES = 3600       # ساعة واحدة

# إعدادات المراقبة
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# إعدادات الأمان والشبكة
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# إعدادات الذاكرة
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000  # 200MB

# إعدادات التسجيل
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_LOG_COLOR = False

# تخصيص إعدادات للبيئة الإنتاجية
if not DEBUG:
    CELERY_TASK_SOFT_TIME_LIMIT = 180  # 3 دقائق
    CELERY_TASK_TIME_LIMIT = 300       # 5 دقائق
    CELERY_WORKER_MAX_MEMORY_PER_CHILD = 150000  # 150MB
