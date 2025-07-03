"""
إشارات النظام لإصلاح تسلسل ID تلقائياً
"""

import threading
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.core.management import call_command
from django.conf import settings
import logging
import os
from datetime import datetime, timedelta
from django.apps import apps

# Thread-safe initialization tracking
_sequence_monitor_initialized = False
_sequence_monitor_lock = threading.Lock()

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def auto_fix_sequences_after_migrate(sender, **kwargs):
    """
    إصلاح تسلسل ID تلقائياً بعد تطبيق الترحيلات
    يتم تشغيله بعد كل عملية migrate
    """
    try:
        # تجنب التشغيل أثناء الاختبارات
        if hasattr(settings, 'TESTING') and settings.TESTING:
            return
            
        # Skip if this is not the main database
        if kwargs.get('using') != 'default':
            return

        logger.info("فحص تسلسل ID بعد الترحيل...")
        
        # استخدام الفحص التلقائي
        call_command('auto_fix_sequences', '--check-only', verbosity=0)
        
    except Exception as e:
        logger.error(f"خطأ في إصلاح التسلسل بعد الترحيل: {str(e)}", exc_info=True)


def detect_backup_restore():
    """اكتشاف عملية استعادة نسخة احتياطية حديثة"""
    try:
        # فحص ملفات النسخ الاحتياطي الحديثة
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            return False

        # البحث عن ملفات تم إنشاؤها في آخر ساعة
        current_time = datetime.now()
        recent_threshold = timedelta(hours=1)

        for filename in os.listdir(backup_dir):
            if filename.endswith(('.json', '.sql')):
                file_path = os.path.join(backup_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                if current_time - file_time < recent_threshold:
                    return True

        return False

    except Exception as e:
        logger.error(
            f"خطأ في اكتشاف استعادة النسخة الاحتياطية: {str(e)}",
            exc_info=True
        )
        return False


def schedule_sequence_check():
    """جدولة فحص دوري لتسلسل ID"""
    # Check if already scheduled
    if hasattr(schedule_sequence_check, '_scheduled'):
        return
        
    try:
        # يمكن دمج هذا مع django-apscheduler إذا كان متاحاً
        if 'django_apscheduler' in settings.INSTALLED_APPS:
            from django_apscheduler.jobstores import DjangoJobStore
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.jobstores.base import ConflictingIdError
            from apscheduler.executors.pool import ThreadPoolExecutor
            
            # Use a single scheduler instance
            if not hasattr(schedule_sequence_check, '_scheduler'):
                schedule_sequence_check._scheduler = BackgroundScheduler(
                    jobstores={'default': DjangoJobStore()},
                    executors={'default': ThreadPoolExecutor(1)},
                    job_defaults={
                        'coalesce': True,
                        'max_instances': 1,
                        'misfire_grace_time': 60 * 60  # 1 hour
                    }
                )
                
            scheduler = schedule_sequence_check._scheduler

            # جدولة فحص يومي
            try:
                if not scheduler.running:
                    scheduler.add_job(
                        run_sequence_check,
                        'cron',
                        hour=3,  # 3 صباحاً
                        minute=0,
                        id='daily_sequence_check',
                        replace_existing=True
                    )
                    scheduler.start()
                    logger.info("تم جدولة فحص تسلسل ID اليومي")
                else:
                    logger.debug("المجدول يعمل بالفعل")
                    
            except ConflictingIdError:
                logger.debug("مهمة الفحص الدوري موجودة مسبقاً")
                if not scheduler.running:
                    scheduler.start()
                return

    except Exception as e:
        logger.error(
            f"خطأ في جدولة فحص التسلسل: {str(e)}",
            exc_info=True
        )


def run_sequence_check():
    """
    تشغيل فحص تسلسل ID
    """
    if hasattr(run_sequence_check, '_running'):
        logger.debug("الفحص الدوري يعمل حالياً")
        return
        
    run_sequence_check._running = True
    try:
        logger.info("بدء الفحص الدوري لتسلسل ID...")
        call_command('auto_fix_sequences', '--check-only', verbosity=0)
        logger.info("انتهى الفحص الدوري لتسلسل ID")
    except Exception as e:
        logger.error(
            f"خطأ في فحص التسلسل: {str(e)}",
            exc_info=True
        )
    finally:
        run_sequence_check._running = False


class SequenceMonitor:
    """مراقب تسلسل ID"""

    @classmethod
    def check_and_fix_if_needed(cls):
        """فحص وإصلاح التسلسل إذا لزم الأمر"""
        try:
            log_file = os.path.join(settings.BASE_DIR, 'media', 'sequence_monitor.log')
            timestamp = datetime.now().isoformat()
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}: فحص حالة التسلسل\n")
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل حالة التسلسل: {str(e)}")


# تشغيل المراقب عند بدء التطبيق
def initialize_sequence_monitor():
    """
    تهيئة مراقب التسلسل
    يتم استدعاؤها بعد اكتمال تحميل التطبيقات
    """
    global _sequence_monitor_initialized
    
    # Prevent multiple initializations with thread safety
    with _sequence_monitor_lock:
        if _sequence_monitor_initialized:
            logger.debug("مراقب التسلسل مهيأ مسبقاً")
            return True
            
        # Mark as initialized early to prevent re-entry
        _sequence_monitor_initialized = True
        
    try:
        # التحقق من اكتمال تحميل التطبيقات
        if not apps.ready:
            logger.debug(
                "تأجيل تهيئة مراقب التسلسل - التطبيقات غير جاهزة بعد"
            )
            return False

        logger.debug("بدء تهيئة مراقب تسلسل ID...")

        # فحص أولي مع معالجة الأخطاء
        try:
            SequenceMonitor.check_and_fix_if_needed()
        except Exception as e:
            logger.error(
                f"خطأ في الفحص الأولي للتسلسل: {str(e)}",
                exc_info=True
            )

        # جدولة الفحص الدوري
        try:
            schedule_sequence_check()
        except Exception as e:
            logger.error(
                f"خطأ في جدولة الفحص الدوري: {str(e)}",
                exc_info=True
            )

        logger.info("تم تهيئة مراقب تسلسل ID بنجاح")
        _sequence_monitor_initialized = True
        return True

    except Exception as e:
        logger.error(
            f"خطأ في تهيئة مراقب التسلسل: {str(e)}",
            exc_info=True
        )
        return False


@receiver(post_migrate)
def delayed_sequence_monitor_init(sender, **kwargs):
    """
    تأجيل تهيئة مراقب التسلسل حتى يكتمل تحميل التطبيقات
    """
    try:
        if not initialize_sequence_monitor():
            # إعادة المحاولة بعد ثانية إذا فشلت المحاولة الأولى
            from threading import Timer
            Timer(1.0, initialize_sequence_monitor).start()
    except Exception as e:
        logger.error(
            f"خطأ في تشغيل مراقب التسلسل: {str(e)}",
            exc_info=True
        )
