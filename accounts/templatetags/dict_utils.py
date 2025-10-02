import json

from django import template

register = template.Library()


@register.filter
def to_json(value):
    """Convert a Python object to JSON string"""
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return "{}"


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
