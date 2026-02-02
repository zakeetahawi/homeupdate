"""
Views لنظام الرسائل الداخلية بين المستخدمين
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

# from django.contrib import messages as django_messages  # تم تعطيل رسائل Django
from .models import InternalMessage, User


@login_required
def inbox(request):
    """
    صندوق المحادثات (Unified Chat List) - عرض المحادثات مجمعة
    """
    # 1. العثور على جميع المستخدمين الذين حدث تواصل معهم (إرسالاً أو استقبالاً)
    sent_partners = InternalMessage.objects.filter(
        sender=request.user, is_deleted_by_sender=False
    ).values_list("recipient", flat=True)

    received_partners = InternalMessage.objects.filter(
        recipient=request.user, is_deleted_by_recipient=False
    ).values_list("sender", flat=True)

    # توحيد القوائم لإزالة التكرار
    partner_ids = set(list(sent_partners) + list(received_partners))

    conversations = []

    # 2. تجميع بيانات كل محادثة
    for partner_id in partner_ids:
        try:
            partner = User.objects.get(id=partner_id)
        except User.DoesNotExist:
            continue

        # آخر رسالة بين الطرفين (سواء واردة أو صادرة)
        last_message = (
            InternalMessage.objects.filter(
                (Q(sender=request.user) & Q(recipient=partner))
                | (Q(sender=partner) & Q(recipient=request.user))
            )
            .filter(
                ~Q(sender=request.user, is_deleted_by_sender=True)
                & ~Q(recipient=request.user, is_deleted_by_recipient=True)
            )
            .order_by("-created_at")
            .first()
        )

        if not last_message:
            continue

        # عدد الرسائل غير المقروءة الواردة من هذا الشريك
        unread_count = InternalMessage.objects.filter(
            sender=partner,
            recipient=request.user,
            is_read=False,
            is_deleted_by_recipient=False,
        ).count()

        conversations.append(
            {
                "sender": partner,  # We call it sender in template but it's really "partner"
                "last_message": last_message,
                "unread_count": unread_count,
                "timestamp": last_message.created_at,
            }
        )

    # 3. ترتيب المحادثات حسب تاريخ آخر رسالة (الأحدث أولاً)
    conversations.sort(key=lambda x: x["timestamp"], reverse=True)

    # Search Logic
    search_query = request.GET.get("search", "")
    if search_query:
        query = search_query.lower()
        conversations = [
            c
            for c in conversations
            if query in c["sender"].get_full_name().lower()
            or query in c["sender"].username.lower()
            or query in c["last_message"].subject.lower()
            or query in c["last_message"].body.lower()
        ]

    # Pagination
    paginator = Paginator(conversations, 20)
    page_number = request.GET.get("page")
    conversations_page = paginator.get_page(page_number)

    context = {
        "conversations": conversations_page,
        "unread_count": InternalMessage.get_unread_count(request.user),
        "search_query": search_query,
        "page_title": "المحادثات",
    }

    return render(request, "accounts/messages/inbox.html", context)


@login_required
def sent_messages(request):
    """صندوق الصادر - عرض الرسائل المرسلة"""
    messages_list = InternalMessage.get_sent_messages(request.user).order_by(
        "-created_at"
    )

    # البحث
    search_query = request.GET.get("search", "")
    if search_query:
        messages_list = messages_list.filter(
            Q(subject__icontains=search_query)
            | Q(body__icontains=search_query)
            | Q(recipient__username__icontains=search_query)
            | Q(recipient__first_name__icontains=search_query)
            | Q(recipient__last_name__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(messages_list, 20)
    page_number = request.GET.get("page")
    messages_page = paginator.get_page(page_number)

    context = {
        "messages": messages_page,
        "search_query": search_query,
        "page_title": "صندوق الصادر",
    }

    return render(request, "accounts/messages/sent.html", context)


@login_required
def compose_message(request):
    """إنشاء رسالة جديدة"""
    if request.method == "POST":
        recipient_id = request.POST.get("recipient")
        subject = request.POST.get("subject")
        body = request.POST.get("body")
        is_important = request.POST.get("is_important") == "on"

        # التحقق من صحة البيانات
        if not recipient_id or not subject or not body:
            # django_messages.error(request, 'جميع الحقول مطلوبة')
            return redirect("accounts:compose_message")

        try:
            recipient = User.objects.get(id=recipient_id)

            # إنشاء الرسالة
            message = InternalMessage.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=subject,
                body=body,
                is_important=is_important,
            )

            # django_messages.success(request, f'تم إرسال الرسالة إلى {recipient.get_full_name()} بنجاح')
            return redirect("accounts:sent_messages")

        except User.DoesNotExist:
            # django_messages.error(request, 'المستخدم المحدد غير موجود')
            return redirect("accounts:compose_message")

    # الحصول على قائمة المستخدمين النشطين (عدا المستخدم الحالي)
    users = (
        User.objects.filter(is_active=True)
        .exclude(id=request.user.id)
        .order_by("first_name", "last_name", "username")
    )

    # إذا كان هناك معرف مستخدم في الرابط (للرد)
    recipient_id = request.GET.get("to")
    selected_recipient = None
    if recipient_id:
        try:
            selected_recipient = User.objects.get(id=recipient_id, is_active=True)
        except User.DoesNotExist:
            pass

    context = {
        "users": users,
        "selected_recipient": selected_recipient,
        "page_title": "إنشاء رسالة جديدة",
    }

    return render(request, "accounts/messages/compose.html", context)


@login_required
def view_message(request, message_id):
    """عرض تفاصيل رسالة"""
    # التحقق من أن الرسالة تخص المستخدم الحالي (كمرسل أو مستلم)
    message = get_object_or_404(
        InternalMessage,
        Q(id=message_id) & (Q(sender=request.user) | Q(recipient=request.user)),
    )

    # تحديد الرسالة كمقروءة إذا كان المستخدم هو المستلم
    if message.recipient == request.user:
        message.mark_as_read()

    context = {"message": message, "page_title": message.subject}

    return render(request, "accounts/messages/view.html", context)


@login_required
@require_http_methods(["POST"])
def delete_message(request, message_id):
    """حذف رسالة (soft delete)"""
    message = get_object_or_404(
        InternalMessage,
        Q(id=message_id) & (Q(sender=request.user) | Q(recipient=request.user)),
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
        return redirect("accounts:sent_messages")
    else:
        return redirect("accounts:inbox")


@login_required
@require_http_methods(["POST"])
def mark_as_read(request, message_id):
    """تحديد رسالة كمقروءة"""
    message = get_object_or_404(InternalMessage, id=message_id, recipient=request.user)
    message.mark_as_read()

    return JsonResponse({"success": True, "message": "تم تحديد الرسالة كمقروءة"})


@login_required
@require_http_methods(["POST"])
def mark_all_as_read(request):
    """تحديد جميع الرسائل كمقروءة"""
    InternalMessage.objects.filter(
        recipient=request.user, is_read=False, is_deleted_by_recipient=False
    ).update(is_read=True, read_at=timezone.now())

    return JsonResponse({"success": True, "message": "تم تحديد جميع الرسائل كمقروءة"})


@login_required
def get_unread_count(request):
    """API للحصول على عدد الرسائل غير المقروءة"""
    count = InternalMessage.get_unread_count(request.user)
    return JsonResponse({"unread_count": count})


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
        online_users = (
            OnlineUser.get_online_users()
            .select_related("user")
            .exclude(user=request.user)  # استثناء المستخدم الحالي
        )

        users_data = []
        for online_user in online_users:
            user = online_user.user

            # حساب عدد الرسائل غير المقروءة من هذا المستخدم
            unread_from_user = InternalMessage.objects.filter(
                sender=user,
                recipient=request.user,
                is_read=False,
                is_deleted_by_recipient=False,
            ).count()

            # تحديد دور المستخدم
            user_role = "مستخدم عادي"
            if user.is_superuser:
                user_role = "مدير عام"
            elif user.is_staff:
                user_role = "موظف"
            elif hasattr(user, "get_user_role_display"):
                user_role = user.get_user_role_display()

            # تحديد الفرع
            user_branch = "غير محدد"
            if hasattr(user, "branch") and user.branch:
                user_branch = user.branch.name

            # الصورة الشخصية
            avatar_url = None
            if hasattr(user, "image") and user.image:
                try:
                    avatar_url = user.image.url
                except (ValueError, AttributeError):
                    avatar_url = None

            users_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.get_full_name() or user.username,
                    "role": user_role,
                    "branch": user_branch,
                    "is_online": online_user.is_online,
                    "last_seen": (
                        online_user.last_seen.isoformat()
                        if online_user.last_seen
                        else None
                    ),
                    "unread_messages": unread_from_user,
                    "avatar_url": avatar_url,
                }
            )

        return JsonResponse(
            {
                "users": users_data,
                "total_online": len(users_data),
                "total_unread": InternalMessage.get_unread_count(request.user),
            }
        )

    except Exception as e:
        # في حالة وجود خطأ، نرجع استجابة JSON فارغة بدلاً من خطأ 500
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_online_users_with_messages: {str(e)}")

        return JsonResponse(
            {
                "users": [],
                "total_online": 0,
                "total_unread": (
                    InternalMessage.get_unread_count(request.user)
                    if request.user.is_authenticated
                    else 0
                ),
                "error": "حدث خطأ في تحميل المستخدمين",
            }
        )


@login_required
def reply_to_message(request, message_id):
    """الرد على رسالة"""
    original_message = get_object_or_404(
        InternalMessage, id=message_id, recipient=request.user
    )

    if request.method == "POST":
        subject = request.POST.get("subject", f"Re: {original_message.subject}")
        body = request.POST.get("body")

        if not body:
            # django_messages.error(request, 'نص الرسالة مطلوب')
            return redirect("accounts:view_message", message_id=message_id)

        # إنشاء الرد
        reply = InternalMessage.objects.create(
            sender=request.user,
            recipient=original_message.sender,
            subject=subject,
            body=body,
            parent_message=original_message,
        )

        # django_messages.success(request, 'تم إرسال الرد بنجاح')
        return redirect("accounts:view_message", message_id=reply.id)

    context = {
        "original_message": original_message,
        "page_title": f"الرد على: {original_message.subject}",
    }

    return render(request, "accounts/messages/reply.html", context)


import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import InternalMessage, User


@login_required
def api_get_chat_history(request, user_id):
    """
    API لجلب سجل المحادثة مع مستخدم معين
    """
    other_user = get_object_or_404(User, id=user_id)

    # جلب الرسائل المتبادلة بين المستخدم الحالي والمستخدم الآخر
    messages = (
        InternalMessage.objects.filter(
            (Q(sender=request.user) & Q(recipient=other_user))
            | (Q(sender=other_user) & Q(recipient=request.user))
        )
        .filter(
            # استثناء الرسائل المحذوفة من قبل المستخدم الحالي
            ~Q(sender=request.user, is_deleted_by_sender=True)
            & ~Q(recipient=request.user, is_deleted_by_recipient=True)
        )
        .order_by("created_at")
    )

    # تحديد الرسائل الواردة كمقروءة وإرسال إشعارات بالقراءة
    # Use direct query to ensure we catch all unread messages from this user independent of the history limit/ordering
    unread_messages = InternalMessage.objects.filter(
        recipient=request.user, sender=other_user, is_read=False
    )

    if unread_messages.exists():
        print(
            f"DEBUG: Found {unread_messages.count()} unread messages in history fetch"
        )
        channel_layer = get_channel_layer()
        for msg in unread_messages:
            msg.mark_as_read()

            # Notify Sender (Read Receipt)
            try:
                print(
                    f"DEBUG: Sending Read Receipt for Msg {msg.id} to Sender {msg.sender.id}"
                )
                async_to_sync(channel_layer.group_send)(
                    f"user_{msg.sender.id}",
                    {
                        "type": "read_receipt",
                        "message_id": msg.id,
                        "sender_id": msg.sender.id,  # The one who sent the original message
                        "recipient_id": request.user.id,  # The one who just read it
                    },
                )
                # print("DEBUG: Read Receipt Sent Successfully to Group")
            except Exception as e:
                pass
                # print(f"DEBUG: Failed to send read receipt for msg {msg.id}: {e}")

    # تنسيق البيانات
    messages_data = []
    for msg in messages:
        messages_data.append(
            {
                "id": msg.id,
                "sender_id": msg.sender.id,
                "sender_name": msg.sender.get_full_name() or msg.sender.username,
                "sender_avatar": msg.sender.image.url if msg.sender.image else None,
                "body": msg.body,
                "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M"),
                "is_me": msg.sender == request.user,
                "is_read": msg.is_read,
            }
        )

    return JsonResponse(
        {
            "messages": messages_data,
            "other_user": {
                "id": other_user.id,
                "name": other_user.get_full_name() or other_user.username,
                "avatar_url": other_user.image.url if other_user.image else None,
            },
        }
    )


@login_required
@require_http_methods(["POST"])
def api_send_chat_message(request, user_id):
    """
    API لإرسال رسالة فورية عبر الدردشة
    """
    try:
        data = json.loads(request.body)
        body = data.get("body")

        if not body:
            return JsonResponse(
                {"success": False, "error": "نص الرسالة مطلوب"}, status=400
            )

        recipient = get_object_or_404(User, id=user_id)

        # إنشاء الرسالة
        message = InternalMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            subject="رسالة محادثة فورية",  # موضوع افتراضي للدردشة
            body=body,
            is_important=False,
        )

        # =========================================================
        # REAL-TIME PUSH: Notify the recipient instantly via WebSockets
        # =========================================================
        try:
            channel_layer = get_channel_layer()
            group_name = f"user_{recipient.id}"
            print(f"DEBUG: Sending message to Group: {group_name}")

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "chat_message",
                    "message": {
                        "id": message.id,
                        "sender_id": request.user.id,
                        "sender_name": request.user.get_full_name()
                        or request.user.username,
                        "sender_avatar": (
                            request.user.image.url if request.user.image else None
                        ),
                        "body": message.body,
                        "created_at": message.created_at.strftime("%Y-%m-%d %H:%M"),
                        "is_me": False,  # For the recipient, it's NOT me
                    },
                },
            )
            print("DEBUG: Message Pushed to Channel Layer")
        except Exception as e:
            print(f"DEBUG: WebSocket Push Failed: {e}")
            import traceback

            traceback.print_exc()

        return JsonResponse(
            {
                "success": True,
                "message": {
                    "id": message.id,
                    "body": message.body,
                    "created_at": message.created_at.strftime("%Y-%m-%d %H:%M"),
                    "sender_avatar": (
                        request.user.image.url if request.user.image else None
                    ),
                    "is_me": True,
                },
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "بيانات غير صالحة"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


from django.db.models import Count, Q


@login_required
def api_check_new_messages(request):
    """
    API للتحقق من وجود رسائل جديدة غير مقروءة من جميع المستخدمين
    يعيد قائمة بمعرفات المستخدمين وعدد الرسائل غير المقروءة لكل منهم
    """
    # تجميع الرسائل غير المقروءة حسب المرسل
    unread_stats = (
        InternalMessage.objects.filter(
            recipient=request.user, is_read=False, is_deleted_by_recipient=False
        )
        .values("sender")
        .annotate(count=Count("id"))
    )

    # تحويل النتيجة إلى قائمة
    unread_data = []
    for item in unread_stats:
        sender_id = item["sender"]
        count = item["count"]

        # نحتاج اسم المرسل أيضا للإشعار
        try:
            sender = User.objects.get(id=sender_id)
            sender_name = sender.get_full_name() or sender.username
        except User.DoesNotExist:
            sender_name = "مستخدم غير معروف"

        unread_data.append(
            {"sender_id": sender_id, "sender_name": sender_name, "count": count}
        )

    return JsonResponse(
        {
            "unread_conversations": unread_data,
            "total_unread": sum(item["count"] for item in unread_data),
        }
    )


@login_required
def api_recent_conversations(request):
    """
    API لجلب آخر المحادثات (للويدجت العائم)
    يعيد قائمة بالمحادثات مرتبة حسب الأحدث
    """
    # 1. تجميع معرفات المستخدمين الذين تواصلت معهم
    sent_partners = InternalMessage.objects.filter(
        sender=request.user, is_deleted_by_sender=False
    ).values_list("recipient", flat=True)

    received_partners = InternalMessage.objects.filter(
        recipient=request.user, is_deleted_by_recipient=False
    ).values_list("sender", flat=True)

    partner_ids = set(list(sent_partners) + list(received_partners))
    conversations_data = []

    for partner_id in partner_ids:
        # تجاوز المستخدم الحالي
        if partner_id == request.user.id:
            continue

        try:
            partner = User.objects.get(id=partner_id)
        except User.DoesNotExist:
            continue

        # آخر رسالة
        last_message = (
            InternalMessage.objects.filter(
                (Q(sender=request.user) & Q(recipient=partner))
                | (Q(sender=partner) & Q(recipient=request.user))
            )
            .filter(
                ~Q(sender=request.user, is_deleted_by_sender=True)
                & ~Q(recipient=request.user, is_deleted_by_recipient=True)
            )
            .order_by("-created_at")
            .first()
        )

        if not last_message:
            continue

        # عدد الرسائل غير المقروءة
        unread_count = InternalMessage.objects.filter(
            sender=partner,
            recipient=request.user,
            is_read=False,
            is_deleted_by_recipient=False,
        ).count()

        # الصورة
        avatar_url = None
        if hasattr(partner, "image") and partner.image:
            try:
                avatar_url = partner.image.url
            except:
                pass

        conversations_data.append(
            {
                "user_id": partner.id,
                "user_name": partner.get_full_name() or partner.username,
                "avatar_url": avatar_url,
                "last_message": (
                    last_message.body[:50] + "..."
                    if len(last_message.body) > 50
                    else last_message.body
                ),
                "timestamp": last_message.created_at,
                "timestamp_str": last_message.created_at.strftime(
                    "%Y-%m-%d %H:%M"
                ),  # Simplification for JSON
                "unread_count": unread_count,
            }
        )

    # الترتيب حسب الأحدث
    conversations_data.sort(key=lambda x: x["timestamp"], reverse=True)

    # تحويل التواريخ للنص النهائي
    for c in conversations_data:
        # تحسين عرض الوقت (مثلاً: "منذ دقيقة") يمكن أن يتم في الفرونت إند
        pass

    return JsonResponse({"conversations": conversations_data})
