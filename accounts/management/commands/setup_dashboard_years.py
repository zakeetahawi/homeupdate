"""
أمر إدارة لإعداد السنوات الافتراضية في الداشبورد
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import DashboardYearSettings


class Command(BaseCommand):
    help = "إعداد السنوات الافتراضية في الداشبورد"

    def add_arguments(self, parser):
        parser.add_argument(
            "--years",
            type=int,
            nargs="+",
            help="قائمة السنوات المراد إضافتها (مثال: 2023 2024 2025)",
        )
        parser.add_argument("--default-year", type=int, help="السنة الافتراضية")
        parser.add_argument(
            "--auto",
            action="store_true",
            help="إعداد تلقائي للسنوات (السنة الحالية والسنتين السابقتين)",
        )

    def handle(self, *args, **options):
        current_year = timezone.now().year

        if options["auto"]:
            # إعداد تلقائي: السنة الحالية والسنتين السابقتين
            years_to_add = [current_year - 2, current_year - 1, current_year]
            default_year = current_year
        else:
            years_to_add = options.get("years", [current_year])
            default_year = options.get("default_year", current_year)

        self.stdout.write(self.style.SUCCESS(f"بدء إعداد السنوات: {years_to_add}"))

        # إضافة السنوات
        for year in years_to_add:
            year_setting, created = DashboardYearSettings.objects.get_or_create(
                year=year,
                defaults={
                    "is_active": True,
                    "is_default": (year == default_year),
                    "description": f"سنة {year}",
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"تم إنشاء إعدادات السنة {year}"))
            else:
                self.stdout.write(self.style.WARNING(f"السنة {year} موجودة بالفعل"))

        # تعيين السنة الافتراضية
        if default_year:
            # إلغاء الافتراضية من جميع السنوات
            DashboardYearSettings.objects.update(is_default=False)

            # تعيين السنة الافتراضية
            try:
                year_setting = DashboardYearSettings.objects.get(year=default_year)
                year_setting.is_default = True
                year_setting.is_active = True
                year_setting.save()

                self.stdout.write(
                    self.style.SUCCESS(f"تم تعيين السنة {default_year} كافتراضية")
                )
            except DashboardYearSettings.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"السنة {default_year} غير موجودة"))

        # عرض ملخص الإعدادات
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("ملخص إعدادات السنوات:"))
        self.stdout.write("=" * 50)

        for year_setting in DashboardYearSettings.objects.all().order_by("-year"):
            status = []
            if year_setting.is_active:
                status.append("نشط")
            if year_setting.is_default:
                status.append("افتراضي")

            status_text = ", ".join(status) if status else "غير نشط"

            self.stdout.write(f"السنة {year_setting.year}: {status_text}")

        self.stdout.write("=" * 50)
        self.stdout.write(self.style.SUCCESS("تم الانتهاء من إعداد السنوات بنجاح!"))
