"""
أمر Django لتشخيص مشاكل نظام الشكاوى
"""

import time

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import connection

from accounts.models import User
from complaints.models import Complaint, ComplaintUserPermissions


class Command(BaseCommand):
    help = "تشخيص مشاكل نظام الشكاوى والأداء"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="اسم المستخدم للفحص المفصل",
        )
        parser.add_argument(
            "--complaint-id",
            type=int,
            help="رقم الشكوى للفحص المفصل",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== تشخيص نظام الشكاوى ==="))

        self.check_database_status()
        self.check_groups()
        self.check_user_permissions()
        self.check_complaints_status()

        if options["user"]:
            self.check_specific_user(options["user"])

        if options["complaint_id"]:
            self.check_specific_complaint(options["complaint_id"])

        self.performance_test()

    def check_database_status(self):
        """فحص حالة قاعدة البيانات"""
        self.stdout.write("\n=== فحص قاعدة البيانات ===")

        # عدد الشكاوى
        complaints_count = Complaint.objects.count()
        self.stdout.write(f"عدد الشكاوى الإجمالي: {complaints_count}")

        # عدد المستخدمين
        users_count = User.objects.count()
        self.stdout.write(f"عدد المستخدمين: {users_count}")

        # عدد صلاحيات الشكاوى
        permissions_count = ComplaintUserPermissions.objects.count()
        self.stdout.write(f"عدد سجلات صلاحيات الشكاوى: {permissions_count}")

    def check_groups(self):
        """فحص المجموعات المطلوبة"""
        self.stdout.write("\n=== فحص المجموعات ===")

        required_groups = [
            "Complaints_Managers",
            "Complaints_Supervisors",
            "Managers",
            "Complaints_Staff",
        ]

        for group_name in required_groups:
            try:
                group = Group.objects.get(name=group_name)
                users_count = group.user_set.count()
                self.stdout.write(f"✓ {group_name}: {users_count} مستخدم")
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"✗ المجموعة غير موجودة: {group_name}")
                )

    def check_user_permissions(self):
        """فحص صلاحيات المستخدمين"""
        self.stdout.write("\n=== فحص صلاحيات المستخدمين ===")

        # المستخدمون بدون صلاحيات شكاوى
        users_without_permissions = User.objects.exclude(
            id__in=ComplaintUserPermissions.objects.values_list("user_id", flat=True)
        )

        if users_without_permissions.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"المستخدمون بدون صلاحيات شكاوى: {users_without_permissions.count()}"
                )
            )
            for user in users_without_permissions[:5]:
                self.stdout.write(f"  - {user.username}")
        else:
            self.stdout.write("✓ جميع المستخدمين لديهم صلاحيات شكاوى")

        # المستخدمون مع صلاحيات كاملة
        admin_permissions = ComplaintUserPermissions.objects.filter(
            can_edit_all_complaints=True, is_active=True
        )
        self.stdout.write(f"المستخدمون مع صلاحيات إدارية: {admin_permissions.count()}")

    def check_complaints_status(self):
        """فحص حالة الشكاوى"""
        self.stdout.write("\n=== فحص حالة الشكاوى ===")

        # إحصائيات الحالات
        from django.db.models import Count

        status_stats = (
            Complaint.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        for stat in status_stats:
            self.stdout.write(f'{stat["status"]}: {stat["count"]} شكوى')

        # الشكاوى المتأخرة
        from django.utils import timezone

        overdue_complaints = Complaint.objects.filter(
            deadline__lt=timezone.now(), status__in=["new", "in_progress"]
        ).count()

        if overdue_complaints > 0:
            self.stdout.write(
                self.style.WARNING(f"الشكاوى المتأخرة: {overdue_complaints}")
            )
        else:
            self.stdout.write("✓ لا توجد شكاوى متأخرة")

    def check_specific_user(self, username):
        """فحص مستخدم محدد"""
        self.stdout.write(f"\n=== فحص المستخدم: {username} ===")

        try:
            user = User.objects.get(username=username)

            # المجموعات
            groups = [group.name for group in user.groups.all()]
            self.stdout.write(f"المجموعات: {groups}")

            # صلاحيات الشكاوى
            try:
                permissions = user.complaint_permissions
                self.stdout.write(f"صلاحيات الشكاوى:")
                self.stdout.write(f"  - نشط: {permissions.is_active}")
                self.stdout.write(
                    f"  - تعديل الكل: {permissions.can_edit_all_complaints}"
                )
                self.stdout.write(
                    f"  - عرض الكل: {permissions.can_view_all_complaints}"
                )
                self.stdout.write(f"  - إسناد: {permissions.can_assign_complaints}")
                self.stdout.write(f"  - تصعيد: {permissions.can_escalate_complaints}")
                self.stdout.write(f"  - حل: {permissions.can_resolve_complaints}")
                self.stdout.write(f"  - إغلاق: {permissions.can_close_complaints}")
            except ComplaintUserPermissions.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR("لا توجد صلاحيات شكاوى لهذا المستخدم")
                )

            # الشكاوى المسندة
            assigned_complaints = Complaint.objects.filter(assigned_to=user).count()
            self.stdout.write(f"الشكاوى المسندة: {assigned_complaints}")

            # الشكاوى المنشأة
            created_complaints = Complaint.objects.filter(created_by=user).count()
            self.stdout.write(f"الشكاوى المنشأة: {created_complaints}")

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"المستخدم غير موجود: {username}"))

    def check_specific_complaint(self, complaint_id):
        """فحص شكوى محددة"""
        self.stdout.write(f"\n=== فحص الشكوى رقم: {complaint_id} ===")

        try:
            complaint = Complaint.objects.select_related(
                "customer", "complaint_type", "assigned_to", "created_by"
            ).get(id=complaint_id)

            self.stdout.write(f"رقم الشكوى: {complaint.complaint_number}")
            self.stdout.write(f"العميل: {complaint.customer.name}")
            self.stdout.write(f"النوع: {complaint.complaint_type.name}")
            self.stdout.write(f"الحالة: {complaint.status}")
            self.stdout.write(f"الأولوية: {complaint.priority}")
            self.stdout.write(f"مسندة إلى: {complaint.assigned_to}")
            self.stdout.write(f"منشأة بواسطة: {complaint.created_by}")
            self.stdout.write(f"تاريخ الإنشاء: {complaint.created_at}")
            self.stdout.write(f"المهلة النهائية: {complaint.deadline}")

            # التحديثات والمرفقات
            updates_count = complaint.updates.count()
            attachments_count = complaint.attachments.count()
            self.stdout.write(f"عدد التحديثات: {updates_count}")
            self.stdout.write(f"عدد المرفقات: {attachments_count}")

        except Complaint.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"الشكوى غير موجودة: {complaint_id}"))

    def performance_test(self):
        """اختبار الأداء"""
        self.stdout.write("\n=== اختبار الأداء ===")

        # اختبار تحميل قائمة الشكاوى
        connection.queries_log.clear()
        start_time = time.time()

        complaints = list(
            Complaint.objects.select_related(
                "customer", "complaint_type", "assigned_to"
            )[:10]
        )

        end_time = time.time()

        self.stdout.write(f"وقت تحميل 10 شكاوى: {end_time - start_time:.3f} ثانية")
        self.stdout.write(f"عدد الاستعلامات: {len(connection.queries)}")

        # اختبار تحميل شكوى واحدة مع التفاصيل
        if complaints:
            connection.queries_log.clear()
            start_time = time.time()

            complaint = (
                Complaint.objects.select_related(
                    "customer", "complaint_type", "assigned_to"
                )
                .prefetch_related("updates__created_by", "attachments__uploaded_by")
                .get(id=complaints[0].id)
            )

            # تحميل التحديثات والمرفقات
            updates = list(complaint.updates.all())
            attachments = list(complaint.attachments.all())

            end_time = time.time()

            self.stdout.write(
                f"وقت تحميل شكوى مع التفاصيل: {end_time - start_time:.3f} ثانية"
            )
            self.stdout.write(f"عدد الاستعلامات: {len(connection.queries)}")
