"""
Template filters for number conversion
فلاتر القوالب لتحويل الأرقام
"""
from django import template
from core.utils.general import convert_arabic_numbers_to_english

register = template.Library()


@register.filter(name='en')
def english_numbers(value):
    """
    تحويل الأرقام العربية إلى إنجليزية في العرض
    Convert Arabic numbers to English for display
    
    Usage in templates:
        {{ order.order_number|en }}
        {{ payment.amount|en }}
        {{ customer.code|en }}
    """
    if value is None:
        return value
    return convert_arabic_numbers_to_english(str(value))


@register.filter(name='english_numbers')
def english_numbers_verbose(value):
    """
    نفس الفلتر بإسم طويل للوضوح
    Same filter with verbose name for clarity
    """
    return english_numbers(value)
