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
from core.mixins import PaginationFixMixin

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication

from django.contrib.auth import get_user_model
from .models import Notification, NotificationVisibility, NotificationSettings
from .serializers import NotificationSerializer, NotificationVisibilitySerializer
from .utils import get_user_notification_count, mark_notification_as_read, mark_all_notifications_as_read


class NotificationListView(PaginationFixMixin, LoginRequiredMixin, ListView):
    """صفحة قائمة الإشعارات"""
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    allow_empty = True  # السماح بالصفحات الفارغة دون رفع 404

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

        # فلترة حسب التاريخ
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        # فلترة حسب المستخدم المنشئ
        created_by = self.request.GET.get('created_by')
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        # البحث
        search = self.request.GET.get('search')
        if search:
            # البحث في العنوان والرسالة
            search_query = Q(title__icontains=search) | Q(message__icontains=search)
            
            # البحث في extra_data (JSON)
            # نبحث في القيم النصية في extra_data
            search_query |= Q(extra_data__icontains=search)
            
            queryset = queryset.filter(search_query)

        # إضافة visibility record لكل إشعار
        notifications = list(queryset.distinct())
        for notification in notifications:
            notification.user_visibility = notification.get_visibility_for_user(self.request.user)

        return notifications

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

        # إضافة المستخدمين الذين لديهم إشعارات
        User = get_user_model()
        users_with_notifications = User.objects.filter(
            id__in=Notification.objects.for_user(self.request.user).values('created_by').distinct()
        ).order_by('first_name', 'last_name', 'username')
        context['users_with_notifications'] = users_with_notifications

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
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🔔 محاولة تحديد الإشعار {pk} كمقروء للمستخدم {request.user.username}")

    notification = get_object_or_404(
        Notification.objects.for_user(request.user),
        pk=pk
    )

    success = mark_notification_as_read(notification, request.user)
    logger.info(f"📖 نتيجة تحديد الإشعار {pk}: {success}")

    # إذا كان AJAX request، إرجاع JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if success:
            return JsonResponse({
                'success': True,
                'message': 'تم تحديد الإشعار كمقروء',
                'notification_id': notification.pk,
                'user': request.user.get_full_name() or request.user.username
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'حدث خطأ أثناء تحديث الإشعار'
            }, status=400)

    # للطلبات العادية
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
def mark_all_notifications_read(request):
    """تحديد جميع الإشعارات كمقروءة"""

    # إذا كان GET request، اعرض صفحة تأكيد
    if request.method == 'GET':
        # عدد الإشعارات غير المقروءة
        from .utils import get_user_notification_count
        unread_count = get_user_notification_count(request.user)

        if unread_count == 0:
            messages.info(request, _('لا توجد إشعارات غير مقروءة'))
            return redirect('notifications:list')

        # عرض صفحة تأكيد
        context = {
            'unread_count': unread_count,
            'title': _('تحديد جميع الإشعارات كمقروءة')
        }
        return render(request, 'notifications/confirm_mark_all_read.html', context)

    # إذا كان POST request، قم بالتحديث
    elif request.method == 'POST':
        try:
            count = mark_all_notifications_as_read(request.user)

            message = _('تم تحديد {} إشعار كمقروء').format(count)

            # إذا كان الطلب AJAX، أرجع JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'count': count,
                    'message': message
                })

            # إذا كان طلب عادي، أضف رسالة وأعد التوجيه
            messages.success(request, message)
            return redirect('notifications:list')

        except Exception as e:
            error_message = _('حدث خطأ أثناء تحديث الإشعارات: {}').format(str(e))

            # إذا كان الطلب AJAX، أرجع JSON للخطأ
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=500)

            # إذا كان طلب عادي، أضف رسالة خطأ وأعد التوجيه
            messages.error(request, error_message)
            return redirect('notifications:list')

    # إذا كان method آخر، أرجع خطأ
    else:
        return JsonResponse({
            'success': False,
            'message': _('طريقة الطلب غير مدعومة')
        }, status=405)


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
    ).select_related('created_by', 'content_type').prefetch_related(
        'visibility_records'
    )

    notifications_data = []
    for notification in notifications:
        # الحصول على حالة القراءة من الـ prefetch
        visibility_records = [v for v in notification.visibility_records.all() if v.user == request.user]
        is_read = visibility_records[0].is_read if visibility_records else False

        # الحصول على بيانات الأيقونة واللون
        icon_data = notification.get_icon_and_color()

        notifications_data.append({
            'id': notification.pk,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'notification_type_display': notification.get_notification_type_display(),
            'priority': notification.priority,
            'priority_display': notification.get_priority_display(),
            'icon_class': icon_data['icon'],
            'color_class': icon_data['color'],
            'bg_color': icon_data['bg'],
            'is_read': is_read,
            'created_at': notification.created_at.isoformat(),
            'url': notification.get_absolute_url(),
            'created_by_name': notification.created_by.get_full_name() if notification.created_by else None,
            'extra_data': notification.extra_data,
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
