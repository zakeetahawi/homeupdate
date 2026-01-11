from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Report(models.Model):
    """
    Base model for all reports
    """

    REPORT_TYPE_CHOICES = [
        ("sales", _("تقرير المبيعات")),
        ("production", _("تقرير الإنتاج")),
        ("inventory", _("تقرير المخزون")),
        ("financial", _("تقرير مالي")),
        ("analytics", _("تقرير تحليلي")),
        ("seller_activity", _("تقرير نشاط البائعين")),
        ("custom", _("تقرير مخصص")),
    ]
    title = models.CharField(_("عنوان التقرير"), max_length=200)
    report_type = models.CharField(
        _("نوع التقرير"), max_length=20, choices=REPORT_TYPE_CHOICES
    )
    description = models.TextField(_("وصف التقرير"), blank=True)
    parameters = models.JSONField(_("معلمات التقرير"), default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports_created",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("تقرير")
        verbose_name_plural = _("التقارير")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SavedReport(models.Model):
    """
    Model for saved report results
    """

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="saved_results",
        verbose_name=_("التقرير"),
    )
    name = models.CharField(_("اسم النتيجة المحفوظة"), max_length=200)
    data = models.JSONField(_("بيانات التقرير"), default=dict)
    parameters_used = models.JSONField(
        _("المعلمات المستخدمة"), default=dict, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="saved_reports",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("تقرير محفوظ")
        verbose_name_plural = _("التقارير المحفوظة")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.report.title}"


class ReportSchedule(models.Model):
    """
    Model for scheduling reports
    """

    FREQUENCY_CHOICES = [
        ("daily", _("يومي")),
        ("weekly", _("أسبوعي")),
        ("monthly", _("شهري")),
        ("quarterly", _("ربع سنوي")),
    ]
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name=_("التقرير"),
    )
    name = models.CharField(_("اسم الجدولة"), max_length=200)
    frequency = models.CharField(_("التكرار"), max_length=20, choices=FREQUENCY_CHOICES)
    parameters = models.JSONField(_("معلمات التقرير"), default=dict, blank=True)
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="report_subscriptions",
        verbose_name=_("المستلمون"),
    )
    is_active = models.BooleanField(_("نشط"), default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="report_schedules_created",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("جدولة تقرير")
        verbose_name_plural = _("جدولات التقارير")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.report.title} ({self.get_frequency_display()})"
