from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from model_utils.tracker import FieldTracker
import re

class InspectionEvaluation(models.Model):
    CRITERIA_CHOICES = [
        ('location', _('الموقع')),
        ('condition', _('الحالة')),
        ('suitability', _('الملاءمة')),
        ('safety', _('السلامة')),
        ('accessibility', _('سهولة الوصول')),
    ]
    RATING_CHOICES = [
        (1, _('ضعيف')),
        (2, _('مقبول')),
        (3, _('جيد')),
        (4, _('جيد جداً')),
        (5, _('ممتاز')),
    ]
    inspection = models.ForeignKey('Inspection', on_delete=models.CASCADE, related_name='evaluations', verbose_name=_('المعاينة'))
    criteria = models.CharField(_('معيار التقييم'), max_length=20, choices=CRITERIA_CHOICES)
    rating = models.IntegerField(_('التقييم'), choices=RATING_CHOICES)
    notes = models.TextField(_('ملاحظات التقييم'), blank=True)
    created_at = models.DateTimeField(_('تاريخ التقييم'), auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='evaluations_created', verbose_name=_('تم التقييم بواسطة')
    )
    class Meta:
        verbose_name = _('تقييم المعاينة')
        verbose_name_plural = _('تقييمات المعاينات')
        indexes = [
            models.Index(fields=['inspection'], name='inspection_eval_insp_idx'),
            models.Index(fields=['criteria'], name='inspection_eval_criteria_idx'),
            models.Index(fields=['rating'], name='inspection_eval_rating_idx'),
            models.Index(fields=['created_by'], name='inspection_eval_creator_idx'),
            models.Index(fields=['created_at'], name='inspection_eval_created_idx'),
        ]
    def __str__(self):
        return f"تقييم معاينة {self.inspection.contract_number}"

class InspectionNotification(models.Model):
    TYPE_CHOICES = [
        ('scheduled', _('موعد معاينة')),
        ('reminder', _('تذكير')),
        ('status_change', _('تغيير الحالة')),
        ('evaluation', _('تقييم جديد')),
    ]
    inspection = models.ForeignKey('Inspection', on_delete=models.CASCADE, related_name='notifications', verbose_name=_('المعاينة'))
    type = models.CharField(_('نوع التنبيه'), max_length=20, choices=TYPE_CHOICES)
    message = models.TextField(_('نص التنبيه'))
    is_read = models.BooleanField(_('تم القراءة'), default=False)
    created_at = models.DateTimeField(_('تاريخ التنبيه'), auto_now_add=True)
    scheduled_for = models.DateTimeField(_('موعد التنبيه'), null=True, blank=True)
    class Meta:
        verbose_name = _('تنبيه معاينة')
        verbose_name_plural = _('تنبيهات المعاينات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inspection'], name='inspection_notif_insp_idx'),
            models.Index(fields=['type'], name='inspection_notif_type_idx'),
            models.Index(fields=['is_read'], name='inspection_notif_read_idx'),
            models.Index(fields=['created_at'], name='inspection_notif_created_idx'),
            models.Index(fields=['scheduled_for'], name='inspection_notif_scheduled_idx'),
        ]
    def __str__(self):
        return f"تنبيه: {self.message[:50]}..."
    @property
    def is_scheduled(self):
        return bool(self.scheduled_for)

class InspectionReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('daily', _('يومي')),
        ('weekly', _('أسبوعي')),
        ('monthly', _('شهري')),
        ('custom', _('مخصص')),
    ]
    title = models.CharField(_('عنوان التقرير'), max_length=200)
    report_type = models.CharField(_('نوع التقرير'), max_length=10, choices=REPORT_TYPE_CHOICES)
    branch = models.ForeignKey(
        'accounts.Branch', on_delete=models.CASCADE, related_name='inspection_reports', verbose_name=_('الفرع')
    )
    date_from = models.DateField(_('من تاريخ'))
    date_to = models.DateField(_('إلى تاريخ'))
    total_inspections = models.IntegerField(_('إجمالي المعاينات'), default=0)
    successful_inspections = models.IntegerField(_('المعاينات الناجحة'), default=0)
    pending_inspections = models.IntegerField(_('المعاينات المعلقة'), default=0)
    cancelled_inspections = models.IntegerField(_('المعاينات الملغاة'), default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ إنشاء التقرير'), auto_now_add=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='inspection_reports_created', verbose_name=_('تم الإنشاء بواسطة')
    )
    class Meta:
        verbose_name = _('تقرير معاينات')
        verbose_name_plural = _('تقارير المعاينات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type'], name='inspection_report_type_idx'),
            models.Index(fields=['branch'], name='inspection_report_branch_idx'),
            models.Index(fields=['date_from'], name='inspection_report_from_idx'),
            models.Index(fields=['date_to'], name='inspection_report_to_idx'),
            models.Index(fields=['created_at'], name='inspection_report_created_idx'),
            models.Index(fields=['created_by'], name='inspection_report_creator_idx'),
        ]
    def __str__(self):
        return f"{self.title} - {self.get_report_type_display()}"
    def calculate_statistics(self):
        from django.core.cache import cache
        # إنشاء مفتاح تخزين مؤقت فريد بناءً على معلمات التقرير
        cache_key = f'inspection_report_stats_{self.branch_id}_{self.date_from}_{self.date_to}'
        # محاولة استرداد النتائج من التخزين المؤقت
        cached_stats = cache.get(cache_key)
        if cached_stats is None:
            # إذا لم تكن النتائج مخزنة مؤقتًا، قم بحساب الإحصائيات من قاعدة البيانات
            inspections = Inspection.objects.filter(
                branch=self.branch,
                request_date__gte=self.date_from,
                request_date__lte=self.date_to
            )
            self.total_inspections = inspections.count()
            self.successful_inspections = inspections.filter(result='passed').count()
            self.pending_inspections = inspections.filter(status='pending').count()
            self.cancelled_inspections = inspections.filter(status='cancelled').count()
            # حفظ النتائج في التخزين المؤقت لمدة ساعة واحدة (3600 ثانية)
            cached_stats = {
                'total': self.total_inspections,
                'successful': self.successful_inspections,
                'pending': self.pending_inspections,
                'cancelled': self.cancelled_inspections
            }
            cache.set(cache_key, cached_stats, 3600)
        else:
            # استخدام النتائج المخزنة مؤقتًا
            self.total_inspections = cached_stats['total']
            self.successful_inspections = cached_stats['successful']
            self.pending_inspections = cached_stats['pending']
            self.cancelled_inspections = cached_stats['cancelled']
        self.save()

class Inspection(models.Model):
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('scheduled', _('مجدول')),
        ('completed', _('مكتملة')),
        ('cancelled', _('ملغية')),
    ]
    RESULT_CHOICES = [
        ('passed', _('ناجحة')),
        ('failed', _('غير مجدية')),
    ]
    # إضافة متتبع الحقول
    tracker = FieldTracker(fields=['status', 'result'])
    contract_number = models.CharField(_('رقم العقد'), max_length=50, unique=True, blank=True, null=True)
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='inspections',
        verbose_name=_('العميل'),
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.PROTECT,
        related_name='inspections',
        verbose_name=_('الفرع'),
        null=True,
        blank=True
    )
    inspector = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_inspections',
        verbose_name=_('المعاين')
    )
    responsible_employee = models.ForeignKey(
        'accounts.Salesperson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('البائع'),
        related_name='inspections'
    )
    is_from_orders = models.BooleanField(_('من قسم الطلبات'), default=False)
    windows_count = models.IntegerField(_('عدد الشبابيك'), null=True, blank=True)
    inspection_file = models.FileField(_('ملف المعاينة'), upload_to='inspections/files/', null=True, blank=True)
    # حقول Google Drive
    google_drive_file_id = models.CharField(_('معرف ملف Google Drive'), max_length=255, blank=True, null=True)
    google_drive_file_url = models.URLField(_('رابط ملف Google Drive'), blank=True, null=True)
    google_drive_file_name = models.CharField(_('اسم الملف في Google Drive'), max_length=500, blank=True, null=True)
    is_uploaded_to_drive = models.BooleanField(_('تم الرفع إلى Google Drive'), default=False)
    request_date = models.DateField(_('تاريخ طلب المعاينة'))
    scheduled_date = models.DateField(_('تاريخ تنفيذ المعاينة'))
    status = models.CharField(
        _('الحالة'),
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    result = models.CharField(
        _('النتيجة'),
        max_length=10,
        choices=RESULT_CHOICES,
        null=True,
        blank=True
    )
    notes = models.TextField(_('ملاحظات'), blank=True)
    order_notes = models.TextField(_('ملاحظات الطلب'), blank=True, help_text=_('نسخة ثابتة من ملاحظات الطلب'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_inspections',
        verbose_name=_('تم الإنشاء بواسطة')
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inspections',
        verbose_name=_('الطلب المرتبط')
    )
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    completed_at = models.DateTimeField(_('تاريخ الإكتمال'), null=True, blank=True)
    class Meta:
        verbose_name = _('معاينة')
        verbose_name_plural = _('المعاينات')
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['contract_number'], name='inspection_contract_idx'),
            models.Index(fields=['customer'], name='inspection_customer_idx'),
            models.Index(fields=['branch'], name='inspection_branch_idx'),
            models.Index(fields=['inspector'], name='inspection_inspector_idx'),
            models.Index(fields=['status'], name='inspection_status_idx'),
            models.Index(fields=['result'], name='inspection_result_idx'),
            models.Index(fields=['request_date'], name='inspection_req_date_idx'),
            models.Index(fields=['scheduled_date'], name='inspection_sched_date_idx'),
            models.Index(fields=['order'], name='inspection_order_idx'),
            models.Index(fields=['created_at'], name='inspection_created_idx'),
        ]
    def __str__(self):
        customer_name = self.customer.name if self.customer else 'عميل جديد'
        return f"{self.contract_number} - {customer_name}"
    def clean(self):
        # Ensure scheduled date is not before request date
        if self.scheduled_date and self.request_date:
            if self.scheduled_date < self.request_date:
                raise ValidationError(_('تاريخ تنفيذ المعاينة لا يمكن أن يكون قبل تاريخ الطلب'))
        # Only allow users to create inspections in their branch
        if self.created_by and not self.created_by.is_superuser:
            if self.branch != self.created_by.branch:
                raise ValidationError(_('لا يمكنك إضافة معاينات لفرع آخر'))
    def save(self, *args, **kwargs):
        if not self.branch and self.created_by:
            self.branch = self.created_by.branch
        # تتبع التغييرات في حقل status
        status_changed = self.tracker.has_changed('status')
        old_status = self.tracker.previous('status')
        # Set completed_at when status changes to completed
        if status_changed and self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif status_changed and old_status == 'completed' and self.status != 'completed':
            self.completed_at = None
        # نسخ ملاحظات الطلب إلى الحقل الجديد إذا كان الطلب موجودًا
        if self.order and self.order.notes and not self.order_notes:
            self.order_notes = self.order.notes
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
        super().save(*args, **kwargs)
        # رفع تلقائي إلى Google Drive فقط إذا تغير الملف ولم يتم رفعه بعد
        if file_changed and self.inspection_file and not self.is_uploaded_to_drive:
            self.upload_to_google_drive_async()
    def get_status_color(self):
        status_colors = {
            'pending': 'warning',
            'scheduled': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return status_colors.get(self.status, 'secondary')
    @property
    def is_scheduled(self):
        return self.status == 'scheduled'
    @property
    def is_pending(self):
        return self.status == 'pending'
    @property
    def is_completed(self):
        return self.status == 'completed'
    @property
    def is_cancelled(self):
        return self.status == 'cancelled'
    @property
    def is_successful(self):
        return self.result == 'passed'
    @property
    def is_overdue(self):
        return self.status == 'pending' and self.scheduled_date < timezone.now().date()
    def generate_drive_filename(self):
        """توليد اسم الملف للرفع على Google Drive"""
        # اسم العميل (تنظيف الاسم من الرموز الخاصة)
        if self.customer and self.customer.name:
            customer_name = self.customer.name
        elif hasattr(self, 'customer_name') and self.customer_name:
            customer_name = self.customer_name
        else:
            customer_name = "عميل_جديد"
        customer_name = self._clean_filename(customer_name)
        # الفرع
        branch_name = self.branch.name if self.branch else "فرع_غير_محدد"
        branch_name = self._clean_filename(branch_name)
        # التاريخ
        date_str = self.scheduled_date.strftime("%Y-%m-%d") if self.scheduled_date else timezone.now().strftime("%Y-%m-%d")
        # رقم الطلب
        order_number = self.order.order_number if self.order else self.contract_number or "بدون_رقم"
        order_number = self._clean_filename(order_number)
        # تجميع اسم الملف
        filename = f"{customer_name}_{branch_name}_{date_str}_{order_number}.pdf"
        return filename
    def _clean_filename(self, name):
        """تنظيف اسم الملف من الرموز الخاصة"""
        # إزالة الرموز الخاصة والمسافات
        cleaned = re.sub(r'[^\w\u0600-\u06FF\s-]', '', str(name))
        # استبدال المسافات بـ underscore
        cleaned = re.sub(r'\s+', '_', cleaned)
        return cleaned[:50]  # تحديد الطول الأقصى
    def upload_to_google_drive_async(self):
        """رفع الملف إلى Google Drive بشكل تلقائي"""
        try:
            from inspections.services.google_drive_service import get_google_drive_service
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"بدء رفع ملف المعاينة {self.id} إلى Google Drive")
            # الحصول على خدمة Google Drive
            drive_service = get_google_drive_service()
            if not drive_service:
                logger.error("فشل في الحصول على خدمة Google Drive")
                return False
            # رفع الملف
            result = drive_service.upload_inspection_file(
                file_path=self.inspection_file.path,
                inspection=self
            )
            if result.get('success'):
                # تحديث بيانات المعاينة
                self.google_drive_file_id = result.get('file_id')
                self.google_drive_file_url = result.get('view_url')
                self.is_uploaded_to_drive = True
                # حفظ التحديثات في قاعدة البيانات
                try:
                    # تحديث قاعدة البيانات مباشرة
                    Inspection.objects.filter(id=self.id).update(
                        google_drive_file_id=self.google_drive_file_id,
                        google_drive_file_url=self.google_drive_file_url,
                        is_uploaded_to_drive=True
                    )
                    # إعادة تحميل الكائن من قاعدة البيانات للتأكد من التحديث
                    self.refresh_from_db()
                    logger.info(f"تم تحديث بيانات المعاينة {self.id} في قاعدة البيانات")
                except Exception as update_error:
                    logger.error(f"خطأ في تحديث قاعدة البيانات للمعاينة {self.id}: {str(update_error)}")
                logger.info(f"تم رفع ملف المعاينة {self.id} بنجاح إلى Google Drive")
                return True
            else:
                logger.error(f"فشل في رفع ملف المعاينة {self.id}: {result.get('message')}")
                return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في رفع ملف المعاينة {self.id} إلى Google Drive: {str(e)}")
            return False


# Signal to update order status when inspection is completed
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Inspection)
def update_order_status_on_inspection_completion(sender, instance, **kwargs):
    """
    Update order status to completed when inspection is completed
    """
    if instance.status == 'completed' and instance.order:
        try:
            # Update order status to completed
            instance.order.tracking_status = 'completed'
            instance.order.save(update_fields=['tracking_status'])

            # Log the status change
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"تم تحديث حالة الطلب {instance.order.id} إلى مكتمل بعد اكتمال المعاينة {instance.id}")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في تحديث حالة الطلب {instance.order.id} بعد اكتمال المعاينة: {str(e)}")

@receiver(post_save, sender=Inspection)
def update_order_status_on_inspection_change(sender, instance, **kwargs):
    """
    تحديث حالة الطلب بناءً على حالة المعاينة للطلبات من نوع معاينة
    """
    if instance.order and 'inspection' in instance.order.get_selected_types_list():
        try:
            # خريطة تحويل حالات المعاينة إلى حالات الطلب
            inspection_to_order_status = {
                'pending': 'pending',           # قيد الانتظار
                'scheduled': 'pending',         # مجدول -> قيد الانتظار
                'completed': 'completed',       # مكتملة -> مكتمل
                'cancelled': 'cancelled',       # ملغية -> ملغي
            }
            
            # خريطة تحويل حالات المعاينة إلى حالات التتبع
            inspection_to_tracking_status = {
                'pending': 'processing',        # قيد الانتظار -> قيد المعالجة
                'scheduled': 'processing',      # مجدول -> قيد المعالجة
                'completed': 'ready',           # مكتملة -> جاهز للتسليم
                'cancelled': 'pending',         # ملغية -> قيد الانتظار
            }
            
            # الحصول على الحالات الجديدة
            new_order_status = inspection_to_order_status.get(instance.status, 'pending')
            new_tracking_status = inspection_to_tracking_status.get(instance.status, 'processing')
            
            # تحديث حالة الطلب
            from orders.models import Order
            Order.objects.filter(pk=instance.order.pk).update(
                order_status=new_order_status,
                tracking_status=new_tracking_status
            )
            
            # تسجيل التحديث
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"تم تحديث حالة الطلب {instance.order.order_number} إلى {new_order_status} بناءً على حالة المعاينة {instance.status}")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في تحديث حالة الطلب {instance.order.id} بناءً على حالة المعاينة: {str(e)}")
