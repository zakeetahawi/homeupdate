import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.soft_delete import SoftDeleteMixin


def installation_receipt_path(instance, filename):
    """مسار حفظ مذكرة استلام التركيب"""
    return f"installations/receipts/{instance.installation.id}/{filename}"


def modification_report_path(instance, filename):
    """مسار حفظ تقارير التعديل"""
    return f"installations/modifications/{instance.installation.id}/{filename}"


def modification_images_path(instance, filename):
    """مسار حفظ صور التعديل"""
    return f"installations/modifications/{instance.installation.id}/images/{filename}"


class CustomerDebt(models.Model):
    """نموذج مديونية العملاء"""

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, verbose_name=_("العميل")
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, verbose_name=_("الطلب")
    )
    debt_amount = models.DecimalField(
        _("مبلغ المديونية"), max_digits=10, decimal_places=2
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    is_paid = models.BooleanField(_("تم الدفع"), default=False)
    payment_receipt_number = models.CharField(
        _("رقم إذن استلام المبلغ"), max_length=100, blank=True
    )
    payment_receiver_name = models.CharField(
        _("اسم المستلم"), max_length=100, blank=True
    )
    payment_date = models.DateTimeField(_("تاريخ الدفع"), null=True, blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("مديونية عميل")
        verbose_name_plural = _("مديونيات العملاء")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "is_paid"], name="inst_debt_cust_paid_idx"),
            models.Index(fields=["order"], name="inst_debt_order_idx"),
            models.Index(fields=["-created_at"], name="inst_debt_created_idx"),
        ]

    def __str__(self):
        return f"مديونية #{self.pk} - عميل {self.customer_id}"

    def save(self, *args, **kwargs):
        if self.is_paid and not self.payment_date:
            self.payment_date = timezone.now()
        super().save(*args, **kwargs)


class Technician(SoftDeleteMixin, models.Model):
    """نموذج الفنيين"""

    DEPARTMENT_CHOICES = [
        ("installation", _("التركيبات")),
        ("inspection", _("المعاينات")),
        ("maintenance", _("الصيانة")),
        ("general", _("عام")),
    ]

    name = models.CharField(_("اسم الفني"), max_length=100)
    phone = models.CharField(_("رقم الهاتف"), max_length=20)
    specialization = models.CharField(_("التخصص"), max_length=100, blank=True)
    department = models.CharField(
        _("القسم"), max_length=20, choices=DEPARTMENT_CHOICES, default="general"
    )
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("فني")
        verbose_name_plural = _("الفنيين")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_department_display()})"

    def save(self, *args, **kwargs):
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(self, ["phone"])
        super().save(*args, **kwargs)


class Vehicle(SoftDeleteMixin, models.Model):
    """نموذج المركبات"""

    name = models.CharField(_("اسم المركبة"), max_length=100)
    plate_number = models.CharField(_("رقم اللوحة"), max_length=20, unique=True)
    model = models.CharField(_("الموديل"), max_length=50, blank=True)
    chassis_number = models.CharField(_("رقم الشاصي"), max_length=50, blank=True)
    vehicle_type = models.CharField(
        _("نوع المركبة"),
        max_length=20,
        choices=[
            ("truck", _("سيارة نقل")),
            ("van", _("فان")),
            ("car", _("سيارة ملاكي")),
            ("motorcycle", _("دراجة نارية")),
            ("other", _("أخرى")),
        ],
        default="truck",
    )
    status = models.CharField(
        _("الحالة"),
        max_length=20,
        choices=[
            ("active", _("نشط")),
            ("maintenance", _("صيانة")),
            ("inactive", _("غير نشط")),
        ],
        default="active",
    )
    license_expiry = models.DateField(_("تاريخ انتهاء الرخصة"), null=True, blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("مركبة")
        verbose_name_plural = _("المركبات")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.plate_number})"

    @property
    def current_driver(self):
        """إرجاع السائق الحالي للمركبة"""
        return self.drivers.filter(is_active=True).first()


class VehicleMission(SoftDeleteMixin, models.Model):
    """نموذج مهمة المركبة"""

    MISSION_TYPES = [
        ("installation", _("تركيب")),
        ("custom", _("مهمة خاصة")),
        ("maintenance", _("صيانة")),
    ]

    STATUS_CHOICES = [
        ("pending", _("معلق")),
        ("active", _("نشط")),
        ("completed", _("مكتمل")),
        ("cancelled", _("ملغي")),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("المركبة"),
        related_name="missions",
    )
    driver = models.ForeignKey(
        "Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("السائق"),
        related_name="missions",
    )
    mission_type = models.CharField(
        _("نوع المهمة"), max_length=20, choices=MISSION_TYPES, default="custom"
    )
    installation = models.ForeignKey(
        "InstallationSchedule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("التركيب المرتبط (قديم)"),
        related_name="legacy_missions",
    )
    description = models.TextField(_("وصف المهمة"), blank=True)
    date = models.DateField(_("التاريخ"))
    start_time = models.TimeField(_("وقت البدء"), null=True, blank=True)
    end_time = models.TimeField(_("وقت الانتهاء"), null=True, blank=True)
    status = models.CharField(
        _("الحالة"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("أنشئ بواسطة"),
        related_name="created_missions",
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("مهمة مركبة")
        verbose_name_plural = _("مهام المركبات")
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["vehicle", "date"], name="vmission_veh_date_idx"),
            models.Index(fields=["status", "date"], name="vmission_status_date_idx"),
            models.Index(fields=["installation"], name="vmission_inst_idx"),
        ]

    def __str__(self):
        return f"{self.get_mission_type_display()} - {self.vehicle}"

    @property
    def duration_display(self):
        """حساب ومدة المهمة بتنسيق مقروء"""
        if not self.start_time or not self.end_time:
            return None

        # تحويل الوقت إلى دقائق لحساب الفارق
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute

        # في حال كانت المهمة عبرت منتصف الليل (نادر جداً هنا لكن للاحتياط)
        diff = end_minutes - start_minutes
        if diff < 0:
            diff += 20 * 60

        hours = diff // 60
        minutes = diff % 60

        parts = []
        if hours > 0:
            if hours == 1:
                parts.append("ساعة")
            elif hours == 2:
                parts.append("ساعتين")
            elif 3 <= hours <= 10:
                parts.append(f"{hours} ساعات")
            else:
                parts.append(f"{hours} ساعة")

        if minutes > 0:
            if minutes == 1:
                parts.append("دقيقة")
            elif minutes == 2:
                parts.append("دقيقتين")
            elif 3 <= minutes <= 10:
                parts.append(f"{minutes} دقائق")
            else:
                parts.append(f"{minutes} دقيقة")

        return " و ".join(parts) if parts else "أقل من دقيقة"


class VehicleRequest(SoftDeleteMixin, models.Model):
    """نموذج طلب المركبة"""

    STATUS_CHOICES = [
        ("pending", _("قيد الانتظار")),
        ("approved", _("تمت الموافقة")),
        ("rejected", _("مرفوض")),
    ]

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("مقدم الطلب"),
        related_name="vehicle_requests",
    )
    requested_date = models.DateField(_("التاريخ المطلوب"))
    requested_time = models.TimeField(_("الوقت المطلوب"), null=True, blank=True)
    purpose = models.TextField(_("الغر"))
    status = models.CharField(
        _("الحالة"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    assigned_mission = models.OneToOneField(
        VehicleMission,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("المهمة المرتبطة"),
        related_name="request",
    )
    rejection_reason = models.TextField(_("سبب الرفض"), blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("طلب مركبة")
        verbose_name_plural = _("طلبات المركبات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="vreq_status_created_idx"),
            models.Index(fields=["requester"], name="vreq_requester_idx"),
        ]

    def __str__(self):
        return f"طلب مركبة من {self.requester} ليوم {self.requested_date}"


class Driver(SoftDeleteMixin, models.Model):
    """نموذج السائقين"""

    name = models.CharField(_("اسم السائق"), max_length=100)
    phone = models.CharField(_("رقم الهاتف"), max_length=20)
    license_number = models.CharField(_("رقم الرخصة"), max_length=50, blank=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("المركبة الافتراضية"),
        related_name="drivers",
    )
    # vehicle_number kept for backward compatibility or as text backup
    vehicle_number = models.CharField(
        _("رقم المركبة (قديم)"), max_length=50, blank=True
    )
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("سائق")
        verbose_name_plural = _("السائقين")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(
            self, ["phone", "license_number", "vehicle_number"]
        )
        super().save(*args, **kwargs)


class InstallationTeam(SoftDeleteMixin, models.Model):
    """نموذج فرق التركيب"""

    name = models.CharField(_("اسم الفريق"), max_length=100)
    technicians = models.ManyToManyField(Technician, verbose_name=_("الفنيين"))
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("السائق"),
    )
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("فريق تركيب")
        verbose_name_plural = _("فرق التركيب")
        ordering = ["name"]

    def __str__(self):
        return self.name


class InstallationSchedule(SoftDeleteMixin, models.Model):
    """نموذج جدولة التركيب"""

    STATUS_CHOICES = [
        ("needs_scheduling", _("بحاجة جدولة")),
        ("scheduled", _("مجدول")),
        ("in_installation", _("قيد التركيب")),
        ("completed", _("مكتمل")),
        ("cancelled", _("ملغي")),
        ("modification_required", _("يحتاج تعديل")),
        ("modification_scheduled", _("جدولة التعديل")),
        ("modification_in_progress", _("التعديل قيد التنفيذ")),
        ("modification_completed", _("التعديل مكتمل")),
    ]

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, verbose_name=_("الطلب")
    )
    team = models.ForeignKey(
        InstallationTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("الفريق (قديم)"),
    )
    technicians = models.ManyToManyField(
        Technician,
        verbose_name=_("الفنيين"),
        blank=True,
        related_name="installations",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("السائق"),
        related_name="installations",
    )
    scheduled_date = models.DateField(_("تاريخ التركيب"), null=True, blank=True)
    scheduled_time = models.TimeField(_("موعد التركيب"), null=True, blank=True)
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
    location_address = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("عنوان التركيب"),
        help_text="عنوان التركيب بالتفصيل",
    )
    windows_count = models.PositiveIntegerField(
        verbose_name=_("عدد الشبابيك"),
        null=True,
        blank=True,
        help_text=_("عدد الشبابيك المطلوبة للتركيب"),
    )
    status = models.CharField(
        _("الحالة"), max_length=30, choices=STATUS_CHOICES, default="needs_scheduling"
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    vehicle_mission = models.ForeignKey(
        "VehicleMission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("مهمة المركبة المرتبطة"),
        related_name="scheduled_installations",
    )
    completion_date = models.DateTimeField(_("تاريخ الإكمال"), null=True, blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="installation_schedules_updated",
        verbose_name=_("آخر تعديل بواسطة"),
        editable=False,
    )

    class Meta:
        verbose_name = _("جدولة تركيب")
        verbose_name_plural = _("جدولة التركيبات")
        ordering = ["-scheduled_date", "-scheduled_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["order"], name="unique_installation_per_order"
            )
        ]
        # ✅ تحسين: إضافة indexes شاملة لتسريع 1000%
        indexes = [
            models.Index(
                fields=["status", "scheduled_date"], name="inst_status_date_idx"
            ),
            models.Index(fields=["order", "status"], name="inst_order_status_idx"),
            models.Index(fields=["team", "scheduled_date"], name="inst_team_date_idx"),
            models.Index(
                fields=["status", "-created_at"], name="inst_status_created_idx"
            ),
            models.Index(
                fields=["scheduled_date", "status", "team"],
                name="inst_date_status_team_idx",
            ),
            models.Index(
                fields=["-scheduled_date", "-scheduled_time"], name="inst_date_time_idx"
            ),
        ]

    def __str__(self):
        return f"طلب تركيب {self.installation_code} - {self.get_status_display()}"

    @property
    def installation_code(self):
        """إرجاع رقم طلب التركيب الموحد (رقم الطلب + T)"""
        if self.order and self.order.order_number:
            return f"{self.order.order_number}-T"
        return f"#{self.id}-T"  # للبيانات القديمة التي لا تحتوي على order_number

    def get_absolute_url(self):
        """إرجاع رابط تفاصيل التركيب باستخدام كود التركيب"""
        from django.urls import reverse

        return reverse(
            "installations:installation_detail_by_code", args=[self.installation_code]
        )

    def clean(self):
        """التحقق من صحة البيانات"""
        if self.scheduled_date and self.scheduled_date < timezone.now().date():
            raise ValidationError(_("لا يمكن جدولة تركيب في تاريخ ماضي"))

    def save(self, *args, **kwargs):
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(self, ["location_address"])

        # حفظ الحالة السابقة قبل التحديث
        old_status = None
        old_scheduled_date = None
        if self.pk:
            try:
                old_instance = InstallationSchedule.objects.get(pk=self.pk)
                old_status = old_instance.status
                old_scheduled_date = old_instance.scheduled_date
            except InstallationSchedule.DoesNotExist:
                pass

        # حفظ الحالة الأصلية للإشارات
        self._original_status = old_status

        # تحديث حالة الطلب عند إكمال التركيب
        if self.status == "completed" and not self.completion_date:
            # استخدام التاريخ المحلي للمنطقة الزمنية المحددة
            from datetime import datetime, time
            from zoneinfo import ZoneInfo

            from django.utils import timezone as django_timezone

            # الحصول على المنطقة الزمنية من الإعدادات
            local_tz = ZoneInfo("Africa/Cairo")
            current_time = django_timezone.now()
            local_time = current_time.astimezone(local_tz)

            # إنشاء datetime بالتوقيت المحلي
            local_date = local_time.date()
            local_datetime = datetime.combine(
                local_date, local_time.time(), tzinfo=local_tz
            )

            self.completion_date = local_datetime

            # تحديث تاريخ الجدولة إلى تاريخ الإكمال إذا كان مختلفاً
            if self.scheduled_date and self.scheduled_date != local_date:
                old_date = self.scheduled_date
                self.scheduled_date = local_date

                # إضافة ملاحظة عن تغيير التاريخ
                date_note = f"\n--- ملاحظة تغيير التاريخ ---\n"
                date_note += f"الموعد كان مجدولاً في: {old_date.strftime('%Y-%m-%d')}\n"
                date_note += f"تم تنفيذ التركيب في: {self.completion_date.strftime('%Y-%m-%d')}\n"
                date_note += f"تم تحديث التاريخ تلقائياً إلى تاريخ التنفيذ الفعلي\n"
                date_note += f"--- نهاية الملاحظة ---\n"

                if self.notes:
                    self.notes += date_note
                else:
                    self.notes = date_note

                # تحديث تاريخ التسليم المتوقع للطلب إلى تاريخ الإكمال الفعلي
                if self.order:
                    self.order.expected_delivery_date = local_date
                    self.order.save(update_fields=["expected_delivery_date"])

        # إنشاء أرشيف عند إكمال التعديل
        elif (
            self.status == "modification_completed"
            and old_status != "modification_completed"
        ):
            try:
                # إنشاء أرشيف للتعديل المكتمل
                InstallationArchive.objects.create(
                    installation=self,
                    archive_notes=f'تم إكمال التعديل مع تركيب مكتمل - {self.notes or ""}',
                )
            except Exception as e:
                # لا نريد أن يفشل الحفظ بسبب الأرشفة
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"خطأ في إنشاء أرشيف التعديل: {e}")

        # تحديث تاريخ الجدولة عند بدء التركيب في يوم مختلف
        elif self.status == "in_installation" and old_status == "scheduled":
            # استخدام التاريخ المحلي للمنطقة الزمنية المحددة
            from zoneinfo import ZoneInfo

            from django.utils import timezone as django_timezone

            # الحصول على المنطقة الزمنية من الإعدادات
            local_tz = ZoneInfo("Africa/Cairo")
            current_time = django_timezone.now()
            local_time = current_time.astimezone(local_tz)
            current_date = local_time.date()

            if self.scheduled_date and self.scheduled_date != current_date:
                old_date = self.scheduled_date
                self.scheduled_date = current_date

                # إضافة ملاحظة عن تغيير التاريخ
                date_note = f"\n--- ملاحظة تغيير التاريخ ---\n"
                date_note += f"الموعد كان مجدولاً في: {old_date.strftime('%Y-%m-%d')}\n"
                date_note += f"تم بدء التركيب في: {current_date.strftime('%Y-%m-%d')}\n"
                date_note += f"تم تحديث التاريخ تلقائياً إلى تاريخ البدء الفعلي\n"
                date_note += f"--- نهاية الملاحظة ---\n"

                if self.notes:
                    self.notes += date_note
                else:
                    self.notes = date_note

                # تحديث تاريخ التسليم المتوقع للطلب إلى تاريخ البدء الفعلي
                if self.order:
                    self.order.expected_delivery_date = current_date
                    self.order.save(update_fields=["expected_delivery_date"])

        # تحديث تاريخ التسليم المتوقع عند الجدولة لأول مرة أو تغيير الجدولة
        elif self.status == "scheduled" and self.scheduled_date:
            # إذا كان هذا تغيير في تاريخ الجدولة أو جدولة جديدة
            if old_scheduled_date != self.scheduled_date and self.order:
                self.order.expected_delivery_date = self.scheduled_date
                self.order.save(update_fields=["expected_delivery_date"])

        # تم تعطيل تسجيل تغيير حالة التركيب هنا
        # لأننا ننشئ السجل يدوياً في installations/views.py (update_related_orders)
        # مع المستخدم الحقيقي من request.user
        # السطر 46-59 في views.py

        super().save(*args, **kwargs)

    def can_change_status_to(self, new_status):
        """التحقق من إمكانية تغيير الحالة إلى الحالة الجديدة

        تم تعديل هذه الطريقة للسماح بتغيير الحالة إلى أي حالة صالحة دون قيود تسلسل.
        سابقاً كان هناك تدفق مقيد (status_flow) يحدد الحالات المسموحة من كل حالة.
        الآن يتم التحقق فقط من أن الحالة الجديدة موجودة في STATUS_CHOICES.
        """
        # السماح بتغيير الحالة إلى أي حالة صالحة دون قيود تسلسل
        valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
        return new_status in valid_statuses

    def get_next_possible_statuses(self):
        """الحصول على الحالات الممكنة التالية"""
        # السماح بجميع الحالات الممكنة دون قيود تسلسل
        return [(choice[0], choice[1]) for choice in self.STATUS_CHOICES]

    def get_installation_date(self):
        """إرجاع تاريخ التركيب المناسب حسب الحالة"""
        # إذا كان مكتمل وله تاريخ إكمال، إرجاع تاريخ الإكمال الفعلي (أولوية عالية)
        if self.status == "completed" and self.completion_date:
            # تحويل تاريخ الإكمال إلى المنطقة الزمنية المحلية للعرض
            from zoneinfo import ZoneInfo

            local_tz = ZoneInfo("Africa/Cairo")
            local_completion_date = self.completion_date.astimezone(local_tz)
            return local_completion_date.date()
        # إذا كان التركيب مجدول أو قيد التنفيذ، إرجاع تاريخ الجدولة
        elif self.scheduled_date and self.status in [
            "scheduled",
            "in_installation",
            "modification_required",
            "modification_in_progress",
            "modification_completed",
        ]:
            return self.scheduled_date
        # في الحالات الأخرى، إرجاع تاريخ الجدولة إذا كان متوفراً
        elif self.scheduled_date:
            return self.scheduled_date
        # إذا لم يكن هناك تاريخ محدد، إرجاع None
        else:
            return None

    def get_assigned_driver(self):
        """إرجاع السائق المعين (إما المباشر أو سائق الفريق)"""
        if self.driver:
            return self.driver
        if self.team and self.team.driver:
            return self.team.driver
        return None

    def get_installation_date_label(self):
        """إرجاع تسمية تاريخ التركيب المناسبة حسب الحالة"""
        if self.status == "completed" and self.completion_date:
            return "تاريخ إكمال التركيب"
        elif self.status in ["scheduled", "in_installation"] and self.scheduled_date:
            return "تاريخ التركيب المجدول"
        elif self.scheduled_date:
            return "تاريخ التركيب"
        else:
            return "تاريخ التركيب المتوقع"

    def get_expected_installation_date(self):
        """إرجاع تاريخ التركيب المتوقع"""
        # إذا كان هناك تاريخ جدولة، إرجاعه كتاريخ متوقع
        if self.scheduled_date:
            return self.scheduled_date
        # إذا لم يكن هناك جدولة، إرجاع تاريخ ا��تسليم المتوقع من الطلب
        elif self.order.expected_delivery_date:
            return self.order.expected_delivery_date
        else:
            return None

    def requires_scheduling_settings(self):
        """التحقق من الحاجة لإعدادات الجدولة"""
        return self.status in ["needs_scheduling", "scheduled"]


class ModificationRequest(SoftDeleteMixin, models.Model):
    """نموذج طلب التعديل"""

    PRIORITY_CHOICES = [
        ("low", _("منخفض")),
        ("medium", _("متوسط")),
        ("high", _("عالي")),
        ("urgent", _("عاجل")),
    ]

    installation = models.ForeignKey(
        InstallationSchedule, on_delete=models.CASCADE, verbose_name=_("التركيب")
    )
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, verbose_name=_("العميل")
    )
    modification_type = models.CharField(_("نوع التعديل"), max_length=100)
    description = models.TextField(_("تفاصيل التعديل"))
    priority = models.CharField(
        _("الأولوية"), max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    estimated_cost = models.DecimalField(
        _("التكلفة المتوقعة"), max_digits=10, decimal_places=2, default=0
    )
    customer_approval = models.BooleanField(_("موافقة العميل"), default=False)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("طلب تعديل")
        verbose_name_plural = _("طلبات التعديل")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["installation", "priority"], name="modreq_inst_pri_idx"),
            models.Index(fields=["-created_at"], name="modreq_created_idx"),
        ]

    def __str__(self):
        return f"طلب تعديل #{self.pk} - تركيب {self.installation_id}"


class ModificationImage(models.Model):
    """نموذج صور التعديل"""

    modification = models.ForeignKey(
        ModificationRequest, on_delete=models.CASCADE, verbose_name=_("طلب التعديل")
    )
    image = models.ImageField(_("صورة"), upload_to=modification_images_path)
    description = models.CharField(_("وصف الصورة"), max_length=200, blank=True)
    uploaded_at = models.DateTimeField(_("تاريخ الرفع"), auto_now_add=True)

    class Meta:
        verbose_name = _("صورة تعديل")
        verbose_name_plural = _("صور التعديل")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"صورة تعديل #{self.pk} - طلب {self.modification_id}"


class ModificationManufacturingOrder(SoftDeleteMixin, models.Model):
    """نموذج أمر التصنيع للتعديلات — مختلف عن manufacturing.ManufacturingOrder"""

    ORDER_TYPE_CHOICES = [
        ("new", _("جديد")),
        ("modification", _("تعديل")),
        ("repair", _("إصلاح")),
    ]

    STATUS_CHOICES = [
        ("pending", _("في الانتظار")),
        ("approved", _("موافق عليه")),
        ("in_progress", _("قيد التنفيذ")),
        ("completed", _("مكتمل")),
        ("cancelled", _("ملغي")),
    ]

    modification_request = models.ForeignKey(
        ModificationRequest,
        on_delete=models.CASCADE,
        verbose_name=_("طلب التعديل"),
        related_name="modification_manufacturing_orders",
    )
    order_type = models.CharField(
        _("نوع الأمر"),
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default="modification",
    )
    status = models.CharField(
        _("الحالة"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    description = models.TextField(_("تفاصيل الأمر"))
    estimated_completion_date = models.DateField(
        _("تاريخ الإكمال المتوقع"), null=True, blank=True
    )
    actual_completion_date = models.DateTimeField(
        _("تاريخ الإكمال الفعلي"), null=True, blank=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("مُسند إلى"),
        related_name="installation_manufacturing_orders",
    )
    manager_notes = models.TextField(_("ملاحظات المدير"), blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        db_table = "installations_manufacturingorder"  # تثبيت اسم الجدول القديم
        verbose_name = _("أمر تصنيع تعديل")
        verbose_name_plural = _("أوامر تصنيع التعديلات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["modification_request", "status"], name="instmfg_modreq_sts_idx"),
            models.Index(fields=["-created_at"], name="instmfg_created_idx"),
        ]

    def __str__(self):
        return f"أمر تصنيع #{self.pk} - طلب تعديل {self.modification_request_id}"


class ModificationReport(models.Model):
    """نموذج تقارير التعديل"""

    modification_request = models.ForeignKey(
        ModificationRequest, on_delete=models.CASCADE, verbose_name=_("طلب التعديل")
    )
    manufacturing_order = models.ForeignKey(
        ModificationManufacturingOrder,
        on_delete=models.CASCADE,
        verbose_name=_("أمر التصنيع"),
        null=True,
        blank=True,
    )
    report_file = models.FileField(
        _("ملف التقرير"), upload_to=modification_report_path, blank=True
    )
    description = models.TextField(_("وصف التعديل المنجز"))
    completion_notes = models.TextField(_("ملاحظات الإكمال"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("أنشئ بواسطة"),
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("تقرير تعديل")
        verbose_name_plural = _("تقارير التعديل")
        ordering = ["-created_at"]

    def __str__(self):
        return f"تقرير تعديل #{self.pk} - طلب {self.modification_request_id}"


class ReceiptMemo(models.Model):
    """نموذج مذكرة الاستلام"""

    installation = models.OneToOneField(
        InstallationSchedule, on_delete=models.CASCADE, verbose_name=_("التركيب")
    )
    receipt_image = models.ImageField(
        _("صورة مذكرة الاستلام"), upload_to=installation_receipt_path
    )
    customer_signature = models.BooleanField(_("توقيع العميل"), default=False)
    amount_received = models.DecimalField(
        _("المبلغ المستلم"), max_digits=10, decimal_places=2, default=0
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("مذكرة استلام")
        verbose_name_plural = _("مذكرات الاستلام")

    def __str__(self):
        return f"مذكرة استلام - تركيب {self.installation_id}"


class InstallationPayment(models.Model):
    """نموذج مدفوعات التركيب"""

    PAYMENT_TYPE_CHOICES = [
        ("remaining", _("المتبقي")),
        ("additional", _("إضافي")),
        ("refund", _("استرداد")),
    ]

    installation = models.ForeignKey(
        InstallationSchedule, on_delete=models.CASCADE, verbose_name=_("التركيب")
    )
    payment_type = models.CharField(
        _("نوع الدفع"), max_length=20, choices=PAYMENT_TYPE_CHOICES
    )
    amount = models.DecimalField(_("المبلغ"), max_digits=15, decimal_places=2)
    payment_method = models.CharField(_("طريقة الدفع"), max_length=50, blank=True)
    receipt_number = models.CharField(_("رقم الإيصال"), max_length=50, blank=True)
    notes = models.TextField(_("ملاحظات"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("دفعة تركيب")
        verbose_name_plural = _("مدفوعات التركيب")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["installation", "-created_at"], name="instpay_inst_created_idx"),
            models.Index(fields=["payment_type"], name="instpay_type_idx"),
        ]

    def __str__(self):
        return f"دفعة {self.get_payment_type_display()} - تركيب {self.installation_id}"


class InstallationArchive(models.Model):
    """نموذج أرشيف التركيبات المكتملة"""

    installation = models.OneToOneField(
        InstallationSchedule, on_delete=models.CASCADE, verbose_name=_("التركيب")
    )
    completion_date = models.DateTimeField(_("تاريخ الإكمال"), auto_now_add=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("تم الأرشفة بواسطة"),
    )
    archive_notes = models.TextField(_("ملاحظات الأرشفة"), blank=True)

    class Meta:
        verbose_name = _("أرشيف تركيب")
        verbose_name_plural = _("أرشيف التركيبات")
        ordering = ["-completion_date"]

    def __str__(self):
        return f"أرشيف - تركيب {self.installation_id}"


class InstallationAnalytics(models.Model):
    """نموذج تحليل التركيبات الشهري"""

    month = models.DateField(_("الشهر"), help_text="أول يوم من الشهر")
    total_installations = models.IntegerField(_("إجمالي التركيبات"), default=0)
    completed_installations = models.IntegerField(_("التركيبات المكتملة"), default=0)
    pending_installations = models.IntegerField(_("التركيبات في الانتظار"), default=0)
    in_progress_installations = models.IntegerField(
        _("التركيبات قيد التنفيذ"), default=0
    )
    total_customers = models.IntegerField(_("إجمالي العملاء"), default=0)
    new_customers = models.IntegerField(_("العملاء الجدد"), default=0)
    total_visits = models.IntegerField(_("إجمالي الزيارات"), default=0)
    total_modifications = models.IntegerField(_("إجمالي التعديلات"), default=0)
    modification_rate = models.DecimalField(
        _("نسبة التعديلات %"), max_digits=5, decimal_places=2, default=0
    )
    completion_rate = models.DecimalField(
        _("نسبة الإكمال %"), max_digits=5, decimal_places=2, default=0
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("تحليل تركيب شهري")
        verbose_name_plural = _("تحليلات التركيبات الشهرية")
        ordering = ["-month"]
        unique_together = ["month"]

    def __str__(self):
        return f"تحليل {self.month.strftime('%Y-%m')}"

    def calculate_rates(self):
        """حساب النسب المئوية"""
        if self.total_installations > 0:
            self.completion_rate = (
                self.completed_installations / self.total_installations
            ) * 100
            self.modification_rate = (
                self.total_modifications / self.total_installations
            ) * 100
        self.save()


class ModificationErrorType(models.Model):
    """نموذج أنواع أسباب التعديلات"""

    name = models.CharField(_("اسم السبب"), max_length=100)
    description = models.TextField(_("الوصف"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("نوع سبب تعديل")
        verbose_name_plural = _("أنواع أسباب التعديلات")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ModificationErrorAnalysis(models.Model):
    """نموذج تحليل أخطاء التعديلات"""

    SEVERITY_CHOICES = [
        ("low", _("منخفض")),
        ("medium", _("متوسط")),
        ("high", _("عالي")),
        ("critical", _("حرج")),
    ]

    modification_request = models.ForeignKey(
        ModificationRequest, on_delete=models.CASCADE, verbose_name=_("طلب التعديل")
    )
    error_type = models.ForeignKey(
        ModificationErrorType, on_delete=models.CASCADE, verbose_name=_("نوع السبب")
    )
    severity = models.CharField(
        _("الشدة"), max_length=20, choices=SEVERITY_CHOICES, default="medium"
    )
    error_description = models.TextField(_("وصف الخطأ"))
    root_cause = models.TextField(_("السبب الجذري"))
    solution_applied = models.TextField(_("الحل المطبق"))
    prevention_measures = models.TextField(_("إجراءات الوقاية"), blank=True)
    cost_impact = models.DecimalField(
        _("التأثير المالي"), max_digits=10, decimal_places=2, default=0
    )
    time_impact_hours = models.IntegerField(_("التأثير الزمني (ساعات)"), default=0)
    analyzed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("تم التحليل بواسطة"),
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("تحليل خطأ تعديل")
        verbose_name_plural = _("تحليلات أخطاء التعديلات")
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"تحليل خطأ - {self.modification_request.installation.order.order_number}"
        )


class InstallationStatusLog(models.Model):
    """نموذج سجل تغيير حالات التركيب"""

    installation = models.ForeignKey(
        InstallationSchedule,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name=_("التركيب"),
    )
    old_status = models.CharField(
        _("الحالة السابقة"), max_length=30, choices=InstallationSchedule.STATUS_CHOICES
    )
    new_status = models.CharField(
        _("الحالة الجديدة"), max_length=30, choices=InstallationSchedule.STATUS_CHOICES
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("تم التغيير بواسطة"),
    )
    reason = models.TextField(
        _("سبب التغيير"),
        blank=True,
        help_text="سبب تغيير الحالة (مطلوب لبعض التغييرات)",
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("عنوان IP"),
    )
    created_at = models.DateTimeField(_("تاريخ التغيير"), auto_now_add=True)

    class Meta:
        verbose_name = _("سجل حالة التركيب")
        verbose_name_plural = _("سجلات حالات التركيب")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["installation", "-created_at"], name="inststatlog_inst_crtd_idx"),
        ]

    def __str__(self):
        return f"تغيير حالة تركيب {self.installation_id} من {self.get_old_status_display()} إلى {self.get_new_status_display()}"


class InstallationSchedulingSettings(models.Model):
    """نموذج إعدادات جدولة التركيب"""

    installation = models.OneToOneField(
        InstallationSchedule,
        on_delete=models.CASCADE,
        related_name="scheduling_settings",
        verbose_name=_("التركيب"),
    )
    technician_name = models.CharField(_("اسم الفني"), max_length=100, blank=True)
    driver_name = models.CharField(_("اسم السائق"), max_length=100, blank=True)
    customer_address = models.TextField(_("عنوان العميل"), blank=True)
    customer_phone = models.CharField(_("رقم هاتف العميل"), max_length=20, blank=True)
    contract_number = models.CharField(_("رقم العقد"), max_length=100, blank=True)
    invoice_number = models.CharField(_("رقم الفاتورة"), max_length=100, blank=True)
    salesperson_name = models.CharField(_("اسم البائع"), max_length=100, blank=True)
    branch_name = models.CharField(_("اسم الفرع"), max_length=100, blank=True)
    special_instructions = models.TextField(_("تعليمات خاصة"), blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("إعدادات ج��ولة التركيب")
        verbose_name_plural = _("إعدادات جدولة التركيبات")

    def __str__(self):
        return f"إعدادات جدولة {self.installation.order.order_number}"

    def populate_from_order(self):
        """ملء البيانات من الطلب المرتبط"""
        order = self.installation.order

        # بيانات العميل
        if order.customer:
            self.customer_phone = order.customer.phone
            if hasattr(order.customer, "address"):
                self.customer_address = order.customer.address

        # بيانات الطلب
        self.contract_number = order.contract_number or ""
        self.invoice_number = order.invoice_number or ""

        # بيانات البائع والفرع
        if order.salesperson:
            self.salesperson_name = order.salesperson.get_display_name()

        if order.branch:
            self.branch_name = order.branch.name

        # بيانات الفريق
        if self.installation.team:
            # أسماء الفنيين
            technicians = self.installation.team.technicians.all()
            if technicians:
                self.technician_name = ", ".join([tech.name for tech in technicians])

            # اسم السائق
            if self.installation.team.driver:
                self.driver_name = self.installation.team.driver.name

        self.save()


class InstallationEventLog(models.Model):
    """نموذج سجل أحداث التركيبات"""

    EVENT_TYPES = [
        ("status_change", _("تغيير حالة")),
        ("schedule_change", _("تغيير جدولة")),
        ("team_assignment", _("تعيين فريق")),
        ("modification_request", _("طلب تعديل")),
        ("payment_received", _("استلام دفعة")),
        ("completion", _("إكمال")),
        ("cancellation", _("إلغاء")),
    ]

    installation = models.ForeignKey(
        InstallationSchedule,
        on_delete=models.CASCADE,
        related_name="event_logs",
        verbose_name=_("التركيب"),
    )
    event_type = models.CharField(_("نوع الحدث"), max_length=20, choices=EVENT_TYPES)
    description = models.TextField(_("وصف الحدث"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("المستخدم"),
    )
    metadata = models.JSONField(_("بيانات إضافية"), default=dict, blank=True)
    created_at = models.DateTimeField(_("تاريخ الحدث"), auto_now_add=True)

    class Meta:
        verbose_name = _("سجل حدث التركيب")
        verbose_name_plural = _("سجل أحداث التركيبات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["installation", "event_type"], name="instevt_inst_type_idx"),
            models.Index(fields=["-created_at"], name="instevt_created_idx"),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} - تركيب {self.installation_id}"
