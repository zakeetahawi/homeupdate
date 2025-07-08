from django.db import models
from django.utils import timezone

class ManufacturingOrder(models.Model):
    order_number = models.CharField(max_length=50, unique=True, verbose_name="رقم الطلب")
    description = models.TextField(verbose_name="الوصف")
    start_date = models.DateTimeField(default=timezone.now, verbose_name="تاريخ البدء")
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإنجاز")
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'قيد الانتظار'),
            ('in_progress', 'قيد التنفيذ'),
            ('completed', 'مكتمل'),
            ('cancelled', 'ملغي')
        ],
        default='pending',
        verbose_name="الحالة"
    )

    class Meta:
        verbose_name = "طلب تصنيع"
        verbose_name_plural = "طلبات التصنيع"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.order_number} - {self.get_status_display()}"
