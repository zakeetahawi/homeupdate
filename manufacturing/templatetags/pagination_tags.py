"""
Template tags للتعامل مع pagination مع الحفاظ على الفلاتر
"""

from django import template
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def pagination_url(context, page_number):
    """
    إنشاء URL للصفحة مع الحفاظ على جميع معاملات البحث
    """
    request = context['request']
    params = {}

    # نسخ المعاملات مع تحويل القوائم إلى قيم مفردة
    for key, value_list in request.GET.lists():
        if key != 'page':  # تجاهل page الحالية
            if len(value_list) == 1:
                params[key] = value_list[0]
            elif len(value_list) > 1:
                # للمعاملات المتعددة مثل status، نضعها كقائمة
                params[key] = value_list

    params['page'] = page_number
    return f"?{urlencode(params, doseq=True)}"

@register.inclusion_tag('core/pagination.html', takes_context=True)
def render_pagination(context, page_obj, extra_classes=''):
    """
    عرض pagination مع الحفاظ على جميع معاملات البحث
    """
    request = context['request']

    # الحصول على معاملات البحث الحالية (بدون page)
    params = {}
    for key, value_list in request.GET.lists():
        if key != 'page':  # تجاهل page الحالية
            if len(value_list) == 1:
                params[key] = value_list[0]
            elif len(value_list) > 1:
                # للمعاملات المتعددة مثل status، نضعها كقائمة
                params[key] = value_list

    # إنشاء قائمة الصفحات للعرض
    page_range = []
    current_page = page_obj.number
    total_pages = page_obj.paginator.num_pages

    # منطق عرض الصفحات
    if total_pages <= 7:
        # إذا كان العدد الكلي للصفحات 7 أو أقل، اعرض جميع الصفحات
        page_range = list(range(1, total_pages + 1))
    else:
        # إذا كان العدد أكبر من 7، اعرض الصفحات بذكاء
        if current_page <= 4:
            # إذا كانت الصفحة الحالية في البداية
            page_range = list(range(1, 6)) + ['...', total_pages]
        elif current_page >= total_pages - 3:
            # إذا كانت الصفحة الحالية في النهاية
            page_range = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else:
            # إذا كانت الصفحة الحالية في المنتصف
            page_range = [1, '...'] + list(range(current_page - 1, current_page + 2)) + ['...', total_pages]

    return {
        'page_obj': page_obj,
        'page_range': page_range,
        'query_params': urlencode(params, doseq=True),
        'extra_classes': extra_classes,
        'request': request,
    }

@register.simple_tag(takes_context=True)
def preserve_filters(context, **kwargs):
    """
    الحفاظ على الفلاتر الحالية مع إضافة فلاتر جديدة
    """
    request = context['request']
    params = request.GET.copy()

    # إضافة أو تحديث المعاملات الجديدة
    for key, value in kwargs.items():
        if value is not None and value != '':
            params[key] = value
        elif key in params:
            del params[key]

    return urlencode(params)

@register.simple_tag(takes_context=True)
def get_filter_url(context, **kwargs):
    """
    إنشاء URL مع فلاتر محددة
    """
    request = context['request']
    params = request.GET.copy()

    # إزالة page عند تطبيق فلاتر جديدة
    if 'page' in params:
        del params['page']

    # إضافة أو تحديث المعاملات الجديدة
    for key, value in kwargs.items():
        if value is not None and value != '':
            params[key] = value
        elif key in params:
            del params[key]

    return f"?{urlencode(params)}"

@register.simple_tag(takes_context=True)
def is_filter_active(context, filter_name, filter_value):
    """
    التحقق من أن فلتر معين نشط
    """
    request = context['request']
    current_value = request.GET.get(filter_name)
    return str(current_value) == str(filter_value)

@register.simple_tag(takes_context=True)
def get_sort_url(context, field):
    """
    إنشاء URL للترتيب مع الحفاظ على الفلاتر
    """
    request = context['request']
    params = request.GET.copy()

    # إزالة page عند تغيير الترتيب
    if 'page' in params:
        del params['page']

    current_sort = params.get('sort', '')

    # تحديد الترتيب الجديد
    if current_sort == field:
        # إذا كان الترتيب الحالي نفس الحقل، اعكس الترتيب
        new_sort = f'-{field}'
    elif current_sort == f'-{field}':
        # إذا كان الترتيب الحالي عكسي، أزل الترتيب
        if 'sort' in params:
            del params['sort']
        return f"?{urlencode(params)}"
    else:
        # ترتيب جديد
        new_sort = field

    params['sort'] = new_sort
    return f"?{urlencode(params)}"

@register.simple_tag(takes_context=True)
def get_sort_icon(context, field):
    """
    الحصول على أيقونة الترتيب للحقل
    """
    request = context['request']
    current_sort = request.GET.get('sort', '')

    if current_sort == field:
        return mark_safe('<i class="fas fa-sort-up"></i>')
    elif current_sort == f'-{field}':
        return mark_safe('<i class="fas fa-sort-down"></i>')
    else:
        return mark_safe('<i class="fas fa-sort"></i>')

@register.filter
def get_item(dictionary, key):
    """
    الحصول على قيمة من dictionary باستخدام مفتاح متغير
    """
    return dictionary.get(key)

@register.simple_tag
def url_replace(request, field, value):
    """
    استبدال قيمة معاملة في URL مع الحفاظ على باقي المعاملات
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()

@register.simple_tag
def multiply(value, arg):
    """
    ضرب قيمتين
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_page_range(page_obj):
    """
    إنشاء قائمة الصفحات للعرض مع منطق ذكي
    """
    current_page = page_obj.number
    total_pages = page_obj.paginator.num_pages

    # منطق عرض الصفحات
    if total_pages <= 7:
        # إذا كان العدد الكلي للصفحات 7 أو أقل، اعرض جميع الصفحات
        return list(range(1, total_pages + 1))
    else:
        # إذا كان العدد أكبر من 7، اعرض الصفحات بذكاء
        if current_page <= 4:
            # إذا كانت الصفحة الحالية في البداية
            return list(range(1, 6)) + ['...', total_pages]
        elif current_page >= total_pages - 3:
            # إذا كانت الصفحة الحالية في النهاية
            return [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else:
            # إذا كانت الصفحة الحالية في المنتصف
            return [1, '...'] + list(range(current_page - 1, current_page + 2)) + ['...', total_pages]