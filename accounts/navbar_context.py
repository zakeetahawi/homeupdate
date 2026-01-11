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
        "installations": {
            "name": "التركيبات",
            "icon": "fa-tools",
            "url": "/installations/",
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
            if unit.show_installations and "installations" in navbar_items:
                navbar_items["installations"]["units"].append(unit_dict)
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
                if unit.show_installations and "installations" in navbar_items:
                    navbar_items["installations"]["units"].append(unit_dict)
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

    # إزالة العناصر الفارغة
    navbar_items_filtered = {
        key: value for key, value in navbar_items.items() if value["units"]
    }

    return {"navbar_departments": navbar_items_filtered}
