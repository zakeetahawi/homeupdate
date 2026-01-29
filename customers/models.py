from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()
from core.soft_delete import SoftDeleteMixin


def get_customer_types():
    """استرجاع أنواع العملاء من قاعدة البيانات مع تخزين مؤقت"""
    cache_key = "customer_types_choices"
    cached_types = cache.get(cache_key)

    if cached_types is None:
        try:
            from django.apps import apps

            CustomerType = apps.get_model("customers", "CustomerType")

            types = [
                (t.code, t.name)
                for t in CustomerType.objects.filter(is_active=True).order_by("name")
            ]
            cache.set(cache_key, types, timeout=3600)
            cached_types = types
        except Exception:
            cached_types = [
                ("retail", "أفراد"),
                ("wholesale", "جملة"),
                ("corporate", "شركات"),
            ]

    return cached_types or []


class CustomerCategory(models.Model):
    name = models.CharField(_("اسم التصنيف"), max_length=50, db_index=True)
    description = models.TextField(_("وصف التصنيف"), blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("تصنيف العملاء")
        verbose_name_plural = _("تصنيفات العملاء")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="customer_cat_name_idx"),
        ]

    def __str__(self):
        return self.name


def get_default_customer_category_id():
    """Return the PK of the default customer category named 'فرع'.

    If it does not exist create it. This is used as a callable default
    for the Customer.category ForeignKey so newly created customers get
    this category by default.
    """
    try:
        from django.apps import apps

        CustomerCategory = apps.get_model("customers", "CustomerCategory")
        obj, created = CustomerCategory.objects.get_or_create(
            name="فرع", defaults={"description": "تصنيف افتراضي: فرع"}
        )
        return obj.pk
    except Exception:
        # In case migrations or app registry aren't ready, return None.
        # Django will raise a clear error later; returning None avoids
        # import-time database access problems in some contexts.
        return None


class CustomerNote(models.Model):
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="notes_history",
        verbose_name=_("العميل"),
    )
    note = models.TextField(_("الملاحظة"))
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="customer_notes_created",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("ملاحظة العميل")
        verbose_name_plural = _("ملاحظات العملاء")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "created_at"], name="customer_note_idx"),
            models.Index(fields=["created_by"], name="customer_note_creator_idx"),
        ]

    def __str__(self):
        return f"{self.customer.name} - " f"{self.created_at.strftime('%Y-%m-%d')}"


class CustomerAccessLog(models.Model):
    """سجل الوصول للعملاء"""

    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="access_logs",
        verbose_name=_("العميل"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("المستخدم"))
    user_branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_accesses",
        verbose_name=_("فرع المستخدم"),
    )
    customer_branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_accesses",
        verbose_name=_("فرع العميل"),
    )
    is_cross_branch = models.BooleanField(_("وصول عبر فروع"), default=False)
    ip_address = models.GenericIPAddressField(_("عنوان IP"), null=True, blank=True)
    user_agent = models.TextField(_("معلومات المتصفح"), blank=True)
    accessed_at = models.DateTimeField(_("تاريخ الوصول"), auto_now_add=True)

    class Meta:
        verbose_name = _("سجل وصول العميل")
        verbose_name_plural = _("سجلات وصول العملاء")
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(
                fields=["customer", "accessed_at"], name="customer_access_log_idx"
            ),
            models.Index(fields=["user", "accessed_at"], name="user_access_log_idx"),
            models.Index(
                fields=["is_cross_branch", "accessed_at"],
                name="cross_branch_access_idx",
            ),
        ]

    def __str__(self):
        cross_branch_text = " (عبر فروع)" if self.is_cross_branch else ""
        return (
            f"{self.user.get_full_name() or self.user.username} - "
            f"{self.customer.name}{cross_branch_text} - "
            f"{self.accessed_at.strftime('%Y-%m-%d %H:%M')}"
        )

    @property
    def access_type(self):
        """نوع الوصول"""
        if self.is_cross_branch:
            return "وصول عبر فروع"
        return "وصول عادي"

    @property
    def time_since_access(self):
        """الوقت منذ الوصول"""
        from django.utils import timezone

        now = timezone.now()
        diff = now - self.accessed_at

        if diff.days > 0:
            return f"منذ {diff.days} يوم"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"منذ {hours} ساعة"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"منذ {minutes} دقيقة"
        else:
            return "منذ لحظات"


class CustomerType(models.Model):
    """نوع العميل مع إعدادات التسعير والبادج"""

    PRICING_TYPE_CHOICES = [
        ("retail", _("قطاعي")),
        ("wholesale", _("جملة")),
        ("discount", _("قطاعي مع خصم")),
    ]

    BADGE_STYLE_CHOICES = [
        ("solid", _("صلب")),
        ("outline", _("مخطط")),
        ("gradient", _("متدرج")),
        ("glass", _("زجاجي")),
    ]

    # ===== الحقول الأساسية =====
    code = models.CharField(_("الرمز"), max_length=20, unique=True)
    name = models.CharField(_("اسم النوع"), max_length=50, db_index=True)
    description = models.TextField(_("وصف النوع"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    # ===== إعدادات التسعير =====
    pricing_type = models.CharField(
        _("نوع التسعير"),
        max_length=20,
        choices=PRICING_TYPE_CHOICES,
        default="retail",
        help_text=_("يحدد طريقة حساب السعر للعميل"),
    )

    discount_percentage = models.DecimalField(
        _("نسبة الخصم الثابتة"),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text=_("النسبة المئوية للخصم المطبق تلقائياً (للنوع: قطاعي مع خصم)"),
    )

    discount_warehouses = models.ManyToManyField(
        "inventory.Warehouse",
        blank=True,
        related_name="discount_customer_types",
        verbose_name=_("مستودعات الخصم"),
        help_text=_(
            "المستودعات التي يُطبق عليها الخصم تلقائياً - اتركها فارغة لتطبيق الخصم على جميع المستودعات"
        ),
    )

    # ===== إعدادات البادج =====
    badge_color = models.CharField(
        _("لون البادج"),
        max_length=20,
        default="#6c757d",
        help_text=_("لون البادج بصيغة HEX (مثال: #FF5733)"),
    )

    badge_style = models.CharField(
        _("شكل البادج"),
        max_length=20,
        choices=BADGE_STYLE_CHOICES,
        default="solid",
    )

    badge_icon = models.CharField(
        _("أيقونة البادج"),
        max_length=50,
        blank=True,
        help_text=_("أيقونة Font Awesome (مثال: fas fa-crown)"),
    )

    # ===== أنواع الطلبات المتاحة =====
    ORDER_TYPE_CHOICES = [
        ("fabric", _("أقمشة")),
        ("accessory", _("إكسسوار")),
        ("tailoring", _("تفصيل/تسليم")),
        ("installation", _("تركيب")),
        ("inspection", _("معاينة")),
        ("products", _("منتجات")),
    ]

    allowed_order_types = models.JSONField(
        _("أنواع الطلبات المتاحة"),
        default=list,
        blank=True,
        help_text=_(
            "أنواع الطلبات المسموح بها لهذا النوع من العملاء - اتركها فارغة للسماح بجميع الأنواع"
        ),
    )

    class Meta:
        verbose_name = _("نوع العميل")
        verbose_name_plural = _("أنواع العملاء")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"], name="customer_type_code_idx"),
            models.Index(fields=["name"], name="customer_type_name_idx"),
            models.Index(fields=["pricing_type"], name="customer_type_price_idx"),
        ]

    def __str__(self):
        return self.name

    def get_badge_html(self):
        """إرجاع HTML البادج"""
        from django.utils.html import escape
        from django.utils.safestring import mark_safe

        if self.badge_style == "solid":
            style = f"background-color: {escape(self.badge_color)}; color: white;"
        elif self.badge_style == "outline":
            style = f"border: 2px solid {escape(self.badge_color)}; color: {escape(self.badge_color)}; background: transparent;"
        elif self.badge_style == "gradient":
            style = f"background: linear-gradient(135deg, {escape(self.badge_color)}, {escape(self.badge_color)}cc); color: white;"
        else:  # glass
            style = f"background: {escape(self.badge_color)}33; backdrop-filter: blur(4px); color: {escape(self.badge_color)};"

        icon_html = (
            f'<i class="{escape(self.badge_icon)}" style="margin-left: 4px;"></i>'
            if self.badge_icon
            else ""
        )

        return mark_safe(
            f'<span class="customer-type-badge" style="{style}; padding: 2px 8px; border-radius: 4px; font-size: 11px; display: inline-block;">{icon_html} {escape(self.name)}</span>'
        )

    def should_apply_discount_to_warehouse(self, warehouse):
        """تحقق ما إذا كان يجب تطبيق الخصم على هذا المستودع"""
        if self.pricing_type != "discount":
            return False
        if not self.discount_percentage or self.discount_percentage <= 0:
            return False
        # إذا لم تُحدد مستودعات، طبق على الكل
        if not self.discount_warehouses.exists():
            return True
        # تحقق ما إذا كان المستودع ضمن القائمة
        return (
            self.discount_warehouses.filter(pk=warehouse.pk).exists()
            if warehouse
            else True
        )


class DiscountType(models.Model):
    """أنواع الخصومات"""

    name = models.CharField(_("اسم نوع الخصم"), max_length=100, db_index=True)
    percentage = models.DecimalField(
        _("نسبة الخصم"),
        max_digits=5,
        decimal_places=2,
        help_text=_("نسبة الخصم بالمئة (مثال: 10.50)"),
    )
    description = models.TextField(_("وصف الخصم"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True)
    is_default = models.BooleanField(_("افتراضي"), default=False)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("نوع الخصم")
        verbose_name_plural = _("أنواع الخصومات")
        ordering = ["-is_default", "percentage", "name"]
        indexes = [
            models.Index(fields=["is_active"], name="discount_type_active_idx"),
            models.Index(fields=["percentage"], name="discount_type_perc_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.percentage < 0 or self.percentage > 100:
            raise ValidationError(_("نسبة الخصم يجب أن تكون بين 0 و 100"))


class CustomerResponsible(models.Model):
    """مسؤولي العملاء (للشركات والجهات الحكومية)"""

    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="responsibles",
        verbose_name=_("العميل"),
    )
    name = models.CharField(_("اسم المسؤول"), max_length=200, db_index=True)
    position = models.CharField(_("المنصب"), max_length=100, blank=True)
    phone = models.CharField(_("رقم الهاتف"), max_length=20, blank=True)
    email = models.EmailField(_("البريد الإلكتروني"), blank=True)
    is_primary = models.BooleanField(_("المسؤول الرئيسي"), default=False)
    order = models.PositiveSmallIntegerField(_("الترتيب"), default=1)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("مسؤول العميل")
        verbose_name_plural = _("مسؤولي العملاء")
        ordering = ["order", "name"]
        unique_together = [("customer", "order")]
        indexes = [
            models.Index(
                fields=["customer", "is_primary"], name="cust_resp_primary_idx"
            ),
            models.Index(fields=["name"], name="cust_resp_name_idx"),
        ]

    def __str__(self):
        return f"{self.name} - {self.customer.name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # التأكد من وجود مسؤول رئيسي واحد فقط لكل عميل
        if self.is_primary:
            existing_primary = CustomerResponsible.objects.filter(
                customer=self.customer, is_primary=True
            ).exclude(pk=self.pk)

            if existing_primary.exists():
                raise ValidationError(
                    _("يمكن أن يكون هناك مسؤول رئيسي واحد فقط لكل عميل")
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Customer(SoftDeleteMixin, models.Model):
    STATUS_CHOICES = [
        ("active", _("نشط")),
        ("inactive", _("غير نشط")),
        ("blocked", _("محظور")),
    ]

    code = models.CharField(_("كود العميل"), max_length=10, unique=True, blank=True)
    image = models.ImageField(
        _("صورة العميل"), upload_to="customers/images/%Y/%m/", blank=True, null=True
    )
    category = models.ForeignKey(
        CustomerCategory,
        on_delete=models.SET_DEFAULT,
        default=get_default_customer_category_id,
        null=False,
        blank=False,
        related_name="customers",
        verbose_name=_("تصنيف العميل"),
    )
    customer_type = models.CharField(
        _("نوع العميل"), max_length=20, default="retail", db_index=True
    )
    name = models.CharField(_("اسم العميل"), max_length=200, db_index=True)
    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.CASCADE,
        related_name="customers",
        verbose_name=_("الفرع"),
        null=True,
        blank=True,
    )
    phone = models.CharField(_("رقم الهاتف"), max_length=20, db_index=True)
    phone2 = models.CharField(
        _("رقم الهاتف الثاني"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("رقم هاتف إضافي اختياري"),
    )
    email = models.EmailField(_("البريد الإلكتروني"), blank=True, null=True)
    birth_date = models.DateField(
        _("تاريخ الميلاد"),
        blank=True,
        null=True,
        help_text=_("أدخل الشهر واليوم فقط (مثال: 15-03)"),
    )
    address = models.TextField(_("العنوان"))
    location_type = models.CharField(
        max_length=20,
        choices=[
            ("open", "مفتوح"),
            ("compound", "كومبوند"),
        ],
        blank=True,
        null=True,
        verbose_name=_("نوع المكان"),
        help_text="نوع المكان (مفتوح أو كومبوند)",
    )
    interests = models.TextField(
        _("اهتمامات العميل"), blank=True, help_text=_("اكتب اهتمامات العميل وتفضيلاته")
    )
    status = models.CharField(
        _("الحالة"),
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
    )
    notes = models.TextField(_("ملاحظات"), blank=True)

    # حقل الخصم
    discount_type = models.ForeignKey(
        "DiscountType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
        verbose_name=_("نوع الخصم"),
        help_text=_("نوع الخصم المطبق على هذا العميل"),
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="customers_created",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    # ملاحظة: هذا الحقل يجب أن يكون قابل للتعيين من الكود (وليس auto_now_add) حتى يمكن استيراد التاريخ من مصادر خارجية مثل Google Sheets
    created_at = models.DateTimeField(
        _("تاريخ الإنشاء"), default=timezone.now, editable=True
    )
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("عميل")
        verbose_name_plural = _("سجل العملاء")
        ordering = ["-created_at"]
        indexes = [
            # فهارس بسيطة للحقول الأساسية
            models.Index(fields=["code"], name="cust_code_idx"),
            models.Index(fields=["name"], name="cust_name_idx"),
            models.Index(fields=["phone", "phone2"], name="cust_phones_idx"),
            models.Index(fields=["email"], name="cust_email_idx"),
            models.Index(fields=["status"], name="cust_status_idx"),
            models.Index(fields=["customer_type"], name="cust_type_idx"),
            models.Index(fields=["created_at"], name="cust_created_idx"),
            models.Index(fields=["updated_at"], name="cust_updated_idx"),
            # فهارس مركبة للبحث المتعدد
            models.Index(
                fields=["branch", "status", "customer_type"], name="cust_br_st_type_idx"
            ),
            models.Index(fields=["name", "phone", "email"], name="cust_search_idx"),
            models.Index(
                fields=["created_by", "branch"], name="cust_creator_branch_idx"
            ),
            # فهرس جزئي للعملاء النشطين
            models.Index(
                fields=["name", "phone"],
                name="cust_active_idx",
                condition=models.Q(status="active"),
            ),
        ]
        permissions = [
            ("view_customer_reports", _("Can view customer reports")),
            ("export_customer_data", _("Can export customer data")),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_customer_type_badge_html(self):
        """الحصول على HTML بادج نوع العميل"""
        from django.utils.safestring import mark_safe

        if self.customer_type:
            try:
                customer_type_obj = CustomerType.objects.get(code=self.customer_type)
                return customer_type_obj.get_badge_html()
            except CustomerType.DoesNotExist:
                pass
        # بادج افتراضي إذا لم يوجد نوع
        return mark_safe('<span class="badge bg-secondary">غير محدد</span>')

    def get_customer_type_display(self):
        """الحصول على اسم نوع العميل"""
        if self.customer_type:
            try:
                customer_type_obj = CustomerType.objects.get(code=self.customer_type)
                return customer_type_obj.name
            except CustomerType.DoesNotExist:
                pass
        return self.customer_type or "غير محدد"

    def clean(self):
        if self.created_by and not self.created_by.is_superuser:
            if self.branch != self.created_by.branch:
                raise ValidationError(_("لا يمكنك إضافة عملاء لفرع آخر"))
        # منع تكرار رقم الهاتف
        if self.phone:
            qs = Customer.objects.filter(phone=self.phone)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"phone": _("رقم الهاتف مستخدم بالفعل لعميل آخر")}
                )

    def save(self, *args, **kwargs):
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(
            self, ["phone", "phone2", "national_id", "tax_number"]
        )

        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def generate_unique_code(self):
        """توليد كود عميل فريد بشكل تسلسلي صحيح"""
        try:
            # الحصول على كود الفرع
            branch_code = self.branch.code if self.branch else "00"

            # استرجاع جميع الأكواد التي تبدأ بكود الفرع الحالي
            # نستخدم values_list لتقليل استهلاك الذاكرة
            existing_codes = Customer.objects.filter(
                code__startswith=f"{branch_code}-"
            ).values_list("code", flat=True)

            max_sequence = 0

            # البحث عن أكبر رقم تسلسلي صحيح
            for code in existing_codes:
                try:
                    # تقسيم الكود: BRANCH-SEQUENCENO
                    parts = code.split("-")
                    # نتأكد أن الكود يتكون من جزئين وأن الجزء الثاني رقمي بالكامل
                    if len(parts) >= 2:
                        sequence_part = parts[-1]
                        if sequence_part.isdigit():
                            sequence = int(sequence_part)
                            if sequence > max_sequence:
                                max_sequence = sequence
                except (IndexError, ValueError):
                    continue

            # الرقم التالي هو الأكبر + 1
            next_sequence = max_sequence + 1

            # محاولات للتأكد من عدم التكرار (حماية إضافية)
            # في حال وجود تضارب لحظي في إنشاء العملاء
            max_attempts = 100
            for _ in range(max_attempts):
                new_code = f"{branch_code}-{next_sequence:04d}"
                
                # التحقق إذا كان الكود موجوداً بالفعل
                # نستثني العميل الحالي في حالة التعديل (رغم أن هذا الكود يستخدم عند الإنشاء عادة)
                qs = Customer.objects.filter(code=new_code)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                
                if not qs.exists():
                    return new_code
                
                next_sequence += 1

            # في حالة نادرة جداً من الفشل المستمر (مثل سباق عالي جداً)، نلجأ لمؤقت زمني لضمان الفرادة
            # لكن نحافظ على الصيغة الرقمية قدر الإمكـان
            import time
            timestamp_seq = int(time.time() * 1000) % 1000000
            return f"{branch_code}-{timestamp_seq:06d}"

        except Exception:
            # Fallback آمن جداً
            import uuid
            return f"ERR-{str(uuid.uuid4())[:8]}"

    @property
    def branch_code(self):
        """Get the branch code part"""
        return self.code.split("-")[0] if self.code else ""

    @property
    def sequence_number(self):
        """Get the sequence number part"""
        return self.code.split("-")[1] if self.code else ""

    @classmethod
    def get_customer_types(cls):
        """Helper method to get customer types"""
        return get_customer_types()

    def get_customer_type_display(self):
        """عرض نوع العميل بالاسم المقروء"""
        if not self.customer_type:
            return "غير محدد"

        customer_types_dict = dict(get_customer_types())
        return customer_types_dict.get(self.customer_type, self.customer_type)

    def get_absolute_url(self):
        """الحصول على رابط تفاصيل العميل"""
        from django.urls import reverse

        return reverse(
            "customers:customer_detail_by_code", kwargs={"customer_code": self.code}
        )

    def requires_responsibles(self):
        """تحديد ما إذا كان نوع العميل يتطلب مسؤولين"""
        return self.customer_type in ["corporate", "government"]

    def get_primary_responsible(self):
        """الحصول على المسؤول الرئيسي"""
        return self.responsibles.filter(is_primary=True).first()

    def get_all_responsibles(self):
        """الحصول على جميع المسؤولين مرتبين"""
        return self.responsibles.all().order_by("order", "name")

    def get_discount_percentage(self):
        """الحصول على نسبة الخصم"""
        if self.discount_type:
            return self.discount_type.percentage
        return 0

    def has_discount(self):
        """تحديد ما إذا كان العميل له خصم"""
        return self.discount_type is not None and self.discount_type.is_active

    def delete(self, *args, **kwargs):
        """حذف العميل مع حذف السجلات المرتبطة بشكل آمن"""
        from django.db import connection, transaction
        from django.db.models.signals import post_delete

        from orders import signals as order_signals
        from orders.models import OrderItem

        # تعطيل signal حذف عناصر الطلب مؤقتاً
        post_delete.disconnect(order_signals.log_order_item_deletion, sender=OrderItem)

        try:
            with transaction.atomic():
                # حذف سجلات OrderStatusLog لجميع طلبات العميل
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM orders_orderstatuslog
                        WHERE order_id IN (
                            SELECT id FROM orders_order WHERE customer_id = %s
                        )
                    """,
                        [self.pk],
                    )

                # حذف العميل (سيتم حذف الطلبات تلقائياً بسبب CASCADE)
                super().delete(*args, **kwargs)
        finally:
            # إعادة تفعيل signal حذف عناصر الطلب
            post_delete.connect(order_signals.log_order_item_deletion, sender=OrderItem)
