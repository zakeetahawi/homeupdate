#!/usr/bin/env python
"""
أمر Django لإصلاح تسلسل ID تلقائياً
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """تكوين أمر إصلاح تسلسل ID"""
    help = 'فحص وإصلاح تسلسل ID تلقائياً'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='فحص فقط دون إصلاح'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل أكثر'
        )

    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        check_only = options.get('check_only', False)
        
        try:
            problems_found = self.detect_sequence_problems()
            
            if problems_found:
                if check_only:
                    self.stdout.write(
                        self.style.ERROR('تم اكتشاف مشاكل في التسلسل')
                    )
                else:
                    self.fix_sequences()
                    self.stdout.write(
                        self.style.SUCCESS('تم إصلاح التسلسل بنجاح')
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS('لا توجد مشاكل في التسلسل')
                )
                
        except Exception as e:
            raise CommandError(f'خطأ في تنفيذ الأمر: {str(e)}')

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
                        c.column_default,
                        c.is_identity
                    FROM information_schema.tables t
                    JOIN information_schema.columns c 
                        ON t.table_name = c.table_name
                    WHERE t.table_schema = 'public'
                    AND (
                        c.column_default LIKE 'nextval%%' 
                        OR c.is_identity = 'YES'
                    )
                    ORDER BY t.table_name
                """)
                
                tables_with_sequences = cursor.fetchall()
                
                for row in tables_with_sequences:
                    table_name, column_name = row[0], row[1]
                    column_default, is_identity = row[2], row[3]
                    
                    if is_identity == 'YES':
                        seq_name = f"{table_name}_{column_name}_seq"
                    else:
                        seq_name = self.extract_sequence_name(
                            column_default
                        )
                    
                    if seq_name:
                        has_problem = self.check_sequence_problem(
                            table_name, 
                            column_name, 
                            seq_name
                        )
                        if has_problem:
                            problems_found = True
                            if self.verbose:
                                msg = f'⚠️  مشكلة في {table_name}.{column_name}'
                                self.stdout.write(
                                    self.style.ERROR(msg)
                                )
                
                return problems_found
                
            except Exception as e:
                logger.error(f"خطأ في اكتشاف المشاكل: {str(e)}")
                raise

    def extract_sequence_name(self, column_default):
        """استخراج اسم التسلسل من column_default"""
        if not column_default:
            return None
            
        import re
        match = re.search(r"nextval\('([^']+)'", column_default)
        if match:
            return match.group(1)
        return None

    def check_sequence_problem(self, table_name, column_name, sequence_name):
        """فحص وجود مشكلة في تسلسل محدد"""
        with connection.cursor() as cursor:
            try:
                # التحقق من وجود التسلسل
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM pg_sequences
                        WHERE sequencename = %s
                    )
                """, [sequence_name])

                if not cursor.fetchone()[0]:
                    if self.verbose:
                        msg = f'⚠️  التسلسل {sequence_name} غير موجود'
                        self.stdout.write(self.style.ERROR(msg))
                    return True

                # الحصول على أعلى ID موجود
                sql = (
                    f'SELECT COALESCE(MAX({column_name}), 0) '
                    f'FROM {table_name}'
                )
                cursor.execute(sql)
                max_id = cursor.fetchone()[0]
                
                # الحصول على القيمة الحالية للتسلسل
                sql = f"SELECT last_value FROM {sequence_name}"
                cursor.execute(sql)
                current_seq = cursor.fetchone()[0]
                
                # إذا كان التسلسل أقل من أو يساوي أعلى ID، فهناك مشكلة
                has_problem = current_seq <= max_id
                if has_problem and self.verbose:
                    msg = (
                        f'⚠️  التسلسل {sequence_name} ({current_seq}) '
                        f'أقل من أعلى ID ({max_id})'
                    )
                    self.stdout.write(self.style.ERROR(msg))
                return has_problem
                
            except Exception as e:
                logger.error(f"خطأ في فحص {sequence_name}: {str(e)}")
                return False

    def fix_sequences(self):
        """إصلاح جميع التسلسلات"""
        with connection.cursor() as cursor:
            try:
                # الحصول على جميع الجداول التي تحتوي على تسلسل
                cursor.execute("""
                    SELECT 
                        t.table_name,
                        c.column_name,
                        c.column_default,
                        c.is_identity
                    FROM information_schema.tables t
                    JOIN information_schema.columns c 
                        ON t.table_name = c.table_name
                    WHERE t.table_schema = 'public'
                    AND (
                        c.column_default LIKE 'nextval%%' 
                        OR c.is_identity = 'YES'
                    )
                    ORDER BY t.table_name
                """)
                
                tables_with_sequences = cursor.fetchall()
                
                for row in tables_with_sequences:
                    table_name, column_name = row[0], row[1]
                    column_default, is_identity = row[2], row[3]
                    
                    if is_identity == 'YES':
                        seq_name = f"{table_name}_{column_name}_seq"
                    else:
                        seq_name = self.extract_sequence_name(
                            column_default
                        )
                    
                    if seq_name:
                        # الحصول على أعلى ID موجود
                        sql = (
                            f'SELECT COALESCE(MAX({column_name}), 0) '
                            f'FROM {table_name}'
                        )
                        cursor.execute(sql)
                        max_id = cursor.fetchone()[0]
                        
                        # إعادة تعيين التسلسل
                        if max_id is not None:
                            new_value = max_id + 1
                            sql = (
                                f"ALTER SEQUENCE {seq_name} "
                                f"RESTART WITH {new_value}"
                            )
                            cursor.execute(sql)
                            
                            if self.verbose:
                                msg = (
                                    f'✅ تم إصلاح {table_name}.{column_name} '
                                    f'(تم التعيين إلى {new_value})'
                                )
                                self.stdout.write(
                                    self.style.SUCCESS(msg)
                                )
                
            except Exception as e:
                logger.error(f"خطأ في إصلاح التسلسلات: {str(e)}")
                raise
