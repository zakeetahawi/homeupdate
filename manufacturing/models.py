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
    
    rejection_reply = models.TextField(
        blank=True,
        null=True,
        verbose_name='رد على الرفض'
    )
    
    rejection_reply_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الرد على الرفض'
    )
    
    has_rejection_reply = models.BooleanField(
        default=False,
        verbose_name='يوجد رد على الرفض'
    )

    completion_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الانتهاء',
        help_text='يتم تعبئته تلقائياً عند اكتمال التصنيع أو جاهزية المنتج للتركيب'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='تم الإنشاء بواسطة'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=True,
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
        return f'طلب تصنيع {self.manufacturing_code} - {self.get_status_display()}'
    
    @property
    def manufacturing_code(self):
        """إرجاع رقم طلب التصنيع الموحد (رقم الطلب + M)"""
        if self.order and self.order.order_number:
            return f"{self.order.order_number}-M"
        return f"#{self.id}-M"  # للبيانات القديمة التي لا تحتوي على order_number
    
    def get_absolute_url(self):
        """إرجاع رابط تفاصيل أمر التصنيع باستخدام كود التصنيع"""
        from django.urls import reverse
        return reverse('manufacturing:order_detail_by_code', args=[self.manufacturing_code])

    def get_delete_url(self):
        """إرجاع رابط حذف أمر التصنيع"""
        from django.urls import reverse
        return reverse('manufacturing:order_delete', kwargs={'pk': self.pk})
    
    @property
    def is_delivery_delayed(self):
        """التحقق من تأخر موعد التسليم"""
        if not self.expected_delivery_date:
            return False

        # إذا كان الطلب مكتمل أو تم تسليمه، لا يعتبر متأخر
        if self.status in ['completed', 'delivered']:
            return False

        # مقارنة تاريخ التسليم المتوقع مع التاريخ الحالي
        today = timezone.now().date()
        return self.expected_delivery_date < today

    @property
    def days_remaining(self):
        """حساب الأيام المتبقية للتسليم"""
        if not self.expected_delivery_date:
            return None

        # إذا كان الطلب مكتمل أو تم تسليمه، لا توجد أيام متبقية
        if self.status in ['completed', 'delivered']:
            return 0

        today = timezone.now().date()
        delta = self.expected_delivery_date - today
        return delta.days

    @property
    def delivery_status_indicator(self):
        """إرجاع مؤشر حالة التسليم (دائرة ملونة مع رقم أو رمز)"""
        if self.is_delivery_delayed:
            return {
                'type': 'overdue',
                'color': 'red',
                'icon': 'fas fa-exclamation-triangle',
                'text': 'متأخر',
                'class': 'delivery-indicator overdue'
            }

        days_left = self.days_remaining
        if days_left is None:
            return {
                'type': 'unknown',
                'color': 'gray',
                'icon': 'fas fa-question',
                'text': '؟',
                'class': 'delivery-indicator unknown'
            }

        if days_left <= 0:
            return {
                'type': 'completed',
                'color': 'green',
                'icon': 'fas fa-check',
                'text': 'مكتمل',
                'class': 'delivery-indicator completed'
            }

        # تحديد لون الدائرة بناءً على الأيام المتبقية
        if days_left <= 3:
            color = 'orange'
            urgency_class = 'urgent'
        elif days_left <= 7:
            color = 'yellow'
            urgency_class = 'warning'
        else:
            color = 'green'
            urgency_class = 'normal'

        return {
            'type': 'countdown',
            'color': color,
            'days': days_left,
            'text': str(days_left),
            'class': f'delivery-indicator countdown {urgency_class}'
        }

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
        # تطابق مباشر بين الحالات
        order_status_mapping = {
            'pending_approval': 'pending_approval',
            'pending': 'pending',
            'in_progress': 'in_progress',
            'ready_install': 'ready_install',
            'completed': 'completed',
            'delivered': 'delivered',
            'rejected': 'rejected',
            'cancelled': 'cancelled',
        }

        # تحديث حالة التتبع للطلب
        tracking_status_mapping = {
            'pending_approval': 'factory',
            'pending': 'factory',
            'in_progress': 'factory',
            'ready_install': 'ready',
            'completed': 'ready',
            'delivered': 'delivered',
            'rejected': 'factory',
            'cancelled': 'factory',
        }

        new_order_status = order_status_mapping.get(self.status, self.status)
        new_tracking_status = tracking_status_mapping.get(self.status, 'factory')

        # تحديث بدون إطلاق الإشارات لتجنب الrecursion
        Order.objects.filter(pk=self.order.pk).update(
            order_status=new_order_status,
            tracking_status=new_tracking_status
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
