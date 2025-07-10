from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.apps import apps
from django.db import transaction

# سيتم استيراد النماذج عند الحاجة باستخدام apps.get_model


@receiver(post_save, sender='orders.Order')  # استخدام الإشارة النصية
@receiver(post_save, sender='orders.OrderItem')  # إضافة مستمع لـ OrderItem أيضاً
def create_manufacturing_order_from_order(sender, instance, created, **kwargs):
    """
    إنشاء أمر تصنيع تلقائياً عند إنشاء طلب جديد من نوع تركيب أو تفصيل
    """
    # الحصول على النماذج المطلوبة
    Order = apps.get_model('orders', 'Order')
    ManufacturingOrder = apps.get_model('manufacturing', 'ManufacturingOrder')
    
    # التحقق من أن الطلب جديد ومن نوع يتطلب تصنيعاً
    if created and hasattr(instance, 'order_type') and instance.order_type in ['installation', 'detail']:
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
            ManufacturingOrderItem = apps.get_model('manufacturing', 'ManufacturingOrderItem')
            for item in instance.items.all():
                ManufacturingOrderItem.objects.create(
                    manufacturing_order=manufacturing_order,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    specifications=item.specifications,
                    status='pending'
                )


# تم حذف هذه الإشارة لأنها تسبب مشاكل - يتم التحديث عبر نموذج التصنيع مباشرة


@receiver(post_save, sender='manufacturing.ManufacturingOrderItem')
def update_manufacturing_order_status(sender, instance, created, **kwargs):
    """
    تحديث حالة أمر التصنيع بناءً على حالة عناصره
    """
    if not created:  # نتعامل فقط مع التحديثات وليس الإنشاء
        ManufacturingOrder = apps.get_model('manufacturing', 'ManufacturingOrder')
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
            # manufacturing_order.save(update_fields=['status'])  # معطل لتجنب الرسائل الكثيرة
            pass


@receiver(post_delete, sender='manufacturing.ManufacturingOrder')
def delete_related_installation(sender, instance, **kwargs):
    """
    حذف سجل التركيب المرتبط في حالة حذف أمر التصنيع
    """
    if hasattr(instance, 'installation'):
        instance.installation.delete()


@receiver(post_save, sender='orders.Order')
def sync_order_updates(sender, instance, created, **kwargs):
    """
    مزامنة تحديثات الطلب مع أمر التصنيع المرتبط
    """
    if created:
        return  # تم التعامل مع الحالات الجديدة في إشارة أخرى
    
    ManufacturingOrder = apps.get_model('manufacturing', 'ManufacturingOrder')
    
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
