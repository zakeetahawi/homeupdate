# دليل إنشاء تطبيق الإشعارات المنفصل

## هيكل التطبيق

```
notifications/
├── __init__.py
├── apps.py
├── models.py
├── views.py
├── urls.py
├── admin.py
├── services.py
├── signals.py
├── api_views.py
├── forms.py
├── serializers.py
├── middleware.py
├── templatetags/
│   ├── __init__.py
│   └── notification_tags.py
├── templates/
│   └── notifications/
│       ├── notification_list.html
│       ├── notification_detail.html
│       ├── notification_form.html
│       └── includes/
│           ├── notification_badge.html
│           └── notification_dropdown.html
├── static/
│   └── notifications/
│       ├── css/
│       │   └── notifications.css
│       └── js/
│           ├── notifications.js
│           └── realtime.js
└── migrations/
    └── __init__.py
```

## النماذج (models.py)

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

User = get_user_model()

class Notification(models.Model):
    """
    نموذج الإشعارات المحسن
    """
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    
    TYPE_CHOICES = [
        ('system', 'نظام'),
        ('order', 'طلب'),
        ('inspection', 'معاينة'),
        ('inventory', 'مخزون'),
        ('manufacturing', 'تصنيع'),
        ('customer', 'عميل'),
        ('custom', 'مخصص'),
    ]
    
    # معلومات أساسية
    title = models.CharField(max_length=200, verbose_name='العنوان')
    message = models.TextField(verbose_name='الرسالة')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    
    # المرسل والمستقبلون
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    recipients = models.ManyToManyField(User, related_name='received_notifications')
    
    # إعدادات متقدمة
    is_scheduled = models.BooleanField(default=False, verbose_name='مجدول')
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name='موعد الإرسال')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ انتهاء الصلاحية')
    
    # إحصائيات
    read_count = models.PositiveIntegerField(default=0, verbose_name='عدد القراء')
    total_recipients = models.PositiveIntegerField(default=0, verbose_name='إجمالي المستقبلين')
    
    # علاقات عامة
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # تواريخ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    
    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['priority']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['scheduled_for']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"
    
    def mark_as_read(self, user):
        """تحديد الإشعار كمقروء"""
        NotificationRead.objects.get_or_create(
            notification=self,
            user=user,
            defaults={'read_at': timezone.now()}
        )
        self.read_count = self.notification_reads.count()
        self.save(update_fields=['read_count'])
    
    def is_read_by(self, user):
        """التحقق من قراءة الإشعار"""
        return self.notification_reads.filter(user=user).exists()
    
    def is_expired(self):
        """التحقق من انتهاء صلاحية الإشعار"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_be_read(self):
        """التحقق من إمكانية قراءة الإشعار"""
        return not self.is_expired()


class NotificationRead(models.Model):
    """
    نموذج لتتبع قراءة الإشعارات
    """
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='notification_reads')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_reads')
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ القراءة')
    
    class Meta:
        unique_together = ['notification', 'user']
        verbose_name = 'قراءة إشعار'
        verbose_name_plural = 'قراءات الإشعارات'
    
    def __str__(self):
        return f"{self.user.username} قرأ {self.notification.title}"


class NotificationTemplate(models.Model):
    """
    نموذج قوالب الإشعارات
    """
    name = models.CharField(max_length=100, verbose_name='اسم القالب')
    title_template = models.CharField(max_length=200, verbose_name='قالب العنوان')
    message_template = models.TextField(verbose_name='قالب الرسالة')
    notification_type = models.CharField(max_length=20, choices=Notification.TYPE_CHOICES)
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    class Meta:
        verbose_name = 'قالب إشعار'
        verbose_name_plural = 'قوالب الإشعارات'
    
    def __str__(self):
        return self.name
    
    def render(self, context):
        """عرض القالب مع السياق"""
        from django.template import Template, Context
        title = Template(self.title_template).render(Context(context))
        message = Template(self.message_template).render(Context(context))
        return title, message


class NotificationSettings(models.Model):
    """
    إعدادات الإشعارات للمستخدمين
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')
    
    # إعدادات عامة
    email_notifications = models.BooleanField(default=True, verbose_name='إشعارات البريد الإلكتروني')
    push_notifications = models.BooleanField(default=True, verbose_name='الإشعارات الفورية')
    desktop_notifications = models.BooleanField(default=True, verbose_name='إشعارات سطح المكتب')
    
    # إعدادات حسب النوع
    system_notifications = models.BooleanField(default=True, verbose_name='إشعارات النظام')
    order_notifications = models.BooleanField(default=True, verbose_name='إشعارات الطلبات')
    inspection_notifications = models.BooleanField(default=True, verbose_name='إشعارات المعاينات')
    inventory_notifications = models.BooleanField(default=True, verbose_name='إشعارات المخزون')
    manufacturing_notifications = models.BooleanField(default=True, verbose_name='إشعارات التصنيع')
    customer_notifications = models.BooleanField(default=True, verbose_name='إشعارات العملاء')
    
    # إعدادات متقدمة
    quiet_hours_start = models.TimeField(null=True, blank=True, verbose_name='بداية الساعات الهادئة')
    quiet_hours_end = models.TimeField(null=True, blank=True, verbose_name='نهاية الساعات الهادئة')
    max_notifications_per_day = models.PositiveIntegerField(default=50, verbose_name='الحد الأقصى للإشعارات يومياً')
    
    class Meta:
        verbose_name = 'إعدادات الإشعارات'
        verbose_name_plural = 'إعدادات الإشعارات'
    
    def __str__(self):
        return f"إعدادات إشعارات {self.user.username}"
```

## الخدمات (services.py)

```python
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache
from .models import Notification, NotificationSettings

class NotificationService:
    """
    خدمة إدارة الإشعارات
    """
    
    @staticmethod
    def create_notification(title, message, sender, recipients, **kwargs):
        """
        إنشاء إشعار جديد
        """
        notification = Notification.objects.create(
            title=title,
            message=message,
            sender=sender,
            **kwargs
        )
        
        if isinstance(recipients, (list, tuple)):
            notification.recipients.add(*recipients)
        else:
            notification.recipients.add(recipients)
        
        notification.total_recipients = notification.recipients.count()
        notification.save(update_fields=['total_recipients'])
        
        # إرسال الإشعار الفوري
        NotificationService.send_realtime_notification(notification)
        
        return notification
    
    @staticmethod
    def send_realtime_notification(notification):
        """
        إرسال إشعار فوري عبر WebSocket
        """
        # سيتم تنفيذ هذا لاحقاً مع Django Channels
        pass
    
    @staticmethod
    def get_user_notifications(user, unread_only=False, limit=None):
        """
        الحصول على إشعارات المستخدم
        """
        cache_key = f"user_notifications_{user.id}_{unread_only}_{limit}"
        notifications = cache.get(cache_key)
        
        if notifications is None:
            queryset = Notification.objects.filter(recipients=user)
            
            if unread_only:
                queryset = queryset.exclude(notification_reads__user=user)
            
            notifications = list(queryset.order_by('-created_at'))
            
            if limit:
                notifications = notifications[:limit]
            
            cache.set(cache_key, notifications, 300)  # 5 دقائق
        
        return notifications
    
    @staticmethod
    def mark_as_read(notification, user):
        """
        تحديد إشعار كمقروء
        """
        notification.mark_as_read(user)
        
        # مسح التخزين المؤقت
        cache_keys = [
            f"user_notifications_{user.id}_False_None",
            f"user_notifications_{user.id}_True_None",
            f"user_notifications_{user.id}_False_5",
            f"user_notifications_{user.id}_True_5",
        ]
        
        for key in cache_keys:
            cache.delete(key)
    
    @staticmethod
    def get_notification_stats(user):
        """
        الحصول على إحصائيات الإشعارات
        """
        cache_key = f"notification_stats_{user.id}"
        stats = cache.get(cache_key)
        
        if stats is None:
            notifications = Notification.objects.filter(recipients=user)
            
            stats = {
                'total': notifications.count(),
                'unread': notifications.exclude(notification_reads__user=user).count(),
                'high_priority': notifications.filter(priority='high').exclude(
                    notification_reads__user=user
                ).count(),
                'urgent': notifications.filter(priority='urgent').exclude(
                    notification_reads__user=user
                ).count(),
            }
            
            cache.set(cache_key, stats, 300)
        
        return stats
```

## الإشارات (signals.py)

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import Notification, NotificationSettings
from .services import NotificationService

@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    """
    معالجة إشارة حفظ الإشعار
    """
    if created:
        # إرسال إشعار فوري
        NotificationService.send_realtime_notification(instance)
        
        # مسح التخزين المؤقت للمستقبلين
        for recipient in instance.recipients.all():
            cache_keys = [
                f"user_notifications_{recipient.id}_False_None",
                f"user_notifications_{recipient.id}_True_None",
                f"notification_stats_{recipient.id}",
            ]
            for key in cache_keys:
                cache.delete(key)

@receiver(post_save, sender=NotificationRead)
def notification_read_post_save(sender, instance, created, **kwargs):
    """
    معالجة إشارة قراءة الإشعار
    """
    if created:
        # مسح التخزين المؤقت
        cache_keys = [
            f"user_notifications_{instance.user.id}_False_None",
            f"user_notifications_{instance.user.id}_True_None",
            f"notification_stats_{instance.user.id}",
        ]
        for key in cache_keys:
            cache.delete(key)

# إشارات تلقائية للإشعارات
def create_order_notification(sender, instance, created, **kwargs):
    """
    إنشاء إشعار عند إنشاء طلب جديد
    """
    if created:
        NotificationService.create_notification(
            title=f'طلب جديد #{instance.id}',
            message=f'تم إنشاء طلب جديد للعميل {instance.customer.name}',
            sender=instance.created_by,
            recipients=[instance.created_by],  # يمكن تعديل هذا حسب الحاجة
            notification_type='order',
            priority='medium',
            content_object=instance
        )

def create_inspection_notification(sender, instance, created, **kwargs):
    """
    إنشاء إشعار عند إنشاء معاينة جديدة
    """
    if created:
        NotificationService.create_notification(
            title=f'معاينة جديدة #{instance.id}',
            message=f'تم إنشاء معاينة جديدة للعميل {instance.customer.name}',
            sender=instance.created_by,
            recipients=[instance.inspector] if instance.inspector else [instance.created_by],
            notification_type='inspection',
            priority='medium',
            content_object=instance
        )

def create_inventory_notification(sender, instance, created, **kwargs):
    """
    إنشاء إشعار عند انخفاض المخزون
    """
    if instance.current_stock <= instance.minimum_stock:
        NotificationService.create_notification(
            title=f'تنبيه مخزون - {instance.name}',
            message=f'المخزون الحالي للمنتج {instance.name} منخفض ({instance.current_stock})',
            sender=instance.created_by,
            recipients=User.objects.filter(is_staff=True),  # إرسال لجميع الموظفين
            notification_type='inventory',
            priority='high',
            content_object=instance
        )
```

## الواجهات (views.py)

```python
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Notification, NotificationSettings
from .services import NotificationService

@login_required
def notification_list(request):
    """
    عرض قائمة الإشعارات
    """
    filter_type = request.GET.get('filter', 'all')
    page_number = request.GET.get('page', 1)
    
    notifications = NotificationService.get_user_notifications(request.user)
    
    if filter_type == 'unread':
        notifications = [n for n in notifications if not n.is_read_by(request.user)]
    elif filter_type == 'read':
        notifications = [n for n in notifications if n.is_read_by(request.user)]
    
    paginator = Paginator(notifications, 20)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'stats': NotificationService.get_notification_stats(request.user)
    }
    
    return render(request, 'notifications/notification_list.html', context)

@login_required
def notification_detail(request, pk):
    """
    عرض تفاصيل الإشعار
    """
    notification = get_object_or_404(Notification, pk=pk, recipients=request.user)
    
    if not notification.is_read_by(request.user):
        NotificationService.mark_as_read(notification, request.user)
    
    context = {
        'notification': notification
    }
    
    return render(request, 'notifications/notification_detail.html', context)

@login_required
def mark_as_read_ajax(request, pk):
    """
    تحديد إشعار كمقروء عبر AJAX
    """
    if request.method == 'POST':
        notification = get_object_or_404(Notification, pk=pk, recipients=request.user)
        NotificationService.mark_as_read(notification, request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'تم تحديد الإشعار كمقروء'
        })
    
    return JsonResponse({'success': False, 'message': 'طريقة غير صالحة'})

@login_required
def mark_all_as_read(request):
    """
    تحديد جميع الإشعارات كمقروءة
    """
    if request.method == 'POST':
        unread_notifications = NotificationService.get_user_notifications(
            request.user, unread_only=True
        )
        
        for notification in unread_notifications:
            NotificationService.mark_as_read(notification, request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'تم تحديد {len(unread_notifications)} إشعار كمقروء'
        })
    
    return JsonResponse({'success': False, 'message': 'طريقة غير صالحة'})

class NotificationSettingsView(LoginRequiredMixin, CreateView):
    """
    عرض إعدادات الإشعارات
    """
    model = NotificationSettings
    template_name = 'notifications/notification_settings.html'
    fields = [
        'email_notifications', 'push_notifications', 'desktop_notifications',
        'system_notifications', 'order_notifications', 'inspection_notifications',
        'inventory_notifications', 'manufacturing_notifications', 'customer_notifications',
        'quiet_hours_start', 'quiet_hours_end', 'max_notifications_per_day'
    ]
    
    def get_object(self):
        """الحصول على إعدادات المستخدم أو إنشاء جديدة"""
        settings, created = NotificationSettings.objects.get_or_create(
            user=self.request.user
        )
        return settings
    
    def get_success_url(self):
        return reverse('notifications:settings')
```

## API Views (api_views.py)

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Notification
from .services import NotificationService
from .serializers import NotificationSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list_api(request):
    """
    API للحصول على قائمة الإشعارات
    """
    filter_type = request.GET.get('filter', 'all')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    
    notifications = NotificationService.get_user_notifications(
        request.user, 
        unread_only=(filter_type == 'unread'),
        limit=limit
    )
    
    serializer = NotificationSerializer(notifications, many=True)
    
    return Response({
        'notifications': serializer.data,
        'stats': NotificationService.get_notification_stats(request.user),
        'page': page,
        'has_next': len(notifications) == limit
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read_api(request, pk):
    """
    API لتحديد إشعار كمقروء
    """
    try:
        notification = Notification.objects.get(pk=pk, recipients=request.user)
        NotificationService.mark_as_read(notification, request.user)
        
        return Response({
            'success': True,
            'message': 'تم تحديد الإشعار كمقروء'
        })
    except Notification.DoesNotExist:
        return Response({
            'success': False,
            'message': 'الإشعار غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read_api(request):
    """
    API لتحديد جميع الإشعارات كمقروءة
    """
    unread_notifications = NotificationService.get_user_notifications(
        request.user, unread_only=True
    )
    
    for notification in unread_notifications:
        NotificationService.mark_as_read(notification, request.user)
    
    return Response({
        'success': True,
        'message': f'تم تحديد {len(unread_notifications)} إشعار كمقروء'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats_api(request):
    """
    API للحصول على إحصائيات الإشعارات
    """
    stats = NotificationService.get_notification_stats(request.user)
    
    return Response(stats)
```

## التطبيق في settings.py

```python
# إضافة التطبيق إلى INSTALLED_APPS
INSTALLED_APPS = [
    # ... التطبيقات الأخرى
    'notifications',
]

# إعدادات الإشعارات
NOTIFICATION_SETTINGS = {
    'DEFAULT_PRIORITY': 'medium',
    'MAX_NOTIFICATIONS_PER_USER': 1000,
    'CACHE_TIMEOUT': 300,  # 5 دقائق
    'REALTIME_ENABLED': True,
    'EMAIL_ENABLED': True,
    'PUSH_ENABLED': True,
}
```

## التطبيق في urls.py الرئيسي

```python
# إضافة مسارات الإشعارات
urlpatterns = [
    # ... المسارات الأخرى
    path('notifications/', include('notifications.urls')),
]
```

## ملف urls.py للتطبيق

```python
from django.urls import path
from . import views, api_views

app_name = 'notifications'

urlpatterns = [
    # المسارات العادية
    path('', views.notification_list, name='notification_list'),
    path('<int:pk>/', views.notification_detail, name='notification_detail'),
    path('<int:pk>/mark-read/', views.mark_as_read_ajax, name='mark_as_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('settings/', views.NotificationSettingsView.as_view(), name='settings'),
    
    # مسارات API
    path('api/', api_views.notification_list_api, name='api_list'),
    path('api/<int:pk>/mark-read/', api_views.mark_as_read_api, name='api_mark_read'),
    path('api/mark-all-read/', api_views.mark_all_as_read_api, name='api_mark_all_read'),
    path('api/stats/', api_views.notification_stats_api, name='api_stats'),
]
```

هذا الهيكل يوفر نظام إشعارات متكامل ومحسن مع:
- نماذج محسنة مع فهارس
- خدمات منفصلة للوظائف
- إشارات تلقائية
- API كامل
- تخزين مؤقت محسن
- إعدادات قابلة للتخصيص
- دعم الإشعارات الفورية (لاحقاً مع WebSocket) 