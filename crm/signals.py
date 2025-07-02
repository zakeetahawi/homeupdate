"""
إشارات النظام لإصلاح تسلسل ID تلقائياً
"""

from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.core.management import call_command
from django.conf import settings
import logging
import os
from datetime import datetime, timedelta

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
        
        # فحص ما إذا كانت هناك حاجة لإصلاح التسلسل
        from django.core.management import call_command
        
        logger.info("فحص تسلسل ID بعد الترحيل...")
        
        # استخدام الفحص التلقائي
        call_command('auto_fix_sequences', '--check-only', verbosity=0)
        
    except Exception as e:
        logger.error(f"خطأ في إصلاح التسلسل بعد الترحيل: {str(e)}")


def detect_backup_restore():
    """
    اكتشاف عملية استعادة نسخة احتياطية حديثة
    """
    try:
        # فحص ملفات النسخ الاحتياطي الحديثة
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            return False
        
        # البحث عن ملفات تم إنشاؤها في آخر ساعة
        current_time = datetime.now()
        recent_threshold = timedelta(hours=1)
        
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json') or filename.endswith('.sql'):
                file_path = os.path.join(backup_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if current_time - file_time < recent_threshold:
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"خطأ في اكتشاف استعادة النسخة الاحتياطية: {str(e)}")
        return False


def schedule_sequence_check():
    """
    جدولة فحص دوري لتسلسل ID
    """
    try:
        # يمكن دمج هذا مع django-apscheduler إذا كان متاحاً
        if 'django_apscheduler' in settings.INSTALLED_APPS:
            from django_apscheduler.jobstores import DjangoJobStore
            from apscheduler.schedulers.background import BackgroundScheduler
            
            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), "default")
            
            # جدولة فحص يومي
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
            
    except Exception as e:
        logger.error(f"خطأ في جدولة فحص التسلسل: {str(e)}")


def run_sequence_check():
    """
    تشغيل فحص تسلسل ID
    """
    try:
        logger.info("بدء الفحص الدوري لتسلسل ID...")
        call_command('auto_fix_sequences', verbosity=0)
        logger.info("انتهى الفحص الدوري لتسلسل ID")
        
    except Exception as e:
        logger.error(f"خطأ في الفحص الدوري: {str(e)}")


class SequenceMonitor:
    """
    مراقب تسلسل ID
    """
    
    @staticmethod
    def check_and_fix_if_needed():
        """
        فحص وإصلاح التسلسل إذا لزم الأمر
        """
        try:
            # فحص سريع للمشاكل الحرجة
            from django.db import connection
            
            with connection.cursor() as cursor:
                # فحص عينة من الجداول المهمة
                critical_tables = [
                    'customers_customer',
                    'orders_order',
                    'accounts_user',
                    'inspections_inspection'
                ]
                
                problems_found = False
                
                for table_name in critical_tables:
                    try:
                        # فحص وجود الجدول
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = %s
                            )
                        """, [table_name])
                        
                        if not cursor.fetchone()[0]:
                            continue
                        
                        # فحص التسلسل
                        cursor.execute(f"""
                            SELECT
                                COALESCE(MAX(id), 0) as max_id
                            FROM {table_name}
                        """)
                        max_id_result = cursor.fetchone()
                        max_id = max_id_result[0] if max_id_result else 0

                        # الحصول على قيمة التسلسل
                        cursor.execute(f"""
                            SELECT last_value
                            FROM pg_sequences
                            WHERE sequencename = '{table_name}_id_seq'
                        """)

                        seq_result = cursor.fetchone()
                        seq_value = seq_result[0] if seq_result else 0

                        if max_id >= seq_value:
                            problems_found = True
                            logger.warning(f"مشكلة في تسلسل {table_name}: max_id={max_id}, seq={seq_value}")
                            break
                    
                    except Exception as e:
                        logger.error(f"خطأ في فحص {table_name}: {str(e)}")
                        continue
                
                if problems_found:
                    logger.info("تم اكتشاف مشاكل في التسلسل - بدء الإصلاح...")
                    call_command('fix_all_sequences', verbosity=0)
                    logger.info("تم إصلاح مشاكل التسلسل")
                
        except Exception as e:
            logger.error(f"خطأ في مراقب التسلسل: {str(e)}")
    
    @staticmethod
    def log_sequence_status():
        """
        تسجيل حالة التسلسل
        """
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
    """
    try:
        # فحص أولي
        SequenceMonitor.check_and_fix_if_needed()
        
        # جدولة الفحص الدوري
        schedule_sequence_check()
        
        logger.info("تم تهيئة مراقب تسلسل ID")
        
    except Exception as e:
        logger.error(f"خطأ في تهيئة مراقب التسلسل: {str(e)}")


# تشغيل التهيئة عند استيراد الملف
try:
    initialize_sequence_monitor()
except Exception as e:
    logger.error(f"خطأ في تشغيل مراقب التسلسل: {str(e)}")
