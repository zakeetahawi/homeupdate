"""
أمر Django لإعداد صلاحيات نظام الشكاوى
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from accounts.models import User
from complaints.models import Complaint, ComplaintUserPermissions


class Command(BaseCommand):
    help = "إعداد صلاحيات نظام الشكاوى والمجموعات المطلوبة"

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-groups",
            action="store_true",
            help="إنشاء المجموعات المطلوبة",
        )
        parser.add_argument(
            "--assign-users",
            action="store_true",
            help="إسناد المستخدمين إلى المجموعات",
        )
        parser.add_argument(
            "--setup-permissions",
            action="store_true",
            help="إعداد الصلاحيات للمجموعات",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="تنفيذ جميع العمليات",
        )

    def handle(self, *args, **options):
        if options["all"]:
            options["create_groups"] = True
            options["assign_users"] = True
            options["setup_permissions"] = True

        if options["create_groups"]:
            self.create_groups()

        if options["setup_permissions"]:
            self.setup_permissions()

        if options["assign_users"]:
            self.assign_users()

        self.stdout.write(self.style.SUCCESS("✅ تم إعداد صلاحيات نظام الشكاوى بنجاح"))

    def create_groups(self):
        """إنشاء المجموعات المطلوبة"""
        self.stdout.write("🔧 إنشاء المجموعات المطلوبة...")

        groups_to_create = [
            ("Complaints_Supervisors", "مشرفو الشكاوى"),
            ("Managers", "المدراء"),
            ("Complaints_Managers", "مدراء الشكاوى"),
            ("Complaints_Staff", "موظفو الشكاوى"),
        ]

        for group_name, description in groups_to_create:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"  ✅ تم إنشاء مجموعة: {group_name}")
            else:
                self.stdout.write(f"  ℹ️  المجموعة موجودة مسبقاً: {group_name}")

    def setup_permissions(self):
        """إعداد الصلاحيات للمجموعات"""
        self.stdout.write("🔧 إعداد الصلاحيات للمجموعات...")

        # الحصول على نوع المحتوى للشكاوى
        complaint_content_type = ContentType.objects.get_for_model(Complaint)

        # الصلاحيات المطلوبة
        permissions_to_create = [
            ("view_complaint", "Can view complaint"),
            ("add_complaint", "Can add complaint"),
            ("change_complaint", "Can change complaint"),
            ("delete_complaint", "Can delete complaint"),
            ("can_assign_complaints", "Can assign complaints"),
            ("can_escalate_complaints", "Can escalate complaints"),
            ("can_resolve_complaints", "Can resolve complaints"),
        ]

        # إنشاء الصلاحيات إذا لم تكن موجودة
        for codename, name in permissions_to_create:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=complaint_content_type,
                defaults={"name": name},
            )
            if created:
                self.stdout.write(f"  ✅ تم إنشاء صلاحية: {name}")

        # إسناد الصلاحيات للمجموعات
        self.assign_permissions_to_groups()

    def assign_permissions_to_groups(self):
        """إسناد الصلاحيات للمجموعات"""
        complaint_content_type = ContentType.objects.get_for_model(Complaint)

        # صلاحيات المشرفين والمدراء (جميع الصلاحيات)
        admin_permissions = Permission.objects.filter(
            content_type=complaint_content_type
        )

        # صلاحيات الموظفين (عرض وإضافة وتعديل فقط)
        staff_permissions = Permission.objects.filter(
            content_type=complaint_content_type,
            codename__in=["view_complaint", "add_complaint", "change_complaint"],
        )

        # إسناد الصلاحيات
        groups_permissions = {
            "Complaints_Supervisors": admin_permissions,
            "Managers": admin_permissions,
            "Complaints_Managers": admin_permissions,
            "Complaints_Staff": staff_permissions,
        }

        for group_name, permissions in groups_permissions.items():
            try:
                group = Group.objects.get(name=group_name)
                group.permissions.set(permissions)
                self.stdout.write(f"  ✅ تم إسناد الصلاحيات لمجموعة: {group_name}")
            except Group.DoesNotExist:
                self.stdout.write(f"  ❌ المجموعة غير موجودة: {group_name}")

    def assign_users(self):
        """إسناد المستخدمين إلى المجموعات"""
        self.stdout.write("🔧 إسناد المستخدمين إلى المجموعات...")

        # الحصول على المجموعات
        try:
            supervisors_group = Group.objects.get(name="Complaints_Supervisors")
            managers_group = Group.objects.get(name="Managers")
            complaints_managers_group = Group.objects.get(name="Complaints_Managers")
            staff_group = Group.objects.get(name="Complaints_Staff")
        except Group.DoesNotExist as e:
            self.stdout.write(f"❌ خطأ: {e}")
            return

        # إضافة المستخدمين الإداريين وتحديث صلاحياتهم
        admin_users = User.objects.filter(
            complaint_permissions__can_edit_all_complaints=True,
            complaint_permissions__is_active=True,
        )

        for user in admin_users:
            user.groups.add(
                supervisors_group, managers_group, complaints_managers_group
            )
            # تحديث الصلاحيات الجديدة
            permissions = user.complaint_permissions
            permissions.can_escalate_complaints = True
            permissions.can_assign_complaints = True
            permissions.can_resolve_complaints = True
            permissions.can_close_complaints = True
            permissions.can_delete_complaints = True
            permissions.can_change_complaint_status = True
            permissions.save()
            self.stdout.write(
                f"  ✅ تم إضافة {user.username} إلى مجموعات الإدارة وتحديث صلاحياته"
            )

        # إضافة المستخدمين الذين يمكن إسناد الشكاوى إليهم
        staff_users = User.objects.filter(
            complaint_permissions__can_be_assigned_complaints=True,
            complaint_permissions__is_active=True,
        ).exclude(complaint_permissions__can_edit_all_complaints=True)

        for user in staff_users:
            user.groups.add(staff_group)
            self.stdout.write(f"  ✅ تم إضافة {user.username} إلى مجموعة الموظفين")

        # إضافة المستخدمين الإداريين (superuser)
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            user.groups.add(
                supervisors_group, managers_group, complaints_managers_group
            )
            self.stdout.write(
                f"  ✅ تم إضافة المدير {user.username} إلى جميع المجموعات"
            )

        # عرض الإحصائيات
        self.show_statistics()

    def show_statistics(self):
        """عرض إحصائيات المجموعات"""
        self.stdout.write("\n📊 إحصائيات المجموعات:")

        groups = [
            "Complaints_Supervisors",
            "Managers",
            "Complaints_Managers",
            "Complaints_Staff",
        ]
        for group_name in groups:
            try:
                group = Group.objects.get(name=group_name)
                count = group.user_set.count()
                self.stdout.write(f"  - {group_name}: {count} مستخدم")
            except Group.DoesNotExist:
                self.stdout.write(f"  - {group_name}: غير موجود")

        # إحصائيات الصلاحيات
        total_permissions = ComplaintUserPermissions.objects.filter(
            is_active=True
        ).count()
        self.stdout.write(
            f"\n📋 إجمالي المستخدمين الذين لديهم صلاحيات شكاوى: {total_permissions}"
        )
