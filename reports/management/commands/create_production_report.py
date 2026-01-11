"""
Management command to create a sample production report
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from reports.models import Report

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a sample production report"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", type=str, help="اسم المستخدم الذي سيتم إنشاء التقرير باسمه"
        )

    def handle(self, *args, **kwargs):
        username = kwargs.get("user")

        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                self.stdout.write(self.style.ERROR(f"المستخدم {username} غير موجود"))
                return
        else:
            # البحث عن المستخدم النشط الأخير أو الـ superuser
            user = User.objects.filter(is_superuser=True, is_active=True).first()
            if not user:
                user = User.objects.filter(is_active=True).first()

        if not user:
            self.stdout.write(
                self.style.ERROR("No user found. Please create a user first.")
            )
            return

        # تواريخ افتراضية: آخر 30 يوم
        date_to = timezone.now().date()
        date_from = date_to - timedelta(days=30)

        report_data = {
            "title": "تقرير الإنتاج الشامل",
            "report_type": "production",
            "description": "تقرير شامل لمراقبة الإنتاج وحساب الأمتار حسب فلتر المستودعات. يمكنك تغيير الفترة الزمنية ونوع الطلبات من خلال فورم الفلترة.",
            "parameters": {
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "order_types": [],  # كل الأنواع
                "production_lines": [],  # كل خطوط الإنتاج
                "changed_by": None,  # كل المستلمين
            },
            "created_by": user,
        }

        # البحث عن تقرير موجود بنفس النوع
        existing_report = Report.objects.filter(report_type="production").first()

        if existing_report:
            # تحديث التقرير الموجود
            existing_report.parameters = report_data["parameters"]
            existing_report.description = report_data["description"]
            existing_report.created_by = user
            existing_report.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ تم تحديث تقرير الإنتاج: {existing_report.title}"
                )
            )
            self.stdout.write(self.style.SUCCESS(f"   - ID: {existing_report.id}"))
            self.stdout.write(
                self.style.SUCCESS(
                    f"   - المالك: {user.get_full_name() or user.username}"
                )
            )
            report = existing_report
        else:
            # إنشاء تقرير جديد
            report = Report.objects.create(**report_data)

            self.stdout.write(
                self.style.SUCCESS(f"✅ تم إنشاء تقرير الإنتاج بنجاح: {report.title}")
            )
            self.stdout.write(self.style.SUCCESS(f"   - ID: {report.id}"))
            self.stdout.write(
                self.style.SUCCESS(
                    f"   - المالك: {user.get_full_name() or user.username}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n📊 يمكنك الآن الوصول للتقرير من خلال:")
        )
        self.stdout.write(self.style.SUCCESS(f"   /reports/{report.id}/"))
        self.stdout.write(
            self.style.SUCCESS(
                f"\n💡 نصيحة: يمكنك تغيير الفترة الزمنية والفلاتر مباشرة من صفحة التقرير"
            )
        )
