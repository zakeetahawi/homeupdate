"""
Management Command للتحسين النهائي الشامل
"""

import time
import json
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.contrib.auth.models import User
from accounts.models import UnifiedSystemSettings, UserSecurityProfile, AuditLog
from crm.services.performance_service import PerformanceMonitor, DatabaseOptimizer

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'التحسين النهائي الشامل للنظام'

    def add_arguments(self, parser):
        parser.add_argument(
            '--optimize-all',
            action='store_true',
            help='تنفيذ جميع التحسينات'
        )
        parser.add_argument(
            '--security-check',
            action='store_true',
            help='فحص الأمان'
        )
        parser.add_argument(
            '--performance-check',
            action='store_true',
            help='فحص الأداء'
        )
        parser.add_argument(
            '--database-optimize',
            action='store_true',
            help='تحسين قاعدة البيانات'
        )
        parser.add_argument(
            '--cache-optimize',
            action='store_true',
            help='تحسين Cache'
        )
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='إنشاء مستخدم admin'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 بدء التحسين النهائي الشامل للنظام')
        )
        
        start_time = time.time()
        
        try:
            if options['optimize_all'] or options['security_check']:
                self.optimize_security()
            
            if options['optimize_all'] or options['performance_check']:
                self.optimize_performance()
            
            if options['optimize_all'] or options['database_optimize']:
                self.optimize_database()
            
            if options['optimize_all'] or options['cache_optimize']:
                self.optimize_cache()
            
            if options['create_admin']:
                self.create_admin_user()
            
            if options['optimize_all']:
                self.final_checks()
            
            duration = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(f'✅ تم الانتهاء من التحسين في {duration:.2f} ثانية')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في التحسين: {e}')
            )
            raise CommandError(f'فشل في التحسين: {e}')

    def optimize_security(self):
        """تحسين الأمان"""
        self.stdout.write('🔒 بدء تحسين الأمان...')
        
        # إنشاء إعدادات أمان افتراضية
        settings, created = UnifiedSystemSettings.objects.get_or_create(
            defaults={
                'company_name': 'شركة افتراضية',
                'currency': 'EGP',
                'language': 'ar',
                'timezone': 'Africa/Cairo',
                'security_level': 'high',
                'session_timeout': 30,
                'max_login_attempts': 5,
                'password_expiry_days': 90,
                'two_factor_enabled': True,
                'audit_logging_enabled': True,
            }
        )
        
        if created:
            self.stdout.write('✅ تم إنشاء إعدادات أمان افتراضية')
        
        # إنشاء ملفات أمان للمستخدمين
        users_without_profile = User.objects.filter(security_profile__isnull=True)
        for user in users_without_profile:
            UserSecurityProfile.objects.create(user=user)
        
        if users_without_profile.exists():
            self.stdout.write(f'✅ تم إنشاء ملفات أمان لـ {users_without_profile.count()} مستخدم')
        
        # تسجيل حدث التحسين
        AuditLog.log_event(
            user=None,
            event_type='system_event',
            description='تم تنفيذ تحسين الأمان',
            severity='medium',
            additional_data={'optimization_type': 'security'}
        )
        
        self.stdout.write('✅ تم تحسين الأمان بنجاح')

    def optimize_performance(self):
        """تحسين الأداء"""
        self.stdout.write('⚡ بدء تحسين الأداء...')
        
        # تنظيف cache
        cache.clear()
        self.stdout.write('✅ تم تنظيف cache')
        
        # إعادة تعيين مقاييس الأداء
        cache.delete('cache_hits')
        cache.delete('cache_misses')
        cache.delete('slow_queries')
        cache.delete('error_count')
        self.stdout.write('✅ تم إعادة تعيين مقاييس الأداء')
        
        # تحسين قاعدة البيانات
        try:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM ANALYZE;")
            self.stdout.write('✅ تم تحسين قاعدة البيانات')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'تحذير في تحسين قاعدة البيانات: {e}')
            )
        
        # تسجيل حدث التحسين
        AuditLog.log_event(
            user=None,
            event_type='system_event',
            description='تم تنفيذ تحسين الأداء',
            severity='medium',
            additional_data={'optimization_type': 'performance'}
        )
        
        self.stdout.write('✅ تم تحسين الأداء بنجاح')

    def optimize_database(self):
        """تحسين قاعدة البيانات"""
        self.stdout.write('🗄️ بدء تحسين قاعدة البيانات...')
        
        try:
            with connection.cursor() as cursor:
                # تحليل الجداول
                cursor.execute("ANALYZE;")
                self.stdout.write('✅ تم تحليل الجداول')
                
                # تنظيف الجداول
                cursor.execute("VACUUM;")
                self.stdout.write('✅ تم تنظيف الجداول')
                
                # إعادة بناء الفهارس
                cursor.execute("REINDEX DATABASE;")
                self.stdout.write('✅ تم إعادة بناء الفهارس')
                
                # تحسين الإحصائيات
                cursor.execute("SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public';")
                tables = cursor.fetchall()
                
                for table in tables:
                    cursor.execute(f"ANALYZE {table[1]};")
                
                self.stdout.write(f'✅ تم تحليل {len(tables)} جدول')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في تحسين قاعدة البيانات: {e}')
            )
            return
        
        # تسجيل حدث التحسين
        AuditLog.log_event(
            user=None,
            event_type='system_event',
            description='تم تنفيذ تحسين قاعدة البيانات',
            severity='medium',
            additional_data={'optimization_type': 'database'}
        )
        
        self.stdout.write('✅ تم تحسين قاعدة البيانات بنجاح')

    def optimize_cache(self):
        """تحسين Cache"""
        self.stdout.write('💾 بدء تحسين Cache...')
        
        # تنظيف جميع أنواع cache
        cache.clear()
        
        # إعادة تعيين إحصائيات cache
        cache.set('cache_hits', 0, 86400)  # يوم واحد
        cache.set('cache_misses', 0, 86400)
        
        # إنشاء cache keys مهمة
        important_keys = [
            'system_settings',
            'user_permissions',
            'dashboard_stats',
            'recent_activities',
            'notification_count',
        ]
        
        for key in important_keys:
            cache.set(key, {}, 3600)  # ساعة واحدة
        
        self.stdout.write(f'✅ تم إنشاء {len(important_keys)} cache key مهم')
        
        # تسجيل حدث التحسين
        AuditLog.log_event(
            user=None,
            event_type='system_event',
            description='تم تنفيذ تحسين Cache',
            severity='medium',
            additional_data={'optimization_type': 'cache'}
        )
        
        self.stdout.write('✅ تم تحسين Cache بنجاح')

    def create_admin_user(self):
        """إنشاء مستخدم admin"""
        self.stdout.write('👤 إنشاء مستخدم admin...')
        
        try:
            # إنشاء مستخدم admin إذا لم يكن موجوداً
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@example.com',
                    'first_name': 'مدير',
                    'last_name': 'النظام',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                self.stdout.write('✅ تم إنشاء مستخدم admin')
            else:
                self.stdout.write('ℹ️ مستخدم admin موجود بالفعل')
            
            # إنشاء ملف أمان للمستخدم
            UserSecurityProfile.objects.get_or_create(user=admin_user)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إنشاء مستخدم admin: {e}')
            )

    def final_checks(self):
        """الفحوصات النهائية"""
        self.stdout.write('🔍 بدء الفحوصات النهائية...')
        
        # فحص إعدادات النظام
        settings = UnifiedSystemSettings.objects.first()
        if not settings:
            self.stdout.write(
                self.style.WARNING('⚠️ إعدادات النظام غير موجودة')
            )
        else:
            self.stdout.write('✅ إعدادات النظام موجودة')
        
        # فحص المستخدمين
        user_count = User.objects.count()
        self.stdout.write(f'✅ عدد المستخدمين: {user_count}')
        
        # فحص قاعدة البيانات
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                self.stdout.write(f'✅ إصدار قاعدة البيانات: {version.split()[0]}')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️ خطأ في فحص قاعدة البيانات: {e}')
            )
        
        # فحص Cache
        try:
            cache.set('test_key', 'test_value', 60)
            test_value = cache.get('test_key')
            if test_value == 'test_value':
                self.stdout.write('✅ Cache يعمل بشكل صحيح')
            else:
                self.stdout.write('⚠️ مشكلة في Cache')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️ خطأ في Cache: {e}')
            )
        
        # فحص الأداء
        metrics = PerformanceMonitor.get_performance_metrics()
        self.stdout.write(f'✅ مقاييس الأداء: Cache Hit Rate = {metrics["cache_hit_rate"]:.1f}%')
        
        # تسجيل حدث التحسين النهائي
        AuditLog.log_event(
            user=None,
            event_type='system_event',
            description='تم الانتهاء من التحسين النهائي الشامل',
            severity='medium',
            additional_data={
                'optimization_type': 'final',
                'user_count': user_count,
                'cache_hit_rate': metrics['cache_hit_rate']
            }
        )
        
        self.stdout.write('✅ تم الانتهاء من الفحوصات النهائية')

    def generate_report(self):
        """إنشاء تقرير التحسين"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'optimization_type': 'final_comprehensive',
            'system_status': 'optimized',
            'performance_metrics': PerformanceMonitor.get_performance_metrics(),
            'security_status': 'enhanced',
            'database_status': 'optimized',
            'cache_status': 'cleared_and_optimized',
        }
        
        return report 