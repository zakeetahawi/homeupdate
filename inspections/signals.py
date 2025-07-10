from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Inspection


@receiver(post_save, sender=Inspection)
def update_order_status_on_inspection_change(sender, instance, created,
                                             **kwargs):
    """
    تحديث حالة الطلب بناءً على حالة المعاينة للطلبات من نوع معاينة
    """
    # التحقق من وجود طلب مرتبط وأن الطلب من نوع معاينة
    if not instance.order:
        return
        
    try:
        order_types = instance.order.get_selected_types_list()
        if 'inspection' not in order_types:
            return
            
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
        new_order_status = inspection_to_order_status.get(
            instance.status, 'pending'
        )
        new_tracking_status = inspection_to_tracking_status.get(
            instance.status, 'processing'
        )
        
        # تحديث حالة الطلب فقط إذا تغيرت الحالة
        current_order_status = instance.order.order_status
        current_tracking_status = instance.order.tracking_status
        
        if (current_order_status != new_order_status or
                current_tracking_status != new_tracking_status):
            # تحديث حالة الطلب
            instance.order.order_status = new_order_status
            instance.order.tracking_status = new_tracking_status
            instance.order.save(update_fields=[
                'order_status', 'tracking_status'
            ])
            
            # تسجيل التحديث [[memory:2733641]]
            success_msg = (
                f"✅ تم تحديث حالة الطلب {instance.order.order_number} "
                f"إلى {new_order_status} بناءً على حالة المعاينة "
                f"{instance.status}"
            )
            print(f"\033[32m{success_msg}\033[0m")
            
    except Exception as e:
        # تسجيل الخطأ [[memory:2733641]]
        error_msg = (
            f"❌ خطأ في تحديث حالة الطلب {instance.order.id} "
            f"بناءً على حالة المعاينة: {str(e)}"
        )
        print(f"\033[31m{error_msg}\033[0m") 