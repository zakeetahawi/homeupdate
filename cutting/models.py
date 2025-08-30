from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import User, Branch
from inventory.models import Warehouse
import uuid


class CuttingOrder(models.Model):
    """نموذج أمر التقطيع"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التقطيع'),
        ('completed', 'مكتمل'),
        ('rejected', 'مرفوض'),
    ]
    
    # معرف فريد لأمر التقطيع
    cutting_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='كود التقطيع',
        help_text='كود فريد لأمر التقطيع'
    )
    
    # الطلب المرتبط
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='cutting_orders',
        verbose_name='الطلب'
    )
    
    # المستودع المسؤول عن التقطيع
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='cutting_orders',
        verbose_name='المستودع'
    )
    
    # حالة أمر التقطيع
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='حالة التقطيع'
    )
    
    # تواريخ مهمة
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ بدء التقطيع'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ اكتمال التقطيع'
    )

    # سبب الرفض
    rejection_reason = models.TextField(
        blank=True,
        verbose_name='سبب الرفض',
        help_text='يُملأ في حالة رفض أمر التقطيع'
    )
    
    # المستخدم المسؤول
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cutting_orders',
        verbose_name='مسؤول التقطيع'
    )
    
    # ملاحظات عامة
    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات'
    )
    
    # إشعارات لمنشئ الطلب
    notifications_sent = models.JSONField(
        default=list,
        blank=True,
        verbose_name='الإشعارات المرسلة'
    )
    
    class Meta:
        verbose_name = 'أمر تقطيع'
        verbose_name_plural = 'أوامر التقطيع'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order'], name='cutting_order_idx'),
            models.Index(fields=['warehouse'], name='cutting_warehouse_idx'),
            models.Index(fields=['status'], name='cutting_status_idx'),
            models.Index(fields=['created_at'], name='cutting_created_idx'),
        ]
    
    def __str__(self):
        return f"تقطيع {self.cutting_code} - {self.order.customer.name}"
    
    def save(self, *args, **kwargs):
        if not self.cutting_code:
            if self.order and self.order.order_number:
                # استخدام رقم الطلب الأساسي مع إضافة C
                base_number = self.order.order_number
                # التحقق من عدم وجود كود مكرر
                counter = 1
                cutting_code = f"C-{base_number}"
                while CuttingOrder.objects.filter(cutting_code=cutting_code).exists():
                    cutting_code = f"C-{base_number}-{counter}"
                    counter += 1
                self.cutting_code = cutting_code
            else:
                # في حالة عدم وجود طلب، استخدم الطريقة القديمة
                self.cutting_code = f"CUT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def total_items(self):
        """إجمالي عدد العناصر"""
        return self.items.count()
    
    @property
    def completed_items(self):
        """عدد العناصر المكتملة"""
        return self.items.filter(status='completed').count()
    
    @property
    def pending_items(self):
        """عدد العناصر المعلقة"""
        return self.items.filter(status='pending').count()
    
    @property
    def rejected_items(self):
        """عدد العناصر المرفوضة"""
        return self.items.filter(status='rejected').count()
    
    @property
    def completion_percentage(self):
        """نسبة الإنجاز"""
        if self.total_items == 0:
            return 0
        return (self.completed_items / self.total_items) * 100

    @property
    def has_rejected_items(self):
        """التحقق من وجود عناصر مرفوضة"""
        return self.items.filter(status='rejected').exists()


class CuttingOrderItem(models.Model):
    """نموذج عنصر أمر التقطيع"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التقطيع'),
        ('completed', 'مكتمل'),
        ('rejected', 'مرفوض'),
    ]
    
    # أمر التقطيع
    cutting_order = models.ForeignKey(
        CuttingOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='أمر التقطيع'
    )
    
    # عنصر الطلب الأصلي
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.CASCADE,
        related_name='cutting_items',
        verbose_name='عنصر الطلب'
    )
    
    # حالة التقطيع
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='حالة التقطيع'
    )
    
    # بيانات التقطيع
    cutter_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='اسم القصاص'
    )
    
    permit_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='رقم الإذن'
    )
    
    receiver_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='اسم المستلم'
    )
    
    # تواريخ مهمة
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
    

    
    # كمية إضافية
    additional_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='كمية إضافية'
    )
    
    # ملاحظات خاصة بالعنصر
    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات'
    )
    
    # سبب الرفض
    rejection_reason = models.TextField(
        blank=True,
        verbose_name='سبب الرفض'
    )

    # حقول تكامل المخزون الجديدة
    inventory_deducted = models.BooleanField(
        default=False,
        verbose_name='تم خصم المخزون'
    )

    inventory_transaction = models.ForeignKey(
        'inventory.StockTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cutting_items',
        verbose_name='معاملة المخزون'
    )

    inventory_deduction_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاريخ خصم المخزون'
    )

    # المستخدم الذي قام بالتحديث
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='محدث بواسطة'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )
    
    class Meta:
        verbose_name = 'عنصر تقطيع'
        verbose_name_plural = 'عناصر التقطيع'
        ordering = ['cutting_order', 'order_item']
        indexes = [
            models.Index(fields=['cutting_order'], name='cutting_item_order_idx'),
            models.Index(fields=['order_item'], name='cutting_item_original_idx'),
            models.Index(fields=['status'], name='cutting_item_status_idx'),
        ]
    
    def __str__(self):
        return f"{self.order_item.product.name} - {self.get_status_display()}"
    
    @property
    def total_quantity(self):
        """الكمية الإجمالية (الأصلية + الإضافية)"""
        return self.order_item.quantity + self.additional_quantity
    
    def mark_as_completed(self, cutter_name, permit_number, receiver_name, user, notes='', auto_deduct_inventory=True):
        """تعيين العنصر كمكتمل مع خصم المخزون التلقائي"""
        self.status = 'completed'
        self.cutter_name = cutter_name
        self.permit_number = permit_number
        self.receiver_name = receiver_name
        self.cutting_date = timezone.now()
        self.delivery_date = timezone.now()
        self.notes = notes
        self.updated_by = user
        self.save()

        # خصم المخزون التلقائي
        if auto_deduct_inventory and not self.inventory_deducted:
            try:
                from .inventory_integration import deduct_inventory_for_cutting
                transaction = deduct_inventory_for_cutting(self, user)
                if transaction:
                    self.inventory_deduction_date = timezone.now()
                    self.save()
            except Exception as e:
                # تسجيل الخطأ ولكن لا نوقف العملية
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"خطأ في خصم المخزون للعنصر {self.id}: {str(e)}")

                # إرسال إشعار بالخطأ
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        user=user,
                        title='خطأ في خصم المخزون',
                        message=f'فشل في خصم المخزون للعنصر {self.order_item.product.name}: {str(e)}',
                        notification_type='stock_shortage'
                    )
                except:
                    pass
    
    def mark_as_rejected(self, reason, user):
        """تعيين العنصر كمرفوض مع عكس خصم المخزون إذا لزم الأمر"""
        # عكس خصم المخزون إذا كان قد تم خصمه مسبقاً
        if self.inventory_deducted:
            try:
                from .inventory_integration import reverse_inventory_deduction
                reverse_inventory_deduction(self, user, f"رفض التقطيع: {reason}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"خطأ في عكس خصم المخزون للعنصر المرفوض {self.id}: {str(e)}")

        self.status = 'rejected'
        self.rejection_reason = reason
        self.updated_by = user
        self.save()

    def reset_to_pending(self, user):
        """إعادة تعيين العنصر إلى حالة الانتظار"""
        # عكس خصم المخزون إذا كان قد تم خصمه
        if self.inventory_deducted:
            try:
                from .inventory_integration import reverse_inventory_deduction
                reverse_inventory_deduction(self, user, "إعادة تعيين إلى الانتظار")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"خطأ في عكس خصم المخزون عند إعادة التعيين {self.id}: {str(e)}")

        # إعادة تعيين جميع البيانات
        self.status = 'pending'
        self.cutter_name = ''
        self.permit_number = ''
        self.receiver_name = ''
        self.cutting_date = None
        self.delivery_date = None

        self.additional_quantity = 0
        self.notes = ''
        self.rejection_reason = ''
        self.updated_by = user
        self.save()

    @property
    def can_deduct_inventory(self):
        """التحقق من إمكانية خصم المخزون"""
        return (
            self.status == 'completed' and
            not self.inventory_deducted and
            self.order_item.product
        )

    @property
    def inventory_status_display(self):
        """عرض حالة المخزون"""
        if self.inventory_deducted:
            return 'تم الخصم'
        elif self.status == 'completed':
            return 'جاهز للخصم'
        else:
            return 'لم يتم الخصم'

    def get_inventory_status_color(self):
        """لون حالة المخزون"""
        if self.inventory_deducted:
            return 'success'
        elif self.status == 'completed':
            return 'warning'
        else:
            return 'secondary'


@receiver(post_save, sender=CuttingOrder)
def update_products_order_status(sender, instance, **kwargs):
    """تحديث حالة طلبات المنتجات عند إكمال التقطيع"""
    if (instance.status == 'completed' and
        instance.order and
        'products' in instance.order.get_selected_types_list()):

        # طلبات المنتجات لا تحتاج أمر تصنيع - تكتمل مباشرة بعد التقطيع
        instance.order.order_status = 'completed'
        instance.order.tracking_status = 'completed'
        instance.order._updating_statuses = True  # تجنب الحلقة اللانهائية
        instance.order.save()

        print(f"✅ تم تحديث حالة طلب المنتجات {instance.order.order_number} إلى مكتمل (بدون أمر تصنيع)")


# إشارات لإنشاء أمر التقطيع التلقائي
from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order





class CuttingReport(models.Model):
    """نموذج تقرير التقطيع"""
    
    REPORT_TYPE_CHOICES = [
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('yearly', 'سنوي'),
    ]
    
    report_type = models.CharField(
        max_length=10,
        choices=REPORT_TYPE_CHOICES,
        verbose_name='نوع التقرير'
    )
    
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='cutting_reports',
        verbose_name='المستودع'
    )
    
    start_date = models.DateField(verbose_name='تاريخ البداية')
    end_date = models.DateField(verbose_name='تاريخ النهاية')
    
    total_orders = models.PositiveIntegerField(default=0, verbose_name='إجمالي الأوامر')
    completed_items = models.PositiveIntegerField(default=0, verbose_name='العناصر المكتملة')
    rejected_items = models.PositiveIntegerField(default=0, verbose_name='العناصر المرفوضة')
    pending_items = models.PositiveIntegerField(default=0, verbose_name='العناصر المعلقة')
    
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='منشئ التقرير')
    
    class Meta:
        verbose_name = 'تقرير تقطيع'
        verbose_name_plural = 'تقارير التقطيع'
        ordering = ['-generated_at']
