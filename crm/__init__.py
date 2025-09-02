"""
تهيئة تطبيق CRM
"""

# تحميل Celery عند بدء Django
from .celery import app as celery_app

__all__ = ('celery_app',)

# استيراد الإشارات لإصلاح تسلسل ID
try:
    from . import signals  # noqa: F401
except ImportError:
    pass

default_app_config = 'crm.apps.CrmConfig'