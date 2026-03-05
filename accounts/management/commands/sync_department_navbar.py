"""
sync_department_navbar - يزامن إعدادات الناف بار لوحدات الأقسام

يُشغَّل تلقائياً عند كل deployment لضمان تزامن قاعدة البيانات
على جميع السيرفرات (dev / production) دون تدخل يدوي.

الاستخدام:
    python manage.py sync_department_navbar
    python manage.py sync_department_navbar --dry-run   # معاينة فقط بدون حفظ
"""

from django.core.cache import cache
from django.core.management.base import BaseCommand

from accounts.models import Department

# =====================================================================
# خريطة التكوين: url_name → أقسام الناف بار المطلوبة
# المفتاح: url_name للوحدة
# القيمة: dict يحدد أي show_* يكون True والبقية False
#
# لإضافة وحدة جديدة أو تعديل قسم وحدة موجودة:
# - أضف مدخلاً جديداً بالـ url_name الخاص بها
# - حدد الأقسام التي تظهر فيها (يمكن أكثر من قسم)
# =====================================================================
NAVBAR_CONFIG = {
    # ── العملاء ──────────────────────────────────────────────────────
    "/customers/":                      {"customers": True},

    # ── الطلبات ──────────────────────────────────────────────────────
    "/orders/":                         {"orders": True},

    # ── المخزون ──────────────────────────────────────────────────────
    "/inventory/":                      {"inventory": True},
    "/inventory/base-products/":        {"inventory": True},
    "/inventory/warehouses/":           {"inventory": True},
    "/inventory/colors/":               {"inventory": True},
    "/inventory/transfers/":            {"inventory": True},

    # ── المعاينات ─────────────────────────────────────────────────────
    "/inspections/":                    {"inspections": True},

    # ── التركيبات / العمليات ──────────────────────────────────────────
    "/installations/":                  {"operations": True},

    # ── المصنع ───────────────────────────────────────────────────────
    "/manufacturing/":                  {"manufacturing": True},
    "/manufacturing/fabric-receipt/":   {"manufacturing": True},
    "/manufacturing/product-receipt/":  {"inventory": True},
    "/factory-accounting/reports/":     {"reports": True},          # ← تقرير إنتاج (تقارير فقط)

    # ── التقطيع ──────────────────────────────────────────────────────
    "/cutting/":                        {"inventory": True},
    "/cutting/orders/completed/":       {"inventory": True},
    "/cutting/reports/":                {"inventory": True},

    # ── الشكاوى ──────────────────────────────────────────────────────
    "/complaints/":                     {"complaints": True},
    "/complaints/list/":                {"complaints": True},
    "/complaints/admin/":               {"complaints": True},

    # ── التقارير ─────────────────────────────────────────────────────
    "/reports/":                        {"reports": True},
    "/reports/production/":             {"reports": True},
    "/reports/orders/":                 {"reports": True},

    # ── المحاسبة ─────────────────────────────────────────────────────
    "/accounting/":                     {"accounting": True},
    "/accounting/transactions/":        {"accounting": True},
    "/accounting/accounts/":            {"accounting": True},
    "/accounting/advances/":            {"accounting": True},

    # ── قاعدة البيانات ───────────────────────────────────────────────
    "/database/":                       {"database": True},
}

ALL_SECTIONS = [
    "customers", "orders", "inventory", "inspections",
    "operations", "manufacturing", "complaints", "reports",
    "accounting", "database",
]

# خريطة اسم القسم → اسم حقل show_*
SECTION_TO_FIELD = {
    "customers":     "show_customers",
    "orders":        "show_orders",
    "inventory":     "show_inventory",
    "inspections":   "show_inspections",
    "operations":    "show_installations",
    "manufacturing": "show_manufacturing",
    "complaints":    "show_complaints",
    "reports":       "show_reports",
    "accounting":    "show_accounting",
    "database":      "show_database",
}


class Command(BaseCommand):
    help = "يزامن إعدادات الناف بار (show_*) لوحدات الأقسام — يُشغَّل عند كل deployment"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="معاينة التغييرات بدون حفظ في قاعدة البيانات",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0
        skipped = 0
        not_found = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n⚙  مزامنة إعدادات الناف بار للوحدات...\n"
        ))

        for url_name, desired_sections in NAVBAR_CONFIG.items():
            units = Department.objects.filter(url_name=url_name)

            if not units.exists():
                self.stdout.write(
                    self.style.WARNING(f"  ⚠  غير موجودة: {url_name}")
                )
                not_found += 1
                continue

            for unit in units:
                # بناء القيم المطلوبة لكل show_*
                new_values = {}
                for section in ALL_SECTIONS:
                    field = SECTION_TO_FIELD[section]
                    desired = desired_sections.get(section, False)
                    if getattr(unit, field) != desired:
                        new_values[field] = desired

                if not new_values:
                    skipped += 1
                    continue

                # عرض التغييرات
                changes_str = ", ".join(
                    f"{k}={v}" for k, v in new_values.items()
                )
                self.stdout.write(
                    f"  {'[DRY]' if dry_run else '✓'} "
                    f"{unit.name} ({url_name})\n"
                    f"      التغيير: {changes_str}"
                )

                if not dry_run:
                    Department.objects.filter(pk=unit.pk).update(**new_values)
                    updated += 1

        if not dry_run:
            # مسح كاش الناف بار لجميع المستخدمين
            cache.clear()
            self.stdout.write(self.style.SUCCESS("\n✓ تم مسح كاش الناف بار"))

        self.stdout.write(self.style.SUCCESS(
            f"\n{'[DRY RUN] ' if dry_run else ''}النتيجة: "
            f"تم تحديث {updated} • "
            f"لا تحتاج تعديل {skipped} • "
            f"غير موجودة {not_found}\n"
        ))
