from django.core.cache import cache
from django.utils import timezone

from accounts.models import FooterSettings
from accounts.models import SystemSettings as AccountsSystemSettings

from .models import BranchMessage, CompanyInfo, Department

# ====== Cache TTL Constants ======
_CACHE_TTL_LONG = 600  # 10 دقائق — بيانات تتغير نادراً
_CACHE_TTL_SHORT = 60  # 1 دقيقة — بيانات تتغير أحياناً


def departments(request):
    """
    Context processor to add departments to all templates in a hierarchical
    structure. Cached per-user for 10 minutes.
    """
    if not request.user.is_authenticated:
        return {
            "all_departments": [],
            "parent_departments": [],
            "user_departments": [],
            "user_parent_departments": [],
        }

    user = request.user
    cache_key = f"ctx_departments_{user.pk}_{user.is_superuser}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Get all active departments
    all_departments = list(Department.objects.filter(is_active=True).order_by("order"))
    parent_departments = [d for d in all_departments if d.parent_id is None]

    if user.is_superuser:
        user_departments = all_departments
        user_parent_departments = parent_departments
    else:
        user_departments = list(
            user.departments.filter(is_active=True).order_by("order")
        )
        user_parent_ids = set()
        for dept in user_departments:
            dept_id = dept.parent_id if dept.parent_id else dept.id
            user_parent_ids.add(dept_id)
        user_parent_departments = [
            d for d in all_departments if d.id in user_parent_ids
        ]

    result = {
        "all_departments": all_departments,
        "parent_departments": parent_departments,
        "user_departments": user_departments,
        "user_parent_departments": user_parent_departments,
    }
    cache.set(cache_key, result, _CACHE_TTL_LONG)
    return result


def company_info(request):
    """توفير معلومات الشركة لجميع القوالب — Cached 10 minutes"""
    cached = cache.get("ctx_company_info")
    if cached is not None:
        return cached

    try:
        company = CompanyInfo.objects.first()
        if not company:
            company = CompanyInfo.objects.create(
                name="الخواجة للستائر والمفروشات",
                description="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
                version="1.0.0",
                release_date="2025-04-30",
                developer="zakee tahawi",
                working_hours="9 صباحاً - 5 مساءً",
                copyright_text="جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi",
            )
    except Exception:
        company = CompanyInfo(
            name="الخواجة للستائر والمفروشات",
            description="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
            version="1.0.0",
            release_date="2025-04-30",
            developer="zakee tahawi",
            working_hours="9 صباحاً - 5 مساءً",
            copyright_text="جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi",
        )

    if hasattr(company, "logo") and company.logo:
        try:
            company.logo.url
        except (ValueError, FileNotFoundError):
            company.logo = None

    result = {"company_info": company}
    cache.set("ctx_company_info", result, _CACHE_TTL_LONG)
    return result


def footer_settings(request):
    """توفير إعدادات التذييل لجميع القوالب — Cached 10 minutes"""
    cached = cache.get("ctx_footer_settings")
    if cached is not None:
        return cached

    try:
        fs = FooterSettings.objects.first()
        if not fs:
            fs = FooterSettings.objects.create(
                left_column_title="عن الشركة",
                left_column_text="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
                middle_column_title="روابط سريعة",
                right_column_title="تواصل معنا",
            )
    except Exception:
        fs = FooterSettings(
            left_column_title="عن الشركة",
            left_column_text="نظام متكامل لإدارة العملاء والمبيعات والإنتاج والمخزون",
            middle_column_title="روابط سريعة",
            right_column_title="تواصل معنا",
        )

    result = {"footer_settings": fs, "current_year": timezone.now().year}
    cache.set("ctx_footer_settings", result, _CACHE_TTL_LONG)
    return result


def system_settings(request):
    """توفير إعدادات النظام لجميع القوالب — Cached 1 hour"""
    _CACHE_KEY = "ctx_system_settings"
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    try:
        settings, _created = AccountsSystemSettings.objects.get_or_create(pk=1)
    except Exception:
        return {
            "system_settings": None,
            "currency_code": "SAR",
            "currency_symbol": "ر.س",
        }

    result = {
        "system_settings": settings,
        "currency_code": settings.currency,
        "currency_symbol": settings.CURRENCY_SYMBOLS.get(
            settings.currency, settings.currency
        ),
    }
    cache.set(_CACHE_KEY, result, 3600)
    return result


def user_context(request):
    """Context processor to add user-specific context to all templates."""
    context = {}
    if request.user.is_authenticated:
        has_branch = hasattr(request.user, "branch")
        context["user_branch"] = request.user.branch if has_branch else None
    return context


def branch_messages(request):
    """
    Context processor to add branch messages to templates.
    Only loads messages for the home page.
    """
    if request.user.is_authenticated and request.path == "/":
        from django.db.models import Q

        messages_query = Q(
            is_active=True, start_date__lte=timezone.now(), end_date__gte=timezone.now()
        )

        # إضافة الرسائل العامة
        messages_query &= Q(is_for_all_branches=True)

        # إضافة رسائل الفرع المحدد إذا كان للمستخدم فرع
        if hasattr(request.user, "branch") and request.user.branch:
            messages_query |= Q(
                branch=request.user.branch,
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now(),
            )

        messages = BranchMessage.objects.filter(messages_query).order_by("-created_at")
        return {"branch_messages": messages}
    return {"branch_messages": []}


def notifications_context(request):
    """إضافة عدادات الإشعارات إلى السياق — Cached 30s per user"""
    if not request.user.is_authenticated:
        return {}

    user = request.user
    cache_key = f"ctx_notifications_{user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from .models import InternalMessage

    internal_messages_unread = InternalMessage.get_unread_count(user)

    result = {
        "simple_notifications_unread": 0,
        "total_notifications_unread": 0,
        "internal_messages_unread": internal_messages_unread,
    }
    cache.set(cache_key, result, 30)
    return result


def admin_notifications_context(request):
    """إضافة عدادات الإشعارات لـ admin panel"""
    context = {}

    if request.user.is_authenticated and (
        request.user.is_staff or request.user.is_superuser
    ):
        # الإشعارات - تم إزالتها
        total_simple = 0
        unread_simple = 0
        urgent_simple = 0

        context.update(
            {
                "admin_simple_total": total_simple,
                "admin_simple_unread": unread_simple,
                "admin_simple_urgent": urgent_simple,
                "admin_total_unread": unread_simple,
            }
        )

    return context
