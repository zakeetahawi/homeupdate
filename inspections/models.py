import os
import re
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils.tracker import FieldTracker

from core.soft_delete import SoftDeleteMixin


def validate_inspection_pdf_file(value):
    """التحقق من أن ملف المعاينة المرفوع هو PDF"""
    if value:
        ext = os.path.splitext(value.name)[1]
        if ext.lower() != ".pdf":
            raise ValidationError("يجب أن يكون الملف من نوع PDF فقط")

        # التحقق من حجم الملف (أقل من 50 ميجابايت)
        if value.size > 50 * 1024 * 1024:
            raise ValidationError("حجم الملف يجب أن يكون أقل من 50 ميجابايت")


class InspectionEvaluation(models.Model):
    CRITERIA_CHOICES = [
        ("location", _("الموقع")),
        ("condition", _("الحالة")),
        ("suitability", _("الملاءمة")),
        ("safety", _("السلامة")),
        ("accessibility", _("سهولة الوصول")),
    ]
    RATING_CHOICES = [
        (1, _("ضعيف")),
        (2, _("مقبول")),
        (3, _("جيد")),
        (4, _("جيد جداً")),
        (5, _("ممتاز")),
    ]
    inspection = models.ForeignKey(
        "Inspection",
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name=_("المعاينة"),
    )
    criteria = models.CharField(
        _("معيار التقييم"), max_length=20, choices=CRITERIA_CHOICES
    )
    rating = models.IntegerField(_("التقييم"), choices=RATING_CHOICES)
    notes = models.TextField(_("ملاحظات التقييم"), blank=True)
    created_at = models.DateTimeField(_("تاريخ التقييم"), auto_now_add=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="evaluations_created",
        verbose_name=_("تم التقييم بواسطة"),
    )

    class Meta:
        verbose_name = _("تقييم المعاينة")
        verbose_name_plural = _("تقييمات المعاينات")
        indexes = [
            models.Index(fields=["inspection"], name="inspection_eval_insp_idx"),
            models.Index(fields=["criteria"], name="inspection_eval_criteria_idx"),
            models.Index(fields=["rating"], name="inspection_eval_rating_idx"),
            models.Index(fields=["created_by"], name="inspection_eval_creator_idx"),
            models.Index(fields=["created_at"], name="inspection_eval_created_idx"),
        ]

    def __str__(self):
        return f"تقييم معاينة {self.inspection.contract_number}"


class InspectionNotification(models.Model):
    TYPE_CHOICES = [
        ("scheduled", _("موعد معاينة")),
        ("reminder", _("تذكير")),
        ("status_change", _("تغيير الحالة")),
        ("evaluation", _("تقييم جديد")),
    ]
    inspection = models.ForeignKey(
        "Inspection",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("المعاينة"),
    )
    type = models.CharField(_("نوع التنبيه"), max_length=20, choices=TYPE_CHOICES)
    message = models.TextField(_("نص التنبيه"))
    is_read = models.BooleanField(_("تم القراءة"), default=False)
    created_at = models.DateTimeField(_("تاريخ التنبيه"), auto_now_add=True)
    scheduled_for = models.DateTimeField(_("موعد التنبيه"), null=True, blank=True)

    class Meta:
        verbose_name = _("تنبيه معاينة")
        verbose_name_plural = _("تنبيهات المعاينات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inspection"], name="inspection_notif_insp_idx"),
            models.Index(fields=["type"], name="inspection_notif_type_idx"),
            models.Index(fields=["is_read"], name="inspection_notif_read_idx"),
            models.Index(fields=["created_at"], name="inspection_notif_created_idx"),
            models.Index(
                fields=["scheduled_for"], name="inspection_notif_scheduled_idx"
            ),
        ]

    def __str__(self):
        return f"تنبيه: {self.message[:50]}..."

    @property
    def is_scheduled(self):
        return bool(self.scheduled_for)


class InspectionReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ("daily", _("يومي")),
        ("weekly", _("أسبوعي")),
        ("monthly", _("شهري")),
        ("custom", _("مخصص")),
    ]
    title = models.CharField(_("عنوان التقرير"), max_length=200)
    report_type = models.CharField(
        _("نوع التقرير"), max_length=10, choices=REPORT_TYPE_CHOICES
    )
    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.CASCADE,
        related_name="inspection_reports",
        verbose_name=_("الفرع"),
    )
    date_from = models.DateField(_("من تاريخ"))
    date_to = models.DateField(_("إلى تاريخ"))
    total_inspections = models.IntegerField(_("إجمالي المعاينات"), default=0)
    successful_inspections = models.IntegerField(_("المعاينات الناجحة"), default=0)
    pending_inspections = models.IntegerField(_("المعاينات المعلقة"), default=0)
    cancelled_inspections = models.IntegerField(_("المعاينات الملغاة"), default=0)
    notes = models.TextField(_("ملاحظات"), blank=True)
    created_at = models.DateTimeField(_("تاريخ إنشاء التقرير"), auto_now_add=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="inspection_reports_created",
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    class Meta:
        verbose_name = _("تقرير معاينات")
        verbose_name_plural = _("تقارير المعاينات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["report_type"], name="inspection_report_type_idx"),
            models.Index(fields=["branch"], name="inspection_report_branch_idx"),
            models.Index(fields=["date_from"], name="inspection_report_from_idx"),
            models.Index(fields=["date_to"], name="inspection_report_to_idx"),
            models.Index(fields=["created_at"], name="inspection_report_created_idx"),
            models.Index(fields=["created_by"], name="inspection_report_creator_idx"),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_report_type_display()}"

    def calculate_statistics(self):
        from django.core.cache import cache

        # إنشاء مفتاح تخزين مؤقت فريد بناءً على معلمات التقرير
        cache_key = (
            f"inspection_report_stats_{self.branch_id}_{self.date_from}_{self.date_to}"
        )
        # محاولة استرداد النتائج من التخزين المؤقت
        cached_stats = cache.get(cache_key)
        if cached_stats is None:
            # إذا لم تكن النتائج مخزنة مؤقتًا، قم بحساب الإحصائيات من قاعدة البيانات
            inspections = Inspection.objects.filter(
                branch=self.branch,
                request_date__gte=self.date_from,
                request_date__lte=self.date_to,
            )
            self.total_inspections = inspections.count()
            self.successful_inspections = inspections.filter(result="passed").count()
            self.pending_inspections = inspections.filter(status="pending").count()
            self.cancelled_inspections = inspections.filter(status="cancelled").count()
            # حفظ النتائج في التخزين المؤقت لمدة ساعة واحدة (3600 ثانية)
            cached_stats = {
                "total": self.total_inspections,
                "successful": self.successful_inspections,
                "pending": self.pending_inspections,
                "cancelled": self.cancelled_inspections,
            }
            cache.set(cache_key, cached_stats, 3600)
        else:
            # استخدام النتائج المخزنة مؤقتًا
            self.total_inspections = cached_stats["total"]
            self.successful_inspections = cached_stats["successful"]
            self.pending_inspections = cached_stats["pending"]
            self.cancelled_inspections = cached_stats["cancelled"]
        self.save()


class Inspection(SoftDeleteMixin, models.Model):
    STATUS_CHOICES = [
        ("not_scheduled", _("غير مجدولة")),
        ("pending", _("قيد الانتظار")),
        ("scheduled", _("مجدول")),
        ("completed", _("مكتملة")),
        ("cancelled", _("ملغية")),
        ("postponed_by_customer", _("مؤجل من طرف العميل")),
    ]
    RESULT_CHOICES = [
        ("passed", _("ناجحة")),
        ("failed", _("غير مجدية")),
    ]
    # إضافة متتبع الحقول
    tracker = FieldTracker(fields=["status", "result"])
    contract_number = models.CharField(
        _("رقم العقد"), max_length=50, unique=True, blank=True, null=True
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="inspections",
        verbose_name=_("العميل"),
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.CASCADE,
        related_name="inspections",
        verbose_name=_("الفرع"),
        null=True,
        blank=True,
    )
    inspector = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_inspections",
        verbose_name=_("المعاين"),
    )
    responsible_employee = models.ForeignKey(
        "accounts.Salesperson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("البائع"),
        related_name="inspections",
    )
    is_from_orders = models.BooleanField(_("من قسم الطلبات"), default=False)
    windows_count = models.IntegerField(_("عدد الشبابيك"), null=True, blank=True)
    inspection_file = models.FileField(
        _("ملف المعاينة"),
        upload_to="inspections/files/",
        null=True,
        blank=True,
        validators=[validate_inspection_pdf_file],
        help_text="يجب أن يكون الملف من نوع PDF وأقل من 50 ميجابايت",
    )
    # حقول Google Drive
    google_drive_file_id = models.CharField(
        _("معرف ملف Google Drive"), max_length=255, blank=True, null=True
    )
    google_drive_file_url = models.URLField(
        _("رابط ملف Google Drive"), blank=True, null=True
    )
    google_drive_file_name = models.CharField(
        _("اسم الملف في Google Drive"), max_length=500, blank=True, null=True
    )
    is_uploaded_to_drive = models.BooleanField(
        _("تم الرفع إلى Google Drive"), default=False
    )
    request_date = models.DateField(
        _("تاريخ طلب المعاينة"), default=timezone.now, editable=True
    )
    scheduled_date = models.DateField(
        _("تاريخ تنفيذ المعاينة"), blank=True, null=True, editable=True
    )
    scheduled_time = models.TimeField(_("وقت تنفيذ المعاينة"), blank=True, null=True)

    # حالة المديونية
    PAYMENT_STATUS_CHOICES = [
        ("paid", "مكتمل السداد"),
        ("collect_on_visit", "تحصيل عند العميل"),
    ]
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="paid",
        verbose_name=_("حالة المديونية"),
    )
    status = models.CharField(
        _("الحالة"),
        max_length=32,  # Increased to fit 'postponed_by_customer'
        choices=STATUS_CHOICES,
        default="pending",
    )
    result = models.CharField(
        _("النتيجة"), max_length=10, choices=RESULT_CHOICES, null=True, blank=True
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    order_notes = models.TextField(
        _("ملاحظات الطلب"), blank=True, help_text=_("نسخة ثابتة من ملاحظات الطلب")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_inspections",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_inspections",
        verbose_name=_("آخر تعديل بواسطة"),
        editable=False,
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspections",
        verbose_name=_("الطلب المرتبط"),
        help_text=_("كل معاينة يجب أن تكون مرتبطة بطلب من قسم الطلبات"),
    )
    created_at = models.DateTimeField(
        _("تاريخ الإنشاء"), default=timezone.now, editable=True
    )
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    completed_at = models.DateTimeField(_("تاريخ الإكتمال"), null=True, blank=True)
    expected_delivery_date = models.DateField(
        _("تاريخ التسليم المتوقع"),
        null=True,
        blank=True,
        help_text=_("يتم حسابه تلقائياً بناءً على نوع الطلب"),
    )

    class Meta:
        verbose_name = _("معاينة")
        verbose_name_plural = _("المعاينات")
        ordering = ["-request_date"]
        indexes = [
            models.Index(fields=["contract_number"], name="inspection_contract_idx"),
            models.Index(fields=["customer"], name="inspection_customer_idx"),
            models.Index(fields=["branch"], name="inspection_branch_idx"),
            models.Index(fields=["inspector"], name="inspection_inspector_idx"),
            models.Index(fields=["status"], name="inspection_status_idx"),
            models.Index(fields=["result"], name="inspection_result_idx"),
            models.Index(fields=["request_date"], name="inspection_req_date_idx"),
            models.Index(fields=["scheduled_date"], name="inspection_sched_date_idx"),
            models.Index(fields=["order"], name="inspection_order_idx"),
            models.Index(fields=["created_at"], name="inspection_created_idx"),
        ]

    def __str__(self):
        customer_name = self.customer.name if self.customer else "عميل جديد"
        return f"{self.inspection_code} - {customer_name}"

    @property
    def inspection_code(self):
        """إرجاع رقم طلب المعاينة الموحد (رقم الطلب + I)"""
        if self.order and self.order.order_number:
            return f"{self.order.order_number}-I"
        return f"#{self.id}-I"  # للبيانات القديمة التي لا تحتوي على طلب

    def get_absolute_url(self):
        """إرجاع رابط تفاصيل المعاينة باستخدام كود المعاينة"""
        from django.urls import reverse

        return reverse(
            "inspections:inspection_detail_by_code", args=[self.inspection_code]
        )

    def clean(self):
        # التأكد من وجود طلب مرتبط
        if not self.order:
            raise ValidationError(_("يجب ربط المعاينة بطلب من قسم الطلبات"))

        # Ensure scheduled date is not before request date
        if self.scheduled_date and self.request_date:
            if self.scheduled_date < self.request_date:
                raise ValidationError(
                    _("تاريخ تنفيذ المعاينة لا يمكن أن يكون قبل تاريخ الطلب")
                )

        # ملاحظة: تم إزالة فحص الفرع من هنا لأن:
        # 1. الـ view يفحص الصلاحيات بالفعل (InspectionUpdateView.test_func)
        # 2. مديرو النظام يحتاجون تحديث أي معاينة بغض النظر عن نقل الموظفين
        # 3. الفحص هنا كان يعتمد على created_by وليس المستخدم الحالي

    def save(self, *args, **kwargs):
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(self, ["contract_number"])

        if not self.branch and self.created_by:
            self.branch = self.created_by.branch
        # تتبع التغييرات في حقل status
        status_changed = self.tracker.has_changed("status")
        old_status = self.tracker.previous("status")
        # Set completed_at when status changes to completed
        if status_changed and self.status == "completed" and not self.completed_at:
            self.completed_at = timezone.now()
        elif (
            status_changed and old_status == "completed" and self.status != "completed"
        ):
            self.completed_at = None
        # نسخ ملاحظات الطلب إلى الحقل الجديد إذا كان الطلب موجودًا
        if self.order and self.order.notes and not self.order_notes:
            self.order_notes = self.order.notes

        # تحديد حالة المديونية تلقائياً بناءً على حالة الدفع في الطلب
        # فقط عند الإنشاء الأول أو إذا لم تكن محددة
        if self.order and not self.pk:  # فقط عند الإنشاء الجديد
            if self.order.is_fully_paid:
                self.payment_status = "paid"
            else:
                self.payment_status = "collect_on_visit"
        elif self.order and not self.payment_status:  # إذا لم تكن محددة
            if self.order.is_fully_paid:
                self.payment_status = "paid"
            else:
                self.payment_status = "collect_on_visit"
        # التحقق من تغيير الملف
        file_changed = False
        if self.pk:  # إذا كان هذا تحديث وليس إنشاء جديد
            try:
                old_instance = Inspection.objects.get(pk=self.pk)
                # التحقق من تغيير الملف
                if old_instance.inspection_file != self.inspection_file:
                    file_changed = True
                    # إعادة تعيين حالة الرفع إذا تغير الملف
                    self.is_uploaded_to_drive = False
                    self.google_drive_file_id = None
                    self.google_drive_file_url = None
                    self.google_drive_file_name = None
            except Inspection.DoesNotExist:
                file_changed = True
        else:
            # إنشاء جديد
            file_changed = bool(self.inspection_file)
        # توليد اسم الملف لـ Google Drive فقط إذا تغير الملف
        if self.inspection_file and (file_changed or not self.google_drive_file_name):
            self.google_drive_file_name = self.generate_drive_filename()

        # حساب تاريخ التسليم المتوقع إذا لم يكن محدداً
        if not self.expected_delivery_date:
            self.expected_delivery_date = self.calculate_expected_delivery_date()

        super().save(*args, **kwargs)
        # جدولة رفع تلقائي إلى Google Drive فقط إذا تغير الملف ولم يتم رفعه بعد
        if file_changed and self.inspection_file and not self.is_uploaded_to_drive:
            self.schedule_upload_to_google_drive()

    def get_status_color(self):
        status_colors = {
            "pending": "warning",
            "scheduled": "info",
            "completed": "success",
            "cancelled": "danger",
            "postponed_by_customer": "secondary",
        }
        return status_colors.get(self.status, "secondary")

    def get_status_badge_class(self):
        """إرجاع فئة الـ badge المناسبة لحالة المعاينة - ألوان موحدة"""
        status_badges = {
            "not_scheduled": "bg-secondary",  # فضي
            "pending": "bg-warning text-dark",  # برتقالي
            "scheduled": "bg-info",  # أزرق فاتح
            "in_progress": "bg-primary",  # أزرق
            "completed": "bg-success",  # أخضر
            "cancelled": "bg-danger",  # أحمر
            "postponed_by_customer": "bg-secondary",  # رمادي لطيف
        }
        return status_badges.get(self.status, "bg-secondary")

    def get_status_icon(self):
        """إرجاع أيقونة الحالة المناسبة"""
        status_icons = {
            "pending": "fas fa-clock",
            "scheduled": "fas fa-calendar",
            "completed": "fas fa-check-circle",
            "cancelled": "fas fa-times-circle",
            "postponed_by_customer": "fas fa-pause-circle",
        }
        return status_icons.get(self.status, "fas fa-minus")

    @property
    def is_scheduled(self):
        return self.status == "scheduled"

    @property
    def is_pending(self):
        return self.status == "pending"

    @property
    def is_completed(self):
        return self.status == "completed"

    @property
    def is_cancelled(self):
        return self.status == "cancelled"

    @property
    def is_successful(self):
        return self.result == "passed"

    @property
    def is_overdue(self):
        return self.status == "pending" and self.scheduled_date < timezone.now().date()

    def generate_drive_filename(self):
        """توليد اسم الملف للرفع على Google Drive"""
        # اسم العميل (تنظيف الاسم من الرموز الخاصة)
        if self.customer and self.customer.name:
            customer_name = self.customer.name
        elif hasattr(self, "customer_name") and self.customer_name:
            customer_name = self.customer_name
        else:
            customer_name = "عميل_جديد"
        customer_name = self._clean_filename(customer_name)
        # الفرع
        branch_name = self.branch.name if self.branch else "فرع_غير_محدد"
        branch_name = self._clean_filename(branch_name)
        # التاريخ
        date_str = (
            self.scheduled_date.strftime("%Y-%m-%d")
            if self.scheduled_date
            else timezone.now().strftime("%Y-%m-%d")
        )
        # رقم الطلب
        order_number = (
            self.order.order_number
            if self.order
            else self.contract_number or "بدون_رقم"
        )
        order_number = self._clean_filename(order_number)
        # تجميع اسم الملف
        filename = f"{customer_name}_{branch_name}_{date_str}_{order_number}.pdf"
        return filename

    def _clean_filename(self, name):
        """تنظيف اسم الملف من الرموز الخاصة"""
        # إزالة الرموز الخاصة والمسافات
        cleaned = re.sub(r"[^\w\u0600-\u06FF\s-]", "", str(name))
        # استبدال المسافات بـ underscore
        cleaned = re.sub(r"\s+", "_", cleaned)
        return cleaned[:50]  # تحديد الطول الأقصى

    def calculate_expected_delivery_date(self):
        """حساب تاريخ التسليم المتوقع للمعاينة"""
        from orders.models import DeliveryTimeSettings

        if not self.request_date:
            return None

        # تحديد نوع الطلب بناءً على الطلب المرتبط
        order_type = "normal"  # افتراضي
        if self.order and hasattr(self.order, "status"):
            if self.order.status == "vip":
                order_type = "vip"

        # الحصول على عدد الأيام من إعدادات المعاينة
        delivery_days = DeliveryTimeSettings.get_delivery_days(
            service_type="inspection", order_type=order_type
        )

        # حساب التاريخ المتوقع
        expected_date = self.request_date + timedelta(days=delivery_days)
        return expected_date

    def recalculate_expected_delivery_date(self):
        """إعادة حساب تاريخ التسليم المتوقع وحفظه"""
        self.expected_delivery_date = self.calculate_expected_delivery_date()
        self.save(update_fields=["expected_delivery_date"])

    def upload_to_google_drive_async(self):
        """رفع الملف إلى Google Drive بشكل تلقائي"""
        try:
            import logging

            from inspections.services.google_drive_service import (
                get_google_drive_service,
            )

            logger = logging.getLogger(__name__)
            logger.info(f"بدء رفع ملف المعاينة {self.id} إلى Google Drive")
            # الحصول على خدمة Google Drive
            drive_service = get_google_drive_service()
            if not drive_service:
                logger.error("فشل في الحصول على خدمة Google Drive")
                return False
            # رفع الملف
            result = drive_service.upload_inspection_file(
                file_path=self.inspection_file.path, inspection=self
            )

            # التحقق من نجاح الرفع (result يحتوي على file_id إذا نجح)
            if result and result.get("file_id"):
                # تحديث بيانات المعاينة
                self.google_drive_file_id = result.get("file_id")
                self.google_drive_file_url = result.get("view_url")
                self.is_uploaded_to_drive = True
                # حفظ التحديثات في قاعدة البيانات
                try:
                    # تحديث قاعدة البيانات مباشرة
                    Inspection.objects.filter(id=self.id).update(
                        google_drive_file_id=self.google_drive_file_id,
                        google_drive_file_url=self.google_drive_file_url,
                        is_uploaded_to_drive=True,
                    )
                    # إعادة تحميل الكائن من قاعدة البيانات للتأكد من التحديث
                    self.refresh_from_db()
                    # logger.info(f"تم تحديث بيانات المعاينة {self.id} في قاعدة البيانات")  # معطل لتجنب الرسائل الكثيرة
                except Exception as update_error:
                    logger.error(
                        f"خطأ في تحديث قاعدة البيانات للمعاينة {self.id}: {str(update_error)}"
                    )
                logger.info(f"تم رفع ملف المعاينة {self.id} بنجاح إلى Google Drive")
                return True
            else:
                logger.error(f"فشل في رفع ملف المعاينة {self.id}: {result}")
                return False
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"خطأ في رفع ملف المعاينة {self.id} إلى Google Drive: {str(e)}"
            )
            return False

    def schedule_upload_to_google_drive(self):
        """جدولة رفع الملف إلى Google Drive بشكل غير متزامن"""
        try:
            from orders.tasks import upload_inspection_to_drive_async

            upload_inspection_to_drive_async.delay(self.pk)
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"تم جدولة رفع ملف المعاينة {self.id} إلى Google Drive")
            return True
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في جدولة رفع ملف المعاينة {self.id}: {str(e)}")
            # في حالة فشل الجدولة، نحاول الرفع المباشر كبديل
            return self.upload_to_google_drive_async()


# Signal handlers moved to inspections/signals.py to avoid circular imports


class InspectionFile(models.Model):
    """
    نموذج لتخزين ملفات المعاينة المتعددة.
    يدعم حتى 5 ملفات لكل معاينة مع رفع تلقائي لـ Google Drive.
    """

    inspection = models.ForeignKey(
        "Inspection",
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name=_("المعاينة"),
    )
    file = models.FileField(
        _("الملف"),
        upload_to="inspections/files/",
        validators=[validate_inspection_pdf_file],
        help_text=_("يجب أن يكون الملف من نوع PDF وأقل من 50 ميجابايت"),
    )
    original_filename = models.CharField(
        _("اسم الملف الأصلي"),
        max_length=500,
        blank=True,
    )
    google_drive_file_id = models.CharField(
        _("معرف ملف Google Drive"),
        max_length=255,
        blank=True,
        null=True,
    )
    google_drive_file_url = models.URLField(
        _("رابط ملف Google Drive"),
        blank=True,
        null=True,
    )
    google_drive_file_name = models.CharField(
        _("اسم الملف في Google Drive"),
        max_length=500,
        blank=True,
        null=True,
    )
    is_uploaded_to_drive = models.BooleanField(
        _("تم الرفع إلى Google Drive"),
        default=False,
    )
    order = models.PositiveIntegerField(
        _("الترتيب"),
        default=0,
        help_text=_("ترتيب عرض الملف"),
    )
    created_at = models.DateTimeField(
        _("تاريخ الإنشاء"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("ملف معاينة")
        verbose_name_plural = _("ملفات المعاينات")
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["inspection"], name="insp_file_inspection_idx"),
            models.Index(
                fields=["is_uploaded_to_drive"], name="insp_file_uploaded_idx"
            ),
            models.Index(fields=["created_at"], name="insp_file_created_idx"),
        ]

    def __str__(self):
        return f"ملف معاينة #{self.inspection_id} - {self.original_filename or self.file.name}"

    def save(self, *args, **kwargs):
        # حفظ اسم الملف الأصلي
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)

        # توليد اسم ملف Google Drive
        if self.file and not self.google_drive_file_name:
            self.google_drive_file_name = self.generate_drive_filename()

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # جدولة رفع الملف إلى Google Drive
        if is_new and self.file and not self.is_uploaded_to_drive:
            self.schedule_upload_to_google_drive()

    def generate_drive_filename(self):
        """
        توليد اسم الملف للرفع على Google Drive
        الصيغة: اسم_العميل + رقم_تسلسلي (مثال: زكي1، زكي2، محمد1، محمد2)
        """
        inspection = self.inspection
        # اسم العميل
        if inspection.customer and inspection.customer.name:
            customer_name = inspection.customer.name
        else:
            customer_name = "عميل_جديد"
        customer_name = self._clean_filename(customer_name)

        # حساب الرقم التسلسلي الفريد لهذا العميل
        # نحسب عدد الملفات الموجودة لهذا العميل في كل المعاينات
        customer_files_count = (
            InspectionFile.objects.filter(inspection__customer=inspection.customer)
            .exclude(pk=self.pk)
            .count()
        )

        # الرقم التسلسلي = عدد الملفات الموجودة + 1
        sequential_number = customer_files_count + 1

        # تجميع اسم الملف: اسم_العميل + الرقم_التسلسلي
        filename = f"{customer_name}{sequential_number}.pdf"
        return filename

    def _clean_filename(self, name):
        """تنظيف اسم الملف من الرموز الخاصة"""
        cleaned = re.sub(r"[^\w\u0600-\u06FF\s-]", "", str(name))
        cleaned = re.sub(r"\s+", "_", cleaned)
        return cleaned[:50]

    def schedule_upload_to_google_drive(self):
        """جدولة رفع الملف إلى Google Drive"""
        try:
            from orders.tasks import upload_inspection_file_to_drive_async

            upload_inspection_file_to_drive_async.delay(self.pk)
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"تم جدولة رفع ملف المعاينة {self.pk} إلى Google Drive")
            return True
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في جدولة رفع الملف {self.pk}: {str(e)}")
            # محاولة الرفع المباشر
            return self.upload_to_google_drive_sync()

    def upload_to_google_drive_sync(self):
        """رفع الملف إلى Google Drive بشكل متزامن"""
        try:
            import logging

            from inspections.services.google_drive_service import (
                get_google_drive_service,
            )

            logger = logging.getLogger(__name__)
            logger.info(f"بدء رفع ملف {self.pk} إلى Google Drive")

            drive_service = get_google_drive_service()
            if not drive_service:
                logger.error("فشل في الحصول على خدمة Google Drive")
                return False

            # رفع الملف
            result = drive_service.upload_inspection_file(
                file_path=self.file.path, inspection=self.inspection
            )

            if result and result.get("file_id"):
                InspectionFile.objects.filter(id=self.id).update(
                    google_drive_file_id=result.get("file_id"),
                    google_drive_file_url=result.get("view_url"),
                    is_uploaded_to_drive=True,
                )
                logger.info(f"تم رفع الملف {self.pk} بنجاح")
                return True
            else:
                logger.error(f"فشل رفع الملف {self.pk}")
                return False
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في رفع الملف {self.pk}: {str(e)}")
            return False
