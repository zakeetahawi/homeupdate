"""
أمر إدارة لتنظيف الأقسام وإبقاء الأقسام الحقيقية فقط
"""

from django.core.management.base import BaseCommand

from accounts.models import Department


class Command(BaseCommand):
    help = "Clean up departments and keep only real app departments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force deletion without confirmation",
        )

    def handle(self, *args, **options):
        # قائمة الأقسام الحقيقية الوحيدة المسموح بها
        real_departments = [
            "customers",  # العملاء
            "orders",  # الطلبات
            "inventory",  # المخزون
            "inspections",  # المعاينات
            "installations",  # التركيبات
            "reports",  # التقارير
            "data_management",  # إدارة البيانات
        ]

        self.stdout.write("🔍 فحص جميع الأقسام الموجودة...")

        # الحصول على جميع الأقسام
        all_departments = Department.objects.all().order_by("department_type", "order")

        if not all_departments.exists():
            self.stdout.write(self.style.WARNING("⚠️ لا توجد أقسام في قاعدة البيانات"))
            return

        # تصنيف الأقسام
        real_deps = []
        fake_deps = []

        for dept in all_departments:
            if dept.code in real_departments:
                real_deps.append(dept)
            else:
                fake_deps.append(dept)

        # عرض النتائج
        self.stdout.write(f"\n📊 إحصائيات الأقسام:")
        self.stdout.write(f"  - إجمالي الأقسام: {all_departments.count()}")
        self.stdout.write(f"  - الأقسام الحقيقية: {len(real_deps)}")
        self.stdout.write(f"  - الأقسام الوهمية/الإضافية: {len(fake_deps)}")

        if real_deps:
            self.stdout.write(f"\n✅ الأقسام الحقيقية ({len(real_deps)}):")
            for dept in real_deps:
                self.stdout.write(
                    f"  - {dept.department_type}: {dept.name} ({dept.code}) - أساسي: {dept.is_core}"
                )

        if fake_deps:
            self.stdout.write(f"\n❌ الأقسام الوهمية/الإضافية ({len(fake_deps)}):")
            for dept in fake_deps:
                self.stdout.write(
                    f"  - {dept.department_type}: {dept.name} ({dept.code}) - أساسي: {dept.is_core}"
                )

        if not fake_deps:
            self.stdout.write(
                self.style.SUCCESS("\n🎉 ممتاز! جميع الأقسام حقيقية - لا حاجة للتنظيف")
            )
            return

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(f"\n🔍 وضع المعاينة - سيتم حذف {len(fake_deps)} قسم")
            )
            return

        # طلب التأكيد
        if not options["force"]:
            confirm = input(
                f"\n❓ هل تريد حذف {len(fake_deps)} قسم وهمي/إضافي؟ (yes/no): "
            )
            if confirm.lower() not in ["yes", "y", "نعم"]:
                self.stdout.write("❌ تم إلغاء العملية")
                return

        # حذف الأقسام الوهمية/الإضافية
        deleted_count = 0
        for dept in fake_deps:
            dept_name = dept.name
            dept_code = dept.code
            dept_type = dept.department_type

            try:
                dept.delete()
                deleted_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ تم حذف: {dept_type} - {dept_name} ({dept_code})"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ فشل حذف {dept_name}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 تم حذف {deleted_count} قسم وهمي/إضافي بنجاح!")
        )

        # عرض الأقسام المتبقية
        remaining_departments = Department.objects.filter(code__in=real_departments)
        self.stdout.write(f"\n📋 الأقسام المتبقية ({remaining_departments.count()}):")
        for dept in remaining_departments.order_by("order"):
            self.stdout.write(f"  - {dept.name} ({dept.code})")

        self.stdout.write(
            self.style.SUCCESS("\n🔄 يُنصح بإعادة تشغيل السيرفر لتطبيق التغييرات")
        )
