from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count

User = get_user_model()

class Command(BaseCommand):
    help = 'إصلاح المستخدمين المكررين في قاعدة البيانات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض التغييرات دون تنفيذها',
        )
        parser.add_argument(
            '--fix-sessions',
            action='store_true',
            help='إصلاح جلسات المستخدمين أيضًا',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fix_sessions = options['fix_sessions']

        # إصلاح جلسات المستخدمين إذا تم طلب ذلك
        if fix_sessions:
            self.fix_sessions(dry_run)

    def fix_sessions(self, dry_run=False):
        """إصلاح جلسات المستخدمين المكررة"""
        from django.contrib.sessions.models import Session

        self.stdout.write('البحث عن جلسات المستخدمين المكررة...')

        # البحث عن مفاتيح الجلسات المكررة
        session_keys = Session.objects.values_list('session_key', flat=True)

        # البحث عن المفاتيح المكررة
        duplicate_keys = set()
        unique_keys = set()

        for key in session_keys:
            if key in unique_keys:
                duplicate_keys.add(key)
            else:
                unique_keys.add(key)

        if not duplicate_keys:
            self.stdout.write(self.style.SUCCESS('لا يوجد جلسات مكررة في قاعدة البيانات.'))
            return

        self.stdout.write(f'تم العثور على {len(duplicate_keys)} جلسة مكررة')

        # معالجة كل جلسة مكررة
        for key in duplicate_keys:
            # الحصول على جميع الجلسات بهذا المفتاح
            sessions = Session.objects.filter(session_key=key).order_by('-expire_date')

            self.stdout.write(f'معالجة الجلسة: {key}')
            self.stdout.write(f'عدد الجلسات المكررة: {sessions.count()}')

            # الاحتفاظ بأحدث جلسة وحذف البقية
            if sessions.count() > 1:
                primary_session = sessions.first()
                duplicate_sessions = sessions.exclude(id=primary_session.id)

                self.stdout.write(f'الاحتفاظ بالجلسة الأحدث (ID: {primary_session.id}) وحذف {duplicate_sessions.count()} جلسة مكررة')

                if not dry_run:
                    duplicate_sessions.delete()
                    self.stdout.write(self.style.SUCCESS(f'تم إصلاح الجلسة المكررة: {key}'))
                else:
                    self.stdout.write(self.style.WARNING('وضع المحاكاة: لم يتم تنفيذ أي تغييرات'))

        # حذف الجلسات المنتهية الصلاحية
        from django.utils import timezone
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        expired_count = expired_sessions.count()

        if expired_count > 0:
            self.stdout.write(f'تم العثور على {expired_count} جلسة منتهية الصلاحية')

            if not dry_run:
                expired_sessions.delete()
                self.stdout.write(self.style.SUCCESS(f'تم حذف {expired_count} جلسة منتهية الصلاحية'))
            else:
                self.stdout.write(self.style.WARNING('وضع المحاكاة: لم يتم تنفيذ أي تغييرات'))

        # البحث عن المستخدمين المكررين
        self.stdout.write('البحث عن المستخدمين المكررين...')

        # استخدام استعلام أكثر دقة للبحث عن المستخدمين المكررين
        duplicate_users = User.objects.values('username').annotate(
            count=Count('username')
        ).filter(count__gt=1).order_by('username')

        # استخراج أسماء المستخدمين المكررة
        duplicate_usernames = [item['username'] for item in duplicate_users]

        if not duplicate_usernames:
            self.stdout.write(self.style.SUCCESS('لا يوجد مستخدمين مكررين في قاعدة البيانات.'))
            return

        self.stdout.write(f'تم العثور على {len(duplicate_usernames)} اسم مستخدم مكرر:')

        # معالجة كل اسم مستخدم مكرر
        for username in duplicate_usernames:
            # الحصول على جميع المستخدمين بهذا الاسم
            users = User.objects.filter(username=username).order_by('id')

            self.stdout.write(f'\nمعالجة المستخدم: {username}')
            self.stdout.write(f'عدد المستخدمين المكررين: {users.count()}')

            # عرض معلومات المستخدمين
            for i, user in enumerate(users):
                self.stdout.write(f'  {i+1}. ID: {user.id}, البريد الإلكتروني: {user.email}, تاريخ الانضمام: {user.date_joined}')

            # الاحتفاظ بأول مستخدم وحذف البقية
            primary_user = users.first()
            duplicate_users = users.exclude(id=primary_user.id)

            self.stdout.write(f'الاحتفاظ بالمستخدم الأول (ID: {primary_user.id}) وحذف {duplicate_users.count()} مستخدم مكرر')

            if not dry_run:
                with transaction.atomic():
                    # نقل العلاقات من المستخدمين المكررين إلى المستخدم الأساسي
                    for dup_user in duplicate_users:
                        # نقل الأدوار
                        from accounts.models import UserRole
                        for role in UserRole.objects.filter(user=dup_user):
                            UserRole.objects.get_or_create(user=primary_user, role=role.role)

                        # نقل الأقسام
                        primary_user.departments.add(*dup_user.departments.all())

                        # تم حذف نظام الإشعارات

                        # حذف المستخدم المكرر
                        self.stdout.write(f'حذف المستخدم المكرر (ID: {dup_user.id})')
                        dup_user.delete()

                self.stdout.write(self.style.SUCCESS(f'تم إصلاح المستخدم المكرر: {username}'))
            else:
                self.stdout.write(self.style.WARNING('وضع المحاكاة: لم يتم تنفيذ أي تغييرات'))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('تم إصلاح جميع المستخدمين المكررين بنجاح.'))
        else:
            self.stdout.write(self.style.WARNING('وضع المحاكاة: لم يتم تنفيذ أي تغييرات. قم بتشغيل الأمر بدون --dry-run لتنفيذ التغييرات.'))
