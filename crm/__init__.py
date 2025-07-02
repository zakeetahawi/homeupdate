"""
تهيئة تطبيق CRM
"""

# استيراد الإشارات لإصلاح تسلسل ID
try:
    from . import signals  # noqa: F401
except ImportError:
    pass