"""
فلاتر مخصصة للقوالب
"""

import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def pprint(value):
    """
    تنسيق البيانات بشكل مقروء
    """
    try:
        if isinstance(value, str):
            # محاولة تحليل السلسلة كـ JSON
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # تحويل القيمة إلى JSON منسق
        formatted_json = json.dumps(value, indent=4, ensure_ascii=False, sort_keys=True)
        
        # إرجاع النص المنسق
        return mark_safe(formatted_json)
    except Exception as e:
        return f"خطأ في تنسيق البيانات: {str(e)}"

# Register odoo_pprint as an alias for pprint
odoo_pprint = pprint
register.filter('odoo_pprint', odoo_pprint)