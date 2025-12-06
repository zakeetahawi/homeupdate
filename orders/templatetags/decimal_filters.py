from django import template
from decimal import Decimal, ROUND_HALF_UP

register = template.Library()

@register.filter
def clean_decimal(value, max_decimals=2):
    """
    ⚡ إزالة الأصفار الزائدة بعد الفاصلة العشرية بذكاء
    - يحتفظ فقط بالأرقام المعنوية (1-9)
    - يسمح بصفر واحد فقط بعد الفاصلة إذا كان ضرورياً
    - التقريب التلقائي إلى max_decimals
    
    Usage: {{ value|clean_decimal }}
    Examples:
    - 440.00000 -> 440
    - 440.50000 -> 440.5
    - 440.25000 -> 440.25
    - 0.00000000 -> 0
    - 123.4567 -> 123.46 (مع max_decimals=2)
    - 100.10 -> 100.1
    - 100.01 -> 100.01
    """
    if value is None or value == '':
        return '0'
    
    try:
        # تحويل إلى Decimal للدقة
        if isinstance(value, str):
            value = Decimal(value)
        elif isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif not isinstance(value, Decimal):
            return '0'
        
        # معالجة القيم الصغيرة جداً (أقل من 0.01)
        if abs(value) < Decimal('0.01'):
            return '0'
        
        # التقريب إلى max_decimals خانات
        quantizer = Decimal('0.1') ** max_decimals
        rounded = value.quantize(quantizer, rounding=ROUND_HALF_UP)
        
        # تحويل إلى string وتنظيف
        str_value = str(rounded)
        
        # إزالة الأصفار الزائدة بذكاء
        if '.' in str_value:
            # إزالة الأصفار من النهاية
            str_value = str_value.rstrip('0')
            # إزالة الفاصلة إذا لم يبق أي رقم بعدها
            str_value = str_value.rstrip('.')
        
        return str_value
        
    except (ValueError, TypeError, ArithmeticError):
        return '0'


@register.filter
def format_currency(value, currency_symbol=None):
    """
    ⚡ تنسيق المبلغ المالي مع رمز العملة من إعدادات النظام
    
    Usage: 
    - {{ value|format_currency }}  -> يستخدم العملة من الإعدادات
    - {{ value|format_currency:"$" }}  -> 150.5 $
    
    Examples:
    - 440.00 -> 440 ج.م
    - 150.50 -> 150.5 ج.م
    - 1250.75 -> 1,250.75 ج.م
    """
    # تنظيف القيمة
    clean_value = clean_decimal(value, max_decimals=2)
    
    # الحصول على رمز العملة
    if currency_symbol is None:
        try:
            from accounts.models import SystemSettings
            settings = SystemSettings.get_settings()
            currency_symbol = settings.currency_symbol
        except:
            currency_symbol = 'ج.م'
    
    # إضافة الفواصل للأرقام الكبيرة (اختياري)
    try:
        num = float(clean_value)
        if abs(num) >= 1000:
            # تنسيق مع فواصل الآلاف
            clean_value = f"{num:,.10f}".rstrip('0').rstrip('.')
    except:
        pass
    
    return f"{clean_value} {currency_symbol}"


@register.filter  
def format_quantity(value, unit=''):
    """
    ⚡ تنسيق الكميات مع الوحدة
    
    Usage: {{ value|format_quantity:"متر" }}
    Examples:
    - 4.250 + "متر" -> 4.25 متر
    - 1.000 + "قطعة" -> 1 قطعة
    - 10.500 + "كجم" -> 10.5 كجم
    """
    clean_value = clean_decimal(value, max_decimals=3)
    if unit:
        return f"{clean_value} {unit}"
    return clean_value


@register.filter
def format_percentage(value):
    """
    ⚡ تنسيق النسب المئوية
    
    Usage: {{ value|format_percentage }}
    Examples:
    - 15.00 -> 15%
    - 12.50 -> 12.5%
    - 0.00 -> 0%
    """
    clean_value = clean_decimal(value, max_decimals=2)
    return f"{clean_value}%"


# Aliases للتوافق مع الكود القديم
@register.filter
def clean_decimal_with_unit(value, unit=''):
    """Alias لـ format_quantity"""
    return format_quantity(value, unit)


@register.filter
def clean_decimal_currency(value, currency_symbol=None):
    """Alias لـ format_currency"""
    if currency_symbol is None:
        return format_currency(value)
    return format_currency(value, currency_symbol)
