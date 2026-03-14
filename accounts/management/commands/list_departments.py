"""
أمر إدارة لعرض جميع الأقسام الموجودة
"""

from django.core.management.base import BaseCommand

from accounts.models import Department


class Command(BaseCommand):
    help = "List all departments in the system"

    def handle(self, *args, **options):
        departments = Department.objects.all().order_by(
            "department_type", "order", "name"
        )

        if not departments.exists():
            self.stdout.write(self.style.WARNING("⚠️ لا توجد أقسام في النظام"))
            return

        # تجميع الأقسام حسب النوع
        by_type = {}
        for dept in departments:
            dept_type = dept.get_department_type_display()
            if dept_type not in by_type:
                by_type[dept_type] = []
            by_type[dept_type].append(dept)

        self.stdout.write(f"📋 إجمالي الأقسام: {departments.count()}")
        self.stdout.write("=" * 50)

        for dept_type, dept_list in by_type.items():
            self.stdout.write(f"\n📂 {dept_type} ({len(dept_list)}):")
            for dept in dept_list:
                status = "🟢" if dept.is_active else "🔴"
                core = "⭐" if dept.is_core else "  "
                parent = f" (تحت: {dept.parent.name})" if dept.parent else ""

                self.stdout.write(
                    f"  {status} {core} {dept.name} ({dept.code}){parent}"
                )

        # إحصائيات
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 الإحصائيات:")
        self.stdout.write(f"  - المفعلة: {departments.filter(is_active=True).count()}")
        self.stdout.write(
            f"  - غير المفعلة: {departments.filter(is_active=False).count()}"
        )
        self.stdout.write(f"  - الأساسية: {departments.filter(is_core=True).count()}")
        self.stdout.write(
            f"  - غير الأساسية: {departments.filter(is_core=False).count()}"
        )

        # الأقسام الحقيقية المطلوبة
        real_departments = [
            "customers",
            "orders",
            "inventory",
            "inspections",
            "installations",
            "reports",
            "data_management",
        ]

        missing = []
        extra = []

        for code in real_departments:
            if not departments.filter(code=code).exists():
                missing.append(code)

        for dept in departments:
            if dept.code not in real_departments:
                extra.append(dept)

        if missing:
            self.stdout.write(f"\n❌ أقسام مفقودة ({len(missing)}):")
            for code in missing:
                self.stdout.write(f"  - {code}")

        if extra:
            self.stdout.write(f"\n⚠️ أقسام إضافية ({len(extra)}):")
            for dept in extra:
                self.stdout.write(
                    f"  - {dept.department_type}: {dept.name} ({dept.code})"
                )

        if not missing and not extra:
            self.stdout.write(
                self.style.SUCCESS("\n✅ النظام نظيف - الأقسام الحقيقية فقط!")
            )
