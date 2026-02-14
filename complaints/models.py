from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models import Avg, DurationField, ExpressionWrapper, F, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class ComplaintType(models.Model):
    """نوع الشكوى مع إعدادات تلقائية"""

    PRIORITY_CHOICES = [
        ("low", "منخفضة"),
        ("medium", "متوسطة"),
        ("high", "عالية"),
        ("urgent", "عاجلة"),
    ]

    name = models.CharField(max_length=100, verbose_name="نوع الشكوى", unique=True)
    description = models.TextField(blank=True, verbose_name="وصف النوع")
    default_priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="الأولوية الافتراضية",
    )
    default_deadline_hours = models.PositiveIntegerField(
        default=72,
        verbose_name="المهلة الافتراضية (بالساعات)",
        help_text="المهلة الزمنية المحددة تلقائياً لحل الشكوى",
        validators=[MinValueValidator(1), MaxValueValidator(720)],  # max 30 days
    )
    business_hours_start = models.TimeField(
        default="09:00", verbose_name="بداية ساعات العمل"
    )
    business_hours_end = models.TimeField(
        default="17:00", verbose_name="نهاية ساعات العمل"
    )
    working_days = models.CharField(
        max_length=20,
        default="1,2,3,4,5",  # Sunday to Thursday
        verbose_name="أيام العمل",
        help_text="أرقام أيام العمل (1=الأحد، 7=السبت) مفصولة بفواصل",
    )
    responsible_department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="القسم المسؤول",
        help_text="القسم المحول إليه تلقائياً",
    )
    default_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المسؤول الافتراضي",
        help_text="الموظف المسؤول عن المتابعة",
    )
    responsible_staff = models.ManyToManyField(
        User,
        blank=True,
        related_name="responsible_complaint_types",
        verbose_name="الموظفون المسؤولون",
        help_text="الموظفون المسؤولون عن هذا النوع من الشكاوى",
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "نوع شكوى"
        verbose_name_plural = "أنواع الشكاوى"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Complaint(models.Model):
    """نموذج الشكوى الرئيسي"""

    STATUS_CHOICES = [
        ("new", "جديدة"),
        ("in_progress", "قيد الحل"),
        ("resolved", "محلولة"),
        ("pending_evaluation", "بحاجة تقييم"),
        ("closed", "مغلقة"),
        ("overdue", "متأخرة"),
        ("escalated", "مصعدة"),
    ]

    PRIORITY_CHOICES = [
        ("low", "منخفضة"),
        ("medium", "متوسطة"),
        ("high", "عالية"),
        ("urgent", "عاجلة"),
    ]

    RATING_CHOICES = [
        (1, "غير راضي جداً"),
        (2, "غير راضي"),
        (3, "محايد"),
        (4, "راضي"),
        (5, "راضي جداً"),
    ]

    # معلومات أساسية
    complaint_number = models.CharField(
        max_length=50, unique=True, verbose_name="رقم الشكوى", editable=False
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="complaints",
        verbose_name="العميل",
    )
    complaint_type = models.ForeignKey(
        ComplaintType, on_delete=models.CASCADE, verbose_name="نوع الشكوى"
    )
    title = models.CharField(max_length=200, verbose_name="موضوع الشكوى")
    description = models.TextField(verbose_name="وصف الشكوى")

    # الطلب المرتبط
    related_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
        verbose_name="الطلب المرتبط",
    )

    # الأنظمة المرتبطة - Generic Relations
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="نوع المحتوى المرتبط",
    )
    object_id = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="معرف الكائن المرتبط"
    )
    related_object = GenericForeignKey("content_type", "object_id")

    # حالة ومعلومات الشكوى
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="new", verbose_name="حالة الشكوى"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="الأولوية",
    )

    # التوقيتات
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التقديم")
    deadline = models.DateTimeField(verbose_name="الموعد النهائي للحل")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    closed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ الإغلاق"
    )

    # المسؤوليات
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
        verbose_name="إسناد إلى",
    )
    assigned_department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="القسم المحول إليه",
    )

    # معلومات الإنشاء
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_complaints",
        verbose_name="تم الإنشاء بواسطة",
    )
    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="الفرع",
    )

    # تقييم العميل
    customer_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="تقييم العميل",
    )
    customer_feedback = models.TextField(
        blank=True, verbose_name="تعليق العميل على الحل"
    )

    # طريقة الحل
    resolution_method = models.ForeignKey(
        "ResolutionMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="طريقة الحل",
    )

    # ملاحظات إضافية
    internal_notes = models.TextField(blank=True, verbose_name="ملاحظات داخلية")

    # تتبع التحديثات
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    last_activity_at = models.DateTimeField(auto_now=True, verbose_name="آخر نشاط")

    class Meta:
        verbose_name = "شكوى"
        verbose_name_plural = "الشكاوى"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["complaint_number"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["deadline"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        # إنشاء رقم الشكوى تلقائياً
        if not self.complaint_number:
            self.complaint_number = self.generate_complaint_number()

        # تحديد الموعد النهائي إذا لم يكن محدداً
        if not self.deadline and self.complaint_type:
            # حساب الموعد النهائي مع مراعاة ساعات العمل
            deadline = self.calculate_business_hours_deadline(
                timezone.now(),
                self.complaint_type.default_deadline_hours,
                self.complaint_type.business_hours_start,
                self.complaint_type.business_hours_end,
                [int(d) for d in self.complaint_type.working_days.split(",")],
            )
            self.deadline = deadline

        # تحديد القسم والمسؤول تلقائياً من نوع الشكوى
        if self.complaint_type:
            if (
                not self.assigned_department
                and self.complaint_type.responsible_department
            ):
                self.assigned_department = self.complaint_type.responsible_department
            # جعل منشئ الشكوى هو المسؤول الافتراضي
            if not self.assigned_to:
                if self.created_by:
                    self.assigned_to = self.created_by
                elif self.complaint_type.default_assignee:
                    self.assigned_to = self.complaint_type.default_assignee
            if not self.priority:
                self.priority = self.complaint_type.default_priority

        # تحديث حالة الشكوى إذا تجاوزت الموعد النهائي
        if (
            self.deadline
            and timezone.now() > self.deadline
            and self.status in ["new", "in_progress"]
        ):
            self.status = "overdue"

        # تحديد تاريخ الحل
        if self.status in ["resolved", "pending_evaluation"] and not self.resolved_at:
            self.resolved_at = timezone.now()

        # تحديد تاريخ الإغلاق
        if self.status == "closed" and not self.closed_at:
            self.closed_at = timezone.now()

        # فحص تجاوز SLA وتصعيد تلقائي
        if self.pk and hasattr(self.complaint_type, "sla"):
            sla = self.complaint_type.sla
            current_time = timezone.now()

            # تصعيد تلقائي عند تجاوز وقت الحل
            if not self.resolved_at and current_time > self.deadline + timedelta(
                hours=sla.escalation_time_hours
            ):
                self.status = "escalated"

                # إنشاء سجل تصعيد
                ComplaintEscalation.objects.create(
                    complaint=self,
                    reason="overdue",
                    description="تصعيد تلقائي لتجاوز وقت الحل",
                    escalated_from=self.assigned_to,
                    escalated_to=(
                        self.assigned_department.manager
                        if self.assigned_department
                        else None
                    ),
                    escalated_by=None,  # تصعيد تلقائي
                )

        super().save(*args, **kwargs)

    def calculate_business_hours_deadline(
        self, start_time, hours, start_hour, end_hour, working_days
    ):
        """حساب الموعد النهائي مع مراعاة ساعات وأيام العمل"""
        current = start_time
        remaining_hours = hours

        while remaining_hours > 0:
            # تخطي أيام العطل
            while current.isoweekday() not in working_days:
                current += timedelta(days=1)
                current = current.replace(
                    hour=start_hour.hour, minute=start_hour.minute
                )

            # حساب ساعات العمل المتبقية في اليوم الحالي
            day_end = current.replace(hour=end_hour.hour, minute=end_hour.minute)
            if current.time() < start_hour:
                current = current.replace(
                    hour=start_hour.hour, minute=start_hour.minute
                )

            working_hours = (day_end - current).seconds / 3600
            if working_hours > remaining_hours:
                current += timedelta(hours=remaining_hours)
                remaining_hours = 0
            else:
                remaining_hours -= working_hours
                current = (current + timedelta(days=1)).replace(
                    hour=start_hour.hour, minute=start_hour.minute
                )

        return current

    def generate_complaint_number(self):
        """توليد رقم شكوى فريد بناءً على كود العميل مسبوقاً بحرف P"""
        try:
            # الحصول على كود العميل
            customer_code = (
                self.customer.code
                if self.customer and self.customer.code
                else "UNKNOWN"
            )

            # البحث عن آخر رقم شكوى لهذا العميل
            last_complaint = (
                Complaint.objects.filter(
                    customer=self.customer,
                    complaint_number__startswith=f"P{customer_code}",
                )
                .exclude(pk=self.pk)
                .order_by("-complaint_number")
                .first()
            )

            if last_complaint:
                try:
                    # استخراج الرقم التسلسلي من آخر شكوى
                    # مثال: P01-0001-001 -> 001
                    last_num = int(last_complaint.complaint_number.split("-")[-1])
                    next_num = last_num + 1
                except (IndexError, ValueError):
                    next_num = 1
            else:
                next_num = 1

            # التأكد من عدم تكرار رقم الشكوى
            max_attempts = 100
            for attempt in range(max_attempts):
                potential_complaint_number = f"P{customer_code}-{next_num:03d}"

                # التحقق من عدم وجود رقم مكرر (باستثناء الشكوى الحالية)
                if (
                    not Complaint.objects.filter(
                        complaint_number=potential_complaint_number
                    )
                    .exclude(pk=self.pk)
                    .exists()
                ):
                    return potential_complaint_number

                next_num += 1

            # إذا فشل في العثور على رقم فريد، استخدم UUID
            import uuid

            return f"P{customer_code}-{str(uuid.uuid4())[:6].upper()}"

        except Exception as e:
            print(f"Error generating complaint number: {e}")
            # استخدام طريقة احتياطية في حالة حدوث خطأ
            import uuid
            from datetime import datetime

            year = datetime.now().year
            month = datetime.now().month
            return f"P-{year}{month:02d}-{uuid.uuid4().hex[:6].upper()}"

    def __str__(self):
        return f"{self.complaint_number} - {self.customer.name}"

    def get_absolute_url(self):
        return reverse("complaints:complaint_detail", kwargs={"pk": self.pk})

    @property
    def is_overdue(self):
        """التحقق من تجاوز الموعد النهائي"""
        if self.status in ["resolved", "pending_evaluation", "closed"]:
            return False
        return timezone.now() > self.deadline

    @property
    def needs_evaluation(self):
        """هل الشكوى بحاجة تقييم؟"""
        return self.status == "pending_evaluation"

    @property
    def is_evaluated(self):
        """هل تم تقييم الشكوى؟"""
        return hasattr(self, "evaluation") and self.evaluation is not None

    @property
    def can_be_closed(self):
        """هل يمكن إغلاق الشكوى؟"""
        return self.status == "pending_evaluation" and self.is_evaluated

    def can_be_closed_by_user(self, user):
        """هل يمكن للمستخدم إغلاق الشكوى؟"""
        # فقط منشئ الشكوى يمكنه إغلاقها
        if self.created_by == user:
            return True

        # المدراء والمشرفين يمكنهم إغلاق أي شكوى
        if (
            user.is_superuser
            or user.groups.filter(
                name__in=["Managers", "Complaints_Supervisors"]
            ).exists()
        ):
            return True

        return False

    @property
    def is_fully_completed(self):
        """هل الشكوى منتهية تماماً؟"""
        return self.status == "closed" and self.is_evaluated

    @property
    def time_remaining(self):
        """الوقت المتبقي للحل"""
        if self.status in ["resolved", "closed"]:
            return None
        remaining = self.deadline - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    @property
    def resolution_time(self):
        """وقت الحل الفعلي"""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None

    def get_status_badge_class(self):
        """لون الشارة حسب الحالة"""
        status_classes = {
            "new": "bg-primary",
            "in_progress": "bg-warning",
            "resolved": "bg-success",
            "closed": "bg-secondary",
            "overdue": "bg-danger",
            "escalated": "bg-dark",
        }
        return status_classes.get(self.status, "bg-secondary")

    def get_priority_badge_class(self):
        """لون الشارة حسب الأولوية"""
        priority_classes = {
            "low": "bg-info",
            "medium": "bg-warning",
            "high": "bg-danger",
            "urgent": "bg-dark",
        }
        return priority_classes.get(self.priority, "bg-secondary")


class ComplaintUpdate(models.Model):
    """سجل التحديثات والإجراءات على الشكوى"""

    MAX_TITLE_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 5000

    class Meta:
        verbose_name = "تحديث شكوى"
        verbose_name_plural = "تحديثات الشكاوى"
        ordering = ["-created_at"]

    UPDATE_TYPES = [
        ("status_change", "تغيير الحالة"),
        ("assignment", "تعيين مسؤول"),
        ("comment", "تعليق"),
        ("note", "ملاحظة"),
        ("escalation", "تصعيد"),
        ("resolution", "حل"),
        ("customer_response", "رد العميل"),
        ("internal_note", "ملاحظة داخلية"),
    ]

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="updates",
        verbose_name="الشكوى",
    )
    update_type = models.CharField(
        max_length=20, choices=UPDATE_TYPES, verbose_name="نوع التحديث"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان التحديث")
    description = models.TextField(
        verbose_name="الوصف", validators=[MaxLengthValidator(MAX_DESCRIPTION_LENGTH)]
    )

    def clean(self):
        """التحقق من صحة البيانات"""
        if len(self.title) > self.MAX_TITLE_LENGTH:
            raise ValidationError(
                {
                    "title": f"عنوان التحديث لا يمكن أن يتجاوز {self.MAX_TITLE_LENGTH} حرف"
                }
            )

        if len(self.description) > self.MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                {
                    "description": f"وصف التحديث لا يمكن أن يتجاوز {self.MAX_DESCRIPTION_LENGTH} حرف"
                }
            )

        # التحقق من تغيير الحالة
        if self.update_type == "status_change":
            if not self.old_status or not self.new_status:
                raise ValidationError(
                    "يجب تحديد الحالة القديمة والجديدة عند تغيير الحالة"
                )

        # التحقق من تغيير المسؤول
        if self.update_type == "assignment":
            if not self.new_assignee:
                raise ValidationError("يجب تحديد المسؤول الجديد عند تغيير التعيين")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, verbose_name="تم الإنشاء بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التحديث")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="عنوان IP"
    )
    is_visible_to_customer = models.BooleanField(
        default=True, verbose_name="مرئي للعميل"
    )

    # للتحديثات التي تغير الحالة
    old_status = models.CharField(
        max_length=20, blank=True, verbose_name="الحالة السابقة"
    )
    new_status = models.CharField(
        max_length=20, blank=True, verbose_name="الحالة الجديدة"
    )

    # للتحديثات التي تغير المسؤول
    old_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="old_assignments",
        verbose_name="المسؤول السابق",
    )
    new_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_assignments",
        verbose_name="المسؤول الجديد",
    )

    # طريقة الحل (للتحديثات من نوع resolution)
    resolution_method = models.ForeignKey(
        "ResolutionMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="طريقة الحل",
    )

    class Meta:
        verbose_name = "تحديث شكوى"
        verbose_name_plural = "تحديثات الشكاوى"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.get_update_type_display()}"


class ComplaintAttachment(models.Model):
    """مرفقات الشكوى"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = ["pdf", "doc", "docx", "jpg", "jpeg", "png", "xls", "xlsx"]

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="الشكوى",
    )
    file = models.FileField(
        upload_to="complaints/attachments/%Y/%m/%d/",
        verbose_name="الملف",
        help_text="الحد الأقصى للحجم: 10 ميجابايت. الصيغ المسموحة: PDF, DOC, DOCX, JPG, PNG, XLS, XLSX",
    )
    filename = models.CharField(max_length=255, verbose_name="اسم الملف")
    description = models.CharField(max_length=500, blank=True, verbose_name="وصف الملف")
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, verbose_name="رفع بواسطة"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")
    file_size = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="حجم الملف (بايت)"
    )

    class Meta:
        verbose_name = "مرفق شكوى"
        verbose_name_plural = "مرفقات الشكاوى"
        ordering = ["-uploaded_at"]

    def clean(self):
        if self.file:
            # التحقق من حجم الملف
            if self.file.size > self.MAX_FILE_SIZE:
                raise ValidationError(
                    f"حجم الملف يتجاوز الحد المسموح به ({self.MAX_FILE_SIZE/1024/1024:.1f} ميجابايت)"
                )

            # التحقق من امتداد الملف
            ext = self.file.name.split(".")[-1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                raise ValidationError(
                    f'نوع الملف غير مسموح به. الأنواع المسموحة: {", ".join(self.ALLOWED_EXTENSIONS)}'
                )

            self.filename = self.file.name
            self.file_size = self.file.size

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.filename}"


class ComplaintEscalation(models.Model):
    """تصعيد الشكاوى"""

    ESCALATION_REASONS = [
        ("overdue", "تجاوز الموعد النهائي"),
        ("high_priority", "أولوية عالية"),
        ("customer_request", "طلب العميل"),
        ("complex_issue", "مشكلة معقدة"),
        ("department_change", "تغيير القسم"),
        ("unsatisfactory_response", "استجابة غير مرضية"),
    ]

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="escalations",
        verbose_name="الشكوى",
    )
    reason = models.CharField(
        max_length=30, choices=ESCALATION_REASONS, verbose_name="سبب التصعيد"
    )
    description = models.TextField(verbose_name="وصف التصعيد")
    escalated_from = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="escalated_from_complaints",
        verbose_name="المصعد من",
    )
    escalated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="escalated_to_complaints",
        verbose_name="المصعد إلى",
    )
    escalated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="escalation_actions",
        verbose_name="تم التصعيد بواسطة",
    )
    escalated_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التصعيد")
    resolved_at = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ حل التصعيد"
    )
    resolution_notes = models.TextField(blank=True, verbose_name="ملاحظات الحل")

    class Meta:
        verbose_name = "تصعيد شكوى"
        verbose_name_plural = "تصعيدات الشكاوى"
        ordering = ["-escalated_at"]

    def __str__(self):
        return f"{self.complaint.complaint_number} - {self.get_reason_display()}"


class ComplaintSLA(models.Model):
    """اتفاقية مستوى الخدمة للشكاوى"""

    BREACH_LEVELS = [("warning", "تحذير"), ("critical", "حرج"), ("breach", "خرق")]
    complaint_type = models.OneToOneField(
        ComplaintType,
        on_delete=models.CASCADE,
        related_name="sla",
        verbose_name="نوع الشكوى",
    )
    response_time_hours = models.PositiveIntegerField(
        default=4, verbose_name="وقت الاستجابة (ساعات)"
    )
    resolution_time_hours = models.PositiveIntegerField(
        default=72, verbose_name="وقت الحل (ساعات)"
    )
    # أوقات الاستجابة والحل
    response_time_hours = models.PositiveIntegerField(
        default=4,
        verbose_name="وقت الاستجابة (ساعات)",
        validators=[MinValueValidator(1), MaxValueValidator(24)],
    )
    resolution_time_hours = models.PositiveIntegerField(
        default=72,
        verbose_name="وقت الحل (ساعات)",
        validators=[MinValueValidator(1), MaxValueValidator(720)],
    )
    escalation_time_hours = models.PositiveIntegerField(
        default=48,
        verbose_name="وقت التصعيد (ساعات)",
        validators=[MinValueValidator(1), MaxValueValidator(168)],
    )

    # مستويات التصعيد
    warning_threshold = models.PositiveIntegerField(
        default=70,
        verbose_name="نسبة التحذير (%)",
        help_text="النسبة المئوية من وقت الحل للتحذير",
        validators=[MinValueValidator(50), MaxValueValidator(90)],
    )
    critical_threshold = models.PositiveIntegerField(
        default=90,
        verbose_name="نسبة الحرج (%)",
        help_text="النسبة المئوية من وقت الحل للحالة الحرجة",
        validators=[MinValueValidator(80), MaxValueValidator(99)],
    )
    target_satisfaction_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=90.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="معدل الرضا المستهدف (%)",
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "اتفاقية مستوى خدمة"
        verbose_name_plural = "اتفاقيات مستوى الخدمة"

    def __str__(self):
        return f"SLA - {self.complaint_type.name}"

    def check_breach_level(self, complaint):
        """التحقق من مستوى خرق SLA"""
        if complaint.status in ["resolved", "closed"]:
            return None

        elapsed_time = timezone.now() - complaint.created_at
        elapsed_hours = elapsed_time.total_seconds() / 3600
        resolution_hours = self.resolution_time_hours

        if elapsed_hours >= resolution_hours:
            return "breach"
        elif elapsed_hours >= (resolution_hours * self.critical_threshold / 100):
            return "critical"
        elif elapsed_hours >= (resolution_hours * self.warning_threshold / 100):
            return "warning"
        return None

    def get_performance_metrics(self, start_date=None, end_date=None):
        """حساب مؤشرات الأداء"""
        complaints = Complaint.objects.filter(complaint_type=self.complaint_type)

        if start_date:
            complaints = complaints.filter(created_at__gte=start_date)
        if end_date:
            complaints = complaints.filter(created_at__lte=end_date)

        total = complaints.count()
        if total == 0:
            return {
                "resolution_rate": 0,
                "satisfaction_rate": 0,
                "avg_resolution_time": 0,
                "breaches": 0,
                "warning_count": 0,
                "critical_count": 0,
            }

        resolved = complaints.filter(status="resolved").count()
        satisfied = complaints.filter(customer_rating__gte=4).count()
        breaches = complaints.filter(
            Q(status="resolved") & Q(resolved_at__gt=F("deadline"))
        ).count()

        # حساب عدد التحذيرات والحالات الحرجة
        warning_count = 0
        critical_count = 0
        for complaint in complaints:
            breach_level = self.check_breach_level(complaint)
            if breach_level == "warning":
                warning_count += 1
            elif breach_level == "critical":
                critical_count += 1

        resolution_times = complaints.filter(status="resolved").annotate(
            resolution_time=ExpressionWrapper(
                F("resolved_at") - F("created_at"), output_field=DurationField()
            )
        )

        avg_resolution_time = resolution_times.aggregate(avg=Avg("resolution_time"))[
            "avg"
        ]

        return {
            "resolution_rate": (resolved / total) * 100,
            "satisfaction_rate": (satisfied / total) * 100,
            "avg_resolution_time": (
                avg_resolution_time.total_seconds() / 3600 if avg_resolution_time else 0
            ),
            "breaches": breaches,
            "warning_count": warning_count,
            "critical_count": critical_count,
        }


class ComplaintNotification(models.Model):
    """إشعارات نظام الشكاوى"""

    NOTIFICATION_TYPES = [
        ("new_complaint", "شكوى جديدة"),
        ("status_change", "تغيير الحالة"),
        ("assignment", "تعيين مسؤول"),
        ("comment", "تعليق جديد"),
        ("deadline", "اقتراب الموعد النهائي"),
        ("overdue", "تجاوز الموعد النهائي"),
        ("escalation", "تصعيد"),
        ("resolution", "حل الشكوى"),
    ]

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="الشكوى",
    )
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, verbose_name="نوع الإشعار"
    )
    title = models.CharField(max_length=200, verbose_name="عنوان الإشعار")
    message = models.TextField(verbose_name="نص الإشعار")
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="complaint_notifications",
        verbose_name="المستلم",
    )
    is_read = models.BooleanField(default=False, verbose_name="تمت القراءة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ القراءة")
    url = models.CharField(
        max_length=255, verbose_name="رابط الإشعار", help_text="الرابط المرتبط بالإشعار"
    )

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["complaint", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.complaint.complaint_number}"

    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    @classmethod
    def create_notification(
        cls, complaint, notification_type, recipient, title, message=None, url=None
    ):
        """إنشاء إشعار جديد"""
        if not message:
            message = title

        if not url:
            url = reverse("complaints:complaint_detail", kwargs={"pk": complaint.pk})

        notification = cls.objects.create(
            complaint=complaint,
            notification_type=notification_type,
            recipient=recipient,
            title=title,
            message=message,
            url=url,
        )

        # WebSocket notifications disabled - chat system removed
        # from channels.layers import get_channel_layer
        # from asgiref.sync import async_to_sync
        #
        # channel_layer = get_channel_layer()
        # async_to_sync(channel_layer.group_send)(
        #     f"user_{recipient.id}_notifications",
        #     {
        #         "type": "notification.message",
        #         "notification": {
        #             "id": notification.id,
        #             "type": notification.notification_type,
        #             "title": notification.title,
        #             "message": notification.message,
        #             "url": notification.url,
        #             "created_at": notification.created_at.isoformat()
        #         }
        #     }
        # )

        return notification


class ComplaintTemplate(models.Model):
    """نماذج الشكاوى الجاهزة"""

    name = models.CharField(max_length=100, verbose_name="اسم النموذج", unique=True)
    complaint_type = models.ForeignKey(
        ComplaintType,
        on_delete=models.CASCADE,
        related_name="templates",
        verbose_name="نوع الشكوى",
    )
    title_template = models.CharField(
        max_length=200,
        verbose_name="قالب العنوان",
        help_text="يمكن استخدام {customer} و {order} كمتغيرات",
    )
    description_template = models.TextField(
        verbose_name="قالب الوصف",
        help_text="يمكن استخدام {customer}، {order}، {date} كمتغيرات",
    )
    priority = models.CharField(
        max_length=10,
        choices=Complaint.PRIORITY_CHOICES,
        default="medium",
        verbose_name="الأولوية",
    )
    default_deadline_hours = models.PositiveIntegerField(
        default=72, verbose_name="المهلة الافتراضية (بالساعات)"
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "نموذج شكوى"
        verbose_name_plural = "نماذج الشكاوى"
        ordering = ["complaint_type", "name"]

    def __str__(self):
        return f"{self.complaint_type.name} - {self.name}"

    def generate_title(self, customer=None, order=None):
        """توليد عنوان الشكوى من القالب"""
        context = {
            "customer": customer.name if customer else "",
            "order": order.order_number if order else "",
        }
        return self.title_template.format(**context)

    def generate_description(self, customer=None, order=None):
        """توليد وصف الشكوى من القالب"""
        context = {
            "customer": customer.name if customer else "",
            "order": order.order_number if order else "",
            "date": timezone.now().strftime("%Y-%m-%d"),
        }
        return self.description_template.format(**context)


class ComplaintEvaluation(models.Model):
    """تقييم مفصل للشكوى"""

    RATING_CHOICES = [
        (1, "غير راضي جداً"),
        (2, "غير راضي"),
        (3, "محايد"),
        (4, "راضي"),
        (5, "راضي جداً"),
    ]

    RESPONSE_TIME_RATING = [
        (1, "بطيء جداً"),
        (2, "بطيء"),
        (3, "مقبول"),
        (4, "سريع"),
        (5, "ممتاز"),
    ]

    SOLUTION_QUALITY_RATING = [
        (1, "غير مناسب"),
        (2, "ضعيف"),
        (3, "مقبول"),
        (4, "جيد"),
        (5, "ممتاز"),
    ]

    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name="evaluation",
        verbose_name="الشكوى",
    )

    # التقييمات المختلفة
    overall_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name="التقييم العام",
        help_text="تقييم عام لتجربة حل الشكوى",
    )
    response_time_rating = models.PositiveSmallIntegerField(
        choices=RESPONSE_TIME_RATING, verbose_name="تقييم سرعة الاستجابة"
    )
    solution_quality_rating = models.PositiveSmallIntegerField(
        choices=SOLUTION_QUALITY_RATING, verbose_name="تقييم جودة الحل"
    )
    staff_behavior_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, verbose_name="تقييم تعامل الموظفين"
    )

    # التعليقات
    positive_feedback = models.TextField(
        blank=True,
        verbose_name="ما أعجبك في الخدمة؟",
        help_text="اذكر النقاط الإيجابية",
    )
    negative_feedback = models.TextField(
        blank=True,
        verbose_name="ما لم يعجبك؟",
        help_text="اذكر النقاط التي تحتاج تحسين",
    )
    suggestions = models.TextField(
        blank=True,
        verbose_name="اقتراحات للتحسين",
        help_text="كيف يمكننا تحسين خدمتنا؟",
    )

    # معلومات إضافية
    would_recommend = models.BooleanField(
        null=True, blank=True, verbose_name="هل تنصح بخدماتنا؟"
    )
    evaluation_date = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ التقييم"
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="عنوان IP"
    )

    class Meta:
        verbose_name = "تقييم شكوى"
        verbose_name_plural = "تقييمات الشكاوى"
        ordering = ["-evaluation_date"]

    def __str__(self):
        return f"تقييم {self.complaint.complaint_number} - {self.overall_rating}/5"

    @property
    def average_rating(self):
        """متوسط التقييمات"""
        ratings = [
            self.overall_rating,
            self.response_time_rating,
            self.solution_quality_rating,
            self.staff_behavior_rating,
        ]
        return sum(ratings) / len(ratings)

    @property
    def rating_color(self):
        """لون التقييم حسب المتوسط"""
        avg = self.average_rating
        if avg >= 4.5:
            return "success"
        elif avg >= 3.5:
            return "warning"
        else:
            return "danger"


class ResolutionMethod(models.Model):
    """طرق حل الشكاوى"""

    name = models.CharField(max_length=100, verbose_name="اسم طريقة الحل", unique=True)
    description = models.TextField(blank=True, verbose_name="وصف طريقة الحل")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "طريقة حل"
        verbose_name_plural = "طرق الحل"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ComplaintUserPermissions(models.Model):
    """إعدادات صلاحيات المستخدمين في نظام الشكاوى"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="complaint_permissions",
        verbose_name="المستخدم",
    )

    # صلاحيات الإسناد والتصعيد
    can_be_assigned_complaints = models.BooleanField(
        default=False,
        verbose_name="يمكن إسناد الشكاوى إليه",
        help_text="هل يمكن إسناد الشكاوى لهذا المستخدم؟",
    )
    can_receive_escalations = models.BooleanField(
        default=False,
        verbose_name="يمكن تصعيد الشكاوى إليه",
        help_text="هل يمكن تصعيد الشكاوى لهذا المستخدم؟",
    )
    can_escalate_complaints = models.BooleanField(
        default=False,
        verbose_name="يمكن تصعيد الشكاوى",
        help_text="هل يمكن لهذا المستخدم تصعيد الشكاوى للآخرين؟",
    )

    # صلاحيات العرض والتعديل
    can_view_all_complaints = models.BooleanField(
        default=False,
        verbose_name="يمكن عرض جميع الشكاوى",
        help_text="هل يمكن لهذا المستخدم عرض جميع الشكاوى؟",
    )
    can_edit_all_complaints = models.BooleanField(
        default=False,
        verbose_name="يمكن تعديل جميع الشكاوى",
        help_text="هل يمكن لهذا المستخدم تعديل جميع الشكاوى؟",
    )
    can_delete_complaints = models.BooleanField(
        default=False,
        verbose_name="يمكن حذف الشكاوى",
        help_text="هل يمكن لهذا المستخدم حذف الشكاوى؟",
    )

    # صلاحيات إدارية
    can_assign_complaints = models.BooleanField(
        default=False,
        verbose_name="يمكن إسناد الشكاوى للآخرين",
        help_text="هل يمكن لهذا المستخدم إسناد الشكاوى للمستخدمين الآخرين؟",
    )
    can_change_complaint_status = models.BooleanField(
        default=True,
        verbose_name="يمكن تغيير حالة الشكوى",
        help_text="هل يمكن لهذا المستخدم تغيير حالة الشكاوى المسندة إليه؟",
    )
    can_resolve_complaints = models.BooleanField(
        default=True,
        verbose_name="يمكن حل الشكاوى",
        help_text="هل يمكن لهذا المستخدم حل الشكاوى؟",
    )
    can_close_complaints = models.BooleanField(
        default=False,
        verbose_name="يمكن إغلاق الشكاوى",
        help_text="هل يمكن لهذا المستخدم إغلاق الشكاوى نهائياً؟",
    )
    max_assigned_complaints = models.PositiveIntegerField(
        default=0,
        verbose_name="الحد الأقصى للشكاوى المسندة",
        help_text="الحد الأقصى لعدد الشكاوى التي يمكن إسنادها لهذا المستخدم (0 = بلا حدود)",
    )
    departments = models.ManyToManyField(
        "accounts.Department",
        blank=True,
        verbose_name="الأقسام المخولة",
        help_text="الأقسام التي يمكن لهذا المستخدم التعامل مع شكاواها",
    )
    complaint_types = models.ManyToManyField(
        ComplaintType,
        blank=True,
        verbose_name="أنواع الشكاوى المخولة",
        help_text="أنواع الشكاوى التي يمكن لهذا المستخدم التعامل معها",
    )
    is_active = models.BooleanField(
        default=True, verbose_name="نشط", help_text="هل هذه الصلاحيات نشطة؟"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "صلاحيات مستخدم الشكاوى"
        verbose_name_plural = "صلاحيات مستخدمي الشكاوى"
        ordering = ["user__username"]

    def __str__(self):
        return f"صلاحيات {self.user.get_full_name() or self.user.username}"

    @property
    def current_assigned_complaints_count(self):
        """عدد الشكاوى المسندة حالياً"""
        return self.user.assigned_complaints.filter(
            status__in=["new", "in_progress", "escalated"]
        ).count()

    def can_accept_new_complaint(self):
        """هل يمكن قبول شكوى جديدة؟"""
        if not self.can_be_assigned_complaints or not self.is_active:
            return False

        if self.max_assigned_complaints == 0:
            return True

        return self.current_assigned_complaints_count < self.max_assigned_complaints
