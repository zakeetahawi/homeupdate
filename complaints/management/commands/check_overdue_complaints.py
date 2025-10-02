"""
أمر إدارة للتحقق من الشكاوى المتأخرة وإرسال التنبيهات
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from complaints.models import Complaint
from complaints.services.notification_service import ComplaintNotificationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "فحص الشكاوى المتأخرة وإرسال التنبيهات للمستخدمين المناسبين"

    def add_arguments(self, parser):
        parser.add_argument(
            "--send-notifications",
            action="store_true",
            help="إرسال التنبيهات فعلياً (بدون هذا الخيار سيتم العرض فقط)",
        )
        parser.add_argument(
            "--days-overdue",
            type=int,
            default=0,
            help="عدد الأيام المتأخرة (افتراضي: جميع الشكاوى المتأخرة)",
        )

    def handle(self, *args, **options):
        send_notifications = options["send_notifications"]
        days_overdue = options["days_overdue"]

        self.stdout.write(self.style.SUCCESS("🔍 بدء فحص الشكاوى المتأخرة..."))

        # البحث عن الشكاوى المتأخرة
        now = timezone.now()
        overdue_filter = {
            "deadline__lt": now,
            "status__in": ["new", "in_progress", "overdue"],
        }

        if days_overdue > 0:
            cutoff_date = now - timezone.timedelta(days=days_overdue)
            overdue_filter["deadline__lt"] = cutoff_date

        overdue_complaints = (
            Complaint.objects.filter(**overdue_filter)
            .select_related(
                "customer", "complaint_type", "assigned_to", "assigned_department"
            )
            .order_by("deadline")
        )

        if not overdue_complaints.exists():
            self.stdout.write(self.style.SUCCESS("✅ لا توجد شكاوى متأخرة"))
            return

        self.stdout.write(
            self.style.WARNING(
                f"⚠️  تم العثور على {overdue_complaints.count()} شكوى متأخرة"
            )
        )

        # عرض تفاصيل الشكاوى المتأخرة
        for complaint in overdue_complaints:
            days_late = (now - complaint.deadline).days
            self.stdout.write(
                f"📋 {complaint.complaint_number} - {complaint.customer.name}"
            )
            self.stdout.write(f"   📅 متأخرة منذ: {days_late} يوم")
            self.stdout.write(f'   👤 المسؤول: {complaint.assigned_to or "غير محدد"}')
            self.stdout.write(
                f'   🏢 القسم: {complaint.assigned_department or "غير محدد"}'
            )
            self.stdout.write(f"   📊 الحالة: {complaint.get_status_display()}")
            self.stdout.write("   " + "-" * 50)

        if send_notifications:
            self.stdout.write(self.style.SUCCESS("📧 بدء إرسال التنبيهات..."))

            notification_service = ComplaintNotificationService()

            for complaint in overdue_complaints:
                try:
                    # تحديث حالة الشكوى إلى متأخرة إذا لم تكن كذلك
                    if complaint.status != "overdue":
                        complaint.status = "overdue"
                        complaint.save()
                        self.stdout.write(
                            f"✅ تم تحديث حالة الشكوى {complaint.complaint_number} إلى متأخرة"
                        )

                    # إرسال تنبيه للمسؤول الحالي
                    if complaint.assigned_to:
                        notification_service._send_notification(
                            complaint=complaint,
                            recipient=complaint.assigned_to,
                            notification_type="overdue_reminder",
                            title=f"تذكير: شكوى متأخرة {complaint.complaint_number}",
                            message=f"الشكوى متأخرة منذ {(now - complaint.deadline).days} يوم",
                            send_email=True,
                        )
                        self.stdout.write(
                            f"📧 تم إرسال تنبيه للمسؤول: {complaint.assigned_to}"
                        )

                    # إرسال تنبيهات للمستخدمين الذين يمكن التصعيد إليهم
                    notification_service.notify_overdue_to_escalation_users(complaint)
                    self.stdout.write(
                        f"📧 تم إرسال تنبيهات التصعيد للشكوى {complaint.complaint_number}"
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ خطأ في إرسال التنبيهات للشكوى {complaint.complaint_number}: {str(e)}"
                        )
                    )

            self.stdout.write(self.style.SUCCESS("✅ تم الانتهاء من إرسال التنبيهات"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  لم يتم إرسال التنبيهات (استخدم --send-notifications لإرسالها)"
                )
            )

        # إحصائيات إضافية
        self.stdout.write("\n📊 إحصائيات الشكاوى المتأخرة:")

        # حسب القسم
        departments = {}
        for complaint in overdue_complaints:
            dept_name = (
                complaint.assigned_department.name
                if complaint.assigned_department
                else "غير محدد"
            )
            departments[dept_name] = departments.get(dept_name, 0) + 1

        for dept, count in departments.items():
            self.stdout.write(f"   🏢 {dept}: {count} شكوى")

        # حسب المسؤول
        assignees = {}
        for complaint in overdue_complaints:
            assignee_name = (
                str(complaint.assigned_to) if complaint.assigned_to else "غير محدد"
            )
            assignees[assignee_name] = assignees.get(assignee_name, 0) + 1

        self.stdout.write("\n👥 حسب المسؤول:")
        for assignee, count in assignees.items():
            self.stdout.write(f"   👤 {assignee}: {count} شكوى")

        self.stdout.write(
            self.style.SUCCESS("\n✅ تم الانتهاء من فحص الشكاوى المتأخرة")
        )
