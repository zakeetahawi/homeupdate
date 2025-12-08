"""
أمر لحذف الجلسات القديمة والمنتهية بسرعة
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.sessions.models import Session
from user_activity.models import UserSession
from datetime import timedelta


class Command(BaseCommand):
    help = 'حذف الجلسات القديمة والمنتهية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=2,
            help='حذف الجلسات الأقدم من عدد الساعات المحدد (الافتراضي: 2)'
        )
        parser.add_argument(
            '--all-inactive',
            action='store_true',
            help='حذف جميع الجلسات غير النشطة'
        )
        parser.add_argument(
            '--django-sessions',
            action='store_true',
            help='حذف جلسات Django المنتهية'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم حذفه دون تنفيذ الحذف'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🧹 تنظيف الجلسات'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        total_deleted = 0
        
        # 1. حذف جلسات Django المنتهية
        if options['django_sessions']:
            self.stdout.write('\n📊 فحص جلسات Django...')
            expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
            count = expired_sessions.count()
            
            if count > 0:
                self.stdout.write(f'⏰ تم العثور على {count:,} جلسة منتهية')
                if not dry_run:
                    # حذف مباشر دون signals
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM django_session WHERE expire_date < NOW()")
                        deleted = cursor.rowcount
                    self.stdout.write(self.style.SUCCESS(f'✅ تم حذف {deleted:,} جلسة Django'))
                    total_deleted += deleted
                else:
                    self.stdout.write(self.style.WARNING(f'🔍 سيتم حذف {count:,} جلسة Django'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ لا توجد جلسات Django منتهية'))
        
        # 2. حذف جلسات UserSession غير النشطة
        if options['all_inactive']:
            self.stdout.write('\n📊 فحص جلسات UserSession غير النشطة...')
            inactive = UserSession.objects.filter(is_active=False)
            count = inactive.count()
            
            if count > 0:
                self.stdout.write(f'⏰ تم العثور على {count:,} جلسة غير نشطة')
                if not dry_run:
                    # حذف مباشر
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM user_activity_usersession WHERE is_active = FALSE")
                        deleted = cursor.rowcount
                    self.stdout.write(self.style.SUCCESS(f'✅ تم حذف {deleted:,} جلسة غير نشطة'))
                    total_deleted += deleted
                else:
                    self.stdout.write(self.style.WARNING(f'🔍 سيتم حذف {count:,} جلسة غير نشطة'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ لا توجد جلسات غير نشطة'))
        
        # 3. حذف الجلسات القديمة
        self.stdout.write(f'\n📊 فحص الجلسات الأقدم من {hours} ساعة...')
        cutoff_time = timezone.now() - timedelta(hours=hours)
        old_sessions = UserSession.objects.filter(last_activity__lt=cutoff_time)
        count = old_sessions.count()
        
        if count > 0:
            self.stdout.write(f'⏰ تم العثور على {count:,} جلسة قديمة')
            if not dry_run:
                # حذف مباشر
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM user_activity_usersession WHERE last_activity < %s",
                        [cutoff_time]
                    )
                    deleted = cursor.rowcount
                self.stdout.write(self.style.SUCCESS(f'✅ تم حذف {deleted:,} جلسة قديمة'))
                total_deleted += deleted
            else:
                self.stdout.write(self.style.WARNING(f'🔍 سيتم حذف {count:,} جلسة قديمة'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ لا توجد جلسات أقدم من {hours} ساعة'))
        
        # الملخص
        self.stdout.write('\n' + '=' * 70)
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 وضع المحاكاة (Dry Run) - لم يتم حذف شيء'))
            self.stdout.write(self.style.WARNING('قم بإزالة --dry-run لتنفيذ الحذف فعلياً'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ تم حذف {total_deleted:,} جلسة إجمالاً'))
            self.stdout.write(self.style.SUCCESS('🎉 اكتمل التنظيف بنجاح!'))
        self.stdout.write('=' * 70)
        
        # نصائح
        self.stdout.write('\n💡 نصائح:')
        self.stdout.write('  • استخدم --hours=24 لحذف الجلسات الأقدم من 24 ساعة')
        self.stdout.write('  • استخدم --all-inactive لحذف جميع الجلسات غير النشطة')
        self.stdout.write('  • استخدم --django-sessions لحذف جلسات Django المنتهية')
        self.stdout.write('  • استخدم --dry-run لمعاينة ما سيتم حذفه\n')
