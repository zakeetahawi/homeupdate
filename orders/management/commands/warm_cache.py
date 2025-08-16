"""
أمر Django لتسخين التخزين المؤقت
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from orders.cache_utils import warm_up_cache, get_cache_stats, clear_all_form_cache


class Command(BaseCommand):
    help = 'تسخين التخزين المؤقت لتحسين الأداء'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='تنظيف التخزين المؤقت قبل التسخين',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='عرض إحصائيات التخزين المؤقت',
        )
        parser.add_argument(
            '--clear-only',
            action='store_true',
            help='تنظيف التخزين المؤقت فقط بدون تسخين',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔥 بدء عملية إدارة التخزين المؤقت...')
        )

        # عرض الإحصائيات قبل العملية
        if options['stats']:
            self.show_cache_stats('قبل العملية')

        # تنظيف التخزين المؤقت إذا طُلب
        if options['clear'] or options['clear_only']:
            self.stdout.write('🧹 تنظيف التخزين المؤقت...')
            clear_all_form_cache()
            self.stdout.write(
                self.style.SUCCESS('✅ تم تنظيف التخزين المؤقت بنجاح')
            )

        # إذا كان المطلوب التنظيف فقط، توقف هنا
        if options['clear_only']:
            return

        # تسخين التخزين المؤقت
        self.stdout.write('🔥 تسخين التخزين المؤقت...')
        try:
            warm_up_cache()
            self.stdout.write(
                self.style.SUCCESS('✅ تم تسخين التخزين المؤقت بنجاح')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في تسخين التخزين المؤقت: {str(e)}')
            )

        # عرض الإحصائيات بعد العملية
        if options['stats']:
            self.show_cache_stats('بعد العملية')

        self.stdout.write(
            self.style.SUCCESS('🎉 انتهت عملية إدارة التخزين المؤقت')
        )

    def show_cache_stats(self, when):
        """عرض إحصائيات التخزين المؤقت"""
        self.stdout.write(f'\n📊 إحصائيات التخزين المؤقت {when}:')
        self.stdout.write('-' * 50)
        
        stats = get_cache_stats()
        
        if stats['type'] == 'Redis':
            self.stdout.write(f"النوع: {stats['type']}")
            self.stdout.write(f"الذاكرة المستخدمة: {stats['used_memory']}")
            self.stdout.write(f"العملاء المتصلون: {stats['connected_clients']}")
            self.stdout.write(f"إجمالي الأوامر: {stats['total_commands_processed']}")
            self.stdout.write(f"نجاح الوصول: {stats['keyspace_hits']}")
            self.stdout.write(f"فشل الوصول: {stats['keyspace_misses']}")
            self.stdout.write(f"معدل النجاح: {stats['hit_rate']}%")
        else:
            self.stdout.write(f"النوع: {stats['type']}")
            self.stdout.write(f"الرسالة: {stats.get('message', 'لا توجد معلومات إضافية')}")
        
        self.stdout.write('-' * 50)
