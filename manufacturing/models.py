from django.db import models
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

# تمت إزالة استيراد Order لتجنب الاعتماد الدائري
# سيتم استخدام الإشارة النصية 'orders.Order' بدلاً من ذلك


class ManufacturingOrder(models.Model):
    """نموذج يمثل أمر التصنيع"""
    
    ORDER_TYPE_CHOICES = [
        ('installation', 'تركيب'),
        ('custom', 'تفصيل'),
        ('accessory', 'اكسسوار'),
    ]
    
    STATUS_CHOICES = [
        ('pending_approval', 'قيد الموافقة'),
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التصنيع'),
        ('ready_install', 'جاهز للتركيب'),
        ('completed', 'مكتمل'),
        ('delivered', 'تم التسليم'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
    ]
    
    order = models.OneToOneField(
        'orders.Order',  # استخدام الإشارة النصية بدلاً من الاستيراد المباشر
        on_delete=models.CASCADE,
        related_name='manufacturing_order',
        verbose_name='رقم الطلب'
    )
    
    contract_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='رقم العقد'
    )
    
    invoice_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='رقم الفاتورة'
    )
    
    contract_file = models.FileField(
        upload_to='manufacturing/contracts/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        verbose_name='ملف العقد'
    )
    
    inspection_file = models.FileField(
        upload_to='manufacturing/inspections/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        verbose_name='ملف المعاينة'
    )
    
    order_date = models.DateField(
        default=timezone.now,
        verbose_name='تاريخ استلام الطلب'
    )
    
    expected_delivery_date = models.DateField(
        verbose_name='تاريخ التسليم المتوقع'
    )
    
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        verbose_name='نوع الطلب'
    )
    
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending_approval',
        verbose_name='حالة الطلب'
    )
    
    exit_permit_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='رقم إذن الخروج'
    )
    
    delivery_permit_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='رقم إذن التسليم'
    )
    
    delivery_recipient_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='اسم المستلم'
    )
    
    delivery_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ التسليم'
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='ملاحظات'
    )
    
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='سبب الرفض'
    )

    completion_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الانتهاء',
        help_text='يتم تعبئته تلقائياً عند اكتمال التصنيع أو جاهزية المنتج للتركيب'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )
    
    class Meta:
        verbose_name = 'أمر تصنيع'
        verbose_name_plural = 'أوامر التصنيع'
        ordering = ['-created_at']
        permissions = [
            ('can_approve_orders', 'يمكن الموافقة على أوامر التصنيع'),
            ('can_reject_orders', 'يمكن رفض أوامر التصنيع'),
        ]
    
    def __str__(self):
        return f'أمر تصنيع #{self.id} - {self.get_status_display()}'
    
    def get_absolute_url(self):
        return reverse('manufacturing:order_detail', args=[str(self.id)])

    def get_delete_url(self):
        return reverse('manufacturing:order_delete', kwargs={'pk': self.pk})
    
    def update_order_status(self):
        """تحديث حالة الطلب الأصلي بناءً على حالة أمر التصنيع"""
        from django.apps import apps
        from django.utils import timezone
        
        Order = apps.get_model('orders', 'Order')
        
        # تحديث تاريخ الإكمال عند الوصول لحالة مكتمل أو جاهز للتركيب
        if self.status in ['completed', 'ready_install'] and not self.completion_date:
            self.completion_date = timezone.now()
            # حفظ بدون إطلاق الإشارات لتجنب الrecursion
            ManufacturingOrder.objects.filter(pk=self.pk).update(
                completion_date=self.completion_date
            )
        
        # تحديث حالة الطلب لتتطابق مع حالة التصنيع
        status_mapping = {
            'pending_approval': 'factory',
            'pending': 'factory',
            'in_progress': 'factory',
            'ready_install': 'ready',
            'completed': 'ready',
            'delivered': 'delivered',
            'rejected': 'factory',
            'cancelled': 'factory',
        }
        
        tracking_status = status_mapping.get(self.status, 'factory')
        
        # تحديث بدون إطلاق الإشارات لتجنب الrecursion
        Order.objects.filter(pk=self.order.pk).update(
            order_status=self.status,
            tracking_status=tracking_status
        )


class ManufacturingOrderItem(models.Model):
    """نموذج يمثل عناصر أمر التصنيع"""
    
    manufacturing_order = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='أمر التصنيع'
    )
    
    product_name = models.CharField(
        max_length=255,
        verbose_name='اسم المنتج'
    )
    
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='الكمية'
    )
    
    specifications = models.TextField(
        blank=True,
        null=True,
        verbose_name='المواصفات'
    )
    
    status = models.CharField(
        max_length=30,
        choices=ManufacturingOrder.STATUS_CHOICES,
        default='pending',
        verbose_name='حالة العنصر'
    )
    
    class Meta:
        verbose_name = 'عنصر أمر تصنيع'
        verbose_name_plural = 'عناصر أوامر التصنيع'
    
    def __str__(self):
        return f'{self.product_name} - {self.quantity}'


@receiver(post_save, sender=ManufacturingOrder)
def update_related_models(sender, instance, **kwargs):
    """تحديث النماذج المرتبطة عند تحديث أمر التصنيع"""
    instance.update_order_status()
