"""فلاتر القالب لسجلات التدقيق"""
from django import template

register = template.Library()


@register.filter(name="get_dict_value")
def get_dict_value(dictionary, key):
    """
    استخراج قيمة من قاموس باستخدام مفتاح ديناميكي.
    الاستخدام: {{ my_dict|get_dict_value:key_var }}
    """
    if isinstance(dictionary, dict):
        val = dictionary.get(key, "—")
        if val is None or val == "":
            return "—"
        return val
    return "—"
