"""
Management command لإعادة تعيين بيانات النشاط وحذف البيانات التجريبية
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import OnlineUser, UserActivityLog, UserLoginHistory, UserSession


class Command(BaseCommand):
    help = "إعادة تعيين بيانات النشاط وحذف البيانات التجريبية"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm", action="store_true", help="تأكيد حذف جميع البيانات"
        )

        parser.add_argument(
            "--keep-real-sessions",
            action="store_true",
            help="الاحتفاظ بالجلسات النشطة الحقيقية",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ هذا الأمر سيحذف جميع بيانات النشاط!\n"
                    "استخدم --confirm لتأكيد العملية"
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("🧹 بدء إعادة تعيين بيانات النشاط..."))

        # حذف سجلات النشاط
        activity_count = UserActivityLog.objects.count()
        UserActivityLog.objects.all().delete()
        self.stdout.write(f"✅ تم حذف {activity_count} سجل نشاط")

        # حذف الجلسات
        session_count = UserSession.objects.count()
        UserSession.objects.all().delete()
        self.stdout.write(f"✅ تم حذف {session_count} جلسة")

        # حذف سجلات تسجيل الدخول
        login_count = UserLoginHistory.objects.count()
        UserLoginHistory.objects.all().delete()
        self.stdout.write(f"✅ تم حذف {login_count} سجل دخول")

        if options["keep_real_sessions"]:
            # تنظيف المستخدمين غير المتصلين فقط
            offline_count = OnlineUser.objects.filter(
                last_seen__lt=timezone.now() - timezone.timedelta(minutes=5)
            ).count()
            OnlineUser.cleanup_offline_users()
            self.stdout.write(f"✅ تم حذف {offline_count} مستخدم غير متصل")
        else:
            # حذف جميع المستخدمين النشطين
            online_count = OnlineUser.objects.count()
            OnlineUser.objects.all().delete()
            self.stdout.write(f"✅ تم حذف {online_count} مستخدم نشط")

        self.stdout.write(
            self.style.SUCCESS(
                "🎉 تم إعادة تعيين بيانات النشاط بنجاح!\n"
                "الآن سيتم تسجيل النشاط الفعلي للمستخدمين فقط."
            )
        )
