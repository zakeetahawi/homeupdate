from django.core.management.base import BaseCommand
from complaints.services.notification_service import notification_service


class Command(BaseCommand):
    help = 'تنظيف الإشعارات القديمة وغير الصحيحة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم تنظيفه دون تطبيق التغييرات',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🧹 بدء تنظيف الإشعارات القديمة...')
        )

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('⚠️ وضع المعاينة - لن يتم تطبيق التغييرات')
            )
            # TODO: إضافة منطق المعاينة
            return

        # تنظيف الإشعارات
        cleaned_count = notification_service.cleanup_old_notifications()

        if cleaned_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ تم تنظيف {cleaned_count} إشعار قديم بنجاح!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ لا توجد إشعارات قديمة للتنظيف')
            )

        self.stdout.write(
            self.style.SUCCESS('🎉 اكتمل تنظيف الإشعارات!')
        )
