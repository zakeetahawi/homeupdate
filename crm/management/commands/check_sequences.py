#!/usr/bin/env python
"""
أداة فحص تسلسل ID في جميع الجداول
تستخدم لتحديد المشاكل المحتملة في تسلسل ID قبل حدوث تضارب
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
import logging
import os

# Set up logging
logger = logging.getLogger('sequence_checker')
logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Create file handler which logs debug messages
log_file = os.path.join(log_dir, 'sequence_checker.log')
fh = logging.FileHandler(log_file, encoding='utf-8')
fh.setLevel(logging.DEBUG)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


class Command(BaseCommand):
    help = 'فحص حالة تسلسل ID في جميع الجداول وتحديد المشاكل المحتملة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='فحص تطبيق محدد فقط'
        )
        parser.add_argument(
            '--table',
            type=str,
            help='فحص جدول محدد فقط'
        )
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='عرض جميع الجداول حتى التي لا تحتوي على مشاكل'
        )
        parser.add_argument(
            '--export',
            type=str,
            help='تصدير النتائج إلى ملف JSON'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إصلاح التسلسل تلقائياً'
        )

    def handle(self, *args, **options):
        """Handle the command"""
        self.verbosity = options.get('verbosity', 1)
        self.fix = options.get('fix', False)
        specific_table = options.get('table')
        self.show_all = options.get('show_all', False)
        self.export_file = options.get('export')
        
        # Set up logging based on verbosity
        if self.verbosity >= 2:
            logger.setLevel(logging.DEBUG)
        elif self.verbosity >= 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)
    
        # Check if we're running in a test environment
        import sys
        if 'test' in sys.argv:
            logger.info("Running in test environment, skipping sequence check")
            return
            
        # Check if database is ready
        try:
            from django.db import connections
            conn = connections['default']
            conn.ensure_connection()
        except Exception as e:
            logger.warning(f"Database not ready yet, skipping sequence check: {str(e)}")
            return

        self.stdout.write(
            self.style.SUCCESS('🔍 بدء فحص تسلسل ID...')
        )

        if options.get('table'):
            results = self.check_single_table(options['table'])
        elif options.get('app'):
            results = self.check_app_sequences(options['app'])
        else:
            results = self.check_all_sequences()

        # عرض الملخص
        self.display_summary(results)

        # تصدير النتائج إذا طُلب ذلك
        if self.export_file:
            self.export_results(results, self.export_file)

    def check_all_sequences(self):
        """فحص تسلسل ID لجميع الجداول"""
        local_apps = [
            'accounts', 'customers', 'factory', 'inspections',
            'installations', 'inventory', 'orders', 'reports',
            'odoo_db_manager'
        ]
        
        all_results = {
            'problems': [],
            'healthy': [],
            'no_sequence': [],
            'errors': []
        }
        
        for app_name in local_apps:
            try:
                app_config = apps.get_app_config(app_name)
                app_results = self.check_app_sequences(app_name, show_header=False)
                
                # دمج النتائج
                for key in all_results:
                    all_results[key].extend(app_results[key])
                    
            except LookupError:
                continue
        
        return all_results

    def check_app_sequences(self, app_name, show_header=True):
        """فحص تسلسل ID لتطبيق محدد"""
        if show_header:
            self.stdout.write(
                self.style.SUCCESS(f'🔍 فحص التطبيق: {app_name}')
            )
        
        try:
            app_config = apps.get_app_config(app_name)
        except LookupError:
            self.stdout.write(
                self.style.ERROR(f'❌ التطبيق {app_name} غير موجود')
            )
            return {'problems': [], 'healthy': [], 'no_sequence': [], 'errors': []}
        
        models = app_config.get_models()
        results = {
            'problems': [],
            'healthy': [],
            'no_sequence': [],
            'errors': []
        }
        
        for model in models:
            table_name = model._meta.db_table
            try:
                result = self.check_table_sequence(table_name, model)
                if result:
                    results[result['status']].append(result)
            except Exception as e:
                error_result = {
                    'table': table_name,
                    'status': 'errors',
                    'error': str(e)
                }
                results['errors'].append(error_result)
                self.stdout.write(
                    self.style.ERROR(f'❌ خطأ في فحص {table_name}: {str(e)}')
                )
        
        if show_header:
            self.display_app_summary(app_name, results)
        
        return results

    def check_single_table(self, table_name):
        """فحص تسلسل ID لجدول محدد"""
        self.stdout.write(
            self.style.SUCCESS(f'🔍 فحص الجدول: {table_name}')
        )
        
        results = {
            'problems': [],
            'healthy': [],
            'no_sequence': [],
            'errors': []
        }
        
        try:
            result = self.check_table_sequence(table_name)
            if result:
                results[result['status']].append(result)
                self.display_table_result(result)
        except Exception as e:
            error_result = {
                'table': table_name,
                'status': 'errors',
                'error': str(e)
            }
            results['errors'].append(error_result)
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في فحص {table_name}: {str(e)}')
            )
        
        return results

    def check_table_sequence(self, table_name, model=None):
        """فحص تسلسل ID لجدول محدد"""
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
                    return None
                
                # البحث عن أعمدة ID التلقائية (IDENTITY أو SERIAL)
                cursor.execute("""
                    SELECT column_name, column_default, is_identity
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND (column_default LIKE 'nextval%%' OR is_identity = 'YES')
                """, [table_name])
                
                auto_columns = cursor.fetchall()
                
                if not auto_columns:
                    return {
                        'table': table_name,
                        'status': 'no_sequence',
                        'message': 'لا يوجد عمود ID تلقائي'
                    }
                
                # فحص كل عمود ID تلقائي
                for column_name, column_default, is_identity in auto_columns:
                    if is_identity == 'YES':
                        # IDENTITY column - استخدام اسم التسلسل المتوقع
                        sequence_name = f"{table_name}_{column_name}_seq"
                    else:
                        # SERIAL column - استخراج اسم التسلسل من column_default
                        sequence_name = self.extract_sequence_name(column_default)

                    if sequence_name:
                        return self.check_sequence_health(
                            table_name, column_name, sequence_name
                        )
                
                return {
                    'table': table_name,
                    'status': 'no_sequence',
                    'message': 'لم يتم العثور على تسلسل صالح'
                }
                
            except Exception as e:
                logger.error(f"خطأ في فحص جدول {table_name}: {str(e)}")
                raise

    def extract_sequence_name(self, column_default):
        """استخراج اسم التسلسل من column_default"""
        import re
        match = re.search(r"nextval\('([^']+)'", column_default)
        if match:
            return match.group(1)
        return None

    def check_sequence_health(self, table_name, column_name, sequence_name):
        """Check health of a single sequence with improved error handling"""
        logger.debug(f"Checking sequence health for table={table_name}, column={column_name}, sequence={sequence_name}")
        
        try:
            # Ensure database connection is ready
            connection.ensure_connection()

            with connection.cursor() as cursor:
                # First try to get the sequence directly
                cursor.execute(
                    """
                    SELECT sequencename, last_value
                    FROM pg_sequences 
                    WHERE schemaname = 'public' 
                    AND sequencename = %s
                    """,
                    [sequence_name]
                )
                seq_row = cursor.fetchone()
                
                # If sequence not found, try to find it by table and column name
                if not seq_row:
                    cursor.execute(
                        """
                        SELECT sequencename, last_value
                        FROM pg_sequences 
                        WHERE schemaname = 'public' 
                        AND sequencename LIKE %s
                        """,
                        [f'%{table_name}%']
                    )
                    seq_row = cursor.fetchone()
                    if seq_row:
                        sequence_name = seq_row[0]
                        logger.debug(f"Found alternative sequence: {sequence_name}")
                
                if not seq_row:
                    # Get all sequences for debugging
                    cursor.execute("""
                        SELECT sequencename, last_value 
                        FROM pg_sequences 
                        WHERE schemaname = 'public'
                        ORDER BY sequencename
                    """)
                    all_sequences = cursor.fetchall()
                    logger.debug(f"Available sequences: {all_sequences}")
                    
                    return {
                        'table': table_name,
                        'status': 'missing',
                        'severity': 'warning',
                        'message': f'تسلسل {sequence_name} غير موجود',
                        'recommendation': 'يجب إنشاء التسلسل المفقود',
                        'sequence_name': sequence_name,
                        'current_value': None,
                        'max_id': None,
                        'gap': 0,
                        'table_name': table_name,
                        'column_name': column_name,
                        'available_sequences': all_sequences
                    }
                
                # If we get here, we have a valid sequence row
                current_seq = seq_row[1] if seq_row[1] is not None else 0
                
                # Get max ID from the table
                try:
                    cursor.execute(f'SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}')
                    max_id_row = cursor.fetchone()
                    max_id = max_id_row[0] if max_id_row and max_id_row[0] is not None else 0
                    logger.debug(f"Max ID for {table_name}: {max_id} (type: {type(max_id) if max_id is not None else 'NoneType'})")
                except Exception as e:
                    logger.error(f"Error getting max ID for {table_name}: {str(e)}")
                    max_id = 0

                # Calculate next sequence value and gap
                next_value = current_seq + 1
                gap = max(0, max_id - current_seq) if max_id is not None else 0
                
                logger.debug(f"Sequence values for {table_name} - max_id: {max_id} (type: {type(max_id)}), current_seq: {current_seq} (type: {type(current_seq)}), next_value: {next_value}, gap: {gap}")

                # Determine sequence health
                result = {
                    'table': table_name,
                    'sequence_name': sequence_name,
                    'current_value': current_seq,
                    'max_id': max_id,
                    'gap': gap,
                    'table_name': table_name,
                    'column_name': column_name
                }

                if max_id is None or current_seq is None:
                    result.update({
                        'status': 'error',
                        'severity': 'critical',
                        'message': 'خطأ في قراءة قيم التسلسل',
                        'recommendation': 'يجب التحقق من صحة الجدول والتسلسل'
                    })
                elif gap == 0:
                    result.update({
                        'status': 'healthy',
                        'severity': 'info',
                        'message': 'التسلسل سليم',
                        'recommendation': 'لا يلزم اتخاذ إجراء'
                    })
                elif gap > 0 and gap <= 1000:
                    result.update({
                        'status': 'warning',
                        'severity': 'warning',
                        'message': f'هناك فجوة صغيرة في التسلسل ({gap})',
                        'recommendation': 'يمكن تجاهل الفجوة الصغيرة'
                    })
                else:
                    result.update({
                        'status': 'problems',
                        'severity': 'critical',
                        'message': f'فجوة كبيرة في التسلسل ({gap})',
                        'recommendation': 'يجب إعادة تعيين التسلسل'
                    })

                return result

        except Exception as e:
            logger.error(f"Error checking sequence health for {table_name}: {str(e)}", exc_info=True)
            return {
                'table': table_name,
                'status': 'error',
                'severity': 'critical',
                'message': f'خطأ في فحص التسلسل: {str(e)}',
                'recommendation': 'يجب مراجعة سجلات الخطأ',
                'sequence_name': sequence_name,
                'current_value': None,
                'max_id': None,
                'gap': 0,
                'table_name': table_name,
                'column_name': column_name
            }

    def display_table_result(self, result):
        """Display the result of checking a single table.
        
        Args:
            result (dict): Dictionary containing table check results
        """
        table = result['table']
        status = result['status']

        # Set style and icon based on status and severity
        if status == 'problems':
            if result['severity'] == 'critical':
                style = getattr(self.style, 'ERROR', lambda x: f"ERROR: {x}")
                icon = '🚨'
            else:
                style = self.style.WARNING
                icon = '⚠️'
        elif status == 'healthy':
            style = self.style.SUCCESS
            icon = '✅'
        else:
            style = self.style.WARNING
            icon = 'ℹ️'

        # Display main message
        self.stdout.write(style(f'{icon} {table}: {result["message"]}'))

        # Display additional details if available
        if 'column' in result:
            self.stdout.write(f'   العمود: {result["column"]}')
            self.stdout.write(f'   أعلى ID: {result["max_id"]}')
            self.stdout.write(f'   التسلسل الحالي: {result["current_seq"]}')
            self.stdout.write(f'   عدد الصفوف: {result["row_count"]}')

    def display_app_summary(self, app_name, results):
        """عرض ملخص نتائج التطبيق"""
        problems = len(results['problems'])
        healthy = len(results['healthy'])
        no_seq = len(results['no_sequence'])
        errors = len(results['errors'])
        
        self.stdout.write(f'\n📊 ملخص {app_name}:')
        if problems > 0:
            self.stdout.write(self.style.ERROR(f'  🚨 مشاكل: {problems}'))
        if healthy > 0:
            self.stdout.write(self.style.SUCCESS(f'  ✅ سليم: {healthy}'))
        if no_seq > 0:
            self.stdout.write(self.style.WARNING(f'  ℹ️  بدون تسلسل: {no_seq}'))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'  ❌ أخطاء: {errors}'))

    def display_summary(self, results):
        """عرض الملخص العام"""
        problems = results['problems']
        healthy = results['healthy']
        no_seq = results['no_sequence']
        errors = results['errors']
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 الملخص العام:'))
        
        if problems:
            critical = [p for p in problems if p.get('severity') == 'critical']
            warnings = [p for p in problems if p.get('severity') == 'warning']
            
            if critical:
                self.stdout.write(
                    self.style.ERROR(f'🚨 مشاكل حرجة: {len(critical)}')
                )
                for problem in critical:
                    self.stdout.write(f'   - {problem["table"]}: {problem["message"]}')
            
            if warnings:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  تحذيرات: {len(warnings)}')
                )
                if self.show_all:
                    for warning in warnings:
                        self.stdout.write(f'   - {warning["table"]}: {warning["message"]}')
        
        if healthy and self.show_all:
            self.stdout.write(
                self.style.SUCCESS(f'✅ جداول سليمة: {len(healthy)}')
            )
        
        if no_seq and self.show_all:
            self.stdout.write(
                self.style.WARNING(f'ℹ️  جداول بدون تسلسل: {len(no_seq)}')
            )
        
        if errors:
            self.stdout.write(
                self.style.ERROR(f'❌ أخطاء: {len(errors)}')
            )
            for error in errors:
                self.stdout.write(f'   - {error["table"]}: {error["error"]}')
        
        # توصيات
        if problems:
            self.stdout.write('\n💡 التوصيات:')
            critical_count = len([p for p in problems if p.get('severity') == 'critical'])
            if critical_count > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f'🚨 يجب إصلاح {critical_count} مشكلة حرجة فوراً!'
                    )
                )
                self.stdout.write('   استخدم: python manage.py fix_all_sequences')

    def export_results(self, results, filename):
        """تصدير النتائج إلى ملف JSON"""
        import json
        from datetime import datetime
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'problems': len(results['problems']),
                'healthy': len(results['healthy']),
                'no_sequence': len(results['no_sequence']),
                'errors': len(results['errors'])
            },
            'details': results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.stdout.write(
                self.style.SUCCESS(f'📄 تم تصدير النتائج إلى: {filename}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ فشل في تصدير النتائج: {str(e)}')
            )
