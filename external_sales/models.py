from django.db import models
from django.utils.translation import gettext_lazy as _


class DecoratorEngineerProfile(models.Model):
    """
    ملف مهندس الديكور — بيانات مرئية لقسم المبيعات الخارجية فقط
    """

    PRIORITY_CHOICES = [
        ("vip", "VIP — أولوية قصوى"),
        ("active", "نشط"),
        ("regular", "عادي"),
        ("cold", "فاتر — يحتاج إعادة تفعيل"),
    ]

    PRICE_SEGMENT_CHOICES = [
        ("low", "اقتصادي"),
        ("medium", "متوسط"),
        ("luxury", "فاخر"),
    ]

    PROJECT_TYPE_CHOICES = [
        ("residential", "سكني"),
        ("commercial", "تجاري"),
        ("hospitality", "ضيافة / فنادق"),
        ("mixed", "متعدد"),
    ]

    # Core link
    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="decorator_profile",
        verbose_name=_("العميل (المهندس)"),
    )

    # Auto-generated unique code (e.g. DEC-0042)
    designer_code = models.CharField(
        _("كود المهندس"),
        max_length=20,
        unique=True,
        blank=True,
        db_index=True,
        help_text=_("يُولَّد تلقائياً عند الإنشاء"),
    )

    # Business card info
    company_office_name = models.CharField(
        _("اسم المكتب / الشركة"), max_length=200, blank=True
    )
    years_of_experience = models.PositiveSmallIntegerField(
        _("سنوات الخبرة"), null=True, blank=True
    )
    area_of_operation = models.CharField(
        _("منطقة العمل"),
        max_length=300,
        blank=True,
        help_text=_("المدن / المناطق التي يعمل فيها المهندس"),
    )

    # Location
    city = models.CharField(_("المدينة"), max_length=100, blank=True, db_index=True)

    # Social / portfolio
    instagram_handle = models.CharField("Instagram", max_length=100, blank=True)
    portfolio_url = models.URLField("Portfolio URL", blank=True)
    linkedin_url = models.URLField("LinkedIn URL", blank=True)

    # Design preferences
    price_segment = models.CharField(
        _("الشريحة السعرية"),
        max_length=10,
        choices=PRICE_SEGMENT_CHOICES,
        blank=True,
        db_index=True,
    )
    design_style = models.CharField(
        _("أسلوب التصميم"),
        max_length=200,
        blank=True,
        help_text=_("مثال: كلاسيك، مودرن، كونتمبوراري"),
    )
    preferred_colors = models.TextField(_("الألوان المفضلة"), blank=True)
    project_types = models.JSONField(
        _("أنواع المشاريع"),
        default=list,
        blank=True,
        help_text=_("أنواع المشاريع التي يتخصص فيها المهندس"),
    )

    # Department-private notes & interests
    interests_notes = models.TextField(
        _("اهتمامات المهندس وتفضيلاته"),
        blank=True,
        help_text=_("أنواع الخامات والأقمشة المفضلة"),
    )
    internal_notes = models.TextField(
        _("ملاحظات داخلية (للقسم فقط)"), blank=True
    )

    # Priority & assignment
    priority = models.CharField(
        _("الأولوية"),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="regular",
        db_index=True,
    )
    assigned_staff = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_decorator_engineers",
        verbose_name=_("موظف المتابعة"),
        limit_choices_to={"is_active": True},
    )

    # Denormalized cached fields — updated by signals
    last_contact_date = models.DateField(
        _("آخر تواصل"), null=True, blank=True, db_index=True
    )
    last_order_date = models.DateField(
        _("آخر طلب"), null=True, blank=True, db_index=True
    )
    next_followup_date = models.DateField(
        _("موعد المتابعة القادمة"), null=True, blank=True, db_index=True
    )
    total_clients_count = models.PositiveIntegerField(_("عدد العملاء"), default=0)
    total_orders_count = models.PositiveIntegerField(_("عدد الطلبات"), default=0)

    # Timestamps & audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="decorator_profiles_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="decorator_profiles_updated",
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("ملف مهندس ديكور")
        verbose_name_plural = _("ملفات مهندسي الديكور")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["priority", "-created_at"]),
            models.Index(fields=["assigned_staff"]),
            models.Index(fields=["city"]),
        ]
        permissions = [
            ("view_decorator_profiles", "Can view decorator engineer profiles"),
            ("manage_decorator_profiles", "Can manage decorator engineer profiles"),
            ("view_decorator_commissions", "Can view commission data"),
            ("manage_decorator_commissions", "Can manage commissions"),
        ]

    def __str__(self):
        return f"{self.designer_code} - {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.designer_code:
            last = DecoratorEngineerProfile.objects.aggregate(
                last_id=models.Max("id")
            )["last_id"] or 0
            self.designer_code = f"DEC-{(last + 1):04d}"
        super().save(*args, **kwargs)


class EngineerLinkedCustomer(models.Model):
    """
    ربط عميل أفراد بمهندس الديكور يدوياً
    يمثل العملاء الذين جاء بهم المهندس أو تتم متابعتهم من خلاله
    """

    RELATIONSHIP_TYPE_CHOICES = [
        ("referred_client", "عميل أحاله المهندس"),
        ("designer_project", "مشروع المهندس نفسه"),
    ]

    engineer = models.ForeignKey(
        DecoratorEngineerProfile,
        on_delete=models.CASCADE,
        related_name="linked_customers",
        verbose_name=_("المهندس"),
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="engineer_links",
        verbose_name=_("العميل"),
    )
    linked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="customer_links_created",
        verbose_name=_("ربط بواسطة"),
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    relationship_type = models.CharField(
        _("نوع العلاقة"),
        max_length=20,
        choices=RELATIONSHIP_TYPE_CHOICES,
        default="referred_client",
    )
    default_commission_rate = models.DecimalField(
        _("نسبة العمولة الافتراضية %"),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text=_("تُطبق تلقائياً على الطلبات الجديدة إذا لم تُحدَّد قيمة خاصة"),
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True, db_index=True)

    class Meta:
        verbose_name = _("عميل مرتبط بمهندس")
        verbose_name_plural = _("العملاء المرتبطون بمهندسين")
        unique_together = [("engineer", "customer")]
        indexes = [models.Index(fields=["engineer", "is_active"])]

    def __str__(self):
        return f"{self.engineer.designer_code} → {self.customer.name}"


class EngineerLinkedOrder(models.Model):
    """
    ربط طلب محدد بملف مهندس الديكور مع إدارة العمولة
    """

    COMMISSION_STATUS = [
        ("pending", "معلقة"),
        ("approved", "معتمدة"),
        ("paid", "مدفوعة"),
        ("cancelled", "ملغاة"),
    ]
    LINK_TYPE = [
        ("manual", "يدوي"),
        ("auto", "تلقائي عبر العميل المرتبط"),
    ]
    COMMISSION_TYPE_CHOICES = [
        ("percentage", "نسبة مئوية من قيمة الطلب"),
        ("fixed_amount", "مبلغ ثابت"),
    ]

    engineer = models.ForeignKey(
        DecoratorEngineerProfile,
        on_delete=models.CASCADE,
        related_name="linked_orders",
        verbose_name=_("المهندس"),
    )
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="engineer_link",
        verbose_name=_("الطلب"),
    )
    link_type = models.CharField(
        _("نوع الربط"), max_length=10, choices=LINK_TYPE, default="manual"
    )
    linked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_links_created",
        verbose_name=_("ربط بواسطة"),
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    # Commission
    commission_type = models.CharField(
        _("نوع العمولة"),
        max_length=15,
        choices=COMMISSION_TYPE_CHOICES,
        default="percentage",
    )
    commission_rate = models.DecimalField(
        _("نسبة العمولة %"), max_digits=5, decimal_places=2, default=0
    )
    commission_value = models.DecimalField(
        _("قيمة العمولة"),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("يُحسب تلقائياً أو يُدخل يدوياً"),
    )
    commission_status = models.CharField(
        _("حالة العمولة"),
        max_length=10,
        choices=COMMISSION_STATUS,
        default="pending",
        db_index=True,
    )
    commission_paid_at = models.DateTimeField(
        _("تاريخ دفع العمولة"), null=True, blank=True
    )
    commission_paid_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commissions_paid",
    )
    notes = models.TextField(_("ملاحظات العمولة"), blank=True)

    class Meta:
        verbose_name = _("طلب مرتبط بمهندس")
        verbose_name_plural = _("الطلبات المرتبطة بمهندسين")
        indexes = [
            models.Index(fields=["engineer", "commission_status"]),
            models.Index(fields=["engineer", "-linked_at"]),
        ]

    def __str__(self):
        return f"{self.engineer.designer_code} — Order #{self.order.order_number}"

    def calculate_commission(self):
        """احسب قيمة العمولة تلقائياً"""
        if self.commission_type == "fixed_amount":
            return self.commission_value
        if self.commission_rate and self.order_id:
            total = getattr(self.order, "total_amount", 0) or 0
            self.commission_value = (self.commission_rate / 100) * total
        return self.commission_value


class EngineerContactLog(models.Model):
    """
    سجل المتابعة والتواصل مع مهندس الديكور
    """

    CONTACT_TYPES = [
        ("call", "مكالمة هاتفية"),
        ("whatsapp", "رسالة واتساب"),
        ("meeting", "اجتماع"),
        ("appointment", "حجز موعد زيارة"),
        ("email", "بريد إلكتروني"),
        ("visit", "زيارة ميدانية"),
        ("other", "أخرى"),
    ]
    OUTCOME_CHOICES = [
        ("answered", "رد على المكالمة"),
        ("no_answer", "لم يرد"),
        ("busy", "مشغول"),
        ("appointment_booked", "تم حجز موعد"),
        ("interested", "مهتم"),
        ("not_interested", "غير مهتم"),
        ("callback_requested", "طلب معاودة الاتصال"),
        ("completed", "اكتملت المتابعة"),
    ]

    engineer = models.ForeignKey(
        DecoratorEngineerProfile,
        on_delete=models.CASCADE,
        related_name="contact_logs",
        verbose_name=_("المهندس"),
    )
    contact_type = models.CharField(
        _("نوع التواصل"), max_length=15, choices=CONTACT_TYPES, db_index=True
    )
    contact_date = models.DateTimeField(_("تاريخ ووقت التواصل"), db_index=True)
    outcome = models.CharField(
        _("نتيجة التواصل"), max_length=25, choices=OUTCOME_CHOICES
    )
    notes = models.TextField(_("تفاصيل / ملاحظات"))

    # Follow-up scheduling
    next_followup_date = models.DateField(
        _("موعد المتابعة القادمة"), null=True, blank=True, db_index=True
    )
    next_followup_notes = models.TextField(
        _("تفاصيل المتابعة القادمة"), blank=True
    )

    # Appointment details (if outcome == appointment_booked)
    appointment_datetime = models.DateTimeField(
        _("تاريخ ووقت الموعد"), null=True, blank=True
    )
    appointment_location = models.CharField(
        _("مكان الموعد"), max_length=300, blank=True
    )
    appointment_confirmed = models.BooleanField(
        _("تأكيد الموعد"), default=False
    )

    # Audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="contact_logs_created",
        verbose_name=_("سُجِّل بواسطة"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("سجل تواصل")
        verbose_name_plural = _("سجلات التواصل")
        ordering = ["-contact_date"]
        indexes = [
            models.Index(fields=["engineer", "-contact_date"]),
            models.Index(fields=["next_followup_date"]),
            models.Index(fields=["outcome"]),
        ]

    def __str__(self):
        return f"{self.engineer.designer_code} — {self.get_contact_type_display()} ({self.contact_date:%Y-%m-%d})"


class EngineerMaterialInterest(models.Model):
    """
    الخامات والأقمشة التي يفضلها مهندس الديكور
    """

    INTEREST_LEVELS = [
        ("high", "مرتفع"),
        ("medium", "متوسط"),
        ("low", "منخفض"),
    ]

    engineer = models.ForeignKey(
        DecoratorEngineerProfile,
        on_delete=models.CASCADE,
        related_name="material_interests",
        verbose_name=_("المهندس"),
    )
    material_name = models.CharField(
        _("اسم الخامة / القماش"), max_length=200
    )
    inventory_category = models.ForeignKey(
        "inventory.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="engineer_interests",
        verbose_name=_("تصنيف المخزون"),
    )
    interest_level = models.CharField(
        _("درجة الاهتمام"),
        max_length=10,
        choices=INTEREST_LEVELS,
        default="medium",
    )
    request_count = models.PositiveIntegerField(
        _("عدد مرات الطلب"),
        default=1,
        help_text=_("كم مرة طلب المهندس هذه الخامة"),
    )
    last_requested_date = models.DateField(
        _("آخر مرة طُلبت"), null=True, blank=True, db_index=True
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    added_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("اهتمام بخامة")
        verbose_name_plural = _("اهتمامات الخامات")
        ordering = ["-request_count"]
        unique_together = [("engineer", "material_name")]

    def __str__(self):
        return f"{self.engineer.designer_code} — {self.material_name}"
