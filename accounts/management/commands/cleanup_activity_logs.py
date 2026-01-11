"""
Management command لتنظيف سجلات النشاط القديمة
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import OnlineUser, UserActivityLog, UserLoginHistory, UserSession


class Command(BaseCommand):
    help = "تنظيف سجلات النشاط القديمة والجلسات المنتهية"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=getattr(settings, "ACTIVITY_TRACKING", {}).get("CLEANUP_DAYS", 30),
            help="عدد الأيام للاحتفاظ بالسجلات (افتراضي: 30)",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض ما سيتم حذفه دون تنفيذ الحذف الفعلي",
        )

        parser.add_argument(
            "--cleanup-online-users",
            action="store_true",
            help="تنظيف المستخدمين غير المتصلين من قائمة النشطين",
        )

        parser.add_argument(
            "--cleanup-sessions", action="store_true", help="تنظيف الجلسات المنتهية"
        )

        parser.add_argument(
            "--cleanup-activity-logs",
            action="store_true",
            help="تنظيف سجلات النشاط القديمة",
        )

        parser.add_argument(
            "--cleanup-login-history",
            action="store_true",
            help="تنظيف سجلات تسجيل الدخول القديمة",
        )

        parser.add_argument(
            "--all", action="store_true", help="تنظيف جميع البيانات القديمة"
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cleanup_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.SUCCESS(f"🧹 بدء تنظيف سجلات النشاط الأقدم من {days} يوم")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️ وضع المعاينة - لن يتم حذف أي بيانات فعلياً")
            )

        total_deleted = 0

        # تنظيف المستخدمين غير المتصلين
        if options["cleanup_online_users"] or options["all"]:
            total_deleted += self.cleanup_online_users(dry_run)

        # تنظيف الجلسات المنتهية
        if options["cleanup_sessions"] or options["all"]:
            total_deleted += self.cleanup_expired_sessions(cleanup_date, dry_run)

        # تنظيف سجلات النشاط القديمة
        if options["cleanup_activity_logs"] or options["all"]:
            total_deleted += self.cleanup_activity_logs(cleanup_date, dry_run)

        # تنظيف سجلات تسجيل الدخول القديمة
        if options["cleanup_login_history"] or options["all"]:
            total_deleted += self.cleanup_login_history(cleanup_date, dry_run)

        # إذا لم يتم تحديد أي خيار، تنظيف كل شيء
        if not any(
            [
                options["cleanup_online_users"],
                options["cleanup_sessions"],
                options["cleanup_activity_logs"],
                options["cleanup_login_history"],
                options["all"],
            ]
        ):
            total_deleted += self.cleanup_online_users(dry_run)
            total_deleted += self.cleanup_expired_sessions(cleanup_date, dry_run)
            total_deleted += self.cleanup_activity_logs(cleanup_date, dry_run)
            total_deleted += self.cleanup_login_history(cleanup_date, dry_run)

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"✅ المعاينة مكتملة - سيتم حذف {total_deleted} سجل")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✅ التنظيف مكتمل - تم حذف {total_deleted} سجل")
            )

    def cleanup_online_users(self, dry_run=False):
        """تنظيف المستخدمين غير المتصلين"""
        timeout_minutes = getattr(settings, "ACTIVITY_TRACKING", {}).get(
            "ONLINE_TIMEOUT_MINUTES", 5
        )
        timeout_date = timezone.now() - timedelta(minutes=timeout_minutes)

        offline_users = OnlineUser.objects.filter(last_seen__lt=timeout_date)
        count = offline_users.count()

        if count > 0:
            self.stdout.write(f"🔄 تنظيف {count} مستخدم غير متصل...")
            if not dry_run:
                offline_users.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ تم حذف {count} مستخدم غير متصل")
                )
        else:
            self.stdout.write("ℹ️ لا توجد مستخدمون غير متصلون للحذف")

        return count

    def cleanup_expired_sessions(self, cleanup_date, dry_run=False):
        """تنظيف الجلسات المنتهية"""
        expired_sessions = UserSession.objects.filter(last_activity__lt=cleanup_date)
        count = expired_sessions.count()

        if count > 0:
            self.stdout.write(f"🔄 تنظيف {count} جلسة منتهية...")
            if not dry_run:
                expired_sessions.delete()
                self.stdout.write(self.style.SUCCESS(f"✅ تم حذف {count} جلسة منتهية"))
        else:
            self.stdout.write("ℹ️ لا توجد جلسات منتهية للحذف")

        return count

    def cleanup_activity_logs(self, cleanup_date, dry_run=False):
        """تنظيف سجلات النشاط القديمة"""
        old_logs = UserActivityLog.objects.filter(timestamp__lt=cleanup_date)
        count = old_logs.count()

        if count > 0:
            self.stdout.write(f"🔄 تنظيف {count} سجل نشاط قديم...")
            if not dry_run:
                # حذف على دفعات لتجنب مشاكل الذاكرة
                batch_size = 1000
                deleted_total = 0

                while True:
                    batch = list(old_logs[:batch_size])
                    if not batch:
                        break

                    UserActivityLog.objects.filter(
                        id__in=[log.id for log in batch]
                    ).delete()

                    deleted_total += len(batch)
                    self.stdout.write(f"  📦 تم حذف {deleted_total} من {count} سجل...")

                self.stdout.write(
                    self.style.SUCCESS(f"✅ تم حذف {count} سجل نشاط قديم")
                )
        else:
            self.stdout.write("ℹ️ لا توجد سجلات نشاط قديمة للحذف")

        return count

    def cleanup_login_history(self, cleanup_date, dry_run=False):
        """تنظيف سجلات تسجيل الدخول القديمة"""
        old_logins = UserLoginHistory.objects.filter(login_time__lt=cleanup_date)
        count = old_logins.count()

        if count > 0:
            self.stdout.write(f"🔄 تنظيف {count} سجل دخول قديم...")
            if not dry_run:
                old_logins.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ تم حذف {count} سجل دخول قديم")
                )
        else:
            self.stdout.write("ℹ️ لا توجد سجلات دخول قديمة للحذف")

        return count

    def cleanup_excessive_logs_per_user(self, dry_run=False):
        """تنظيف السجلات الزائدة لكل مستخدم"""
        max_logs = getattr(settings, "ACTIVITY_TRACKING", {}).get(
            "MAX_ACTIVITY_LOGS_PER_USER", 1000
        )

        from django.db.models import Count

        from accounts.models import User

        users_with_excess_logs = User.objects.annotate(
            log_count=Count("activity_logs")
        ).filter(log_count__gt=max_logs)

        total_deleted = 0

        for user in users_with_excess_logs:
            # الاحتفاظ بأحدث السجلات وحذف الباقي
            logs_to_delete = UserActivityLog.objects.filter(user=user).order_by(
                "-timestamp"
            )[max_logs:]

            count = logs_to_delete.count()
            if count > 0:
                self.stdout.write(
                    f"🔄 تنظيف {count} سجل زائد للمستخدم {user.username}..."
                )
                if not dry_run:
                    logs_to_delete.delete()
                total_deleted += count

        if total_deleted > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ تم حذف {total_deleted} سجل زائد"))
        else:
            self.stdout.write("ℹ️ لا توجد سجلات زائدة للحذف")

        return total_deleted
