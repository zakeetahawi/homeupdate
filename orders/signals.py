import json
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderItem, Payment, OrderStatusLog, ManufacturingDeletionLog
from manufacturing.models import ManufacturingOrder
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
import logging
from django.db import models

logger = logging.getLogger(__name__)

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
        # print(f"--- SIGNAL TRIGGERED for Order PK: {instance.pk} ---")
        # print(f"Raw selected_types from instance: {instance.selected_types}")
        
        MANUFACTURING_TYPES = {'installation', 'tailoring', 'accessory'}
        
        order_types = set()
        try:
            # selected_types is stored as a JSON string, so we need to parse it.
            parsed_types = json.loads(instance.selected_types)
            if isinstance(parsed_types, list):
                order_types = set(parsed_types)
            # print(f"Successfully parsed types: {order_types}")
        except (json.JSONDecodeError, TypeError):
            # print(f"Could not parse selected_types. Value was: {instance.selected_types}")
            # Fallback for plain string if needed, though not expected
            if isinstance(instance.selected_types, str):
                order_types = {instance.selected_types}

        if order_types.intersection(MANUFACTURING_TYPES):
            # print(f"MATCH FOUND: Order types {order_types} intersect with {MANUFACTURING_TYPES}. Creating manufacturing order...")
            
            # Use a transaction to ensure both creations happen or neither.
            from django.db import transaction
            with transaction.atomic():
                from datetime import timedelta
                expected_date = instance.expected_delivery_date or (instance.created_at + timedelta(days=15)).date()
                
                mfg_order, created_mfg = ManufacturingOrder.objects.get_or_create(
                    order=instance,
                    defaults={
                        'status': 'pending_approval',
                        'notes': instance.notes,
                        'order_date': instance.created_at.date(),
                        'expected_delivery_date': expected_date,
                        'contract_number': instance.contract_number,
                        'invoice_number': instance.invoice_number,
                    }
                )
                
                # Also update the original order's tracking status
                if created_mfg:
                    # تحديث بدون إطلاق الإشارات لتجنب الrecursion
                    Order.objects.filter(pk=instance.pk).update(
                        tracking_status='factory',
                        order_status='pending_approval'
                    )
                    # print(f"SUCCESS: Created ManufacturingOrder PK: {mfg_order.pk} and updated Order PK: {instance.pk} tracking_status to 'factory'")
                else:
                    pass  # ManufacturingOrder already existed
        else:
            pass


@receiver(post_save, sender=Order)
def create_inspection_on_order_creation(sender, instance, created, **kwargs):
    """
    إنشاء معاينة تلقائية عند إنشاء طلب من نوع معاينة
    """
    if created:
        # print(f"--- INSPECTION SIGNAL TRIGGERED for Order PK: {instance.pk} ---")
        
        # استخدام الدالة الموجودة لتحليل أنواع الطلب
        order_types = instance.get_selected_types_list()
        # print(f"Successfully parsed types for inspection: {order_types}")

        # إذا كان الطلب يحتوي على نوع معاينة
        if 'inspection' in order_types:
            # print(f"INSPECTION MATCH FOUND: Creating inspection for order {instance.pk}")
            
            try:
                from django.db import transaction
                with transaction.atomic():
                    # استيراد نموذج المعاينة
                    from inspections.models import Inspection
                    
                    # إنشاء معاينة جديدة
                    inspection = Inspection.objects.create(
                        customer=instance.customer,
                        branch=instance.branch,
                        responsible_employee=instance.salesperson,
                        order=instance,
                        is_from_orders=True,
                        request_date=timezone.now().date(),
                        scheduled_date=timezone.now().date() + timedelta(days=1),
                        status='pending',
                        notes=f'معاينة تلقائية للطلب رقم {instance.order_number}',
                        order_notes=instance.notes,
                        created_by=instance.created_by
                    )
                    
                    # تحديث حالة الطلب لتعكس حالة المعاينة
                    Order.objects.filter(pk=instance.pk).update(
                        tracking_status='processing',
                        order_status='pending'
                    )
                    
                    # print(f"SUCCESS: Created Inspection PK: {inspection.pk} for Order PK: {instance.pk}")
                    
            except Exception as e:
                # print(f"ERROR: Failed to create inspection for order {instance.pk}: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            pass


def set_default_delivery_option(order):
    """تحديد خيار التسليم الافتراضي حسب نوع الطلب"""
    if not hasattr(order, 'delivery_option'):
        return
        
    # إذا كان الطلب يحتوي على تركيب، تحديد التسليم مع التركيب
    if hasattr(order, 'selected_types') and order.selected_types:
        if 'installation' in order.selected_types or 'تركيب' in order.selected_types:
            Order.objects.filter(pk=order.pk).update(delivery_option='with_installation')
    # إذا كان الطلب تسليم في الفرع
    elif hasattr(order, 'delivery_type') and order.delivery_type == 'branch':
        Order.objects.filter(pk=order.pk).update(delivery_option='branch_pickup')
    # إذا كان الطلب توصيل منزلي
    elif hasattr(order, 'delivery_type') and order.delivery_type == 'home':
        Order.objects.filter(pk=order.pk).update(delivery_option='home_delivery')


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


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """معالج حفظ الطلب"""
    if created:
        # إنشاء سجل حالة أولية
        OrderStatusLog.objects.create(
            order=instance,
            old_status='',
            new_status=instance.tracking_status,
            notes='تم إنشاء الطلب'
        )
    else:
        # التحقق من تغيير الحالة
        if hasattr(instance, '_tracking_status_changed') and instance._tracking_status_changed:
            OrderStatusLog.objects.create(
                order=instance,
                old_status=instance.tracker.previous('tracking_status'),
                new_status=instance.tracking_status,
                notes='تم تغيير حالة الطلب'
            )

@receiver(post_save, sender=OrderItem)
def order_item_post_save(sender, instance, created, **kwargs):
    """معالج حفظ عنصر الطلب"""
    if created:
        # تحديث المبلغ الإجمالي للطلب
        instance.order.calculate_final_price()
        # تحديث مباشر في قاعدة البيانات لتجنب التكرار الذاتي
        Order.objects.filter(pk=instance.order.pk).update(
            final_price=instance.order.final_price
        )

@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    """معالج حفظ الدفعة"""
    if created:
        # تحديث المبلغ المدفوع للطلب
        order = instance.order
        paid_amount = order.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        # تحديث مباشر في قاعدة البيانات لتجنب التكرار الذاتي
        Order.objects.filter(pk=order.pk).update(paid_amount=paid_amount)

# إشارات تحديث حالة الطلب من الأقسام الأخرى
# تم إزالة signal التركيب لتجنب الحلقة اللانهائية - يتم التعامل معه في orders/models.py

@receiver(post_save, sender='inspections.Inspection')
def update_order_inspection_status(sender, instance, created, **kwargs):
    """تحديث حالة الطلب عند تغيير حالة المعاينة"""
    try:
        if instance.order:
            order = instance.order
            order.update_inspection_status()
            order.update_completion_status()
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة المعاينة للطلب: {str(e)}")

@receiver(post_save, sender='manufacturing.ManufacturingOrder')
def update_order_manufacturing_status(sender, instance, created, **kwargs):
    """تحديث حالة الطلب عند تغيير حالة التصنيع"""
    try:
        order = instance.order
        # تحديث حالة الطلب بناءً على حالة التصنيع
        new_status = None
        if instance.status in ['completed', 'ready_install']:
            new_status = instance.status
        elif instance.status == 'delivered':
            new_status = 'delivered'
        
        # تحديث الحالة فقط إذا تغيرت لتجنب التكرار الذاتي
        if new_status and new_status != order.order_status:
            Order.objects.filter(pk=order.pk).update(order_status=new_status)
            order.refresh_from_db()
            order.update_completion_status()
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة التصنيع للطلب {instance.order.id}: {str(e)}")

# إشارة حذف أوامر التصنيع
@receiver(post_delete, sender='manufacturing.ManufacturingOrder')
def log_manufacturing_order_deletion(sender, instance, **kwargs):
    """تسجيل حذف أمر التصنيع"""
    try:
        # حفظ بيانات أمر التصنيع قبل الحذف
        manufacturing_data = {
            'id': instance.id,
            'status': instance.status,
            'order_type': instance.order_type,
            'contract_number': instance.contract_number,
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
        }
        
        ManufacturingDeletionLog.objects.create(
            order=instance.order,
            manufacturing_order_id=instance.id,
            manufacturing_order_data=manufacturing_data,
            reason='تم حذف أمر التصنيع'
        )
        
        # تحديث حالة الطلب
        Order.objects.filter(pk=instance.order.pk).update(order_status='manufacturing_deleted')
        
    except Exception as e:
        logger.error(f"خطأ في تسجيل حذف أمر التصنيع: {str(e)}")