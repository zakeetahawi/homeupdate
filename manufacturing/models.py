from django.db import models
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

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

    # خط الإنتاج المرتبط بالطلب
    production_line = models.ForeignKey(
        'ProductionLine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manufacturing_orders',
        verbose_name='خط الإنتاج',
        help_text='خط الإنتاج المسؤول عن هذا الطلب'
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

        # إذا كان الطلب مكتمل أو جاهز للتركيب أو تم تسليمه، لا يعتبر متأخر
        if self.status in ['completed', 'ready_install', 'delivered']:
            return False

        # مقارنة تاريخ التسليم المتوقع مع التاريخ الحالي
        today = timezone.now().date()
        return self.expected_delivery_date < today

    @property
    def days_remaining(self):
        """حساب الأيام المتبقية للتسليم"""
        if not self.expected_delivery_date:
            return None

        # إذا كان الطلب مكتمل أو جاهز للتركيب أو تم تسليمه، لا توجد أيام متبقية
        if self.status in ['completed', 'ready_install', 'delivered']:
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

        # تحديث حالة التركيب للطلبات من نوع التركيب
        installation_status_mapping = {
            'pending_approval': 'needs_scheduling',
            'pending': 'needs_scheduling', 
            'in_progress': 'needs_scheduling',
            'ready_install': 'scheduled',
            'completed': 'completed',
            'delivered': 'completed',
            'rejected': 'needs_scheduling',
            'cancelled': 'cancelled',
        }

        new_order_status = order_status_mapping.get(self.status, self.status)
        new_tracking_status = tracking_status_mapping.get(self.status, 'factory')

        # إعداد البيانات للتحديث
        update_fields = {
            'order_status': new_order_status,
            'tracking_status': new_tracking_status
        }

        # إضافة حالة التركيب إذا كان طلب تركيب
        if self.order_type == 'installation':
            new_installation_status = installation_status_mapping.get(self.status)
            if new_installation_status:
                update_fields['installation_status'] = new_installation_status

        # تحديث بدون إطلاق الإشارات لتجنب الrecursion
        Order.objects.filter(pk=self.order.pk).update(**update_fields)

    def assign_production_line(self):
        """تحديد خط الإنتاج تلقائياً بناءً على فرع العميل"""
        if self.production_line:
            return  # إذا كان خط الإنتاج محدد مسبقاً، لا نغيره

        # الحصول على فرع العميل
        customer_branch = None
        if self.order and self.order.customer and hasattr(self.order.customer, 'branch'):
            customer_branch = self.order.customer.branch
        elif self.order and hasattr(self.order, 'branch'):
            customer_branch = self.order.branch

        # تحديد خط الإنتاج المناسب
        self.production_line = ProductionLine.get_default_line_for_branch(customer_branch)

    @property
    def total_items_count(self):
        """إجمالي عدد العناصر"""
        return self.items.count()

    @property
    def received_items_count(self):
        """عدد العناصر المستلمة"""
        return self.items.filter(fabric_received=True).count()

    @property
    def pending_items_count(self):
        """عدد العناصر المعلقة"""
        return self.items.filter(fabric_received=False).count()

    @property
    def items_completion_percentage(self):
        """نسبة اكتمال استلام العناصر"""
        total = self.total_items_count
        if total == 0:
            return 0
        received = self.received_items_count
        return (received / total) * 100

    @property
    def is_all_items_received(self):
        """التحقق من استلام جميع العناصر"""
        return self.received_items_count == self.total_items_count and self.total_items_count > 0

    def get_items_status_display(self):
        """إرجاع حالة العناصر للعرض"""
        if self.is_all_items_received:
            return 'مكتمل العناصر'
        elif self.received_items_count > 0:
            return f'مكتمل جزئياً ({self.received_items_count}/{self.total_items_count})'
        else:
            return 'لم يتم الاستلام'

    def get_items_status_color(self):
        """إرجاع لون حالة العناصر"""
        if self.is_all_items_received:
            return 'success'
        elif self.received_items_count > 0:
            return 'warning'
        else:
            return 'secondary'


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
    
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=1,
        verbose_name='الكمية',
        help_text='يمكن إدخال قيم عشرية مثل 4.25 متر'
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

    # حقول بيانات التقطيع والاستلام الجديدة
    receiver_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='اسم المستلم'
    )

    permit_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='رقم الإذن'
    )

    cutting_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ التقطيع'
    )

    delivery_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ التسليم'
    )

    bag_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='رقم الشنطة'
    )

    # حالة استلام الأقمشة في المصنع
    fabric_received = models.BooleanField(
        default=False,
        verbose_name='تم استلام الأقمشة'
    )

    fabric_received_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ استلام الأقمشة'
    )

    fabric_received_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_fabric_items',
        verbose_name='مستلم الأقمشة'
    )

    # ملاحظات استلام الأقمشة
    fabric_notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات استلام الأقمشة'
    )

    class Meta:
        verbose_name = 'عنصر أمر تصنيع'
        verbose_name_plural = 'عناصر أوامر التصنيع'
    
    def __str__(self):
        return f'{self.product_name} - {self.get_clean_quantity_display()}'
    
    def get_clean_quantity_display(self):
        """إرجاع الكمية بدون أصفار زائدة"""
        if self.quantity is None:
            return '0'

        str_value = str(self.quantity)
        if '.' in str_value:
            str_value = str_value.rstrip('0')
            if str_value.endswith('.'):
                str_value = str_value[:-1]
        return str_value

    def mark_fabric_received(self, bag_number, user, notes=''):
        """تعيين الأقمشة كمستلمة"""
        from django.utils import timezone

        self.fabric_received = True
        self.bag_number = bag_number
        self.fabric_received_date = timezone.now()
        self.fabric_received_by = user
        self.fabric_notes = notes
        self.save()

    @property
    def has_cutting_data(self):
        """التحقق من وجود بيانات التقطيع"""
        return bool(self.receiver_name and self.permit_number)

    @property
    def is_fabric_received(self):
        """التحقق من استلام الأقمشة"""
        return self.fabric_received

    def get_fabric_status_display(self):
        """إرجاع حالة استلام الأقمشة"""
        if self.fabric_received:
            return 'تم الاستلام'
        elif self.has_cutting_data:
            return 'جاهز للاستلام'
        else:
            return 'لم يتم التقطيع'

    def get_fabric_status_color(self):
        """إرجاع لون حالة استلام الأقمشة"""
        if self.fabric_received:
            return 'success'
        elif self.has_cutting_data:
            return 'warning'
        else:
            return 'secondary'


class ProductionLine(models.Model):
    """نموذج خطوط الإنتاج مع دعم أنواع الطلبات"""

    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='اسم خط الإنتاج',
        help_text='اسم مميز لخط الإنتاج'
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='الوصف',
        help_text='وصف تفصيلي لخط الإنتاج ونوع المنتجات التي ينتجها'
    )

    # ربط خط الإنتاج بالفروع
    branches = models.ManyToManyField(
        'accounts.Branch',
        blank=True,
        related_name='production_lines',
        verbose_name='الفروع المرتبطة',
        help_text='الفروع التي يخدمها هذا الخط'
    )

    # أنواع الطلبات المدعومة
    ORDER_TYPE_CHOICES = [
        ('installation', 'تركيب'),
        ('custom', 'تفصيل'),
        ('accessory', 'اكسسوار'),
        ('delivery', 'تسليم'),
        ('inspection', 'معاينة'),
    ]

    supported_order_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name='أنواع الطلبات المدعومة',
        help_text='أنواع الطلبات التي يمكن لهذا الخط التعامل معها'
    )

    # إعدادات خط الإنتاج
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط',
        help_text='تحديد ما إذا كان خط الإنتاج نشطاً أم لا'
    )

    capacity_per_day = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='الطاقة الإنتاجية اليومية',
        help_text='عدد الطلبات التي يمكن إنتاجها يومياً (اختياري)'
    )

    priority = models.PositiveIntegerField(
        default=1,
        verbose_name='الأولوية',
        help_text='أولوية خط الإنتاج (الرقم الأعلى له أولوية أكبر)'
    )

    # معلومات التتبع
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_production_lines',
        verbose_name='تم الإنشاء بواسطة'
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
        verbose_name = 'خط إنتاج'
        verbose_name_plural = 'خطوط الإنتاج'
        ordering = ['-priority', 'name']

    def __str__(self):
        return self.name

    @property
    def orders_count(self):
        """عدد أوامر التصنيع المرتبطة بهذا الخط"""
        return self.manufacturing_orders.count()

    @property
    def active_orders_count(self):
        """عدد أوامر التصنيع النشطة المرتبطة بهذا الخط"""
        return self.manufacturing_orders.filter(
            status__in=['pending_approval', 'pending', 'in_progress']
        ).count()

    @property
    def completed_orders_count(self):
        """عدد أوامر التصنيع المكتملة المرتبطة بهذا الخط"""
        return self.manufacturing_orders.filter(
            status__in=['ready_install', 'completed', 'delivered']
        ).count()

    def get_branches_display(self):
        """عرض الفروع المرتبطة بشكل مقروء"""
        branches = self.branches.all()
        if not branches.exists():
            return 'لا توجد فروع مرتبطة'

        return ', '.join([branch.name for branch in branches[:3]]) + \
               (f' و {branches.count() - 3} فروع أخرى' if branches.count() > 3 else '')

    def get_supported_order_types_display(self):
        """عرض أنواع الطلبات المدعومة بشكل مقروء"""
        if not self.supported_order_types:
            return 'جميع الأنواع'

        type_names = []
        for order_type in self.supported_order_types:
            for choice_value, choice_display in self.ORDER_TYPE_CHOICES:
                if choice_value == order_type:
                    type_names.append(choice_display)
                    break

        return ', '.join(type_names) if type_names else 'جميع الأنواع'

    def supports_order_type(self, order_type):
        """التحقق من دعم نوع طلب معين"""
        if not self.supported_order_types:
            return True  # إذا لم يتم تحديد أنواع، فهو يدعم جميع الأنواع

        return order_type in self.supported_order_types

    @classmethod
    def get_default_line_for_branch(cls, branch):
        """الحصول على خط الإنتاج الافتراضي للفرع"""
        if not branch:
            return cls.objects.filter(is_active=True).order_by('-priority').first()

        # البحث عن خط إنتاج مرتبط بالفرع
        line = cls.objects.filter(
            is_active=True,
            branches=branch
        ).order_by('-priority').first()

        if line:
            return line

        # إذا لم يوجد خط مرتبط بالفرع، إرجاع الخط الافتراضي
        return cls.objects.filter(is_active=True).order_by('-priority').first()


class ManufacturingDisplaySettings(models.Model):
    """إعدادات عرض طلبات التصنيع"""

    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='اسم الإعداد',
        help_text='اسم مميز لإعداد العرض'
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='الوصف',
        help_text='وصف تفصيلي لإعداد العرض'
    )

    # فلاتر العرض
    allowed_statuses = models.JSONField(
        default=list,
        blank=True,
        verbose_name='الحالات المسموحة',
        help_text='حدد الحالات التي ستظهر في هذا العرض'
    )

    allowed_order_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name='أنواع الطلبات المسموحة',
        help_text='حدد أنواع الطلبات التي ستظهر في هذا العرض'
    )

    # المستخدمون المستهدفون
    target_users = models.ManyToManyField(
        'accounts.User',
        blank=True,
        related_name='display_settings',
        verbose_name='المستخدمون المستهدفون',
        help_text='المستخدمون الذين ينطبق عليهم هذا الإعداد'
    )

    apply_to_all_users = models.BooleanField(
        default=False,
        verbose_name='تطبيق على جميع المستخدمين',
        help_text='تطبيق هذا الإعداد على جميع المستخدمين'
    )

    # خيارات العرض
    show_customer_info = models.BooleanField(
        default=True,
        verbose_name='إظهار معلومات العميل',
        help_text='إظهار معلومات العميل في الجدول'
    )

    show_order_details = models.BooleanField(
        default=True,
        verbose_name='إظهار تفاصيل الطلب',
        help_text='إظهار تفاصيل الطلب في الجدول'
    )

    show_dates = models.BooleanField(
        default=True,
        verbose_name='إظهار التواريخ',
        help_text='إظهار التواريخ في الجدول'
    )

    show_files = models.BooleanField(
        default=True,
        verbose_name='إظهار الملفات',
        help_text='إظهار الملفات المرفقة في الجدول'
    )

    # إعدادات الإعداد
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط',
        help_text='تحديد ما إذا كان هذا الإعداد نشطاً'
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name='افتراضي',
        help_text='تحديد ما إذا كان هذا الإعداد افتراضياً'
    )

    priority = models.PositiveIntegerField(
        default=1,
        verbose_name='الأولوية',
        help_text='أولوية الإعداد (الرقم الأعلى له أولوية أكبر)'
    )

    # معلومات التتبع
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_display_settings',
        verbose_name='تم الإنشاء بواسطة'
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
        verbose_name = 'إعداد عرض التصنيع'
        verbose_name_plural = 'إعدادات عرض التصنيع'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return self.name

    def get_allowed_statuses_display(self):
        """عرض الحالات المسموحة بشكل مقروء"""
        if not self.allowed_statuses:
            return 'جميع الحالات'

        status_names = []
        for status in self.allowed_statuses:
            for choice_value, choice_display in ManufacturingOrder.STATUS_CHOICES:
                if choice_value == status:
                    status_names.append(choice_display)
                    break

        return ', '.join(status_names) if status_names else 'جميع الحالات'

    def get_allowed_order_types_display(self):
        """عرض أنواع الطلبات المسموحة بشكل مقروء"""
        if not self.allowed_order_types:
            return 'جميع الأنواع'

        type_names = []
        for order_type in self.allowed_order_types:
            for choice_value, choice_display in ManufacturingOrder.ORDER_TYPE_CHOICES:
                if choice_value == order_type:
                    type_names.append(choice_display)
                    break

        return ', '.join(type_names) if type_names else 'جميع الأنواع'

    def get_target_users_display(self):
        """عرض المستخدمين المستهدفين بشكل مقروء"""
        if self.apply_to_all_users:
            return 'جميع المستخدمين'

        users = self.target_users.all()
        if not users.exists():
            return 'لا يوجد مستخدمون محددون'

        return ', '.join([user.get_full_name() or user.username for user in users[:3]]) + \
               (f' و {users.count() - 3} مستخدمين آخرين' if users.count() > 3 else '')

    @classmethod
    def get_user_settings(cls, user):
        """الحصول على إعدادات العرض للمستخدم"""
        # البحث عن إعداد مخصص للمستخدم
        user_setting = cls.objects.filter(
            is_active=True,
            target_users=user
        ).order_by('-priority').first()

        if user_setting:
            return user_setting

        # البحث عن إعداد عام
        general_setting = cls.objects.filter(
            is_active=True,
            apply_to_all_users=True
        ).order_by('-priority').first()

        if general_setting:
            return general_setting

        # البحث عن الإعداد الافتراضي
        default_setting = cls.objects.filter(
            is_active=True,
            is_default=True
        ).first()

        return default_setting


@receiver(post_save, sender=ManufacturingOrder)
def update_related_models(sender, instance, created, **kwargs):
    """تحديث النماذج المرتبطة عند تحديث أمر التصنيع"""
    # تحديد خط الإنتاج تلقائياً للطلبات الجديدة
    if created:
        instance.assign_production_line()
        if instance.production_line:
            # حفظ بدون إطلاق signal مرة أخرى
            ManufacturingOrder.objects.filter(pk=instance.pk).update(
                production_line=instance.production_line
            )

    instance.update_order_status()


class FabricReceipt(models.Model):
    """
    نموذج استلام الأقمشة من المصنع
    """
    RECEIPT_TYPES = [
        ('cutting_order', 'أمر تقطيع'),
        ('manufacturing_order', 'أمر تصنيع'),
        ('direct', 'استلام مباشر'),
    ]

    # معرف فريد لاستلام الأقمشة
    receipt_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='كود الاستلام',
        help_text='كود فريد لاستلام الأقمشة'
    )

    # نوع الاستلام
    receipt_type = models.CharField(
        max_length=20,
        choices=RECEIPT_TYPES,
        default='cutting_order',
        verbose_name='نوع الاستلام'
    )

    # الطلب الأساسي
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='fabric_receipts',
        verbose_name='الطلب'
    )

    # أمر التقطيع (إذا كان الاستلام من أمر تقطيع)
    cutting_order = models.ForeignKey(
        'cutting.CuttingOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fabric_receipts',
        verbose_name='أمر التقطيع'
    )

    # أمر التصنيع المنشأ
    manufacturing_order = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fabric_receipts',
        verbose_name='أمر التصنيع'
    )

    # رقم الإذن
    permit_number = models.CharField(
        max_length=100,
        verbose_name='رقم الإذن',
        blank=True,
        null=True
    )

    # رقم الشنطة
    bag_number = models.CharField(
        max_length=50,
        verbose_name='رقم الشنطة'
    )

    # تاريخ الاستلام
    receipt_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='تاريخ الاستلام'
    )

    # اسم المستلم الفعلي
    received_by_name = models.CharField(
        max_length=200,
        verbose_name='اسم المستلم',
        blank=True,
        null=True
    )

    # المستخدم الذي سجل الاستلام
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='fabric_receipts',
        verbose_name='المستخدم المسجل'
    )

    # ملاحظات
    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات'
    )

    # تاريخ الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'استلام أقمشة'
        verbose_name_plural = 'استلام الأقمشة'
        ordering = ['-receipt_date']
        indexes = [
            models.Index(fields=['receipt_code'], name='fabric_receipt_code_idx'),
            models.Index(fields=['receipt_date'], name='fabric_receipt_date_idx'),
            models.Index(fields=['bag_number'], name='fabric_receipt_bag_idx'),
        ]

    def __str__(self):
        return f"استلام {self.receipt_code} - {self.order.customer.name}"

    def save(self, *args, **kwargs):
        if not self.receipt_code:
            import uuid
            self.receipt_code = f"FR-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def customer_name(self):
        """اسم العميل"""
        return self.order.customer.name if self.order else ''

    @property
    def contract_number(self):
        """رقم العقد"""
        return self.order.contract_number if self.order else ''

    @property
    def invoice_number(self):
        """رقم الفاتورة"""
        return self.order.invoice_number if self.order else ''

    @property
    def order_number(self):
        """رقم الطلب"""
        return self.order.order_number if self.order else ''


class ProductReceipt(models.Model):
    """
    نموذج استلام المنتجات من المخازن
    """
    # الطلب الأساسي
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='product_receipts',
        verbose_name='الطلب'
    )

    # أمر التقطيع
    cutting_order = models.ForeignKey(
        'cutting.CuttingOrder',
        on_delete=models.CASCADE,
        related_name='product_receipts',
        verbose_name='أمر التقطيع'
    )

    # رقم الإذن (من أمر التقطيع)
    permit_number = models.CharField(
        max_length=100,
        verbose_name='رقم الإذن'
    )

    # رقم الشنطة
    bag_number = models.CharField(
        max_length=50,
        verbose_name='رقم الشنطة'
    )

    # تاريخ الاستلام
    receipt_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='تاريخ الاستلام'
    )

    # اسم المستلم الفعلي
    received_by_name = models.CharField(
        max_length=200,
        verbose_name='اسم المستلم'
    )

    # المستخدم الذي سجل الاستلام
    received_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_receipts',
        verbose_name='المستخدم المسجل'
    )

    # ملاحظات
    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات'
    )

    # تاريخ الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'استلام منتج'
        verbose_name_plural = 'استلام المنتجات'
        ordering = ['-receipt_date']
        indexes = [
            models.Index(fields=['permit_number'], name='product_receipt_permit_idx'),
            models.Index(fields=['receipt_date'], name='product_receipt_date_idx'),
            models.Index(fields=['bag_number'], name='product_receipt_bag_idx'),
        ]

    def __str__(self):
        return f"استلام منتج {self.permit_number} - {self.order.customer.name}"

    @property
    def customer_name(self):
        """اسم العميل"""
        return self.order.customer.name if self.order and self.order.customer else ''

    @property
    def order_number(self):
        """رقم الطلب"""
        return self.order.order_number if self.order else ''


class FabricReceiptItem(models.Model):
    """
    عناصر استلام الأقمشة
    """
    # استلام الأقمشة
    fabric_receipt = models.ForeignKey(
        FabricReceipt,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='استلام الأقمشة'
    )

    # عنصر الطلب الأساسي
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='عنصر الطلب'
    )

    # عنصر التقطيع (إذا كان من أمر تقطيع)
    cutting_item = models.ForeignKey(
        'cutting.CuttingOrderItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='عنصر التقطيع'
    )

    # اسم المنتج
    product_name = models.CharField(
        max_length=200,
        verbose_name='اسم المنتج'
    )

    # الكمية المستلمة
    quantity_received = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name='الكمية المستلمة'
    )

    # ملاحظات خاصة بالعنصر
    item_notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات العنصر'
    )

    # تاريخ الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'عنصر استلام أقمشة'
        verbose_name_plural = 'عناصر استلام الأقمشة'
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} - {self.quantity_received}"
