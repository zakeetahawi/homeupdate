from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class NotificationManager(models.Manager):
    """مدير مخصص للإشعارات"""

    def for_user(self, user):
        """الحصول على الإشعارات المرئية للمستخدم"""
        return self.filter(visible_to=user)

    def unread_for_user(self, user):
        """الحصول على الإشعارات غير المقروءة للمستخدم"""
        return self.filter(
            visible_to=user, read_by__user=user, read_by__is_read=False
        ).distinct()

    def recent_for_user(self, user, limit=10):
        """الحصول على آخر الإشعارات للمستخدم مع معلومات القراءة"""
        return (
            self.for_user(user)
            .prefetch_related("visibility_records")
            .order_by("-created_at")[:limit]
        )


class Notification(models.Model):
    """نموذج الإشعارات الرئيسي"""

    NOTIFICATION_TYPES = [
        ("customer_created", _("عميل جديد")),
        ("order_created", _("طلب جديد")),
        ("order_updated", _("تعديل طلب")),
        ("order_status_changed", _("تغيير حالة طلب")),
        ("order_delivered", _("تسليم طلب")),
        ("installation_scheduled", _("جدولة تركيب")),
        ("installation_completed", _("إكمال تركيب")),
        ("inspection_created", _("معاينة جديدة")),
        ("inspection_status_changed", _("تغيير حالة معاينة")),
        ("manufacturing_status_changed", _("تغيير حالة أمر التصنيع")),
        ("complaint_created", _("شكوى جديدة")),
        ("complaint_status_changed", _("تغيير حالة شكوى")),
        ("complaint_assigned", _("إسناد شكوى")),
        ("complaint_escalated", _("تصعيد شكوى")),
        ("complaint_resolved", _("حل شكوى")),
        ("complaint_overdue", _("تأخر شكوى")),
        ("complaint_comment", _("تعليق على شكوى")),
        # إشعارات التقطيع الجديدة
        ("cutting_order_created", _("أمر تقطيع جديد")),
        ("cutting_completed", _("اكتمال التقطيع")),
        ("cutting_item_rejected", _("رفض عنصر تقطيع")),
        ("stock_shortage", _("نقص في المخزون")),
        ("fabric_received", _("استلام أقمشة")),
        ("cutting_ready_for_pickup", _("جاهز للاستلام من التقطيع")),
        # إشعارات التحويلات المخزنية
        ("transfer_cancelled", _("إلغاء تحويل مخزني")),
        ("transfer_rejected", _("رفض تحويل مخزني")),
        # إشعارات رفض الطلبات
        ("order_rejected", _("رفض طلب")),
    ]

    PRIORITY_LEVELS = [
        ("low", _("منخفضة")),
        ("normal", _("عادية")),
        ("high", _("عالية")),
        ("urgent", _("عاجلة")),
    ]

    # الحقول الأساسية
    title = models.CharField(
        _("العنوان"), max_length=200, help_text=_("عنوان قصير للإشعار")
    )

    message = models.TextField(_("الرسالة"), help_text=_("نص تفصيلي للإشعار"))

    notification_type = models.CharField(
        _("نوع الإشعار"), max_length=30, choices=NOTIFICATION_TYPES, db_index=True
    )

    priority = models.CharField(
        _("الأولوية"),
        max_length=10,
        choices=PRIORITY_LEVELS,
        default="normal",
        db_index=True,
    )

    # الكائن المرتبط (Generic Foreign Key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("نوع المحتوى"),
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(_("معرف الكائن"), null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    # المستخدم المنشئ
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notifications",
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    # المستخدمون المصرح لهم برؤية الإشعار
    visible_to = models.ManyToManyField(
        User,
        through="NotificationVisibility",
        related_name="visible_notifications",
        verbose_name=_("مرئي لـ"),
    )

    # التوقيتات
    created_at = models.DateTimeField(
        _("تاريخ الإنشاء"), auto_now_add=True, db_index=True
    )

    # بيانات إضافية (JSON)
    extra_data = models.JSONField(
        _("بيانات إضافية"),
        default=dict,
        blank=True,
        help_text=_("بيانات إضافية للإشعار في صيغة JSON"),
    )

    objects = NotificationManager()

    class Meta:
        verbose_name = _("إشعار")
        verbose_name_plural = _("الإشعارات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["notification_type", "-created_at"]),
            models.Index(fields=["priority", "-created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"

    def get_absolute_url(self):
        """الحصول على رابط الإشعار — بدون استعلامات DB إضافية"""
        # محاولة بناء الرابط من extra_data مباشرة (بدون استعلام DB)
        if self.extra_data:
            # إذا كان الرابط محفوظ مباشرة
            if "url" in self.extra_data:
                return self.extra_data["url"]

            # بناء رابط الطلب من رقم الطلب
            if "order_number" in self.extra_data:
                return f"/orders/order/{self.extra_data['order_number']}/"

            # بناء رابط من order_id
            if "order_id" in self.extra_data:
                return f"/orders/{self.extra_data['order_id']}/"

            # بناء رابط العميل من كود العميل
            if "customer_code" in self.extra_data:
                return f"/customers/{self.extra_data['customer_code']}/"

            # بناء رابط المعاينة من رقم العقد
            if "contract_number" in self.extra_data:
                return f"/inspections/{self.extra_data['contract_number']}/"

        # رابط افتراضي لصفحة تفاصيل الإشعار
        return reverse("notifications:detail", kwargs={"pk": self.pk})

    def get_icon_and_color(self):
        """الحصول على أيقونة ولون الإشعار حسب النوع"""
        icon_map = {
            # إشعارات الطلبات
            "order_created": {
                "icon": "fas fa-shopping-cart",
                "color": "#2196f3",
                "bg": "#e3f2fd",
            },
            "order_status_changed": {
                "icon": "fas fa-exchange-alt",
                "color": "#e67e00",
                "bg": "#fff3e0",
                "header": "orange",
            },
            "order_completed": {
                "icon": "fas fa-check-circle",
                "color": "#28a745",
                "bg": "#d4edda",
                "header": "green",
            },
            "order_delivered": {
                "icon": "fas fa-truck",
                "color": "#28a745",
                "bg": "#d4edda",
                "header": "green",
            },
            # إشعارات المعاينات
            "inspection_created": {
                "icon": "fas fa-search",
                "color": "#9c27b0",
                "bg": "#f3e5f5",
            },
            "inspection_status_changed": {
                "icon": "fas fa-clipboard-check",
                "color": "#e67e00",
                "bg": "#fff3e0",
                "header": "orange",
            },
            "inspection_completed": {
                "icon": "fas fa-check-circle",
                "color": "#28a745",
                "bg": "#d4edda",
                "header": "green",
            },
            "inspection_scheduled": {
                "icon": "fas fa-calendar-check",
                "color": "#9c27b0",
                "bg": "#f3e5f5",
            },
            # إشعارات التصنيع
            "manufacturing_created": {
                "icon": "fas fa-industry",
                "color": "#607d8b",
                "bg": "#eceff1",
            },
            "manufacturing_status_changed": {
                "icon": "fas fa-cogs",
                "color": "#e67e00",
                "bg": "#fff3e0",
                "header": "orange",
            },
            "manufacturing_completed": {
                "icon": "fas fa-check-double",
                "color": "#28a745",
                "bg": "#d4edda",
                "header": "green",
            },
            # إشعارات التركيب
            "installation_scheduled": {
                "icon": "fas fa-tools",
                "color": "#795548",
                "bg": "#efebe9",
            },
            "installation_completed": {
                "icon": "fas fa-home",
                "color": "#28a745",
                "bg": "#d4edda",
                "header": "green",
            },
            "installation_updated": {
                "icon": "fas fa-wrench",
                "color": "#795548",
                "bg": "#efebe9",
            },
            # إشعارات العملاء
            "customer_created": {
                "icon": "fas fa-user-plus",
                "color": "#00bcd4",
                "bg": "#e0f2f1",
            },
            "customer_updated": {
                "icon": "fas fa-user-edit",
                "color": "#00bcd4",
                "bg": "#e0f2f1",
            },
            # إشعارات المدفوعات
            "payment_received": {
                "icon": "fas fa-credit-card",
                "color": "#4caf50",
                "bg": "#e8f5e8",
            },
            "payment_pending": {
                "icon": "fas fa-clock",
                "color": "#ff9800",
                "bg": "#fff3e0",
            },
            # إشعارات النظام
            "system_notification": {
                "icon": "fas fa-bell",
                "color": "#757575",
                "bg": "#f5f5f5",
            },
            "user_notification": {
                "icon": "fas fa-user",
                "color": "#3f51b5",
                "bg": "#e8eaf6",
            },
            # إشعارات التقطيع الجديدة
            "cutting_order_created": {
                "icon": "fas fa-cut",
                "color": "#6f42c1",
                "bg": "#f3e5f5",
            },
            "cutting_completed": {
                "icon": "fas fa-check-circle",
                "color": "#28a745",
                "bg": "#d4edda",
            },
            "cutting_item_rejected": {
                "icon": "fas fa-times-circle",
                "color": "#dc3545",
                "bg": "#f8d7da",
            },
            "stock_shortage": {
                "icon": "fas fa-exclamation-triangle",
                "color": "#fd7e14",
                "bg": "#fff3cd",
            },
            "fabric_received": {
                "icon": "fas fa-industry",
                "color": "#20c997",
                "bg": "#d1ecf1",
            },
            "cutting_ready_for_pickup": {
                "icon": "fas fa-hand-holding",
                "color": "#17a2b8",
                "bg": "#d1ecf1",
            },
            # إشعارات الشكاوى
            "complaint_created": {
                "icon": "fas fa-exclamation-triangle",
                "color": "#ff9800",
                "bg": "#fff3e0",
            },
            "complaint_status_changed": {
                "icon": "fas fa-exchange-alt",
                "color": "#ff5722",
                "bg": "#fbe9e7",
            },
            "complaint_assigned": {
                "icon": "fas fa-user-tag",
                "color": "#e91e63",
                "bg": "#fce4ec",
            },
            "complaint_escalated": {
                "icon": "fas fa-fire",
                "color": "#dc3545",
                "bg": "#f8d7da",
            },
            "complaint_resolved": {
                "icon": "fas fa-check-circle",
                "color": "#28a745",
                "bg": "#d4edda",
            },
            "complaint_overdue": {
                "icon": "fas fa-clock",
                "color": "#dc3545",
                "bg": "#f8d7da",
            },
            "complaint_comment": {
                "icon": "fas fa-comment-alt",
                "color": "#6f42c1",
                "bg": "#e8daf5",
            },
            # إشعارات التحويلات المخزنية
            "transfer_cancelled": {
                "icon": "fas fa-times-circle",
                "color": "#dc3545",
                "bg": "#f8d7da",
            },
            "transfer_rejected": {
                "icon": "fas fa-ban",
                "color": "#ffc107",
                "bg": "#fff3cd",
            },
            # إشعارات رفض الطلبات
            "order_rejected": {
                "icon": "fas fa-times-circle",
                "color": "#dc3545",
                "bg": "#f8d7da",
                "header": "red",
            },
        }

        return icon_map.get(
            self.notification_type,
            {"icon": "fas fa-info-circle", "color": "#757575", "bg": "#f5f5f5"},
        )

    def get_icon_class(self):
        """الحصول على فئة الأيقونة حسب نوع الإشعار"""
        icon_map = {
            "customer_created": "fas fa-user-plus",
            "order_created": "fas fa-shopping-cart",
            "order_updated": "fas fa-edit",
            "order_status_changed": "fas fa-exchange-alt",
            "order_delivered": "fas fa-truck",
            "installation_scheduled": "fas fa-calendar-plus",
            "installation_completed": "fas fa-check-circle",
            "inspection_created": "fas fa-search",
            "inspection_status_changed": "fas fa-clipboard-check",
            "complaint_created": "fas fa-exclamation-triangle",
            "transfer_cancelled": "fas fa-times-circle",
            "transfer_rejected": "fas fa-ban",
            "order_rejected": "fas fa-times-circle",
        }
        return icon_map.get(self.notification_type, "fas fa-bell")

    def get_color_class(self):
        """الحصول على فئة اللون حسب الأولوية"""
        color_map = {
            "low": "text-muted",
            "normal": "text-info",
            "high": "text-warning",
            "urgent": "text-danger",
        }
        return color_map.get(self.priority, "text-info")

    def get_visibility_for_user(self, user):
        """الحصول على سجل الرؤية لهذا الإشعار لمستخدم معين"""
        return self.visibility_records.filter(user=user).first()

    def get_related_info(self):
        """الحصول على معلومات الكائن المرتبط"""
        if not self.related_object:
            return None

        info = {
            "type": self.content_type.model,
            "object": self.related_object,
        }

        # إضافة معلومات محددة حسب النوع
        if self.content_type.model == "order":
            info.update(
                {
                    "code": self.related_object.order_number,
                    "customer": (
                        self.related_object.customer.name
                        if self.related_object.customer
                        else None
                    ),
                    "url": self.related_object.get_absolute_url(),
                }
            )
        elif self.content_type.model == "customer":
            info.update(
                {
                    "code": self.related_object.code,
                    "name": self.related_object.name,
                    "url": self.related_object.get_absolute_url(),
                }
            )
        elif self.content_type.model == "inspection":
            info.update(
                {
                    "code": self.related_object.contract_number
                    or f"معاينة-{self.related_object.pk}",
                    "customer": (
                        self.related_object.customer.name
                        if self.related_object.customer
                        else None
                    ),
                    "url": (
                        self.related_object.get_absolute_url()
                        if hasattr(self.related_object, "get_absolute_url")
                        else None
                    ),
                }
            )
        elif self.content_type.model == "installationschedule":
            info.update(
                {
                    "code": f"تركيب-{self.related_object.pk}",
                    "order": (
                        self.related_object.order.order_number
                        if self.related_object.order
                        else None
                    ),
                    "url": (
                        self.related_object.get_absolute_url()
                        if hasattr(self.related_object, "get_absolute_url")
                        else None
                    ),
                }
            )
        elif self.content_type.model == "manufacturingorder":
            info.update(
                {
                    "code": f"تصنيع-{self.related_object.pk}",
                    "order": (
                        self.related_object.order.order_number
                        if self.related_object.order
                        else None
                    ),
                    "url": (
                        self.related_object.get_absolute_url()
                        if hasattr(self.related_object, "get_absolute_url")
                        else None
                    ),
                }
            )

        return info


class NotificationVisibility(models.Model):
    """نموذج وسطي لتحديد رؤية الإشعارات للمستخدمين"""

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="visibility_records"
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notification_visibility"
    )

    is_read = models.BooleanField(_("مقروء"), default=False, db_index=True)

    read_at = models.DateTimeField(_("تاريخ القراءة"), null=True, blank=True)

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("رؤية الإشعار")
        verbose_name_plural = _("رؤية الإشعارات")
        unique_together = ["notification", "user"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["notification", "user"]),
        ]

    def __str__(self):
        status = _("مقروء") if self.is_read else _("غير مقروء")
        return f"{self.notification.title} - {self.user.username} ({status})"

    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class NotificationSettings(models.Model):
    """إعدادات الإشعارات للمستخدمين"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="notification_settings",
        verbose_name=_("المستخدم"),
    )

    # إعدادات أنواع الإشعارات
    enable_customer_notifications = models.BooleanField(
        _("إشعارات العملاء"), default=True
    )

    enable_order_notifications = models.BooleanField(_("إشعارات الطلبات"), default=True)

    enable_inspection_notifications = models.BooleanField(
        _("إشعارات المعاينات"), default=True
    )

    enable_installation_notifications = models.BooleanField(
        _("إشعارات التركيبات"), default=True
    )

    enable_complaint_notifications = models.BooleanField(
        _("إشعارات الشكاوى"), default=True
    )

    # إعدادات الأولوية
    min_priority_level = models.CharField(
        _("الحد الأدنى لمستوى الأولوية"),
        max_length=10,
        choices=Notification.PRIORITY_LEVELS,
        default="low",
        help_text=_("لن يتم عرض الإشعارات أقل من هذا المستوى"),
    )

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("إعدادات الإشعارات")
        verbose_name_plural = _("إعدادات الإشعارات")

    def __str__(self):
        return f"إعدادات إشعارات {self.user.username}"
