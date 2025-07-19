from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """
    Split a string by the given delimiter
    Usage: {{ "a,b,c"|split:"," }}
    """
    return value.split(arg)

@register.filter
def get_month_name(month_number):
    """
    Get Arabic month name from month number
    """
    months = {
        1: 'يناير',
        2: 'فبراير',
        3: 'مارس',
        4: 'أبريل',
        5: 'مايو',
        6: 'يونيو',
        7: 'يوليو',
        8: 'أغسطس',
        9: 'سبتمبر',
        10: 'أكتوبر',
        11: 'نوفمبر',
        12: 'ديسمبر'
    }
    return months.get(int(month_number), str(month_number)) 