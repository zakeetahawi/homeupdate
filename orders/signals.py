import json
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Order
from manufacturing.models import ManufacturingOrder

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


@receiver(post_save, sender=Order)
def create_manufacturing_order_on_order_creation(sender, instance, created, **kwargs):
    """
    Creates a ManufacturingOrder automatically when a new Order is created
    with specific types ('installation', 'tailoring', 'accessory').
    """
    if created:
        print(f"--- SIGNAL TRIGGERED for Order PK: {instance.pk} ---")
        print(f"Raw selected_types from instance: {instance.selected_types}")
        
        MANUFACTURING_TYPES = {'installation', 'tailoring', 'accessory'}
        
        order_types = set()
        try:
            # selected_types is stored as a JSON string, so we need to parse it.
            parsed_types = json.loads(instance.selected_types)
            if isinstance(parsed_types, list):
                order_types = set(parsed_types)
            print(f"Successfully parsed types: {order_types}")
        except (json.JSONDecodeError, TypeError):
            print(f"Could not parse selected_types. Value was: {instance.selected_types}")
            # Fallback for plain string if needed, though not expected
            if isinstance(instance.selected_types, str):
                order_types = {instance.selected_types}

        if order_types.intersection(MANUFACTURING_TYPES):
            print(f"MATCH FOUND: Order types {order_types} intersect with {MANUFACTURING_TYPES}. Creating manufacturing order...")
            
            # Use a transaction to ensure both creations happen or neither.
            from django.db import transaction
            with transaction.atomic():
                mfg_order, created_mfg = ManufacturingOrder.objects.get_or_create(
                    order=instance,
                    defaults={
                        'status': 'pending_approval',
                        'notes': instance.notes,
                        'order_date': instance.created_at.date(),
                        'expected_delivery_date': instance.expected_delivery_date,
                        'contract_number': instance.contract_number,
                        'invoice_number': instance.invoice_number,
                    }
                )
                
                # Also update the original order's tracking status
                if created_mfg:
                    instance.tracking_status = 'factory'
                    instance.save(update_fields=['tracking_status'])
                    print(f"SUCCESS: Created ManufacturingOrder PK: {mfg_order.pk} and updated Order PK: {instance.pk} tracking_status to 'factory'")
                else:
                    print(f"INFO: ManufacturingOrder already existed for this order. PK: {mfg_order.pk}")
        else:
            print(f"NO MATCH: Order types {order_types} do not require manufacturing.")
    else:
        print(f"--- SIGNAL TRIGGERED for Order PK: {instance.pk} (UPDATE, not creation) ---")


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