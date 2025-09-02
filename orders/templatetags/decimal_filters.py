from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def clean_decimal(value):
    """
    إخفاء الأصفار بعد الفاصلة العشرية
    Usage: {{ value|clean_decimal }}
    Examples:
    - 4.250 -> 4.25
    - 1.000 -> 1
    - 10.500 -> 10.5
    - 0.001 -> 0.001
    """
    if value is None:
        return ''
    
    try:
        # تحويل القيمة إلى Decimal للتأكد من دقة العمليات
        if isinstance(value, str):
            value = Decimal(value)
        elif isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, Decimal):
            pass
        else:
            return str(value)
        
        # إزالة الأصفار الزائدة بعد الفاصلة
        # تحويل إلى string وإزالة الأصفار من النهاية
        str_value = str(value)
        
        # إذا كان هناك فاصلة عشرية
        if '.' in str_value:
            # إزالة الأصفار من النهاية
            str_value = str_value.rstrip('0')
            # إزالة الفاصلة إذا لم يتبق شيء بعدها
            if str_value.endswith('.'):
                str_value = str_value[:-1]
        
        return str_value
    except (ValueError, TypeError):
        return str(value)

@register.filter
def clean_decimal_with_unit(value, unit=''):
    """
    إخفاء الأصفار بعد الفاصلة العشرية مع إضافة الوحدة
    Usage: {{ value|clean_decimal_with_unit:"متر" }}
    Examples:
    - 4.250 + "متر" -> 4.25 متر
    - 1.000 + "قطعة" -> 1 قطعة
    - 10.500 + "كيلو" -> 10.5 كيلو
    """
    clean_value = clean_decimal(value)
    if unit:
        return f"{clean_value} {unit}"
    return clean_value

@register.filter
def clean_decimal_currency(value, currency_symbol='ج.م'):
    """
    إخفاء الأصفار بعد الفاصلة العشرية مع إضافة رمز العملة
    Usage: {{ value|clean_decimal_currency:"ر.س" }}
    Examples:
    - 150.00 + "ج.م" -> 150 ج.م
    - 150.50 + "ج.م" -> 150.5 ج.م
    - 150.25 + "ج.م" -> 150.25 ج.م
    """
    clean_value = clean_decimal(value)
    return f"{clean_value} {currency_symbol}"
