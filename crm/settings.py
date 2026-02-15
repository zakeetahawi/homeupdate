"""
إعدادات مشروع الخواجة ERP
تم تنظيفها وتوحيدها في 2026-02-15
النسخة الأصلية: crm/settings_pre_cleanup.py (1847 سطر)
"""
import logging
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.utils.deprecation import MiddlewareMixin
from dotenv import load_dotenv

# ======================================
# 1. Base Configuration
# ======================================

BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل متغيرات البيئة
if os.path.exists(BASE_DIR / ".env"):
    load_dotenv(BASE_DIR / ".env")

TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# إنشاء المجلدات الضرورية
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
(BASE_DIR / "temp").mkdir(exist_ok=True)

# ======================================
# 2. Security Core
# ======================================

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if os.environ.get("DEVELOPMENT_MODE", "False").lower() == "true":
        import secrets
        SECRET_KEY = "dev-insecure-" + secrets.token_hex(32)
        print("⚠️  WARNING: Using development SECRET_KEY. Set SECRET_KEY in environment for production!")
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set in environment variables. "
            "Generate one using: python -c 'import secrets; print(secrets.token_hex(50))'"
        )

# ✅ FIX C-2: الافتراضي False للأمان — لن يعمل DEBUG في الإنتاج بدون تعيين صريح
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

if DEBUG and not os.environ.get("DEVELOPMENT_MODE"):
    import warnings
    warnings.warn(
        "⚠️  DEBUG is True without DEVELOPMENT_MODE! This may be production!",
        RuntimeWarning,
        stacklevel=2,
    )

ALLOWED_HOSTS = [
    "elkhawaga.uk",
    "www.elkhawaga.uk",
    ".elkhawaga.uk",
]

if DEBUG:
    ALLOWED_HOSTS.extend(["localhost", "127.0.0.1", "[::1]", "192.168.1.22", "0.0.0.0"])

if extra_hosts := os.environ.get("EXTRA_ALLOWED_HOSTS"):
    ALLOWED_HOSTS.extend([h.strip() for h in extra_hosts.split(",")])

if DEBUG and os.environ.get("DEVELOPMENT_MODE"):
    ALLOWED_HOSTS.extend(["*.ngrok.io", "*.trycloudflare.com"])
    print(f"🔧 Development mode: ALLOWED_HOSTS = {ALLOWED_HOSTS}")

ADMINS = [("Admin", "admin@localhost")]
MANAGERS = ADMINS

# Suppress non-critical system checks
SILENCED_SYSTEM_CHECKS = ["urls.W002", "models.W042", "security.W019"]

# ======================================
# 3. Installed Apps
# ======================================

INSTALLED_APPS = [
    # ASGI/Channels
    "daphne",
    "channels",
    # Admin interface
    "admin_interface",
    "colorfield",
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Security
    "axes",
    # Project apps
    "core",
    "crm.apps.CrmConfig",
    "accounts",
    "user_activity.apps.UserActivityConfig",
    "customers",
    "inspections",
    "inventory",
    "orders",
    "manufacturing",
    "cutting.apps.CuttingConfig",
    "reports",
    "installations",
    "complaints.apps.ComplaintsConfig",
    "notifications.apps.NotificationsConfig",
    "accounting.apps.AccountingConfig",
    "factory_accounting.apps.FactoryAccountingConfig",
    "installation_accounting.apps.InstallationAccountingConfig",
    "odoo_db_manager.apps.OdooDbManagerConfig",
    "backup_system.apps.BackupSystemConfig",
    "public",
    "whatsapp",
    # Third-party
    "corsheaders",
    "django_apscheduler",
    "dbbackup",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "widget_tweaks",
    "board_dashboard.apps.BoardDashboardConfig",
]

# ======================================
# 4. Authentication
# ======================================

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "accounts.backends.CustomModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Password Validation — مرة واحدة فقط (12 حرف، صارم)
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"max_similarity": 0.5},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Password Hashers — Argon2 (الافضل) + PBKDF2 (للتوافق)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
PASSWORD_RESET_TIMEOUT = 900  # 15 دقيقة

# ======================================
# 5. Middleware
# ======================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "accounts.middleware.current_user.CurrentUserMiddleware",
    "user_activity.middleware.UserSessionTrackingMiddleware",
    "core.audit.AuditLoggingMiddleware",
]

# ✅ FIX C-4: تعطيل CSRF لـ API فقط في وضع التطوير الصريح (ليس مجرد DEBUG)
if DEBUG and os.environ.get("DEVELOPMENT_MODE", "").lower() == "true":

    class DisableCSRFForDevAPI:
        """تعطيل CSRF لمسارات API في وضع التطوير فقط"""
        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            if request.path.startswith("/api/"):
                setattr(request, "_dont_enforce_csrf_checks", True)
            return self.get_response(request)

    MIDDLEWARE.insert(0, "crm.settings.DisableCSRFForDevAPI")

# ======================================
# 6. URL & Template Configuration
# ======================================

ROOT_URLCONF = "crm.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.departments",
                "accounts.context_processors.company_info",
                "accounts.context_processors.footer_settings",
                "accounts.context_processors.system_settings",
                "accounts.context_processors.branch_messages",
                # ✅ FIX H-6: حذف notifications_context المكرر من accounts
                # accounts.context_processors.notifications_context ← محذوف (مكرر)
                # accounts.context_processors.admin_notifications_context ← محذوف (كود ميت)
                "accounts.navbar_context.navbar_departments",
                "notifications.context_processors.notifications_context",
                "crm.context_processors.admin_stats",
                "crm.context_processors.jazzmin_extras",
                "inventory.context_processors.pending_transfers",
                "cutting.context_processors.cutting_notifications",
            ],
        },
    },
]

ASGI_APPLICATION = "crm.asgi.application"

# ======================================
# 7. Database
# ======================================

# ✅ FIX C-1: كلمة المرور من متغير البيئة
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "crm_system"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 300,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "client_encoding": "UTF8",
            "sslmode": "prefer",
            "connect_timeout": 10,
            "options": " ".join([
                "-c statement_timeout=30000",
                "-c idle_in_transaction_session_timeout=60000",
                "-c lock_timeout=10000",
            ]),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ======================================
# 8. Cache (Redis)
# ======================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50, "retry_on_timeout": True},
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,
        },
        "TIMEOUT": 300,
        "KEY_PREFIX": "crm_",
        "VERSION": 1,
    },
    "session": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 20, "retry_on_timeout": True},
            "IGNORE_EXCEPTIONS": True,
        },
        "TIMEOUT": 3600,
        "KEY_PREFIX": "homeupdate_session",
    },
    "query": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/3",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 30, "retry_on_timeout": True},
            "IGNORE_EXCEPTIONS": True,
        },
        "TIMEOUT": 600,
        "KEY_PREFIX": "homeupdate_query",
    },
}

CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = "elkhawaga_"

# ======================================
# 9. Channels (WebSocket)
# ======================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    },
}

# ======================================
# 10. Internationalization
# ======================================

LANGUAGE_CODE = "ar"
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("ar", "العربية"),
    ("en", "English"),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]

# ======================================
# 11. Static & Media Files
# ======================================

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_VERSION = "20260215-01"
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ======================================
# 12. File Upload
# ======================================

# ✅ FIX: قيمة واحدة فقط — 10MB للأمان (العمليات الكبيرة عبر Celery)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
FILE_UPLOAD_TEMP_DIR = os.path.join(BASE_DIR, "temp")

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
]

ALLOWED_UPLOAD_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".pdf", ".xlsx", ".xls", ".docx", ".doc",
]

MAX_IMAGE_WIDTH = 4096
MAX_IMAGE_HEIGHT = 4096

# Django 5.2+
FORMS_URLFIELD_ASSUME_HTTPS = True

# ======================================
# 13. Security Settings (Unified — NO DUPLICATES)
# ======================================

# -- الإعدادات المشتركة (كلتا البيئتين) --
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_HTTPONLY = True

# CSRF — مرة واحدة
CSRF_COOKIE_HTTPONLY = False  # يجب أن يكون False للسماح لـ JavaScript بالوصول
CSRF_COOKIE_NAME = "elkhawaga_csrftoken"
CSRF_COOKIE_AGE = 31449600  # سنة
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_PATH = "/"
CSRF_USE_SESSIONS = False
CSRF_FAILURE_VIEW = "crm.csrf_views.csrf_failure"

# Session — مرة واحدة
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"  # ✅ FIX M-6: Redis أولاً، DB احتياط
SESSION_CACHE_ALIAS = "session"
SESSION_COOKIE_NAME = "elkhawaga_sessionid"
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_AGE = 3600  # ساعة واحدة
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# -- الإعدادات حسب البيئة --
if not DEBUG:
    # Production
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "same-origin"
    SECURE_CROSS_ORIGIN_OPENER_POLICY = (
        "same-origin" if os.environ.get("ENABLE_SSL_SECURITY", "false").lower() == "true" else None
    )
    SECURE_REDIRECT_EXEMPT = []

    CSRF_TRUSTED_ORIGINS = [
        "https://elkhawaga.uk",
        "https://www.elkhawaga.uk",
        "https://crm.elkhawaga.uk",
        "https://api.elkhawaga.uk",
        "https://admin.elkhawaga.uk",
    ]

    # Content Security Policy
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
    CSP_BLOCK_ALL_MIXED_CONTENT = True

else:
    # Development
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0  # ✅ FIX: لا HSTS في التطوير
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    X_FRAME_OPTIONS = "SAMEORIGIN"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None
    CSP_REPORT_ONLY = True  # في التطوير: تقارير فقط بدون حظر

    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost",
        "http://127.0.0.1",
        "http://192.168.1.22:8000",
    ]

# ======================================
# 14. CORS
# ======================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.22:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://elkhawaga.uk",
    "https://www.elkhawaga.uk",
    "https://crm.elkhawaga.uk",
    "https://api.elkhawaga.uk",
    "https://admin.elkhawaga.uk",
]

CORS_ORIGIN_WHITELIST = CORS_ALLOWED_ORIGINS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["*"]
CORS_ALLOW_HEADERS = [
    "Authorization", "Content-Type", "X-CSRFToken",
    "accept", "accept-encoding", "content-type",
    "dnt", "origin", "user-agent", "x-requested-with", "x-request-id",
]

# إضافة CORS origins لـ CSRF (في الإنتاج فقط HTTPS)
if not DEBUG:
    CSRF_TRUSTED_ORIGINS += [o for o in CORS_ALLOWED_ORIGINS if o.startswith("https://")]

# ======================================
# 15. REST Framework & JWT
# ======================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["crm.auth.CustomJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",
        "user": "200/hour",
    },
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_SAMESITE": "Lax",
    "AUTH_COOKIE_SECURE": not DEBUG,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Rate Limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "default"

# ======================================
# 16. Email
# ======================================

EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

# ======================================
# 17. Celery
# ======================================

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Cairo"
CELERY_ENABLE_UTC = True
CELERY_TASK_COMPRESSION = "gzip"
CELERY_RESULT_COMPRESSION = "gzip"
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXPIRES = 7200

# Time limits
if DEBUG:
    CELERY_TASK_SOFT_TIME_LIMIT = 1800  # 30 دقيقة تطوير
    CELERY_TASK_TIME_LIMIT = 3600
    CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000
else:
    CELERY_TASK_SOFT_TIME_LIMIT = 180  # 3 دقائق إنتاج
    CELERY_TASK_TIME_LIMIT = 300
    CELERY_WORKER_MAX_MEMORY_PER_CHILD = 150000

# Task routing
CELERY_TASK_ROUTES = {
    "orders.tasks.upload_*": {"queue": "file_uploads"},
    "orders.tasks.sync_*": {"queue": "file_uploads"},
    "orders.tasks.bulk_*": {"queue": "file_uploads"},
    "inventory.tasks.sync_*": {"queue": "file_uploads"},
}

# Task annotations — مرة واحدة فقط
CELERY_TASK_ANNOTATIONS = {
    "inventory.tasks_optimized.bulk_upload_products_fast": {
        "rate_limit": None,
        "time_limit": 600,
        "soft_time_limit": 540,
    },
    "orders.tasks.upload_file_to_google_drive": {
        "rate_limit": "5/m",
        "time_limit": 1800,
        "soft_time_limit": 1500,
        "retry_kwargs": {"max_retries": 5, "countdown": 60},
    },
    "orders.tasks.sync_products_with_google": {
        "rate_limit": "1/h",
        "time_limit": 7200,
        "soft_time_limit": 6600,
        "retry_kwargs": {"max_retries": 3, "countdown": 300},
    },
    "orders.tasks.bulk_update_prices": {
        "rate_limit": "2/h",
        "time_limit": 3600,
        "soft_time_limit": 3300,
        "retry_kwargs": {"max_retries": 3, "countdown": 180},
    },
}

# Monitoring
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_LOG_COLOR = False

# Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "check-complaint-deadlines": {
        "task": "complaints.tasks.check_complaint_deadlines_task",
        "schedule": crontab(minute=0),
        "options": {"queue": "default"},
    },
    "daily-complaints-report": {
        "task": "complaints.tasks.daily_complaints_report_task",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "default"},
    },
    "auto-delay-complaints": {
        "task": "complaints.tasks.auto_create_delay_complaints",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": "default"},
    },
}

# ======================================
# 18. Django Axes (Brute Force Protection)
# ======================================

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # ساعة واحدة
AXES_LOCKOUT_PARAMETERS = ["username"]  # حظر بالاسم فقط (Cloudflare Tunnel يمنع حظر IP)
AXES_CLIENT_IP_CALLABLE = "user_activity.utils.get_client_ip_from_request"
AXES_LOCKOUT_TEMPLATE = "axes/lockout.html"
AXES_VERBOSE = True
AXES_ENABLED = True
AXES_LOCK_OUT_AT_FAILURE = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_RESET_ON_SUCCESS = True
AXES_FAILURE_HANDLER = "axes.handlers.database.AxesDatabaseHandler"

# ======================================
# 19. Backup
# ======================================

BACKUP_ROOT = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUP_ROOT, exist_ok=True)

DBBACKUP_TMP_DIR = BACKUP_ROOT
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {"location": BACKUP_ROOT}
DBBACKUP_CLEANUP_KEEP = 10

BACKUP_COMPRESSION = {
    "ENABLED": True,
    "COMPRESSION_LEVEL": 9,
    "FILE_EXTENSION": ".gz",
    "AUTO_COMPRESS_ON_CREATE": True,
    "AUTO_COMPRESS_ON_DOWNLOAD": True,
    "CHUNK_SIZE": 1024 * 1024,
}
BACKUP_SUPPORTED_FORMATS = ["json", "sqlite3", "sql", "csv", "txt"]
BACKUP_ENCRYPTION_ENABLED = True
BACKUP_RETENTION_DAYS = 30

# ======================================
# 20. APScheduler
# ======================================

APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25

SCHEDULER_CONFIG = {
    "apscheduler.jobstores.default": {"class": "django_apscheduler.jobstores:DjangoJobStore"},
    "apscheduler.executors.processpool": {"type": "threadpool", "max_workers": 5},
    "apscheduler.job_defaults.coalesce": "false",
    "apscheduler.job_defaults.max_instances": "3",
    "apscheduler.timezone": TIME_ZONE,
}

SESSION_CLEANUP_SCHEDULE = {
    "days": 1, "fix_users": True, "frequency": "daily", "hour": 3, "minute": 0,
}

# ======================================
# 21. Activity Tracking
# ======================================

ACTIVITY_TRACKING = {
    "ENABLED": True,
    "LOG_ANONYMOUS_USERS": False,
    "LOG_STATIC_FILES": False,
    "LOG_MEDIA_FILES": False,
    "CLEANUP_DAYS": 30,
    "ONLINE_TIMEOUT_MINUTES": 5,
    "AUTO_CLEANUP_ENABLED": True,
    "MAX_ACTIVITY_LOGS_PER_USER": 1000,
}

# ======================================
# 22. Performance & Application Config
# ======================================

PERFORMANCE_SETTINGS = {
    "QUERY_TIMEOUT": 30,
    "CACHE_TIMEOUT": 300,
    "PAGINATION_SIZE": 20,
    "MAX_UPLOAD_SIZE": 10 * 1024 * 1024,
    "COMPRESSION_ENABLED": True,
    "LAZY_LOADING_ENABLED": True,
    "VIRTUAL_SCROLLING_ENABLED": True,
    "QUERY_DEBUG_ENABLED": DEBUG,
    "SLOW_QUERY_THRESHOLD": 0.1,
}

SECURITY_SETTINGS = {
    "PASSWORD_MIN_LENGTH": 12,
    "PASSWORD_COMPLEXITY": True,
    "PASSWORD_EXPIRY_DAYS": 90,
    "SESSION_TIMEOUT": 30,
    "MAX_LOGIN_ATTEMPTS": 5,
    "LOCKOUT_DURATION": 30,
    "TWO_FACTOR_ENABLED": False,
    "AUDIT_LOGGING_ENABLED": True,
}

# Large Operations Config
LARGE_OPERATIONS_CONFIG = {
    "MAX_UPLOAD_SIZE": 2 * 1024 * 1024 * 1024,
    "UPLOAD_CHUNK_SIZE": 10 * 1024 * 1024,
    "CONNECTION_TIMEOUT": 900,
    "READ_TIMEOUT": 1800,
    "BRIDGE_KEEPALIVE": 300,
}

GOOGLE_SYNC_CONFIG = {
    "BATCH_SIZE": 1000, "MAX_RETRIES": 5, "RETRY_DELAY": 60,
    "TIMEOUT_PER_BATCH": 600, "TOTAL_TIMEOUT": 7200,
}

PRODUCT_UPDATE_CONFIG = {
    "BATCH_SIZE": 500, "PROCESSING_TIMEOUT": 1800,
    "DATABASE_BATCH_SIZE": 100, "MEMORY_LIMIT": 512 * 1024 * 1024,
}

REQUEST_TIMEOUT = 300

# ======================================
# 23. External Services
# ======================================

SITE_URL = os.environ.get("SITE_URL", "https://www.elkhawaga.uk")

CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL", "https://qr.elkhawaga.uk")
CLOUDFLARE_SYNC_API_KEY = os.environ.get("CLOUDFLARE_SYNC_API_KEY", "")
CLOUDFLARE_SYNC_ENABLED = os.environ.get("CLOUDFLARE_SYNC_ENABLED", "False").lower() in ("true", "1", "yes")
CLOUDFLARE_KV_NAMESPACE_ID = os.environ.get("CLOUDFLARE_KV_NAMESPACE_ID", "5dad2f4d72b246758bdafa17dfe4eb10")

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "elkhawaga-whatsapp-webhook-2026")

# Security flags
USE_ENCRYPTION = True
USE_SRI = True
SECURITY_MONITORING_ENABLED = True
LOG_SECURITY_EVENTS = True
ALERT_ON_ATTACK_ATTEMPTS = True
ENABLE_IP_FILTERING = False
IP_BLACKLIST = []
IP_WHITELIST = []
AUTO_CHECK_SECURITY_UPDATES = True
SECURITY_UPDATE_CHECK_INTERVAL = 86400
TWO_FACTOR_AUTH_ENABLED = False
TWO_FACTOR_AUTH_REQUIRED_FOR_ADMIN = True
ALLOWED_CONTENT_TYPES = ["text/html", "application/json", "application/xml", "text/plain"]
ACCOUNT_LOCKOUT_THRESHOLD = 5
ACCOUNT_LOCKOUT_DURATION = 1800

# ======================================
# 24. Company & Admin
# ======================================

COMPANY_NAME = "شركة الخواجة للألمنيوم والزجاج"
ADMIN_URL = "admin/"
ADMIN_SITE_HEADER = "نظام إدارة الخواجة"
ADMIN_SITE_TITLE = "لوحة الإدارة"
ADMIN_INDEX_TITLE = "مرحباً بك في نظام إدارة الخواجة"

# ======================================
# 25. Admin Interface (Jazzmin)
# ======================================

JAZZMIN_SETTINGS = {
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
    "usermenu_links": [
        {"name": "إعدادات الشركة", "url": "/accounts/company_info/", "icon": "fas fa-building"},
        {"model": "auth.user"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [
        "accounts", "customers", "orders", "installations",
        "factory_accounting", "installation_accounting",
        "inventory", "reports", "complaints", "backup_system", "odoo_db_manager",
    ],
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
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": "admin/css/sidebar_left.css",
    "custom_js": "admin/js/custom_admin.js",
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "theme": "flatly",
    "dark_mode_theme": "darkly",
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs",
    },
    "language_chooser": False,
    "custom_links": {
        "customers": [{"name": "إضافة عميل جديد", "url": "admin:customers_customer_add", "icon": "fas fa-plus", "permissions": ["customers.add_customer"]}],
        "orders": [{"name": "إنشاء طلب جديد", "url": "admin:orders_order_add", "icon": "fas fa-plus", "permissions": ["orders.add_order"]}],
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False, "footer_small_text": False, "body_small_text": False,
    "brand_small_text": False, "brand_colour": "navbar-primary", "accent": "accent-primary",
    "navbar": "navbar-primary navbar-dark", "no_navbar_border": False,
    "navbar_fixed": False, "layout_boxed": False, "footer_fixed": False,
    "sidebar_fixed": False, "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False, "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False, "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False, "sidebar_nav_flat_style": False,
    "theme": "flatly", "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary", "secondary": "btn-secondary", "info": "btn-info",
        "warning": "btn-warning", "danger": "btn-danger", "success": "btn-success",
    },
    "actions_sticky_top": False,
}

# ======================================
# 26. Logging (Unified — NO DUPLICATES)
# ======================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} - {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[{asctime}] {levelname} - {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "security": {
            "format": "[SECURITY] {asctime} | {levelname} | {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "django_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "django.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "errors.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "security_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "security.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "security",
            "encoding": "utf-8",
        },
        "performance_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "performance.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "audit_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "audit.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "slow_queries_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "slow_queries.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "attack_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "attacks.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "null": {"class": "logging.NullHandler"},
    },
    "loggers": {
        "django": {"handlers": ["console", "django_file"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["error_file", "console"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["security_file"], "level": "WARNING", "propagate": False},
        "django.db.backends": {"handlers": ["slow_queries_file"], "level": "WARNING", "propagate": False},
        "performance": {"handlers": ["performance_file", "console"], "level": "INFO", "propagate": False},
        "security": {"handlers": ["security_file", "console"], "level": "INFO", "propagate": False},
        "attacks": {"handlers": ["attack_file", "console"], "level": "WARNING", "propagate": False},
        "audit": {"handlers": ["audit_file"], "level": "INFO", "propagate": False},
        "crm": {"handlers": ["console", "django_file"], "level": "INFO", "propagate": False},
        "accounts": {"handlers": ["console", "django_file", "security_file"], "level": "INFO", "propagate": False},
        "orders": {"handlers": ["console", "django_file"], "level": "INFO", "propagate": False},
        "customers": {"handlers": ["console", "django_file"], "level": "INFO", "propagate": False},
        "api": {"handlers": ["django_file", "console"], "level": "INFO", "propagate": False},
        # Suppress noisy loggers
        "accounts.middleware": {"handlers": ["null"], "level": "ERROR", "propagate": False},
        "accounts.signals": {"handlers": ["null"], "level": "ERROR", "propagate": False},
        "user_activity": {"handlers": ["null"], "level": "ERROR", "propagate": False},
        "daphne.http_protocol": {"handlers": ["null"], "level": "ERROR", "propagate": False},
        "daphne.ws_protocol": {"handlers": ["null"], "level": "ERROR", "propagate": False},
        "websocket_blocker": {"handlers": ["slow_queries_file"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console", "django_file"], "level": "INFO"},
}

# Reduce Django logging in production
if not DEBUG:
    logging.getLogger("django.request").setLevel(logging.ERROR)
    logging.getLogger("django.db.backends").setLevel(logging.ERROR)

# ======================================
# 27. Slow Query Monitoring Middleware (unused but kept for reference)
# ======================================

class QueryPerformanceLoggingMiddleware(MiddlewareMixin):
    """Middleware لتسجيل الاستعلامات البطيئة — غير مُضاف للـ MIDDLEWARE افتراضياً"""
    def process_view(self, request, view_func, view_args, view_kwargs):
        request._start_time = time.time()
        from django.db import connection, reset_queries
        if not DEBUG:
            connection.force_debug_cursor = True
        reset_queries()
        request._queries_before = len(connection.queries)

    def process_response(self, request, response):
        total_time = (time.time() - getattr(request, "_start_time", time.time())) * 1000
        from django.db import connection
        queries_count = len(connection.queries) - getattr(request, "_queries_before", 0)
        if total_time > 1000:
            perf_logger = logging.getLogger("performance")
            perf_logger.warning(
                f"SLOW_PAGE: {request.path} | {int(total_time)}ms | {queries_count} queries | user={getattr(request, 'user', None)}"
            )
        if hasattr(connection, "queries") and connection.queries:
            sq_logger = logging.getLogger("websocket_blocker")
            for query in connection.queries[getattr(request, "_queries_before", 0):]:
                if "time" in query and float(query["time"]) > 0.1:
                    sq_logger.warning(f"SLOW_QUERY: {query['time']}s | {query['sql'][:200]}...")
        if not DEBUG:
            connection.force_debug_cursor = False
        return response

# ======================================
# 28. Runtime Setup
# ======================================

sys.setrecursionlimit(5000)
