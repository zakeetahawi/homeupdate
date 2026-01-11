"""
أمر Django لإصلاح مشاكل الأداء في نظام الشكاوى
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import connection

from accounts.models import User
from complaints.models import ComplaintUserPermissions


class Command(BaseCommand):
    help = "إصلاح مشاكل الأداء والصلاحيات في نظام الشكاوى"

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-indexes",
            action="store_true",
            help="إنشاء فهارس قاعدة البيانات لتحسين الأداء",
        )
        parser.add_argument(
            "--fix-permissions",
            action="store_true",
            help="إصلاح صلاحيات المستخدمين",
        )
        parser.add_argument(
            "--create-groups",
            action="store_true",
            help="إنشاء المجموعات المطلوبة",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="تطبيق جميع الإصلاحات",
        )

    def handle(self, *args, **options):
        if options["all"]:
            options["create_indexes"] = True
            options["fix_permissions"] = True
            options["create_groups"] = True

        if options["create_groups"]:
            self.create_required_groups()

        if options["fix_permissions"]:
            self.fix_user_permissions()

        if options["create_indexes"]:
            self.create_database_indexes()

        self.stdout.write(self.style.SUCCESS("تم إصلاح مشاكل الأداء والصلاحيات بنجاح!"))

    def create_required_groups(self):
        """إنشاء المجموعات المطلوبة لنظام الشكاوى"""
        self.stdout.write("إنشاء المجموعات المطلوبة...")

        groups = [
            "Complaints_Managers",
            "Complaints_Supervisors",
            "Managers",
            "Complaints_Staff",
        ]

        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"تم إنشاء المجموعة: {group_name}")
            else:
                self.stdout.write(f"المجموعة موجودة: {group_name}")

    def fix_user_permissions(self):
        """إصلاح صلاحيات المستخدمين"""
        self.stdout.write("إصلاح صلاحيات المستخدمين...")

        # إنشاء صلاحيات للمستخدمين الذين ليس لديهم صلاحيات
        users_without_permissions = User.objects.exclude(
            id__in=ComplaintUserPermissions.objects.values_list("user_id", flat=True)
        )

        for user in users_without_permissions:
            # تحديد الصلاحيات بناءً على المجموعات
            is_admin = user.groups.filter(
                name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
            ).exists()

            permissions = ComplaintUserPermissions.objects.create(
                user=user,
                can_be_assigned_complaints=True,
                can_escalate_complaints=is_admin,
                can_assign_complaints=is_admin,
                can_view_all_complaints=is_admin,
                can_edit_all_complaints=is_admin,
                can_resolve_complaints=True,
                can_close_complaints=is_admin,
                can_delete_complaints=is_admin,
                is_active=True,
            )

            self.stdout.write(f"تم إنشاء صلاحيات للمستخدم: {user.username}")

        # تحديث صلاحيات المستخدمين الموجودين
        existing_permissions = ComplaintUserPermissions.objects.all()
        for perm in existing_permissions:
            user = perm.user
            is_admin = user.groups.filter(
                name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
            ).exists()

            if is_admin and not perm.can_edit_all_complaints:
                perm.can_edit_all_complaints = True
                perm.can_view_all_complaints = True
                perm.can_assign_complaints = True
                perm.can_escalate_complaints = True
                perm.can_close_complaints = True
                perm.save()
                self.stdout.write(f"تم تحديث صلاحيات المدير: {user.username}")

    def create_database_indexes(self):
        """إنشاء فهارس قاعدة البيانات لتحسين الأداء"""
        self.stdout.write("إنشاء فهارس قاعدة البيانات...")

        indexes = [
            # فهارس للشكاوى
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_status_created 
            ON complaints_complaint(status, created_at DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_customer_status 
            ON complaints_complaint(customer_id, status);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_assigned_status 
            ON complaints_complaint(assigned_to_id, status) 
            WHERE assigned_to_id IS NOT NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_deadline_status 
            ON complaints_complaint(deadline, status) 
            WHERE status IN ('new', 'in_progress');
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_type_created 
            ON complaints_complaint(complaint_type_id, created_at DESC);
            """,
            # فهارس للتحديثات
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_update_complaint_created 
            ON complaints_complaintupdate(complaint_id, created_at DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_update_type_created 
            ON complaints_complaintupdate(update_type, created_at DESC);
            """,
            # فهارس للمرفقات
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_attachment_complaint 
            ON complaints_complaintattachment(complaint_id, uploaded_at DESC);
            """,
            # فهارس للصلاحيات
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_permissions_user_active 
            ON complaints_complaintuserpermissions(user_id, is_active);
            """,
        ]

        with connection.cursor() as cursor:
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    self.stdout.write(f"تم إنشاء فهرس بنجاح")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"خطأ في إنشاء فهرس: {e}"))

        self.stdout.write("تم الانتهاء من إنشاء الفهارس")
