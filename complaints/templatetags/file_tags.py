from django import template

register = template.Library()


@register.filter
def filesize_format(value):
    """
    Format file size as bytes, KB or MB with one decimal place
    """
    try:
        value = float(value)
        if value < 1024:
            return f"{value} بايت"
        elif value < 1048576:
            return f"{value / 1024:.1f} ك.ب"
        else:
            return f"{value / 1048576:.1f} م.ب"
    except (ValueError, TypeError):
        return value
