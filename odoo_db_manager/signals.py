"""
إشارات تطبيق إدارة قواعد البيانات على طراز أودو
"""

import os
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.apps import apps

from .models import Database
from .services.database_service import DatabaseService

logger = logging.getLogger(__name__)

# تم نقل مزامنة قواعد البيانات إلى ملف apps.py

# تم حذف معالج Backup لأنه تم نقله إلى backup_system

@receiver(post_save, sender=Database)
def handle_database_save(sender, instance, created, **kwargs):
    """معالجة حفظ قاعدة البيانات"""
    if created:
        logger.info(f"تم إنشاء قاعدة بيانات جديدة: {instance.name}")
    else:
        logger.info(f"تم تحديث قاعدة البيانات: {instance.name}")

        # إذا تم تنشيط قاعدة البيانات، قم بإلغاء تنشيط جميع قواعد البيانات الأخرى
        if instance.is_active:
            # تحديث ملف الإعدادات
            from .services.database_service import DatabaseService
            database_service = DatabaseService()
            database_service._update_settings_file(instance)

            logger.info(f"تم تنشيط قاعدة البيانات: {instance.name}")

@receiver(post_delete, sender=Database)
def handle_database_delete(sender, instance, **kwargs):
    """معالجة حذف قاعدة البيانات"""
    logger.info(f"تم حذف قاعدة البيانات: {instance.name}")

    # إذا كانت قاعدة البيانات نشطة، قم بتنشيط قاعدة بيانات أخرى
    if instance.is_active:
        # البحث عن قاعدة بيانات أخرى
        other_db = Database.objects.exclude(id=instance.id).first()
        if other_db:
            other_db.is_active = True
            other_db.save()

            logger.info(f"تم تنشيط قاعدة البيانات البديلة: {other_db.name}")
        else:
            # إذا لم تكن هناك قواعد بيانات أخرى، قم بإنشاء ملف إعدادات فارغ
            from .services.database_service import DatabaseService
            database_service = DatabaseService()
            database_service._update_settings_file(None)

            logger.info("تم إنشاء ملف إعدادات فارغ")
