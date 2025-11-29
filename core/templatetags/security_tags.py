"""
Template tags للحماية من XSS
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape, strip_tags
import re

register = template.Library()


@register.filter(name='safe_html')
def safe_html(value):
    """
    تنظيف HTML من العناصر الخطرة
    يسمح فقط بالعناصر الآمنة
    
    ملاحظة: للحصول على تنظيف أفضل، ثبت bleach:
    pip install bleach
    """
    if not value:
        return ''
    
    try:
        import bleach
        
        # العناصر المسموحة
        allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'a', 'span', 'div', 'blockquote', 'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td'
        ]
        
        # الخصائص المسموحة
        allowed_attributes = {
            'a': ['href', 'title', 'target'],
            'span': ['class'],
            'div': ['class'],
            'p': ['class'],
            'code': ['class'],
        }
        
        # البروتوكولات المسموحة للروابط
        allowed_protocols = ['http', 'https', 'mailto']
        
        # تنظيف HTML
        cleaned = bleach.clean(
            value,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=allowed_protocols,
            strip=True
        )
        return mark_safe(cleaned)
    except ImportError:
        # إذا لم يكن bleach مثبتاً، استخدم escape
        return escape(value)


@register.filter(name='safe_url')
def safe_url(value):
    """
    التحقق من أن الرابط آمن
    """
    if not value:
        return ''
    
    # السماح فقط بـ http/https/mailto
    allowed_schemes = ['http://', 'https://', 'mailto:', '/']
    
    value_lower = value.lower().strip()
    
    # التحقق من البروتوكول
    is_safe = any(value_lower.startswith(scheme) for scheme in allowed_schemes)
    
    if not is_safe:
        return '#'
    
    # التحقق من javascript
    if 'javascript:' in value_lower or 'data:' in value_lower:
        return '#'
    
    return value


@register.filter(name='strip_tags_safe')
def strip_tags_safe(value):
    """
    إزالة جميع HTML tags بشكل آمن
    """
    if not value:
        return ''
    
    try:
        import bleach
        # إزالة جميع HTML
        cleaned = bleach.clean(value, tags=[], strip=True)
        return cleaned
    except ImportError:
        # استخدام Django's strip_tags
        return strip_tags(value)


@register.filter(name='sanitize_js')
def sanitize_js(value):
    """
    تنظيف القيمة لاستخدامها في JavaScript
    """
    if not value:
        return ''
    
    # escape الأحرف الخطرة
    dangerous_chars = {
        '<': '\\u003c',
        '>': '\\u003e',
        '&': '\\u0026',
        '"': '\\u0022',
        "'": '\\u0027',
        '/': '\\u002f',
        '\\': '\\u005c',
    }
    
    result = str(value)
    for char, escaped in dangerous_chars.items():
        result = result.replace(char, escaped)
    
    return result


@register.filter(name='sanitize_css')
def sanitize_css(value):
    """
    تنظيف القيمة لاستخدامها في CSS
    """
    if not value:
        return ''
    
    # إزالة الأحرف الخطرة
    dangerous_patterns = [
        r'expression\s*\(',
        r'javascript:',
        r'vbscript:',
        r'@import',
        r'behavior:',
        r'-moz-binding',
    ]
    
    result = str(value)
    for pattern in dangerous_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    return result


@register.simple_tag
def csrf_input():
    """
    إضافة حقل CSRF بشكل آمن
    """
    from django.middleware.csrf import get_token
    from django.template import RequestContext
    
    return mark_safe(
        '<input type="hidden" name="csrfmiddlewaretoken" '
        'value="{{ csrf_token }}" />'
    )


@register.filter(name='truncate_safe')
def truncate_safe(value, length=100):
    """
    اقتصاص النص بشكل آمن دون قطع HTML
    """
    if not value:
        return ''
    
    # إزالة HTML أولاً
    text = strip_tags_safe(value)
    
    if len(text) <= length:
        return text
    
    return text[:length] + '...'
