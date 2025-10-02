import logging

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Notification, NotificationVisibility
from .utils import get_notification_recipients

User = get_user_model()
logger = logging.getLogger(__name__)


def clean_extra_data(data):
    """تنظيف البيانات الإضافية من النصوص المترجمة لتجنب مشاكل JSON"""
    if not isinstance(data, dict):
        return data

    cleaned_data = {}
    for key, value in data.items():
        if hasattr(value, "__str__"):
            cleaned_data[key] = str(value)
        else:
            cleaned_data[key] = value

    return cleaned_data


def create_notification(
    title,
    message,
    notification_type,
    related_object=None,
    created_by=None,
    priority="normal",
    extra_data=None,
    recipients=None,
):
    """
    إنشاء إشعار جديد مع تحديد المستخدمين المصرح لهم برؤيته

    Args:
        title: عنوان الإشعار
        message: نص الإشعار
        notification_type: نوع الإشعار
        related_object: الكائن المرتبط (اختياري)
        created_by: المستخدم المنشئ (اختياري)
        priority: أولوية الإشعار (افتراضي: normal)
        extra_data: بيانات إضافية (اختياري)
        recipients: قائمة المستخدمين المستهدفين (اختياري)

    Returns:
        Notification: الإشعار المنشأ
    """
    from datetime import timedelta

    from django.utils import timezone

    # فحص الإشعارات المكررة (نفس النوع والكائن المرتبط في آخر دقيقة)
    if related_object:
        recent_time = timezone.now() - timedelta(minutes=1)
        existing_notification = Notification.objects.filter(
            notification_type=notification_type,
            content_type=ContentType.objects.get_for_model(related_object),
            object_id=related_object.pk,
            created_at__gte=recent_time,
        ).first()

        # للإشعارات الحساسة، فحص أكثر دقة
        if existing_notification and notification_type in [
            "order_status_changed",
            "manufacturing_status_changed",
        ]:
            # فحص إذا كان نفس التغيير بالضبط
            if (
                extra_data
                and existing_notification.extra_data
                and extra_data.get("old_status")
                == existing_notification.extra_data.get("old_status")
                and extra_data.get("new_status")
                == existing_notification.extra_data.get("new_status")
            ):
                print(f"⚠️ تم تجاهل إشعار مكرر: {title}")
                return existing_notification
        elif existing_notification:
            print(f"⚠️ تم تجاهل إشعار مكرر: {title}")
            return existing_notification

    # إنشاء الإشعار
    notification = Notification.objects.create(
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        created_by=created_by,
        extra_data=clean_extra_data(extra_data or {}),
        content_type=(
            ContentType.objects.get_for_model(related_object)
            if related_object
            else None
        ),
        object_id=related_object.pk if related_object else None,
    )

    # تحديد المستخدمين المصرح لهم برؤية الإشعار
    if recipients is None:
        recipients = get_notification_recipients(
            notification_type, related_object, created_by
        )

    # إنشاء سجلات الرؤية
    visibility_records = []
    for user in recipients:
        visibility_records.append(
            NotificationVisibility(notification=notification, user=user, is_read=False)
        )

    if visibility_records:
        NotificationVisibility.objects.bulk_create(visibility_records)

    return notification


# ===== إشعارات العملاء =====


@receiver(post_save, sender="customers.Customer")
def customer_created_notification(sender, instance, created, **kwargs):
    """إشعار عند إنشاء عميل جديد"""
    if created:
        title = f"عميل جديد: {instance.name}"
        message = f"تم إنشاء عميل جديد باسم {instance.name} في فرع {instance.branch.name if instance.branch else 'غير محدد'}"

        if instance.created_by:
            message += f" بواسطة {instance.created_by.get_full_name() or instance.created_by.username}"

        create_notification(
            title=title,
            message=message,
            notification_type="customer_created",
            related_object=instance,
            created_by=instance.created_by,
            priority="normal",
            extra_data={
                "customer_code": instance.code,
                "branch_name": instance.branch.name if instance.branch else None,
            },
        )


# ===== إشعارات الطلبات =====


@receiver(post_save, sender="orders.Order")
def order_created_notification(sender, instance, created, **kwargs):
    """إشعار عند إنشاء طلب جديد"""
    if created:
        order_types = (
            instance.get_selected_types_list()
            if hasattr(instance, "get_selected_types_list")
            else []
        )
        order_types_str = ", ".join(
            [dict(instance.ORDER_TYPES).get(t, t) for t in order_types]
        )

        title = f"طلب جديد: {instance.order_number}"
        message = f"تم إنشاء طلب جديد رقم {instance.order_number} من نوع ({order_types_str}) للعميل {instance.customer.name}"

        if instance.created_by:
            message += f" بواسطة {instance.created_by.get_full_name() or instance.created_by.username}"

        create_notification(
            title=title,
            message=message,
            notification_type="order_created",
            related_object=instance,
            created_by=instance.created_by,
            priority="normal",
            extra_data={
                "order_number": instance.order_number,
                "customer_code": instance.customer.code,
                "order_types": order_types,
                "total_amount": (
                    str(instance.total_amount)
                    if hasattr(instance, "total_amount")
                    else None
                ),
            },
        )


# ===== إشعارات الطلبات معطلة =====
# تم تعطيل إشعارات الطلبات نهائياً لتجنب التكرار
# الأقسام (معاينة، تصنيع، تركيب) تتولى إرسال الإشعارات
# وتوجه المستخدم لتفاصيل الطلب مباشرة
#
# @receiver(pre_save, sender='orders.Order')
# def order_status_changed_notification(sender, instance, **kwargs):
#     """إشعار عند تغيير حالة الطلب - معطل لأن الأقسام تتولى الإشعارات"""
#     pass
# الكود المعطل - تم نقل المسؤولية للأقسام
# تم تعطيل جميع إشعارات الطلبات - الأقسام تتولى الإشعارات
#
# ملاحظة: إذا احتجت لإشعارات الطلبات المباشرة لاحقاً،
# يمكن إضافة فحص للتأكد أن التحديث ليس من الأقسام


# ===== إشعارات المعاينات =====


@receiver(post_save, sender="inspections.Inspection")
def inspection_created_notification(sender, instance, created, **kwargs):
    """إشعار عند إنشاء معاينة جديدة"""
    if created:
        # استخدام كود الطلب فقط
        order_number = None
        if hasattr(instance, "order") and instance.order:
            order_number = instance.order.order_number
        else:
            order_number = f"معاينة-{instance.pk}"

        title = f"معاينة جديدة: {order_number}"
        message = f"تم إنشاء معاينة جديدة للعميل {instance.customer.name if instance.customer else 'غير محدد'}"

        if hasattr(instance, "order") and instance.order:
            message += f" للطلب {instance.order.order_number}"

        if instance.responsible_employee:
            message += f" بواسطة {instance.responsible_employee.name}"

        create_notification(
            title=title,
            message=message,
            notification_type="inspection_created",
            related_object=instance,
            created_by=getattr(instance, "created_by", None),
            priority="normal",
            extra_data={
                "order_number": order_number,
                "customer_name": instance.customer.name if instance.customer else None,
                "branch_name": instance.branch.name if instance.branch else None,
                "responsible_employee": (
                    instance.responsible_employee.name
                    if instance.responsible_employee
                    else None
                ),
            },
        )


@receiver(pre_save, sender="inspections.Inspection")
def inspection_status_changed_notification(sender, instance, **kwargs):
    """إشعار عند تغيير حالة المعاينة"""
    logger.info(f"🔍 فحص تغيير حالة المعاينة: {instance.pk}")

    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            logger.info(
                f"📊 الحالة القديمة: {old_instance.status}, الحالة الجديدة: {instance.status}"
            )

            if old_instance.status != instance.status:
                old_status_display = str(
                    dict(instance.STATUS_CHOICES).get(
                        old_instance.status, old_instance.status
                    )
                )
                new_status_display = str(
                    dict(instance.STATUS_CHOICES).get(instance.status, instance.status)
                )

                # تحسين العنوان والرسالة
                contract_info = instance.contract_number or f"معاينة-{instance.pk}"
                if hasattr(instance, "order") and instance.order:
                    contract_info = instance.order.order_number

                title = f"تحديث المعاينة: {contract_info}"
                message = f"تم تغيير حالة المعاينة للطلب {contract_info} من '{old_status_display}' إلى '{new_status_display}'"

                # إضافة معلومات العميل إذا كانت متوفرة
                if hasattr(instance, "customer") and instance.customer:
                    message += f" - العميل: {instance.customer.name}"

                # إضافة ملاحظة أن النقر سيوجه لتفاصيل الطلب
                message += f" (انقر لعرض تفاصيل الطلب)"

                priority = "high" if instance.status == "completed" else "normal"

                logger.info(f"✅ إنشاء إشعار تغيير المعاينة: {title}")

                create_notification(
                    title=title,
                    message=message,
                    notification_type="inspection_status_changed",
                    related_object=instance,
                    created_by=None,
                    priority=priority,
                    extra_data={
                        "contract_number": instance.contract_number,
                        "old_status": old_instance.status,
                        "new_status": instance.status,
                        "old_status_display": old_status_display,
                        "new_status_display": new_status_display,
                    },
                )

                logger.info(f"🎉 تم إنشاء إشعار المعاينة بنجاح")
            else:
                logger.info(f"⚠️ لا يوجد تغيير في حالة المعاينة")

        except sender.DoesNotExist:
            logger.info(f"⚠️ لم يتم العثور على المعاينة القديمة: {instance.pk}")
            pass
    else:
        logger.info(f"ℹ️ معاينة جديدة، لا حاجة لإشعار تغيير الحالة")


# ===== إشعارات التركيبات =====


@receiver(post_save, sender="installations.InstallationSchedule")
def installation_scheduled_notification(sender, instance, created, **kwargs):
    """إشعار عند جدولة تركيب"""
    if created:
        title = f"جدولة تركيب: {instance.order.order_number}"
        message = f"تم جدولة تركيب للطلب {instance.order.order_number}"

        if instance.scheduled_date:
            message += f" في تاريخ {instance.scheduled_date.strftime('%Y-%m-%d')}"

        if instance.team:
            message += f" مع فريق {instance.team.name}"

        create_notification(
            title=title,
            message=message,
            notification_type="installation_scheduled",
            related_object=instance,
            created_by=getattr(instance, "created_by", None),
            priority="normal",
            extra_data={
                "order_number": instance.order.order_number,
                "scheduled_date": (
                    instance.scheduled_date.isoformat()
                    if instance.scheduled_date
                    else None
                ),
                "team_name": instance.team.name if instance.team else None,
            },
        )


@receiver(pre_save, sender="installations.InstallationSchedule")
def installation_completed_notification(sender, instance, **kwargs):
    """إشعار عند إكمال التركيب"""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)

            if (
                old_instance.status != instance.status
                and instance.status == "completed"
            ):

                title = f"تم إكمال التركيب: {instance.order.order_number}"
                message = f"تم إكمال تركيب الطلب {instance.order.order_number} بنجاح"

                if instance.completion_date:
                    message += (
                        f" في تاريخ {instance.completion_date.strftime('%Y-%m-%d')}"
                    )

                create_notification(
                    title=title,
                    message=message,
                    notification_type="installation_completed",
                    related_object=instance,
                    created_by=None,
                    priority="high",
                    extra_data={
                        "order_number": instance.order.order_number,
                        "completion_date": (
                            instance.completion_date.isoformat()
                            if instance.completion_date
                            else None
                        ),
                    },
                )

        except sender.DoesNotExist:
            pass


# ===== إشعارات أوامر التصنيع =====


@receiver(pre_save, sender="manufacturing.ManufacturingOrder")
def manufacturing_order_status_changed_notification(sender, instance, **kwargs):
    """إشعار عند تغيير حالة أمر التصنيع"""
    if instance.pk:  # التأكد من أن أمر التصنيع موجود مسبقاً
        try:
            old_instance = sender.objects.get(pk=instance.pk)

            if old_instance.status != instance.status:
                old_status_display = str(
                    dict(instance.STATUS_CHOICES).get(
                        old_instance.status, old_instance.status
                    )
                )
                new_status_display = str(
                    dict(instance.STATUS_CHOICES).get(instance.status, instance.status)
                )

                title = f"تحديث التصنيع: {instance.order.order_number}"
                message = f"تم تغيير حالة التصنيع للطلب {instance.order.order_number} من '{old_status_display}' إلى '{new_status_display}' (انقر لعرض تفاصيل الطلب)"

                # تحديد الأولوية حسب نوع التغيير
                priority = "normal"
                if instance.status in ["completed", "ready_install"]:
                    priority = "high"
                elif instance.status in ["rejected", "cancelled"]:
                    priority = "urgent"

                # محاولة الحصول على المستخدم الذي قام بالتغيير
                changed_by = None
                try:
                    # أولاً: البحث في سجل حالة الطلب
                    from django.utils import timezone

                    from orders.models import OrderStatusLog

                    # البحث عن آخر سجل حالة للطلب المرتبط
                    recent_status_log = (
                        OrderStatusLog.objects.filter(
                            order=instance.order, new_status=instance.status
                        )
                        .order_by("-created_at")
                        .first()
                    )

                    if (
                        recent_status_log
                        and (timezone.now() - recent_status_log.created_at).seconds
                        < 120
                    ):
                        changed_by = recent_status_log.changed_by
                        logger.info(f"Found user from status log: {changed_by}")

                    # إذا لم نجد في سجل الحالة، نبحث في admin log
                    if not changed_by:
                        from django.contrib.admin.models import CHANGE, LogEntry
                        from django.contrib.contenttypes.models import ContentType

                        recent_log = (
                            LogEntry.objects.filter(
                                content_type=ContentType.objects.get_for_model(
                                    instance
                                ),
                                object_id=instance.id,
                                action_flag=CHANGE,
                            )
                            .order_by("-action_time")
                            .first()
                        )

                        if (
                            recent_log
                            and (timezone.now() - recent_log.action_time).seconds < 60
                        ):
                            changed_by = recent_log.user
                            logger.info(f"Found user from admin log: {changed_by}")

                except Exception as e:
                    logger.warning(
                        f"Could not determine user who changed manufacturing status: {e}"
                    )

                # تحسين الرسالة لتشمل اسم المستخدم
                if changed_by:
                    message += (
                        f" بواسطة {changed_by.get_full_name() or changed_by.username}"
                    )
                else:
                    # إذا لم نتمكن من تحديد المستخدم، نضيف رسالة عامة
                    message += " (تم التغيير من قبل المستخدم)"

                create_notification(
                    title=title,
                    message=message,
                    notification_type="manufacturing_status_changed",
                    related_object=instance.order,  # ربط بالطلب الأصلي
                    created_by=changed_by,  # المستخدم الذي قام بالتغيير
                    priority=priority,
                    extra_data={
                        "order_number": instance.order.order_number,
                        "manufacturing_order_id": instance.id,
                        "old_status": old_instance.status,
                        "new_status": instance.status,
                        "old_status_display": old_status_display,
                        "new_status_display": new_status_display,
                        "order_type": instance.order_type,
                        "changed_by": (
                            changed_by.get_full_name()
                            if changed_by
                            else "مستخدم النظام"
                        ),
                        "changed_by_username": (
                            changed_by.username if changed_by else "system"
                        ),
                    },
                )

        except sender.DoesNotExist:
            pass


# ===== إشعارات الشكاوى =====


@receiver(post_save, sender="complaints.Complaint")
def complaint_created_notification(sender, instance, created, **kwargs):
    """إشعار عند تسجيل شكوى جديدة"""
    if created:
        title = f"شكوى جديدة: {instance.complaint_number}"
        message = f"تم تسجيل شكوى جديدة من العميل {instance.customer.name} بعنوان '{instance.title}'"

        # تحديد الأولوية حسب نوع الشكوى
        priority = "normal"
        if hasattr(instance, "priority"):
            priority_map = {
                "urgent": "urgent",
                "high": "high",
                "medium": "normal",
                "low": "low",
            }
            priority = priority_map.get(instance.priority, "normal")

        create_notification(
            title=title,
            message=message,
            notification_type="complaint_created",
            related_object=instance,
            created_by=getattr(instance, "created_by", None),
            priority=priority,
            extra_data={
                "complaint_number": instance.complaint_number,
                "customer_name": instance.customer.name,
                "complaint_title": instance.title,
                "complaint_type": (
                    instance.complaint_type.name
                    if hasattr(instance, "complaint_type")
                    else None
                ),
            },
        )
