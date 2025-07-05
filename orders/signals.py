from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

@receiver(pre_save, sender='orders.Order')
def track_price_changes(sender, instance, **kwargs):
    """تتبع تغييرات الأسعار في الطلبات"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        try:
            Order = instance.__class__
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.final_price != instance.final_price:
                instance.price_changed = True
                instance.modified_at = timezone.now()
        except Order.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(post_save, sender='orders.Order')
def handle_order_creation(sender, instance, created, **kwargs):
    """معالجة إنشاء الطلب"""

    if created:
        # سيتم تحديث هذه الوظائف لاحقاً بعد إعادة بناء أنظمة المصنع والتركيبات
        pass


def set_default_delivery_option(order):
    """تحديد خيار التسليم الافتراضي حسب نوع الطلب"""
    if not hasattr(order, 'delivery_option'):
        return
        
    # إذا كان الطلب يحتوي على تركيب، تحديد التسليم مع التركيب
    if hasattr(order, 'selected_types') and order.selected_types:
        if 'installation' in order.selected_types or 'تركيب' in order.selected_types:
            order.delivery_option = 'with_installation'
            order.save(update_fields=['delivery_option'])
    # إذا كان الطلب تسليم في الفرع
    elif hasattr(order, 'delivery_type') and order.delivery_type == 'branch':
        order.delivery_option = 'branch_pickup'
        order.save(update_fields=['delivery_option'])
    # إذا كان الطلب توصيل منزلي
    elif hasattr(order, 'delivery_type') and order.delivery_type == 'home':
        order.delivery_option = 'home_delivery'
        order.save(update_fields=['delivery_option'])


def find_available_team(target_date, branch=None):
    """البحث عن فريق متاح في تاريخ محدد"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء نظام التركيبات
    return None


def calculate_windows_count(order):
    """حساب عدد الشبابيك من عناصر الطلب"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء النظام
    return 1


def create_production_order(order):
    """إنشاء طلب إنتاج"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء نظام المصنع
    return None


def set_default_delivery_option(order):
    """تحديد خيار التسليم الافتراضي حسب نوع الطلب"""
    try:
        # التحقق من أن الطلب يحتوي على أنواع مختارة
        if hasattr(order, 'selected_types') and order.selected_types:
            # إذا كان نوع الطلب يحتوي على تركيب، التسليم للمنزل
            if 'installation' in order.selected_types or 'تركيب' in order.selected_types:
                order.delivery_type = 'home'
                order.delivery_address = order.customer.address if order.customer else ''
                order.save(update_fields=['delivery_type', 'delivery_address'])
                print(f"✅ تم تحديد التسليم للمنزل للطلب #{order.order_number}")

            # إذا كان نوع الطلب تفصيل، الاستلام من الفرع
            elif 'tailoring' in order.selected_types or 'تفصيل' in order.selected_types:
                order.delivery_type = 'branch'
                order.save(update_fields=['delivery_type'])
                print(f"✅ تم تحديد الاستلام من الفرع للطلب #{order.order_number}")

    except Exception as e:
        print(f"❌ خطأ في تحديد خيار التسليم للطلب #{order.order_number}: {e}")
        # Removed installations related code as part of the refactoring

    # Removed installations exception handler as part of the refactoring