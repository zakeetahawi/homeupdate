import os
from pathlib import Path

# تحميل متغيرات البيئة من .env
from dotenv import load_dotenv
load_dotenv()

# ======================================
# Enhanced Logging Configuration
# ======================================
import logging

# الحصول على BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# إنشاء مجلد logs إذا لم يكن موجوداً
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
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
        'minimal': {
            'format': '{message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'django_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'security.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 10,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'performance_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'performance.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'database_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'database.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'api_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'api.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'slow_queries_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'slow_queries.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'null': {
            'class': 'logging.NullHandler',
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
        'customers': {
            'handlers': ['console', 'django_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['api_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # إيقاف رسائل التصحيح غير المهمة
        'accounts.middleware': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'accounts.signals': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'user_activity': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'daphne.http_protocol': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'daphne.ws_protocol': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
        'websocket_blocker': {
            'handlers': ['slow_queries_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'django_file'],
        'level': 'INFO',
    },
}

# تسجيل الاستعلامات البطيئة فقط (أكبر من 1000ms) لتقليل الضغط
import time
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

class QueryPerformanceLoggingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        request._start_time = time.time()
        # تفعيل مراقبة الاستعلامات - مع التأكد من تفعيل queries logging
        from django.db import connection, reset_queries
        from django.conf import settings
        
        # تفعيل queries logging حتى في حالة DEBUG=False
        if not settings.DEBUG:
            connection.force_debug_cursor = True
        
        reset_queries()
        request._queries_before = len(connection.queries)

    def process_response(self, request, response):
        # حساب الوقت المستغرق
        total_time = (time.time() - getattr(request, '_start_time', time.time())) * 1000
        
        # حساب عدد الاستعلامات
        from django.db import connection
        from django.conf import settings
        
        queries_count = len(connection.queries) - getattr(request, '_queries_before', 0)
        
        # تسجيل الصفحات البطيئة (أكثر من ثانية)
        if total_time > 1000:
            logger = logging.getLogger('performance')
            logger.warning(f"SLOW_PAGE: {request.path} | {int(total_time)}ms | {queries_count} queries | user={getattr(request, 'user', None)}")
        
        # تسجيل الاستعلامات البطيئة (أكثر من 100ms)
        if hasattr(connection, 'queries') and connection.queries:
            slow_queries_logger = logging.getLogger('websocket_blocker')
            for query in connection.queries[getattr(request, '_queries_before', 0):]:
                if 'time' in query and float(query['time']) > 0.1:  # 100ms
                    slow_queries_logger.warning(f"SLOW_QUERY: {query['time']}s | {query['sql'][:200]}...")
        
        # إعادة ضبط force_debug_cursor
        if not settings.DEBUG:
            connection.force_debug_cursor = False
        
        return response

# أضف هذا الميدل وير في أعلى قائمة MIDDLEWARE
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
# تم إزالة dj_database_url و ImproperlyConfigured غير المستخدمين
from django.core.exceptions import ImproperlyConfigured
# تحديد ما إذا كان النظام في وضع الاختبار
TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

# تحميل متغيرات البيئة من ملف .env (إذا كان موجوداً)
if os.path.exists(os.path.join(os.path.dirname(__file__), '..', '.env')):
    load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# إعدادات المطورين لعرض الأخطاء
ADMINS = [
    ('Admin', 'admin@localhost'),
]
MANAGERS = ADMINS

# --- إعدادات الأمان المحسّنة ---
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if os.environ.get('DEVELOPMENT_MODE', 'False').lower() == 'true':
        # مفتاح للتطوير فقط - يتم توليده عشوائياً
        import secrets
        SECRET_KEY = 'dev-insecure-' + secrets.token_hex(32)
        print("⚠️  WARNING: Using development SECRET_KEY. Set SECRET_KEY in environment for production!")
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set in environment variables. "
            "Generate one using: python -c 'import secrets; print(secrets.token_hex(50))'"
        )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# تحذير إذا كان DEBUG مفعّل بدون وضع التطوير
if DEBUG and not os.environ.get('DEVELOPMENT_MODE'):
    import warnings
    warnings.warn(
        "⚠️  DEBUG is True without DEVELOPMENT_MODE! This may be production!",
        RuntimeWarning,
        stacklevel=2
    )

# إعدادات لتقليل الرسائل غير الضرورية وتحسين الأداء
SILENCED_SYSTEM_CHECKS = [
    'urls.W002',  # تجاهل تحذيرات URL patterns
    'models.W042',  # تجاهل تحذيرات auto_now
]

# تقليل مستوى تسجيل Django
if not DEBUG:
    import logging
    logging.getLogger('django.request').setLevel(logging.ERROR)
    logging.getLogger('django.db.backends').setLevel(logging.ERROR)

# إعداد ALLOWED_HOSTS الآمن
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '[::1]',  # IPv6 localhost
    '192.168.1.30',  # IP المحلي
    'elkhawaga.uk',
    'www.elkhawaga.uk',
    '.elkhawaga.uk',  # جميع النطاقات الفرعية
]

# إضافة نطاقات إضافية من متغيرات البيئة
if extra_hosts := os.environ.get('EXTRA_ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend([host.strip() for host in extra_hosts.split(',')])

# في التطوير فقط - السماح لجميع المضيفين المحليين
if DEBUG and os.environ.get('DEVELOPMENT_MODE'):
    ALLOWED_HOSTS.extend([
        '192.168.*.*',
        '10.*.*.*',
        '*.local',
        '*.ngrok.io',
        '*.trycloudflare.com',
    ])
    print(f"🔧 Development mode: ALLOWED_HOSTS = {ALLOWED_HOSTS}")

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
    'core',  # التطبيق الأساسي للـ template tags المشتركة
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
    'accounting.apps.AccountingConfig',  # النظام المحاسبي المتكامل
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


# قائمة الوسطاء الأساسية مع إدارة اتصالات محسنة
# قائمة Middleware محسّنة للأداء والاستقرار
MIDDLEWARE = [
    # الأساسيات - خفيفة وسريعة
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # ضروري للنظام
    'orders.middleware.CurrentUserMiddleware',
    'accounts.middleware.current_user.CurrentUserMiddleware',
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
                'inventory.context_processors.pending_transfers',
            ],
        },
    },
]

WSGI_APPLICATION = 'crm.wsgi.application'



# --- قاعدة البيانات ---
# استخدام الإعدادات المباشرة بدلاً من DATABASE_URL لتبسيط التكوين

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
        'TIMEOUT': 3600,  # ساعة واحدة (نفس SESSION_COOKIE_AGE)
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

# Database Configuration - إعدادات محسّنة للأداء
# تم التحسين في: 2025-10-01
# التحسينات:
# 1. CONN_MAX_AGE = 600 (بدلاً من 0) - إبقاء الاتصالات مفتوحة لمدة 10 دقائق
# 2. CONN_HEALTH_CHECKS = True - فحص صحة الاتصالات تلقائياً
# 3. connect_timeout = 10 - زيادة وقت الانتظار للاتصال
# 4. إضافة statement_timeout - حماية من الاستعلامات البطيئة
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'crm_system',
        'USER': 'postgres',
        'PASSWORD': '5525',
        'HOST': 'localhost',
        'PORT': '5432',

        # ✅ تحسين: إبقاء الاتصالات مفتوحة لمدة 5 دقائق (تقليل من 10 دقائق)
        # يوفر موارد الذاكرة مع الحفاظ على الأداء
        'CONN_MAX_AGE': 300,

        # ✅ تحسين: تفعيل فحص صحة الاتصالات
        # يمنع استخدام اتصالات معطلة ويحسن الاستقرار
        'CONN_HEALTH_CHECKS': True,

        'OPTIONS': {
            'client_encoding': 'UTF8',
            'sslmode': 'disable',

            # ✅ تحسين: زيادة timeout الاتصال من 5 إلى 10 ثوان
            'connect_timeout': 10,

            # ✅ تحسين: إعدادات PostgreSQL للأداء والأمان
            'options': ' '.join([
                '-c statement_timeout=30000',  # 30 ثانية max للاستعلامات
                '-c idle_in_transaction_session_timeout=60000',  # دقيقة للمعاملات الخاملة
                '-c lock_timeout=10000',  # 10 ثوان للأقفال
            ]),
        },
    }
}

# إعدادات احتياطية للاتصال المباشر (للطوارئ)
DATABASES_DIRECT = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'crm_system',
        'USER': 'postgres',
        'PASSWORD': '5525',
        'HOST': 'localhost',
        'PORT': '5432',  # الاتصال المباشر
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'client_encoding': 'UTF8',
            'sslmode': 'prefer',
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000 -c idle_in_transaction_session_timeout=30000',
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
# استخدام WhiteNoise لخدمة الملفات الثابتة في الإنتاج مع Cache Busting
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# إضافة version للملفات لإجبار المتصفح على تحديث الـ cache
STATIC_VERSION = '20251130'  # تحديث هذا الرقم عند تغيير الملفات الثابتة
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

# Forms URLField settings (Django 5.2+)
# استخدام https كافتراضي لحقول URL
FORMS_URLFIELD_ASSUME_HTTPS = True

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

# ============================================
# 🔒 Security Settings - محسّن وآمن
# ============================================

if not DEBUG:
    # HTTPS/SSL Settings
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # سنة واحدة
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Session Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_AGE = 3600  # ساعة واحدة (1 hour)
    
    # CSRF Security
    CSRF_COOKIE_SECURE = True
    # ملاحظة: لا نضع CSRF_COOKIE_HTTPONLY هنا - يتم تعيينه في القسم العام
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_TRUSTED_ORIGINS = [
        'https://elkhawaga.uk',
        'https://www.elkhawaga.uk',
    ]
    
    # Browser Security Headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'same-origin'
    
    # Content Security Policy (CSP) - مفعّل للإنتاج - جميع الموارد محلية + Cloudflare Insights
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'", "https://static.cloudflareinsights.com")
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
    CSP_IMG_SRC = ("'self'", "data:", "blob:")
    CSP_FONT_SRC = ("'self'", "data:")
    CSP_CONNECT_SRC = ("'self'", "https://cloudflareinsights.com")
    CSP_FRAME_ANCESTORS = ("'none'",)
    CSP_BASE_URI = ("'self'",)
    CSP_FORM_ACTION = ("'self'",)
    CSP_UPGRADE_INSECURE_REQUESTS = True
    # حظر جميع المصادر الخارجية غير المصرح بها
    CSP_BLOCK_ALL_MIXED_CONTENT = True
    
else:
    # Development Settings - أقل تقييداً للتطوير
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True  # دائماً مفعّل
    # ملاحظة: لا نضع CSRF_COOKIE_HTTPONLY هنا - يتم تعيينه في القسم العام
    SESSION_COOKIE_AGE = 3600  # ساعة واحدة (1 hour)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'  # أقل تقييداً في التطوير
    
    # CSP في وضع التطوير - معطل أو مرن جداً
    # تعطيل CSP في التطوير لتجنب مشاكل التحميل
    CSP_ENABLED = False  # تعطيل CSP بالكامل في التطوير

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
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://192.168.1.30:8000',
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

# إعدادات CSRF موحدة ومحسنة - تمت إزالة التكرار
CSRF_COOKIE_HTTPONLY = False  # يجب أن يكون False للسماح لـ JavaScript بالوصول
CSRF_USE_SESSIONS = False
CSRF_FAILURE_VIEW = 'crm.csrf_views.csrf_failure'  # صفحة خطأ CSRF مخصصة
# CSRF_COOKIE_SECURE و CSRF_COOKIE_SAMESITE - انظر قسم Security Settings أعلاه

# إعدادات Session موحدة - محسّنة للأمان والأداء
# تم تغيير من cached_db إلى db لحل مشكلة تسجيل الخروج المتكرر
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # استخدام DB فقط لضمان الاستقرار
SESSION_CACHE_ALIAS = 'session'  # لا يُستخدم مع db backend لكن نبقيه للتوافق
SESSION_COOKIE_NAME = 'elkhawaga_sessionid'  # اسم مخصص غير قابل للتخمين
SESSION_SAVE_EVERY_REQUEST = False  # تحسين الأداء
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # يبقى المستخدم مسجلاً حتى بعد إغلاق المتصفح
# SESSION_COOKIE_AGE, SESSION_COOKIE_SECURE - انظر قسم Security Settings أعلاه

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
# Additional Security Headers - تمت إزالة التكرار
# جميع إعدادات الأمان موجودة في قسم Security Settings أعلاه

# Password Security - محسّنة
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # 8 أحرف على الأقل
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password Hashers - محسّنة للأمان
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # افتراضي Django - آمن
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Rate Limiting (if using django-ratelimit)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Security Headers
SECURE_HSTS_SECONDS = 0  # Set to 31536000 in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # Set to True in production
SECURE_HSTS_PRELOAD = False  # Set to True in production

# File Upload Security - محسن للملفات الكبيرة
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1GB للعمليات الكبيرة
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1GB للعمليات الكبيرة
FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# إعدادات إضافية للملفات الكبيرة
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
]

# إعدادات Connection للعمليات الكبيرة - تم توحيدها في DATABASES
# CONN_MAX_AGE = 0  # تم نقلها إلى DATABASES
# CONN_HEALTH_CHECKS = True  # تم نقلها إلى DATABASES

# زمن انتظار أطول للعمليات الكبيرة
REQUEST_TIMEOUT = 300  # 5 دقائق

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

# إعدادات انتهاء الصلاحية - محسنة للعمليات الكبيرة
CELERY_TASK_SOFT_TIME_LIMIT = 1800  # 30 دقيقة للعمليات الكبيرة
CELERY_TASK_TIME_LIMIT = 3600       # 60 دقيقة كحد أقصى
CELERY_RESULT_EXPIRES = 7200        # ساعتان

# إعدادات خاصة لقوائم مختلفة
CELERY_TASK_ROUTES = {
    'orders.tasks.upload_*': {'queue': 'file_uploads'},
    'orders.tasks.sync_*': {'queue': 'file_uploads'},
    'orders.tasks.bulk_*': {'queue': 'file_uploads'},
    'inventory.tasks.sync_*': {'queue': 'file_uploads'},
}

# زمن انتظار أطول للمهام الكبيرة
CELERY_TASK_ANNOTATIONS = {
    'orders.tasks.upload_*': {'time_limit': 3600, 'soft_time_limit': 1800},
    'orders.tasks.sync_*': {'time_limit': 3600, 'soft_time_limit': 1800},
    'inventory.tasks.sync_*': {'time_limit': 3600, 'soft_time_limit': 1800},
}

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

# ===== إعدادات خاصة للعمليات الكبيرة والمزامنة =====
# Large Operations Configuration

# إعدادات خاصة بالرفع والجسر لمنع انقطاع الاتصال
LARGE_OPERATIONS_CONFIG = {
    'MAX_UPLOAD_SIZE': 2 * 1024 * 1024 * 1024,  # 2 جيجابايت
    'UPLOAD_CHUNK_SIZE': 10 * 1024 * 1024,       # 10 ميجابايت chunks
    'CONNECTION_TIMEOUT': 900,                    # 15 دقيقة
    'READ_TIMEOUT': 1800,                        # 30 دقيقة
    'BRIDGE_KEEPALIVE': 300,                     # 5 دقائق keep-alive
}

# إعدادات خاصة بمزامنة جداول جوجل
GOOGLE_SYNC_CONFIG = {
    'BATCH_SIZE': 1000,           # عدد الصفوف في كل دفعة
    'MAX_RETRIES': 5,             # عدد المحاولات
    'RETRY_DELAY': 60,            # الانتظار بين المحاولات (ثانية)
    'TIMEOUT_PER_BATCH': 600,     # 10 دقائق لكل دفعة
    'TOTAL_TIMEOUT': 7200,        # ساعتان للعملية الكاملة
}

# إعدادات خاصة بتحديث أسعار المنتجات
PRODUCT_UPDATE_CONFIG = {
    'BATCH_SIZE': 500,            # منتجات في كل دفعة
    'PROCESSING_TIMEOUT': 1800,   # 30 دقيقة
    'DATABASE_BATCH_SIZE': 100,   # حفظ كل 100 منتج
    'MEMORY_LIMIT': 512 * 1024 * 1024,  # 512 ميجابايت
}

# تطبيق الإعدادات على Celery للعمليات الكبيرة
CELERY_TASK_ANNOTATIONS = {
    # استثناء: رفع المنتجات بالجملة - بدون قيود سرعة
    'inventory.tasks_optimized.bulk_upload_products_fast': {
        'rate_limit': None,  # بدون حد - سرعة قصوى
        'time_limit': 600,
        'soft_time_limit': 540,
    },
    'orders.tasks.upload_file_to_google_drive': {
        'rate_limit': '5/m',
        'time_limit': 1800,     # 30 دقيقة
        'soft_time_limit': 1500, # 25 دقيقة
        'retry_kwargs': {'max_retries': 5, 'countdown': 60},
    },
    'orders.tasks.sync_products_with_google': {
        'rate_limit': '1/h',     # مرة واحدة في الساعة
        'time_limit': 7200,      # ساعتان
        'soft_time_limit': 6600, # ساعة و 50 دقيقة
        'retry_kwargs': {'max_retries': 3, 'countdown': 300},
    },
    'orders.tasks.bulk_update_prices': {
        'rate_limit': '2/h',     # مرتان في الساعة
        'time_limit': 3600,      # ساعة واحدة
        'soft_time_limit': 3300, # 55 دقيقة
        'retry_kwargs': {'max_retries': 3, 'countdown': 180},
    },
}

# إعدادات خاصة بقاعدة البيانات للعمليات الكبيرة - تم توحيدها أعلاه
# تم نقل جميع إعدادات قاعدة البيانات إلى DATABASES في بداية الملف لتجنب التضارب
# DATABASES['default']['CONN_MAX_AGE'] = 0  # تم توحيدها
# DATABASES['default']['CONN_HEALTH_CHECKS'] = True  # تم توحيدها
# DATABASES['default']['OPTIONS'] تم توحيدها أعلاه

# Session timeout للعمليات الطويلة
# ملاحظة: تم توحيد إعدادات Session في قسم Security Settings أعلاه
# SESSION_COOKIE_AGE = 86400  # تم نقلها - انظر أعلاه

# إعدادات Cache للعمليات الكبيرة
CACHE_MIDDLEWARE_SECONDS = 300  # 5 دقائق
CACHE_MIDDLEWARE_KEY_PREFIX = 'elkhawaga_'

# إعدادات Logging للعمليات الكبيرة - تم دمجها في تكوين LOGGING الرئيسي أعلاه

# تطبيق الإعدادات على أساس نوع العملية
def apply_large_operation_settings():
    """تطبيق إعدادات خاصة للعمليات الكبيرة"""
    import os
    import sys
    
    # زيادة حدود Python
    sys.setrecursionlimit(5000)
    
    # إعدادات متغيرات البيئة
    os.environ['DJANGO_SETTINGS_MODULE'] = 'crm.settings'
    os.environ['CELERY_OPTIMIZATION_ENABLED'] = '1'
    
    return True

# استدعاء دالة تطبيق الإعدادات
apply_large_operation_settings()

# ======================================
# إعدادات الأمان المحسّنة للإنتاج
# ======================================

if not DEBUG:
    # 1. إجبار HTTPS
    SECURE_SSL_REDIRECT = True
    
    # 2. HTTP Strict Transport Security
    SECURE_HSTS_SECONDS = 31536000  # سنة واحدة
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # 3. Cookies آمنة
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    # ملاحظة: CSRF_COOKIE_HTTPONLY = False للسماح لـ JavaScript بقراءة التوكن
    # تم تعيينه في القسم العام أعلاه
    
    # 4. حماية من Clickjacking
    X_FRAME_OPTIONS = 'DENY'
    
    # 5. منع MIME type sniffing
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # 6. فلتر XSS في المتصفح
    SECURE_BROWSER_XSS_FILTER = True
    
    # 7. Referrer Policy
    SECURE_REFERRER_POLICY = 'same-origin'

# ======================================
# إعدادات CSRF المحسّنة
# ======================================
# ملاحظة: CSRF_USE_SESSIONS = False في القسم الرئيسي (سطر 853)
# لا نعيد تعريفه هنا لتجنب التعارض
CSRF_COOKIE_SAMESITE = 'Lax'  # Lax للسماح بالتنقل الطبيعي
SESSION_COOKIE_SAMESITE = 'Lax'  # Lax للسماح بالتنقل الطبيعي

# ======================================
# إعدادات رفع الملفات
# ======================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB

# قائمة الامتدادات المسموحة
ALLOWED_UPLOAD_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.webp',  # صور
    '.pdf',  # مستندات PDF
    '.xlsx', '.xls',  # إكسل
    '.docx', '.doc',  # وورد
]

# الحد الأقصى لحجم الصورة
MAX_IMAGE_WIDTH = 4096
MAX_IMAGE_HEIGHT = 4096

# ======================================
# نظام Logging متقدم للأمان
# ======================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} | {levelname} | {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'security',
        },
        'attack_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'attacks.log'),
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'audit.log'),
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'attacks': {
            'handlers': ['attack_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ======================================
# إعدادات أمان متقدمة إضافية
# ======================================

# تشفير البيانات الحساسة
USE_ENCRYPTION = True

# إعدادات Session أكثر أماناً
# ملاحظة: تم توحيد إعدادات Session الأساسية أعلاه
# SESSION_ENGINE, SESSION_COOKIE_AGE, SESSION_COOKIE_NAME - انظر أعلاه

# حماية من BREACH attack
SECURE_CONTENT_TYPE_NOSNIFF = True

# منع Clickjacking
X_FRAME_OPTIONS = 'DENY'

# حماية CSRF إضافية
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'  # صفحة خطأ مخصصة
CSRF_COOKIE_AGE = 31449600  # سنة
CSRF_COOKIE_NAME = 'elkhawaga_csrftoken'  # اسم مخصص

# حماية Password
PASSWORD_RESET_TIMEOUT = 900  # 15 دقيقة فقط

# Rate Limiting للAPI
REST_FRAMEWORK_RATE_LIMIT = {
    'anon': '100/hour',  # المستخدمون غير المصادقين
    'user': '1000/hour',  # المستخدمون المصادقون
}

# تسجيل محاولات تسجيل الدخول الفاشلة
AXES_ENABLED = False  # نستخدم نظامنا الخاص في middleware
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1800  # 30 دقيقة

# منع المعلومات الحساسة من الظهور في الأخطاء
ADMINS = [('Admin', 'admin@localhost')]
MANAGERS = ADMINS

# تحديد الحد الأقصى لحجم الرفع (للحماية من DoS)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000  # الحد الأقصى لحقول النموذج

# ======================================
# إعدادات الأمان المطلق - المستوى النهائي
# ======================================

# تفعيل جميع security headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REDIRECT_EXEMPT = []  # لا استثناءات

# Cookie Security مطلق
SESSION_COOKIE_DOMAIN = None  # استخدام النطاق الحالي فقط
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = '/'
CSRF_COOKIE_PATH = '/'

# منع استخدام iframe من نطاقات أخرى
X_FRAME_OPTIONS = 'DENY'

# Subresource Integrity
USE_SRI = True  # للتحقق من سلامة الملفات الخارجية

# Database Connection Security
CONN_MAX_AGE = 600  # 10 دقائق max
CONN_HEALTH_CHECKS = True  # فحص صحة الاتصال

# Password Validation مشدد
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'max_similarity': 0.5}  # أكثر صرامة
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12}  # 12 حرف على الأقل
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password Hashers (Argon2 - الأقوى)
# تثبيت المكتبة: pip install django[argon2]
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # الأقوى - يحتاج تثبيت
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # احتياطي
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',  # احتياطي
]

# Account Lockout
ACCOUNT_LOCKOUT_THRESHOLD = 5  # بعد 5 محاولات
ACCOUNT_LOCKOUT_DURATION = 1800  # حظر 30 دقيقة

# Session Security محسّن
# ملاحظة: تم توحيد جميع إعدادات Session في الأقسام أعلاه
# SESSION_EXPIRE_AT_BROWSER_CLOSE = False  - المستخدم يبقى مسجل
# SESSION_COOKIE_AGE - انظر Security Settings أعلاه

# Security Monitoring
SECURITY_MONITORING_ENABLED = True
LOG_SECURITY_EVENTS = True
ALERT_ON_ATTACK_ATTEMPTS = True

# Content Type Restrictions
ALLOWED_CONTENT_TYPES = [
    'text/html',
    'application/json',
    'application/xml',
    'text/plain',
]

# IP Blacklist/Whitelist Support
ENABLE_IP_FILTERING = False  # فعّل في الإنتاج إذا لزم الأمر
IP_BLACKLIST = []  # قائمة IP المحظورة
IP_WHITELIST = []  # قائمة IP المسموحة فقط

# Automatic Security Updates Check
AUTO_CHECK_SECURITY_UPDATES = True
SECURITY_UPDATE_CHECK_INTERVAL = 86400  # كل 24 ساعة

# Database Backup Encryption
BACKUP_ENCRYPTION_ENABLED = True
BACKUP_RETENTION_DAYS = 30

# Two-Factor Authentication
TWO_FACTOR_AUTH_ENABLED = False  # فعّل عند الحاجة
TWO_FACTOR_AUTH_REQUIRED_FOR_ADMIN = True
