
# ============================================
# 🚀 إعدادات التسريع 1000x
# أضف هذه الإعدادات في نهاية settings.py
# ============================================

# 1. تحسين الجلسات - استخدام Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'

# 2. تحسين Cache للصفحات
CACHE_MIDDLEWARE_SECONDS = 300  # 5 دقائق
CACHE_MIDDLEWARE_KEY_PREFIX = 'homeupdate_page'

# 3. تحسين Templates
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# 4. تعطيل عدّ النتائج في Admin
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# 5. تحسين الملفات الثابتة
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 6. إعدادات الضغط
WHITENOISE_MAX_AGE = 31536000  # سنة
WHITENOISE_AUTOREFRESH = DEBUG

# 7. تحسين قاعدة البيانات
if not DEBUG:
    CONN_MAX_AGE = 600  # 10 دقائق

# 8. تقليل Logging في Production
if not DEBUG:
    LOGGING['handlers']['console']['level'] = 'WARNING'
