"""
أمر Django لتنظيف البيانات القديمة
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

from installations.models_new import InstallationAlert, DailyInstallationReport

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'تنظيف البيانات القديمة من النظام'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alerts-days',
            type=int,
            default=90,
            help='عدد الأيام للاحتفاظ بالإنذارات المحلولة (افتراضي: 90)',
        )
        parser.add_argument(
            '--reports-days',
            type=int,
            default=365,
            help='عدد الأيام للاحتفاظ بالتقارير اليومية (افتراضي: 365)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم حذفه بدون تنفيذ الحذف الفعلي',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='تنفيذ التنظيف بدون تأكيد',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('بدء تنظيف البيانات القديمة...')
        )

        try:
            alerts_days = options['alerts_days']
            reports_days = options['reports_days']
            dry_run = options['dry_run']
            force = options['force']

            # حساب التواريخ الحدية
            alerts_cutoff = timezone.now() - timedelta(days=alerts_days)
            reports_cutoff = timezone.now().date() - timedelta(days=reports_days)

            self.stdout.write(f'تنظيف الإنذارات أقدم من: {alerts_cutoff.date()}')
            self.stdout.write(f'تنظيف التقارير أقدم من: {reports_cutoff}')

            # تنظيف الإنذارات القديمة
            alerts_deleted = self.cleanup_old_alerts(alerts_cutoff, dry_run)
            
            # تنظيف التقارير القديمة
            reports_deleted = self.cleanup_old_reports(reports_cutoff, dry_run)

            # عرض النتائج
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('تشغيل تجريبي - لم يتم حذف أي بيانات')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('تم تنظيف البيانات بنجاح')
                )

            self.stdout.write(f'الإنذارات المحذوفة: {alerts_deleted}')
            self.stdout.write(f'التقارير المحذوفة: {reports_deleted}')

            # تسجيل العملية
            logger.info(
                f'تنظيف البيانات: {alerts_deleted} إنذار، {reports_deleted} تقرير'
            )

        except Exception as e:
            error_msg = f'خطأ في تنظيف البيانات: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise

    def cleanup_old_alerts(self, cutoff_date, dry_run=False):
        """تنظيف الإنذارات القديمة المحلولة"""
        
        # البحث عن الإنذارات القديمة المحلولة
        old_alerts = InstallationAlert.objects.filter(
            created_at__lt=cutoff_date,
            is_resolved=True
        )

        count = old_alerts.count()
        
        if count == 0:
            self.stdout.write('لا توجد إنذارات قديمة للحذف')
            return 0

        self.stdout.write(f'تم العثور على {count} إنذار قديم محلول')

        # عرض تفاصيل الإنذارات إذا كان العدد قليل
        if count <= 10:
            for alert in old_alerts:
                self.stdout.write(
                    f'  - {alert.title} ({alert.created_at.date()})'
                )

        if not dry_run:
            # تأكيد الحذف
            if count > 100:
                self.stdout.write(
                    self.style.WARNING(
                        f'سيتم حذف {count} إنذار. هذا عدد كبير!'
                    )
                )
                confirm = input('هل تريد المتابعة؟ (yes/no): ')
                if confirm.lower() not in ['yes', 'y', 'نعم']:
                    self.stdout.write('تم إلغاء العملية')
                    return 0

            # تنفيذ الحذف
            deleted_count, _ = old_alerts.delete()
            return deleted_count

        return count

    def cleanup_old_reports(self, cutoff_date, dry_run=False):
        """تنظيف التقارير اليومية القديمة"""
        
        # البحث عن التقارير القديمة
        old_reports = DailyInstallationReport.objects.filter(
            report_date__lt=cutoff_date
        )

        count = old_reports.count()
        
        if count == 0:
            self.stdout.write('لا توجد تقارير قديمة للحذف')
            return 0

        self.stdout.write(f'تم العثور على {count} تقرير قديم')

        # عرض تفاصيل التقارير إذا كان العدد قليل
        if count <= 10:
            for report in old_reports:
                self.stdout.write(
                    f'  - تقرير {report.report_date} ({report.total_installations} تركيب)'
                )

        if not dry_run:
            # تأكيد الحذف
            if count > 50:
                self.stdout.write(
                    self.style.WARNING(
                        f'سيتم حذف {count} تقرير. هذا عدد كبير!'
                    )
                )
                confirm = input('هل تريد المتابعة؟ (yes/no): ')
                if confirm.lower() not in ['yes', 'y', 'نعم']:
                    self.stdout.write('تم إلغاء العملية')
                    return 0

            # تنفيذ الحذف
            deleted_count, _ = old_reports.delete()
            return deleted_count

        return count

    def cleanup_old_sessions(self, days=30, dry_run=False):
        """تنظيف جلسات المستخدمين القديمة"""
        
        try:
            from django.contrib.sessions.models import Session
            
            cutoff_date = timezone.now() - timedelta(days=days)
            old_sessions = Session.objects.filter(expire_date__lt=cutoff_date)
            
            count = old_sessions.count()
            
            if count == 0:
                return 0
            
            self.stdout.write(f'تم العثور على {count} جلسة منتهية الصلاحية')
            
            if not dry_run:
                deleted_count, _ = old_sessions.delete()
                return deleted_count
            
            return count
            
        except ImportError:
            # جدول الجلسات غير متاح
            return 0

    def cleanup_old_logs(self, days=180, dry_run=False):
        """تنظيف سجلات النظام القديمة"""
        
        # يمكن إضافة تنظيف سجلات مخصصة هنا
        # مثل سجلات التغييرات أو سجلات الأخطاء
        
        return 0

    def get_database_size_info(self):
        """الحصول على معلومات حجم قاعدة البيانات"""
        
        try:
            from django.db import connection
            
            with connection.cursor() as cursor:
                # استعلام حجم قاعدة البيانات (PostgreSQL)
                if 'postgresql' in connection.vendor:
                    cursor.execute("""
                        SELECT pg_size_pretty(pg_database_size(current_database()))
                    """)
                    size = cursor.fetchone()[0]
                    self.stdout.write(f'حجم قاعدة البيانات: {size}')
                
                # استعلام حجم الجداول
                cursor.execute("""
                    SELECT 
                        table_name,
                        table_rows
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                    AND table_name LIKE 'installations_%'
                    ORDER BY table_rows DESC
                """)
                
                self.stdout.write('\nأحجام جداول التركيبات:')
                for table_name, row_count in cursor.fetchall():
                    if row_count:
                        self.stdout.write(f'  {table_name}: {row_count:,} سجل')
                        
        except Exception as e:
            self.stdout.write(f'لا يمكن الحصول على معلومات قاعدة البيانات: {e}')

    def optimize_database(self):
        """تحسين قاعدة البيانات"""
        
        try:
            from django.db import connection
            
            with connection.cursor() as cursor:
                if 'postgresql' in connection.vendor:
                    # تحليل وتحسين الجداول
                    tables = [
                        'installations_installationnew',
                        'installations_installationalert',
                        'installations_dailyinstallationreport'
                    ]
                    
                    for table in tables:
                        cursor.execute(f'ANALYZE {table}')
                        self.stdout.write(f'تم تحليل جدول {table}')
                
                elif 'mysql' in connection.vendor:
                    # تحسين الجداول
                    cursor.execute('OPTIMIZE TABLE installations_installationnew')
                    cursor.execute('OPTIMIZE TABLE installations_installationalert')
                    cursor.execute('OPTIMIZE TABLE installations_dailyinstallationreport')
                    self.stdout.write('تم تحسين الجداول')
                    
        except Exception as e:
            self.stdout.write(f'خطأ في تحسين قاعدة البيانات: {e}')
