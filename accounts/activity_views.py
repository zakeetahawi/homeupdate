"""
Views لنظام تتبع النشاط والمستخدمين النشطين
"""

import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import User
from user_activity.models import (
    OnlineUser,
    UserActivityLog,
    UserLoginHistory,
    UserSession,
)


@login_required
@require_http_methods(["GET"])
def online_users_api(request):
    """API لجلب المستخدمين النشطين حالياً والمستخدمين الذين تم تسجيل دخولهم سابقاً"""
    try:
        print(
            f"[DEBUG] Online users API called by user: {request.user if request.user.is_authenticated else 'Anonymous'}"
        )

        # تنظيف المستخدمين غير المتصلين
        OnlineUser.cleanup_offline_users()

        # جلب المستخدمين النشطين
        online_users = OnlineUser.get_online_users().select_related("user")
        online_user_ids = set(online_users.values_list("user_id", flat=True))
        total_online = online_users.count()

        print(f"[DEBUG] Found {total_online} online users")

        # التحقق من صلاحيات المستخدم
        user_is_admin = False
        if request.user.is_authenticated:
            user_is_admin = (
                request.user.is_superuser
                or request.user.is_staff
                or request.user.groups.filter(
                    name__in=["مدير النظام", "Admin", "Administrators"]
                ).exists()
            )

        print(f"[DEBUG] User is admin: {user_is_admin}")

        users_data = []

        # معالجة المستخدمين النشطين
        for online_user in online_users:
            try:
                print(f"[DEBUG] Processing online user: {online_user.user.username}")

                # تحديد دور المستخدم
                user_role = "مستخدم عادي"
                if online_user.user.is_superuser:
                    user_role = "👑 مدير عام"
                elif online_user.user.is_staff:
                    user_role = "⚙️ موظف"
                elif hasattr(online_user.user, "get_user_role_display"):
                    user_role = online_user.user.get_user_role_display()
                elif online_user.user.groups.exists():
                    user_role = f"👥 {online_user.user.groups.first().name}"

                # تحديد الفرع
                user_branch = "غير محدد"
                if hasattr(online_user.user, "branch") and online_user.user.branch:
                    user_branch = online_user.user.branch.name
                # إذا كان المستخدم بائع، نحاول العثور على فرعه من خلال نموذج Salesperson
                elif online_user.user.is_salesperson:
                    try:
                        from accounts.models import Salesperson

                        salesperson = Salesperson.objects.filter(
                            name=online_user.user.get_full_name()
                        ).first()
                        if salesperson and salesperson.branch:
                            user_branch = salesperson.branch.name
                    except Exception:
                        pass

                # جلب آخر تسجيل دخول
                last_login = (
                    UserLoginHistory.objects.filter(user=online_user.user)
                    .order_by("-login_time")
                    .first()
                )
                last_login_time = last_login.login_time if last_login else None

                # معلومات أساسية للجميع
                user_data = {
                    "id": online_user.user.id,
                    "username": online_user.user.username,
                    "full_name": online_user.user.get_full_name()
                    or online_user.user.username,
                    "role": user_role,
                    "branch": user_branch,
                    "is_online": online_user.is_online,  # استخدام خاصية النموذج بدلاً من True الثابت
                    "online_duration": (
                        online_user.online_duration_formatted
                        if online_user.is_online
                        else "غير متصل"
                    ),
                    "last_seen": (
                        online_user.last_seen.strftime("%H:%M")
                        if online_user.last_seen
                        else "غير محدد"
                    ),
                    "last_login": (
                        last_login_time.isoformat() if last_login_time else None
                    ),
                    "last_login_formatted": (
                        last_login_time.strftime("%Y-%m-%d %H:%M")
                        if last_login_time
                        else "غير محدد"
                    ),
                    "avatar_url": (
                        getattr(online_user.user, "image", None).url
                        if hasattr(online_user.user, "image") and online_user.user.image
                        else None
                    ),
                }

                # معلومات إضافية للمديرين فقط
                if user_is_admin:
                    user_data.update(
                        {
                            "current_page": online_user.current_page_title
                            or "غير محدد",
                            "pages_visited": online_user.pages_visited,
                            "actions_performed": online_user.actions_performed,
                            "device_info": online_user.device_info,
                            "ip_address": online_user.ip_address,
                        }
                    )

                users_data.append(user_data)
                # print(f"[DEBUG] Successfully processed online user: {online_user.user.username}")

            except Exception as user_error:
                print(
                    f"[ERROR] Error processing online user {online_user.user.username}: {user_error}"
                )
                continue

        # جلب المستخدمين الذين تم تسجيل دخولهم سابقاً ولكنهم غير متصلين الآن
        recent_login_users = (
            UserLoginHistory.objects.filter(
                login_time__gte=timezone.now() - timedelta(days=7)  # آخر أسبوع
            )
            .exclude(user_id__in=online_user_ids)
            .select_related("user")
            .order_by("-login_time")[:50]
        )  # جلب المزيد للتأكد من وجود مستخدمين مختلفين

        # الحصول على المستخدمين الفريدين
        seen_users = set()
        unique_recent_users = []
        for login_history in recent_login_users:
            if login_history.user_id not in seen_users:
                seen_users.add(login_history.user_id)
                unique_recent_users.append(login_history)
                if len(unique_recent_users) >= 20:  # أخذ أول 20 مستخدم فريد
                    break

        print(f"[DEBUG] Found {len(unique_recent_users)} recently logged in users")

        for login_history in unique_recent_users:
            try:
                user = login_history.user
                # print(f"[DEBUG] Processing offline user: {user.username}")

                # تحديد دور المستخدم
                user_role = "مستخدم عادي"
                if user.is_superuser:
                    user_role = "👑 مدير عام"
                elif user.is_staff:
                    user_role = "⚙️ موظف"
                elif hasattr(user, "get_user_role_display"):
                    user_role = user.get_user_role_display()
                elif user.groups.exists():
                    user_role = f"👥 {user.groups.first().name}"

                # تحديد الفرع
                user_branch = "غير محدد"
                if hasattr(user, "branch") and user.branch:
                    user_branch = user.branch.name
                # إذا كان المستخدم بائع، نحاول العثور على فرعه من خلال نموذج Salesperson
                elif user.is_salesperson:
                    try:
                        from accounts.models import Salesperson

                        salesperson = Salesperson.objects.filter(
                            name=user.get_full_name()
                        ).first()
                        if salesperson and salesperson.branch:
                            user_branch = salesperson.branch.name
                    except Exception:
                        pass

                # معلومات المستخدم غير المتصل
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.get_full_name() or user.username,
                    "role": user_role,
                    "branch": user_branch,
                    "is_online": False,
                    "online_duration": "غير متصل",
                    "last_seen": "غير متصل",
                    "last_login": login_history.login_time.isoformat(),
                    "last_login_formatted": login_history.login_time.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "avatar_url": (
                        getattr(user, "image", None).url
                        if hasattr(user, "image") and user.image
                        else None
                    ),
                }

                # معلومات إضافية للمديرين فقط
                if user_is_admin:
                    user_data.update(
                        {
                            "current_page": "غير متصل",
                            "pages_visited": 0,
                            "actions_performed": 0,
                            "device_info": "غير متصل",
                            "ip_address": login_history.ip_address or "غير محدد",
                        }
                    )

                users_data.append(user_data)
                # print(f"[DEBUG] Successfully processed offline user: {user.username}")

            except Exception as user_error:
                print(
                    f"[ERROR] Error processing offline user {login_history.user.username}: {user_error}"
                )
                continue

        # ترتيب المستخدمين: النشطين أولاً، ثم غير النشطين حسب آخر تسجيل دخول (الأحدث أولاً)
        # نُفضل التجميع الواضح بدل الاعتماد على reverse للوضوح
        online_list = [u for u in users_data if u.get("is_online")]
        offline_list = [u for u in users_data if not u.get("is_online")]

        # فرز القائمة غير المتصلة حسب last_login نزولياً (الأحدث أولاً)
        def _parse_login_key(item):
            # last_login مخزن كـ ISO string أو None
            return item.get("last_login") or ""

        offline_list.sort(key=_parse_login_key, reverse=True)

        users_data = online_list + offline_list

        # print(
        #     f"[DEBUG] Final response: success=True, total_users={len(users_data)}, online={total_online}"
        # )

        return JsonResponse(
            {
                "success": True,
                "users": users_data,
                "total_online": total_online,
                "total_users": len(users_data),
                "user_is_admin": user_is_admin,
                "timestamp": timezone.now().strftime("%H:%M:%S"),
            }
        )

    except Exception as e:
        print(f"[ERROR] Exception in online_users_api: {e}")
        import traceback

        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@staff_member_required
def user_activity_dashboard(request):
    """لوحة تحكم نشاط المستخدمين"""
    # إحصائيات عامة
    total_users = User.objects.count()
    online_users_count = OnlineUser.get_online_users().count()

    # إحصائيات اليوم
    today = timezone.now().date()
    today_logins = UserLoginHistory.objects.filter(login_time__date=today).count()

    today_activities = UserActivityLog.objects.filter(timestamp__date=today).count()

    # أكثر المستخدمين نشاطاً اليوم
    most_active_users = (
        User.objects.filter(activity_logs__timestamp__date=today)
        .annotate(activity_count=Count("activity_logs"))
        .order_by("-activity_count")[:10]
    )

    # أحدث الأنشطة (استبعاد عمليات تسجيل الدخول والخروج)
    recent_activities = (
        UserActivityLog.objects.select_related("user")
        .exclude(action_type__in=["login", "logout"])
        .order_by("-timestamp")[:20]
    )

    # المستخدمون النشطون
    online_users = OnlineUser.get_online_users().select_related("user")

    context = {
        "total_users": total_users,
        "online_users_count": online_users_count,
        "today_logins": today_logins,
        "today_activities": today_activities,
        "most_active_users": most_active_users,
        "recent_activities": recent_activities,
        "online_users": online_users,
    }

    return render(request, "accounts/activity_dashboard.html", context)


@staff_member_required
def user_activity_detail(request, user_id):
    """تفاصيل نشاط مستخدم معين"""
    user = get_object_or_404(User, id=user_id)

    # فلترة حسب التاريخ
    date_filter = request.GET.get("date", "today")
    if date_filter == "today":
        start_date = timezone.now().date()
        end_date = start_date
    elif date_filter == "week":
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
    elif date_filter == "month":
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = None
        end_date = None

    # جلب الأنشطة مع استبعاد الطلبات غير المرغوب فيها وعمليات تسجيل الدخول/الخروج
    activities = (
        UserActivityLog.objects.filter(user=user)
        .exclude(action_type__in=["login", "logout"])
        .exclude(url_path__contains="/accounts/notifications/data/")
        .exclude(url_path__contains="/media/users/")
        .exclude(url_path__startswith="/media/")
        .exclude(url_path__contains="/accounts/api/online-users/")
    )

    if start_date and end_date:
        activities = activities.filter(
            timestamp__date__gte=start_date, timestamp__date__lte=end_date
        )

    # فلترة حسب نوع النشاط
    activity_type = request.GET.get("type")
    if activity_type:
        activities = activities.filter(action_type=activity_type)

    # ترتيب وتقسيم الصفحات
    activities = activities.order_by("-timestamp")
    paginator = Paginator(activities, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # إحصائيات المستخدم
    user_stats = {
        "total_activities": activities.count(),
        "login_count": UserLoginHistory.objects.filter(user=user).count(),
        "last_login": UserLoginHistory.objects.filter(user=user)
        .order_by("-login_time")
        .first(),
        "is_online": hasattr(user, "activity_online_status")
        and user.activity_online_status.is_online,
    }

    # أنواع الأنشطة المتاحة للفلترة
    activity_types = UserActivityLog.ACTION_TYPES

    context = {
        "target_user": user,
        "activities": page_obj,
        "user_stats": user_stats,
        "activity_types": activity_types,
        "current_filters": {
            "date": date_filter,
            "type": activity_type,
        },
    }

    return render(request, "accounts/user_activity_detail.html", context)


@staff_member_required
def activity_logs_list(request):
    """قائمة جميع سجلات النشاط"""
    # فلاتر البحث
    search_query = request.GET.get("search", "")
    user_filter = request.GET.get("user")
    action_filter = request.GET.get("action")
    date_filter = request.GET.get("date", "today")

    # بناء الاستعلام مع استبعاد عمليات تسجيل الدخول والخروج
    activities = (
        UserActivityLog.objects.select_related("user")
        .exclude(action_type__in=["login", "logout"])
        .all()
    )

    # فلترة حسب البحث
    if search_query:
        activities = activities.filter(
            Q(user__username__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(url_path__icontains=search_query)
        )

    # فلترة حسب المستخدم
    if user_filter:
        activities = activities.filter(user_id=user_filter)

    # فلترة حسب نوع النشاط
    if action_filter:
        activities = activities.filter(action_type=action_filter)

    # فلترة حسب التاريخ
    if date_filter == "today":
        activities = activities.filter(timestamp__date=timezone.now().date())
    elif date_filter == "week":
        week_ago = timezone.now() - timedelta(days=7)
        activities = activities.filter(timestamp__gte=week_ago)
    elif date_filter == "month":
        month_ago = timezone.now() - timedelta(days=30)
        activities = activities.filter(timestamp__gte=month_ago)

    # ترتيب وتقسيم الصفحات
    activities = activities.order_by("-timestamp")
    paginator = Paginator(activities, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # بيانات للفلاتر
    users = User.objects.filter(activity_logs__isnull=False).distinct()
    action_types = UserActivityLog.ACTION_TYPES

    context = {
        "activities": page_obj,
        "users": users,
        "action_types": action_types,
        "current_filters": {
            "search": search_query,
            "user": user_filter,
            "action": action_filter,
            "date": date_filter,
        },
    }

    return render(request, "accounts/activity_logs_list.html", context)


@staff_member_required
def login_history_list(request):
    """قائمة سجلات تسجيل الدخول"""
    # فلاتر البحث
    user_filter = request.GET.get("user")
    date_filter = request.GET.get("date", "week")

    # بناء الاستعلام
    logins = UserLoginHistory.objects.select_related("user").all()

    # فلترة حسب المستخدم
    if user_filter:
        logins = logins.filter(user_id=user_filter)

    # فلترة حسب التاريخ
    if date_filter == "today":
        logins = logins.filter(login_time__date=timezone.now().date())
    elif date_filter == "week":
        week_ago = timezone.now() - timedelta(days=7)
        logins = logins.filter(login_time__gte=week_ago)
    elif date_filter == "month":
        month_ago = timezone.now() - timedelta(days=30)
        logins = logins.filter(login_time__gte=month_ago)

    # ترتيب وتقسيم الصفحات
    logins = logins.order_by("-login_time")
    paginator = Paginator(logins, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # بيانات للفلاتر
    users = User.objects.filter(login_history__isnull=False).distinct()

    context = {
        "logins": page_obj,
        "users": users,
        "current_filters": {
            "user": user_filter,
            "date": date_filter,
        },
    }

    return render(request, "accounts/login_history_list.html", context)


@login_required
@require_http_methods(["POST"])
def update_current_page(request):
    """تحديث الصفحة الحالية للمستخدم"""
    try:
        data = json.loads(request.body)
        page_path = data.get("page_path", "")
        page_title = data.get("page_title", "")

        # تحديث المستخدم المتصل
        online_user, created = OnlineUser.objects.get_or_create(
            user=request.user,
            defaults={
                "ip_address": request.META.get("REMOTE_ADDR", ""),
                "session_key": request.session.session_key,
                "login_time": timezone.now(),
            },
        )

        online_user.update_activity(page_path=page_path, page_title=page_title)

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def user_activities_api(request, user_id):
    """API لجلب آخر 5 نشاطات لمستخدم محدد"""
    try:
        print(f"[DEBUG] User activities API called for user: {user_id}")

        # التحقق من صلاحيات المستخدم
        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse(
                {"success": False, "error": "غير مصرح لك بعرض هذه المعلومات"},
                status=403,
            )

        # جلب المستخدم المطلوب
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "المستخدم غير موجود"}, status=404
            )

        # جلب آخر 5 نشاطات (استبعاد عمليات تسجيل الدخول والخروج)
        activities = (
            UserActivityLog.objects.filter(user=target_user)
            .exclude(action_type__in=["login", "logout"])
            .select_related("session")
            .order_by("-timestamp")[:5]
        )

        activities_data = []
        for activity in activities:
            # تحديد الأيقونة حسب نوع العملية
            icon_map = {
                "login": "fa-sign-in-alt",
                "logout": "fa-sign-out-alt",
                "view": "fa-eye",
                "create": "fa-plus",
                "update": "fa-edit",
                "delete": "fa-trash",
                "search": "fa-search",
                "export": "fa-download",
                "import": "fa-upload",
                "upload": "fa-cloud-upload-alt",
                "download": "fa-cloud-download-alt",
                "print": "fa-print",
                "email": "fa-envelope",
                "api_call": "fa-code",
                "error": "fa-exclamation-triangle",
                "security": "fa-shield-alt",
                "admin": "fa-cog",
                "report": "fa-chart-bar",
                "backup": "fa-save",
                "restore": "fa-undo",
                "maintenance": "fa-tools",
            }

            icon = icon_map.get(activity.action_type, "fa-circle")

            # إنشاء عنوان ووصف للنشاط مع روابط تفاعلية
            title = activity.action_type
            description = (
                f"{activity.entity_type}: {activity.entity_name or 'غير محدد'}"
            )
            link_url = None
            link_text = None

            if activity.action_type == "login":
                title = "تسجيل دخول"
                description = f"من {activity.session.ip_address if activity.session else 'غير محدد'}"
            elif activity.action_type == "logout":
                title = "تسجيل خروج"
                description = f"بعد {activity.session.duration if activity.session else 'غير محدد'}"
            elif activity.action_type == "view":
                title = "عرض صفحة"
                description = activity.entity_name or "صفحة غير محددة"
            elif activity.action_type == "create":
                title = "إنشاء"
                if activity.entity_type == "customer" or activity.entity_type == "عميل":
                    title = "إنشاء عميل جديد"
                    description = f"العميل: {activity.entity_name or 'جديد'}"
                    link_url = (
                        f"/complaints/customer/{activity.entity_id}/"
                        if activity.entity_id
                        else None
                    )
                    link_text = "عرض العميل"
                elif activity.entity_type == "order" or activity.entity_type == "طلب":
                    title = "إنشاء طلب جديد"
                    description = f"الطلب: {activity.entity_name or 'جديد'}"
                    link_url = (
                        f"/complaints/order/{activity.entity_id}/"
                        if activity.entity_id
                        else None
                    )
                    link_text = "عرض الطلب"
                else:
                    description = (
                        f"{activity.entity_type}: {activity.entity_name or 'جديد'}"
                    )
            elif activity.action_type == "update":
                title = "تحديث"
                if activity.entity_type == "customer" or activity.entity_type == "عميل":
                    title = "تحديث بيانات عميل"
                    description = f"العميل: {activity.entity_name or 'محدث'}"
                    link_url = (
                        f"/complaints/customer/{activity.entity_id}/"
                        if activity.entity_id
                        else None
                    )
                    link_text = "عرض العميل"
                elif activity.entity_type == "order" or activity.entity_type == "طلب":
                    title = "تحديث طلب"
                    description = f"الطلب: {activity.entity_name or 'محدث'}"
                    link_url = (
                        f"/complaints/order/{activity.entity_id}/"
                        if activity.entity_id
                        else None
                    )
                    link_text = "عرض الطلب"
                else:
                    description = (
                        f"{activity.entity_type}: {activity.entity_name or 'محدث'}"
                    )
            elif activity.action_type == "delete":
                title = "حذف"
                description = (
                    f"{activity.entity_type}: {activity.entity_name or 'محذوف'}"
                )
            elif activity.action_type == "upload" or activity.action_type == "download":
                if activity.action_type == "upload":
                    title = "رفع ملف"
                    description = f"الملف: {activity.entity_name or 'غير محدد'}"
                else:
                    title = "تحميل ملف"
                    description = f"الملف: {activity.entity_name or 'غير محدد'}"
                if activity.url_path and activity.url_path.startswith("/media/"):
                    link_url = activity.url_path
                    link_text = (
                        "عرض الملف"
                        if activity.action_type == "upload"
                        else "تحميل الملف"
                    )

            activities_data.append(
                {
                    "id": activity.id,
                    "action_type": activity.action_type,
                    "title": title,
                    "description": description,
                    "icon": icon,
                    "timestamp": activity.timestamp.isoformat(),
                    "entity_type": activity.entity_type,
                    "entity_name": activity.entity_name,
                    # لا نُرجع عنوان الـ IP في الـ API الخاص بالـ popup لأسباب خصوصية
                    "link_url": link_url,
                    "link_text": link_text,
                }
            )

        # Debug: number of activities collected
        # print(f"[DEBUG] Found {len(activities_data)} activities for user {user_id}")

        return JsonResponse(
            {
                "success": True,
                "activities": activities_data,
                "user": {
                    "id": target_user.id,
                    "username": target_user.username,
                    "full_name": target_user.get_full_name() or target_user.username,
                },
            }
        )

    except Exception as e:
        # print(f"[ERROR] User activities API error: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
