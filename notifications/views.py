from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

from .models import Notification, NotificationVisibility, NotificationSettings
from .serializers import NotificationSerializer, NotificationVisibilitySerializer
from .utils import get_user_notification_count, mark_notification_as_read, mark_all_notifications_as_read


class NotificationListView(LoginRequiredMixin, ListView):
    """صفحة قائمة الإشعارات"""
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        """الحصول على الإشعارات المرئية للمستخدم الحالي"""
        queryset = Notification.objects.for_user(self.request.user).select_related(
            'created_by', 'content_type'
        ).prefetch_related('visibility_records')

        # فلترة حسب النوع
        notification_type = self.request.GET.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        # فلترة حسب الأولوية
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        # فلترة حسب حالة القراءة
        read_status = self.request.GET.get('read')
        if read_status == 'unread':
            queryset = queryset.filter(
                visibility_records__user=self.request.user,
                visibility_records__is_read=False
            )
        elif read_status == 'read':
            queryset = queryset.filter(
                visibility_records__user=self.request.user,
                visibility_records__is_read=True
            )

        # البحث
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(message__icontains=search)
            )

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إضافة معلومات إضافية للسياق
        context.update({
            'notification_types': Notification.NOTIFICATION_TYPES,
            'priority_levels': Notification.PRIORITY_LEVELS,
            'current_type': self.request.GET.get('type', ''),
            'current_priority': self.request.GET.get('priority', ''),
            'current_read': self.request.GET.get('read', ''),
            'current_search': self.request.GET.get('search', ''),
            'unread_count': get_user_notification_count(self.request.user),
        })

        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """صفحة تفاصيل الإشعار"""
    model = Notification
    template_name = 'notifications/detail.html'
    context_object_name = 'notification'

    def get_queryset(self):
        """التأكد من أن المستخدم مصرح له برؤية الإشعار"""
        return Notification.objects.for_user(self.request.user)

    def get_object(self, queryset=None):
        """الحصول على الإشعار وتحديده كمقروء"""
        obj = super().get_object(queryset)

        # تحديد الإشعار كمقروء
        mark_notification_as_read(obj, self.request.user)

        return obj


@login_required
def mark_notification_read(request, pk):
    """تحديد إشعار كمقروء"""
    notification = get_object_or_404(
        Notification.objects.for_user(request.user),
        pk=pk
    )

    success = mark_notification_as_read(notification, request.user)

    if request.method == 'POST':
        if success:
            messages.success(request, _('تم تحديد الإشعار كمقروء'))
        else:
            messages.error(request, _('حدث خطأ أثناء تحديث الإشعار'))

        return redirect('notifications:list')
    else:
        # GET request - redirect to notification detail
        if success:
            messages.success(request, _('تم تحديد الإشعار كمقروء'))

        return redirect(notification.get_absolute_url())


@login_required
@require_POST
def mark_all_notifications_read(request):
    """تحديد جميع الإشعارات كمقروءة"""
    count = mark_all_notifications_as_read(request.user)

    messages.success(
        request,
        _('تم تحديد {} إشعار كمقروء').format(count)
    )

    return redirect('notifications:list')


@login_required
def notification_count_ajax(request):
    """الحصول على عدد الإشعارات غير المقروءة عبر AJAX"""
    count = get_user_notification_count(request.user)

    return JsonResponse({
        'success': True,
        'count': count
    })


@login_required
def recent_notifications_ajax(request):
    """الحصول على آخر الإشعارات عبر AJAX"""
    limit = int(request.GET.get('limit', 10))

    notifications = Notification.objects.recent_for_user(
        request.user, limit=limit
    ).select_related('created_by', 'content_type')

    notifications_data = []
    for notification in notifications:
        # الحصول على حالة القراءة
        try:
            visibility = NotificationVisibility.objects.get(
                notification=notification,
                user=request.user
            )
            is_read = visibility.is_read
        except NotificationVisibility.DoesNotExist:
            is_read = False

        notifications_data.append({
            'id': notification.pk,
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'type': notification.notification_type,
            'type_display': notification.get_notification_type_display(),
            'priority': notification.priority,
            'priority_display': notification.get_priority_display(),
            'icon_class': notification.get_icon_class(),
            'color_class': notification.get_color_class(),
            'is_read': is_read,
            'created_at': notification.created_at.isoformat(),
            'url': notification.get_absolute_url(),
        })

    return JsonResponse({
        'success': True,
        'notifications': notifications_data,
        'count': len(notifications_data)
    })


# ===== API Views =====

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API للإشعارات"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get_queryset(self):
        """الحصول على الإشعارات المرئية للمستخدم الحالي"""
        return Notification.objects.for_user(self.request.user).select_related(
            'created_by', 'content_type'
        ).prefetch_related('visibility_records')

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """الحصول على الإشعارات غير المقروءة"""
        notifications = Notification.objects.unread_for_user(request.user)
        serializer = self.get_serializer(notifications, many=True)

        return Response({
            'count': notifications.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def count(self, request):
        """الحصول على عدد الإشعارات غير المقروءة"""
        count = get_user_notification_count(request.user)

        return Response({
            'unread_count': count
        })

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """تحديد إشعار كمقروء"""
        notification = self.get_object()
        success = mark_notification_as_read(notification, request.user)

        return Response({
            'success': success,
            'message': _('تم تحديد الإشعار كمقروء') if success else _('حدث خطأ')
        })

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """تحديد جميع الإشعارات كمقروءة"""
        count = mark_all_notifications_as_read(request.user)

        return Response({
            'success': True,
            'count': count,
            'message': _('تم تحديد {} إشعار كمقروء').format(count)
        })
