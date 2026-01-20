# Manufacturing template tags and filters
from django import template

register = template.Library()


@register.filter(name='remove_branch_prefix')
def remove_branch_prefix(value):
    """Remove 'فرع ' prefix from branch name"""
    if value:
        return value.replace('فرع ', '').replace('فرع', '').strip()
    return value
