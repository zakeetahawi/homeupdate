from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse

User = get_user_model()


class NotificationManager(models.Manager):
    """مدير مخصص للإشعارات"""

    def for_user(self, user):
        """الحصول على الإشعارات المرئية للمستخدم"""
        return self.filter(visible_to=user)

    def unread_for_user(self, user):
        """الحصول على الإشعارات غير المقروءة للمستخدم"""
        return self.filter(visible_to=user, read_by__user=user, read_by__is_read=False).distinct()

    def recent_for_user(self, user, limit=10):
        """الحصول على آخر الإشعارات للمستخدم مع معلومات القراءة"""
        return self.for_user(user).prefetch_related(
            'visibility_records'
        ).order_by('-created_at')[:limit]


class Notification(models.Model):
    """نموذج الإشعارات الرئيسي"""

    NOTIFICATION_TYPES = [
        ('customer_created', _('عميل جديد')),
        ('order_created', _('طلب جديد')),
        ('order_updated', _('تعديل طلب')),
        ('order_status_changed', _('تغيير حالة طلب')),
        ('order_delivered', _('تسليم طلب')),
        ('installation_scheduled', _('جدولة تركيب')),
        ('installation_completed', _('إكمال تركيب')),
        ('inspection_created', _('معاينة جديدة')),
        ('inspection_status_changed', _('تغيير حالة معاينة')),
        ('manufacturing_status_changed', _('تغيير حالة أمر التصنيع')),
        ('complaint_created', _('شكوى جديدة')),
        # إشعارات التقطيع الجديدة
        ('cutting_order_created', _('أمر تقطيع جديد')),
        ('cutting_completed', _('اكتمال التقطيع')),
        ('cutting_item_rejected', _('رفض عنصر تقطيع')),
        ('stock_shortage', _('نقص في المخزون')),
        ('fabric_received', _('استلام أقمشة')),
        ('cutting_ready_for_pickup', _('جاهز للاستلام من التقطيع')),
    ]

    PRIORITY_LEVELS = [
        ('low', _('منخفضة')),
        ('normal', _('عادية')),
        ('high', _('عالية')),
        ('urgent', _('عاجلة')),
    ]

    # الحقول الأساسية
    title = models.CharField(
        _('العنوان'),
        max_length=200,
        help_text=_('عنوان قصير للإشعار')
    )

    message = models.TextField(
        _('الرسالة'),
        help_text=_('نص تفصيلي للإشعار')
    )

    notification_type = models.CharField(
        _('نوع الإشعار'),
        max_length=30,
        choices=NOTIFICATION_TYPES,
        db_index=True
    )

    priority = models.CharField(
        _('الأولوية'),
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='normal',
        db_index=True
    )

    # الكائن المرتبط (Generic Foreign Key)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('نوع المحتوى'),
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(
        _('معرف الكائن'),
        null=True,
        blank=True
    )
    related_object = GenericForeignKey('content_type', 'object_id')

    # المستخدم المنشئ
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_notifications',
        verbose_name=_('تم الإنشاء بواسطة')
    )

    # المستخدمون المصرح لهم برؤية الإشعار
    visible_to = models.ManyToManyField(
        User,
        through='NotificationVisibility',
        related_name='visible_notifications',
        verbose_name=_('مرئي لـ')
    )

    # التوقيتات
    created_at = models.DateTimeField(
        _('تاريخ الإنشاء'),
        auto_now_add=True,
        db_index=True
    )

    # بيانات إضافية (JSON)
    extra_data = models.JSONField(
        _('بيانات إضافية'),
        default=dict,
        blank=True,
        help_text=_('بيانات إضافية للإشعار في صيغة JSON')
    )

    objects = NotificationManager()

    class Meta:
        verbose_name = _('إشعار')
        verbose_name_plural = _('الإشعارات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"

    def get_absolute_url(self):
        """الحصول على رابط الإشعار"""
        # للإشعارات المرتبطة بالأقسام، توجيه لتفاصيل الطلب إذا كان متوفراً
        if self.notification_type in ['inspection_status_changed', 'manufacturing_status_changed', 'installation_completed', 'installation_scheduled']:
            # البحث عن رقم الطلب في extra_data
            if self.extra_data and 'order_number' in self.extra_data:
                try:
                    from orders.models import Order
                    order = Order.objects.get(order_number=self.extra_data['order_number'])
                    return order.get_absolute_url()
                except Order.DoesNotExist:
                    pass

            # إذا كان الكائن المرتبط له طلب
            if (self.related_object and
                hasattr(self.related_object, 'order') and
                self.related_object.order):
                return self.related_object.order.get_absolute_url()

        # للإشعارات الأخرى، استخدم الكائن المرتبط
        if self.related_object:
            # محاولة الحصول على رابط الكائن المرتبط
            if hasattr(self.related_object, 'get_absolute_url'):
                return self.related_object.get_absolute_url()
            elif hasattr(self.related_object, 'get_admin_url'):
                return self.related_object.get_admin_url()

        # رابط افتراضي لصفحة تفاصيل الإشعار
        return reverse('notifications:detail', kwargs={'pk': self.pk})

    def get_icon_and_color(self):
        """الحصول على أيقونة ولون الإشعار حسب النوع"""
        icon_map = {
            # إشعارات الطلبات
            'order_created': {'icon': 'fas fa-shopping-cart', 'color': '#2196f3', 'bg': '#e3f2fd'},
            'order_status_changed': {'icon': 'fas fa-exchange-alt', 'color': '#ff9800', 'bg': '#fff3e0'},
            'order_completed': {'icon': 'fas fa-check-circle', 'color': '#4caf50', 'bg': '#e8f5e8'},
            'order_delivered': {'icon': 'fas fa-truck', 'color': '#4caf50', 'bg': '#e8f5e8'},

            # إشعارات المعاينات
            'inspection_created': {'icon': 'fas fa-search', 'color': '#9c27b0', 'bg': '#f3e5f5'},
            'inspection_status_changed': {'icon': 'fas fa-clipboard-check', 'color': '#9c27b0', 'bg': '#f3e5f5'},
            'inspection_scheduled': {'icon': 'fas fa-calendar-check', 'color': '#9c27b0', 'bg': '#f3e5f5'},

            # إشعارات التصنيع
            'manufacturing_created': {'icon': 'fas fa-industry', 'color': '#607d8b', 'bg': '#eceff1'},
            'manufacturing_status_changed': {'icon': 'fas fa-cogs', 'color': '#607d8b', 'bg': '#eceff1'},
            'manufacturing_completed': {'icon': 'fas fa-check-double', 'color': '#607d8b', 'bg': '#eceff1'},

            # إشعارات التركيب
            'installation_scheduled': {'icon': 'fas fa-tools', 'color': '#795548', 'bg': '#efebe9'},
            'installation_completed': {'icon': 'fas fa-home', 'color': '#795548', 'bg': '#efebe9'},
            'installation_updated': {'icon': 'fas fa-wrench', 'color': '#795548', 'bg': '#efebe9'},

            # إشعارات العملاء
            'customer_created': {'icon': 'fas fa-user-plus', 'color': '#00bcd4', 'bg': '#e0f2f1'},
            'customer_updated': {'icon': 'fas fa-user-edit', 'color': '#00bcd4', 'bg': '#e0f2f1'},

            # إشعارات المدفوعات
            'payment_received': {'icon': 'fas fa-credit-card', 'color': '#4caf50', 'bg': '#e8f5e8'},
            'payment_pending': {'icon': 'fas fa-clock', 'color': '#ff9800', 'bg': '#fff3e0'},

            # إشعارات النظام
            'system_notification': {'icon': 'fas fa-bell', 'color': '#757575', 'bg': '#f5f5f5'},
            'user_notification': {'icon': 'fas fa-user', 'color': '#3f51b5', 'bg': '#e8eaf6'},

            # إشعارات التقطيع الجديدة
            'cutting_order_created': {'icon': 'fas fa-cut', 'color': '#6f42c1', 'bg': '#f3e5f5'},
            'cutting_completed': {'icon': 'fas fa-check-circle', 'color': '#28a745', 'bg': '#d4edda'},
            'cutting_item_rejected': {'icon': 'fas fa-times-circle', 'color': '#dc3545', 'bg': '#f8d7da'},
            'stock_shortage': {'icon': 'fas fa-exclamation-triangle', 'color': '#fd7e14', 'bg': '#fff3cd'},
            'fabric_received': {'icon': 'fas fa-industry', 'color': '#20c997', 'bg': '#d1ecf1'},
            'cutting_ready_for_pickup': {'icon': 'fas fa-hand-holding', 'color': '#17a2b8', 'bg': '#d1ecf1'},
        }

        return icon_map.get(self.notification_type, {
            'icon': 'fas fa-info-circle',
            'color': '#757575',
            'bg': '#f5f5f5'
        })

    def get_icon_class(self):
        """الحصول على فئة الأيقونة حسب نوع الإشعار"""
        icon_map = {
            'customer_created': 'fas fa-user-plus',
            'order_created': 'fas fa-shopping-cart',
            'order_updated': 'fas fa-edit',
            'order_status_changed': 'fas fa-exchange-alt',
            'order_delivered': 'fas fa-truck',
            'installation_scheduled': 'fas fa-calendar-plus',
            'installation_completed': 'fas fa-check-circle',
            'inspection_created': 'fas fa-search',
            'inspection_status_changed': 'fas fa-clipboard-check',
            'complaint_created': 'fas fa-exclamation-triangle',
        }
        return icon_map.get(self.notification_type, 'fas fa-bell')

    def get_color_class(self):
        """الحصول على فئة اللون حسب الأولوية"""
        color_map = {
            'low': 'text-muted',
            'normal': 'text-info',
            'high': 'text-warning',
            'urgent': 'text-danger',
        }
        return color_map.get(self.priority, 'text-info')


class NotificationVisibility(models.Model):
    """نموذج وسطي لتحديد رؤية الإشعارات للمستخدمين"""

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='visibility_records'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_visibility'
    )

    is_read = models.BooleanField(
        _('مقروء'),
        default=False,
        db_index=True
    )

    read_at = models.DateTimeField(
        _('تاريخ القراءة'),
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        _('تاريخ الإنشاء'),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _('رؤية الإشعار')
        verbose_name_plural = _('رؤية الإشعارات')
        unique_together = ['notification', 'user']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification', 'user']),
        ]

    def __str__(self):
        status = _('مقروء') if self.is_read else _('غير مقروء')
        return f"{self.notification.title} - {self.user.username} ({status})"

    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationSettings(models.Model):
    """إعدادات الإشعارات للمستخدمين"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name=_('المستخدم')
    )

    # إعدادات أنواع الإشعارات
    enable_customer_notifications = models.BooleanField(
        _('إشعارات العملاء'),
        default=True
    )

    enable_order_notifications = models.BooleanField(
        _('إشعارات الطلبات'),
        default=True
    )

    enable_inspection_notifications = models.BooleanField(
        _('إشعارات المعاينات'),
        default=True
    )

    enable_installation_notifications = models.BooleanField(
        _('إشعارات التركيبات'),
        default=True
    )

    enable_complaint_notifications = models.BooleanField(
        _('إشعارات الشكاوى'),
        default=True
    )

    # إعدادات الأولوية
    min_priority_level = models.CharField(
        _('الحد الأدنى لمستوى الأولوية'),
        max_length=10,
        choices=Notification.PRIORITY_LEVELS,
        default='low',
        help_text=_('لن يتم عرض الإشعارات أقل من هذا المستوى')
    )

    created_at = models.DateTimeField(
        _('تاريخ الإنشاء'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('تاريخ التحديث'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('إعدادات الإشعارات')
        verbose_name_plural = _('إعدادات الإشعارات')

    def __str__(self):
        return f"إعدادات إشعارات {self.user.username}"
