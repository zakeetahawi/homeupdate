from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Inspection


@receiver(post_save, sender=Inspection)
def update_order_status_on_inspection_completion(sender, instance, **kwargs):
    """
    Update order status to completed when inspection is completed
    """
    if instance.status == 'completed' and instance.order:
        try:
            # Update order status to completed
            instance.order.tracking_status = 'completed'
            instance.order.save(update_fields=['tracking_status'])

            # Log the status change (معطل لتجنب الرسائل الكثيرة)
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.info(f"تم تحديث حالة الطلب {instance.order.id} إلى مكتمل بعد اكتمال المعاينة {instance.id}")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            # logger.error(f"خطأ في تحديث حالة الطلب {instance.order.id} بعد اكتمال المعاينة: {str(e)}")  # معطل لتجنب الرسائل الكثيرة


@receiver(post_save, sender=Inspection)
def update_order_status_on_inspection_change(sender, instance, **kwargs):
    """
    تحديث حالة الطلب بناءً على حالة المعاينة للطلبات من نوع معاينة
    """
    if instance.order and 'inspection' in instance.order.get_selected_types_list():
        try:
            # خريطة تحويل حالات المعاينة إلى حالات الطلب
            inspection_to_order_status = {
                'pending': 'pending',           # قيد الانتظار
                'scheduled': 'pending',         # مجدول -> قيد الانتظار
                'completed': 'completed',       # مكتملة -> مكتمل
                'cancelled': 'cancelled',       # ملغية -> ملغي
            }
            
            # خريطة تحويل حالات المعاينة إلى حالات التتبع
            inspection_to_tracking_status = {
                'pending': 'processing',        # قيد الانتظار -> قيد المعالجة
                'scheduled': 'processing',      # مجدول -> قيد المعالجة
                'completed': 'ready',           # مكتملة -> جاهز للتسليم
                'cancelled': 'pending',         # ملغية -> قيد الانتظار
            }
            
            # الحصول على الحالات الجديدة
            new_order_status = inspection_to_order_status.get(instance.status, 'pending')
            new_tracking_status = inspection_to_tracking_status.get(instance.status, 'processing')
            
            # تحديث حالة الطلب
            from orders.models import Order
            Order.objects.filter(pk=instance.order.pk).update(
                order_status=new_order_status,
                tracking_status=new_tracking_status
            )
            
            # تسجيل التحديث (معطل لتجنب الرسائل الكثيرة)
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.info(f"تم تحديث حالة الطلب {instance.order.order_number} إلى {new_order_status} بناءً على حالة المعاينة {instance.status}")
            
        except Exception as e:
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.error(f"خطأ في تحديث حالة الطلب {instance.order.id} بناءً على حالة المعاينة: {str(e)}")
            pass 