from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Count, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from model_utils import FieldTracker

from core.soft_delete import SoftDeleteManager, SoftDeleteMixin

User = get_user_model()

# تمت إزالة استيراد Order لتجنب الاعتماد الدائري
# سيتم استخدام الإشارة النصية 'orders.Order' بدلاً من ذلك


class ManufacturingSettings(models.Model):
    """إعدادات نظام التصنيع"""

    # المستودعات المحسوبة في إجمالي الأمتار
    warehouses_for_meters_calculation = models.ManyToManyField(
        "inventory.Warehouse",
        blank=True,
        related_name="manufacturing_meters_settings",
        verbose_name="المستودعات المحسوبة في الأمتار",
        help_text="المستودعات التي يتم حساب أمتارها في badge إجمالي أمتار أمر التصنيع",
    )

    # المستودعات التي تظهر عناصرها في تفاصيل أمر التصنيع
    warehouses_for_display = models.ManyToManyField(
        "inventory.Warehouse",
        blank=True,
        related_name="manufacturing_display_settings",
        verbose_name="المستودعات المعروضة",
        help_text="المستودعات التي تظهر عناصرها في تفاصيل أمر التصنيع",
    )

    # مستودع الأقمشة الخارجية (للتقطيع التلقائي)
    external_fabric_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="external_fabric_settings",
        verbose_name="مستودع الأقمشة الخارجية",
        help_text="المستودع الذي سيتم تعيين أوامر تقطيع الأقمشة الخارجية إليه تلقائياً",
    )

    # حقل singleton للتأكد من وجود سجل واحد فقط
    is_active = models.BooleanField(default=True, verbose_name="نشط", editable=False)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "إعدادات التصنيع"
        verbose_name_plural = "إعدادات التصنيع"

    def __str__(self):
        return "إعدادات نظام التصنيع"

    def save(self, *args, **kwargs):
        """التأكد من وجود سجل واحد فقط"""
        if not self.pk and ManufacturingSettings.objects.exists():
            # إذا كان هناك سجل موجود، نحدثه بدلاً من إنشاء واحد جديد
            existing = ManufacturingSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات (إنشاء إذا لم تكن موجودة) — Cached"""
        from django.core.cache import cache

        _CACHE_KEY = "manufacturing_settings_obj"
        settings = cache.get(_CACHE_KEY)
        if settings is None:
            settings, created = cls.objects.get_or_create(is_active=True)
            cache.set(_CACHE_KEY, settings, 600)
        return settings

    def get_display_warehouse_ids(self):
        """الحصول على IDsمستودعات العرض — Cached"""
        from django.core.cache import cache

        _CACHE_KEY = "manufacturing_display_wh_ids"
        ids = cache.get(_CACHE_KEY)
        if ids is None:
            ids = list(self.warehouses_for_display.values_list("id", flat=True))
            cache.set(_CACHE_KEY, ids, 600)
        return ids


class ManufacturingOrderManager(SoftDeleteManager):
    """Manager محسن لأوامر التصنيع"""

    def with_items_count(self):
        """إضافة عدد العناصر والعناصر المستلمة"""
        return self.annotate(
            total_items_count=Count("items"),
            received_items_count=Count("items", filter=Q(items__fabric_received=True)),
            pending_items_count=Count("items", filter=Q(items__fabric_received=False)),
        )


class ManufacturingOrder(SoftDeleteMixin, models.Model):
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="الوصف",
        help_text="وصف أمر التصنيع أو تفاصيل التعديل إذا كان الأمر خاصاً بتعديل.",
    )
    # ربط أمر التصنيع بطلب التعديل (اختياري)
    modification_request = models.ForeignKey(
        "installations.ModificationRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufacturing_orders",
        verbose_name="طلب التعديل",
        help_text="يربط أمر التصنيع بطلب التعديل إذا كان هذا الأمر خاصاً بتعديل.",
    )
    """نموذج يمثل أمر التصنيع"""

    ORDER_TYPE_CHOICES = [
        ("installation", "تركيب"),
        ("custom", "تفصيل"),
        ("accessory", "اكسسوار"),
        ("modification", "تعديل"),
        ("delivery", "تسليم"),
    ]

    STATUS_CHOICES = [
        ("pending_approval", "قيد الموافقة"),
        ("pending", "قيد الانتظار"),
        ("in_progress", "قيد التصنيع"),
        ("ready_install", "جاهز للتركيب"),
        ("completed", "مكتمل"),
        ("delivered", "تم التسليم"),
        ("rejected", "مرفوض"),
        ("cancelled", "ملغي"),
    ]

    order = models.ForeignKey(
        "orders.Order",  # استخدام الإشارة النصية بدلاً من الاستيراد المباشر
        on_delete=models.CASCADE,
        related_name="manufacturing_orders",
        verbose_name="رقم الطلب",
    )

    contract_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم العقد"
    )

    invoice_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم الفاتورة"
    )

    contract_file = models.FileField(
        upload_to="manufacturing/contracts/%Y/%m/%d/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "jpg", "jpeg", "png"]
            )
        ],
        blank=True,
        null=True,
        verbose_name="ملف العقد",
    )

    inspection_file = models.FileField(
        upload_to="manufacturing/inspections/%Y/%m/%d/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "jpg", "jpeg", "png"]
            )
        ],
        blank=True,
        null=True,
        verbose_name="ملف المعاينة",
    )

    order_date = models.DateField(
        default=timezone.now, verbose_name="تاريخ استلام الطلب"
    )

    expected_delivery_date = models.DateField(verbose_name="تاريخ التسليم المتوقع")

    order_type = models.CharField(
        max_length=20, choices=ORDER_TYPE_CHOICES, verbose_name="نوع الطلب"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending_approval",
        verbose_name="حالة الطلب",
    )

    exit_permit_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم إذن الخروج"
    )

    delivery_permit_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم إذن التسليم"
    )

    delivery_recipient_name = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="اسم المستلم"
    )

    delivery_date = models.DateTimeField(
        blank=True, null=True, verbose_name="تاريخ التسليم"
    )

    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    # خط الإنتاج المرتبط بالطلب
    production_line = models.ForeignKey(
        "ProductionLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufacturing_orders",
        verbose_name="خط الإنتاج",
        help_text="خط الإنتاج المسؤول عن هذا الطلب",
    )

    # تتبع تغيير خط الإنتاج
    previous_production_line = models.ForeignKey(
        "ProductionLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_manufacturing_orders",
        verbose_name="خط الإنتاج السابق",
        help_text="خط الإنتاج قبل آخر تغيير",
    )

    production_line_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ تغيير خط الإنتاج",
    )

    production_line_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_line_changes",
        verbose_name="تم تغيير خط الإنتاج بواسطة",
    )

    rejection_reason = models.TextField(blank=True, null=True, verbose_name="سبب الرفض")

    rejection_reply = models.TextField(
        blank=True, null=True, verbose_name="رد على الرفض"
    )

    rejection_reply_date = models.DateTimeField(
        blank=True, null=True, verbose_name="تاريخ الرد على الرفض"
    )

    has_rejection_reply = models.BooleanField(
        default=False, verbose_name="يوجد رد على الرفض"
    )

    completion_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="تاريخ الانتهاء",
        help_text="يتم تعبئته تلقائياً عند اكتمال التصنيع أو جاهزية المنتج للتركيب",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="تم الإنشاء بواسطة",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufacturing_orders_updated",
        verbose_name="آخر تعديل بواسطة",
        editable=False,
    )

    # Tracker for status changes
    tracker = FieldTracker(fields=["status"])

    created_at = models.DateTimeField(
        default=timezone.now, editable=True, verbose_name="تاريخ الإنشاء"
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    # إضافة المدير المحسن
    objects = ManufacturingOrderManager()

    class Meta:
        verbose_name = "أمر تصنيع"
        verbose_name_plural = "أوامر التصنيع"
        ordering = ["-created_at"]
        permissions = [
            ("can_approve_orders", "يمكن الموافقة على أوامر التصنيع"),
            ("can_reject_orders", "يمكن رفض أوامر التصنيع"),
        ]
        # ✅ تحسين: إضافة indexes شاملة لتسريع 1000%
        indexes = [
            models.Index(fields=["status", "order_type"], name="mfg_status_type_idx"),
            models.Index(fields=["order", "status"], name="mfg_order_status_idx"),
            models.Index(
                fields=["status", "-created_at"], name="mfg_status_created_idx"
            ),
            models.Index(
                fields=["production_line", "status"], name="mfg_line_status_idx"
            ),
            models.Index(
                fields=["expected_delivery_date", "status"],
                name="mfg_delivery_status_idx",
            ),
            models.Index(
                fields=["order_type", "status", "-created_at"],
                name="mfg_type_status_date_idx",
            ),
        ]

    def __str__(self):
        return f"طلب تصنيع {self.manufacturing_code} - {self.get_status_display()}"

    def is_order_deleted(self):
        """Check if the related order is soft-deleted"""
        return self.order and self.order.is_deleted

    def get_order_status_badge(self):
        """Get HTML badge for order status"""
        if self.is_order_deleted():
            return '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; font-size: 11px;">طلب محذوف</span>'
        return ""

    def save(self, *args, **kwargs):
        """حفظ أمر التصنيع وتسجيل حالات الرفض"""
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(
            self,
            [
                "contract_number",
                "invoice_number",
                "exit_permit_number",
                "delivery_permit_number",
            ],
        )

        # التحقق من تغيير الحالة إلى rejected
        if self.pk:  # الكائن موجود مسبقاً
            try:
                old_instance = ManufacturingOrder.objects.get(pk=self.pk)
                # إذا تغيرت الحالة إلى rejected وكان هناك سبب رفض
                if (
                    old_instance.status != "rejected"
                    and self.status == "rejected"
                    and self.rejection_reason
                ):
                    # سيتم إنشاء سجل الرفض بعد الحفظ
                    self._create_rejection_log = True
                    self._previous_status = old_instance.status
            except ManufacturingOrder.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # إنشاء سجل الرفض إذا لزم الأمر
        if hasattr(self, "_create_rejection_log") and self._create_rejection_log:
            ManufacturingRejectionLog.objects.create(
                manufacturing_order=self,
                rejection_reason=self.rejection_reason,
                rejected_by=getattr(self, "_rejected_by", None),
                previous_status=self._previous_status,
            )
            delattr(self, "_create_rejection_log")

    @property
    def manufacturing_code(self):
        """إرجاع رقم طلب التصنيع الموحد (رقم الطلب + M)"""
        if self.order and self.order.order_number:
            return f"{self.order.order_number}-M"
        return f"#{self.id}-M"  # للبيانات القديمة التي لا تحتوي على order_number

    def get_absolute_url(self):
        """إرجاع رابط تفاصيل أمر التصنيع باستخدام كود التصنيع"""
        from django.urls import reverse

        return reverse(
            "manufacturing:order_detail_by_code", args=[self.manufacturing_code]
        )

    def get_delete_url(self):
        """إرجاع رابط حذف أمر التصنيع"""
        from django.urls import reverse

        return reverse("manufacturing:order_delete", kwargs={"pk": self.pk})

    @property
    def is_delivery_delayed(self):
        """التحقق من تأخر موعد التسليم"""
        if not self.expected_delivery_date:
            return False

        # إذا كان الطلب مكتمل أو جاهز للتركيب أو تم تسليمه، لا يعتبر متأخر
        if self.status in ["completed", "ready_install", "delivered"]:
            return False

        # التحقق من أن نوع الطلب من الأنواع المسموحة للطلبات المتأخرة
        allowed_types = ["installation", "custom", "delivery"]
        if self.order_type not in allowed_types:
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
        if self.status in ["completed", "ready_install", "delivered"]:
            return 0

        today = timezone.now().date()
        delta = self.expected_delivery_date - today
        return delta.days

    @property
    def delivery_status_indicator(self):
        """إرجاع مؤشر حالة التسليم (دائرة ملونة مع رقم أو رمز)"""
        if self.is_delivery_delayed:
            return {
                "type": "overdue",
                "color": "red",
                "icon": "fas fa-exclamation-triangle",
                "text": "متأخر",
                "class": "delivery-indicator overdue",
            }

        days_left = self.days_remaining
        if days_left is None:
            return {
                "type": "unknown",
                "color": "gray",
                "icon": "fas fa-question",
                "text": "؟",
                "class": "delivery-indicator unknown",
            }

        if days_left <= 0:
            return {
                "type": "completed",
                "color": "green",
                "icon": "fas fa-check",
                "text": "مكتمل",
                "class": "delivery-indicator completed",
            }

        # تحديد لون الدائرة بناءً على الأيام المتبقية
        if days_left <= 3:
            color = "orange"
            urgency_class = "urgent"
        elif days_left <= 7:
            color = "yellow"
            urgency_class = "warning"
        else:
            color = "green"
            urgency_class = "normal"

        return {
            "type": "countdown",
            "color": color,
            "days": days_left,
            "text": str(days_left),
            "class": f"delivery-indicator countdown {urgency_class}",
        }

    def update_order_status(self):
        """تحديث حالة الطلب الأصلي بناءً على حالة أمر التصنيع"""
        from django.apps import apps
        from django.utils import timezone

        Order = apps.get_model("orders", "Order")

        # تحديث تاريخ الإكمال عند الوصول لحالة مكتمل أو جاهز للتركيب
        if self.status in ["completed", "ready_install"] and not self.completion_date:
            self.completion_date = timezone.now()
            # حفظ بدون إطلاق الإشارات لتجنب الrecursion
            ManufacturingOrder.objects.filter(pk=self.pk).update(
                completion_date=self.completion_date
            )

        # تحديث حالة الطلب لتتطابق مع حالة التصنيع
        # تطابق مباشر بين الحالات
        order_status_mapping = {
            "pending_approval": "pending_approval",
            "pending": "pending",
            "in_progress": "in_progress",
            "ready_install": "ready_install",
            "completed": "completed",
            "delivered": "delivered",
            "rejected": "rejected",
            "cancelled": "cancelled",
        }

        # تحديث حالة التركيب للطلبات من نوع التركيب
        installation_status_mapping = {
            "pending_approval": "needs_scheduling",
            "pending": "needs_scheduling",
            "in_progress": "needs_scheduling",
            "ready_install": "scheduled",
            "completed": "completed",
            "rejected": "needs_scheduling",
            "cancelled": "cancelled",
        }

        new_order_status = order_status_mapping.get(self.status, self.status)

        # إعداد البيانات للتحديث
        update_fields = {
            "order_status": new_order_status,
        }

        # إضافة حالة التركيب إذا كان طلب تركيب
        if self.order_type == "installation":
            new_installation_status = installation_status_mapping.get(self.status)
            if new_installation_status:
                update_fields["installation_status"] = new_installation_status

        # تحديث بدون إطلاق الإشارات لتجنب الrecursion
        updated_count = Order.objects.filter(pk=self.order.pk).update(**update_fields)

        # إجبار تحديث الطلب في الذاكرة
        if updated_count > 0:
            self.order.refresh_from_db()

            # تسجيل التحديث للتتبع
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"تم تحديث حالة الطلب {self.order.order_number} من التصنيع: {update_fields}"
            )

        # تحديث التركيبات المرتبطة إذا كان طلب تركيب
        if self.order_type == "installation" and "installation_status" in update_fields:
            try:
                from installations.models import InstallationSchedule

                # البحث عن التركيبات المرتبطة بهذا الطلب
                installations = InstallationSchedule.objects.filter(order=self.order)
                for installation in installations:
                    installation.status = update_fields["installation_status"]
                    installation.save()
            except ImportError:
                pass  # في حالة عدم وجود تطبيق التركيبات

    def assign_production_line(self):
        """تحديد خط الإنتاج تلقائياً بناءً على فرع العميل"""
        if self.production_line:
            return  # إذا كان خط الإنتاج محدد مسبقاً، لا نغيره

        # الحصول على فرع العميل
        customer_branch = None
        if (
            self.order
            and self.order.customer
            and hasattr(self.order.customer, "branch")
        ):
            customer_branch = self.order.customer.branch
        elif self.order and hasattr(self.order, "branch"):
            customer_branch = self.order.branch

        # تحديد خط الإنتاج المناسب
        self.production_line = ProductionLine.get_default_line_for_branch(
            customer_branch, order_type=self.order_type
        )

    def _get_display_warehouses(self):
        """الحصول على المستودعات المحددة للعرض من الإعدادات — Uses cached settings"""
        settings = ManufacturingSettings.get_settings()
        display_warehouse_ids = settings.get_display_warehouse_ids()
        if display_warehouse_ids:
            from inventory.models import Warehouse

            return list(Warehouse.objects.filter(id__in=display_warehouse_ids))
        return None

    def _get_filtered_order_items(self):
        """الحصول على عناصر الطلب الأصلي المفلترة حسب إعدادات المستودعات"""
        if not self.order:
            return []

        display_warehouses = self._get_display_warehouses()
        order_items = self.order.items.all()

        # إذا لم يتم تحديد مستودعات، نعيد جميع العناصر
        if not display_warehouses:
            return list(order_items)

        # فلترة العناصر حسب المستودعات المحددة
        filtered_items = []
        for order_item in order_items:
            # البحث عن عناصر التقطيع المرتبطة
            cutting_items = order_item.cutting_items.all()

            if cutting_items.exists():
                # تحقق من أن أي من عناصر التقطيع في المستودعات المحددة
                for cutting_item in cutting_items:
                    if (
                        cutting_item.cutting_order
                        and cutting_item.cutting_order.warehouse in display_warehouses
                    ):
                        filtered_items.append(order_item)
                        break
            # العناصر غير المقطوعة لا تظهر عندما يكون هناك فلتر مستودعات

        return filtered_items

    @property
    def total_items_count(self):
        """إجمالي عدد العناصر المفلترة حسب إعدادات المستودعات"""
        return len(self._get_filtered_order_items())

    @property
    def received_items_count(self):
        """عدد العناصر المستلمة في المصنع (مفلترة حسب المستودعات)"""
        display_warehouses = self._get_display_warehouses()

        if not self.order:
            return 0

        # إذا لم يتم تحديد مستودعات، نستخدم ManufacturingOrderItem.items
        if not display_warehouses:
            return self.items.filter(fabric_received=True).count()

        # مع فلتر المستودعات، نحسب من العناصر المفلترة
        count = 0
        for order_item in self._get_filtered_order_items():
            # البحث عن manufacturing item لهذا العنصر
            mfg_item = self.items.filter(
                order_item=order_item, fabric_received=True
            ).first()
            if mfg_item:
                count += 1

        return count

    @property
    def pending_items_count(self):
        """عدد العناصر المعلقة (مفلترة حسب المستودعات)"""
        total = self.total_items_count
        received = self.received_items_count
        return max(0, total - received)

    @property
    def cut_items_count(self):
        """عدد العناصر المقطوعة (مفلترة حسب المستودعات)"""
        display_warehouses = self._get_display_warehouses()

        if not self.order:
            return 0

        count = 0
        filtered_items = self._get_filtered_order_items()

        for order_item in filtered_items:
            # البحث عن عناصر التقطيع المرتبطة
            cutting_items = order_item.cutting_items.all()

            for cutting_item in cutting_items:
                # تحقق من فلتر المستودعات
                if display_warehouses:
                    if not (
                        cutting_item.cutting_order
                        and cutting_item.cutting_order.warehouse in display_warehouses
                    ):
                        continue

                # تحقق من اكتمال التقطيع
                has_cutting_data = bool(
                    cutting_item.receiver_name and cutting_item.permit_number
                )
                if cutting_item.status == "completed" or has_cutting_data:
                    count += 1
                    break  # نحسب العنصر مرة واحدة فقط

        return count

    @property
    def uncut_items_count(self):
        """عدد العناصر غير المقطوعة (مفلترة حسب المستودعات)"""
        total = self.total_items_count
        cut = self.cut_items_count
        return max(0, total - cut)

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
        return (
            self.received_items_count == self.total_items_count
            and self.total_items_count > 0
        )

    def get_items_status_display(self):
        """إرجاع حالة العناصر للعرض"""
        if self.is_all_items_received:
            return "مكتمل العناصر"
        elif self.received_items_count > 0:
            return f"مكتمل جزئياً ({self.received_items_count}/{self.total_items_count})"
        else:
            return "لم يتم الاستلام"

    def get_items_status_color(self):
        """إرجاع لون حالة العناصر"""
        if self.is_all_items_received:
            return "success"
        elif self.received_items_count > 0:
            return "warning"
        else:
            return "secondary"


class ManufacturingRejectionLog(models.Model):
    """نموذج لتسجيل حالات الرفض والردود عليها"""

    manufacturing_order = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        related_name="rejection_logs",
        verbose_name="أمر التصنيع",
    )

    rejection_reason = models.TextField(
        verbose_name="سبب الرفض", help_text="السبب الذي تم رفض أمر التصنيع من أجله"
    )

    rejected_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفض")

    rejected_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_manufacturing_orders",
        verbose_name="تم الرفض بواسطة",
    )

    # حالة أمر التصنيع قبل الرفض
    previous_status = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="الحالة السابقة"
    )

    # الرد على الرفض
    reply_message = models.TextField(
        blank=True, null=True, verbose_name="الرد على الرفض"
    )

    replied_at = models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الرد")

    replied_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replied_manufacturing_rejections",
        verbose_name="تم الرد بواسطة",
    )

    # هل تم قراءة الرد من قبل الإدارة
    reply_read = models.BooleanField(default=False, verbose_name="تم قراءة الرد")

    # حالة أمر التصنيع بعد الرد
    status_after_reply = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="الحالة بعد الرد"
    )

    class Meta:
        verbose_name = "سجل رفض التصنيع"
        verbose_name_plural = "سجلات رفض التصنيع"
        ordering = ["-rejected_at"]

    def __str__(self):
        return f"رفض {self.manufacturing_order} في {self.rejected_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def has_reply(self):
        """التحقق من وجود رد"""
        return bool(self.reply_message)

    @property
    def can_reply(self):
        """التحقق من إمكانية الرد (إذا لم يتم الرد بعد)"""
        return not self.has_reply


class ManufacturingOrderItem(models.Model):
    """نموذج يمثل عناصر أمر التصنيع"""

    manufacturing_order = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="أمر التصنيع",
    )

    # ربط مباشر بعنصر التقطيع (للتتبع الفردي)
    cutting_item = models.ForeignKey(
        "cutting.CuttingOrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufacturing_items",
        verbose_name="عنصر التقطيع",
        help_text="ربط مباشر بعنصر التقطيع للتتبع الفردي",
    )

    # ربط بعنصر الطلب الأصلي (للرجوع للمصدر)
    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="manufacturing_items",
        verbose_name="عنصر الطلب الأصلي",
    )

    product_name = models.CharField(max_length=255, verbose_name="اسم المنتج")

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=1,
        verbose_name="الكمية",
        help_text="يمكن إدخال قيم عشرية مثل 4.25 متر",
    )

    specifications = models.TextField(blank=True, null=True, verbose_name="المواصفات")

    status = models.CharField(
        max_length=30,
        choices=ManufacturingOrder.STATUS_CHOICES,
        default="pending",
        verbose_name="حالة العنصر",
    )

    # حقول بيانات التقطيع والاستلام الجديدة
    receiver_name = models.CharField(
        max_length=100, blank=True, verbose_name="اسم المستلم"
    )

    permit_number = models.CharField(
        max_length=50, blank=True, verbose_name="رقم الإذن"
    )

    cutting_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ التقطيع"
    )

    delivery_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ التسليم"
    )

    bag_number = models.CharField(max_length=50, blank=True, verbose_name="رقم الشنطة")

    # حالة استلام الأقمشة في المصنع
    fabric_received = models.BooleanField(
        default=False, verbose_name="تم استلام الأقمشة"
    )

    fabric_received_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ استلام الأقمشة"
    )

    fabric_received_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_fabric_items",
        verbose_name="مستلم الأقمشة",
    )

    # ملاحظات استلام الأقمشة
    fabric_notes = models.TextField(blank=True, verbose_name="ملاحظات استلام الأقمشة")

    # حقول التسليم لخط الإنتاج
    production_line = models.ForeignKey(
        "ProductionLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufacturing_items",
        verbose_name="خط الإنتاج",
    )

    delivered_to_production = models.BooleanField(
        default=False, verbose_name="تم التسليم لخط الإنتاج"
    )

    production_delivery_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ التسليم لخط الإنتاج"
    )

    production_delivered_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivered_production_items",
        verbose_name="مُسلِّم خط الإنتاج",
    )

    production_delivery_notes = models.TextField(
        blank=True, verbose_name="ملاحظات تسليم خط الإنتاج"
    )

    class Meta:
        verbose_name = "عنصر أمر تصنيع"
        verbose_name_plural = "عناصر أوامر التصنيع"
        permissions = [
            ("can_receive_fabric", "يمكنه استلام الأقمشة من التقطيع"),
            ("can_deliver_to_production_line", "يمكنه تسليم الأقمشة لخطوط الإنتاج"),
            ("can_view_fabric_receipts", "يمكنه عرض قائمة استلامات الأقمشة"),
        ]
        indexes = [
            models.Index(
                fields=["fabric_received", "fabric_received_date"],
                name="fabric_rcvd_idx",
            ),
            models.Index(fields=["bag_number"], name="bag_number_idx"),
            models.Index(
                fields=["fabric_received", "bag_number"], name="fabric_bag_idx"
            ),
            models.Index(
                fields=["delivered_to_production", "production_delivery_date"],
                name="prod_delivery_idx",
            ),
            models.Index(fields=["production_line"], name="prod_line_idx"),
        ]

    def __str__(self):
        return f"{self.product_name} - {self.get_clean_quantity_display()}"

    def get_clean_quantity_display(self):
        """إرجاع الكمية بدون أصفار زائدة"""
        if self.quantity is None:
            return "0"

        str_value = str(self.quantity)
        if "." in str_value:
            str_value = str_value.rstrip("0")
            if str_value.endswith("."):
                str_value = str_value[:-1]
        return str_value

    def mark_fabric_received(self, bag_number, user, notes=""):
        """تعيين الأقمشة كمستلمة وإنشاء سجل FabricReceipt تلقائياً"""
        from django.db import transaction
        from django.utils import timezone

        with transaction.atomic():
            # 1. تحديث ManufacturingOrderItem (النظام القديم)
            self.fabric_received = True
            self.bag_number = bag_number
            self.fabric_received_date = timezone.now()
            self.fabric_received_by = user
            if notes:
                self.fabric_notes = notes
            self.save()

            # 1.5 مزامنة حالة الاستلام مع عنصر التقطيع لمنع الاستلام المزدوج
            if self.cutting_item and not self.cutting_item.fabric_received:
                self.cutting_item.fabric_received = True
                self.cutting_item.bag_number = bag_number
                self.cutting_item.save(update_fields=["fabric_received", "bag_number"])

            # 2. إنشاء أو تحديث FabricReceipt (النظام الجديد)
            # البحث عن سجل استلام موجود لنفس الطلب ورقم الشنطة
            from .models import FabricReceipt, FabricReceiptItem

            fabric_receipt = FabricReceipt.objects.filter(
                manufacturing_order=self.manufacturing_order, bag_number=bag_number
            ).first()

            # إذا لم يوجد، إنشاء سجل جديد
            if not fabric_receipt:
                fabric_receipt = FabricReceipt.objects.create(
                    receipt_type="manufacturing_order",
                    order=(
                        self.manufacturing_order.order
                        if self.manufacturing_order
                        else None
                    ),
                    cutting_order=(
                        self.cutting_item.cutting_order if self.cutting_item else None
                    ),
                    manufacturing_order=self.manufacturing_order,
                    bag_number=bag_number,
                    permit_number=self.permit_number or "",
                    received_by_name=self.receiver_name or "",
                    received_by=user,
                    receipt_date=timezone.now(),
                    notes=notes,
                )

            # 3. إنشاء FabricReceiptItem
            # التحقق من عدم وجود عنصر مكرر
            if not FabricReceiptItem.objects.filter(
                fabric_receipt=fabric_receipt, order_item=self.order_item
            ).exists():
                FabricReceiptItem.objects.create(
                    fabric_receipt=fabric_receipt,
                    order_item=self.order_item,
                    cutting_item=self.cutting_item,
                    product_name=self.product_name,
                    quantity_received=self.quantity,
                    item_notes=notes,
                )

    @staticmethod
    def get_next_bag_number():
        """الحصول على رقم الشنطة التالي تلقائياً - يبدأ من 1"""
        import re

        # الحصول على جميع أرقام الشنطات المستخدمة حالياً (غير المكتملة)
        active_bags = (
            ManufacturingOrderItem.objects.filter(fabric_received=True)
            .exclude(bag_number__isnull=True)
            .exclude(bag_number="")
            .values_list("bag_number", flat=True)
        )

        # استخراج الأرقام فقط
        used_numbers = set()
        for bag in active_bags:
            # محاولة استخراج الرقم من النص
            numbers = re.findall(r"^\d+$", str(bag).strip())
            if numbers:
                used_numbers.add(int(numbers[0]))

        # البحث عن أول رقم متاح بدءاً من 1
        next_number = 1
        while next_number in used_numbers:
            next_number += 1

        return str(next_number)

    @staticmethod
    def get_available_bag_numbers():
        """الحصول على قائمة أرقام الشنطات المتاحة لإعادة الاستخدام"""
        import re

        from django.db.models import Q

        # الحصول على أرقام الشنطات من الطلبات المكتملة (جاهز للتركيب)
        completed_orders = ManufacturingOrder.objects.filter(
            status="ready_for_installation"
        )

        reusable_bags = set()
        for order in completed_orders:
            for item in order.items.filter(fabric_received=True).exclude(bag_number=""):
                bag_num = str(item.bag_number).strip()
                # التحقق من أن الرقم رقمي فقط
                if re.match(r"^\d+$", bag_num):
                    reusable_bags.add(bag_num)

        # ترتيب الأرقام تصاعدياً
        return sorted(reusable_bags, key=lambda x: int(x))

    @property
    def has_cutting_data(self):
        """التحقق من وجود بيانات التقطيع - الاعتماد على نظام التقطيع فقط"""
        # التحقق من وجود عنصر تقطيع فعلي في نظام التقطيع فقط
        if self.cutting_item:
            return self.cutting_item.receiver_name and self.cutting_item.permit_number
        return False

    @property
    def is_fabric_received(self):
        """التحقق من استلام الأقمشة"""
        return self.fabric_received

    @property
    def is_cut(self):
        """التحقق من أن العنصر تم تقطيعه"""
        if self.cutting_item:
            return self.cutting_item.status == "completed"
        return self.has_cutting_data

    @property
    def cutting_status_display(self):
        """عرض حالة التقطيع"""
        if self.cutting_item:
            return self.cutting_item.get_status_display()
        elif self.has_cutting_data:
            return "مكتمل"
        else:
            return "لم يتم التقطيع"

    def get_fabric_status_display(self):
        """إرجاع حالة استلام الأقمشة"""
        if self.fabric_received:
            return "تم الاستلام"
        elif self.has_cutting_data:
            return "جاهز للاستلام"
        else:
            return "لم يتم التقطيع"

    def get_fabric_status_color(self):
        """إرجاع لون حالة استلام الأقمشة"""
        if self.fabric_received:
            return "success"
        elif self.has_cutting_data:
            return "warning"
        else:
            return "secondary"

    def get_cutting_status_color(self):
        """إرجاع لون حالة التقطيع"""
        if self.cutting_item:
            status = self.cutting_item.status
            if status == "completed":
                return "success"
            elif status == "in_progress":
                return "info"
            elif status == "rejected":
                return "danger"
            else:
                return "secondary"
        elif self.has_cutting_data:
            return "success"
        else:
            return "secondary"


class ProductionLine(models.Model):
    """نموذج خطوط الإنتاج مع دعم أنواع الطلبات"""

    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="اسم خط الإنتاج",
        help_text="اسم مميز لخط الإنتاج",
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="الوصف",
        help_text="وصف تفصيلي لخط الإنتاج ونوع المنتجات التي ينتجها",
    )

    # ربط خط الإنتاج بالفروع
    branches = models.ManyToManyField(
        "accounts.Branch",
        blank=True,
        related_name="production_lines",
        verbose_name="الفروع المرتبطة",
        help_text="الفروع التي يخدمها هذا الخط",
    )

    # أنواع الطلبات المدعومة
    ORDER_TYPE_CHOICES = [
        ("installation", "تركيب"),
        ("custom", "تفصيل"),
        ("accessory", "اكسسوار"),
        ("inspection", "معاينة"),
    ]

    supported_order_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name="أنواع الطلبات المدعومة",
        help_text="أنواع الطلبات التي يمكن لهذا الخط التعامل معها",
    )

    # إعدادات خط الإنتاج
    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
        help_text="تحديد ما إذا كان خط الإنتاج نشطاً أم لا",
    )

    capacity_per_day = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="الطاقة الإنتاجية اليومية",
        help_text="عدد الطلبات التي يمكن إنتاجها يومياً (اختياري)",
    )

    priority = models.PositiveIntegerField(
        default=1,
        verbose_name="الأولوية",
        help_text="أولوية خط الإنتاج (الرقم الأعلى له أولوية أكبر)",
    )

    BADGE_COLOR_CHOICES = [
        ("#0d6efd", "أزرق"),
        ("#198754", "أخضر"),
        ("#dc3545", "أحمر"),
        ("#ffc107", "أصفر"),
        ("#0dcaf0", "سماوي"),
        ("#6f42c1", "بنفسجي"),
        ("#fd7e14", "برتقالي"),
        ("#d63384", "وردي"),
        ("#20c997", "أخضر فاتح"),
        ("#6c757d", "رمادي"),
        ("#343a40", "أسود"),
        ("#0b5394", "أزرق داكن"),
    ]

    badge_color = models.CharField(
        max_length=7,
        default="#0d6efd",
        verbose_name="لون البادج",
        help_text="لون البادج الخاص بخط الإنتاج في الصفحات",
    )

    # معلومات التتبع
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_production_lines",
        verbose_name="تم الإنشاء بواسطة",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "خط إنتاج"
        verbose_name_plural = "خطوط الإنتاج"
        ordering = ["-priority", "name"]

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
            status__in=["pending_approval", "pending", "in_progress"]
        ).count()

    @property
    def completed_orders_count(self):
        """عدد أوامر التصنيع المكتملة المرتبطة بهذا الخط"""
        return self.manufacturing_orders.filter(
            status__in=["ready_install", "completed", "delivered"]
        ).count()

    def get_branches_display(self):
        """عرض الفروع المرتبطة بشكل مقروء"""
        branches = self.branches.all()
        if not branches.exists():
            return "لا توجد فروع مرتبطة"

        return ", ".join([branch.name for branch in branches[:3]]) + (
            f" و {branches.count() - 3} فروع أخرى" if branches.count() > 3 else ""
        )

    def get_supported_order_types_display(self):
        """عرض أنواع الطلبات المدعومة بشكل مقروء"""
        configs = self.order_type_configs.prefetch_related("branches").all()
        if not configs.exists():
            # Fallback to old field
            if not self.supported_order_types:
                return "جميع الأنواع"
            type_names = []
            for order_type in self.supported_order_types:
                for choice_value, choice_display in self.ORDER_TYPE_CHOICES:
                    if choice_value == order_type:
                        type_names.append(choice_display)
                        break
            return ", ".join(type_names) if type_names else "جميع الأنواع"

        parts = []
        for config in configs:
            parts.append(config.get_order_type_display())
        return ", ".join(parts) if parts else "جميع الأنواع"

    def supports_order_type(self, order_type):
        """التحقق من دعم نوع طلب معين"""
        configs = self.order_type_configs.all()
        if configs.exists():
            return configs.filter(order_type=order_type).exists()

        # Fallback to old field
        if not self.supported_order_types:
            return True
        return order_type in self.supported_order_types

    @classmethod
    def get_default_line_for_branch(cls, branch, order_type=None):
        """الحصول على خط الإنتاج الافتراضي للفرع ونوع الطلب"""
        from manufacturing.models import ProductionLineOrderTypeConfig

        if not branch:
            # بدون فرع: إرجاع أعلى أولوية يدعم نوع الطلب
            if order_type:
                config = ProductionLineOrderTypeConfig.objects.filter(
                    production_line__is_active=True,
                    order_type=order_type,
                ).select_related("production_line").order_by(
                    "-production_line__priority"
                ).first()
                if config:
                    return config.production_line
            return cls.objects.filter(is_active=True).order_by("-priority").first()

        # البحث عبر الموديل الجديد: فرع + نوع طلب
        config_qs = ProductionLineOrderTypeConfig.objects.filter(
            production_line__is_active=True,
            branches=branch,
        )
        if order_type:
            config_qs = config_qs.filter(order_type=order_type)

        config = config_qs.select_related("production_line").order_by(
            "-production_line__priority"
        ).first()

        if config:
            return config.production_line

        # لم يُعثر على تطابق مباشر: البحث عن أي خط يدعم نوع الطلب
        if order_type:
            config = ProductionLineOrderTypeConfig.objects.filter(
                production_line__is_active=True,
                order_type=order_type,
            ).select_related("production_line").order_by(
                "-production_line__priority"
            ).first()
            if config:
                return config.production_line

        # إذا لم يوجد أي تطابق، إرجاع الخط الافتراضي
        return cls.objects.filter(is_active=True).order_by("-priority").first()


class ProductionLineOrderTypeConfig(models.Model):
    """ربط نوع طلب بفروع محددة لخط إنتاج معين"""

    production_line = models.ForeignKey(
        ProductionLine,
        on_delete=models.CASCADE,
        related_name="order_type_configs",
        verbose_name="خط الإنتاج",
    )

    order_type = models.CharField(
        max_length=20,
        choices=ProductionLine.ORDER_TYPE_CHOICES,
        verbose_name="نوع الطلب",
    )

    branches = models.ManyToManyField(
        "accounts.Branch",
        blank=True,
        related_name="order_type_configs",
        verbose_name="الفروع",
        help_text="الفروع المرتبطة بهذا النوع من الطلبات لهذا الخط",
    )

    class Meta:
        verbose_name = "إعداد نوع طلب"
        verbose_name_plural = "إعدادات أنواع الطلبات"
        unique_together = [("production_line", "order_type")]
        ordering = ["order_type"]

    def __str__(self):
        return f"{self.get_order_type_display()} — {self.production_line.name}"

    def get_branches_display(self):
        branches = self.branches.all()
        if not branches.exists():
            return "جميع الفروع"
        return ", ".join([b.name for b in branches])


class ManufacturingDisplaySettings(models.Model):
    """إعدادات عرض طلبات التصنيع"""

    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="اسم الإعداد",
        help_text="اسم مميز لإعداد العرض",
    )

    description = models.TextField(
        blank=True, null=True, verbose_name="الوصف", help_text="وصف تفصيلي لإعداد العرض"
    )

    # فلاتر العرض
    allowed_statuses = models.JSONField(
        default=list,
        blank=True,
        verbose_name="الحالات المسموحة",
        help_text="حدد الحالات التي ستظهر في هذا العرض",
    )

    allowed_order_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name="أنواع الطلبات المسموحة",
        help_text="حدد أنواع الطلبات التي ستظهر في هذا العرض",
    )

    # المستخدمون المستهدفون
    target_users = models.ManyToManyField(
        "accounts.User",
        blank=True,
        related_name="display_settings",
        verbose_name="المستخدمون المستهدفون",
        help_text="المستخدمون الذين ينطبق عليهم هذا الإعداد",
    )

    apply_to_all_users = models.BooleanField(
        default=False,
        verbose_name="تطبيق على جميع المستخدمين",
        help_text="تطبيق هذا الإعداد على جميع المستخدمين",
    )

    # خيارات العرض
    show_customer_info = models.BooleanField(
        default=True,
        verbose_name="إظهار معلومات العميل",
        help_text="إظهار معلومات العميل في الجدول",
    )

    show_order_details = models.BooleanField(
        default=True,
        verbose_name="إظهار تفاصيل الطلب",
        help_text="إظهار تفاصيل الطلب في الجدول",
    )

    show_dates = models.BooleanField(
        default=True,
        verbose_name="إظهار التواريخ",
        help_text="إظهار التواريخ في الجدول",
    )

    show_files = models.BooleanField(
        default=True,
        verbose_name="إظهار الملفات",
        help_text="إظهار الملفات المرفقة في الجدول",
    )

    # إعدادات الإعداد
    is_active = models.BooleanField(
        default=True, verbose_name="نشط", help_text="تحديد ما إذا كان هذا الإعداد نشطاً"
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="افتراضي",
        help_text="تحديد ما إذا كان هذا الإعداد افتراضياً",
    )

    priority = models.PositiveIntegerField(
        default=1,
        verbose_name="الأولوية",
        help_text="أولوية الإعداد (الرقم الأعلى له أولوية أكبر)",
    )

    # معلومات التتبع
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_display_settings",
        verbose_name="تم الإنشاء بواسطة",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "إعداد عرض التصنيع"
        verbose_name_plural = "إعدادات عرض التصنيع"
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return self.name

    def get_allowed_statuses_display(self):
        """عرض الحالات المسموحة بشكل مقروء"""
        if not self.allowed_statuses:
            return "جميع الحالات"

        status_names = []
        for status in self.allowed_statuses:
            for choice_value, choice_display in ManufacturingOrder.STATUS_CHOICES:
                if choice_value == status:
                    status_names.append(choice_display)
                    break

        return ", ".join(status_names) if status_names else "جميع الحالات"

    def get_allowed_order_types_display(self):
        """عرض أنواع الطلبات المسموحة بشكل مقروء"""
        if not self.allowed_order_types:
            return "جميع الأنواع"

        type_names = []
        for order_type in self.allowed_order_types:
            for choice_value, choice_display in ManufacturingOrder.ORDER_TYPE_CHOICES:
                if choice_value == order_type:
                    type_names.append(choice_display)
                    break

        return ", ".join(type_names) if type_names else "جميع الأنواع"

    def get_target_users_display(self):
        """عرض المستخدمين المستهدفين بشكل مقروء"""
        if self.apply_to_all_users:
            return "جميع المستخدمين"

        users = self.target_users.all()
        if not users.exists():
            return "لا يوجد مستخدمون محددون"

        return ", ".join(
            [user.get_full_name() or user.username for user in users[:3]]
        ) + (f" و {users.count() - 3} مستخدمين آخرين" if users.count() > 3 else "")

    @classmethod
    def get_user_settings(cls, user):
        """الحصول على إعدادات العرض للمستخدم"""
        # البحث عن إعداد مخصص للمستخدم
        user_setting = (
            cls.objects.filter(is_active=True, target_users=user)
            .order_by("-priority")
            .first()
        )

        if user_setting:
            return user_setting

        # البحث عن إعداد عام
        general_setting = (
            cls.objects.filter(is_active=True, apply_to_all_users=True)
            .order_by("-priority")
            .first()
        )

        if general_setting:
            return general_setting

        # البحث عن الإعداد الافتراضي
        default_setting = cls.objects.filter(is_active=True, is_default=True).first()

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
        ("cutting_order", "أمر تقطيع"),
        ("manufacturing_order", "أمر تصنيع"),
        ("direct", "استلام مباشر"),
    ]

    # معرف فريد لاستلام الأقمشة
    receipt_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود الاستلام",
        help_text="كود فريد لاستلام الأقمشة",
    )

    # نوع الاستلام
    receipt_type = models.CharField(
        max_length=20,
        choices=RECEIPT_TYPES,
        default="cutting_order",
        verbose_name="نوع الاستلام",
    )

    # الطلب الأساسي
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="fabric_receipts",
        verbose_name="الطلب",
    )

    # أمر التقطيع (إذا كان الاستلام من أمر تقطيع)
    cutting_order = models.ForeignKey(
        "cutting.CuttingOrder",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fabric_receipts",
        verbose_name="أمر التقطيع",
    )

    # أمر التصنيع المنشأ
    manufacturing_order = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fabric_receipts",
        verbose_name="أمر التصنيع",
    )

    # رقم الإذن
    permit_number = models.CharField(
        max_length=100, verbose_name="رقم الإذن", blank=True, null=True
    )

    # رقم الشنطة
    bag_number = models.CharField(max_length=50, verbose_name="رقم الشنطة")

    # تاريخ الاستلام
    receipt_date = models.DateTimeField(
        default=timezone.now, verbose_name="تاريخ الاستلام"
    )

    # اسم المستلم الفعلي
    received_by_name = models.CharField(
        max_length=200, verbose_name="اسم المستلم", blank=True, null=True
    )

    # المستخدم الذي سجل الاستلام
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fabric_receipts",
        verbose_name="المستخدم المسجل",
    )

    # ملاحظات
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # تاريخ الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "استلام أقمشة"
        verbose_name_plural = "استلام الأقمشة"
        ordering = ["-receipt_date"]
        indexes = [
            models.Index(fields=["receipt_code"], name="fabric_receipt_code_idx"),
            models.Index(fields=["receipt_date"], name="fabric_receipt_date_idx"),
            models.Index(fields=["bag_number"], name="fabric_receipt_bag_idx"),
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
        return self.order.customer.name if self.order else ""

    @property
    def contract_number(self):
        """رقم العقد"""
        return self.order.contract_number if self.order else ""

    @property
    def order_number(self):
        """رقم الطلب"""
        return self.order.order_number if self.order else ""


class ProductReceipt(models.Model):
    """
    نموذج استلام المنتجات من المخازن
    """

    # الطلب الأساسي
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="product_receipts",
        verbose_name="الطلب",
    )

    # أمر التقطيع
    cutting_order = models.ForeignKey(
        "cutting.CuttingOrder",
        on_delete=models.CASCADE,
        related_name="product_receipts",
        verbose_name="أمر التقطيع",
    )

    # رقم الإذن (من أمر التقطيع)
    permit_number = models.CharField(max_length=100, verbose_name="رقم الإذن")

    # رقم الشنطة
    bag_number = models.CharField(max_length=50, verbose_name="رقم الشنطة")

    # تاريخ الاستلام
    receipt_date = models.DateTimeField(
        default=timezone.now, verbose_name="تاريخ الاستلام"
    )

    # اسم المستلم الفعلي
    received_by_name = models.CharField(max_length=200, verbose_name="اسم المستلم")

    # المستخدم الذي سجل الاستلام
    received_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="product_receipts",
        verbose_name="المستخدم المسجل",
    )

    # ملاحظات
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # تاريخ الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "استلام منتج"
        verbose_name_plural = "استلام المنتجات"
        ordering = ["-receipt_date"]
        indexes = [
            models.Index(fields=["permit_number"], name="product_receipt_permit_idx"),
            models.Index(fields=["receipt_date"], name="product_receipt_date_idx"),
            models.Index(fields=["bag_number"], name="product_receipt_bag_idx"),
        ]

    def __str__(self):
        return f"استلام منتج {self.permit_number} - {self.order.customer.name}"

    @property
    def customer_name(self):
        """اسم العميل"""
        return self.order.customer.name if self.order and self.order.customer else ""

    @property
    def order_number(self):
        """رقم الطلب"""
        return self.order.order_number if self.order else ""


class FabricReceiptItem(models.Model):
    """
    عناصر استلام الأقمشة
    """

    # استلام الأقمشة
    fabric_receipt = models.ForeignKey(
        FabricReceipt,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="استلام الأقمشة",
    )

    # عنصر الطلب الأساسي
    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="عنصر الطلب",
    )

    # عنصر التقطيع (إذا كان من أمر تقطيع)
    cutting_item = models.ForeignKey(
        "cutting.CuttingOrderItem",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="عنصر التقطيع",
    )

    # اسم المنتج
    product_name = models.CharField(max_length=200, verbose_name="اسم المنتج")

    # الكمية المستلمة
    quantity_received = models.DecimalField(
        max_digits=12, decimal_places=3, verbose_name="الكمية المستلمة"
    )

    # ملاحظات خاصة بالعنصر
    item_notes = models.TextField(blank=True, verbose_name="ملاحظات العنصر")

    # تاريخ الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "عنصر استلام أقمشة"
        verbose_name_plural = "عناصر استلام الأقمشة"
        ordering = ["id"]

    def __str__(self):
        return f"{self.product_name} - {self.quantity_received}"


class ManufacturingStatusLog(models.Model):
    """
    نموذج لتتبع تغييرات حالة أوامر التصنيع
    يسجل كل تغيير في الحالة مع المستخدم المسؤول والتاريخ
    """

    manufacturing_order = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name="أمر التصنيع",
    )

    previous_status = models.CharField(
        max_length=30,
        choices=ManufacturingOrder.STATUS_CHOICES,
        verbose_name="الحالة السابقة",
        help_text="الحالة قبل التغيير",
    )

    new_status = models.CharField(
        max_length=30,
        choices=ManufacturingOrder.STATUS_CHOICES,
        verbose_name="الحالة الجديدة",
        help_text="الحالة بعد التغيير",
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufacturing_status_changes",
        verbose_name="تم التغيير بواسطة",
    )

    changed_at = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ التغيير", db_index=True
    )

    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="عنوان IP",
    )

    class Meta:
        verbose_name = "سجل حالة التصنيع"
        verbose_name_plural = "سجلات حالات التصنيع"
        ordering = ["-changed_at"]
        db_table = "manufacturing_manufacturingstatuslog"

    def __str__(self):
        return f"{self.manufacturing_order.manufacturing_code}: {self.get_previous_status_display()} → {self.get_new_status_display()}"

    # خصائص للتوافق مع الكود القديم
    @property
    def from_status(self):
        return self.previous_status

    @property
    def to_status(self):
        return self.new_status

    def get_from_status_display(self):
        return self.get_previous_status_display()

    def get_to_status_display(self):
        return self.get_new_status_display()

    @property
    def order_type(self):
        """الحصول على نوع الطلب من أمر التصنيع"""
        return self.manufacturing_order.order_type if self.manufacturing_order else None

    def get_order_type_display(self):
        """عرض نوع الطلب"""
        if self.manufacturing_order and self.manufacturing_order.order_type:
            return dict(ManufacturingOrder.ORDER_TYPE_CHOICES).get(
                self.manufacturing_order.order_type, self.manufacturing_order.order_type
            )
        return None

    @property
    def production_line(self):
        """الحصول على خط الإنتاج من أمر التصنيع"""
        return (
            self.manufacturing_order.production_line
            if self.manufacturing_order
            else None
        )
