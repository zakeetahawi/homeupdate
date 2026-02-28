import json
import math
from itertools import islice

from django import template
from django.utils.safestring import mark_safe

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
        "inspection": "معاينة",
        "installation": "تركيب",
        "accessory": "إكسسوار",
        "tailoring": "تسليم",
    }
    return type_map.get(type_value, type_value)


@register.filter
def get_type_badge_class(type_value):
    """Get badge class for order type"""
    type_map = {
        "inspection": "bg-info",
        "installation": "bg-warning",
        "accessory": "bg-primary",
        "tailoring": "bg-success",
    }
    return type_map.get(type_value, "bg-secondary")


@register.filter
def get_type_icon(type_value):
    """Get icon for order type"""
    type_map = {
        "inspection": "fas fa-eye",
        "installation": "fas fa-tools",
        "accessory": "fas fa-gem",
        "tailoring": "fas fa-cut",
    }
    return type_map.get(type_value, "fas fa-question")


@register.simple_tag
def get_order_type_badge(order_type, order=None):
    """
    إنشاء badge موحد لنوع الطلب مع ألوان متناسقة مع هوية المشروع

    Args:
        order_type: نوع الطلب (installation, tailoring, accessory, inspection)
        order: كائن الطلب (اختياري) للتحقق من حالة VIP
    """
    type_colors = {
        "installation": "#CD853F",
        "tailoring": "#D2691E",
        "accessory": "#A0522D",
        "inspection": "#8B4513",
        "products": "#6c757d",
        "fabric": "#343a40",
        "transport": "#17a2b8",
    }

    type_icons = {
        "installation": "fas fa-tools",
        "tailoring": "fas fa-shipping-fast",
        "accessory": "fas fa-gem",
        "inspection": "fas fa-search",
        "products": "fas fa-box",
        "fabric": "fas fa-tshirt",
        "transport": "fas fa-truck",
    }

    type_texts = {
        "installation": "تركيب",
        "tailoring": "تسليم",
        "accessory": "إكسسوار",
        "inspection": "معاينة",
        "products": "منتجات",
        "fabric": "أقمشة",
        "transport": "نقل",
    }

    color = type_colors.get(order_type, "#6c757d")
    icon = type_icons.get(order_type, "fas fa-tag")
    text = type_texts.get(order_type, order_type)

    # التحقق من حالة VIP إذا تم تمرير كائن الطلب
    is_vip = False
    if order and hasattr(order, "status"):
        is_vip = order.status == "vip"

    if is_vip:
        color = "#FFD700"  # ذهبي للـ VIP
        text = f"VIP - {text}"
        icon = "fas fa-crown"

    html = f"""
    <span class="badge text-white" style="font-size: 0.75rem; background-color: {color};">
        <i class="{icon} me-1"></i>{text}
    </span>
    """

    return mark_safe(html)


@register.simple_tag
def get_vip_badge():
    """
    إنشاء badge للطلبات VIP
    """
    html = """
    <span class="badge text-dark" style="font-size: 0.75rem; background-color: #FFD700;">
        <i class="fas fa-crown me-1"></i>VIP
    </span>
    """
    return mark_safe(html)


@register.simple_tag
def get_status_badge(status, status_type="default", order=None):
    """
    إنشاء badge موحد للحالة مع ألوان متناسقة مع هوية المشروع

    Args:
        status: حالة العنصر (pending, completed, etc.)
        status_type: نوع الحالة (default, manufacturing, installation, inspection)
        order: كائن الطلب (اختياري) لتخصيص النص حسب نوع الطلب
    """
    status_colors = {
        # الحالات المكتملة - أخضر داكن
        "completed": "#228B22",
        "ready_install": "#32CD32",
        "delivered": "#006400",
        "modification_completed": "#228B22",
        # حالات قيد الانتظار - برتقالي/بني فاتح
        "pending": "#D2691E",
        "pending_approval": "#CD853F",
        "modification_required": "#DEB887",
        "needs_scheduling": "#F4A460",
        # حالات غير مجدول - رمادي
        "not_scheduled": "#696969",
        # حالات مجدولة - بني متوسط
        "scheduled": "#A0522D",
        "modification_in_progress": "#8B4513",
        "processing": "#8B4513",
        "in_progress": "#8B4513",
        "in_installation": "#A0522D",
        # حالات ملغية - أحمر داكن
        "cancelled": "#8B0000",
        "rejected": "#DC143C",
        # أمر تصنيع محذوف - رمادي
        "manufacturing_deleted": "#6c757d",
        # مؤجل من طرف العميل - رمادي
        "postponed_by_customer": "#6c757d",
    }

    status_icons = {
        "pending": "fas fa-clock",
        "pending_approval": "fas fa-hourglass-half",
        "processing": "fas fa-cogs",
        "in_progress": "fas fa-tools",
        "in_installation": "fas fa-tools",
        "ready_install": "fas fa-check-circle",
        "completed": "fas fa-check",
        "delivered": "fas fa-truck",
        "rejected": "fas fa-times",
        "cancelled": "fas fa-ban",
        "scheduled": "fas fa-calendar-check",
        "not_scheduled": "fas fa-calendar-times",
        "needs_scheduling": "fas fa-calendar-plus",
        "modification_required": "fas fa-exclamation-triangle",
        "modification_in_progress": "fas fa-wrench",
        "modification_completed": "fas fa-check-double",
        "postponed_by_customer": "fas fa-pause-circle",
        "manufacturing_deleted": "fas fa-trash-alt",
    }

    status_texts = {
        "pending": "قيد الانتظار",
        "pending_approval": "قيد الموافقة",
        "processing": "قيد التنفيذ",
        "in_progress": "قيد التصنيع",
        "in_installation": "قيد التركيب",
        "ready_install": "جاهز للتركيب",
        "completed": "مكتمل",
        "delivered": "تم التسليم",
        "rejected": "مرفوض",
        "cancelled": "ملغي",
        "scheduled": "مجدول",
        "not_scheduled": "غير مجدول",
        "needs_scheduling": "بحاجة جدولة",
        "modification_required": "يحتاج تعديل",
        "modification_in_progress": "التعديل قيد التنفيذ",
        "modification_completed": "التعديل مكتمل",
        "postponed_by_customer": "مؤجل من طرف العميل",
        "manufacturing_deleted": "أمر تصنيع محذوف",
    }

    color = status_colors.get(status, "#6c757d")
    icon = status_icons.get(status, "fas fa-circle")
    text = status_texts.get(status, status)

    # تخصيص النص بناءً على نوع الطلب
    if order and status == "in_progress":
        try:
            # التحقق إذا كان الطلب من نوع منتجات
            selected_types = []
            if hasattr(order, "get_selected_types_list"):
                selected_types = order.get_selected_types_list()
            elif hasattr(order, "selected_types"):
                # fallback parsing
                import json

                try:
                    val = order.selected_types
                    if isinstance(val, str):
                        selected_types = json.loads(val)
                    elif isinstance(val, list):
                        selected_types = val
                except Exception:
                    pass

            if "products" in selected_types:
                text = "قيد التقطيع"
                icon = "fas fa-cut"  # تغيير الأيقونة أيضاً لتناسب التقطيع
        except Exception:
            pass

    html = f"""
    <span class="badge text-white" style="font-size: 0.75rem; background-color: {color};">
        <i class="{icon} me-1"></i>{text}
    </span>
    """

    return mark_safe(html)


@register.filter
def get_status_display(status):
    """Get display name for order status"""
    status_map = {
        "pending": "قيد الانتظار",
        "pending_approval": "قيد الموافقة",
        "approved": "تمت الموافقة",
        "processing": "قيد التنفيذ",
        "in_progress": "قيد التصنيع",
        "ready_install": "جاهز للتركيب",
        "completed": "مكتمل",
        "delivered": "تم التسليم",
        "rejected": "مرفوض",
        "cancelled": "ملغي",
        "scheduled": "مجدول",
        "not_scheduled": "غير مجدول",
        "needs_scheduling": "بحاجة جدولة",
        "modification_required": "يحتاج تعديل",
        "modification_in_progress": "التعديل قيد التنفيذ",
        "modification_completed": "التعديل مكتمل",
        "postponed_by_customer": "مؤجل من طرف العميل",
    }
    return status_map.get(status, status)


@register.filter
def currency_format(amount):
    """Format amount with currency"""
    try:
        from decimal import Decimal

        from accounts.models import SystemSettings

        # تحويل amount إلى رقم إذا كان string
        if isinstance(amount, str):
            # إزالة الفواصل والمسافات
            amount = amount.replace(",", "").replace(" ", "").strip()
            # محاولة تحويله لـ float
            amount = float(amount) if amount else 0
        elif amount is None:
            amount = 0

        # تحويل إلى float للتأكد
        amount = float(amount)

        settings = SystemSettings.get_settings()
        symbol = settings.currency_symbol
        formatted_amount = f"{amount:,.2f}"
        return f"{formatted_amount} {symbol}"
    except Exception as e:
        # في حالة الخطأ، حاول عرض القيمة كما هي
        try:
            amount_float = float(
                str(amount).replace(",", "").replace(" ", "").strip() or 0
            )
            return f"{amount_float:,.2f} ر.س"
        except Exception:
            return f"{amount} ر.س"


@register.simple_tag
def paid_percentage(order):
    """حساب نسبة المبلغ المدفوع من الإجمالي النهائي (بعد الخصم)"""
    try:
        # استخدام المبلغ النهائي بعد الخصم بدلاً من الإجمالي
        total = float(getattr(order, "final_price_after_discount", 0) or 0)
        # إذا لم يكن موجوداً، استخدم final_price
        if total <= 0:
            total = float(getattr(order, "final_price", 0) or 0)

        paid = float(getattr(order, "paid_amount", 0) or 0)

        if total <= 0:
            return "0%"

        pct_value = math.floor((paid * 100.0) / total)

        # إذا كان هناك متبقي لا تسمح بإظهار 100%
        remaining = float(total - paid)
        if (
            remaining > 0.01 and pct_value >= 100
        ):  # استخدام 0.01 للتعامل مع أخطاء التقريب
            pct_value = 99

        pct_value = max(0, min(100, pct_value))
        return f"{pct_value}%"
    except Exception:
        return "0%"


@register.filter
def remaining_amount(total, paid):
    """
    حساب المبلغ المتبقي
    """
    try:
        total_val = float(total) if total else 0
        paid_val = float(paid) if paid else 0
        remaining = total_val - paid_val
        return f"{remaining:.2f}"
    except (ValueError, TypeError):
        return "0.00"


@register.filter
def get_selected_type_display(order):
    """
    إرجاع عرض نوع الطلب المحدد
    """
    try:
        return order.get_selected_type_display()
    except Exception:
        return order.get_order_type_display()


@register.filter
def timesince_days(date):
    """حساب عدد الأيام منذ تاريخ معين"""
    from datetime import datetime

    from django.utils import timezone

    if not date:
        return 0

    today = timezone.now().date()
    if isinstance(date, datetime):
        date = date.date()

    delta = today - date
    return delta.days


@register.filter
def days_until(date):
    """حساب عدد الأيام حتى تاريخ معين"""
    from datetime import datetime

    from django.utils import timezone

    if not date:
        return 0

    today = timezone.now().date()
    if isinstance(date, datetime):
        date = date.date()

    delta = date - today
    return delta.days


@register.filter
def batch(iterable, n):
    """
    تقسيم قائمة إلى مجموعات بحجم n
    مثال: {{ curtains|batch:4 }}
    """
    n = int(n)
    items = list(iterable)
    for i in range(0, len(items), n):
        yield items[i : i + n]


@register.filter
def get_item(dictionary, key):
    """
    الحصول على قيمة من قاموس باستخدام مفتاح
    مثال: {{ my_dict|get_item:my_key }}
    """
    if not dictionary:
        return None
    return dictionary.get(str(key))
