"""
إشارات النظام لإصلاح تسلسل ID تلقائياً
"""

import sys
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.conf import settings
from django.core.management import call_command
import logging


logger = logging.getLogger(__name__)


def run_sequence_check():
    """تشغيل فحص وإصلاح التسلسل"""
    try:
        if not settings.TESTING and 'test' not in sys.argv:
            call_command('auto_fix_sequences', verbosity=0)
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تنفيذ الترحيلات التلقائية: {str(e)}")


@receiver(post_migrate)
def auto_fix_sequences_after_migrate(sender, **kwargs):
    """
    إصلاح تسلسل ID تلقائياً بعد تطبيق الترحيلات
    """
    try:
        if settings.TESTING or kwargs.get('using') != 'default':
            return

        logger.info("فحص تسلسل ID بعد الترحيل...")
        from django.db import transaction
        transaction.on_commit(run_sequence_check)
        
    except Exception as e:
        logger.error(f"خطأ في إصلاح التسلسل بعد الترحيل: {str(e)}")