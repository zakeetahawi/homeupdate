from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order, OrderItem
from django.db import transaction


@receiver(post_save, sender=Order)
def create_manufacturing_order_from_order(sender, instance, created, **kwargs):
    """
    إنشاء أمر تصنيع تلقائياً عند إنشاء طلب جديد من نوع تركيب أو تفصيل
    """
    # التحقق من أن الطلب جديد ومن نوع يتطلب تصنيعاً
    if created and instance.order_type in ['installation', 'detail']:
        with transaction.atomic():
            # إنشاء أمر التصنيع
            manufacturing_order = ManufacturingOrder.objects.create(
                order=instance,
                order_type=instance.order_type,
                contract_number=instance.contract_number,
                order_date=instance.order_date,
                expected_delivery_date=instance.expected_delivery_date,
                status='pending'
            )
            
            # إضافة عناصر الطلب إلى أمر التصنيع
            for item in instance.items.all():
                ManufacturingOrderItem.objects.create(
                    manufacturing_order=manufacturing_order,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    specifications=item.specifications,
                    status='pending'
                )


@receiver(pre_save, sender=ManufacturingOrder)
def update_order_status_from_manufacturing(sender, instance, **kwargs):
    """
    تحديث حالة الطلب الأصلي عند تغيير حالة أمر التصنيع
    """
    if not instance.pk:
        return  # New instance, nothing to update
        
    try:
        old_instance = ManufacturingOrder.objects.get(pk=instance.pk)
        
        # إذا تغيرت حالة أمر التصنيع
        if old_instance.status != instance.status:
            # تحديث حالة الطلب الأصلي بناءً على حالة أمر التصنيع
            if instance.order:
                if instance.status == 'in_progress' and instance.order.status != 'in_progress':
                    instance.order.status = 'in_progress'
                    instance.order.save(update_fields=['status'])
                
                elif instance.status == 'ready_for_installation' and instance.order.order_type == 'installation':
                    # تحديث حالة الطلب إلى "جاهز للتركيب"
                    instance.order.status = 'ready_for_installation'
                    instance.order.save(update_fields=['status'])
                
                elif instance.status == 'completed':
                    # إذا كان الطلب من نوع تفصيل، نقوم بتحديث حالته إلى مكتمل
                    if instance.order_type == 'detail':
                        instance.order.status = 'completed'
                        instance.order.completion_date = timezone.now()
                        instance.order.save(update_fields=['status', 'completion_date'])
                    # إذا كان الطلب من نوع تركيب، نتركه في حالة "جاهز للتركيب"
                    # حتى يتم تأكيد التركيب من قسم التركيبات

    except ManufacturingOrder.DoesNotExist:
        pass  # New instance, nothing to update


@receiver(post_save, sender=ManufacturingOrderItem)
def update_manufacturing_order_status(sender, instance, created, **kwargs):
    """
    تحديث حالة أمر التصنيع بناءً على حالة عناصره
    """
    if not created:  # نتعامل فقط مع التحديثات وليس الإنشاء
        manufacturing_order = instance.manufacturing_order
        
        # الحصول على جميع عناصر أمر التصنيع
        items = manufacturing_order.items.all()
        
        if not items.exists():
            return
        
        # إذا كانت جميع العناصر مكتملة
        if all(item.status == 'completed' for item in items):
            new_status = 'completed'
        # إذا كان هناك عنصر واحد على الأقل قيد التنفيذ
        elif any(item.status == 'in_progress' for item in items):
            new_status = 'in_progress'
        # إذا كانت جميع العناصر معلقة
        elif all(item.status == 'pending' for item in items):
            new_status = 'pending'
        # في الحالات الأخرى (مختلط)
        else:
            new_status = 'in_progress'
        
        # تحديث حالة أمر التصنيع إذا تغيرت
        if manufacturing_order.status != new_status:
            manufacturing_order.status = new_status
            manufacturing_order.save(update_fields=['status'])


@receiver(post_delete, sender=ManufacturingOrder)
def delete_related_installation(sender, instance, **kwargs):
    """
    حذف سجل التركيب المرتبط في حالة حذف أمر التصنيع
    """
    if hasattr(instance, 'installation'):
        instance.installation.delete()


@receiver(post_save, sender=Order)
def sync_order_updates(sender, instance, created, **kwargs):
    """
    مزامنة تحديثات الطلب مع أمر التصنيع المرتبط
    """
    if created:
        return  # تم التعامل مع الحالات الجديدة في إشارة أخرى
    
    try:
        manufacturing_order = ManufacturingOrder.objects.get(order=instance)
        
        # تحديث حقول أمر التصنيع عند تغييرها في الطلب
        update_fields = []
        
        if manufacturing_order.contract_number != instance.contract_number:
            manufacturing_order.contract_number = instance.contract_number
            update_fields.append('contract_number')
        
        if manufacturing_order.order_date != instance.order_date:
            manufacturing_order.order_date = instance.order_date
            update_fields.append('order_date')
        
        if manufacturing_order.expected_delivery_date != instance.expected_delivery_date:
            manufacturing_order.expected_delivery_date = instance.expected_delivery_date
            update_fields.append('expected_delivery_date')
        
        if update_fields:
            manufacturing_order.save(update_fields=update_fields)
            
    except ManufacturingOrder.DoesNotExist:
        pass  # لا يوجد أمر تصنيع مرتبط بهذا الطلب
