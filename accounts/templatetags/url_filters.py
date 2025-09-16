from django import template

register = template.Library()

@register.filter
def fix_url(value):
    """
    تحويل الروابط من الشكل data_management:google_sync إلى /data_management/google-sync/
    """
    if not value:
        return value
    
    # تقسيم الرابط إلى جزئين
    parts = value.split(':')
    if len(parts) != 2:
        return value
    
    app_name = parts[0]
    view_name = parts[1]
    
    # تحويل الشرطة السفلية إلى شرطة عادية
    view_name = view_name.replace('_', '-')
    
    # إرجاع الرابط بالشكل الصحيح
    return f"/{app_name}/{view_name}/" 