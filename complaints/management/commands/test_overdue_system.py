"""
اختبار نظام الشكاوى المتأخرة والتنبيهات
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Department, User
from complaints.models import Complaint, ComplaintType, ComplaintUserPermissions
from complaints.services.notification_service import ComplaintNotificationService
from customers.models import Customer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "اختبار نظام الشكاوى المتأخرة والتنبيهات"

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-test-data",
            action="store_true",
            help="إنشاء بيانات اختبار للشكاوى المتأخرة",
        )
        parser.add_argument(
            "--test-notifications",
            action="store_true",
            help="اختبار نظام التنبيهات",
        )

    def handle(self, *args, **options):
        create_test_data = options["create_test_data"]
        test_notifications = options["test_notifications"]

        self.stdout.write(self.style.SUCCESS("🧪 بدء اختبار نظام الشكاوى المتأخرة..."))

        if create_test_data:
            self.create_test_data()

        if test_notifications:
            self.test_notification_system()

        # فحص الشكاوى المتأخرة الحالية
        self.check_current_overdue_complaints()

        self.stdout.write(self.style.SUCCESS("✅ تم الانتهاء من الاختبار"))

    def create_test_data(self):
        """إنشاء بيانات اختبار للشكاوى المتأخرة"""
        self.stdout.write("📝 إنشاء بيانات اختبار...")

        try:
            # إنشاء عميل اختبار
            customer, created = Customer.objects.get_or_create(
                name="عميل اختبار الشكاوى المتأخرة",
                defaults={"email": "test@example.com", "phone": "123456789"},
            )

            # إنشاء نوع شكوى اختبار
            complaint_type, created = ComplaintType.objects.get_or_create(
                name="شكوى اختبار متأخرة",
                defaults={
                    "description": "نوع شكوى للاختبار",
                    "default_priority": "medium",
                },
            )

            # إنشاء مستخدم اختبار
            user, created = User.objects.get_or_create(
                username="test_user_overdue",
                defaults={
                    "email": "testuser@example.com",
                    "first_name": "مستخدم",
                    "last_name": "اختبار",
                },
            )

            # إنشاء شكوى متأخرة
            now = timezone.now()
            overdue_deadline = now - timedelta(days=2)  # متأخرة بيومين

            complaint, created = Complaint.objects.get_or_create(
                complaint_number="TEST-OVERDUE-001",
                defaults={
                    "customer": customer,
                    "complaint_type": complaint_type,
                    "title": "شكوى اختبار متأخرة",
                    "description": "هذه شكوى اختبار لفحص النظام المتأخر",
                    "status": "new",
                    "priority": "medium",
                    "deadline": overdue_deadline,
                    "assigned_to": user,
                    "created_by": user,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ تم إنشاء شكوى اختبار: {complaint.complaint_number}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  شكوى الاختبار موجودة مسبقاً: {complaint.complaint_number}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ خطأ في إنشاء بيانات الاختبار: {str(e)}")
            )

    def test_notification_system(self):
        """اختبار نظام التنبيهات"""
        self.stdout.write("📧 اختبار نظام التنبيهات...")

        try:
            notification_service = ComplaintNotificationService()

            # البحث عن شكوى متأخرة للاختبار
            overdue_complaints = Complaint.objects.filter(
                deadline__lt=timezone.now(),
                status__in=["new", "in_progress", "overdue"],
            )

            if not overdue_complaints.exists():
                self.stdout.write(
                    self.style.WARNING("⚠️  لا توجد شكاوى متأخرة للاختبار")
                )
                return

            test_complaint = overdue_complaints.first()
            self.stdout.write(
                f"🧪 اختبار التنبيهات للشكوى: {test_complaint.complaint_number}"
            )

            # اختبار تنبيهات التصعيد
            notification_service.notify_overdue_to_escalation_users(test_complaint)
            self.stdout.write("✅ تم اختبار تنبيهات التصعيد")

            # اختبار التنبيهات اليومية
            notification_service.notify_overdue_complaints_daily()
            self.stdout.write("✅ تم اختبار التنبيهات اليومية")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ خطأ في اختبار التنبيهات: {str(e)}"))

    def check_current_overdue_complaints(self):
        """فحص الشكاوى المتأخرة الحالية"""
        self.stdout.write("🔍 فحص الشكاوى المتأخرة الحالية...")

        now = timezone.now()
        overdue_complaints = Complaint.objects.filter(
            deadline__lt=now, status__in=["new", "in_progress", "overdue"]
        ).select_related("customer", "assigned_to", "assigned_department")

        if not overdue_complaints.exists():
            self.stdout.write(self.style.SUCCESS("✅ لا توجد شكاوى متأخرة حالياً"))
            return

        self.stdout.write(
            self.style.WARNING(f"⚠️  عدد الشكاوى المتأخرة: {overdue_complaints.count()}")
        )

        for complaint in overdue_complaints:
            days_late = (now - complaint.deadline).days
            self.stdout.write(
                f"📋 {complaint.complaint_number} - متأخرة {days_late} يوم"
            )
            self.stdout.write(f'   👤 المسؤول: {complaint.assigned_to or "غير محدد"}')
            self.stdout.write(f"   📊 الحالة: {complaint.get_status_display()}")

        # فحص المستخدمين الذين يمكن التصعيد إليهم
        self.stdout.write("\n👥 المستخدمون الذين يمكن التصعيد إليهم:")

        escalation_users = User.objects.filter(
            complaint_permissions__can_receive_escalations=True,
            complaint_permissions__is_active=True,
        )

        if escalation_users.exists():
            for user in escalation_users:
                self.stdout.write(f"   👤 {user.get_full_name() or user.username}")
        else:
            self.stdout.write("   ⚠️  لا يوجد مستخدمون مع صلاحية استقبال التصعيد")

        # فحص المجموعات الإدارية
        from django.contrib.auth.models import Group

        admin_groups = Group.objects.filter(
            name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
        )

        self.stdout.write("\n🏢 المجموعات الإدارية:")
        for group in admin_groups:
            self.stdout.write(f"   👥 {group.name}: {group.user_set.count()} مستخدم")
