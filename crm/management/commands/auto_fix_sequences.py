#!/usr/bin/env python
"""
أداة إصلاح تلقائي لتسلسل ID بعد استعادة النسخ الاحتياطية
تستخدم لإصلاح تسلسل ID تلقائياً عند اكتشاف مشاكل
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إصلاح تلقائي لتسلسل ID بعد استعادة النسخ الاحتياطية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='فحص فقط دون إصلاح'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='إجبار الإصلاح حتى لو لم تُكتشف مشاكل'
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='ملف تسجيل العمليات'
        )

    def handle(self, *args, **options):
        self.check_only = options.get('check_only', False)
        self.force = options.get('force', False)
        self.log_file = options.get('log_file')
        
        if self.log_file:
            self.setup_logging()
        
        self.stdout.write(
            self.style.SUCCESS('🔍 بدء الفحص التلقائي لتسلسل ID...')
        )
        
        try:
            # فحص حالة التسلسل
            problems_detected = self.detect_sequence_problems()
            
            if problems_detected or self.force:
                if self.check_only:
                    self.stdout.write(
                        self.style.WARNING('⚠️  تم اكتشاف مشاكل - استخدم --force للإصلاح')
                    )
                else:
                    self.auto_fix_sequences()
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ جميع التسلسلات تعمل بشكل صحيح')
                )
                
        except Exception as e:
            logger.error(f"خطأ في الإصلاح التلقائي: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'❌ فشل في الإصلاح التلقائي: {str(e)}')
            )

    def setup_logging(self):
        """إعداد تسجيل العمليات"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='a'
        )

    def detect_sequence_problems(self):
        """اكتشاف مشاكل في تسلسل ID"""
        problems_found = False
        
        with connection.cursor() as cursor:
            try:
                # الحصول على جميع الجداول التي تحتوي على تسلسل
                cursor.execute("""
                    SELECT 
                        t.table_name,
                        c.column_name,
                        c.column_default
                    FROM information_schema.tables t
                    JOIN information_schema.columns c ON t.table_name = c.table_name
                    WHERE t.table_schema = 'public'
                    AND c.column_default LIKE 'nextval%%'
                    ORDER BY t.table_name
                """)
                
                tables_with_sequences = cursor.fetchall()
                
                for table_name, column_name, column_default in tables_with_sequences:
                    sequence_name = self.extract_sequence_name(column_default)
                    
                    if sequence_name:
                        if self.check_sequence_problem(table_name, column_name, sequence_name):
                            problems_found = True
                            self.stdout.write(
                                self.style.WARNING(
                                    f'⚠️  مشكلة في {table_name}.{column_name}'
                                )
                            )
                
                return problems_found
                
            except Exception as e:
                logger.error(f"خطأ في اكتشاف المشاكل: {str(e)}")
                raise

    def extract_sequence_name(self, column_default):
        """استخراج اسم التسلسل من column_default"""
        import re
        match = re.search(r"nextval\('([^']+)'", column_default)
        if match:
            return match.group(1)
        return None

    def check_sequence_problem(self, table_name, column_name, sequence_name):
        """فحص وجود مشكلة في تسلسل محدد"""
        with connection.cursor() as cursor:
            try:
                # الحصول على أعلى ID موجود
                cursor.execute(f'SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}')
                max_id = cursor.fetchone()[0]
                
                # الحصول على القيمة الحالية للتسلسل
                cursor.execute(f"SELECT last_value FROM {sequence_name}")
                current_seq = cursor.fetchone()[0]
                
                # إذا كان التسلسل أقل من أو يساوي أعلى ID، فهناك مشكلة
                return current_seq <= max_id
                
            except Exception as e:
                logger.error(f"خطأ في فحص {sequence_name}: {str(e)}")
                return False

    def auto_fix_sequences(self):
        """إصلاح تلقائي لجميع التسلسلات"""
        self.stdout.write(
            self.style.SUCCESS('🔧 بدء الإصلاح التلقائي...')
        )
        
        try:
            # استخدام أداة الإصلاح الشاملة
            call_command('fix_all_sequences', verbosity=1)
            
            # تسجيل العملية
            self.log_fix_operation()
            
            self.stdout.write(
                self.style.SUCCESS('✅ تم الإصلاح التلقائي بنجاح')
            )
            
        except Exception as e:
            logger.error(f"خطأ في الإصلاح التلقائي: {str(e)}")
            raise

    def log_fix_operation(self):
        """تسجيل عملية الإصلاح"""
        timestamp = datetime.now().isoformat()
        log_message = f"تم إصلاح تسلسل ID تلقائياً في {timestamp}"
        
        logger.info(log_message)
        
        # حفظ في ملف منفصل للعمليات التلقائية
        auto_fix_log = os.path.join(settings.BASE_DIR, 'media', 'auto_fix_sequences.log')
        
        try:
            with open(auto_fix_log, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp}: {log_message}\n")
        except Exception as e:
            logger.warning(f"فشل في كتابة ملف السجل: {str(e)}")

    def is_backup_restore_detected(self):
        """اكتشاف ما إذا كانت هناك عملية استعادة نسخة احتياطية حديثة"""
        # يمكن تحسين هذه الطريقة بناءً على آلية النسخ الاحتياطي المستخدمة
        
        # فحص ملفات النسخ الاحتياطي الحديثة
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            return False
        
        import time
        current_time = time.time()
        recent_threshold = 3600  # ساعة واحدة
        
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json') or filename.endswith('.sql'):
                file_path = os.path.join(backup_dir, filename)
                file_time = os.path.getmtime(file_path)
                
                if current_time - file_time < recent_threshold:
                    return True
        
        return False

    def schedule_auto_check(self):
        """جدولة فحص تلقائي دوري"""
        # يمكن دمج هذا مع django-apscheduler
        pass
