"""
نماذج إدارة قواعد البيانات على طراز أودو
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import calendar
from datetime import timedelta

class Database(models.Model):
    """نموذج قاعدة البيانات الرئيسي"""

    DB_TYPES = [
        ('postgresql', 'PostgreSQL'),
    ]

    name = models.CharField(_('اسم قاعدة البيانات'), max_length=100)
    db_type = models.CharField(_('نوع قاعدة البيانات'), max_length=20, choices=DB_TYPES)
    connection_info = models.JSONField(_('معلومات الاتصال'), default=dict)
    is_active = models.BooleanField(_('نشطة'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('قاعدة بيانات')
        verbose_name_plural = _('قواعد البيانات')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def connection_string(self):
        """إنشاء سلسلة الاتصال"""
        if self.db_type == 'postgresql':
            host = self.connection_info.get('HOST', 'localhost')
            port = self.connection_info.get('PORT', '5432')
            name = self.connection_info.get('NAME', self.name)
            user = self.connection_info.get('USER', '')
            return f"postgresql://{user}@{host}:{port}/{name}"
        return ""

    @property
    def status(self):
        """حالة قاعدة البيانات"""
        if '_CREATED' in self.connection_info:
            return self.connection_info.get('_CREATED', False)
        return True

    @property
    def error_message(self):
        """رسالة الخطأ إن وجدت"""
        return self.connection_info.get('_ERROR', "")

    @property
    def size_display(self):
        """عرض حجم قاعدة البيانات بشكل مقروء"""
        # حساب حجم قاعدة البيانات من النسخ الاحتياطية
        total_size = sum(backup.size for backup in self.backups.all())

        # تحويل الحجم إلى وحدة مناسبة
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024.0:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024.0
        return f"{total_size:.1f} TB"

class Backup(models.Model):
    """نموذج النسخ الاحتياطي"""

    BACKUP_TYPES = [
        ('customers', 'بيانات العملاء'),
        ('users', 'بيانات المستخدمين'),
        ('settings', 'إعدادات النظام'),
        ('full', 'كل البيانات'),
    ]

    database = models.ForeignKey(
        Database,
        on_delete=models.CASCADE,
        related_name='backups',
        verbose_name=_('قاعدة البيانات')
    )
    name = models.CharField(_('اسم النسخة الاحتياطية'), max_length=100)
    file_path = models.CharField(_('مسار الملف'), max_length=255)
    size = models.BigIntegerField(_('الحجم (بايت)'), default=0)
    backup_type = models.CharField(
        _('نوع النسخة الاحتياطية'),
        max_length=20,
        choices=BACKUP_TYPES,
        default='full'
    )
    is_scheduled = models.BooleanField(_('مجدولة'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('تم الإنشاء بواسطة')
    )

    class Meta:
        verbose_name = _('نسخة احتياطية')
        verbose_name_plural = _('النسخ الاحتياطية')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def size_display(self):
        """عرض حجم النسخة الاحتياطية بشكل مقروء"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class BackupSchedule(models.Model):
    """نموذج جدولة النسخ الاحتياطية"""

    FREQUENCY_CHOICES = [
        ('hourly', _('كل ساعة')),
        ('daily', _('يومياً')),
        ('weekly', _('أسبوعياً')),
        ('monthly', _('شهرياً')),
    ]

    DAYS_OF_WEEK = [
        (0, _('الاثنين')),
        (1, _('الثلاثاء')),
        (2, _('الأربعاء')),
        (3, _('الخميس')),
        (4, _('الجمعة')),
        (5, _('السبت')),
        (6, _('الأحد')),
    ]

    database = models.ForeignKey(
        Database,
        on_delete=models.CASCADE,
        related_name='backup_schedules',
        verbose_name=_('قاعدة البيانات')
    )
    name = models.CharField(_('اسم الجدولة'), max_length=100)
    backup_type = models.CharField(
        _('نوع النسخة الاحتياطية'),
        max_length=20,
        choices=Backup.BACKUP_TYPES,
        default='full'
    )
    frequency = models.CharField(
        _('التكرار'),
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='daily'
    )

    # وقت التنفيذ
    hour = models.IntegerField(_('الساعة'), default=0, help_text=_('0-23'))
    minute = models.IntegerField(_('الدقيقة'), default=0, help_text=_('0-59'))

    # أيام الأسبوع (للتكرار الأسبوعي)
    day_of_week = models.IntegerField(
        _('يوم الأسبوع'),
        choices=DAYS_OF_WEEK,
        default=0,
        null=True,
        blank=True
    )

    # يوم الشهر (للتكرار الشهري)
    day_of_month = models.IntegerField(
        _('يوم الشهر'),
        default=1,
        help_text=_('1-31'),
        null=True,
        blank=True
    )

    # الحد الأقصى لعدد النسخ الاحتياطية
    max_backups = models.IntegerField(
        _('الحد الأقصى لعدد النسخ'),
        default=24,
        help_text=_('الحد الأقصى هو 24 نسخة')
    )

    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    last_run = models.DateTimeField(_('آخر تشغيل'), null=True, blank=True)
    next_run = models.DateTimeField(_('التشغيل القادم'), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('تم الإنشاء بواسطة'),
        related_name='backup_schedules'
    )

    class Meta:
        verbose_name = _('جدولة النسخ الاحتياطية')
        verbose_name_plural = _('جدولة النسخ الاحتياطية')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"

    def calculate_next_run(self):
        """حساب موعد التشغيل القادم"""
        now = timezone.now()

        # تعيين الساعة والدقيقة
        next_run = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)

        # إذا كان الوقت المحدد قد مر بالفعل، نضيف الفترة المناسبة
        if next_run <= now:
            if self.frequency == 'hourly':
                next_run = next_run.replace(hour=now.hour) + timedelta(hours=1)
            elif self.frequency == 'daily':
                next_run = next_run + timedelta(days=1)
            elif self.frequency == 'weekly':
                # حساب عدد الأيام حتى يوم الأسبوع المحدد
                days_ahead = self.day_of_week - now.weekday()
                if days_ahead <= 0:  # إذا كان اليوم المحدد قد مر هذا الأسبوع
                    days_ahead += 7
                next_run = next_run + timedelta(days=days_ahead)
            elif self.frequency == 'monthly':
                # الانتقال إلى الشهر التالي
                if now.month == 12:
                    next_month = 1
                    next_year = now.year + 1
                else:
                    next_month = now.month + 1
                    next_year = now.year

                # التعامل مع أيام الشهر غير الصالحة
                last_day = calendar.monthrange(next_year, next_month)[1]
                day = min(self.day_of_month, last_day)

                next_run = now.replace(year=next_year, month=next_month, day=day)

        self.next_run = next_run
        self.save(update_fields=['next_run'])
        return next_run
