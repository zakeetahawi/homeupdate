"""
تهيئة تطبيق CRM
"""

# استيراد الإشارات لإصلاح تسلسل ID
try:
    from . import signals  # noqa: F401
except ImportError:
    pass

default_app_config = 'crm.apps.CrmConfig'