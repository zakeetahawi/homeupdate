"""
Management Command لإدارة وتحسين الأداء
"""

import time
import json
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from crm.services.performance_service import PerformanceMonitor, DatabaseOptimizer

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'إدارة وتحسين أداء النظام'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=[
                'monitor', 'optimize', 'cache_clear', 'cache_stats',
                'db_stats', 'db_optimize', 'slow_queries', 'errors',
                'metrics', 'report', 'cleanup'
            ],
            help='الإجراء المطلوب'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='مدة المراقبة بالثواني (افتراضي: 60)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='فاصل المراقبة بالثواني (افتراضي: 10)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='ملف الإخراج للتقارير'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'monitor':
            self.monitor_performance(options)
        elif action == 'optimize':
            self.optimize_performance(options)
        elif action == 'cache_clear':
            self.clear_cache(options)
        elif action == 'cache_stats':
            self.cache_stats(options)
        elif action == 'db_stats':
            self.database_stats(options)
        elif action == 'db_optimize':
            self.optimize_database(options)
        elif action == 'slow_queries':
            self.show_slow_queries(options)
        elif action == 'errors':
            self.show_errors(options)
        elif action == 'metrics':
            self.show_metrics(options)
        elif action == 'report':
            self.generate_report(options)
        elif action == 'cleanup':
            self.cleanup_performance_data(options)

    def monitor_performance(self, options):
        """مراقبة الأداء في الوقت الفعلي"""
        duration = options['duration']
        interval = options['interval']
        
        self.stdout.write(
            self.style.SUCCESS(f'بدء مراقبة الأداء لمدة {duration} ثانية...')
        )
        
        start_time = time.time()
        metrics_history = []
        
        while time.time() - start_time < duration:
            metrics = PerformanceMonitor.get_performance_metrics()
            metrics_history.append(metrics)
            
            self.stdout.write(
                f'Cache Hit Rate: {metrics["cache_hit_rate"]:.1f}% | '
                f'Slow Queries: {metrics["slow_queries"]} | '
                f'Errors: {metrics["error_count"]}'
            )
            
            time.sleep(interval)
        
        # حفظ النتائج
        if options['output']:
            with open(options['output'], 'w', encoding='utf-8') as f:
                json.dump(metrics_history, f, indent=2, default=str)
        
        self.stdout.write(
            self.style.SUCCESS('تم الانتهاء من المراقبة')
        )

    def optimize_performance(self, options):
        """تحسين الأداء"""
        self.stdout.write('بدء تحسين الأداء...')
        
        # تنظيف cache
        cache.clear()
        self.stdout.write('✓ تم تنظيف cache')
        
        # تحسين قاعدة البيانات
        try:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM ANALYZE;")
            self.stdout.write('✓ تم تحسين قاعدة البيانات')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'تحذير في تحسين قاعدة البيانات: {e}')
            )
        
        # إعادة تعيين مقاييس الأداء
        cache.delete('cache_hits')
        cache.delete('cache_misses')
        cache.delete('slow_queries')
        cache.delete('error_count')
        
        self.stdout.write(
            self.style.SUCCESS('تم تحسين الأداء بنجاح')
        )

    def clear_cache(self, options):
        """تنظيف cache"""
        cache.clear()
        self.stdout.write(
            self.style.SUCCESS('تم تنظيف cache بنجاح')
        )

    def cache_stats(self, options):
        """إحصائيات cache"""
        metrics = PerformanceMonitor.get_performance_metrics()
        
        self.stdout.write('إحصائيات Cache:')
        self.stdout.write(f'  Cache Hits: {metrics["cache_hits"]}')
        self.stdout.write(f'  Cache Misses: {metrics["cache_misses"]}')
        self.stdout.write(f'  Hit Rate: {metrics["cache_hit_rate"]:.1f}%')
        
        # إحصائيات إضافية
        cache_keys = cache.keys('*')
        self.stdout.write(f'  Total Cache Keys: {len(cache_keys)}')

    def database_stats(self, options):
        """إحصائيات قاعدة البيانات"""
        try:
            stats = DatabaseOptimizer.get_table_stats()
            
            self.stdout.write('إحصائيات قاعدة البيانات:')
            for stat in stats:
                self.stdout.write(
                    f'  {stat[1]}: {stat[4]} سجلات حية, '
                    f'{stat[5]} سجلات محذوفة'
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في الحصول على إحصائيات قاعدة البيانات: {e}')
            )

    def optimize_database(self, options):
        """تحسين قاعدة البيانات"""
        self.stdout.write('بدء تحسين قاعدة البيانات...')
        
        try:
            with connection.cursor() as cursor:
                # تحليل الجداول
                cursor.execute("ANALYZE;")
                self.stdout.write('✓ تم تحليل الجداول')
                
                # تنظيف الجداول
                cursor.execute("VACUUM;")
                self.stdout.write('✓ تم تنظيف الجداول')
                
                # إعادة بناء الفهارس
                cursor.execute("REINDEX DATABASE;")
                self.stdout.write('✓ تم إعادة بناء الفهارس')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في تحسين قاعدة البيانات: {e}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('تم تحسين قاعدة البيانات بنجاح')
        )

    def show_slow_queries(self, options):
        """عرض الاستعلامات البطيئة"""
        slow_queries = cache.get('slow_queries', [])
        
        if not slow_queries:
            self.stdout.write('لا توجد استعلامات بطيئة مسجلة')
            return
        
        self.stdout.write('الاستعلامات البطيئة:')
        for i, query in enumerate(slow_queries[-10:], 1):  # آخر 10 استعلامات
            self.stdout.write(
                f'  {i}. {query["timestamp"]} - '
                f'{query["duration"]:.3f}s - '
                f'{query["query_count"]} استعلام'
            )

    def show_errors(self, options):
        """عرض الأخطاء الأخيرة"""
        errors = cache.get('recent_errors', [])
        
        if not errors:
            self.stdout.write('لا توجد أخطاء مسجلة')
            return
        
        self.stdout.write('الأخطاء الأخيرة:')
        for i, error in enumerate(errors[-10:], 1):  # آخر 10 أخطاء
            self.stdout.write(
                f'  {i}. {error["timestamp"]} - '
                f'{error["type"]}: {error["message"]}'
            )

    def show_metrics(self, options):
        """عرض مقاييس الأداء الحالية"""
        metrics = PerformanceMonitor.get_performance_metrics()
        
        self.stdout.write('مقاييس الأداء الحالية:')
        self.stdout.write(f'  Timestamp: {metrics["timestamp"]}')
        self.stdout.write(f'  Cache Hit Rate: {metrics["cache_hit_rate"]:.1f}%')
        self.stdout.write(f'  Slow Queries: {metrics["slow_queries"]}')
        self.stdout.write(f'  Error Count: {metrics["error_count"]}')
        
        # إحصائيات إضافية
        total_requests = metrics["cache_hits"] + metrics["cache_misses"]
        if total_requests > 0:
            self.stdout.write(f'  Total Requests: {total_requests}')

    def generate_report(self, options):
        """إنشاء تقرير شامل للأداء"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': PerformanceMonitor.get_performance_metrics(),
            'database_stats': self._get_database_report(),
            'cache_stats': self._get_cache_report(),
            'recommendations': self._get_recommendations()
        }
        
        if options['output']:
            with open(options['output'], 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            self.stdout.write(
                self.style.SUCCESS(f'تم حفظ التقرير في {options["output"]}')
            )
        else:
            self.stdout.write(json.dumps(report, indent=2, default=str))

    def cleanup_performance_data(self, options):
        """تنظيف بيانات الأداء القديمة"""
        self.stdout.write('تنظيف بيانات الأداء القديمة...')
        
        # حذف البيانات القديمة من cache
        cache.delete('slow_queries')
        cache.delete('recent_errors')
        cache.delete('cache_hits')
        cache.delete('cache_misses')
        cache.delete('slow_queries_count')
        cache.delete('error_count')
        
        self.stdout.write(
            self.style.SUCCESS('تم تنظيف بيانات الأداء بنجاح')
        )

    def _get_database_report(self):
        """الحصول على تقرير قاعدة البيانات"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_live_tup as live_rows,
                        n_dead_tup as dead_rows,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            return f"خطأ في الحصول على إحصائيات قاعدة البيانات: {e}"

    def _get_cache_report(self):
        """الحصول على تقرير cache"""
        metrics = PerformanceMonitor.get_performance_metrics()
        return {
            'hit_rate': metrics['cache_hit_rate'],
            'hits': metrics['cache_hits'],
            'misses': metrics['cache_misses'],
            'total_requests': metrics['cache_hits'] + metrics['cache_misses']
        }

    def _get_recommendations(self):
        """الحصول على التوصيات"""
        recommendations = []
        metrics = PerformanceMonitor.get_performance_metrics()
        
        # توصيات cache
        if metrics['cache_hit_rate'] < 70:
            recommendations.append({
                'type': 'cache',
                'priority': 'high',
                'message': 'نسبة نجاح cache منخفضة. يوصى بتحسين استراتيجية cache'
            })
        
        # توصيات الاستعلامات البطيئة
        if metrics['slow_queries'] > 10:
            recommendations.append({
                'type': 'database',
                'priority': 'medium',
                'message': 'عدد الاستعلامات البطيئة مرتفع. يوصى بتحسين الاستعلامات'
            })
        
        # توصيات الأخطاء
        if metrics['error_count'] > 5:
            recommendations.append({
                'type': 'errors',
                'priority': 'high',
                'message': 'عدد الأخطاء مرتفع. يوصى بمراجعة السجلات'
            })
        
        return recommendations 