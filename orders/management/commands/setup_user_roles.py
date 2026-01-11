"""
أمر إدارة لإعداد أدوار المستخدمين والصلاحيات
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "إعداد أدوار المستخدمين والصلاحيات"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id", type=int, help="معرف المستخدم لتطبيق الدور عليه"
        )
        parser.add_argument(
            "--role",
            type=str,
            choices=[
                "salesperson",
                "branch_manager",
                "region_manager",
                "general_manager",
            ],
            help="نوع الدور المراد تطبيقه",
        )
        parser.add_argument("--branch-id", type=int, help="معرف الفرع (للمدير الفرع)")
        parser.add_argument(
            "--managed-branches",
            nargs="+",
            type=int,
            help="معرفات الفروع المُدارة (لمدير المنطقة)",
        )

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        role = options.get("role")
        branch_id = options.get("branch_id")
        managed_branches = options.get("managed_branches", [])

        if not user_id or not role:
            self.stdout.write(self.style.ERROR("يجب تحديد معرف المستخدم ونوع الدور"))
            return

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"المستخدم بالمعرف {user_id} غير موجود"))
            return

        # إزالة جميع الأدوار السابقة
        user.is_salesperson = False
        user.is_branch_manager = False
        user.is_region_manager = False
        user.is_sales_manager = False
        user.managed_branches.clear()

        # تطبيق الدور الجديد
        if role == "salesperson":
            user.is_salesperson = True
            self.stdout.write(self.style.SUCCESS(f"تم تعيين {user.username} كبائع"))

        elif role == "branch_manager":
            user.is_branch_manager = True
            if branch_id:
                from accounts.models import Branch

                try:
                    branch = Branch.objects.get(id=branch_id)
                    user.branch = branch
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"تم تعيين {user.username} كمدير فرع {branch.name}"
                        )
                    )
                except Branch.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"الفرع بالمعرف {branch_id} غير موجود")
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"تم تعيين {user.username} كمدير فرع (بدون فرع محدد)"
                    )
                )

        elif role == "region_manager":
            user.is_region_manager = True
            if managed_branches:
                from accounts.models import Branch

                branches = Branch.objects.filter(id__in=managed_branches)
                user.managed_branches.set(branches)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"تم تعيين {user.username} كمدير منطقة مسؤول عن {branches.count()} فرع"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"تم تعيين {user.username} كمدير منطقة (بدون فروع محددة)"
                    )
                )

        elif role == "general_manager":
            user.is_sales_manager = True
            self.stdout.write(self.style.SUCCESS(f"تم تعيين {user.username} كمدير عام"))

        user.save()

        # إضافة الصلاحيات المناسبة
        self._assign_permissions(user, role)

        self.stdout.write(self.style.SUCCESS("تم إعداد الدور والصلاحيات بنجاح!"))

    def _assign_permissions(self, user, role):
        """إضافة الصلاحيات المناسبة للدور"""
        # الحصول على صلاحيات الطلبات
        from orders.models import Order

        content_type = ContentType.objects.get_for_model(Order)

        # إزالة جميع الصلاحيات السابقة
        user.user_permissions.clear()

        if role == "salesperson":
            # البائع: عرض وإضافة وتعديل طلباته فقط
            permissions = [
                "view_order",
                "add_order",
                "change_order",
            ]
        elif role == "branch_manager":
            # مدير الفرع: جميع الصلاحيات على طلبات فرعه
            permissions = [
                "view_order",
                "add_order",
                "change_order",
                "delete_order",
            ]
        elif role == "region_manager":
            # مدير المنطقة: جميع الصلاحيات على طلبات فروعه
            permissions = [
                "view_order",
                "add_order",
                "change_order",
                "delete_order",
            ]
        elif role == "general_manager":
            # المدير العام: جميع الصلاحيات
            permissions = [
                "view_order",
                "add_order",
                "change_order",
                "delete_order",
            ]
        else:
            permissions = []

        # إضافة ال��لاحيات
        for perm_codename in permissions:
            try:
                permission = Permission.objects.get(
                    codename=perm_codename, content_type=content_type
                )
                user.user_permissions.add(permission)
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"الصلاحية {perm_codename} غير موجودة")
                )

        self.stdout.write(
            self.style.SUCCESS(f"تم إضافة {len(permissions)} صلاحية للمستخدم")
        )
