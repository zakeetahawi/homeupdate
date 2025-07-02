from django import template
import json

register = template.Library()

@register.filter
def parse_selected_types(value):
    """Parse selected_types JSON and return list"""
    if not value:
        return []
    try:
        if isinstance(value, str):
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            else:
                return [parsed]
        elif isinstance(value, list):
            return value
        else:
            return []
    except (json.JSONDecodeError, TypeError):
        # Fallback: try to extract from string representation
        if isinstance(value, str):
            import re
            matches = re.findall(r"'(\w+)'|\"(\w+)\"", value)
            result = [match[0] or match[1] for match in matches]
            return result if result else []
        return []

@register.filter
def get_type_display(type_value):
    """Get display name for order type"""
    type_map = {
        'inspection': 'معاينة',
        'installation': 'تركيب', 
        'accessory': 'إكسسوار',
        'tailoring': 'تفصيل'
    }
    return type_map.get(type_value, type_value)

@register.filter
def get_type_badge_class(type_value):
    """Get badge class for order type"""
    type_map = {
        'inspection': 'bg-info',
        'installation': 'bg-warning', 
        'accessory': 'bg-primary',
        'tailoring': 'bg-success'
    }
    return type_map.get(type_value, 'bg-secondary')

@register.filter
def get_type_icon(type_value):
    """Get icon for order type"""
    type_map = {
        'inspection': 'fas fa-eye',
        'installation': 'fas fa-tools', 
        'accessory': 'fas fa-gem',
        'tailoring': 'fas fa-cut'
    }
    return type_map.get(type_value, 'fas fa-question')
