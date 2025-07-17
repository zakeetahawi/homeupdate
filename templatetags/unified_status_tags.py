from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html

register = template.Library()

@register.simple_tag
def get_status_badge(status, status_type="general"):
    """إرجاع badge للحالة مع اللون المناسب - ألوان موحدة"""
    status_colors = {
        # الحالات المكتملة - أخضر
        'completed': 'bg-success',
        'ready_install': 'bg-success',
        'delivered': 'bg-success',
        'modification_completed': 'bg-success',
        'ready': 'bg-success',
        
        # حالات قيد الانتظار - برتقالي
        'pending': 'bg-warning text-dark',
        'pending_approval': 'bg-warning text-dark',
        'modification_required': 'bg-warning text-dark',
        
        # حالات غير مجدول - فضي
        'not_scheduled': 'bg-secondary',
        'manufacturing_deleted': 'bg-secondary',
        
        # حالات مجدولة - أزرق فاتح
        'scheduled': 'bg-info',
        'modification_in_progress': 'bg-info',
        'processing': 'bg-info',
        'in_progress': 'bg-info',
        
        # حالات أخرى - أزرق
        'in_progress': 'bg-primary',
        
        # حالات ملغية - أحمر
        'cancelled': 'bg-danger',
        'rejected': 'bg-danger',
    }
    
    status_icons = {
        'pending': 'fas fa-clock',
        'processing': 'fas fa-cog',
        'completed': 'fas fa-check-circle',
        'cancelled': 'fas fa-times-circle',
        'scheduled': 'fas fa-calendar-check',
        'in_progress': 'fas fa-play-circle',
        'ready': 'fas fa-check',
        'delivered': 'fas fa-truck',
        'not_scheduled': 'fas fa-minus',
        'modification_required': 'fas fa-exclamation-triangle',
        'modification_in_progress': 'fas fa-tools',
        'modification_completed': 'fas fa-check-double',
    }
    
    color = status_colors.get(status, 'bg-secondary')
    icon = status_icons.get(status, 'fas fa-question')
    
    return format_html(
        '<span class="badge {}" style="font-size: 0.75rem;"><i class="{} me-1"></i>{}</span>',
        color, icon, status
    )

@register.simple_tag
def get_completion_indicator(is_completed):
    """إرجاع مؤشر الإكمال"""
    if is_completed:
        return mark_safe('<span class="badge bg-success" style="font-size: 0.75rem;"><i class="fas fa-check-circle me-1"></i>مكتمل</span>')
    else:
        return mark_safe('<span class="badge bg-warning" style="font-size: 0.75rem;"><i class="fas fa-clock me-1"></i>قيد التنفيذ</span>')

@register.simple_tag
def get_vip_badge():
    """إرجاع badge للعملاء VIP"""
    return mark_safe('<span class="badge bg-warning" style="font-size: 0.75rem;"><i class="fas fa-crown me-1"></i>VIP</span>') 