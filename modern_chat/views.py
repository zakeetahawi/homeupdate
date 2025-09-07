from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.core.paginator import Paginator
import json
from .models import ChatRoom, Message, MessageRead, UserStatus

User = get_user_model()


# تم إزالة views الشاشة الكبيرة - نستخدم النافذة الصغيرة فقط


@login_required
@require_http_methods(["POST"])
def send_message(request):
    """إرسال رسالة جديدة"""
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to')
        
        if not content:
            return JsonResponse({'error': 'المحتوى مطلوب'}, status=400)
        
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        
        # إنشاء الرسالة
        message_data = {
            'room': room,
            'sender': request.user,
            'content': content,
            'message_type': 'text'
        }
        
        if reply_to_id:
            reply_to = get_object_or_404(Message, id=reply_to_id, room=room)
            message_data['reply_to'] = reply_to
        
        message = Message.objects.create(**message_data)
        
        # إرجاع بيانات الرسالة
        response_data = {
            'id': str(message.id),
            'content': message.content,
            'sender': {
                'id': message.sender.id,
                'name': message.sender.get_full_name() or message.sender.username,
                'avatar': getattr(message.sender, 'avatar', None)
            },
            'created_at': message.created_at.isoformat(),
            'reply_to': {
                'id': str(message.reply_to.id),
                'content': message.reply_to.content[:50],
                'sender': message.reply_to.sender.get_full_name() or message.reply_to.sender.username
            } if message.reply_to else None
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_messages(request, room_id):
    """الحصول على رسائل الغرفة (AJAX)"""
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    page = request.GET.get('page', 1)
    
    messages = Message.objects.filter(
        room=room,
        is_deleted=False
    ).select_related('sender', 'reply_to__sender').order_by('created_at')
    
    paginator = Paginator(messages, 50)
    page_obj = paginator.get_page(page)
    
    messages_data = []
    for message in page_obj:
        messages_data.append({
            'id': str(message.id),
            'content': message.content,
            'sender': {
                'id': message.sender.id,
                'name': message.sender.get_full_name() or message.sender.username,
                'is_current_user': message.sender == request.user
            },
            'created_at': message.created_at.isoformat(),
            'reply_to': {
                'id': str(message.reply_to.id),
                'content': message.reply_to.content[:50],
                'sender': message.reply_to.sender.get_full_name() or message.reply_to.sender.username
            } if message.reply_to else None
        })
    
    return JsonResponse({
        'messages': messages_data,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages
    })


@login_required
def create_private_chat(request, user_id):
    """إنشاء دردشة خاصة مع مستخدم - API فقط"""
    other_user = get_object_or_404(User, id=user_id)

    if other_user == request.user:
        return JsonResponse({'error': 'لا يمكن إنشاء دردشة مع نفسك'}, status=400)

    # البحث عن دردشة موجودة
    existing_room = ChatRoom.objects.filter(
        room_type='private',
        participants=request.user
    ).filter(
        participants=other_user
    ).first()

    if existing_room:
        return JsonResponse({
            'room_id': str(existing_room.id),
            'room_name': existing_room.name,
            'other_user': {
                'id': other_user.id,
                'name': other_user.get_full_name() or other_user.username,
                'username': other_user.username
            }
        })

    # إنشاء غرفة جديدة
    room_name = f'{request.user.get_full_name() or request.user.username} & {other_user.get_full_name() or other_user.username}'
    room = ChatRoom.objects.create(
        name=room_name,
        room_type='private',
        created_by=request.user
    )
    room.participants.add(request.user, other_user)

    return JsonResponse({
        'room_id': str(room.id),
        'room_name': room.name,
        'other_user': {
            'id': other_user.id,
            'name': other_user.get_full_name() or other_user.username,
            'username': other_user.username
        }
    })


@login_required
def get_active_users(request):
    """الحصول على المستخدمين النشطين"""
    try:
        # تحديث حالة المستخدم الحالي أولاً
        user_status, created = UserStatus.objects.get_or_create(user=request.user)
        user_status.status = 'online'
        user_status.save()

        # الحصول على المستخدمين النشطين
        active_users = User.objects.filter(
            chat_status__status__in=['online', 'away'],
            chat_status__last_seen__gte=timezone.now() - timezone.timedelta(minutes=10)
        ).exclude(id=request.user.id).select_related('chat_status')

        users_data = []
        for user in active_users:
            users_data.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'username': user.username,
                'status': user.chat_status.status if hasattr(user, 'chat_status') else 'offline',
                'last_seen': user.chat_status.last_seen.isoformat() if hasattr(user, 'chat_status') else timezone.now().isoformat(),
                'avatar': getattr(user, 'avatar', None)
            })

        return JsonResponse({
            'users': users_data,
            'count': len(users_data),
            'current_user_status': user_status.status
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'users': [],
            'count': 0
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_user_status(request):
    """تحديث حالة المستخدم"""
    try:
        data = json.loads(request.body)
        status = data.get('status', 'online')
        
        if status not in ['online', 'away', 'busy', 'offline']:
            return JsonResponse({'error': 'حالة غير صحيحة'}, status=400)
        
        user_status, created = UserStatus.objects.get_or_create(user=request.user)
        user_status.status = status
        user_status.save()
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def check_new_messages(request):
    """فحص الرسائل الجديدة للمستخدم"""
    try:
        # الحصول على آخر وقت فحص من الجلسة
        last_check = request.session.get('last_message_check', timezone.now() - timezone.timedelta(minutes=10))
        if isinstance(last_check, str):
            last_check = timezone.datetime.fromisoformat(last_check.replace('Z', '+00:00'))

        # البحث عن الرسائل الجديدة في غرف المستخدم
        user_rooms = ChatRoom.objects.filter(
            participants=request.user,
            is_active=True
        )

        new_messages = Message.objects.filter(
            room__in=user_rooms,
            created_at__gt=last_check,
            is_deleted=False
        ).exclude(sender=request.user)

        new_message_count = new_messages.count()

        # تحديث وقت آخر فحص
        request.session['last_message_check'] = timezone.now().isoformat()

        return JsonResponse({
            'has_new_messages': new_message_count > 0,
            'new_message_count': new_message_count,
            'last_check': last_check.isoformat() if last_check else None
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'has_new_messages': False,
            'new_message_count': 0
        }, status=500)


@login_required
def get_user_rooms(request):
    """الحصول على غرف المستخدم للنافذة الصغيرة"""
    try:
        user_rooms = ChatRoom.objects.filter(
            participants=request.user,
            is_active=True
        ).prefetch_related('messages', 'participants').annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time', '-updated_at')[:10]

        rooms_data = []
        for room in user_rooms:
            last_message = room.messages.filter(is_deleted=False).order_by('-created_at').first()
            unread_count = room.messages.filter(
                is_deleted=False,
                created_at__gt=timezone.now() - timezone.timedelta(hours=24)
            ).exclude(sender=request.user).count()

            rooms_data.append({
                'id': str(room.id),
                'name': room.name,
                'room_type': room.room_type,
                'last_message': {
                    'content': last_message.content,
                    'sender': last_message.sender.get_full_name() or last_message.sender.username,
                    'created_at': last_message.created_at.isoformat()
                } if last_message else None,
                'unread_count': unread_count,
                'participants_count': room.participants.count()
            })

        return JsonResponse({
            'rooms': rooms_data,
            'count': len(rooms_data)
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'rooms': [],
            'count': 0
        }, status=500)


@login_required
def get_user_info(request, user_id):
    """الحصول على معلومات المستخدم"""
    try:
        user = get_object_or_404(User, id=user_id)
        user_status = getattr(user, 'chat_status', None)

        return JsonResponse({
            'id': user.id,
            'name': user.get_full_name() or user.username,
            'username': user.username,
            'status': user_status.status if user_status else 'offline',
            'last_seen': user_status.last_seen.isoformat() if user_status else None,
            'avatar': getattr(user, 'avatar', None)
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@login_required
def mark_messages_read(request, room_id):
    """تحديد الرسائل كمقروءة"""
    try:
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

        # الحصول على الرسائل غير المقروءة
        unread_messages = Message.objects.filter(
            room=room,
            is_deleted=False
        ).exclude(sender=request.user).exclude(
            reads__user=request.user
        )

        # تحديد الرسائل كمقروءة
        for message in unread_messages:
            MessageRead.objects.get_or_create(
                message=message,
                user=request.user
            )

        return JsonResponse({
            'status': 'success',
            'marked_count': unread_messages.count()
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
