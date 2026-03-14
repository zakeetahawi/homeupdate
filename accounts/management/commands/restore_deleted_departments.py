"""
أمر إدارة لإعادة إنشاء الأقسام المحذوفة خطأً
"""

from django.core.management.base import BaseCommand

from accounts.models import Department


class Command(BaseCommand):
    help = "Restore accidentally deleted departments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation without confirmation",
        )

    def handle(self, *args, **options):
        # قائمة الأقسام المحذوفة التي يجب إعادة إنشاؤها
        departments_to_restore = [
            {
                "name": "العملاء",
                "code": "customers",
                "url_name": "customers:index",
                "department_type": "department",
                "icon": "fas fa-users",
                "order": 10,
                "has_pages": True,
                "is_core": True,
                "is_active": True,
            },
            {
                "name": "الطلبات",
                "code": "orders",
                "url_name": "orders:index",
                "department_type": "department",
                "icon": "fas fa-shopping-cart",
                "order": 20,
                "has_pages": True,
                "is_core": True,
                "is_active": True,
            },
            {
                "name": "المخزون",
                "code": "inventory",
                "url_name": "inventory:index",
                "department_type": "department",
                "icon": "fas fa-boxes",
                "order": 30,
                "has_pages": True,
                "is_core": True,
                "is_active": True,
            },
            {
                "name": "المعاينات",
                "code": "inspections",
                "url_name": "inspections:index",
                "department_type": "department",
                "icon": "fas fa-clipboard-check",
                "order": 40,
                "has_pages": True,
                "is_core": True,
                "is_active": True,
            },
            {
                "name": "التركيبات",
                "code": "installations",
                "url_name": "installations:index",
                "department_type": "department",
                "icon": "fas fa-tools",
                "order": 50,
                "has_pages": True,
                "is_core": True,
                "is_active": True,
            },
            {
                "name": "التقارير",
                "code": "reports",
                "url_name": "reports:list",
                "department_type": "department",
                "icon": "fas fa-chart-bar",
                "order": 70,
                "has_pages": True,
                "is_core": True,
                "is_active": True,
            },
            {
                "name": "إدارة البيانات",
                "code": "data_management",
                "url_name": "odoo_db_manager:dashboard",
                "department_type": "department",
                "icon": "fas fa-database",
                "order": 80,
                "has_pages": True,
                "is_core": True,
                "is_active": True,
            },
        ]

        self.stdout.write("🔍 فحص الأقسام المفقودة...")

        missing_departments = []
        existing_departments = []

        for dept_data in departments_to_restore:
            if Department.objects.filter(code=dept_data["code"]).exists():
                existing_departments.append(dept_data["name"])
            else:
                missing_departments.append(dept_data)

        if existing_departments:
            self.stdout.write(f"✅ الأقسام الموجودة ({len(existing_departments)}):")
            for name in existing_departments:
                self.stdout.write(f"  - {name}")

        if not missing_departments:
            self.stdout.write(
                self.style.SUCCESS("✅ جميع الأقسام موجودة - لا حاجة للإعادة")
            )
            return

        self.stdout.write(f"❌ الأقسام المفقودة ({len(missing_departments)}):")
        for dept_data in missing_departments:
            self.stdout.write(f"  - {dept_data['name']} ({dept_data['code']})")

        # طلب التأكيد
        if not options["force"]:
            confirm = input(
                f"\n❓ هل تريد إعادة إنشاء {len(missing_departments)} قسم مفقود؟ (yes/no): "
            )
            if confirm.lower() not in ["yes", "y", "نعم"]:
                self.stdout.write("❌ تم إلغاء العملية")
                return

        # إعادة إنشاء الأقسام المفقودة
        created_count = 0
        for dept_data in missing_departments:
            try:
                dept = Department.objects.create(**dept_data)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ تم إنشاء: {dept.name} ({dept.code})")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ فشل إنشاء {dept_data['name']}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"🎉 تم إعادة إنشاء {created_count} قسم بنجاح!")
        )

        self.stdout.write(
            self.style.SUCCESS("\n🔄 يُنصح بإعادة تشغيل السيرفر لتطبيق التغييرات")
        )
