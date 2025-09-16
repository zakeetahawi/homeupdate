"""
خدمة النسخ الاحتياطي المجدولة (محسنة ومصححة)
"""

import os
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

from odoo_db_manager.models import Database, BackupSchedule

logger = logging.getLogger(__name__)

# متغير عام للمجدول لتجنب مشاكل التسلسل
_scheduler = None

def get_scheduler():
    """الحصول على المجدول أو إنشاؤه"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.add_jobstore(DjangoJobStore(), "default")
    return _scheduler

def create_backup_job(schedule_id):
    """دالة منفصلة لإنشاء النسخ الاحتياطية (لتجنب مشاكل التسلسل)"""
    try:
        from odoo_db_manager.services.backup_service import BackupService

        # الحصول على جدولة النسخة الاحتياطية
        schedule = BackupSchedule.objects.get(id=schedule_id)

        # التحقق من أن الجدولة نشطة
        if not schedule.is_active:
            logger.info(f"تم تخطي النسخة الاحتياطية {schedule.name} (ID: {schedule.id}) لأنها غير نشطة")
            return

        logger.info(f"بدء إنشاء النسخة الاحتياطية المجدولة {schedule.name} (ID: {schedule.id})")

        # إنشاء خدمة النسخ الاحتياطي
        backup_service = BackupService()

        # إنشاء النسخة الاحتياطية (دائماً نسخة كاملة للجدولة)
        backup = backup_service.create_backup(
            database_id=schedule.database.id,
            name=f"{schedule.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            user=schedule.created_by,
            backup_type='full'  # دائماً نسخة كاملة للجدولة
        )

        # تحديث النسخة الاحتياطية لتكون مجدولة
        if backup:
            backup.is_scheduled = True
            backup.save()

        # تحديث وقت آخر تشغيل
        schedule.last_run = timezone.now()

        # حساب موعد التشغيل القادم
        schedule.calculate_next_run()

        # حذف النسخ الاحتياطية القديمة إذا تجاوزت الحد الأقصى
        cleanup_old_backups(schedule)

        logger.info(f"تم إنشاء النسخة الاحتياطية المجدولة {schedule.name} (ID: {schedule.id}) بنجاح")

        return backup
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إنشاء النسخة الاحتياطية المجدولة: {str(e)}")
        return None

def cleanup_old_backups(schedule):
    """دالة منفصلة لحذف النسخ الاحتياطية القديمة"""
    try:
        # الحصول على النسخ الاحتياطية المرتبطة بهذه الجدولة
        backups = Backup.objects.filter(
            database=schedule.database,
            backup_type=schedule.backup_type,
            is_scheduled=True
        ).order_by('-created_at')

        # التحقق من عدد النسخ الاحتياطية
        if backups.count() > schedule.max_backups:
            # الحصول على النسخ الاحتياطية التي سيتم حذفها
            to_delete = backups[schedule.max_backups:]

            logger.info(f"حذف {to_delete.count()} نسخة احتياطية قديمة لجدولة {schedule.name} (ID: {schedule.id})")

            # حذف النسخ الاحتياطية
            for backup in to_delete:
                # حذف ملف النسخة الاحتياطية
                if os.path.exists(backup.file_path):
                    os.unlink(backup.file_path)

                # حذف سجل النسخة الاحتياطية
                backup.delete()

            logger.info(f"تم حذف {to_delete.count()} نسخة احتياطية قديمة بنجاح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء حذف النسخ الاحتياطية القديمة: {str(e)}")

class ScheduledBackupService:
    """خدمة النسخ الاحتياطي المجدولة (محسنة)"""

    def __init__(self):
        """تهيئة الخدمة"""
        # لا نحفظ المجدول كمتغير في الكلاس لتجنب مشاكل التسلسل
        pass

    def start(self):
        """بدء تشغيل المجدول"""
        scheduler = get_scheduler()
        if scheduler.running:
            logger.info("المجدول يعمل بالفعل")
            return

        logger.info("بدء تشغيل مجدول النسخ الاحتياطي")

        # إضافة المهام المجدولة
        self._schedule_all_backups()

        # بدء تشغيل المجدول
        scheduler.start()
        logger.info("تم بدء تشغيل مجدول النسخ الاحتياطي")

    def stop(self):
        """إيقاف تشغيل المجدول"""
        scheduler = get_scheduler()
        if scheduler.running:
            logger.info("إيقاف تشغيل مجدول النسخ الاحتياطي")
            scheduler.shutdown()
            global _scheduler
            _scheduler = None
            logger.info("تم إيقاف تشغيل مجدول النسخ الاحتياطي")

    def _schedule_all_backups(self):
        """جدولة جميع النسخ الاحتياطية النشطة"""
        try:
            scheduler = get_scheduler()
            # حذف جميع المهام السابقة
            scheduler.remove_all_jobs()

            # الحصول على جميع جدولات النسخ الاحتياطية النشطة
            schedules = BackupSchedule.objects.filter(is_active=True)
            logger.info(f"جدولة {schedules.count()} نسخة احتياطية")
        except Exception as e:
            # إذا كانت الجداول غير موجودة، تخطي الجدولة
            logger.info(f"تخطي جدولة النسخ الاحتياطية: {str(e)}")
            return

        for schedule in schedules:
            self._schedule_backup(schedule)

    def _schedule_backup(self, schedule):
        """جدولة نسخة احتياطية واحدة"""
        scheduler = get_scheduler()
        if not scheduler:
            logger.error("المجدول غير متاح")
            return

        # حساب موعد التشغيل القادم إذا لم يكن محدداً
        if not schedule.next_run:
            schedule.calculate_next_run()

        # إنشاء معرف المهمة
        job_id = f"backup_{schedule.id}"

        # تحديد معاملات التكرار
        trigger_args = {}

        if schedule.frequency == 'hourly':
            trigger = 'interval'
            trigger_args['hours'] = 1
        elif schedule.frequency == 'daily':
            trigger = 'cron'
            trigger_args['hour'] = schedule.hour
            trigger_args['minute'] = schedule.minute
        elif schedule.frequency == 'weekly':
            trigger = 'cron'
            trigger_args['day_of_week'] = schedule.day_of_week
            trigger_args['hour'] = schedule.hour
            trigger_args['minute'] = schedule.minute
        elif schedule.frequency == 'monthly':
            trigger = 'cron'
            trigger_args['day'] = schedule.day_of_month
            trigger_args['hour'] = schedule.hour
            trigger_args['minute'] = schedule.minute
        else:
            logger.error(f"تكرار غير معروف: {schedule.frequency}")
            return

        # إضافة المهمة إلى المجدول
        scheduler.add_job(
            create_backup_job,  # استخدام دالة منفصلة
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            kwargs={
                'schedule_id': schedule.id
            },
            **trigger_args
        )

        logger.info(f"تمت جدولة النسخة الاحتياطية {schedule.name} (ID: {schedule.id}) بتكرار {schedule.get_frequency_display()}")

    def remove_job(self, job_id):
        """حذف مهمة من المجدول"""
        try:
            scheduler = get_scheduler()
            if scheduler:
                scheduler.remove_job(job_id)
                logger.info(f"تم حذف المهمة: {job_id}")
                return True
        except Exception as e:
            logger.error(f"فشل حذف المهمة {job_id}: {str(e)}")
        return False

    def run_job_now(self, schedule_id):
        """تشغيل مهمة النسخ الاحتياطي فوراً"""
        try:
            return create_backup_job(schedule_id)
        except Exception as e:
            logger.error(f"فشل تشغيل المهمة {schedule_id}: {str(e)}")
            return None

    @property
    def scheduler(self):
        """خاصية للتوافق مع الكود القديم - ترجع المجدول أو None"""
        try:
            return get_scheduler()
        except:
            return None

    # تم نقل دوال إنشاء النسخ الاحتياطية إلى دوال منفصلة لتجنب مشاكل التسلسل

# إنشاء نسخة واحدة من الخدمة
scheduled_backup_service = ScheduledBackupService()
