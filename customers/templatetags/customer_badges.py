"""
Template tags for customer type badges
"""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def customer_type_badge(customer, size='sm'):
    """
    عرض بادج نوع العميل
    
    Usage:
        {% load customer_badges %}
        {% customer_type_badge customer %}
        {% customer_type_badge customer 'md' %}
        {% customer_type_badge customer 'lg' %}
    """
    if not customer:
        return ''
    
    customer_type_code = getattr(customer, 'customer_type', None)
    if not customer_type_code:
        return ''
    
    from customers.models import CustomerType
    try:
        ct = CustomerType.objects.get(code=customer_type_code)
    except CustomerType.DoesNotExist:
        return ''
    
    return ct.get_badge_html()


@register.simple_tag
def customer_type_badge_by_code(customer_type_code, size='sm'):
    """
    عرض بادج نوع العميل بناءً على الكود
    
    Usage:
        {% load customer_badges %}
        {% customer_type_badge_by_code 'wholesale' %}
    """
    if not customer_type_code:
        return ''
    
    from customers.models import CustomerType
    try:
        ct = CustomerType.objects.get(code=customer_type_code)
    except CustomerType.DoesNotExist:
        return ''
    
    return ct.get_badge_html()


@register.simple_tag
def get_customer_type_object(customer):
    """
    الحصول على كائن نوع العميل
    
    Usage:
        {% load customer_badges %}
        {% get_customer_type_object customer as ct %}
        {{ ct.pricing_type }}
    """
    if not customer:
        return None
    
    customer_type_code = getattr(customer, 'customer_type', None)
    if not customer_type_code:
        return None
    
    from customers.models import CustomerType
    try:
        return CustomerType.objects.get(code=customer_type_code)
    except CustomerType.DoesNotExist:
        return None


@register.filter
def is_wholesale_customer(customer):
    """
    التحقق من أن العميل من نوع جملة
    
    Usage:
        {% load customer_badges %}
        {% if customer|is_wholesale_customer %}...{% endif %}
    """
    if not customer:
        return False
    
    customer_type_code = getattr(customer, 'customer_type', None)
    if not customer_type_code:
        return False
    
    from customers.models import CustomerType
    try:
        ct = CustomerType.objects.get(code=customer_type_code)
        return ct.pricing_type == 'wholesale'
    except CustomerType.DoesNotExist:
        return False


@register.filter
def get_discount_for_customer_type(customer):
    """
    الحصول على نسبة الخصم لنوع العميل
    
    Usage:
        {% load customer_badges %}
        {{ customer|get_discount_for_customer_type }}
    """
    if not customer:
        return 0
    
    customer_type_code = getattr(customer, 'customer_type', None)
    if not customer_type_code:
        return 0
    
    from customers.models import CustomerType
    try:
        ct = CustomerType.objects.get(code=customer_type_code)
        if ct.pricing_type == 'discount':
            return ct.discount_percentage
        return 0
    except CustomerType.DoesNotExist:
        return 0
