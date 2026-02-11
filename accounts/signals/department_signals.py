"""
Signals لإدارة الأقسام بشكل تلقائي
"""

from django.apps import apps
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from accounts.models import Department


@receiver(post_save, sender=Department)
def auto_enable_department_navbar_visibility(sender, instance, created, **kwargs):
    """
    تفعيل حقل show_* التلقائي للأقسام والوحدات الجديدة
    بناءً على code القسم أو القسم الأب
    """
    if created and instance.is_core:
        # خريطة الأقسام وحقول show_* المرتبطة بها
        department_mapping = {
            "customers": "show_customers",
            "orders": "show_orders",
            "inventory": "show_inventory",
            "inspections": "show_inspections",
            "installations": "show_installations",
            "manufacturing": "show_manufacturing",
            "complaints": "show_complaints",
            "reports": "show_reports",
            "accounting": "show_accounting",
            "database": "show_database",
            "cutting": "show_inventory",  # التقطيع يظهر في المخزون
        }

        # إذا كان قسم رئيسي
        if not instance.parent and instance.code in department_mapping:
            field_name = department_mapping[instance.code]
            setattr(instance, field_name, True)
            instance.save(update_fields=[field_name])

        # إذا كان وحدة فرعية
        elif instance.parent and instance.parent.code in department_mapping:
            field_name = department_mapping[instance.parent.code]
            setattr(instance, field_name, True)
            instance.save(update_fields=[field_name])


@receiver(post_migrate)
def create_default_departments_structure(sender, **kwargs):
    """
    إنشاء هيكل الأقسام والوحدات تلقائياً بعد كل migrate
    يعمل فقط عند تطبيق migrations على تطبيق accounts
    """
    # تشغيل فقط عند migrate لتطبيق accounts
    if sender.name != "accounts":
        return

    # استيراد المودل بعد التأكد من جاهزية قاعدة البيانات
    Department = apps.get_model("accounts", "Department")

    # حذف الوحدات القديمة (navbar_*)
    old_navbar = Department.objects.filter(code__startswith="navbar_")
    old_main = Department.objects.filter(code="main_navbar")
    deleted_count = old_navbar.count() + old_main.count()
    if deleted_count > 0:
        old_navbar.delete()
        old_main.delete()

    # الأقسام الرئيسية
    main_departments = {
        "customers": {"name": "العملاء", "icon": "fa-users", "order": 1},
        "orders": {"name": "الطلبات", "icon": "fa-shopping-cart", "order": 2},
        "inventory": {"name": "المخزون", "icon": "fa-warehouse", "order": 3},
        "inspections": {"name": "المعاينات", "icon": "fa-search", "order": 4},
        "installations": {"name": "التركيبات", "icon": "fa-tools", "order": 5},
        "manufacturing": {"name": "إدارة التصنيع", "icon": "fa-industry", "order": 6},
        "complaints": {
            "name": "الشكاوى",
            "icon": "fa-exclamation-triangle",
            "order": 7,
        },
        "reports": {"name": "التقارير", "icon": "fa-chart-bar", "order": 8},
        "accounting": {"name": "المحاسبة", "icon": "fa-calculator", "order": 9},
        "database": {"name": "إدارة البيانات", "icon": "fa-database", "order": 10},
        "cutting": {"name": "إدارة التقطيع", "icon": "fa-cut", "order": 11},
    }

    for code, data in main_departments.items():
        Department.objects.get_or_create(
            code=code,
            defaults={
                "name": data["name"],
                "department_type": "department",
                "icon": data["icon"],
                "order": data["order"],
                "is_active": True,
                "parent": None,
                "description": f'قسم {data["name"]}',
            },
        )

    # الوحدات الفرعية
    navbar_units = [
        {
            "parent_code": "customers",
            "code": "customers_list",
            "name": "قائمة العملاء",
            "url_name": "/customers/",
            "icon": "fa-list",
            "order": 1,
            "show_customers": True,
        },
        {
            "parent_code": "orders",
            "code": "orders_list",
            "name": "قائمة الطلبات",
            "url_name": "/orders/",
            "icon": "fa-list",
            "order": 1,
            "show_orders": True,
        },
        {
            "parent_code": "inventory",
            "code": "inventory_dashboard",
            "name": "إدارة المخزون",
            "url_name": "/inventory/",
            "icon": "fa-warehouse",
            "order": 1,
            "show_inventory": True,
        },
        {
            "parent_code": "inventory",
            "code": "inventory_warehouses",
            "name": "إدارة المستودعات",
            "url_name": "/inventory/warehouses/",
            "icon": "fa-warehouse",
            "order": 2,
            "show_inventory": True,
        },
        {
            "parent_code": "inventory",
            "code": "inventory_products",
            "name": "المنتجات والألوان",
            "url_name": "/inventory/base-products/",
            "icon": "fa-palette",
            "order": 3,
            "show_inventory": True,
        },
        {
            "parent_code": "inventory",
            "code": "inventory_colors",
            "name": "إدارة الألوان",
            "url_name": "/inventory/colors/",
            "icon": "fa-fill-drip",
            "order": 4,
            "show_inventory": True,
        },
        {
            "parent_code": "inventory",
            "code": "inventory_transfers",
            "name": "تحويلات مخزنية",
            "url_name": "/inventory/transfers/",
            "icon": "fa-exchange-alt",
            "order": 5,
            "show_inventory": True,
        },
        {
            "parent_code": "inspections",
            "code": "inspections_list",
            "name": "قائمة المعاينات",
            "url_name": "/inspections/",
            "icon": "fa-clipboard-check",
            "order": 1,
            "show_inspections": True,
        },
        {
            "parent_code": "installations",
            "code": "installations_dashboard",
            "name": "لوحة التركيبات",
            "url_name": "/installations/",
            "icon": "fa-tools",
            "order": 1,
            "show_installations": True,
        },
        {
            "parent_code": "manufacturing",
            "code": "product_receipt",
            "name": "استلام المنتجات",
            "url_name": "/manufacturing/product-receipt/",
            "icon": "fa-box-open",
            "order": 1,
            "show_inventory": True,
        },
        {
            "parent_code": "manufacturing",
            "code": "manufacturing_orders",
            "name": "أوامر التصنيع",
            "url_name": "/manufacturing/",
            "icon": "fa-list",
            "order": 2,
            "show_manufacturing": True,
        },
        {
            "parent_code": "manufacturing",
            "code": "factory_receiver",
            "name": "استلام من المصنع",
            "url_name": "/manufacturing/fabric-receipt/",
            "icon": "fa-industry",
            "order": 3,
            "show_manufacturing": True,
        },
        {
            "parent_code": "complaints",
            "code": "complaints_dashboard",
            "name": "لوحة الشكاوى",
            "url_name": "/complaints/",
            "icon": "fa-tachometer-alt",
            "order": 1,
            "show_complaints": True,
        },
        {
            "parent_code": "complaints",
            "code": "complaints_list",
            "name": "قائمة الشكاوى",
            "url_name": "/complaints/list/",
            "icon": "fa-list",
            "order": 2,
            "show_complaints": True,
        },
        {
            "parent_code": "complaints",
            "code": "complaints_unsolved",
            "name": "الشكاوى غير المحلولة",
            "url_name": "/complaints/admin/",
            "icon": "fa-shield-alt",
            "order": 3,
            "show_complaints": True,
        },
        {
            "parent_code": "reports",
            "code": "factory_accounting_reports",
            "name": "تقرير إنتاج",
            "url_name": "/factory-accounting/reports/",
            "icon": "fa-industry",
            "order": 1,
            "show_reports": True,
        },
        {
            "parent_code": "accounting",
            "code": "accounting_dashboard",
            "name": "لوحة المحاسبة",
            "url_name": "/accounting/",
            "icon": "fa-tachometer-alt",
            "order": 1,
            "show_accounting": True,
        },
        {
            "parent_code": "accounting",
            "code": "accounting_accounts_tree",
            "name": "شجرة الحسابات",
            "url_name": "/accounting/accounts/",
            "icon": "fa-sitemap",
            "order": 2,
            "show_accounting": True,
        },
        {
            "parent_code": "accounting",
            "code": "accounting_transactions",
            "name": "القيود المحاسبية",
            "url_name": "/accounting/transactions/",
            "icon": "fa-file-invoice",
            "order": 3,
            "show_accounting": True,
        },
        # تم إزالة سلف العملاء - استخدم نظام الدفعات العامة
        # {
        #     "parent_code": "accounting",
        #     "code": "accounting_advances",
        #     "name": "سلف العملاء",
        #     "url_name": "/accounting/advances/",
        #     "icon": "fa-hand-holding-usd",
        #     "order": 4,
        #     "show_accounting": True,
        # },
        {
            "parent_code": "database",
            "code": "database_management",
            "name": "إدارة قاعدة البيانات",
            "url_name": "/database/",
            "icon": "fa-database",
            "order": 1,
            "show_database": True,
        },
        {
            "parent_code": "cutting",
            "code": "cutting_system",
            "name": "نظام التقطيع",
            "url_name": "/cutting/",
            "icon": "fa-cut",
            "order": 1,
            "show_inventory": True,
        },
        {
            "parent_code": "cutting",
            "code": "cutting_batch_orders",
            "name": "أوامر التقطيع المجمعة",
            "url_name": "/cutting/orders/completed/",
            "icon": "fa-list-check",
            "order": 2,
            "show_inventory": True,
        },
        {
            "parent_code": "cutting",
            "code": "cutting_reports",
            "name": "تقارير التقطيع",
            "url_name": "/cutting/reports/",
            "icon": "fa-chart-bar",
            "order": 3,
            "show_inventory": True,
        },
    ]

    parent_dict = {}
    for unit_data in navbar_units:
        parent_code = unit_data.pop("parent_code")
        if parent_code not in parent_dict:
            try:
                parent_dict[parent_code] = Department.objects.get(code=parent_code)
            except Department.DoesNotExist:
                continue

        parent_dept = parent_dict[parent_code]
        show_fields = {}
        for key in list(unit_data.keys()):
            if key.startswith("show_"):
                show_fields[key] = unit_data.pop(key)

        Department.objects.update_or_create(
            code=unit_data["code"],
            defaults={
                "name": unit_data["name"],
                "url_name": unit_data["url_name"],
                "icon": unit_data["icon"],
                "order": unit_data["order"],
                "department_type": "unit",
                "is_active": True,
                "parent": parent_dept,
                "description": f'وحدة {unit_data["name"]} ضمن {parent_dept.name}',
                **show_fields,
            },
        )
