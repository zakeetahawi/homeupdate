from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'تحليل شامل لأداء الاستعلامات في النظام'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-type',
            type=str,
            help='نوع admin للتحليل (orders, manufacturing, customers, etc.)',
            default='all'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل مفصلة'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 بدء تحليل أداء الاستعلامات...')
        )
        
        # تحليل الفهارس
        self.analyze_indexes()
        
        # تحليل الاستعلامات البطيئة
        self.analyze_slow_queries()
        
        # تحليل استعلامات Admin محددة
        admin_type = options.get('admin_type', 'all')
        if admin_type == 'all':
            self.analyze_orders_admin()
            self.analyze_manufacturing_admin()
            self.analyze_customers_admin()
        elif admin_type == 'manufacturing':
            self.analyze_manufacturing_admin()
        elif admin_type == 'orders':
            self.analyze_orders_admin()
        elif admin_type == 'customers':
            self.analyze_customers_admin()

    def analyze_indexes(self):
        """تحليل الفهارس وكفاءتها"""
        self.stdout.write('\n📊 تحليل الفهارس:')
        self.stdout.write('=' * 50)
        
        with connection.cursor() as cursor:
            # فحص استخدام الفهارس
            cursor.execute("""
                SELECT schemaname, relname as tablename, indexrelname as indexname, 
                       idx_tup_read, idx_tup_fetch
                FROM pg_stat_user_indexes 
                ORDER BY idx_tup_read DESC
                LIMIT 10;
            """)
            
            results = cursor.fetchall()
            if results:
                for row in results:
                    schema, table, index, reads, fetches = row
                    efficiency = (fetches / reads * 100) if reads > 0 else 0
                    self.stdout.write(
                        f"  📋 {table}.{index}: "
                        f"قراءات={reads:,}, استخدام={fetches:,}, "
                        f"كفاءة={efficiency:.1f}%"
                    )
            else:
                self.stdout.write("  ℹ️  لا توجد بيانات إحصائية للفهارس")

    def analyze_slow_queries(self):
        """تحليل الاستعلامات البطيئة"""
        self.stdout.write('\n🐌 تحليل الاستعلامات البطيئة:')
        self.stdout.write('=' * 50)
        
        with connection.cursor() as cursor:
            # التحقق من وجود pg_stat_statements
            try:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                    );
                """)
                
                if cursor.fetchone()[0]:
                    cursor.execute("""
                        SELECT query, calls, total_exec_time, mean_exec_time, rows
                        FROM pg_stat_statements 
                        WHERE query LIKE '%manufacturing%' OR query LIKE '%orders%'
                        ORDER BY mean_exec_time DESC
                        LIMIT 5;
                    """)
                    
                    results = cursor.fetchall()
                    if results:
                        for query, calls, total_time, mean_time, rows in results:
                            self.stdout.write(
                                f"  ⏱️  متوسط الوقت: {mean_time:.2f}ms, "
                                f"استدعاءات: {calls}, "
                                f"الاستعلام: {query[:100]}..."
                            )
                    else:
                        self.stdout.write("  ℹ️  لا توجد استعلامات بطيئة مسجلة")
                else:
                    self.stdout.write("  ⚠️  pg_stat_statements غير مفعل")
            except Exception as e:
                self.stdout.write(f"  ⚠️  خطأ في تحليل الاستعلامات: {e}")

    def analyze_manufacturing_admin(self):
        """تحليل أداء admin التصنيع"""
        self.stdout.write('\n🏭 تحليل admin التصنيع:')
        self.stdout.write('=' * 50)
        
        # محاكاة استعلام admin التصنيع
        start_time = time.time()
        start_queries = len(connection.queries)
        
        with connection.cursor() as cursor:
            # محاكاة الاستعلام الذي يحدث في admin
            cursor.execute("""
                SELECT m.id, m.status, m.order_type, m.created_at,
                       o.order_number, c.name as customer_name
                FROM manufacturing_manufacturingorder m
                LEFT JOIN orders_order o ON m.order_id = o.id
                LEFT JOIN customers_customer c ON o.customer_id = c.id
                ORDER BY m.created_at DESC
                LIMIT 25;
            """)
            
            results = cursor.fetchall()
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        total_time = (end_time - start_time) * 1000  # تحويل لميلي ثانية
        total_queries = end_queries - start_queries
        
        self.stdout.write(
            f"  ⏱️  وقت الاستعلام: {total_time:.2f}ms"
        )
        self.stdout.write(
            f"  🔢 عدد الاستعلامات: {total_queries}"
        )
        self.stdout.write(
            f"  📄 عدد السجلات: {len(results)}"
        )
        
        if total_time > 100:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠️  الاستعلام بطيء! يحتاج تحسين"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ الاستعلام سريع"
                )
            )

    def analyze_orders_admin(self):
        """تحليل أداء admin الطلبات"""
        self.stdout.write('\n📦 تحليل admin الطلبات:')
        self.stdout.write('=' * 50)
        
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT o.id, o.order_number, o.status, o.created_at,
                       c.name as customer_name, b.name as branch_name
                FROM orders_order o
                LEFT JOIN customers_customer c ON o.customer_id = c.id
                LEFT JOIN accounts_branch b ON o.branch_id = b.id
                ORDER BY o.created_at DESC
                LIMIT 25;
            """)
            results = cursor.fetchall()
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        self.stdout.write(f"  ⏱️  وقت الاستعلام: {total_time:.2f}ms")
        self.stdout.write(f"  📄 عدد السجلات: {len(results)}")

    def analyze_customers_admin(self):
        """تحليل أداء admin العملاء"""
        self.stdout.write('\n👥 تحليل admin العملاء:')
        self.stdout.write('=' * 50)
        
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.name, c.code, c.status, c.created_at,
                       b.name as branch_name
                FROM customers_customer c
                LEFT JOIN accounts_branch b ON c.branch_id = b.id
                ORDER BY c.created_at DESC
                LIMIT 25;
            """)
            results = cursor.fetchall()
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        self.stdout.write(f"  ⏱️  وقت الاستعلام: {total_time:.2f}ms")
        self.stdout.write(f"  📄 عدد السجلات: {len(results)}")
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(
            self.style.SUCCESS('✅ تم الانتهاء من تحليل الأداء')
        )
