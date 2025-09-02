#!/usr/bin/env python
"""
أداة شاملة لإصلاح تسلسل ID في جميع الجداول
تستخدم هذه الأداة لحل مشاكل تضارب ID خاصة بعد استعادة النسخ الاحتياطية
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.apps import apps
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إصلاح تسلسل ID لجميع الجداول في قاعدة البيانات PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='إصلاح تسلسل ID لتطبيق محدد فقط'
        )
        parser.add_argument(
            '--table',
            type=str,
            help='إصلاح تسلسل ID لجدول محدد فقط'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم تنفيذه دون تطبيق التغييرات'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل أكثر'
        )

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.dry_run = options.get('dry_run', False)
        self.verbose = options.get('verbose', False)
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 وضع المعاينة - لن يتم تطبيق أي تغييرات')
            )
        
        try:
            if options.get('table'):
                self.fix_single_table(options['table'])
            elif options.get('app'):
                self.fix_app_sequences(options['app'])
            else:
                self.fix_all_sequences()
                
        except Exception as e:
            logger.error(f"خطأ في إصلاح التسلسل: {str(e)}")
            raise CommandError(f"فشل في إصلاح التسلسل: {str(e)}")

    def fix_all_sequences(self):
        """إصلاح تسلسل ID لجميع الجداول"""
        self.stdout.write(
            self.style.SUCCESS('🔧 بدء إصلاح تسلسل ID لجميع الجداول...')
        )
        
        # الحصول على جميع التطبيقات المحلية
        local_apps = [
            'accounts', 'customers', 'factory', 'inspections',
            'installations', 'inventory', 'orders', 'reports',
            'odoo_db_manager'
        ]
        
        total_fixed = 0
        total_checked = 0
        
        for app_name in local_apps:
            try:
                app_config = apps.get_app_config(app_name)
                fixed, checked = self.fix_app_sequences(app_name, show_header=False)
                total_fixed += fixed
                total_checked += checked
            except LookupError:
                if self.verbose:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  التطبيق {app_name} غير موجود')
                    )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ تم الانتهاء! فحص {total_checked} جدول، إصلاح {total_fixed} تسلسل'
            )
        )

    def fix_app_sequences(self, app_name, show_header=True):
        """إصلاح تسلسل ID لتطبيق محدد"""
        if show_header:
            self.stdout.write(
                self.style.SUCCESS(f'🔧 إصلاح تسلسل ID للتطبيق: {app_name}')
            )
        
        try:
            app_config = apps.get_app_config(app_name)
        except LookupError:
            raise CommandError(f'التطبيق {app_name} غير موجود')
        
        models = app_config.get_models()
        fixed_count = 0
        checked_count = 0
        
        for model in models:
            table_name = model._meta.db_table
            try:
                if self.fix_table_sequence(table_name, model):
                    fixed_count += 1
                checked_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ خطأ في جدول {table_name}: {str(e)}')
                )
        
        if show_header:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ تم فحص {checked_count} جدول، إصلاح {fixed_count} تسلسل'
                )
            )
        
        return fixed_count, checked_count

    def fix_single_table(self, table_name):
        """إصلاح تسلسل ID لجدول محدد"""
        self.stdout.write(
            self.style.SUCCESS(f'🔧 إصلاح تسلسل ID للجدول: {table_name}')
        )
        
        try:
            if self.fix_table_sequence(table_name):
                self.stdout.write(
                    self.style.SUCCESS(f'✅ تم إصلاح تسلسل الجدول {table_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'ℹ️  الجدول {table_name} لا يحتاج إصلاح')
                )
        except Exception as e:
            raise CommandError(f'فشل في إصلاح جدول {table_name}: {str(e)}')

    def fix_table_sequence(self, table_name, model=None):
        """إصلاح تسلسل ID لجدول محدد"""
        with connection.cursor() as cursor:
            try:
                # التحقق من وجود الجدول
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, [table_name])
                
                if not cursor.fetchone()[0]:
                    if self.verbose:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  الجدول {table_name} غير موجود')
                        )
                    return False
                
                # البحث عن عمود ID التلقائي (IDENTITY أو SERIAL)
                cursor.execute("""
                    SELECT column_name, column_default, is_identity
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND (column_default LIKE 'nextval%%' OR is_identity = 'YES')
                """, [table_name])
                
                auto_columns = cursor.fetchall()

                if not auto_columns:
                    if self.verbose:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  لا يوجد عمود ID تلقائي في {table_name}')
                        )
                    return False

                sequence_fixed = False

                for column_name, column_default, is_identity in auto_columns:
                    if is_identity == 'YES':
                        # IDENTITY column - استخدام اسم التسلسل المتوقع
                        sequence_name = f"{table_name}_{column_name}_seq"
                    else:
                        # SERIAL column - استخراج اسم التسلسل من column_default
                        sequence_name = self.extract_sequence_name(column_default)

                    if sequence_name:
                        if self.fix_sequence(table_name, column_name, sequence_name):
                            sequence_fixed = True

                return sequence_fixed
                
            except Exception as e:
                logger.error(f"خطأ في إصلاح جدول {table_name}: {str(e)}")
                raise

    def extract_sequence_name(self, column_default):
        """استخراج اسم التسلسل من column_default"""
        import re
        # البحث عن نمط nextval('sequence_name'::regclass)
        match = re.search(r"nextval\('([^']+)'", column_default)
        if match:
            return match.group(1)
        return None

    def fix_sequence(self, table_name, column_name, sequence_name):
        """إصلاح تسلسل محدد"""
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
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  التسلسل {sequence_name} غير موجود')
                        )
                    return False

                # الحصول على أعلى ID موجود في الجدول
                cursor.execute(f'SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}')
                max_id = cursor.fetchone()[0]

                # الحصول على القيمة الحالية للتسلسل
                cursor.execute(f"SELECT last_value FROM {sequence_name}")
                seq_result = cursor.fetchone()
                current_seq = seq_result[0] if seq_result else 0
                
                # تحديد القيمة التالية المطلوبة
                next_value = max_id + 1
                
                if current_seq < next_value:
                    if not self.dry_run:
                        # إعادة تعيين التسلسل
                        cursor.execute(
                            f"SELECT setval('{sequence_name}', %s, false)",
                            [next_value]
                        )
                    
                    if self.verbose or self.dry_run:
                        action = "سيتم إصلاح" if self.dry_run else "تم إصلاح"
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'🔧 {action} {table_name}.{column_name}: '
                                f'{current_seq} → {next_value}'
                            )
                        )
                    
                    return True
                else:
                    if self.verbose:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ {table_name}.{column_name}: التسلسل صحيح ({current_seq})'
                            )
                        )
                    return False
                    
            except Exception as e:
                logger.error(f"خطأ في إصلاح تسلسل {sequence_name}: {str(e)}")
                raise

    def get_all_sequences_info(self):
        """الحصول على معلومات جميع التسلسلات"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    sequencename,
                    last_value,
                    start_value,
                    increment_by,
                    max_value,
                    min_value,
                    cache_value,
                    is_cycled
                FROM pg_sequences
                WHERE schemaname = 'public'
                ORDER BY sequencename
            """)
            
            return cursor.fetchall()
