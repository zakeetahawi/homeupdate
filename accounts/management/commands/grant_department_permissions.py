"""
أمر إدارة لمنح صلاحيات إدارة الأقسام للمستخدمين
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from accounts.models import Department

User = get_user_model()


class Command(BaseCommand):
    help = "Grant department management permissions to users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="Username to grant permissions to (default: all staff users)",
        )
        parser.add_argument(
            "--all-staff",
            action="store_true",
            help="Grant permissions to all staff users",
        )

    def handle(self, *args, **options):
        # الحصول على نوع المحتوى للأقسام
        content_type = ContentType.objects.get_for_model(Department)

        # الحصول على صلاحيات الأقسام
        permissions = Permission.objects.filter(content_type=content_type)

        self.stdout.write(f"Found {permissions.count()} department permissions:")
        for perm in permissions:
            self.stdout.write(f"  - {perm.codename}: {perm.name}")

        # تحديد المستخدمين
        if options["user"]:
            try:
                users = [User.objects.get(username=options["user"])]
                self.stdout.write(f"Granting permissions to user: {options['user']}")
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User '{options['user']}' not found")
                )
                return
        elif options["all_staff"]:
            users = User.objects.filter(is_staff=True)
            self.stdout.write(f"Granting permissions to {users.count()} staff users")
        else:
            # افتراضي: جميع المستخدمين الموظفين
            users = User.objects.filter(is_staff=True)
            self.stdout.write(
                f"Granting permissions to {users.count()} staff users (default)"
            )

        # منح الصلاحيات
        for user in users:
            # منح جميع صلاحيات الأقسام
            user.user_permissions.add(*permissions)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Granted department permissions to: {user.username}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully granted permissions to {users.count()} users"
            )
        )
