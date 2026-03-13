from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Department, Role, UserRole

User = get_user_model()


@receiver(post_save, sender=User)
def assign_default_departments(sender, instance, created, **kwargs):
    """
    Assign default departments to new users ONLY when created
    This should NOT run when updating existing users
    """
    # Log every time the signal is triggered
    print(f"📢 Signal triggered for user {instance.username} - created={created}")

    # Only assign default departments to NEW users
    # NOT when updating existing users
    if not created:
        print(
            f"⏭️ Skipping department assignment - user {instance.username} is being UPDATED, not created"
        )
        return

    print(
        f"🆕 New user detected: {instance.username} - will assign default departments"
    )

    # Use transaction.on_commit to delay database operations
    from django.db import transaction

    def assign_departments():
        try:
            # Only assign if user has NO departments already
            existing_depts = list(instance.departments.values_list("name", flat=True))
            if existing_depts:
                print(
                    f"⏭️ User {instance.username} already has departments: {', '.join(existing_depts)} - skipping default assignment"
                )
                return

            # Get the default departments
            default_departments = Department.objects.filter(
                Q(code="customers") | Q(code="orders")
            )

            if not default_departments.exists():
                print(f"⚠️ No default departments found (customers/orders)")
                return

            # Assign departments to user
            for dept in default_departments:
                instance.departments.add(dept)

            assigned_names = ", ".join([d.name for d in default_departments])
            print(
                f"✅ Default departments assigned to NEW user {instance.username}: {assigned_names}"
            )
        except Exception as e:
            print(f"❌ Error assigning default departments to {instance.username}: {e}")
            import traceback

            traceback.print_exc()

    transaction.on_commit(assign_departments)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """تسجيل دخول المستخدم"""
    try:
        from user_agents import parse

        from user_activity.models import OnlineUser, UserLoginHistory

        ip_address = request.META.get(
            "HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")
        )
        if "," in ip_address:
            ip_address = ip_address.split(",")[0].strip()

        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_ua = parse(user_agent)

        # إنشاء سجل تسجيل الدخول
        login_history = UserLoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=request.session.session_key or "",
            browser=f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}",
            operating_system=f"{parsed_ua.os.family} {parsed_ua.os.version_string}",
            device_type=(
                "mobile"
                if parsed_ua.is_mobile
                else "tablet" if parsed_ua.is_tablet else "desktop"
            ),
            is_successful_login=True,
        )

        # إنشاء أو تحديث المستخدم النشط
        from django.utils import timezone

        online_user, created = OnlineUser.objects.update_or_create(
            user=user,
            defaults={
                "ip_address": ip_address,
                "session_key": request.session.session_key or "",
                "login_time": timezone.now(),
                "device_info": {
                    "user_agent": user_agent,
                    "browser": f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}",
                    "os": f"{parsed_ua.os.family} {parsed_ua.os.version_string}",
                    "device_type": (
                        "mobile"
                        if parsed_ua.is_mobile
                        else "tablet" if parsed_ua.is_tablet else "desktop"
                    ),
                },
                "last_seen": timezone.now(),
                "current_page": request.path,
                "current_page_title": "تسجيل الدخول",
            },
        )

        print(f"✅ تم تسجيل دخول المستخدم: {user.username}")

    except Exception as e:
        print(f"❌ خطأ في تسجيل دخول المستخدم: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """تسجيل خروج المستخدم"""
    try:
        from django.utils import timezone

        from user_activity.models import OnlineUser, UserLoginHistory

        if user:
            # تحديث آخر سجل دخول
            try:
                login_history = (
                    UserLoginHistory.objects.filter(user=user, logout_time__isnull=True)
                    .order_by("-login_time")
                    .first()
                )

                if login_history:
                    login_history.logout_time = timezone.now()
                    login_history.logout_reason = "manual"
                    login_history.save()
            except Exception as e:
                print(f"خطأ في تحديث سجل الدخول: {e}")

            # حذف المستخدم من قائمة النشطين
            try:
                OnlineUser.objects.filter(user=user).delete()
            except Exception as e:
                print(f"خطأ في حذف المستخدم النشط: {e}")

            print(f"✅ تم تسجيل خروج المستخدم: {user.username}")

    except Exception as e:
        print(f"❌ خطأ في تسجيل خروج المستخدم: {e}")


# ============================================
# تتبع تغييرات الصلاحيات والمجموعات
# ============================================


@receiver(
    m2m_changed,
    sender=User.groups.through,
    dispatch_uid="track_user_groups_changed",
)
def track_user_groups_changed(sender, instance, action, pk_set, **kwargs):
    """تسجيل تغيير مجموعات المستخدم (إضافة/إزالة أدوار)"""
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    try:
        from core.audit import AuditLog

        if action == "post_clear":
            description = f"إزالة جميع المجموعات من المستخدم: {instance.username}"
            AuditLog.log(
                user=None,
                action="update",
                app_label="accounts",
                model_name="User",
                object_id=str(instance.pk),
                object_repr=instance.username,
                description=description,
                severity="WARNING",
                extra_data={"change_type": "groups_cleared"},
            )
        elif pk_set:
            group_names = list(
                Group.objects.filter(pk__in=pk_set).values_list("name", flat=True)
            )
            if action == "post_add":
                desc = f"إضافة مجموعات [{', '.join(group_names)}] للمستخدم: {instance.username}"
            else:
                desc = f"إزالة مجموعات [{', '.join(group_names)}] من المستخدم: {instance.username}"
            AuditLog.log(
                user=None,
                action="update",
                app_label="accounts",
                model_name="User",
                object_id=str(instance.pk),
                object_repr=instance.username,
                description=desc,
                severity="WARNING",
                extra_data={
                    "change_type": "groups_changed",
                    "action": action,
                    "groups": group_names,
                },
            )
    except Exception as e:
        print(f"❌ خطأ في تسجيل تغيير المجموعات: {e}")


@receiver(
    m2m_changed,
    sender=User.user_permissions.through,
    dispatch_uid="track_user_permissions_changed",
)
def track_user_permissions_changed(sender, instance, action, pk_set, **kwargs):
    """تسجيل تغيير صلاحيات المستخدم المباشرة"""
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    try:
        from django.contrib.auth.models import Permission

        from core.audit import AuditLog

        if action == "post_clear":
            description = f"إزالة جميع الصلاحيات المباشرة من المستخدم: {instance.username}"
            AuditLog.log(
                user=None,
                action="update",
                app_label="accounts",
                model_name="User",
                object_id=str(instance.pk),
                object_repr=instance.username,
                description=description,
                severity="CRITICAL",
                extra_data={"change_type": "permissions_cleared"},
            )
        elif pk_set:
            perm_names = list(
                Permission.objects.filter(pk__in=pk_set).values_list(
                    "codename", flat=True
                )
            )
            if action == "post_add":
                desc = f"إضافة صلاحيات [{', '.join(perm_names)}] للمستخدم: {instance.username}"
            else:
                desc = f"إزالة صلاحيات [{', '.join(perm_names)}] من المستخدم: {instance.username}"
            AuditLog.log(
                user=None,
                action="update",
                app_label="accounts",
                model_name="User",
                object_id=str(instance.pk),
                object_repr=instance.username,
                description=desc,
                severity="CRITICAL",
                extra_data={
                    "change_type": "permissions_changed",
                    "action": action,
                    "permissions": perm_names,
                },
            )
    except Exception as e:
        print(f"❌ خطأ في تسجيل تغيير الصلاحيات: {e}")


# ─── Phase 4: مزامنة Boolean fields ↔ UserRole M2M ──────────────

_SYNCING_ROLES = False  # منع التكرار اللامتناهي


@receiver(post_save, sender=User)
def sync_boolean_roles_to_userrole(sender, instance, **kwargs):
    """مزامنة حقول الأدوار البولينية إلى UserRole M2M عند الحفظ"""
    global _SYNCING_ROLES
    if _SYNCING_ROLES:
        return
    _SYNCING_ROLES = True
    try:
        active_role_keys = instance.get_active_roles()
        for field_name, role_key in User.ROLE_FIELD_MAP.items():
            role_obj, _created = Role.objects.get_or_create(
                name=role_key,
                defaults={"description": f"دور {role_key} (تلقائي)", "is_system_role": True},
            )
            if role_key in active_role_keys:
                UserRole.objects.get_or_create(user=instance, role=role_obj)
            else:
                UserRole.objects.filter(user=instance, role=role_obj).delete()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"خطأ في مزامنة أدوار {instance.username}: {e}")
    finally:
        _SYNCING_ROLES = False
