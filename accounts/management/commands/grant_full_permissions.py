"""
أمر إدارة لمنح صلاحيات كاملة للمستخدمين
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Grant full system permissions to users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="Username to grant full permissions to",
        )
        parser.add_argument(
            "--all-staff",
            action="store_true",
            help="Grant full permissions to all staff users",
        )
        parser.add_argument(
            "--create-superuser-group",
            action="store_true",
            help="Create a superuser group with all permissions",
        )

    def handle(self, *args, **options):
        # إنشاء مجموعة المديرين الكاملة
        if options["create_superuser_group"]:
            self.create_superuser_group()

        # تحديد المستخدمين
        if options["user"]:
            try:
                users = [User.objects.get(username=options["user"])]
                self.stdout.write(
                    f"Granting full permissions to user: {options['user']}"
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User '{options['user']}' not found")
                )
                return
        elif options["all_staff"]:
            users = User.objects.filter(is_staff=True)
            self.stdout.write(
                f"Granting full permissions to {users.count()} staff users"
            )
        else:
            # افتراضي: جميع المستخدمين الموظفين
            users = User.objects.filter(is_staff=True)
            self.stdout.write(
                f"Granting full permissions to {users.count()} staff users (default)"
            )

        # منح الصلاحيات الكاملة
        self.grant_full_permissions(users)

    def create_superuser_group(self):
        """إنشاء مجموعة المديرين الكاملة"""
        group, created = Group.objects.get_or_create(name="مديرين كاملين")

        if created:
            self.stdout.write(self.style.SUCCESS("تم إنشاء مجموعة 'مديرين كاملين'"))

        # إضافة جميع الصلاحيات للمجموعة
        all_permissions = Permission.objects.all()
        group.permissions.set(all_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f"تم إضافة {all_permissions.count()} صلاحية لمجموعة 'مديرين كاملين'"
            )
        )

        return group

    def grant_full_permissions(self, users):
        """منح صلاحيات كاملة للمستخدمين"""
        # الحصول على جميع الصلاحيات
        all_permissions = Permission.objects.all()

        self.stdout.write(
            f"Found {all_permissions.count()} total permissions in system"
        )

        # إنشاء مجموعة المديرين الكاملة
        superuser_group = self.create_superuser_group()

        for user in users:
            # جعل المستخدم موظف ومدير
            user.is_staff = True
            user.is_superuser = True
            user.save()

            # إضافة جميع الصلاحيات المباشرة
            user.user_permissions.set(all_permissions)

            # إضافة المستخدم لمجموعة المديرين الكاملة
            user.groups.add(superuser_group)

            self.stdout.write(
                self.style.SUCCESS(f"✅ منح صلاحيات كاملة للمستخدم: {user.username}")
            )
            self.stdout.write(f"   - is_staff: {user.is_staff}")
            self.stdout.write(f"   - is_superuser: {user.is_superuser}")
            self.stdout.write(f"   - صلاحيات مباشرة: {user.user_permissions.count()}")
            self.stdout.write(f"   - مجموعات: {user.groups.count()}")

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 تم منح صلاحيات كاملة لـ {users.count()} مستخدم بنجاح!"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "⚠️  تحذير: هؤلاء المستخدمون لديهم الآن صلاحيات كاملة للنظام بما في ذلك:"
            )
        )
        self.stdout.write("   - حذف الأقسام الأساسية")
        self.stdout.write("   - تعديل جميع البيانات")
        self.stdout.write("   - إدارة المستخدمين والصلاحيات")
        self.stdout.write("   - الوصول لجميع أجزاء النظام")
