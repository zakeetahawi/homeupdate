import uuid

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import Branch, User
from inventory.models import Warehouse


class Section(models.Model):
    """نموذج الأقسام"""

    name = models.CharField(max_length=100, unique=True, verbose_name="اسم القسم")

    description = models.TextField(blank=True, verbose_name="وصف القسم")

    is_active = models.BooleanField(default=True, verbose_name="نشط")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "الأقسام"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CuttingOrder(models.Model):
    """نموذج أمر التقطيع"""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("in_progress", "قيد التقطيع"),
        ("completed", "مكتمل"),
        ("rejected", "مرفوض"),
    ]

    # معرف فريد لأمر التقطيع
    cutting_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود التقطيع",
        help_text="كود فريد لأمر التقطيع",
    )

    # الطلب المرتبط
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="cutting_orders",
        verbose_name="الطلب",
    )

    # المستودع المسؤول عن التقطيع
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="cutting_orders",
        verbose_name="المستودع",
    )

    # حالة أمر التقطيع
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="حالة التقطيع",
    )

    # تواريخ مهمة
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ بدء التقطيع"
    )

    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ اكتمال التقطيع"
    )

    # سبب الرفض
    rejection_reason = models.TextField(
        blank=True, verbose_name="سبب الرفض", help_text="يُملأ في حالة رفض أمر التقطيع"
    )

    # حقل جديد لتتبع ما إذا كان الأمر يحتاج لإصلاح (لأغراض الأداء)
    needs_fix = models.BooleanField(
        default=False, verbose_name="يحتاج لإصلاح", db_index=True
    )

    # المستخدم المسؤول
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_cutting_orders",
        verbose_name="مسؤول التقطيع",
    )

    # ملاحظات عامة
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # إشعارات لمنشئ الطلب
    notifications_sent = models.JSONField(
        default=list, blank=True, verbose_name="الإشعارات المرسلة"
    )

    class Meta:
        verbose_name = "أمر تقطيع"
        verbose_name_plural = "أوامر التقطيع"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order"], name="cutting_order_idx"),
            models.Index(fields=["warehouse"], name="cutting_warehouse_idx"),
            models.Index(fields=["status"], name="cutting_status_idx"),
            models.Index(fields=["created_at"], name="cutting_created_idx"),
            # NEW Performance Indexes
            models.Index(
                fields=["status", "created_at"], name="cut_status_created_idx"
            ),
            models.Index(fields=["warehouse", "status"], name="cut_wareh_status_idx"),
            models.Index(fields=["order", "status"], name="cut_order_status_idx"),
            models.Index(
                fields=["assigned_to", "status"], name="cut_assign_status_idx"
            ),
        ]

    def __str__(self):
        return f"تقطيع {self.cutting_code} - {self.order.customer.name}"

    def save(self, *args, **kwargs):
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(self, ["cutting_code", "notes"])

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
        return self.items.filter(status="completed").count()

    @property
    def pending_items(self):
        """عدد العناصر المعلقة"""
        return self.items.filter(status="pending").count()

    @property
    def rejected_items(self):
        """عدد العناصر المرفوضة"""
        return self.items.filter(status="rejected").count()

    @property
    def completion_percentage(self):
        """نسبة الإنجاز"""
        if self.total_items == 0:
            return 0
        return (self.completed_items / self.total_items) * 100

    @property
    def has_rejected_items(self):
        """التحقق من وجود عناصر مرفوضة"""
        return self.items.filter(status="rejected").exists()


class CuttingOrderItem(models.Model):
    """نموذج عنصر أمر التقطيع"""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("in_progress", "قيد التقطيع"),
        ("completed", "مكتمل"),
        ("rejected", "مرفوض"),
    ]

    # أمر التقطيع
    cutting_order = models.ForeignKey(
        CuttingOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="أمر التقطيع",
    )

    # عنصر الطلب الأصلي
    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.CASCADE,
        related_name="cutting_items",
        verbose_name="عنصر الطلب",
    )

    # حالة التقطيع
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="حالة التقطيع",
    )

    # بيانات التقطيع
    cutter_name = models.CharField(
        max_length=100, blank=True, verbose_name="اسم القصاص"
    )

    permit_number = models.CharField(
        max_length=50, blank=True, verbose_name="رقم الإذن"
    )

    receiver_name = models.CharField(
        max_length=100, blank=True, verbose_name="اسم المستلم"
    )

    # تواريخ مهمة
    cutting_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ التقطيع"
    )

    delivery_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ التسليم"
    )

    # تاريخ الخروج (تاريخ الإكمال الفعلي)
    exit_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الخروج")

    # سبب التسجيل بتاريخ سابق
    backdate_reason = models.TextField(
        blank=True, verbose_name="سبب التسجيل بتاريخ سابق"
    )

    # كمية إضافية
    additional_quantity = models.DecimalField(
        max_digits=10, decimal_places=3, default=0, verbose_name="كمية إضافية"
    )

    # ملاحظات خاصة بالعنصر
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # سبب الرفض
    rejection_reason = models.TextField(blank=True, verbose_name="سبب الرفض")

    # حقول تكامل المخزون الجديدة
    inventory_deducted = models.BooleanField(
        default=False, verbose_name="تم خصم المخزون"
    )

    inventory_transaction = models.ForeignKey(
        "inventory.StockTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cutting_items",
        verbose_name="معاملة المخزون",
    )

    inventory_deduction_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ خصم المخزون"
    )

    # المستخدم الذي قام بالتحديث
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="محدث بواسطة",
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    # استلام الأقمشة في المصنع
    fabric_received = models.BooleanField(
        default=False, verbose_name="تم استلام الأقمشة"
    )

    # رقم الشنطة
    bag_number = models.CharField(max_length=50, blank=True, verbose_name="رقم الشنطة")

    # تاريخ الإنشاء
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ الإنشاء", null=True, blank=True
    )

    class Meta:
        verbose_name = "عنصر تقطيع"
        verbose_name_plural = "عناصر التقطيع"
        ordering = ["cutting_order", "order_item"]
        indexes = [
            models.Index(fields=["cutting_order"], name="cutting_item_order_idx"),
            models.Index(fields=["order_item"], name="cutting_item_original_idx"),
            models.Index(fields=["status"], name="cutting_item_status_idx"),
            # NEW Performance Indexes
            models.Index(
                fields=["cutting_order", "status"], name="cut_item_ord_sts_idx"
            ),
            models.Index(fields=["status", "exit_date"], name="cut_item_sts_exit_idx"),
            models.Index(
                fields=["inventory_deducted", "status"], name="cut_item_inv_sts_idx"
            ),
        ]

    def __str__(self):
        return f"{self.order_item.product.name} - {self.get_status_display()}"

    @property
    def total_quantity(self):
        """الكمية الإجمالية (الأصلية + الإضافية)"""
        return self.order_item.quantity + self.additional_quantity

    def mark_as_completed(
        self,
        cutter_name,
        permit_number,
        receiver_name,
        user,
        notes="",
        exit_date=None,
        backdate_reason="",
        auto_deduct_inventory=True,
    ):
        """تعيين العنصر كمكتمل مع خصم المخزون التلقائي"""
        from datetime import date, datetime

        self.status = "completed"
        self.cutter_name = cutter_name
        self.permit_number = permit_number
        self.receiver_name = receiver_name
        self.notes = notes
        self.updated_by = user

        # تحديد تاريخ الخروج وتاريخ التقطيع
        actual_exit_date = exit_date if exit_date else date.today()
        self.exit_date = actual_exit_date

        # تاريخ التقطيع هو التاريخ المدخل يدوياً - استخدام timezone.now() لتجنب naive datetime
        current_time = timezone.now()
        self.cutting_date = datetime.combine(actual_exit_date, current_time.time())
        if timezone.is_naive(self.cutting_date):
            self.cutting_date = timezone.make_aware(self.cutting_date)
        self.delivery_date = self.cutting_date

        # تسجيل تاريخ المعاملة الفعلية في الملاحظات
        transaction_datetime = timezone.now()
        today = date.today()

        # إضافة معلومات المعاملة للملاحظات
        transaction_note = (
            f'[تاريخ المعاملة: {transaction_datetime.strftime("%Y-%m-%d %H:%M")}]'
        )

        if actual_exit_date < today:
            # تسجيل بتاريخ سابق
            self.backdate_reason = (
                backdate_reason or f"تم التسجيل بتاريخ سابق ({actual_exit_date})"
            )
            backdate_note = f"[تاريخ التقطيع: {actual_exit_date}] {backdate_reason}"

            if self.notes:
                self.notes += f"\n{transaction_note}\n{backdate_note}"
            else:
                self.notes = f"{transaction_note}\n{backdate_note}"
        elif actual_exit_date == today:
            # تسجيل بتاريخ اليوم
            if self.notes:
                self.notes += f"\n{transaction_note}"
            else:
                self.notes = transaction_note

        self.save()

        # تحديث حالة الطلب إذا كان نوع المنتجات وتم إكمال جميع العناصر
        self._update_order_status_if_completed()

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
                        title="خطأ في خصم المخزون",
                        message=f"فشل في خصم المخزون للعنصر {self.order_item.product.name}: {str(e)}",
                        notification_type="stock_shortage",
                    )
                except:
                    pass

    def _update_order_status_if_completed(self):
        """تحديث حالة الطلب إلى مكتمل إذا كان نوع منتجات وتم إكمال جميع العناصر"""
        try:
            # التحقق من نوع الطلب
            order = self.cutting_order.order
            if order.order_type != "products":
                return

            # التحقق من حالة الطلب الحالية
            if order.tracking_status != "cutting":
                return

            # التحقق من إكمال جميع عناصر التقطيع
            cutting_order = self.cutting_order
            total_items = cutting_order.items.count()
            completed_items = cutting_order.items.filter(status="completed").count()

            # إذا تم إكمال جميع العناصر، حدث حالة الطلب
            if total_items > 0 and total_items == completed_items:
                old_status = order.tracking_status
                order.tracking_status = "ready"
                order.save()

                # تسجيل التغيير في السجل
                from orders.models import OrderStatusLog

                OrderStatusLog.objects.create(
                    order=order,
                    old_status=old_status,
                    new_status="ready",
                    changed_by=self.updated_by,
                    notes=f"تم تحديث الحالة تلقائياً بعد إكمال جميع عناصر التقطيع ({completed_items}/{total_items})",
                    change_type="cutting",
                    is_automatic=True,
                )
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في تحديث حالة الطلب: {str(e)}")

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
                logger.error(
                    f"خطأ في عكس خصم المخزون للعنصر المرفوض {self.id}: {str(e)}"
                )

        self.status = "rejected"
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
                logger.error(
                    f"خطأ في عكس خصم المخزون عند إعادة التعيين {self.id}: {str(e)}"
                )

        # إعادة تعيين جميع البيانات
        self.status = "pending"
        self.cutter_name = ""
        self.permit_number = ""
        self.receiver_name = ""
        self.cutting_date = None
        self.delivery_date = None

        self.additional_quantity = 0
        self.notes = ""
        self.rejection_reason = ""
        self.updated_by = user
        self.save()

    @property
    def can_deduct_inventory(self):
        """التحقق من إمكانية خصم المخزون"""
        return (
            self.status == "completed"
            and not self.inventory_deducted
            and self.order_item.product
        )

    @property
    def inventory_status_display(self):
        """عرض حالة المخزون"""
        if self.inventory_deducted:
            return "تم الخصم"
        elif self.status == "completed":
            return "جاهز للخصم"
        else:
            return "لم يتم الخصم"

    def get_inventory_status_color(self):
        """لون حالة المخزون"""
        if self.inventory_deducted:
            return "success"
        elif self.status == "completed":
            return "warning"
        else:
            return "secondary"


@receiver(post_save, sender=CuttingOrder)
def update_products_order_status(sender, instance, **kwargs):
    """تحديث حالة طلبات المنتجات عند إكمال التقطيع"""
    if (
        instance.status == "completed"
        and instance.order
        and "products" in instance.order.get_selected_types_list()
    ):

        # طلبات المنتجات لا تحتاج أمر تصنيع - تكتمل مباشرة بعد التقطيع
        old_status = instance.order.order_status
        instance.order.order_status = "completed"
        instance.order.tracking_status = "completed"
        instance.order._updating_statuses = True  # تجنب الحلقة اللانهائية
        instance.order.save()

        # إنشاء سجل تغيير الحالة
        try:
            from orders.models import OrderStatusLog

            # محاولة الحصول على المستخدم من آخر عنصر تم تحديثه
            changed_by = None
            last_updated_item = (
                instance.items.filter(updated_by__isnull=False)
                .order_by("-updated_at")
                .first()
            )
            if last_updated_item:
                changed_by = last_updated_item.updated_by

            # إذا لم نجد، نحاول من assigned_to أو completed_by
            if not changed_by:
                changed_by = getattr(instance, "assigned_to", None) or getattr(
                    instance, "completed_by", None
                )

            OrderStatusLog.objects.create(
                order=instance.order,
                old_status=old_status,
                new_status="completed",
                changed_by=changed_by,
                change_type="cutting",
                notes=f"تم إكمال أمر التقطيع #{instance.cutting_code}",
            )
        except Exception as e:
            print(f"خطأ في تسجيل تغيير حالة الطلب: {e}")

        # إنشاء إشعار عند إكمال التقطيع
        if changed_by:
            try:
                from notifications.signals import create_notification

                customer_name = (
                    instance.order.customer.name
                    if instance.order.customer
                    else "غير محدد"
                )
                title = f"تم إكمال أمر التقطيع - {customer_name}"
                message = (
                    f"تم إكمال أمر التقطيع #{instance.cutting_code} "
                    f"للطلب #{instance.order.order_number} - العميل: {customer_name}"
                )

                create_notification(
                    title=title,
                    message=message,
                    notification_type="cutting_completed",
                    related_object=instance,
                    created_by=changed_by,
                    extra_data={
                        "cutting_code": instance.cutting_code,
                        "order_number": instance.order.order_number,
                        "customer_name": customer_name,
                        "changed_by": changed_by.get_full_name() or changed_by.username,
                    },
                )
            except Exception as e:
                print(f"خطأ في إنشاء إشعار إكمال التقطيع: {e}")

        print(
            f"✅ تم تحديث حالة طلب المنتجات {instance.order.order_number} إلى مكتمل (بدون أمر تصنيع)"
        )


# إشارات لإنشاء أمر التقطيع التلقائي
from django.db.models.signals import post_save
from django.dispatch import receiver

from orders.models import Order


class CuttingReport(models.Model):
    """نموذج تقرير التقطيع"""

    REPORT_TYPE_CHOICES = [
        ("daily", "يومي"),
        ("weekly", "أسبوعي"),
        ("monthly", "شهري"),
        ("yearly", "سنوي"),
    ]

    report_type = models.CharField(
        max_length=10, choices=REPORT_TYPE_CHOICES, verbose_name="نوع التقرير"
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="cutting_reports",
        verbose_name="المستودع",
    )

    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(verbose_name="تاريخ النهاية")

    total_orders = models.PositiveIntegerField(default=0, verbose_name="إجمالي الأوامر")
    completed_items = models.PositiveIntegerField(
        default=0, verbose_name="العناصر المكتملة"
    )
    rejected_items = models.PositiveIntegerField(
        default=0, verbose_name="العناصر المرفوضة"
    )
    pending_items = models.PositiveIntegerField(
        default=0, verbose_name="العناصر المعلقة"
    )

    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    generated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="منشئ التقرير"
    )

    class Meta:
        verbose_name = "تقرير تقطيع"
        verbose_name_plural = "تقارير التقطيع"
        ordering = ["-generated_at"]


class CuttingOrderFixLog(models.Model):
    """سجل إصلاح أوامر التقطيع تلقائياً"""

    TRIGGER_CHOICES = [
        ("auto_on_create", "تلقائي عند الإنشاء"),
        ("auto_on_receive", "تلقائي عند الاستلام"),
        ("manual", "يدوي"),
    ]

    cutting_order = models.ForeignKey(
        CuttingOrder,
        on_delete=models.CASCADE,
        related_name="fix_logs",
        verbose_name="أمر التقطيع",
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإصلاح")
    trigger_source = models.CharField(
        max_length=20,
        choices=TRIGGER_CHOICES,
        default="auto_on_create",
        verbose_name="مصدر التشغيل",
    )

    # ملخص النتائج
    items_moved = models.IntegerField(default=0, verbose_name="أصناف منقولة")
    service_items_deleted = models.IntegerField(
        default=0, verbose_name="أصناف خدمية محذوفة"
    )
    duplicates_deleted = models.IntegerField(default=0, verbose_name="تكرارات محذوفة")
    new_orders_created = models.IntegerField(
        default=0, verbose_name="أوامر جديدة منشأة"
    )

    # تفاصيل دقيقة (JSON)
    details = models.JSONField(default=dict, verbose_name="تفاصيل العملية")

    # النجاح/الفشل
    success = models.BooleanField(default=True, verbose_name="نجاح")
    error_message = models.TextField(blank=True, verbose_name="رسالة الخطأ")

    class Meta:
        verbose_name = "سجل إصلاح أمر تقطيع"
        verbose_name_plural = "سجلات إصلاح أوامر التقطيع"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"إصلاح {self.cutting_order.cutting_code} - {self.timestamp}"
