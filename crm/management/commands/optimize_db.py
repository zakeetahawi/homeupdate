"""
Django management command لتحسين قاعدة البيانات
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import psycopg2
import time


class Command(BaseCommand):
    help = 'تحسين إعدادات وأداء قاعدة البيانات'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='تحليل الجداول لتحسين الفهارس'
        )
        
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='تنظيف وضغط قاعدة البيانات'
        )
        
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='إعادة بناء الفهارس'
        )
        
        parser.add_argument(
            '--stats',
            action='store_true',
            help='عرض إحصائيات قاعدة البيانات'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='تشغيل جميع عمليات التحسين'
        )
    
    def handle(self, *args, **options):
        if options['all']:
            self._run_all_optimizations()
        else:
            if options['stats']:
                self._show_database_stats()
            
            if options['analyze']:
                self._analyze_tables()
            
            if options['vacuum']:
                self._vacuum_database()
            
            if options['reindex']:
                self._reindex_database()
    
    def _get_db_connection(self):
        """الحصول على اتصال مباشر لقاعدة البيانات"""
        db_config = settings.DATABASES['default']
        
        # استخدام الاتصال المباشر إذا كان متاحاً
        if hasattr(settings, 'DATABASES_DIRECT'):
            db_config = settings.DATABASES_DIRECT['default']
        
        return psycopg2.connect(
            host=db_config['HOST'],
            port=db_config['PORT'],
            database=db_config['NAME'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            connect_timeout=30,
        )
    
    def _show_database_stats(self):
        """عرض إحصائيات قاعدة البيانات"""
        self.stdout.write(self.style.SUCCESS('📊 إحصائيات قاعدة البيانات:'))
        self.stdout.write('-' * 60)
        
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                # حجم قاعدة البيانات
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;
                """)
                db_size = cursor.fetchone()[0]
                self.stdout.write(f"حجم قاعدة البيانات: {db_size}")
                
                # أكبر الجداول
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY size_bytes DESC 
                    LIMIT 10;
                """)
                
                self.stdout.write('\n🗂️  أكبر الجداول:')
                for row in cursor.fetchall():
                    self.stdout.write(f"   {row[1]}: {row[2]}")
                
                # إحصائيات الاتصالات
                cursor.execute("""
                    SELECT 
                        count(*) as total,
                        count(*) FILTER (WHERE state = 'active') as active,
                        count(*) FILTER (WHERE state = 'idle') as idle,
                        count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                    FROM pg_stat_activity 
                    WHERE datname = current_database();
                """)
                
                conn_stats = cursor.fetchone()
                self.stdout.write('\n🔌 الاتصالات الحالية:')
                self.stdout.write(f"   إجمالي: {conn_stats[0]}")
                self.stdout.write(f"   نشط: {conn_stats[1]}")
                self.stdout.write(f"   خامل: {conn_stats[2]}")
                self.stdout.write(f"   معلق في معاملة: {conn_stats[3]}")
                
                # إحصائيات الفهارس
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY pg_relation_size(indexname::regclass) DESC 
                    LIMIT 10;
                """)
                
                self.stdout.write('\n📇 أكبر الفهارس:')
                for row in cursor.fetchall():
                    self.stdout.write(f"   {row[1]}.{row[2]}: {row[3]}")
            
            conn.close()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطأ في عرض الإحصائيات: {e}'))
    
    def _analyze_tables(self):
        """تحليل الجداول لتحسين الفهارس"""
        self.stdout.write(self.style.SUCCESS('🔍 بدء تحليل الجداول...'))
        
        try:
            conn = self._get_db_connection()
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # الحصول على قائمة الجداول
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename;
                """)
                
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    self.stdout.write(f'   تحليل جدول: {table_name}')
                    
                    start_time = time.time()
                    cursor.execute(f'ANALYZE "{table_name}";')
                    end_time = time.time()
                    
                    self.stdout.write(f'   ✅ تم ({end_time - start_time:.2f}s)')
            
            conn.close()
            self.stdout.write(self.style.SUCCESS('✅ تم تحليل جميع الجداول'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطأ في تحليل الجداول: {e}'))
    
    def _vacuum_database(self):
        """تنظيف وضغط قاعدة البيانات"""
        self.stdout.write(self.style.SUCCESS('🧹 بدء تنظيف قاعدة البيانات...'))
        
        try:
            conn = self._get_db_connection()
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # VACUUM ANALYZE لجميع الجداول
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename;
                """)
                
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    self.stdout.write(f'   تنظيف جدول: {table_name}')
                    
                    start_time = time.time()
                    cursor.execute(f'VACUUM ANALYZE "{table_name}";')
                    end_time = time.time()
                    
                    self.stdout.write(f'   ✅ تم ({end_time - start_time:.2f}s)')
            
            conn.close()
            self.stdout.write(self.style.SUCCESS('✅ تم تنظيف قاعدة البيانات'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطأ في تنظيف قاعدة البيانات: {e}'))
    
    def _reindex_database(self):
        """إعادة بناء الفهارس"""
        self.stdout.write(self.style.SUCCESS('📇 بدء إعادة بناء الفهارس...'))
        
        try:
            conn = self._get_db_connection()
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # إعادة بناء جميع الفهارس
                cursor.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY indexname;
                """)
                
                indexes = cursor.fetchall()
                
                for index in indexes:
                    index_name = index[0]
                    self.stdout.write(f'   إعادة بناء فهرس: {index_name}')
                    
                    start_time = time.time()
                    cursor.execute(f'REINDEX INDEX "{index_name}";')
                    end_time = time.time()
                    
                    self.stdout.write(f'   ✅ تم ({end_time - start_time:.2f}s)')
            
            conn.close()
            self.stdout.write(self.style.SUCCESS('✅ تم إعادة بناء جميع الفهارس'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطأ في إعادة بناء الفهارس: {e}'))
    
    def _run_all_optimizations(self):
        """تشغيل جميع عمليات التحسين"""
        self.stdout.write(self.style.SUCCESS('🚀 بدء تحسين شامل لقاعدة البيانات...'))
        self.stdout.write('=' * 60)
        
        # 1. عرض الإحصائيات قبل التحسين
        self.stdout.write(self.style.SUCCESS('\n1️⃣ الإحصائيات قبل التحسين:'))
        self._show_database_stats()
        
        # 2. تحليل الجداول
        self.stdout.write(self.style.SUCCESS('\n2️⃣ تحليل الجداول:'))
        self._analyze_tables()
        
        # 3. تنظيف قاعدة البيانات
        self.stdout.write(self.style.SUCCESS('\n3️⃣ تنظيف قاعدة البيانات:'))
        self._vacuum_database()
        
        # 4. إعادة بناء الفهارس
        self.stdout.write(self.style.SUCCESS('\n4️⃣ إعادة بناء الفهارس:'))
        self._reindex_database()
        
        # 5. عرض الإحصائيات بعد التحسين
        self.stdout.write(self.style.SUCCESS('\n5️⃣ الإحصائيات بعد التحسين:'))
        self._show_database_stats()
        
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('🎉 تم إكمال التحسين الشامل بنجاح!'))
