from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.apps import apps


class Command(BaseCommand):
    help = 'إصلاح تسلسل ID لجميع الجداول'

    def handle(self, *args, **options):
        self.stdout.write('🔧 بدء إصلاح تسلسل ID...')
        
        try:
            with transaction.atomic():
                self.fix_all_sequences()
            self.stdout.write(
                self.style.SUCCESS('✅ تم إصلاح جميع التسلسلات بنجاح')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في إصلاح التسلسلات: {e}')
            )

    def fix_all_sequences(self):
        """إصلاح جميع تسلسلات ID"""
        with connection.cursor() as cursor:
            # التحقق من نوع قاعدة البيانات
            db_vendor = connection.vendor

            if db_vendor == 'postgresql':
                # PostgreSQL
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
            else:
                # MySQL
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    AND table_type = 'BASE TABLE'
                """)
            
            tables = [row[0] for row in cursor.fetchall()]
            fixed_count = 0
            
            for table in tables:
                try:
                    if db_vendor == 'postgresql':
                        # PostgreSQL - البحث عن sequences
                        cursor.execute(f"""
                            SELECT column_name, column_default
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                            AND table_name = '{table}'
                            AND column_name = 'id'
                            AND column_default LIKE 'nextval%'
                        """)

                        result = cursor.fetchone()
                        if result:
                            # الحصول على أكبر ID موجود
                            cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
                            max_id_result = cursor.fetchone()
                            max_id = max_id_result[0] if max_id_result else 0

                            # إعادة تعيين sequence
                            sequence_name = f"{table}_id_seq"
                            next_id = max_id + 1
                            cursor.execute(f"SELECT setval('{sequence_name}', {next_id}, false)")

                            self.stdout.write(f"   ✅ {table}: MAX_ID={max_id}, NEXT_ID={next_id}")
                            fixed_count += 1
                    else:
                        # MySQL
                        cursor.execute(f"""
                            SELECT COLUMN_NAME, EXTRA
                            FROM information_schema.COLUMNS
                            WHERE TABLE_SCHEMA = DATABASE()
                            AND TABLE_NAME = '{table}'
                            AND COLUMN_NAME = 'id'
                        """)

                        result = cursor.fetchone()
                        if result and len(result) > 1 and 'auto_increment' in result[1]:
                            # الحصول على أكبر ID موجود
                            cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
                            max_id_result = cursor.fetchone()
                            max_id = max_id_result[0] if max_id_result else 0

                            # تعيين AUTO_INCREMENT للقيمة التالية
                            next_id = max_id + 1
                            cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = {next_id}")

                            self.stdout.write(f"   ✅ {table}: MAX_ID={max_id}, NEXT_ID={next_id}")
                            fixed_count += 1

                except Exception as e:
                    self.stdout.write(f"   ⚠️ تحذير في {table}: {e}")
                    continue
            
            self.stdout.write(f"📊 تم إصلاح {fixed_count} جدول")

    def fix_null_values(self):
        """إصلاح القيم الفارغة"""
        with connection.cursor() as cursor:
            try:
                # إصلاح customers_customer
                cursor.execute("""
                    UPDATE customers_customer 
                    SET id = (
                        SELECT COALESCE(MAX(id), 0) + ROW_NUMBER() OVER() 
                        FROM (SELECT id FROM customers_customer WHERE id IS NOT NULL) t
                    ) 
                    WHERE id IS NULL
                """)
                
                # إصلاح accounts_user
                cursor.execute("""
                    UPDATE accounts_user 
                    SET id = (
                        SELECT COALESCE(MAX(id), 0) + ROW_NUMBER() OVER() 
                        FROM (SELECT id FROM accounts_user WHERE id IS NOT NULL) t
                    ) 
                    WHERE id IS NULL
                """)
                
                self.stdout.write("✅ تم إصلاح القيم الفارغة")
                
            except Exception as e:
                self.stdout.write(f"⚠️ تحذير في إصلاح القيم الفارغة: {e}")
