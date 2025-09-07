INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_apscheduler',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'channels',  # دعم WebSocket
    # الأقسام الأساسية
    'accounts',  # Accounts
    'customers',  # إدارة العملاء
    'orders',  # الطلبات
    'inspections',  # المعاينات
    'manufacturing',  # Manufacturing
    'installations',  # قسم التركيبات
    'odoo_db_manager',  # إدارة قواعد البيانات
    'inventory',  # إدارة المخزون
    'reports',  # التقارير
    'backup_system',  # نظام النسخ الاحتياطي والاستعادة الجديد
    'notifications',  # نظام الإشعارات
    'user_activity',  # نظام تتبع نشاط المستخدمين
    'modern_chat',  # نظام الدردشة الحديث
    'cutting',  # نظام التقطيع
    'complaints',  # نظام الشكاوى


]

import os
import dj_database_url

# وضع التطوير
DEBUG = True
ALLOWED_HOSTS = ['*']  # السماح للوصول من جميع الأجهزة

# إعدادات Django الأساسية
ROOT_URLCONF = 'crm.urls'
WSGI_APPLICATION = 'crm.wsgi.application'

# إعدادات الوقت والمنطقة
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_TZ = True

# إعدادات الملفات الثابتة
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'staticfiles')

# إعدادات الوسائط
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media')

# إعدادات الأمان
SECRET_KEY = 'django-insecure-your-secret-key-here-change-in-production'

# إعدادات الجلسات والأمان
SESSION_COOKIE_AGE = 86400  # 24 ساعة
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_SECURE = False  # True في الإنتاج
SESSION_COOKIE_SECURE = False  # True في الإنتاج

# إعدادات قاعدة البيانات الافتراضية
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# إعدادات Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# إعدادات القوالب
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# إعدادات المصادقة
AUTH_USER_MODEL = 'accounts.User'

# إعدادات قاعدة البيانات
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://postgres:5525@localhost:5432/crm_system')

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL)
}

# إعدادات Channels و WebSocket
ASGI_APPLICATION = 'homeupdate.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# إعدادات التخزين المؤقت
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
