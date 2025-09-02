"""
تكوين WSGI للمشروع.
"""

import os
import sys
import atexit
import logging
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise
from .resource_tracker import cleanup_resources

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# تسجيل دالة تنظيف الموارد لتشغيلها عند إيقاف التطبيق
atexit.register(cleanup_resources)

# تهيئة تطبيق WSGI
application = get_wsgi_application()

# تم نقل تنفيذ الترحيلات التلقائية إلى ملف manage.py

# إضافة دعم WhiteNoise للملفات الثابتة
application = WhiteNoise(application)
