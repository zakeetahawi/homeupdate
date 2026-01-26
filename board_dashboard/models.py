from django.db import models


class BoardWidgetSettings(models.Model):
    """
    Settings for controlling the visibility and configuration of dashboard widgets.
    Allows admins to enable/disable widgets and set their order without code changes.
    """

    WIDGET_TYPES = [
        ("revenue_chart", "مخطط الإيرادات"),
        ("inventory_chart", "مخطط المخزون"),
        ("staff_performance", "أداء الموظفين"),
        ("debt_analytics", "تحليل الديون"),
        ("kpi_revenue", "KPI: الإيرادات"),
        ("kpi_cutting", "KPI: القص"),
        ("kpi_top_user", "KPI: أفضل موظف"),
    ]

    name = models.CharField(
        max_length=50, choices=WIDGET_TYPES, unique=True, verbose_name="اسم الودجت"
    )
    display_name = models.CharField(
        max_length=100, verbose_name="العنوان الظاهر", blank=True
    )
    is_active = models.BooleanField(default=True, verbose_name="مفعّل")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتيب العرض")
    config = models.JSONField(default=dict, blank=True, verbose_name="إعدادات إضافية")

    # Future-proofing: Thresholds (e.g., target revenue)
    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="القيمة المستهدفة",
    )

    class Meta:
        verbose_name = "إعداد ودجت اللوحة"
        verbose_name_plural = "إعدادات ودجت اللوحة"
        ordering = ["order"]

    def __str__(self):
        return self.get_name_display()
