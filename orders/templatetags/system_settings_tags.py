"""
Template tags لإعدادات النظام
System Settings Template Tags
"""
from django import template
from orders.models_settings import SystemSettings

register = template.Library()


@register.simple_tag
def get_system_setting(key):
    """
    الحصول على قيمة إعداد معين
    
    الاستخدام:
    {% get_system_setting 'order_system' %}
    """
    settings = SystemSettings.get_settings()
    return getattr(settings, key, None)


@register.simple_tag
def is_wizard_enabled():
    """
    التحقق من تفعيل نظام الويزارد
    
    الاستخدام:
    {% is_wizard_enabled %}
    """
    return SystemSettings.is_wizard_enabled()


@register.simple_tag
def is_legacy_enabled():
    """
    التحقق من تفعيل النظام القديم
    
    الاستخدام:
    {% is_legacy_enabled %}
    """
    return SystemSettings.is_legacy_enabled()


@register.inclusion_tag('orders/tags/order_create_buttons.html')
def show_order_create_buttons():
    """
    عرض أزرار إنشاء الطلبات حسب الإعدادات
    
    الاستخدام:
    {% show_order_create_buttons %}
    """
    settings = SystemSettings.get_settings()
    return {
        'show_wizard': settings.order_system in ['wizard', 'both'] and not settings.hide_wizard_system,
        'show_legacy': settings.order_system in ['legacy', 'both'] and not settings.hide_legacy_system,
    }


@register.simple_tag
def get_edit_url_for_order(order):
    """
    الحصول على رابط التعديل المناسب للطلب
    
    الاستخدام:
    {% get_edit_url_for_order order %}
    """
    from django.urls import reverse
    
    settings = SystemSettings.get_settings()
    
    # إذا كانت الأولوية للويزارد
    if settings.edit_priority == 'wizard':
        return reverse('orders:wizard_edit', args=[order.pk])
    
    # إذا كانت الأولوية للنظام القديم
    elif settings.edit_priority == 'legacy':
        return reverse('orders:order_edit', args=[order.pk])
    
    # حسب طريقة الإنشاء (افتراضي)
    else:
        if order.creation_method == 'wizard':
            return reverse('orders:wizard_edit', args=[order.pk])
        else:
            return reverse('orders:order_edit', args=[order.pk])


@register.filter
def get_tailoring_types(dummy=None):
    """
    الحصول على أنواع التفصيل
    
    الاستخدام:
    {% for type in ''|get_tailoring_types %}
    """
    return SystemSettings.get_tailoring_types()


@register.filter
def get_fabric_types(dummy=None):
    """
    الحصول على أنواع الأقمشة
    
    الاستخدام:
    {% for type in ''|get_fabric_types %}
    """
    return SystemSettings.get_fabric_types()


@register.filter
def get_installation_types(dummy=None):
    """
    الحصول على أنواع التركيب
    
    الاستخدام:
    {% for type in ''|get_installation_types %}
    """
    return SystemSettings.get_installation_types()


@register.filter
def get_payment_methods(dummy=None):
    """
    الحصول على طرق الدفع
    
    الاستخدام:
    {% for method in ''|get_payment_methods %}
    """
    return SystemSettings.get_payment_methods()


@register.inclusion_tag('orders/tags/edit_button.html')
def show_order_edit_button(order):
    """
    عرض زر التعديل المناسب للطلب
    
    الاستخدام:
    {% show_order_edit_button order %}
    """
    from django.urls import reverse
    
    settings = SystemSettings.get_settings()
    
    # تحديد الرابط المناسب
    if settings.edit_priority == 'wizard':
        url = reverse('orders:wizard_edit', args=[order.pk])
        label = 'تعديل (ويزارد)'
    elif settings.edit_priority == 'legacy':
        url = reverse('orders:order_edit', args=[order.pk])
        label = 'تعديل'
    else:
        if order.creation_method == 'wizard':
            url = reverse('orders:wizard_edit', args=[order.pk])
            label = 'تعديل (ويزارد)'
        else:
            url = reverse('orders:order_edit', args=[order.pk])
            label = 'تعديل'
    
    return {
        'order': order,
        'edit_url': url,
        'label': label,
        'is_wizard': order.creation_method == 'wizard'
    }
