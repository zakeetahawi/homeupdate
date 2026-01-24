"""
دوال مساعدة لتطبيق إعدادات السنوات في جميع أنحاء النظام
"""

from django.db.models import Q
from django.utils import timezone


def apply_default_year_filter(
    queryset, request, date_field="created_at", section_name=None
):
    """
    تطبيق فلتر السنة الافتراضية على أي استعلام

    Args:
        queryset: الاستعلام المراد تطبيق الفلتر عليه
        request: كائن الطلب للحصول على المعاملات
        date_field: اسم حقل التاريخ (افتراضي: created_at)
        section_name: غير مستخدم (تم الاحتفاظ به للتوافق)

    Returns:
        queryset مفلتر حسب السنة
    """
    # الحصول على السنوات المحددة من المعاملات
    selected_years = request.GET.getlist("years")
    year_filter = request.GET.get("year", "")

    # إذا تم تحديد سنوات متعددة
    if selected_years:
        try:
            year_filters = Q()
            for year_str in selected_years:
                if year_str != "all":
                    year = int(year_str)
                    year_filters |= Q(**{f"{date_field}__year": year})

            if year_filters:
                queryset = queryset.filter(year_filters)
        except (ValueError, TypeError):
            pass
    # إذا تم تحديد سنة واحدة فقط
    elif year_filter and year_filter != "all":
        try:
            year = int(year_filter)
            queryset = queryset.filter(**{f"{date_field}__year": year})
        except (ValueError, TypeError):
            pass
    # إذا لم يتم تحديد أي سنة، استخدم السنة الحالية
    else:
        current_year = timezone.now().year
        queryset = queryset.filter(**{f"{date_field}__year": current_year})

    return queryset


def apply_year_filter_for_customers(queryset, request, date_field="created_at"):
    """
    تطبيق فلتر السنة للعملاء (بدون سنة افتراضية)
    """
    selected_years = request.GET.getlist("years")
    year_filter = request.GET.get("year", "")

    if selected_years:
        try:
            year_filters = Q()
            for year_str in selected_years:
                if year_str != "all":
                    year = int(year_str)
                    year_filters |= Q(**{f"{date_field}__year": year})

            if year_filters:
                queryset = queryset.filter(year_filters)
        except (ValueError, TypeError):
            pass
    elif year_filter and year_filter != "all":
        try:
            year = int(year_filter)
            queryset = queryset.filter(**{f"{date_field}__year": year})
        except (ValueError, TypeError):
            pass

    return queryset


def get_dashboard_year_context(request):
    """
    الحصول على معلومات السنة للسياق (ديناميكي بدون قاعدة بيانات)
    """
    current_year = timezone.now().year
    # توليد قائمة سنوات من 2024 حتى السنة الحالية
    available_years = range(2024, current_year + 2)

    selected_year = request.GET.get("year", "")
    selected_years = request.GET.getlist("years")

    return {
        "available_years": list(available_years),
        "default_year": current_year,
        "selected_year": selected_year,
        "selected_years": selected_years,
        "current_year": current_year,
    }


def get_year_filter_display(request):
    """
    الحصول على نص وصفي للفلتر المطبق حالياً
    """
    selected_years = request.GET.getlist("years")
    year_filter = request.GET.get("year", "")

    if selected_years:
        if len(selected_years) == 1:
            return f"السنة: {selected_years[0]}"
        else:
            return f"السنوات: {', '.join(selected_years)}"
    elif year_filter and year_filter != "all":
        return f"السنة: {year_filter}"
    else:
        return f"السنة الافتراضية: {timezone.now().year}"
