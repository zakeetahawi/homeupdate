"""
إشارات نشاط المستخدمين
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import OnlineUser, UserActivityLog, UserLoginHistory, UserSession

User = get_user_model()


@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """معالجة تسجيل دخول المستخدم"""
    try:
        # إنشاء سجل تسجيل دخول
        UserLoginHistory.create_login_record(user, request, is_successful=True)

        # تحديث أو إنشاء سجل المستخدم النشط
        OnlineUser.update_user_activity(user, request)

        # تسجيل النشاط مع ضمان وجود قيم صالحة
        ip_address = OnlineUser.get_client_ip(request)
        UserActivityLog.log_activity(
            user=user,
            action_type="login",
            description=f"تسجيل دخول من {ip_address}",
            ip_address=ip_address,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            url_path=request.path if request.path else "/",
            http_method=request.method if request.method else "GET",
            success=True,
        )
    except Exception as e:
        print(f"خطأ في معالجة تسجيل الدخول: {e}")


@receiver(user_logged_out)
def handle_user_logout(sender, request, user, **kwargs):
    """معالجة تسجيل خروج المستخدم"""
    try:
        if user:
            # إنهاء سجل المستخدم النشط
            try:
                online_user = OnlineUser.objects.get(user=user)
                online_user.delete()
            except OnlineUser.DoesNotExist:
                pass

            # تحديث سجل تسجيل الدخول الأخير
            try:
                last_login = (
                    UserLoginHistory.objects.filter(user=user, logout_time__isnull=True)
                    .order_by("-login_time")
                    .first()
                )

                if last_login:
                    last_login.end_session("manual")
            except Exception:
                pass

            # تسجيل النشاط
            UserActivityLog.log_activity(
                user=user,
                action_type="logout",
                description=f'تسجيل خروج من {OnlineUser.get_client_ip(request) if request else "غير معروف"}',
                ip_address=OnlineUser.get_client_ip(request) if request else "0.0.0.0",
                user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
                url_path=request.path if request else "",
                http_method=request.method if request else "",
                success=True,
            )
    except Exception as e:
        print(f"خطأ في معالجة تسجيل الخروج: {e}")


# تم تعطيل تتبع تحديث المستخدم لأنه نشاط نظام وليس نشاط مستخدم
# @receiver(post_save, sender=User)
# def handle_user_update(sender, instance, created, **kwargs):
#     """معالجة تحديث بيانات المستخدم"""
#     ...


@receiver(pre_delete, sender=User)
def handle_user_deletion(sender, instance, **kwargs):
    """معالجة حذف المستخدم"""
    try:
        # تسجيل عملية الحذف قبل حذف المستخدم
        UserActivityLog.log_activity(
            user=instance,
            action_type="delete",
            entity_type="user",
            entity_id=instance.id,
            entity_name=instance.username,
            description=f"حذف المستخدم {instance.username}",
            ip_address="127.0.0.1",
            success=True,
        )

        # تنظيف سجلات المستخدم النشط
        OnlineUser.objects.filter(user=instance).delete()

    except Exception as e:
        print(f"خطأ في معالجة حذف المستخدم: {e}")
