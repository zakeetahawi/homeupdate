from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Inspection


@receiver(post_save, sender=Inspection)
def update_order_status_on_inspection_change(sender, instance, created,
                                             **kwargs):
    """
    تحديث حالة الطلب بناءً على حالة المعاينة للطلبات من نوع معاينة
    الحالة في الطلب يجب أن تكون مطابقة تماماً لحالة المعاينة.
    """
    # التحقق من وجود طلب مرتبط وأن الطلب من نوع معاينة
    if not instance.order:
        return
        
    try:
        order_types = instance.order.get_selected_types_list()
        if 'inspection' not in order_types:
            return
        
        # مزامنة الحالة كما هي
        new_order_status = instance.status
        
        # تحديث حالة الطلب فقط إذا تغيرت الحالة
        current_order_status = instance.order.order_status
        
        if (current_order_status != new_order_status):
            # تحديث حالة الطلب باستخدام update لتجنب التكرار الذاتي
            from django.utils import timezone
            from orders.models import Order
            
            update_fields = {'order_status': new_order_status}
            
            # إذا كانت المعاينة مكتملة، تحديث تاريخ التسليم
            if new_order_status == 'completed':
                update_fields['expected_delivery_date'] = timezone.now().date()
            
            # تحديث الطلب مباشرة في قاعدة البيانات
            Order.objects.filter(pk=instance.order.pk).update(**update_fields)
            
            # تسجيل التحديث
            success_msg = (
                f"✅ تم مزامنة حالة الطلب {instance.order.order_number} لتكون مطابقة لحالة المعاينة: {new_order_status}"
            )
            print(f"\033[32m{success_msg}\033[0m")
        
    except Exception as e:
        # تسجيل الخطأ
        error_msg = (
            f"❌ خطأ في مزامنة حالة الطلب {instance.order.id} بناءً على حالة المعاينة: {str(e)}"
        )
        print(f"\033[31m{error_msg}\033[0m") 