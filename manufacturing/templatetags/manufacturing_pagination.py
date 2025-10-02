"""
Template tags خاصة بـ manufacturing للتعامل مع pagination مع الحفاظ على الفلاتر المتعددة
"""

from django import template
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def manufacturing_pagination_url(context, page_number):
    """
    إنشاء URL للصفحة مع الحفاظ على جميع معاملات البحث للتصنيع
    """
    request = context["request"]
    params = request.GET.copy()

    # التأكد من أن page_number هو integer وليس list أو أي نوع آخر
    if isinstance(page_number, (list, tuple)):
        page_number = page_number[0] if page_number else 1

    try:
        page_number = int(page_number)
    except (ValueError, TypeError):
        page_number = 1

    params["page"] = page_number

    # قائمة بالمعاملات التي يجب أن تكون arrays (فلاتر متعددة الاختيار) خاصة بالتصنيع
    array_params = [
        "status",
        "branch",
        "order_type",
        "production_line",
        "search_columns",
    ]

    # بناء URL مع الحفاظ على الفلاتر المتعددة
    url_parts = []

    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            # إذا كان value هو list وهو فلتر متعدد الاختيار، احتفظ بجميع القيم
            if key in array_params:
                for v in value:
                    if v and str(v).strip():
                        url_parts.append(f"{key}={v}")
            else:
                # إذا كان value هو list وليس فلتر متعدد الاختيار، خذ العنصر الأول
                v = value[0] if value else ""
                if v and str(v).strip():
                    url_parts.append(f"{key}={v}")
        else:
            if value and str(value).strip():
                url_parts.append(f"{key}={value}")

    return f"?{'&'.join(url_parts)}" if url_parts else "?"


@register.inclusion_tag("manufacturing/pagination.html", takes_context=True)
def render_manufacturing_pagination(context, page_obj, extra_classes=""):
    """
    رندر pagination خاص بالتصنيع مع الحفاظ على الفلاتر المتعددة
    """
    return {
        "page_obj": page_obj,
        "request": context["request"],
        "extra_classes": extra_classes,
    }


@register.filter
def get_manufacturing_page_range(page_obj, window=3):
    """
    الحصول على نطاق الصفحات للعرض في التصنيع
    """
    try:
        current_page = int(page_obj.number)
        total_pages = int(page_obj.paginator.num_pages)
        window = int(window)

        start = max(1, current_page - window)
        end = min(total_pages + 1, current_page + window + 1)

        return list(range(start, end))
    except (ValueError, AttributeError, TypeError):
        return [1]
