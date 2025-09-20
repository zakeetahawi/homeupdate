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
    params = request.GET.copy()
    params['page'] = page_number
    
    # تنظيف المعاملات للتأكد من أنها ليست قوائم
    cleaned_params = {}
    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            # إذا كان قائمة، خذ العنصر الأول
            cleaned_params[key] = value[0] if value else ''
        else:
            cleaned_params[key] = value
    
    return f"?{urlencode(cleaned_params)}"

@register.simple_tag(takes_context=True)
def preserve_filters(context, exclude_params=None):
    """
    الحفاظ على جميع معاملات البحث ما عدا المحددة
    """
    request = context['request']
    params = request.GET.copy()
    
    if exclude_params:
        if isinstance(exclude_params, str):
            exclude_params = [exclude_params]
        for param in exclude_params:
            if param in params:
                del params[param]
    
    # تنظيف المعاملات للتأكد من أنها ليست قوائم
    cleaned_params = {}
    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            # إذا كان قائمة، خذ العنصر الأول
            cleaned_params[key] = value[0] if value else ''
        else:
            cleaned_params[key] = value
    
    return urlencode(cleaned_params)

@register.inclusion_tag('core/pagination.html', takes_context=True)
def render_pagination(context, page_obj, extra_classes=''):
    """
    رندر pagination كامل مع الحفاظ على الفلاتر
    """
    return {
        'page_obj': page_obj,
        'request': context['request'],
        'extra_classes': extra_classes,
    }

@register.filter
def add_page_param(url, page_number):
    """
    إضافة معامل page إلى URL موجود
    """
    if '?' in url:
        return f"{url}&page={page_number}"
    else:
        return f"{url}?page={page_number}"

@register.simple_tag(takes_context=True)
def current_url_with_page(context, page_number):
    """
    الحصول على URL الحالي مع تغيير رقم الصفحة فقط
    """
    request = context['request']
    params = request.GET.copy()
    params['page'] = page_number
    
    # إزالة المعاملات الفارغة وتنظيف القوائم
    cleaned_params = {}
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            v = v[0] if v else ''
        if v:  # فقط إذا لم يكن فارغاً
            cleaned_params[k] = v
    
    return f"?{urlencode(cleaned_params)}"

@register.simple_tag(takes_context=True)
def build_filter_url(context, **kwargs):
    """
    بناء URL مع فلاتر جديدة مع الحفاظ على الموجودة
    """
    request = context['request']
    params = request.GET.copy()
    
    # تحديث المعاملات الجديدة
    for key, value in kwargs.items():
        if value is not None and value != '':
            params[key] = value
        elif key in params:
            del params[key]
    
    # إعادة تعيين الصفحة إلى 1 عند تغيير الفلاتر
    params['page'] = 1
    
    # تنظيف المعاملات للتأكد من أنها ليست قوائم
    cleaned_params = {}
    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            # إذا كان قائمة، خذ العنصر الأول
            cleaned_params[key] = value[0] if value else ''
        else:
            cleaned_params[key] = value
    
    return f"?{urlencode(cleaned_params)}"

@register.simple_tag(takes_context=True)
def get_filter_value(context, param_name, default=''):
    """
    الحصول على قيمة فلتر من URL
    """
    request = context['request']
    value = request.GET.get(param_name, default)
    if isinstance(value, (list, tuple)):
        return value[0] if value else default
    return value

@register.simple_tag(takes_context=True)
def is_filter_active(context, param_name, value):
    """
    التحقق من كون فلتر معين نشط
    """
    request = context['request']
    current_value = request.GET.get(param_name)
    if isinstance(current_value, (list, tuple)):
        current_value = current_value[0] if current_value else ''
    return str(current_value) == str(value)

@register.simple_tag(takes_context=True)
def clear_filter_url(context, param_name):
    """
    إزالة فلتر معين من URL
    """
    request = context['request']
    params = request.GET.copy()
    
    if param_name in params:
        del params[param_name]
    
    # إعادة تعيين الصفحة إلى 1
    params['page'] = 1
    
    # تنظيف المعاملات للتأكد من أنها ليست قوائم
    cleaned_params = {}
    for key, value in params.items():
        if isinstance(value, (list, tuple)):
            # إذا كان قائمة، خذ العنصر الأول
            cleaned_params[key] = value[0] if value else ''
        else:
            cleaned_params[key] = value
    
    return f"?{urlencode(cleaned_params)}" if cleaned_params else "?"

@register.simple_tag(takes_context=True)
def clear_all_filters_url(context, keep_params=None):
    """
    إزالة جميع الفلاتر مع الاحتفاظ ببعض المعاملات
    """
    if keep_params is None:
        keep_params = []
    
    request = context['request']
    params = {}
    
    # الاحتفاظ بالمعاملات المحددة فقط
    for param in keep_params:
        if param in request.GET:
            value = request.GET[param]
            if isinstance(value, (list, tuple)):
                value = value[0] if value else ''
            params[param] = value
    
    return f"?{urlencode(params)}" if params else "?"

@register.filter
def get_page_range(page_obj, window=3):
    """
    الحصول على نطاق الصفحات للعرض
    """
    current_page = page_obj.number
    total_pages = page_obj.paginator.num_pages
    
    start = max(1, current_page - window)
    end = min(total_pages + 1, current_page + window + 1)
    
    return range(start, end)

@register.simple_tag
def page_info(page_obj):
    """
    معلومات الصفحة الحالية
    """
    return {
        'current': page_obj.number,
        'total': page_obj.paginator.num_pages,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        'start_index': page_obj.start_index(),
        'end_index': page_obj.end_index(),
        'total_count': page_obj.paginator.count,
    }
