"""
Template tags لإنشاء meta descriptions تلقائياً للصفحات
يولد وصف SEO ديناميكي بناءً على سياق الصفحة (قائمة، تفاصيل، نموذج، تقرير)
"""

from django import template
from django.apps import apps
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def get_meta_description(context, custom_description=None):
    """
    إنشاء meta description تلقائياً بناءً على سياق الصفحة

    Args:
        context: سياق القالب (يحتوي على request، view، object، إلخ)
        custom_description: وصف مخصص (اختياري) - يتجاوز التوليد التلقائي

    Returns:
        نص وصف SEO بحد أقصى 160 حرف

    Examples:
        {% get_meta_description %} - توليد تلقائي
        {% get_meta_description "وصف مخصص للصفحة" %} - وصف يدوي

    يدعم أنماط العرض التالية:
        - List Views: "قائمة {{ model_verbose_name_plural }} | نظام الخواجه"
        - Detail Views: "{{ object }} - {{ model_verbose_name }} | نظام الخواجه"
        - Create/Form Views: "إضافة {{ model_verbose_name }} جديد | نظام الخواجه"
        - Update/Edit Views: "تعديل {{ object }} | نظام الخواجه"
        - Dashboard: "لوحة تحكم {{ app_label }} | نظام الخواجه"
        - Reports: "تقرير {{ report_name }} | نظام الخواجه"
    """
    # إذا تم تمرير وصف مخصص، استخدمه مباشرة
    if custom_description:
        return _truncate_description(custom_description)

    request = context.get("request")
    if not request:
        return _get_fallback_description()

    # الحصول على معلومات الـ View
    view = context.get("view")
    resolver_match = getattr(request, "resolver_match", None)

    # محاولة بناء الوصف بناءً على نوع الصفحة
    description = None

    # 1. Detail View - صفحة تفاصيل كائن واحد
    if context.get("object"):
        description = _get_detail_description(context)

    # 2. List View - صفحة قائمة كائنات
    elif context.get("object_list") is not None or context.get("page_obj"):
        description = _get_list_description(context)

    # 3. Form View - صفحة إضافة أو تعديل
    elif context.get("form"):
        description = _get_form_description(context)

    # 4. Report View - صفحة تقرير
    elif resolver_match and "report" in resolver_match.url_name:
        description = _get_report_description(context)

    # 5. Dashboard View - لوحة تحكم
    elif resolver_match and (
        "dashboard" in resolver_match.url_name or "home" in resolver_match.url_name
    ):
        description = _get_dashboard_description(context)

    # 6. Fallback - وصف افتراضي
    if not description:
        description = _get_fallback_description()

    return _truncate_description(description)


def _get_detail_description(context):
    """
    إنشاء وصف لصفحة التفاصيل
    Format: "{{ object }} - {{ model_verbose_name }} | نظام الخواجه"
    """
    obj = context.get("object")
    model_name = _get_model_verbose_name(obj)

    # استخدام __str__ للكائن
    obj_str = str(obj) if obj else ""

    # تنظيف النص من أي HTML
    obj_str = escape(obj_str)

    if obj_str and model_name:
        return f"{obj_str} - {model_name} | نظام الخواجه"
    elif model_name:
        return f"تفاصيل {model_name} | نظام الخواجه"
    else:
        return "تفاصيل العنصر | نظام الخواجه"


def _get_list_description(context):
    """
    إنشاء وصف لصفحة القائمة
    Format: "قائمة {{ model_verbose_name_plural }} - {{ count }} عنصر | نظام الخواجه"
    """
    # الحصول على القائمة
    object_list = context.get("object_list")
    page_obj = context.get("page_obj")

    # محاولة الحصول على العدد
    count = 0
    if page_obj and hasattr(page_obj, "paginator"):
        count = page_obj.paginator.count
    elif object_list is not None:
        try:
            count = (
                len(object_list)
                if hasattr(object_list, "__len__")
                else object_list.count()
            )
        except (TypeError, AttributeError):
            count = 0

    # الحصول على اسم النموذج
    model_name_plural = None
    if object_list and hasattr(object_list, "model"):
        model = object_list.model
        model_name_plural = _get_model_verbose_name_plural(model)
    elif (
        page_obj
        and hasattr(page_obj, "object_list")
        and hasattr(page_obj.object_list, "model")
    ):
        model = page_obj.object_list.model
        model_name_plural = _get_model_verbose_name_plural(model)

    # الحصول على اسم التطبيق
    app_label = _get_app_label(context)

    if model_name_plural:
        if count > 0:
            return f"قائمة {model_name_plural} - {count} عنصر | نظام الخواجه"
        else:
            return f"قائمة {model_name_plural} | نظام الخواجه"
    elif app_label:
        return f"قائمة {app_label} | نظام الخواجه"
    else:
        return "قائمة العناصر | نظام الخواجه"


def _get_form_description(context):
    """
    إنشاء وصف لصفحة النموذج (إضافة أو تعديل)
    Format:
        - Create: "إضافة {{ model_verbose_name }} جديد | نظام الخواجه"
        - Update: "تعديل {{ object }} | نظام الخواجه"
    """
    obj = context.get("object")
    form = context.get("form")

    # الحصول على اسم النموذج
    model_name = None
    if obj:
        model_name = _get_model_verbose_name(obj)
    elif form and hasattr(form, "_meta") and hasattr(form._meta, "model"):
        model = form._meta.model
        model_name = _get_model_verbose_name_from_class(model)

    # تحديد نوع العملية (إضافة أو تعديل)
    request = context.get("request")
    is_update = obj is not None

    # التحقق من URL للتأكد
    if request and hasattr(request, "resolver_match"):
        url_name = request.resolver_match.url_name
        if "update" in url_name or "edit" in url_name:
            is_update = True
        elif "create" in url_name or "add" in url_name:
            is_update = False

    if is_update:
        obj_str = escape(str(obj)) if obj else ""
        if obj_str and model_name:
            return f"تعديل {obj_str} | نظام الخواجه"
        elif model_name:
            return f"تعديل {model_name} | نظام الخواجه"
        else:
            return "تعديل العنصر | نظام الخواجه"
    else:
        if model_name:
            return f"إضافة {model_name} جديد | نظام الخواجه"
        else:
            return "إضافة عنصر جديد | نظام الخواجه"


def _get_report_description(context):
    """
    إنشاء وصف لصفحة التقرير
    Format: "تقرير {{ report_name }} | نظام الخواجه"
    """
    # محاولة الحصول على اسم التقرير من السياق
    report_name = context.get("report_name") or context.get("report_title")

    # محاولة استخراج اسم التقرير من URL
    if not report_name:
        request = context.get("request")
        if request and hasattr(request, "resolver_match"):
            url_name = request.resolver_match.url_name
            # تحويل اسم URL إلى نص مقروء
            report_name = url_name.replace("_", " ").replace("-", " ").title()

    app_label = _get_app_label(context)

    if report_name:
        report_name = escape(str(report_name))
        return f"تقرير {report_name} | نظام الخواجه"
    elif app_label:
        return f"تقارير {app_label} | نظام الخواجه"
    else:
        return "التقارير | نظام الخواجه"


def _get_dashboard_description(context):
    """
    إنشاء وصف للوحة التحكم
    Format: "لوحة تحكم {{ app_label }} | نظام الخواجه"
    """
    app_label = _get_app_label(context)

    # محاولة الحصول على اسم القسم من السياق
    section_name = context.get("section_name") or context.get("dashboard_title")

    if section_name:
        section_name = escape(str(section_name))
        return f"لوحة تحكم {section_name} | نظام الخواجه"
    elif app_label:
        return f"لوحة تحكم {app_label} | نظام الخواجه"
    else:
        return "لوحة التحكم الرئيسية | نظام الخواجه"


def _get_fallback_description():
    """
    وصف افتراضي عندما لا يمكن تحديد نوع الصفحة
    """
    return "نظام الخواجه - نظام إدارة شامل للطلبات والتصنيع والتركيب والمخزون"


def _get_model_verbose_name(obj):
    """
    الحصول على الاسم المقروء للنموذج من كائن
    """
    if not obj:
        return None

    try:
        if hasattr(obj, "_meta"):
            return obj._meta.verbose_name
        elif hasattr(obj.__class__, "_meta"):
            return obj.__class__._meta.verbose_name
    except (AttributeError, TypeError):
        pass

    return None


def _get_model_verbose_name_from_class(model_class):
    """
    الحصول على الاسم المقروء للنموذج من الـ class
    """
    if not model_class:
        return None

    try:
        if hasattr(model_class, "_meta"):
            return model_class._meta.verbose_name
    except (AttributeError, TypeError):
        pass

    return None


def _get_model_verbose_name_plural(model_or_class):
    """
    الحصول على الاسم المقروء بصيغة الجمع للنموذج
    """
    if not model_or_class:
        return None

    try:
        if hasattr(model_or_class, "_meta"):
            return model_or_class._meta.verbose_name_plural
    except (AttributeError, TypeError):
        pass

    return None


def _get_app_label(context):
    """
    الحصول على اسم التطبيق من السياق
    """
    request = context.get("request")
    if not request or not hasattr(request, "resolver_match"):
        return None

    app_name = request.resolver_match.app_name

    if not app_name:
        return None

    # محاولة الحصول على verbose_name للتطبيق
    try:
        app_config = apps.get_app_config(app_name)
        if hasattr(app_config, "verbose_name"):
            return app_config.verbose_name
    except (LookupError, AttributeError):
        pass

    # تحويل اسم التطبيق إلى نص مقروء
    app_labels = {
        "inventory": "المخزون",
        "orders": "الطلبات",
        "installations": "التركيبات",
        "customers": "العملاء",
        "manufacturing": "التصنيع",
        "inspections": "المعاينات",
        "accounting": "المحاسبة",
        "complaints": "الشكاوى",
        "reports": "التقارير",
        "notifications": "الإشعارات",
        "whatsapp": "واتساب",
        "backup_system": "النسخ الاحتياطي",
        "core": "النظام",
        "accounts": "الحسابات",
        "crm": "إدارة العملاء",
        "cutting": "القص",
        "public": "العام",
        "user_activity": "نشاط المستخدمين",
        "odoo_db_manager": "إدارة Odoo",
    }

    return app_labels.get(app_name, app_name)


def _truncate_description(description, max_length=160):
    """
    اقتصاص الوصف ليكون ضمن الحد المسموح لـ SEO (160 حرف)

    Args:
        description: النص المراد اقتصاصه
        max_length: الحد الأقصى للطول (افتراضي: 160)

    Returns:
        نص مقتصّ بشكل نظيف
    """
    if not description:
        return _get_fallback_description()

    # تنظيف النص من المسافات الزائدة
    description = " ".join(str(description).split())

    # إذا كان النص ضمن الحد المسموح، أرجعه كما هو
    if len(description) <= max_length:
        return description

    # اقتصاص النص عند آخر كلمة كاملة
    truncated = description[:max_length].rsplit(" ", 1)[0]

    # إضافة ... إذا تم الاقتصاص
    if len(truncated) < len(description):
        truncated += "..."

    return truncated


@register.simple_tag(takes_context=True)
def render_meta_description(context, custom_description=None):
    """
    رندر meta description tag كامل جاهز للإدراج في <head>

    Args:
        context: سياق القالب
        custom_description: وصف مخصص (اختياري)

    Returns:
        HTML meta tag جاهز

    Example:
        {% render_meta_description %}
        {% render_meta_description "وصف مخصص للصفحة" %}
    """
    description = get_meta_description(context, custom_description)

    # تنظيف النص من علامات الاقتباس لتجنب مشاكل HTML
    description = description.replace('"', "&quot;").replace("'", "&#39;")

    html = f'<meta name="description" content="{description}">'

    return mark_safe(html)
