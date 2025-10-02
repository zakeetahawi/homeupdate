"""
إشارات ما بعد الهجرة لتطبيق الحسابات
"""

from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_core_departments_after_migrate(sender, **kwargs):
    """
    إنشاء الأقسام الأساسية بعد كل عملية هجرة
    """
    # تشغيل الدالة فقط بعد هجرة تطبيق الحسابات
    if sender.name == "accounts":
        from accounts.core_departments import create_core_departments

        create_core_departments()
