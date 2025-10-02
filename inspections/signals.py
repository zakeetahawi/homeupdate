from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Inspection


@receiver(post_save, sender=Inspection)
def update_order_status_on_inspection_change(sender, instance, created, **kwargs):
    """
    تحديث حالة الطلب بناءً على حالة المعاينة للطلبات من نوع معاينة
    الحالة في الطلب يجب أن تكون مطابقة تماماً لحالة المعاينة.
    """
    # التحقق من وجود طلب مرتبط وأن الطلب من نوع معاينة
    if not instance.order:
        return

    try:
        order_types = instance.order.get_selected_types_list()
        if "inspection" not in order_types:
            return

        # Map inspection status/result to canonical order_status
        from django.utils import timezone

        from orders.models import Order

        if instance.status == "completed" and instance.result == "passed":
            mapped_status = "completed"
        elif instance.status == "completed" and instance.result == "failed":
            mapped_status = "rejected"
        elif instance.status == "scheduled":
            mapped_status = "pending"
        elif instance.status == "pending":
            mapped_status = "pending"
        elif instance.status == "cancelled":
            mapped_status = "cancelled"
        else:
            mapped_status = instance.status

        # تحديث حالة الطلب فقط إذا تغيرت
        current_order_status = instance.order.order_status

        if current_order_status != mapped_status:
            update_fields = {"order_status": mapped_status}

            # إذا كانت المعاينة مكتملة وناجحة، تحديث تاريخ التسليم المتوقع
            if mapped_status == "completed":
                update_fields["expected_delivery_date"] = timezone.now().date()

            # إضافة علامة لتجنب إشعار الطلب
            order = instance.order
            setattr(order, "_skip_order_notification", True)

            # تحديث الطلب مباشرة في قاعدة البيانات
            Order.objects.filter(pk=order.pk).update(**update_fields)

            # إعادة تحميل الكائن ودعوة تحديث الحالات المرتبطة
            try:
                order.refresh_from_db()
                # تحديث الحالات المحسوبة (installation/inspection/completion)
                order.update_all_statuses()
            except Exception:
                pass

            # تسجيل التحديث
            success_msg = f"✅ تم مزامنة حالة الطلب {order.order_number} إلى: {mapped_status} (من حالة المعاينة: {instance.status}/{instance.result})"
            print(f"\033[32m{success_msg}\033[0m")

    except Exception as e:
        # تسجيل الخطأ
        error_msg = f"❌ خطأ في مزامنة حالة الطلب {instance.order.id} بناءً على حالة المعاينة: {str(e)}"
        print(f"\033[31m{error_msg}\033[0m")
