"""
Context processor لعرض قائمة الأقسام والوحدات في navbar
Cached per-user for 5 minutes to eliminate 2-5 queries per page load.
"""

from django.core.cache import cache

from accounts.models import Department

_NAVBAR_CACHE_TTL = 300  # 5 دقائق

# روابط مخفية بشكل دائم من الناف بار — لا تتغير حتى لو تغيرت قاعدة البيانات
_HIDDEN_NAVBAR_URLS = {
    "/reports/production/",    # تقارير الإنتاج — أُزيلت بطلب المدير
    "/reports/orders/",        # تقرير الطلبات — أُزيلت بطلب المدير
    "/inventory/transfers/",   # تحويلات مخزنية — أُزيلت بطلب المدير
}

# خريطة مسارات URL → الأدوار المطلوبة (أحد المذكورين يكفي)
# إذا لم يكن المسار هنا أو المستخدم staff/superuser: يُمرَّر بدون قيد
_URL_ROLE_MAP = {
    "/customers/": ["is_salesperson", "is_branch_manager", "is_region_manager", "is_sales_manager", "is_external_sales_director", "is_decorator_dept_manager", "is_decorator_dept_staff"],
    "/orders/": ["is_salesperson", "is_branch_manager", "is_region_manager", "is_sales_manager", "is_external_sales_director", "is_decorator_dept_manager", "is_decorator_dept_staff"],
    "/inventory/": ["is_warehouse_staff", "is_sales_manager", "is_branch_manager"],
    "/inspections/": ["is_inspection_technician", "is_inspection_manager"],
    "/installations/": ["is_installation_manager", "is_traffic_manager"],
    "/manufacturing/": ["is_factory_manager", "is_factory_accountant", "is_factory_receiver"],
    "/cutting/": ["is_factory_manager", "is_factory_accountant"],
    "/complaints/": ["is_salesperson", "is_branch_manager", "is_sales_manager"],
    "/reports/": ["is_sales_manager", "is_branch_manager", "is_region_manager"],
    "/accounting/": ["is_sales_manager"],
    "/factory-accounting/": ["is_factory_accountant", "is_factory_manager"],
    "/external-sales/": ["is_external_sales_director", "is_decorator_dept_manager", "is_decorator_dept_staff"],
    "/database/": ["is_sales_manager", "is_region_manager"],
}


# خريطة المسار → صلاحيات Django المرتبطة (codename)
# إذا المستخدم يملك أي صلاحية django مرتبطة بالقسم، يُسمح له
_URL_DJANGO_PERM_MAP = {
    "/customers/": ["view_customer", "add_customer", "change_customer"],
    "/orders/": ["view_order", "add_order", "change_order"],
    "/inventory/": ["view_product", "change_product", "view_warehouse"],
    "/inspections/": ["view_inspection", "add_inspection", "change_inspection"],
    "/installations/": ["view_installation", "change_installation"],
    "/manufacturing/": ["view_manufacturingorder", "change_manufacturingorder", "can_approve_orders"],
    "/cutting/": ["view_cuttingorder", "change_cuttingorder"],
    "/complaints/": ["view_complaint", "add_complaint"],
    "/reports/": ["view_order", "view_customer"],
    "/accounting/": ["view_transaction", "view_account"],
    "/factory-accounting/": ["view_tailorpayment", "view_cutterpayment"],
    "/external-sales/": ["view_decoratorprofile", "change_decoratorprofile"],
    "/database/": ["change_user", "view_user"],
}


def _is_url_restricted(user, url_name):
    """هل المستخدم محدود الصلاحية لهذا المسار؟"""
    if not url_name or user.is_superuser or user.is_staff:
        return False
    for prefix, roles in _URL_ROLE_MAP.items():
        if url_name.startswith(prefix):
            # 1) فحص الحقول البولينية (الأدوار الأساسية)
            if any(getattr(user, r, False) for r in roles):
                return False
            # 2) فحص أدوار UserRole M2M
            if hasattr(user, "user_roles"):
                for ur in getattr(user, "_prefetched_user_roles", []) or []:
                    role_key = ur.role.name
                    if role_key in roles or f"is_{role_key}" in roles:
                        return False
                # fallback: DB query
                if user.pk:
                    mapped_keys = [r.replace("is_", "") for r in roles]
                    if user.user_roles.filter(role__name__in=mapped_keys).exists():
                        return False
            # 3) فحص صلاحيات Django الفردية / المجموعات
            django_perms = _URL_DJANGO_PERM_MAP.get(prefix, [])
            for perm_codename in django_perms:
                if user.has_perm(f"accounts.{perm_codename}") or user.has_perm(perm_codename):
                    return False
                # Try with common app labels
                for app in ["customers", "orders", "inventory", "inspections",
                            "installations", "manufacturing", "cutting",
                            "complaints", "accounting", "factory_accounting",
                            "external_sales"]:
                    if user.has_perm(f"{app}.{perm_codename}"):
                        return False
            return True
    return False


def navbar_departments(request):
    """
    إرجاع الأقسام والوحدات التي يجب عرضها في navbar
    بناءً على صلاحيات المستخدم وأقسامه — Cached per user
    """
    if not request.user.is_authenticated:
        return {"navbar_departments": []}

    user = request.user
    cache_key = f"ctx_navbar_{user.pk}_{user.is_staff}_{user.is_superuser}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Import Warehouse here to avoid circular imports
    from inventory.models import Warehouse

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
        "external_sales": {
            "name": "المبيعات الخارجية",
            "icon": "fa-handshake",
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
            # تخطي الروابط المحظورة بشكل دائم
            if unit.url_name in _HIDDEN_NAVBAR_URLS:
                continue
            # تحويل الوحدة إلى dictionary
            unit_dict = {
                "name": unit.name,
                "icon": unit.icon,
                "url_name": unit.url_name,
                "disabled": unit.url_name in (None, "", "#"),
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
            if unit.show_external_sales and "external_sales" in navbar_items:
                navbar_items["external_sales"]["units"].append(unit_dict)
    else:
        # المستخدمون العاديون — صلاحيات على مستوى الصفحة
        # Root مُعيَّن مباشرة → كل أبنائه ظاهرون
        # Child مُعيَّن بلا root → هذا الـ Child فقط ظاهر
        direct_root_ids = set()
        direct_child_ids = set()
        for dept_id, parent_id in user_departments.values_list("id", "parent_id"):
            if parent_id is None:
                direct_root_ids.add(dept_id)
            else:
                direct_child_ids.add(dept_id)

        for unit in all_units:
            # التحقق: root مُعيَّن أو child مُعيَّن مباشرة
            is_authorized = (
                unit.parent_id in direct_root_ids
                or unit.id in direct_child_ids
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
                # تخطي الروابط المحظورة بشكل دائم
                if unit.url_name in _HIDDEN_NAVBAR_URLS:
                    continue
                # تحويل الوحدة إلى dictionary — مع تحقق الصلاحية
                restricted = _is_url_restricted(user, unit.url_name)
                unit_dict = {
                    "name": unit.name,
                    "icon": unit.icon,
                    "url_name": unit.url_name,
                    "restricted": restricted,
                    "disabled": unit.url_name in (None, "", "#"),
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
                if unit.show_external_sales and "external_sales" in navbar_items:
                    navbar_items["external_sales"]["units"].append(unit_dict)

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

    # Inject Installation Accounting Report in Reports section
    # Restrict to Superusers only
    if "reports" in navbar_items and user.is_superuser:
        navbar_items["reports"]["units"].append(
            {
                "name": "محاسبة التركيبات",
                "icon": "fa-tools",
                "url_name": "/installation-accounting/reports/",
            }
        )
        navbar_items["reports"]["units"].append(
            {
                "name": "ترتيب الأداء",
                "icon": "fa-trophy",
                "url_name": "/reports/ranking/",
            }
        )

    # Inject External Sales — فقط إذا لم تأتي من الأقسام في قاعدة البيانات
    if (
        not navbar_items.get("external_sales", {}).get("units")
        and (
            user.is_superuser
            or getattr(user, "is_external_sales_director", False)
            or getattr(user, "is_decorator_dept_manager", False)
            or getattr(user, "is_decorator_dept_staff", False)
        )
        and "external_sales" in navbar_items
    ):
        navbar_items["external_sales"]["units"].extend(
            [
                {
                    "name": "مهندسين الديكور",
                    "icon": "fa-paint-brush",
                    "url_name": "/external-sales/decorator/",
                },
                {
                    "name": "البيع بالجملة (قريباً)",
                    "icon": "fa-boxes",
                    "url_name": "#",
                    "disabled": True,
                },
                {
                    "name": "المشاريع (قريباً)",
                    "icon": "fa-project-diagram",
                    "url_name": "#",
                    "disabled": True,
                },
            ]
        )

    # Inject User & Role Management for managers/superusers
    can_manage = (
        user.is_superuser
        or getattr(user, "is_sales_manager", False)
        or getattr(user, "is_region_manager", False)
    )
    if can_manage:
        # Create a "settings" section if needed or add to database
        if "database" not in navbar_items:
            navbar_items["database"] = {
                "name": "إدارة البيانات",
                "icon": "fa-database",
                "url": "/database/",
                "units": [],
            }
        navbar_items["database"]["units"].extend(
            [
                {
                    "name": "إدارة المستخدمين",
                    "icon": "fa-users-cog",
                    "url_name": "/accounts/manage/users/",
                },
                {
                    "name": "لوحة الأدوار",
                    "icon": "fa-user-shield",
                    "url_name": "/accounts/roles/",
                },
            ]
        )

    # إزالة العناصر الفارغة
    navbar_items_filtered = {
        key: value for key, value in navbar_items.items() if value["units"]
    }

    result = {"navbar_departments": navbar_items_filtered}
    cache.set(cache_key, result, _NAVBAR_CACHE_TTL)
    return result
