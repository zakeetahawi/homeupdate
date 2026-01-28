"""
Context processor لعرض قائمة الأقسام والوحدات في navbar
"""

from accounts.models import Department


def navbar_departments(request):
    """
    إرجاع الأقسام والوحدات التي يجب عرضها في navbar
    بناءً على صلاحيات المستخدم وأقسامه
    """
    if not request.user.is_authenticated:
        return {"navbar_departments": []}

    # Import Warehouse here to avoid circular imports
    from inventory.models import Warehouse

    user = request.user

    # جلب أقسام المستخدم
    user_departments = user.departments.all()

    # جلب جميع الوحدات التي يمكن عرضها
    all_units = (
        Department.objects.filter(parent__isnull=False, is_active=True)
        .select_related("parent")
        .order_by("parent__order", "order")
    )

    # تنظيم الوحدات حسب العناصر المراد عرضها
    navbar_items = {
        "customers": {
            "name": "العملاء",
            "icon": "fa-users",
            "url": "/customers/",
            "units": [],
        },
        "orders": {
            "name": "الطلبات",
            "icon": "fa-shopping-cart",
            "url": "/orders/",
            "units": [],
        },
        "inventory": {"name": "المخزون", "icon": "fa-boxes", "url": None, "units": []},
        "inspections": {
            "name": "المعاينات",
            "icon": "fa-clipboard-check",
            "url": "/inspections/",
            "units": [],
        },
        "operations": {
            "name": "العمليات",
            "icon": "fa-cogs",
            "url": None,  # مفعل كقائمة منسدلة
            "units": [],
        },
        "manufacturing": {
            "name": "المصنع",
            "icon": "fa-industry",
            "url": None,
            "units": [],
        },
        "complaints": {
            "name": "الشكاوى",
            "icon": "fa-exclamation-triangle",
            "url": None,
            "units": [],
        },
        "reports": {
            "name": "التقارير",
            "icon": "fa-chart-bar",
            "url": None,
            "units": [],
        },
        "accounting": {
            "name": "المحاسبة",
            "icon": "fa-calculator",
            "url": None,
            "units": [],
        },
        "database": {
            "name": "إدارة البيانات",
            "icon": "fa-database",
            "url": "/database/",
            "units": [],
        },
    }

    # إذا كان موظف، يرى كل شيء
    if user.is_staff:
        for unit in all_units:
            # تحويل الوحدة إلى dictionary
            unit_dict = {
                "name": unit.name,
                "icon": unit.icon,
                "url_name": unit.url_name,
            }

            # تحديد أي عنصر navbar يجب أن تظهر فيه هذه الوحدة
            if unit.show_customers and "customers" in navbar_items:
                navbar_items["customers"]["units"].append(unit_dict)
            if unit.show_orders and "orders" in navbar_items:
                navbar_items["orders"]["units"].append(unit_dict)
            if unit.show_inventory and "inventory" in navbar_items:
                navbar_items["inventory"]["units"].append(unit_dict)
            if unit.show_inspections and "inspections" in navbar_items:
                navbar_items["inspections"]["units"].append(unit_dict)
            if unit.show_installations and "operations" in navbar_items:
                navbar_items["operations"]["units"].append(unit_dict)
            if unit.show_manufacturing and "manufacturing" in navbar_items:
                navbar_items["manufacturing"]["units"].append(unit_dict)
            if unit.show_complaints and "complaints" in navbar_items:
                navbar_items["complaints"]["units"].append(unit_dict)
            if unit.show_reports and "reports" in navbar_items:
                navbar_items["reports"]["units"].append(unit_dict)
            if unit.show_accounting and "accounting" in navbar_items:
                navbar_items["accounting"]["units"].append(unit_dict)
            if unit.show_database and "database" in navbar_items:
                navbar_items["database"]["units"].append(unit_dict)
    else:
        # المستخدمون العاديون يرون فقط وحدات أقسامهم
        user_dept_ids = user_departments.values_list("id", "parent_id")
        user_dept_ids_flat = set()
        for dept_id, parent_id in user_dept_ids:
            user_dept_ids_flat.add(dept_id)
            if parent_id:
                user_dept_ids_flat.add(parent_id)

        for unit in all_units:
            # التحقق من أن المستخدم ينتمي لهذا القسم
            is_authorized = (
                unit.id in user_dept_ids_flat or unit.parent_id in user_dept_ids_flat
            )

            # صلاحيات خاصة لمدير التركيبات لرؤية أقسام التركيبات والمصنع
            if (
                not is_authorized
                and hasattr(user, "is_installation_manager")
                and user.is_installation_manager
            ):
                if unit.show_installations or unit.show_manufacturing:
                    is_authorized = True

            if is_authorized:
                # تحويل الوحدة إلى dictionary
                unit_dict = {
                    "name": unit.name,
                    "icon": unit.icon,
                    "url_name": unit.url_name,
                }

                if unit.show_customers and "customers" in navbar_items:
                    navbar_items["customers"]["units"].append(unit_dict)
                if unit.show_orders and "orders" in navbar_items:
                    navbar_items["orders"]["units"].append(unit_dict)
                if unit.show_inventory and "inventory" in navbar_items:
                    navbar_items["inventory"]["units"].append(unit_dict)
                if unit.show_inspections and "inspections" in navbar_items:
                    navbar_items["inspections"]["units"].append(unit_dict)
                if unit.show_installations and "operations" in navbar_items:
                    navbar_items["operations"]["units"].append(unit_dict)
                if unit.show_manufacturing and "manufacturing" in navbar_items:
                    navbar_items["manufacturing"]["units"].append(unit_dict)
                if unit.show_complaints and "complaints" in navbar_items:
                    navbar_items["complaints"]["units"].append(unit_dict)
                if unit.show_reports and "reports" in navbar_items:
                    navbar_items["reports"]["units"].append(unit_dict)
                if unit.show_accounting and "accounting" in navbar_items:
                    navbar_items["accounting"]["units"].append(unit_dict)
                if unit.show_database and "database" in navbar_items:
                    navbar_items["database"]["units"].append(unit_dict)

    # Inject Traffic Management for authorized users
    if (
        user.is_superuser or getattr(user, "is_traffic_manager", False)
    ) and "operations" in navbar_items:
        navbar_items["operations"]["units"].append(
            {
                "name": "إدارة الحركة",
                "icon": "fa-traffic-light",
                "url_name": "/installations/traffic/",  # Using raw path as url_name is used as href in template
            }
        )

    # Inject My Inspections for authorized users
    if (
        user.is_superuser
        or getattr(user, "is_inspection_manager", False)
        or getattr(user, "is_inspection_technician", False)
    ) and "inspections" in navbar_items:
        navbar_items["inspections"]["units"].append(
            {
                "name": "معايناتي",
                "icon": "fa-clipboard-check",
                "url_name": "/inspections/technician/",
            }
        )

    # Inject Warehouse Actions for authorized users
    if "inventory" in navbar_items:
        is_warehouse_manager = False
        if user.is_superuser:
            is_warehouse_manager = True
        else:
            # Check if user manages any warehouse or is in warehouse groups
            is_manager = Warehouse.objects.filter(manager=user).exists()
            in_group = user.groups.filter(
                name__in=[
                    "مسؤول مخزون",
                    "مسؤول مخازن",
                    "Warehouse Manager",
                    "مسؤول مستودع",
                ]
            ).exists()
            is_warehouse_manager = is_manager or in_group

        if is_warehouse_manager:
            # Add separator logic if needed, but for now just append
            navbar_items["inventory"]["units"].append(
                {
                    "name": "تحويل مخزني جديد",
                    "icon": "fa-bolt",
                    "url_name": "/inventory/stock-transfer/create/",
                }
            )
            navbar_items["inventory"]["units"].append(
                {
                    "name": "جميع التحويلات",
                    "icon": "fa-list",
                    "url_name": "/inventory/stock-transfers/",
                }
            )

        # Warehouse Management link for staff/superusers
        if user.is_superuser or user.is_staff:
            navbar_items["inventory"]["units"].append(
                {
                    "name": "إدارة المستودعات",
                    "icon": "fa-warehouse",
                    "url_name": "/inventory/warehouses/",
                }
            )

    # Inject Installation Accounting Report in Reports section
    if "reports" in navbar_items:
        navbar_items["reports"]["units"].append(
            {
                "name": "محاسبة التركيبات",
                "icon": "fa-tools",
                "url_name": "/installation-accounting/reports/",
            }
        )

    # إزالة العناصر الفارغة
    navbar_items_filtered = {
        key: value for key, value in navbar_items.items() if value["units"]
    }

    return {"navbar_departments": navbar_items_filtered}
