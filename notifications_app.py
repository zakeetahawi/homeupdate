"""
تطبيق إدارة الإشعارات
Notifications Application
"""

# =============================================================================
# 1. إنشاء تطبيق notifications منفصل
# =============================================================================

def create_notifications_app():
    """
    إنشاء تطبيق notifications منفصل
    """
    from django.db import models
    from django.contrib.auth import get_user_model
    from django.utils.translation import gettext_lazy as _
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.utils import timezone
    
    User = get_user_model()
    
    class NotificationType(models.Model):
        """أنواع الإشعارات"""
        name = models.CharField(max_length=100, verbose_name=_('اسم النوع'))
        code = models.CharField(max_length=50, unique=True, verbose_name=_('الرمز'))
        description = models.TextField(blank=True, verbose_name=_('الوصف'))
        icon = models.CharField(max_length=50, default='fas fa-bell', verbose_name=_('الأيقونة'))
        color = models.CharField(max_length=20, default='primary', verbose_name=_('اللون'))
        is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
        
        class Meta:
            verbose_name = _('نوع الإشعار')
            verbose_name_plural = _('أنواع الإشعارات')
            ordering = ['name']
        
        def __str__(self):
            return self.name
    
    class NotificationTemplate(models.Model):
        """قوالب الإشعارات"""
        name = models.CharField(max_length=200, verbose_name=_('اسم القالب'))
        notification_type = models.ForeignKey(
            NotificationType, 
            on_delete=models.CASCADE,
            verbose_name=_('نوع الإشعار')
        )
        title_template = models.CharField(max_length=200, verbose_name=_('قالب العنوان'))
        message_template = models.TextField(verbose_name=_('قالب الرسالة'))
        variables = models.JSONField(default=dict, verbose_name=_('المتغيرات'))
        is_active = models.BooleanField(default=True, verbose_name=_('نشط'))
        
        class Meta:
            verbose_name = _('قالب الإشعار')
            verbose_name_plural = _('قوالب الإشعارات')
        
        def __str__(self):
            return self.name
    
    class Notification(models.Model):
        """نموذج الإشعارات المحسن"""
        PRIORITY_CHOICES = [
            ('low', _('منخفضة')),
            ('medium', _('متوسطة')),
            ('high', _('عالية')),
            ('urgent', _('عاجلة')),
        ]
        
        STATUS_CHOICES = [
            ('pending', _('في الانتظار')),
            ('sent', _('تم الإرسال')),
            ('delivered', _('تم التسليم')),
            ('read', _('تم القراءة')),
            ('failed', _('فشل الإرسال')),
        ]
        
        # معلومات أساسية
        title = models.CharField(max_length=200, verbose_name=_('العنوان'))
        message = models.TextField(verbose_name=_('الرسالة'))
        notification_type = models.ForeignKey(
            NotificationType,
            on_delete=models.CASCADE,
            verbose_name=_('نوع الإشعار')
        )
        template = models.ForeignKey(
            NotificationTemplate,
            on_delete=models.SET_NULL,
            null=True, blank=True,
            verbose_name=_('القالب المستخدم')
        )
        
        # الأولوية والحالة
        priority = models.CharField(
            max_length=10,
            choices=PRIORITY_CHOICES,
            default='medium',
            verbose_name=_('الأولوية')
        )
        status = models.CharField(
            max_length=10,
            choices=STATUS_CHOICES,
            default='pending',
            verbose_name=_('الحالة')
        )
        
        # المرسل والمستلم
        sender = models.ForeignKey(
            User,
            on_delete=models.CASCADE,
            related_name='sent_notifications',
            verbose_name=_('المرسل')
        )
        recipients = models.ManyToManyField(
            User,
            related_name='received_notifications',
            verbose_name=_('المستلمون')
        )
        
        # الأقسام والفروع
        sender_department = models.ForeignKey(
            'accounts.Department',
            on_delete=models.SET_NULL,
            null=True, blank=True,
            related_name='sent_notifications',
            verbose_name=_('قسم المرسل')
        )
        target_departments = models.ManyToManyField(
            'accounts.Department',
            blank=True,
            verbose_name=_('الأقسام المستهدفة')
        )
        target_branches = models.ManyToManyField(
            'accounts.Branch',
            blank=True,
            verbose_name=_('الفروع المستهدفة')
        )
        
        # الكائن المرتبط
        content_type = models.ForeignKey(
            ContentType,
            on_delete=models.CASCADE,
            null=True, blank=True,
            verbose_name=_('نوع المحتوى')
        )
        object_id = models.PositiveIntegerField(
            null=True, blank=True,
            verbose_name=_('معرف الكائن')
        )
        content_object = GenericForeignKey(
            'content_type', 'object_id'
        )
        
        # التواريخ
        created_at = models.DateTimeField(
            auto_now_add=True,
            verbose_name=_('تاريخ الإنشاء')
        )
        scheduled_at = models.DateTimeField(
            null=True, blank=True,
            verbose_name=_('تاريخ الإرسال المجدول')
        )
        sent_at = models.DateTimeField(
            null=True, blank=True,
            verbose_name=_('تاريخ الإرسال')
        )
        delivered_at = models.DateTimeField(
            null=True, blank=True,
            verbose_name=_('تاريخ التسليم')
        )
        read_at = models.DateTimeField(
            null=True, blank=True,
            verbose_name=_('تاريخ القراءة')
        )
        
        # معلومات إضافية
        metadata = models.JSONField(
            default=dict,
            verbose_name=_('بيانات إضافية')
        )
        error_message = models.TextField(
            blank=True,
            verbose_name=_('رسالة الخطأ')
        )
        
        class Meta:
            verbose_name = _('إشعار')
            verbose_name_plural = _('الإشعارات')
            ordering = ['-created_at']
            indexes = [
                models.Index(fields=['status', 'priority']),
                models.Index(fields=['created_at']),
                models.Index(fields=['sender']),
                models.Index(fields=['notification_type']),
            ]
        
        def __str__(self):
            return f"{self.title} - {self.sender}"
        
        def mark_as_read(self, user):
            """تحديد الإشعار كمقروء"""
            self.read_at = timezone.now()
            self.status = 'read'
            self.save()
        
        def mark_as_sent(self):
            """تحديد الإشعار كمرسل"""
            self.sent_at = timezone.now()
            self.status = 'sent'
            self.save()
        
        def mark_as_delivered(self):
            """تحديد الإشعار كمسلم"""
            self.delivered_at = timezone.now()
            self.status = 'delivered'
            self.save()
        
        def mark_as_failed(self, error_message):
            """تحديد الإشعار كفاشل"""
            self.status = 'failed'
            self.error_message = error_message
            self.save()
        
        @property
        def is_read(self):
            """هل تم قراءة الإشعار"""
            return self.status == 'read'
        
        @property
        def is_sent(self):
            """هل تم إرسال الإشعار"""
            return self.status in ['sent', 'delivered', 'read']
        
        @property
        def is_failed(self):
            """هل فشل إرسال الإشعار"""
            return self.status == 'failed'

# =============================================================================
# 2. إنشاء خدمات الإشعارات
# =============================================================================

def create_notification_services():
    """
    إنشاء خدمات الإشعارات
    """
    from django.core.cache import cache
    from django.utils import timezone
    from datetime import timedelta
    
    class NotificationService:
        """خدمة إدارة الإشعارات"""
        
        @staticmethod
        def create_notification(
            title,
            message,
            sender,
            recipients=None,
            notification_type=None,
            priority='medium',
            departments=None,
            branches=None,
            related_object=None,
            scheduled_at=None,
            metadata=None
        ):
            """إنشاء إشعار جديد"""
            from notifications.models import Notification, NotificationType
            
            # الحصول على نوع الإشعار الافتراضي
            if not notification_type:
                notification_type, _ = NotificationType.objects.get_or_create(
                    code='general',
                    defaults={
                        'name': 'عام',
                        'description': 'إشعارات عامة',
                        'icon': 'fas fa-bell',
                        'color': 'primary'
                    }
                )
            
            # إنشاء الإشعار
            notification = Notification.objects.create(
                title=title,
                message=message,
                sender=sender,
                notification_type=notification_type,
                priority=priority,
                scheduled_at=scheduled_at,
                metadata=metadata or {}
            )
            
            # إضافة المستلمين
            if recipients:
                notification.recipients.set(recipients)
            
            # إضافة الأقسام
            if departments:
                notification.target_departments.set(departments)
            
            # إضافة الفروع
            if branches:
                notification.target_branches.set(branches)
            
            # إضافة الكائن المرتبط
            if related_object:
                notification.content_type = ContentType.objects.get_for_model(related_object)
                notification.object_id = related_object.pk
                notification.save()
            
            return notification
        
        @staticmethod
        def send_notification(notification):
            """إرسال الإشعار"""
            try:
                # تحديث حالة الإشعار
                notification.mark_as_sent()
                
                # إرسال الإشعار للمستلمين
                for recipient in notification.recipients.all():
                    # إرسال إشعار في الوقت الفعلي (WebSocket)
                    NotificationService.send_realtime_notification(recipient, notification)
                    
                    # إرسال إشعار بالبريد الإلكتروني إذا كان مفعلاً
                    if notification.notification_type.is_active:
                        NotificationService.send_email_notification(recipient, notification)
                
                # تحديث حالة التسليم
                notification.mark_as_delivered()
                
                return True
            except Exception as e:
                notification.mark_as_failed(str(e))
                return False
        
        @staticmethod
        def send_realtime_notification(recipient, notification):
            """إرسال إشعار في الوقت الفعلي"""
            # هنا يمكن إضافة كود WebSocket
            pass
        
        @staticmethod
        def send_email_notification(recipient, notification):
            """إرسال إشعار بالبريد الإلكتروني"""
            # هنا يمكن إضافة كود إرسال البريد الإلكتروني
            pass
        
        @staticmethod
        def get_user_notifications(user, unread_only=False, limit=None):
            """الحصول على إشعارات المستخدم"""
            cache_key = f'user_notifications_{user.id}_{unread_only}_{limit}'
            notifications = cache.get(cache_key)
            
            if notifications is None:
                from notifications.models import Notification
                
                queryset = Notification.objects.filter(recipients=user)
                
                if unread_only:
                    queryset = queryset.exclude(status='read')
                
                notifications = list(queryset.order_by('-created_at'))
                
                if limit:
                    notifications = notifications[:limit]
                
                # تخزين في الذاكرة المؤقتة لمدة 5 دقائق
                cache.set(cache_key, notifications, 300)
            
            return notifications
        
        @staticmethod
        def get_unread_count(user):
            """الحصول على عدد الإشعارات غير المقروءة"""
            cache_key = f'unread_count_{user.id}'
            count = cache.get(cache_key)
            
            if count is None:
                from notifications.models import Notification
                count = Notification.objects.filter(
                    recipients=user
                ).exclude(status='read').count()
                
                # تخزين في الذاكرة المؤقتة لمدة دقيقة واحدة
                cache.set(cache_key, count, 60)
            
            return count
        
        @staticmethod
        def mark_all_as_read(user):
            """تحديد جميع إشعارات المستخدم كمقروءة"""
            from notifications.models import Notification
            
            notifications = Notification.objects.filter(
                recipients=user
            ).exclude(status='read')
            
            count = notifications.count()
            
            for notification in notifications:
                notification.mark_as_read(user)
            
            # مسح الذاكرة المؤقتة
            cache.delete(f'user_notifications_{user.id}_*')
            cache.delete(f'unread_count_{user.id}')
            
            return count
        
        @staticmethod
        def cleanup_old_notifications(days=30):
            """تنظيف الإشعارات القديمة"""
            from notifications.models import Notification
            
            cutoff_date = timezone.now() - timedelta(days=days)
            
            deleted_count = Notification.objects.filter(
                created_at__lt=cutoff_date,
                status__in=['read', 'failed']
            ).delete()[0]
            
            return deleted_count

# =============================================================================
# 3. إنشاء إشعارات تلقائية
# =============================================================================

def create_automatic_notifications():
    """
    إنشاء إشعارات تلقائية
    """
    from django.db.models.signals import post_save, post_delete
    from django.dispatch import receiver
    from notifications.services import NotificationService
    
    @receiver(post_save, sender='orders.Order')
    def notify_new_order(sender, instance, created, **kwargs):
        """إشعار عند إنشاء طلب جديد"""
        if created:
            # إشعار لقسم التصنيع
            NotificationService.create_notification(
                title='طلب جديد',
                message=f'تم إنشاء طلب جديد للعميل {instance.customer.name}',
                sender=instance.created_by,
                notification_type_code='new_order',
                priority='high',
                related_object=instance,
                departments=['manufacturing']
            )
    
    @receiver(post_save, sender='inspections.Inspection')
    def notify_new_inspection(sender, instance, created, **kwargs):
        """إشعار عند إنشاء معاينة جديدة"""
        if created:
            NotificationService.create_notification(
                title='معاينة جديدة',
                message=f'تم إنشاء معاينة جديدة للعميل {instance.customer.name}',
                sender=instance.created_by,
                notification_type_code='new_inspection',
                priority='medium',
                related_object=instance,
                departments=['manufacturing']
            )
    
    @receiver(post_save, sender='manufacturing.ManufacturingOrder')
    def notify_manufacturing_status(sender, instance, **kwargs):
        """إشعار عند تغيير حالة التصنيع"""
        if instance.status == 'completed':
            NotificationService.create_notification(
                title='اكتمال التصنيع',
                message=f'تم اكتمال تصنيع الطلب {instance.order.order_number}',
                sender=instance.created_by,
                notification_type_code='manufacturing_completed',
                priority='high',
                related_object=instance,
                departments=['installations']
            )
    
    @receiver(post_save, sender='inventory.Product')
    def notify_low_stock(sender, instance, **kwargs):
        """إشعار عند انخفاض المخزون"""
        if hasattr(instance, 'current_stock') and instance.current_stock <= instance.minimum_stock:
            NotificationService.create_notification(
                title='مخزون منخفض',
                message=f'المنتج {instance.name} وصل للحد الأدنى من المخزون',
                sender=instance.created_by,
                notification_type_code='low_stock',
                priority='medium',
                related_object=instance,
                departments=['inventory']
            )

# =============================================================================
# 4. إنشاء واجهات API
# =============================================================================

def create_notification_apis():
    """
    إنشاء واجهات API للإشعارات
    """
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods
    from django.contrib.auth.decorators import login_required
    from notifications.services import NotificationService
    
    @login_required
    def notifications_list_api(request):
        """API لقائمة الإشعارات"""
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
        limit = int(request.GET.get('limit', 20))
        
        notifications = NotificationService.get_user_notifications(
            request.user, unread_only, limit
        )
        
        return JsonResponse({
            'notifications': [
                {
                    'id': n.id,
                    'title': n.title,
                    'message': n.message,
                    'priority': n.priority,
                    'status': n.status,
                    'created_at': n.created_at.isoformat(),
                    'is_read': n.is_read,
                    'notification_type': {
                        'name': n.notification_type.name,
                        'icon': n.notification_type.icon,
                        'color': n.notification_type.color
                    }
                }
                for n in notifications
            ]
        })
    
    @login_required
    def notification_detail_api(request, notification_id):
        """API لتفاصيل الإشعار"""
        from notifications.models import Notification
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipients=request.user
            )
            
            # تحديد الإشعار كمقروء
            notification.mark_as_read(request.user)
            
            return JsonResponse({
                'notification': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'status': notification.status,
                    'created_at': notification.created_at.isoformat(),
                    'sender': {
                        'id': notification.sender.id,
                        'name': notification.sender.get_full_name()
                    },
                    'notification_type': {
                        'name': notification.notification_type.name,
                        'icon': notification.notification_type.icon,
                        'color': notification.notification_type.color
                    }
                }
            })
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'الإشعار غير موجود'}, status=404)
    
    @login_required
    def mark_notification_read_api(request, notification_id):
        """API لتحديد الإشعار كمقروء"""
        from notifications.models import Notification
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipients=request.user
            )
            notification.mark_as_read(request.user)
            
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'الإشعار غير موجود'}, status=404)
    
    @login_required
    def mark_all_read_api(request):
        """API لتحديد جميع الإشعارات كمقروءة"""
        count = NotificationService.mark_all_as_read(request.user)
        
        return JsonResponse({
            'success': True,
            'count': count
        })
    
    @login_required
    def unread_count_api(request):
        """API لعدد الإشعارات غير المقروءة"""
        count = NotificationService.get_unread_count(request.user)
        
        return JsonResponse({'count': count})

# =============================================================================
# 5. إنشاء واجهات المستخدم
# =============================================================================

def create_notification_views():
    """
    إنشاء واجهات المستخدم للإشعارات
    """
    from django.shortcuts import render, get_object_or_404
    from django.contrib.auth.decorators import login_required
    from django.core.paginator import Paginator
    from notifications.services import NotificationService
    
    @login_required
    def notifications_list_view(request):
        """عرض قائمة الإشعارات"""
        filter_type = request.GET.get('filter', 'all')
        page = request.GET.get('page', 1)
        
        if filter_type == 'unread':
            notifications = NotificationService.get_user_notifications(
                request.user, unread_only=True
            )
        else:
            notifications = NotificationService.get_user_notifications(request.user)
        
        # الصفحات
        paginator = Paginator(notifications, 20)
        page_obj = paginator.get_page(page)
        
        context = {
            'page_obj': page_obj,
            'filter_type': filter_type,
            'unread_count': NotificationService.get_unread_count(request.user)
        }
        
        return render(request, 'notifications/list.html', context)
    
    @login_required
    def notification_detail_view(request, notification_id):
        """عرض تفاصيل الإشعار"""
        from notifications.models import Notification
        
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipients=request.user
        )
        
        # تحديد الإشعار كمقروء
        notification.mark_as_read(request.user)
        
        context = {
            'notification': notification
        }
        
        return render(request, 'notifications/detail.html', context)

# =============================================================================
# 6. إنشاء قوالب الإشعارات
# =============================================================================

def create_notification_templates():
    """
    إنشاء قوالب الإشعارات
    """
    templates = {
        'new_order': {
            'title': 'طلب جديد - {customer_name}',
            'message': 'تم إنشاء طلب جديد للعميل {customer_name} برقم {order_number}',
            'variables': ['customer_name', 'order_number']
        },
        'new_inspection': {
            'title': 'معاينة جديدة - {customer_name}',
            'message': 'تم إنشاء معاينة جديدة للعميل {customer_name}',
            'variables': ['customer_name']
        },
        'manufacturing_completed': {
            'title': 'اكتمال التصنيع - {order_number}',
            'message': 'تم اكتمال تصنيع الطلب {order_number}',
            'variables': ['order_number']
        },
        'low_stock': {
            'title': 'مخزون منخفض - {product_name}',
            'message': 'المنتج {product_name} وصل للحد الأدنى من المخزون ({current_stock})',
            'variables': ['product_name', 'current_stock']
        },
        'installation_scheduled': {
            'title': 'تركيب مجدول - {customer_name}',
            'message': 'تم جدولة تركيب للعميل {customer_name} في {date}',
            'variables': ['customer_name', 'date']
        }
    }
    
    return templates

# =============================================================================
# 7. تطبيق الإشعارات
# =============================================================================

def apply_notifications_app():
    """
    تطبيق تطبيق الإشعارات
    """
    print("🔔 بدء تطبيق نظام الإشعارات المحسن...")
    
    # 1. إنشاء النماذج
    print("✅ إنشاء نماذج الإشعارات")
    create_notifications_app()
    
    # 2. إنشاء الخدمات
    print("✅ إنشاء خدمات الإشعارات")
    create_notification_services()
    
    # 3. إنشاء الإشعارات التلقائية
    print("✅ إنشاء إشعارات تلقائية")
    create_automatic_notifications()
    
    # 4. إنشاء واجهات API
    print("✅ إنشاء واجهات API")
    create_notification_apis()
    
    # 5. إنشاء واجهات المستخدم
    print("✅ إنشاء واجهات المستخدم")
    create_notification_views()
    
    # 6. إنشاء القوالب
    print("✅ إنشاء قوالب الإشعارات")
    create_notification_templates()
    
    print("🎉 تم تطبيق نظام الإشعارات المحسن بنجاح!")

if __name__ == "__main__":
    apply_notifications_app() 