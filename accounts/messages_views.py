"""
Views لنظام الرسائل الداخلية بين المستخدمين
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.views.decorators.http import require_http_methods
# from django.contrib import messages as django_messages  # تم تعطيل رسائل Django
from .models import InternalMessage, User
from django.core.paginator import Paginator


@login_required
def inbox(request):
    """صندوق الوارد - عرض الرسائل الواردة"""
    messages_list = InternalMessage.get_inbox(request.user).order_by('-created_at')
    
    # فلترة حسب الحالة (مقروءة/غير مقروءة)
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'unread':
        messages_list = messages_list.filter(is_read=False)
    elif status_filter == 'read':
        messages_list = messages_list.filter(is_read=True)
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query) |
            Q(body__icontains=search_query) |
            Q(sender__username__icontains=search_query) |
            Q(sender__first_name__icontains=search_query) |
            Q(sender__last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    # إحصائيات
    unread_count = InternalMessage.get_unread_count(request.user)
    
    context = {
        'messages': messages_page,
        'unread_count': unread_count,
        'status_filter': status_filter,
        'search_query': search_query,
        'page_title': 'صندوق الوارد'
    }
    
    return render(request, 'accounts/messages/inbox.html', context)


@login_required
def sent_messages(request):
    """صندوق الصادر - عرض الرسائل المرسلة"""
    messages_list = InternalMessage.get_sent_messages(request.user).order_by('-created_at')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query) |
            Q(body__icontains=search_query) |
            Q(recipient__username__icontains=search_query) |
            Q(recipient__first_name__icontains=search_query) |
            Q(recipient__last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    context = {
        'messages': messages_page,
        'search_query': search_query,
        'page_title': 'صندوق الصادر'
    }
    
    return render(request, 'accounts/messages/sent.html', context)


@login_required
def compose_message(request):
    """إنشاء رسالة جديدة"""
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        is_important = request.POST.get('is_important') == 'on'
        
        # التحقق من صحة البيانات
        if not recipient_id or not subject or not body:
            # django_messages.error(request, 'جميع الحقول مطلوبة')
            return redirect('accounts:compose_message')
        
        try:
            recipient = User.objects.get(id=recipient_id)
            
            # إنشاء الرسالة
            message = InternalMessage.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=subject,
                body=body,
                is_important=is_important
            )
            
            # django_messages.success(request, f'تم إرسال الرسالة إلى {recipient.get_full_name()} بنجاح')
            return redirect('accounts:sent_messages')
            
        except User.DoesNotExist:
            # django_messages.error(request, 'المستخدم المحدد غير موجود')
            return redirect('accounts:compose_message')
    
    # الحصول على قائمة المستخدمين النشطين (عدا المستخدم الحالي)
    users = User.objects.filter(is_active=True).exclude(id=request.user.id).order_by('first_name', 'last_name', 'username')
    
    # إذا كان هناك معرف مستخدم في الرابط (للرد)
    recipient_id = request.GET.get('to')
    selected_recipient = None
    if recipient_id:
        try:
            selected_recipient = User.objects.get(id=recipient_id, is_active=True)
        except User.DoesNotExist:
            pass
    
    context = {
        'users': users,
        'selected_recipient': selected_recipient,
        'page_title': 'إنشاء رسالة جديدة'
    }
    
    return render(request, 'accounts/messages/compose.html', context)


@login_required
def view_message(request, message_id):
    """عرض تفاصيل رسالة"""
    # التحقق من أن الرسالة تخص المستخدم الحالي (كمرسل أو مستلم)
    message = get_object_or_404(
        InternalMessage,
        Q(id=message_id) & (Q(sender=request.user) | Q(recipient=request.user))
    )
    
    # تحديد الرسالة كمقروءة إذا كان المستخدم هو المستلم
    if message.recipient == request.user:
        message.mark_as_read()
    
    context = {
        'message': message,
        'page_title': message.subject
    }
    
    return render(request, 'accounts/messages/view.html', context)


@login_required
@require_http_methods(["POST"])
def delete_message(request, message_id):
    """حذف رسالة (soft delete)"""
    message = get_object_or_404(
        InternalMessage,
        Q(id=message_id) & (Q(sender=request.user) | Q(recipient=request.user))
    )
    
    # حذف ناعم حسب دور المستخدم
    if message.sender == request.user:
        message.is_deleted_by_sender = True
    if message.recipient == request.user:
        message.is_deleted_by_recipient = True
    
    message.save()
    
    # حذف نهائي إذا تم الحذف من الطرفين
    if message.is_deleted_by_sender and message.is_deleted_by_recipient:
        message.delete()
        # django_messages.success(request, 'تم حذف الرسالة نهائياً')
    else:
        pass
        # django_messages.success(request, 'تم حذف الرسالة')
    
    # إرجاع المستخدم إلى الصفحة المناسبة
    if message.sender == request.user:
        return redirect('accounts:sent_messages')
    else:
        return redirect('accounts:inbox')


@login_required
@require_http_methods(["POST"])
def mark_as_read(request, message_id):
    """تحديد رسالة كمقروءة"""
    message = get_object_or_404(InternalMessage, id=message_id, recipient=request.user)
    message.mark_as_read()
    
    return JsonResponse({'success': True, 'message': 'تم تحديد الرسالة كمقروءة'})


@login_required
@require_http_methods(["POST"])
def mark_all_as_read(request):
    """تحديد جميع الرسائل كمقروءة"""
    InternalMessage.objects.filter(
        recipient=request.user,
        is_read=False,
        is_deleted_by_recipient=False
    ).update(is_read=True, read_at=timezone.now())
    
    return JsonResponse({'success': True, 'message': 'تم تحديد جميع الرسائل كمقروءة'})


@login_required
def get_unread_count(request):
    """API للحصول على عدد الرسائل غير المقروءة"""
    count = InternalMessage.get_unread_count(request.user)
    return JsonResponse({'unread_count': count})


@login_required
def get_online_users_with_messages(request):
    """
    API للحصول على المستخدمين النشطين مع عدد الرسائل غير المقروءة
    """
    try:
        from user_activity.models import OnlineUser
        
        # تنظيف المستخدمين غير المتصلين
        OnlineUser.cleanup_offline_users()
        
        # الحصول على المستخدمين النشطين
        online_users = OnlineUser.get_online_users().select_related('user').exclude(
            user=request.user  # استثناء المستخدم الحالي
        )
        
        users_data = []
        for online_user in online_users:
            user = online_user.user
            
            # حساب عدد الرسائل غير المقروءة من هذا المستخدم
            unread_from_user = InternalMessage.objects.filter(
                sender=user,
                recipient=request.user,
                is_read=False,
                is_deleted_by_recipient=False
            ).count()
            
            # تحديد دور المستخدم
            user_role = 'مستخدم عادي'
            if user.is_superuser:
                user_role = 'مدير عام'
            elif user.is_staff:
                user_role = 'موظف'
            elif hasattr(user, 'get_user_role_display'):
                user_role = user.get_user_role_display()
            
            # تحديد الفرع
            user_branch = 'غير محدد'
            if hasattr(user, 'branch') and user.branch:
                user_branch = user.branch.name
            
            # الصورة الشخصية
            avatar_url = None
            if hasattr(user, 'image') and user.image:
                try:
                    avatar_url = user.image.url
                except (ValueError, AttributeError):
                    avatar_url = None
            
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'role': user_role,
                'branch': user_branch,
                'is_online': online_user.is_online,
                'last_seen': online_user.last_seen.isoformat() if online_user.last_seen else None,
                'unread_messages': unread_from_user,
                'avatar_url': avatar_url
            })
        
        return JsonResponse({
            'users': users_data,
            'total_online': len(users_data),
            'total_unread': InternalMessage.get_unread_count(request.user)
        })
    
    except Exception as e:
        # في حالة وجود خطأ، نرجع استجابة JSON فارغة بدلاً من خطأ 500
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_online_users_with_messages: {str(e)}")
        
        return JsonResponse({
            'users': [],
            'total_online': 0,
            'total_unread': InternalMessage.get_unread_count(request.user) if request.user.is_authenticated else 0,
            'error': 'حدث خطأ في تحميل المستخدمين'
        })


@login_required
def reply_to_message(request, message_id):
    """الرد على رسالة"""
    original_message = get_object_or_404(InternalMessage, id=message_id, recipient=request.user)
    
    if request.method == 'POST':
        subject = request.POST.get('subject', f'Re: {original_message.subject}')
        body = request.POST.get('body')
        
        if not body:
            # django_messages.error(request, 'نص الرسالة مطلوب')
            return redirect('accounts:view_message', message_id=message_id)
        
        # إنشاء الرد
        reply = InternalMessage.objects.create(
            sender=request.user,
            recipient=original_message.sender,
            subject=subject,
            body=body,
            parent_message=original_message
        )
        
        # django_messages.success(request, 'تم إرسال الرد بنجاح')
        return redirect('accounts:view_message', message_id=reply.id)
    
    context = {
        'original_message': original_message,
        'page_title': f'الرد على: {original_message.subject}'
    }
    
    return render(request, 'accounts/messages/reply.html', context)

