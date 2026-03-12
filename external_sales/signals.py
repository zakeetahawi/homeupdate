import logging
from datetime import date

from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from customers.models import Customer

from .models import (
    DecoratorEngineerProfile,
    EngineerContactLog,
    EngineerLinkedCustomer,
    EngineerLinkedOrder,
)

logger = logging.getLogger(__name__)


# ─── Auto-create profile + notify on designer customer ────────────
@receiver(post_save, sender=Customer)
def auto_create_decorator_profile(sender, instance, created, **kwargs):
    """
    عند إنشاء أو تعديل عميل نوعه 'designer'،
    يُنشأ بروفايل مهندس ديكور تلقائياً إن لم يكن موجوداً،
    ويُرسل إشعار للمدراء عند الإنشاء الأول.
    """
    if getattr(instance, "customer_type", "") != "designer":
        return

    # Auto-create profile if missing
    profile_created = False
    if not DecoratorEngineerProfile.objects.filter(customer=instance).exists():
        DecoratorEngineerProfile.objects.create(
            customer=instance,
            city=instance.branch.name if instance.branch else "",
            priority="regular",
        )
        profile_created = True

    # Notify managers only on first creation
    if not (created or profile_created):
        return

    from accounts.models import User

    managers = User.objects.filter(
        is_decorator_dept_manager=True, is_active=True
    )
    if not managers.exists():
        return

    try:
        from django.contrib.contenttypes.models import ContentType

        from notifications.models import Notification, NotificationVisibility

        ct = ContentType.objects.get_for_model(Customer)

        notification = Notification.objects.create(
            title=f"مهندس ديكور جديد: {instance.name}",
            message=(
                f"تم إضافة مهندس ديكور جديد:\n"
                f"• الاسم: {instance.name}\n"
                f"• الكود: {instance.code}\n"
                f"• الفرع: {instance.branch.name if instance.branch else 'غير محدد'}\n"
                f"• أضيف بواسطة: {instance.created_by.get_full_name() if instance.created_by else 'غير معروف'}\n"
                f"• التاريخ: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                f"يرجى مراجعة الملف وإسناد موظف متابعة في أقرب وقت."
            ),
            notification_type="decorator_engineer_added",
            priority="high",
            content_type=ct,
            object_id=instance.pk,
            extra_data={
                "customer_code": instance.code,
                "customer_name": instance.name,
                "branch": instance.branch.name if instance.branch else None,
                "url": f"/external-sales/decorator/create-profile/{instance.code}/",
            },
        )
        for manager in managers:
            NotificationVisibility.objects.create(
                notification=notification, user=manager
            )
    except Exception as e:
        logger.error(f"Error sending decorator engineer notification: {e}")


# ─── Audit log for profile changes ────────────────────────────────
@receiver(post_save, sender=DecoratorEngineerProfile)
def audit_decorator_profile(sender, instance, created, **kwargs):
    try:
        from accounts.middleware.current_user import get_current_user
        from core.audit import AuditLog

        user = get_current_user()
        AuditLog.log(
            user=user,
            action="CREATE" if created else "UPDATE",
            description=f'{"إنشاء" if created else "تعديل"} ملف مهندس ديكور: {instance.customer}',
            app_label="external_sales",
            model_name="DecoratorEngineerProfile",
            object_id=str(instance.pk),
            object_repr=str(instance.customer),
            severity="INFO",
        )
    except Exception as e:
        logger.error(f"Audit log error (decorator profile): {e}")


# ─── Audit log for commission changes ─────────────────────────────
@receiver(post_save, sender=EngineerLinkedOrder)
def audit_commission_change(sender, instance, created, **kwargs):
    if created:
        return
    try:
        from accounts.middleware.current_user import get_current_user
        from core.audit import AuditLog

        user = get_current_user()
        AuditLog.log(
            user=user,
            action="UPDATE",
            description=f"تغيير حالة عمولة: طلب {instance.order_id} → {instance.commission_status}",
            app_label="external_sales",
            model_name="EngineerLinkedOrder",
            object_id=str(instance.pk),
            severity="INFO",
        )
    except Exception as e:
        logger.error(f"Audit log error (commission): {e}")


# ─── Update cached fields on profile ──────────────────────────────
@receiver(post_save, sender=EngineerContactLog)
def update_profile_contact_cache(sender, instance, **kwargs):
    try:
        profile = instance.engineer
        actual_last = EngineerContactLog.objects.filter(
            engineer=profile
        ).aggregate(last=Max("contact_date"))["last"]
        profile.last_contact_date = actual_last.date() if actual_last else None

        earliest = (
            EngineerContactLog.objects.filter(
                engineer=profile, next_followup_date__gte=date.today()
            )
            .order_by("next_followup_date")
            .values_list("next_followup_date", flat=True)
            .first()
        )
        profile.next_followup_date = earliest
        profile.save(update_fields=["last_contact_date", "next_followup_date"])
    except Exception as e:
        logger.error(f"Error updating contact cache: {e}")


@receiver(post_save, sender=EngineerLinkedOrder)
def update_profile_order_cache(sender, instance, **kwargs):
    try:
        profile = instance.engineer
        profile.last_order_date = instance.linked_at.date()
        profile.total_orders_count = profile.linked_orders.count()
        profile.save(update_fields=["last_order_date", "total_orders_count"])
    except Exception as e:
        logger.error(f"Error updating order cache: {e}")


@receiver(post_save, sender=EngineerLinkedCustomer)
def update_profile_customer_cache(sender, instance, **kwargs):
    try:
        profile = instance.engineer
        profile.total_clients_count = profile.linked_customers.filter(
            is_active=True
        ).count()
        profile.save(update_fields=["total_clients_count"])
    except Exception as e:
        logger.error(f"Error updating customer cache: {e}")
