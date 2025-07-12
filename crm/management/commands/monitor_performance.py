from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import time
import psutil
import os
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'مراقبة أداء النظام وإحصائيات قاعدة البيانات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='مدة المراقبة بالثواني (افتراضي: 60)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='فاصل المراقبة بالثواني (افتراضي: 5)'
        )

    def handle(self, *args, **options):
        duration = options['duration']
        interval = options['interval']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'بدء مراقبة الأداء لمدة {duration} ثانية بفاصل {interval} ثواني'
            )
        )
        
        start_time = time.time()
        end_time = start_time + duration
        
        # إحصائيات النظام
        stats = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_usage': [],
            'db_connections': [],
            'cache_hits': [],
            'cache_misses': [],
            'slow_queries': []
        }
        
        while time.time() < end_time:
            try:
                # جمع الإحصائيات
                current_stats = self.collect_stats()
                
                # عرض الإحصائيات
                self.display_stats(current_stats)
                
                # حفظ الإحصائيات
                for key in stats:
                    stats[key].append(current_stats.get(key, 0))
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('تم إيقاف المراقبة بواسطة المستخدم'))
                break
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'خطأ في المراقبة: {e}')
                )
                time.sleep(interval)
        
        # عرض التقرير النهائي
        self.generate_report(stats, start_time, time.time())

    def collect_stats(self):
        """جمع إحصائيات النظام"""
        stats = {}
        
        # استخدام CPU
        stats['cpu_usage'] = psutil.cpu_percent(interval=1)
        
        # استخدام الذاكرة
        memory = psutil.virtual_memory()
        stats['memory_usage'] = memory.percent
        
        # استخدام القرص
        disk = psutil.disk_usage('/')
        stats['disk_usage'] = disk.percent
        
        # اتصالات قاعدة البيانات
        stats['db_connections'] = len(connection.queries)
        
        # إحصائيات الذاكرة المؤقتة
        cache_stats = cache.get('cache_stats', {'hits': 0, 'misses': 0})
        stats['cache_hits'] = cache_stats.get('hits', 0)
        stats['cache_misses'] = cache_stats.get('misses', 0)
        
        # الاستعلامات البطيئة
        slow_queries = [
            q for q in connection.queries 
            if float(q.get('time', 0)) > 0.1
        ]
        stats['slow_queries'] = len(slow_queries)
        
        return stats

    def display_stats(self, stats):
        """عرض الإحصائيات الحالية"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # تلوين النتائج
        cpu_color = self.get_performance_color(stats['cpu_usage'], 80, 60)
        memory_color = self.get_performance_color(stats['memory_usage'], 80, 60)
        disk_color = self.get_performance_color(stats['disk_usage'], 90, 70)
        
        self.stdout.write(
            f'\n[{timestamp}] إحصائيات الأداء:'
        )
        self.stdout.write(
            f'  CPU: {cpu_color}{stats["cpu_usage"]:.1f}%{self.style.RESET_ALL}'
        )
        self.stdout.write(
            f'  الذاكرة: {memory_color}{stats["memory_usage"]:.1f}%{self.style.RESET_ALL}'
        )
        self.stdout.write(
            f'  القرص: {disk_color}{stats["disk_usage"]:.1f}%{self.style.RESET_ALL}'
        )
        self.stdout.write(
            f'  استعلامات DB: {stats["db_connections"]}'
        )
        self.stdout.write(
            f'  الذاكرة المؤقتة: {stats["cache_hits"]} نجح / {stats["cache_misses"]} فشل'
        )
        self.stdout.write(
            f'  استعلامات بطيئة: {stats["slow_queries"]}'
        )

    def get_performance_color(self, value, critical_threshold, warning_threshold):
        """تحديد لون الأداء"""
        if value >= critical_threshold:
            return self.style.ERROR
        elif value >= warning_threshold:
            return self.style.WARNING
        else:
            return self.style.SUCCESS

    def generate_report(self, stats, start_time, end_time):
        """إنشاء تقرير الأداء النهائي"""
        duration = end_time - start_time
        
        self.stdout.write(
            self.style.SUCCESS('\n' + '='*50)
        )
        self.stdout.write(
            self.style.SUCCESS('تقرير مراقبة الأداء النهائي')
        )
        self.stdout.write(
            self.style.SUCCESS('='*50)
        )
        
        # متوسط الإحصائيات
        avg_cpu = sum(stats['cpu_usage']) / len(stats['cpu_usage']) if stats['cpu_usage'] else 0
        avg_memory = sum(stats['memory_usage']) / len(stats['memory_usage']) if stats['memory_usage'] else 0
        avg_disk = sum(stats['disk_usage']) / len(stats['disk_usage']) if stats['disk_usage'] else 0
        
        self.stdout.write(f'مدة المراقبة: {duration:.1f} ثانية')
        self.stdout.write(f'متوسط استخدام CPU: {avg_cpu:.1f}%')
        self.stdout.write(f'متوسط استخدام الذاكرة: {avg_memory:.1f}%')
        self.stdout.write(f'متوسط استخدام القرص: {avg_disk:.1f}%')
        
        # تحليل الأداء
        max_cpu = max(stats['cpu_usage']) if stats['cpu_usage'] else 0
        max_memory = max(stats['memory_usage']) if stats['memory_usage'] else 0
        
        if max_cpu > 80:
            self.stdout.write(
                self.style.ERROR('تحذير: استخدام CPU مرتفع!')
            )
        
        if max_memory > 80:
            self.stdout.write(
                self.style.ERROR('تحذير: استخدام الذاكرة مرتفع!')
            )
        
        # توصيات
        self.stdout.write('\nالتوصيات:')
        if avg_cpu > 60:
            self.stdout.write('- فكر في تحسين الكود أو إضافة خوادم إضافية')
        
        if avg_memory > 70:
            self.stdout.write('- فكر في زيادة الذاكرة أو تحسين استخدام الذاكرة')
        
        if stats['slow_queries'] and sum(stats['slow_queries']) > 0:
            self.stdout.write('- فكر في تحسين استعلامات قاعدة البيانات')
        
        cache_hit_rate = 0
        total_cache_requests = sum(stats['cache_hits']) + sum(stats['cache_misses'])
        if total_cache_requests > 0:
            cache_hit_rate = (sum(stats['cache_hits']) / total_cache_requests) * 100
        
        if cache_hit_rate < 50:
            self.stdout.write('- فكر في تحسين استخدام الذاكرة المؤقتة')
        
        self.stdout.write(
            self.style.SUCCESS('\nتم إنشاء التقرير بنجاح!')
        ) 