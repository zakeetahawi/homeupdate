from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


def get_notification_recipients(
    notification_type, related_object=None, created_by=None
):
    """
    تحديد المستخدمين المصرح لهم برؤية الإشعار حسب نوع الإشعار والصلاحيات

    Args:
        notification_type: نوع الإشعار
        related_object: الكائن المرتبط
        created_by: المستخدم المنشئ

    Returns:
        QuerySet: المستخدمون المصرح لهم برؤية الإشعار
    """
    # جمع جميع IDs المستخدمين
    recipient_ids = set()

    # مديرو النظام يرون جميع الإشعارات
    super_admins = User.objects.filter(
        Q(is_superuser=True) | Q(is_sales_manager=True), is_active=True
    ).values_list("id", flat=True)
    recipient_ids.update(super_admins)

    # تحديد المستخدمين حسب نوع الإشعار
    if notification_type in ["customer_created"]:
        customer_recipients = get_customer_notification_recipients(
            related_object, created_by
        ).values_list("id", flat=True)
        recipient_ids.update(customer_recipients)

    elif notification_type in [
        "order_created",
        "order_updated",
        "order_status_changed",
        "order_delivered",
        "manufacturing_status_changed",
    ]:
        order_recipients = get_order_notification_recipients(
            related_object, created_by, notification_type
        ).values_list("id", flat=True)
        recipient_ids.update(order_recipients)

    elif notification_type in ["inspection_created", "inspection_status_changed"]:
        inspection_recipients = get_inspection_notification_recipients(
            related_object, created_by, notification_type
        ).values_list("id", flat=True)
        recipient_ids.update(inspection_recipients)

    elif notification_type in [
        "installation_scheduled",
        "installation_completed",
        "installation_status_changed",
    ]:
        installation_recipients = get_installation_notification_recipients(
            related_object, created_by, notification_type
        ).values_list("id", flat=True)
        recipient_ids.update(installation_recipients)

    elif notification_type in ["complaint_created"]:
        complaint_recipients = get_complaint_notification_recipients(
            related_object, created_by
        ).values_list("id", flat=True)
        recipient_ids.update(complaint_recipients)

    # إرجاع QuerySet للمستخدمين
    return User.objects.filter(id__in=recipient_ids)


def get_customer_notification_recipients(customer, created_by):
    """تحديد مستقبلي إشعارات العملاء"""
    recipients = User.objects.none()

    if customer and hasattr(customer, "branch") and customer.branch:
        # مديرو الفرع والمنطقة
        branch_managers = User.objects.filter(
            Q(is_branch_manager=True) | Q(is_region_manager=True),
            branch=customer.branch,
            is_active=True,
        )
        recipients = recipients.union(branch_managers)

        # البائعون في نفس الفرع
        salespeople = User.objects.filter(
            is_salesperson=True, branch=customer.branch, is_active=True
        )
        recipients = recipients.union(salespeople)

    # المستخدم المنشئ
    if created_by:
        recipients = recipients.union(User.objects.filter(pk=created_by.pk))

    return recipients


def get_order_notification_recipients(order, created_by, notification_type):
    """تحديد مستقبلي إشعارات الطلبات"""
    recipients = User.objects.none()

    if order:
        # المستخدم المنشئ للطلب
        if hasattr(order, "created_by") and order.created_by:
            recipients = recipients.union(User.objects.filter(pk=order.created_by.pk))

        # مديرو الفرع والمنطقة للطلب
        if hasattr(order, "branch") and order.branch:
            managers = User.objects.filter(
                Q(is_branch_manager=True) | Q(is_region_manager=True),
                branch=order.branch,
                is_active=True,
            )
            recipients = recipients.union(managers)

        # الأقسام المسؤولة حسب نوع الطلب
        if hasattr(order, "get_selected_types_list"):
            order_types = order.get_selected_types_list()

            # قسم التصنيع للطلبات التي تحتاج تصنيع
            if any(t in order_types for t in ["installation", "tailoring"]):
                factory_users = User.objects.filter(
                    is_factory_manager=True, is_active=True
                )
                recipients = recipients.union(factory_users)

            # قسم المعاينات للطلبات التي تحتاج معاينة
            if "inspection" in order_types:
                inspection_users = User.objects.filter(
                    is_inspection_manager=True, is_active=True
                )
                recipients = recipients.union(inspection_users)

            # قسم التركيبات للطلبات التي تحتاج تركيب
            if "installation" in order_types:
                installation_users = User.objects.filter(
                    is_installation_manager=True, is_active=True
                )
                recipients = recipients.union(installation_users)

        # للإشعارات الخاصة بتغيير الحالة، إضافة المديرين المباشرين
        if notification_type == "order_status_changed":
            if hasattr(order, "created_by") and order.created_by:
                # مدير الفرع للمستخدم المنشئ
                if order.created_by.branch:
                    direct_managers = User.objects.filter(
                        Q(is_branch_manager=True) | Q(is_region_manager=True),
                        branch=order.created_by.branch,
                        is_active=True,
                    )
                    recipients = recipients.union(direct_managers)

            # إضافة مديري المصنع لإشعارات أوامر التصنيع
            factory_managers = User.objects.filter(
                is_factory_manager=True, is_active=True
            )
            recipients = recipients.union(factory_managers)

    return recipients


def get_inspection_notification_recipients(inspection, created_by, notification_type):
    """تحديد مستقبلي إشعارات المعاينات"""
    recipients = User.objects.none()

    if inspection:
        # المستخدم المنشئ للمعاينة
        if hasattr(inspection, "created_by") and inspection.created_by:
            recipients = recipients.union(
                User.objects.filter(pk=inspection.created_by.pk)
            )

        # البائع المسؤول
        if (
            hasattr(inspection, "responsible_employee")
            and inspection.responsible_employee
        ):
            if (
                hasattr(inspection.responsible_employee, "user")
                and inspection.responsible_employee.user
            ):
                recipients = recipients.union(
                    User.objects.filter(pk=inspection.responsible_employee.user.pk)
                )

        # المعاين المكلف
        if hasattr(inspection, "inspector") and inspection.inspector:
            recipients = recipients.union(
                User.objects.filter(pk=inspection.inspector.pk)
            )

        # مديرو قسم المعاينات
        inspection_managers = User.objects.filter(
            is_inspection_manager=True, is_active=True
        )
        recipients = recipients.union(inspection_managers)

        # مديرو الفرع والمنطقة
        if hasattr(inspection, "branch") and inspection.branch:
            managers = User.objects.filter(
                Q(is_branch_manager=True) | Q(is_region_manager=True),
                branch=inspection.branch,
                is_active=True,
            )
            recipients = recipients.union(managers)

        # للإشعارات الخاصة بتغيير الحالة، إضافة المديرين المباشرين
        if notification_type == "inspection_status_changed":
            if (
                hasattr(inspection, "responsible_employee")
                and inspection.responsible_employee
                and hasattr(inspection.responsible_employee, "user")
                and inspection.responsible_employee.user
                and hasattr(inspection.responsible_employee.user, "branch")
                and inspection.responsible_employee.user.branch
            ):

                direct_managers = User.objects.filter(
                    Q(is_branch_manager=True) | Q(is_region_manager=True),
                    branch=inspection.responsible_employee.user.branch,
                    is_active=True,
                )
                recipients = recipients.union(direct_managers)

    return recipients


def get_installation_notification_recipients(
    installation, created_by, notification_type
):
    """تحديد مستقبلي إشعارات التركيبات"""
    recipients = User.objects.none()

    if installation:
        # مديرو قسم التركيبات
        installation_managers = User.objects.filter(
            is_installation_manager=True, is_active=True
        )
        recipients = recipients.union(installation_managers)

        # المستخدم المنشئ للطلب المرتبط
        if hasattr(installation, "order") and installation.order:
            if (
                hasattr(installation.order, "created_by")
                and installation.order.created_by
            ):
                recipients = recipients.union(
                    User.objects.filter(pk=installation.order.created_by.pk)
                )

            # مديرو فرع الطلب
            if hasattr(installation.order, "branch") and installation.order.branch:
                managers = User.objects.filter(
                    Q(is_branch_manager=True) | Q(is_region_manager=True),
                    branch=installation.order.branch,
                    is_active=True,
                )
                recipients = recipients.union(managers)

        # المستخدم المنشئ للتركيب
        if hasattr(installation, "created_by") and installation.created_by:
            recipients = recipients.union(
                User.objects.filter(pk=installation.created_by.pk)
            )

    return recipients


def get_complaint_notification_recipients(complaint, created_by):
    """تحديد مستقبلي إشعارات الشكاوى"""
    recipients = User.objects.none()

    if complaint:
        # المستخدم المستهدف بالشكوى (إذا كان محدداً)
        if hasattr(complaint, "target_user") and complaint.target_user:
            recipients = recipients.union(
                User.objects.filter(pk=complaint.target_user.pk)
            )

        # مديرو خدمة العملاء أو الشكاوى
        complaint_managers = User.objects.filter(
            Q(is_sales_manager=True) | Q(is_region_manager=True), is_active=True
        )
        recipients = recipients.union(complaint_managers)

        # مدير فرع العميل
        if hasattr(complaint, "customer") and complaint.customer:
            if hasattr(complaint.customer, "branch") and complaint.customer.branch:
                branch_managers = User.objects.filter(
                    Q(is_branch_manager=True) | Q(is_region_manager=True),
                    branch=complaint.customer.branch,
                    is_active=True,
                )
                recipients = recipients.union(branch_managers)

        # المستخدم المنشئ للشكوى
        if created_by:
            recipients = recipients.union(User.objects.filter(pk=created_by.pk))

    return recipients


def get_user_notification_count(user):
    """الحصول على عدد الإشعارات غير المقروءة للمستخدم"""
    from .models import NotificationVisibility

    return NotificationVisibility.objects.filter(user=user, is_read=False).count()


def mark_notification_as_read(notification, user):
    """تحديد إشعار كمقروء لمستخدم معين"""
    from django.utils import timezone

    from .models import NotificationVisibility

    try:
        visibility = NotificationVisibility.objects.get(
            notification=notification, user=user
        )

        # تسجيل المستخدم الذي قرأ الإشعار ووقت القراءة
        if not visibility.is_read:
            visibility.is_read = True
            visibility.read_at = timezone.now()
            visibility.save()

            # تسجيل في الـ logs للمراجعة
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"📖 الإشعار {notification.pk} تم قراءته بواسطة {user.username} في {timezone.now()}"
            )

        return True
    except NotificationVisibility.DoesNotExist:
        return False


def mark_all_notifications_as_read(user):
    """تحديد جميع الإشعارات كمقروءة لمستخدم معين"""
    from django.utils import timezone

    from .models import NotificationVisibility

    unread_notifications = NotificationVisibility.objects.filter(
        user=user, is_read=False
    )

    count = unread_notifications.update(is_read=True, read_at=timezone.now())

    return count
