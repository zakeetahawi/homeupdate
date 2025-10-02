"""
نماذج نظام النسخ الاحتياطي والاستعادة الجديد
"""

import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class BackupJob(models.Model):
    """نموذج مهام النسخ الاحتياطي"""

    STATUS_CHOICES = [
        ("pending", "في الانتظار"),
        ("running", "قيد التنفيذ"),
        ("completed", "مكتمل"),
        ("failed", "فشل"),
        ("cancelled", "ملغي"),
    ]

    TYPE_CHOICES = [
        ("full", "نسخة كاملة"),
        ("partial", "نسخة جزئية"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("اسم النسخة الاحتياطية", max_length=200)
    description = models.TextField("الوصف", blank=True)
    backup_type = models.CharField(
        "نوع النسخة", max_length=20, choices=TYPE_CHOICES, default="full"
    )

    # معلومات الملف
    file_path = models.CharField("مسار الملف", max_length=500, blank=True)
    file_size = models.BigIntegerField("حجم الملف (بايت)", default=0)
    compressed_size = models.BigIntegerField("الحجم المضغوط (بايت)", default=0)
    compression_ratio = models.FloatField("نسبة الضغط", default=0.0)

    # حالة المهمة
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    progress_percentage = models.FloatField("نسبة التقدم", default=0.0)
    current_step = models.CharField("الخطوة الحالية", max_length=200, blank=True)

    # إحصائيات
    total_records = models.IntegerField("إجمالي السجلات", default=0)
    processed_records = models.IntegerField("السجلات المعالجة", default=0)

    # رسائل الخطأ
    error_message = models.TextField("رسالة الخطأ", blank=True)

    # التواريخ
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    started_at = models.DateTimeField("تاريخ البدء", null=True, blank=True)
    completed_at = models.DateTimeField("تاريخ الانتهاء", null=True, blank=True)

    # المستخدم
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="أنشئ بواسطة"
    )

    class Meta:
        app_label = "backup_system"
        verbose_name = "مهمة نسخ احتياطي"
        verbose_name_plural = "مهام النسخ الاحتياطي"
        ordering = ["-created_at"]

    def __str__(self):
        return "{} - {}".format(self.name, self.get_status_display())

    @property
    def file_size_display(self):
        """عرض حجم الملف بشكل مقروء"""
        if self.file_size == 0:
            return "0 B"

        size = self.file_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return "{:.1f} {}".format(size, unit)
            size /= 1024.0
        return "{:.1f} PB".format(size)

    @property
    def compressed_size_display(self):
        """عرض الحجم المضغوط بشكل مقروء"""
        if self.compressed_size == 0:
            return "0 B"

        size = self.compressed_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return "{:.1f} {}".format(size, unit)
            size /= 1024.0
        return "{:.1f} PB".format(size)

    @property
    def space_saved_display(self):
        """عرض المساحة الموفرة بشكل مقروء"""
        if self.file_size > 0 and self.compressed_size > 0:
            saved = self.file_size - self.compressed_size
            if saved <= 0:
                return "0 B"

            size = saved
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if size < 1024.0:
                    return "{:.1f} {}".format(size, unit)
                size /= 1024.0
            return "{:.1f} PB".format(size)
        return "0 B"

    @property
    def duration(self):
        """مدة تنفيذ المهمة"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None

    def update_progress(self, percentage, step=None, processed_records=None):
        """تحديث تقدم المهمة"""
        self.progress_percentage = min(100.0, max(0.0, percentage))
        if step:
            self.current_step = step
        if processed_records is not None:
            self.processed_records = processed_records
        self.save(
            update_fields=["progress_percentage", "current_step", "processed_records"]
        )

    def mark_as_started(self):
        """تعيين المهمة كبدأت"""
        self.status = "running"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_as_completed(self, file_path, file_size, compressed_size):
        """تعيين المهمة كمكتملة"""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.progress_percentage = 100.0
        self.file_path = file_path
        self.file_size = file_size
        self.compressed_size = compressed_size
        if file_size > 0:
            self.compression_ratio = ((file_size - compressed_size) / file_size) * 100
        self.current_step = "تم بنجاح"
        self.save()

    def mark_as_failed(self, error_message):
        """تعيين المهمة كفاشلة"""
        self.status = "failed"
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.current_step = "فشل"
        self.save()


class RestoreJob(models.Model):
    """نموذج مهام الاستعادة"""

    STATUS_CHOICES = [
        ("pending", "في الانتظار"),
        ("running", "قيد التنفيذ"),
        ("completed", "مكتمل"),
        ("failed", "فشل"),
        ("cancelled", "ملغي"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("اسم الاستعادة", max_length=200)
    description = models.TextField("الوصف", blank=True)

    # معلومات الملف
    source_file = models.CharField("ملف المصدر", max_length=500)
    file_size = models.BigIntegerField("حجم الملف (بايت)", default=0)

    # خيارات الاستعادة
    clear_existing_data = models.BooleanField("حذف البيانات الموجودة", default=False)

    # حالة المهمة
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    progress_percentage = models.FloatField("نسبة التقدم", default=0.0)
    current_step = models.CharField("الخطوة الحالية", max_length=200, blank=True)

    # إحصائيات
    total_records = models.IntegerField("إجمالي السجلات", default=0)
    processed_records = models.IntegerField("السجلات المعالجة", default=0)
    success_records = models.IntegerField("السجلات الناجحة", default=0)
    failed_records = models.IntegerField("السجلات الفاشلة", default=0)

    # رسائل الخطأ
    error_message = models.TextField("رسالة الخطأ", blank=True)

    # التواريخ
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    started_at = models.DateTimeField("تاريخ البدء", null=True, blank=True)
    completed_at = models.DateTimeField("تاريخ الانتهاء", null=True, blank=True)

    # المستخدم
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="أنشئ بواسطة"
    )

    class Meta:
        app_label = "backup_system"
        verbose_name = "مهمة استعادة"
        verbose_name_plural = "مهام الاستعادة"
        ordering = ["-created_at"]

    def __str__(self):
        return "{} - {}".format(self.name, self.get_status_display())

    @property
    def file_size_display(self):
        """عرض حجم الملف بشكل مقروء"""
        if self.file_size == 0:
            return "0 B"

        size = self.file_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return "{:.1f} {}".format(size, unit)
            size /= 1024.0
        return "{:.1f} PB".format(size)

    @property
    def duration(self):
        """مدة تنفيذ المهمة"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None

    @property
    def success_rate(self):
        """نسبة النجاح"""
        if self.total_records == 0:
            return 0.0
        return (self.success_records / self.total_records) * 100

    def update_progress(
        self, percentage, step=None, processed=None, success=None, failed=None
    ):
        """تحديث تقدم المهمة"""
        self.progress_percentage = min(100.0, max(0.0, percentage))
        if step:
            self.current_step = step
        if processed is not None:
            self.processed_records = processed
        if success is not None:
            self.success_records = success
        if failed is not None:
            self.failed_records = failed
        self.save(
            update_fields=[
                "progress_percentage",
                "current_step",
                "processed_records",
                "success_records",
                "failed_records",
            ]
        )

    def mark_as_started(self):
        """تعيين المهمة كبدأت"""
        self.status = "running"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_as_completed(self):
        """تعيين المهمة كمكتملة"""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.progress_percentage = 100.0
        self.current_step = "تم بنجاح"
        self.save()

    def mark_as_failed(self, error_message):
        """تعيين المهمة كفاشلة"""
        self.status = "failed"
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.current_step = "فشل"
        self.save()


class BackupSchedule(models.Model):
    """نموذج جدولة النسخ الاحتياطية"""

    FREQUENCY_CHOICES = [
        ("daily", "يومياً"),
        ("weekly", "أسبوعياً"),
        ("monthly", "شهرياً"),
    ]

    name = models.CharField("اسم الجدولة", max_length=200)
    description = models.TextField("الوصف", blank=True)

    # إعدادات الجدولة
    frequency = models.CharField("التكرار", max_length=20, choices=FREQUENCY_CHOICES)
    hour = models.IntegerField("الساعة", default=2)  # 2 AM افتراضياً
    minute = models.IntegerField("الدقيقة", default=0)

    # إعدادات النسخة الاحتياطية
    backup_type = models.CharField(
        "نوع النسخة", max_length=20, choices=BackupJob.TYPE_CHOICES, default="full"
    )
    max_backups_to_keep = models.IntegerField("عدد النسخ المحفوظة", default=7)

    # حالة الجدولة
    is_active = models.BooleanField("نشط", default=True)
    last_run = models.DateTimeField("آخر تشغيل", null=True, blank=True)
    next_run = models.DateTimeField("التشغيل القادم", null=True, blank=True)

    # التواريخ
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التحديث", auto_now=True)

    # المستخدم
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="أنشئ بواسطة"
    )

    class Meta:
        app_label = "backup_system"
        verbose_name = "جدولة نسخ احتياطي"
        verbose_name_plural = "جدولة النسخ الاحتياطية"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
