from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html

register = template.Library()

@register.simple_tag
def get_status_badge(status, status_type="default"):
    """
    إنشاء badge موحد للحالة مع اللون المناسب
    
    Args:
        status: حالة العنصر (pending, completed, etc.)
        status_type: نوع الحالة (default, manufacturing, installation, inspection)
    """
    # خرائط النصوص حسب نوع الحالة
    status_texts_map = {
        'default': {
            'pending': 'قيد الانتظار',
            'pending_approval': 'قيد الموافقة',
            'processing': 'قيد التنفيذ',
            'in_progress': 'قيد التصنيع',
            'in_installation': 'قيد التركيب',
            'ready_install': 'جاهز للتركيب',
            'completed': 'مكتمل',
            'delivered': 'تم التسليم',
            'rejected': 'مرفوض',
            'cancelled': 'ملغي',
            'scheduled': 'مجدول',
            'not_scheduled': 'غير مجدول',
            'needs_scheduling': 'بحاجة جدولة',
            'modification_required': 'يحتاج تعديل',
            'modification_in_progress': 'التعديل قيد التنفيذ',
            'modification_completed': 'التعديل مكتمل',
            'postponed_by_customer': 'مؤجل من طرف العميل',
        },
        'inspection': {
            'pending': 'قيد الانتظار',
            'scheduled': 'مجدول',
            'completed': 'مكتملة',
            'cancelled': 'ملغية',
            'postponed_by_customer': 'مؤجل من طرف العميل',
        },
        'manufacturing': {
            'pending_approval': 'قيد الموافقة',
            'pending': 'قيد الانتظار',
            'in_progress': 'قيد التصنيع',
            'ready_install': 'جاهز للتركيب',
            'completed': 'مكتمل',
            'delivered': 'تم التسليم',
            'rejected': 'مرفوض',
            'cancelled': 'ملغي',
        },
        'installation': {
            'not_scheduled': 'غير مجدول',
            'pending': 'في الانتظار',
            'scheduled': 'مجدول',
            'in_progress': 'قيد التنفيذ',
            'completed': 'مكتمل',
            'cancelled': 'ملغي',
            'modification_required': 'يحتاج تعديل',
            'modification_in_progress': 'التعديل قيد التنفيذ',
            'modification_completed': 'التعديل مكتمل',
        }
    }
    
    status_classes = {
        # الحالات المكتملة - أخضر
        'completed': 'status-completed',
        'ready_install': 'status-ready_install',
        'delivered': 'status-delivered',
        'modification_completed': 'status-modification_completed',
        # حالات قيد الانتظار - برتقالي
        'pending': 'status-pending',
        'pending_approval': 'status-pending_approval',
        'modification_required': 'status-modification_required',
        'needs_scheduling': 'status-needs_scheduling',
        # حالات غير مجدول - فضي
        'not_scheduled': 'status-not_scheduled',
        # حالات مجدولة - أزرق فاتح
        'scheduled': 'status-scheduled',
        'modification_in_progress': 'status-modification_in_progress',
        'processing': 'status-processing',
        'in_progress': 'status-in_progress',
        'in_installation': 'status-in_installation',
        # حالات ملغية - أحمر
        'cancelled': 'status-cancelled',
        'rejected': 'status-rejected',
        # مؤجل من طرف العميل - رمادي داكن
        'postponed_by_customer': 'status-postponed_by_customer',
    }

    status_icons = {
        'pending': 'fas fa-clock',
        'pending_approval': 'fas fa-hourglass-half',
        'processing': 'fas fa-cogs',
        'in_progress': 'fas fa-tools',
        'in_installation': 'fas fa-tools',
        'ready_install': 'fas fa-check-circle',
        'completed': 'fas fa-check',
        'delivered': 'fas fa-truck',
        'rejected': 'fas fa-times',
        'cancelled': 'fas fa-ban',
        'scheduled': 'fas fa-calendar-check',
        'not_scheduled': 'fas fa-calendar-times',
        'needs_scheduling': 'fas fa-calendar-plus',
        'modification_required': 'fas fa-exclamation-triangle',
        'modification_in_progress': 'fas fa-wrench',
        'modification_completed': 'fas fa-check-double',
        'postponed_by_customer': 'fas fa-pause-circle',
    }

    # الحصول على خريطة النصوص المناسبة
    status_texts = status_texts_map.get(status_type, status_texts_map['default'])
    
    css_class = status_classes.get(status, 'status-secondary')
    icon = status_icons.get(status, 'fas fa-circle')
    text = status_texts.get(status, status)
    
    html = f'''
    <span class="unified-badge {css_class} status-badge" title="{text}" style="font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.2); box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <i class="{icon} me-1"></i>{text}
    </span>
    '''
    
    return mark_safe(html)

@register.simple_tag
def get_order_type_badge(order_type, order=None):
    """
    إنشاء badge موحد لنوع الطلب
    
    Args:
        order_type: نوع الطلب (installation, tailoring, accessory, inspection)
        order: كائن الطلب (اختياري) للتحقق من حالة VIP
    """
    type_classes = {
        'installation': 'order-type-installation',
        'tailoring': 'order-type-tailoring',
        'accessory': 'order-type-accessory',
        'inspection': 'order-type-inspection',
    }
    
    type_icons = {
        'installation': 'fas fa-tools',
        'tailoring': 'fas fa-cut',
        'accessory': 'fas fa-puzzle-piece',
        'inspection': 'fas fa-search',
    }
    
    type_texts = {
        'installation': 'تركيب',
        'tailoring': 'تسليم',
        'accessory': 'إكسسوارات',
        'inspection': 'معاينة',
    }
    
    css_class = type_classes.get(order_type, 'order-type-secondary')
    icon = type_icons.get(order_type, 'fas fa-tag')
    text = type_texts.get(order_type, order_type)
    
    # التحقق من حالة VIP إذا تم تمرير كائن الطلب
    is_vip = False
    if order and hasattr(order, 'status'):
        is_vip = order.status == 'vip'
    
    if is_vip:
        css_class = 'order-type-vip'
        text = f"VIP - {text}"
    
    html = f'''
    <span class="unified-badge {css_class} order-type-badge" title="{text}">
        <i class="{icon} me-1"></i>{text}
    </span>
    '''
    
    return mark_safe(html)

@register.simple_tag
def get_order_type_text(order_type, is_vip=False):
    """
    إنشاء نص نوع الطلب بدون خلفية
    
    Args:
        order_type: نوع الطلب
        is_vip: هل الطلب VIP أم لا
    """
    type_texts = {
        'installation': 'تركيب',
        'tailoring': 'تسليم',
        'accessory': 'إكسسوارات',
        'inspection': 'معاينة',
    }
    
    text = type_texts.get(order_type, order_type)
    
    if is_vip:
        css_class = 'order-type-vip'
        text = f"⭐ VIP - {text} ⭐"
    else:
        css_class = 'order-type-text'
    
    html = f'<span class="{css_class}">{text}</span>'
    return mark_safe(html)

@register.simple_tag
def get_status_indicator(status, size="normal"):
    """
    إنشاء مؤشر حالة دائري (أيقونة)
    
    Args:
        status: حالة العنصر
        size: حجم المؤشر (small, normal, large)
    """
    status_indicator_classes = {
        'pending': 'warning',
        'pending_approval': 'warning',
        'processing': 'info',
        'in_progress': 'info',
        'ready_install': 'info',
        'completed': 'success',
        'delivered': 'success',
        'rejected': 'error',
        'cancelled': 'secondary',
        'scheduled': 'info',
        'not_scheduled': 'secondary',
        'modification_required': 'warning',
        'modification_in_progress': 'info',
        'modification_completed': 'success',
    }
    
    status_icons = {
        'pending': '⏳',
        'pending_approval': '⏳',
        'processing': '⚙️',
        'in_progress': '🔧',
        'ready_install': '✅',
        'completed': '✅',
        'delivered': '🚚',
        'rejected': '❌',
        'cancelled': '🚫',
        'scheduled': '📅',
        'not_scheduled': '📅',
        'modification_required': '⚠️',
        'modification_in_progress': '🔧',
        'modification_completed': '✅',
    }
    
    indicator_class = status_indicator_classes.get(status, 'secondary')
    icon = status_icons.get(status, '●')
    
    size_classes = {
        'small': 'status-indicator-sm',
        'normal': 'status-indicator',
        'large': 'status-indicator-lg',
    }
    
    css_class = f"status-indicator {indicator_class} {size_classes.get(size, 'status-indicator')}"
    
    html = f'<span class="{css_class}" title="{status}">{icon}</span>'
    return mark_safe(html)

@register.simple_tag
def get_completion_indicator(is_completed):
    """
    إنشاء مؤشر الإكمال (صح خضراء أو خطأ حمراء)
    
    Args:
        is_completed: هل العنصر مكتمل أم لا
    """
    if is_completed:
        html = '''
        <span class="status-indicator success" title="مكتمل">
            <i class="fas fa-check"></i>
        </span>
        '''
    else:
        html = '''
        <span class="status-indicator error" title="غير مكتمل">
            <i class="fas fa-times"></i>
        </span>
        '''
    
    return mark_safe(html)

@register.simple_tag
def get_vip_badge():
    """
    إنشاء badge للطلبات VIP
    """
    html = '''
    <span class="unified-badge order-type-vip vip-badge" title="عميل VIP">
        <i class="fas fa-crown me-1"></i>VIP
    </span>
    '''
    return mark_safe(html)

@register.simple_tag
def get_urgent_badge():
    """
    إنشاء badge للطلبات العاجلة
    """
    html = '''
    <span class="unified-badge status-urgent urgent-badge" title="طلب عاجل">
        <i class="fas fa-exclamation-triangle me-1"></i>عاجل
    </span>
    '''
    return mark_safe(html) 