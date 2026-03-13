"""
Views لإدارة المستخدمين — واجهة Bootstrap مخصصة (خارج Django Admin)
User Management Views — Custom Bootstrap Interface
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from accounts.models import ROLE_HIERARCHY, Branch, Role, User, UserRole

logger = logging.getLogger(__name__)


def _can_manage_users(user):
    """التحقق من صلاحية إدارة المستخدمين"""
    return (
        user.is_superuser
        or user.is_sales_manager
        or user.is_region_manager
        or user.is_external_sales_director
        or user.has_perm("accounts.change_user")
    )


# ─── قائمة المستخدمين ────────────────────────────────────────


@login_required
def user_manage_list(request):
    """قائمة المستخدمين مع فلترة وبحث"""
    if not _can_manage_users(request.user):
        messages.error(request, _("ليس لديك صلاحية لإدارة المستخدمين"))
        return redirect("home")

    qs = (
        User.objects.filter(is_active=True)
        .select_related("branch", "assigned_warehouse")
        .prefetch_related("user_roles__role", "departments")
        .order_by("-date_joined")
    )

    # بحث
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
        )

    # فلتر بالفرع
    branch_id = request.GET.get("branch", "")
    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    # فلتر بالدور
    role_filter = request.GET.get("role", "")
    if role_filter:
        field_name = f"is_{role_filter}"
        if hasattr(User, field_name):
            qs = qs.filter(**{field_name: True})

    # فلتر المعطل
    show_inactive = request.GET.get("inactive", "")
    if show_inactive:
        qs = User.objects.filter(is_active=False).select_related(
            "branch", "assigned_warehouse"
        )

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    # بيانات الفلاتر
    branches = Branch.objects.filter(is_active=True).order_by("name")
    role_choices = [
        (key, data["display"])
        for key, data in ROLE_HIERARCHY.items()
        if key not in ("system_admin", "user")
    ]

    # بناء بيانات الأدوار لكل مستخدم — لعرض الأسماء العربية
    role_display_map = {k: v.get("display", k) for k, v in ROLE_HIERARCHY.items()}

    # إحصائيات
    total_active = User.objects.filter(is_active=True).count()
    total_with_roles = sum(1 for u in qs if u.get_active_roles())

    context = {
        "page_obj": page,
        "branches": branches,
        "role_choices": role_choices,
        "role_display_map": role_display_map,
        "q": q,
        "branch_id": branch_id,
        "role_filter": role_filter,
        "total_users": total_active,
        "total_with_roles": total_with_roles,
        "show_inactive": show_inactive,
    }
    return render(request, "accounts/manage/user_list.html", context)


# ─── تعديل مستخدم ────────────────────────────────────────────


@login_required
def user_manage_edit(request, pk):
    """تعديل مستخدم — النموذج الديناميكي"""
    if not _can_manage_users(request.user):
        messages.error(request, _("ليس لديك صلاحية لإدارة المستخدمين"))
        return redirect("home")

    user_obj = get_object_or_404(
        User.objects.select_related("branch", "assigned_warehouse").prefetch_related(
            "user_roles__role", "departments", "managed_branches", "assigned_warehouses"
        ),
        pk=pk,
    )

    # التأكد من صلاحية إدارة هذا المستخدم
    if not request.user.is_superuser and not request.user.can_manage_user(user_obj):
        messages.error(request, _("لا يمكنك إدارة مستخدم بمستوى أعلى"))
        return redirect("accounts:user_manage_list")

    if request.method == "POST":
        return _handle_user_edit_post(request, user_obj)

    # بناء بيانات الأدوار
    role_sections = _build_role_sections(user_obj)
    all_permissions = user_obj.get_role_permissions()
    permissions_with_source = _get_permissions_with_source(user_obj)

    # جلب بيانات المستودعات
    from inventory.models import Warehouse
    all_warehouses = Warehouse.objects.filter(is_active=True).order_by("name")
    managed_branch_ids = list(user_obj.managed_branches.values_list("id", flat=True))
    assigned_warehouse_ids = list(user_obj.assigned_warehouses.values_list("id", flat=True))

    # بناء أقسام المشروع مع الأقسام الفرعية
    department_sections = _build_department_sections(user_obj)
    user_department_ids = set(user_obj.departments.values_list("id", flat=True))

    context = {
        "user_obj": user_obj,
        "role_sections": role_sections,
        "all_permissions": all_permissions,
        "permissions_with_source": permissions_with_source,
        "branches": Branch.objects.filter(is_active=True).order_by("name"),
        "all_warehouses": all_warehouses,
        "managed_branch_ids": managed_branch_ids,
        "assigned_warehouse_ids": assigned_warehouse_ids,
        "role_hierarchy": ROLE_HIERARCHY,
        "department_sections": department_sections,
        "user_department_ids": user_department_ids,
    }
    return render(request, "accounts/manage/user_form.html", context)


def _handle_user_edit_post(request, user_obj):
    """معالجة POST لتعديل المستخدم"""
    # تحديث البيانات الأساسية
    user_obj.first_name = request.POST.get("first_name", user_obj.first_name)
    user_obj.last_name = request.POST.get("last_name", user_obj.last_name)
    user_obj.email = request.POST.get("email", user_obj.email)
    user_obj.phone = request.POST.get("phone", user_obj.phone)

    branch_id = request.POST.get("branch", "")
    user_obj.branch_id = int(branch_id) if branch_id else None

    # تحديث الأدوار
    for field_name in User.ROLE_FIELD_MAP:
        setattr(user_obj, field_name, field_name in request.POST)

    # صلاحيات إضافية
    user_obj.can_export = "can_export" in request.POST
    user_obj.can_edit_price = "can_edit_price" in request.POST
    user_obj.can_apply_administrative_discount = (
        "can_apply_administrative_discount" in request.POST
    )
    user_obj.is_wholesale = "is_wholesale" in request.POST
    user_obj.is_retail = "is_retail" in request.POST

    # مستودع
    warehouse_id = request.POST.get("assigned_warehouse", "")
    user_obj.assigned_warehouse_id = int(warehouse_id) if warehouse_id else None

    try:
        user_obj.save()
    except ValidationError as e:
        for msg in e.messages:
            messages.error(request, msg)
        return redirect("accounts:user_manage_edit", pk=user_obj.pk)

    # Managed branches M2M
    branch_ids = request.POST.getlist("managed_branches")
    if branch_ids:
        user_obj.managed_branches.set(branch_ids)
    else:
        user_obj.managed_branches.clear()

    # Assigned warehouses M2M
    wh_ids = request.POST.getlist("assigned_warehouses")
    if wh_ids:
        user_obj.assigned_warehouses.set(wh_ids)
    else:
        user_obj.assigned_warehouses.clear()

    # Departments M2M
    dept_ids = request.POST.getlist("departments")
    user_obj.departments.set(dept_ids)

    # مسح كاش الناف بار لهذا المستخدم
    for suffix in [f"{user_obj.is_staff}_{user_obj.is_superuser}", "True_True", "True_False", "False_False"]:
        cache.delete(f"ctx_navbar_{user_obj.pk}_{suffix}")

    messages.success(request, _(f"تم تحديث بيانات {user_obj.get_full_name() or user_obj.username} بنجاح"))
    return redirect("accounts:user_manage_edit", pk=user_obj.pk)


# ─── واجهة AJAX للأدوار ──────────────────────────────────────


@login_required
@require_POST
def user_toggle_role_api(request, pk):
    """AJAX: تبديل دور (تفعيل/تعطيل) لمستخدم"""
    if not _can_manage_users(request.user):
        return JsonResponse({"error": "لا صلاحية"}, status=403)

    user_obj = get_object_or_404(User, pk=pk)
    role_field = request.POST.get("role_field", "")

    if role_field not in User.ROLE_FIELD_MAP:
        return JsonResponse({"error": "دور غير صالح"}, status=400)

    current_value = getattr(user_obj, role_field)
    new_value = not current_value

    # استخدام update مباشرة لتجاوز clean() — الدور يُحفظ فوراً
    # التحقق من المستودع يتم عند الحفظ النهائي من النموذج
    User.objects.filter(pk=user_obj.pk).update(**{role_field: new_value})
    user_obj.refresh_from_db()

    active_roles = user_obj.get_active_roles()
    all_perms = user_obj.get_role_permissions()

    return JsonResponse(
        {
            "success": True,
            "field": role_field,
            "value": new_value,
            "active_roles": active_roles,
            "active_roles_display": user_obj.get_active_roles_display(),
            "permissions": all_perms,
            "permissions_count": len(all_perms),
        }
    )


@login_required
def user_permissions_api(request, pk):
    """AJAX: إرجاع ملخص الصلاحيات الفعلية لمستخدم"""
    user_obj = get_object_or_404(User, pk=pk)
    permissions_with_source = _get_permissions_with_source(user_obj)
    return JsonResponse({"permissions": permissions_with_source})


# ─── دوال مساعدة ─────────────────────────────────────────────


def _build_role_sections(user_obj):
    """بناء أقسام الأدوار مع حالتها لكل مستخدم"""
    sections = {
        "sales": {
            "label": "المبيعات والإدارة",
            "icon": "fa-store",
            "roles": [
                ("is_salesperson", "بائع", user_obj.is_salesperson),
                ("is_branch_manager", "مدير فرع", user_obj.is_branch_manager),
                ("is_region_manager", "مدير منطقة", user_obj.is_region_manager),
                ("is_sales_manager", "مدير مبيعات", user_obj.is_sales_manager),
                ("is_traffic_manager", "مدير حركة", user_obj.is_traffic_manager),
            ],
            "has_active": any(
                [
                    user_obj.is_salesperson,
                    user_obj.is_branch_manager,
                    user_obj.is_region_manager,
                    user_obj.is_sales_manager,
                    user_obj.is_traffic_manager,
                ]
            ),
        },
        "factory": {
            "label": "المصنع",
            "icon": "fa-industry",
            "roles": [
                ("is_factory_manager", "مسؤول مصنع", user_obj.is_factory_manager),
                (
                    "is_factory_accountant",
                    "محاسب مصنع",
                    user_obj.is_factory_accountant,
                ),
                ("is_factory_receiver", "مسؤول استلام", user_obj.is_factory_receiver),
            ],
            "has_active": any(
                [
                    user_obj.is_factory_manager,
                    user_obj.is_factory_accountant,
                    user_obj.is_factory_receiver,
                ]
            ),
        },
        "inspections": {
            "label": "المعاينات والتركيبات",
            "icon": "fa-clipboard-check",
            "roles": [
                (
                    "is_inspection_technician",
                    "فني معاينة",
                    user_obj.is_inspection_technician,
                ),
                (
                    "is_inspection_manager",
                    "مسؤول معاينات",
                    user_obj.is_inspection_manager,
                ),
                (
                    "is_installation_manager",
                    "مسؤول تركيبات",
                    user_obj.is_installation_manager,
                ),
            ],
            "has_active": any(
                [
                    user_obj.is_inspection_technician,
                    user_obj.is_inspection_manager,
                    user_obj.is_installation_manager,
                ]
            ),
        },
        "warehouse": {
            "label": "المستودع",
            "icon": "fa-boxes",
            "roles": [
                ("is_warehouse_staff", "موظف مستودع", user_obj.is_warehouse_staff),
            ],
            "has_active": user_obj.is_warehouse_staff,
        },
        "external_sales": {
            "label": "المبيعات الخارجية",
            "icon": "fa-handshake",
            "roles": [
                (
                    "is_external_sales_director",
                    "مدير عام المبيعات الخارجية",
                    user_obj.is_external_sales_director,
                ),
                (
                    "is_decorator_dept_manager",
                    "مدير قسم الديكور",
                    user_obj.is_decorator_dept_manager,
                ),
                (
                    "is_decorator_dept_staff",
                    "موظف قسم الديكور",
                    user_obj.is_decorator_dept_staff,
                ),
            ],
            "has_active": any(
                [user_obj.is_external_sales_director, user_obj.is_decorator_dept_manager, user_obj.is_decorator_dept_staff]
            ),
        },
    }
    return sections


def _get_permissions_with_source(user_obj):
    """إرجاع قائمة الصلاحيات مع مصدر كل صلاحية"""
    result = []
    active_roles = user_obj.get_active_roles()
    if user_obj.is_superuser:
        active_roles = ["system_admin"]

    seen = set()
    for role_key in active_roles:
        role_data = ROLE_HIERARCHY.get(role_key, {})
        role_display = role_data.get("display", role_key)
        for perm in role_data.get("permissions", []):
            if perm not in seen:
                seen.add(perm)
                result.append(
                    {"permission": perm, "source": role_display, "type": "direct"}
                )

    # صلاحيات موروثة
    for inherited_role in user_obj.get_inherited_roles():
        role_data = ROLE_HIERARCHY.get(inherited_role, {})
        role_display = role_data.get("display", inherited_role)
        for perm in role_data.get("permissions", []):
            if perm not in seen:
                seen.add(perm)
                result.append(
                    {
                        "permission": perm,
                        "source": role_display,
                        "type": "inherited",
                    }
                )

    return result


# ─── Department icons map ─────────────────────────────────────
_DEPT_ICONS = {
    "customers": "fa-users",
    "orders": "fa-shopping-cart",
    "inventory": "fa-boxes",
    "inspections": "fa-clipboard-check",
    "installations": "fa-tools",
    "manufacturing": "fa-industry",
    "complaints": "fa-exclamation-triangle",
    "reports": "fa-chart-bar",
    "accounting": "fa-calculator",
    "cutting": "fa-cut",
    "data_management": "fa-database",
    "database": "fa-database",
    "external_sales": "fa-handshake",
}


def _build_department_sections(user_obj):
    """بناء أقسام المشروع — أقسام رئيسية وفرعية مع حالة التعيين"""
    from accounts.models import Department

    roots = (
        Department.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("order")
    )

    user_dept_ids = set(user_obj.departments.values_list("id", flat=True))

    sections = []
    for root in roots:
        children = list(root.children.filter(is_active=True).order_by("order"))
        assigned_count = sum(1 for c in children if c.id in user_dept_ids)
        # Include root in checked too
        root_assigned = root.id in user_dept_ids
        sections.append({
            "root": root,
            "icon": root.icon or _DEPT_ICONS.get(root.code, "fa-folder"),
            "children": children,
            "assigned_count": assigned_count,
            "root_assigned": root_assigned,
        })
    return sections
