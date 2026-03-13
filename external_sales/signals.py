import logging
from datetime import date
from decimal import Decimal

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


# ═══════════════════════════════════════════════════════════════
#  COMMISSION → ACCOUNTING JOURNAL ENTRIES (Phase 2)
# ═══════════════════════════════════════════════════════════════

def _get_commission_reference(instance):
    """Build a unique reference for commission transactions."""
    return f"COMM-{instance.engineer.designer_code}-{instance.order.order_number}"


def _create_commission_approval_transaction(instance):
    """
    عند اعتماد العمولة: قيد محاسبي
    مدين: 5230 عمولات المبيعات (مصروف)
    دائن: 2124 مصروفات مستحقة أخرى (التزام)
    """
    from django.db import transaction as db_transaction

    from accounting.models import Account, Transaction, TransactionLine

    try:
        commission_expense = Account.objects.get(code="5230")
        accrued_expenses = Account.objects.get(code="2124")
    except Account.DoesNotExist:
        logger.error("Commission accounts not found (5230 or 2124)")
        return None

    amount = instance.commission_value
    if not amount or amount <= 0:
        return None

    reference = _get_commission_reference(instance)
    eng_name = instance.engineer.customer.name
    order_num = instance.order.order_number

    try:
        with db_transaction.atomic():
            txn = Transaction.objects.create(
                transaction_type="expense",
                date=timezone.now().date(),
                description=f"عمولة مهندس ديكور: {eng_name} — طلب {order_num}",
                reference=reference,
                customer=instance.engineer.customer,
                order=instance.order,
                status="posted",
            )
            TransactionLine.objects.create(
                transaction=txn,
                account=commission_expense,
                debit=amount,
                credit=Decimal("0"),
                description=f"عمولة المهندس {eng_name}",
            )
            TransactionLine.objects.create(
                transaction=txn,
                account=accrued_expenses,
                debit=Decimal("0"),
                credit=amount,
                description=f"عمولة مستحقة — المهندس {eng_name}",
            )
            txn.calculate_totals()
            logger.info(f"Commission approval transaction created: {txn.transaction_number}")
            return txn
    except Exception as e:
        logger.error(f"Error creating commission approval transaction: {e}", exc_info=True)
        return None


def _create_commission_payment_transaction(instance):
    """
    عند دفع العمولة: قيد محاسبي
    مدين: 2124 مصروفات مستحقة أخرى (إقفال الالتزام)
    دائن: 1110 النقدية (خروج نقد)
    """
    from django.db import transaction as db_transaction

    from accounting.models import Account, AccountingSettings, Transaction, TransactionLine

    try:
        accrued_expenses = Account.objects.get(code="2124")
        settings = AccountingSettings.objects.first()
        cash_account = settings.default_cash_account if settings else None
        if not cash_account:
            cash_account = Account.objects.get(code="1110")
    except Account.DoesNotExist:
        logger.error("Payment accounts not found (2124 or 1110)")
        return None

    amount = instance.commission_value
    if not amount or amount <= 0:
        return None

    reference = _get_commission_reference(instance)
    eng_name = instance.engineer.customer.name
    order_num = instance.order.order_number

    try:
        with db_transaction.atomic():
            txn = Transaction.objects.create(
                transaction_type="payment",
                date=timezone.now().date(),
                description=f"دفع عمولة مهندس ديكور: {eng_name} — طلب {order_num}",
                reference=f"{reference}-PAID",
                customer=instance.engineer.customer,
                order=instance.order,
                status="posted",
            )
            TransactionLine.objects.create(
                transaction=txn,
                account=accrued_expenses,
                debit=amount,
                credit=Decimal("0"),
                description=f"إقفال عمولة مستحقة — المهندس {eng_name}",
            )
            TransactionLine.objects.create(
                transaction=txn,
                account=cash_account,
                debit=Decimal("0"),
                credit=amount,
                description=f"دفع عمولة المهندس {eng_name}",
            )
            txn.calculate_totals()
            logger.info(f"Commission payment transaction created: {txn.transaction_number}")
            return txn
    except Exception as e:
        logger.error(f"Error creating commission payment transaction: {e}", exc_info=True)
        return None


@receiver(post_save, sender=EngineerLinkedOrder)
def create_commission_accounting_entry(sender, instance, created, **kwargs):
    """Create accounting journal entries when commission status changes."""
    if created:
        return

    reference = _get_commission_reference(instance)

    if instance.commission_status == "approved":
        from accounting.models import Transaction
        if Transaction.objects.filter(reference=reference).exists():
            return
        _create_commission_approval_transaction(instance)

    elif instance.commission_status == "paid":
        from accounting.models import Transaction
        if Transaction.objects.filter(reference=f"{reference}-PAID").exists():
            return
        _create_commission_payment_transaction(instance)


# ═══════════════════════════════════════════════════════════════
#  WHATSAPP APPOINTMENT CONFIRMATION (Phase 1.5)
# ═══════════════════════════════════════════════════════════════

@receiver(post_save, sender=EngineerContactLog)
def send_appointment_whatsapp(sender, instance, **kwargs):
    """
    عند تحديد appointment_datetime في سجل التواصل،
    يُرسل تأكيد عبر واتساب لرقم المهندس.
    """
    if not instance.appointment_datetime:
        return

    # Skip if already confirmed
    if instance.appointment_confirmed:
        return

    phone = getattr(instance.engineer.customer, "phone", None)
    if not phone:
        return

    try:
        from whatsapp.signals import get_whatsapp_settings, get_template, send_template_notification

        settings = get_whatsapp_settings()
        if not settings or not settings.is_active:
            return

        template = get_template(settings, "APPOINTMENT_CONFIRMED")

        if template:
            # Send via approved template
            appt_date = instance.appointment_datetime.strftime("%Y-%m-%d")
            appt_time = instance.appointment_datetime.strftime("%H:%M")
            variables = {
                "customer_name": instance.engineer.customer.name,
                "appointment_date": appt_date,
                "appointment_time": appt_time,
                "appointment_location": instance.appointment_location or "",
            }
            send_template_notification(
                phone=phone,
                template=template,
                variables=variables,
                customer=instance.engineer.customer,
            )
        else:
            # Fallback: send as plain text message
            from whatsapp.services import WhatsAppService

            service = WhatsAppService()
            appt_date = instance.appointment_datetime.strftime("%Y-%m-%d")
            appt_time = instance.appointment_datetime.strftime("%H:%M")
            location = instance.appointment_location
            msg = (
                f"مرحباً {instance.engineer.customer.name}،\n"
                f"تم تأكيد موعدكم:\n"
                f"📅 التاريخ: {appt_date}\n"
                f"🕐 الوقت: {appt_time}\n"
            )
            if location:
                msg += f"📍 المكان: {location}\n"
            msg += "\nشكراً لتعاملكم معنا — الخواجه"

            service.send_message(
                customer=instance.engineer.customer,
                message_text=msg,
                message_type="APPOINTMENT_CONFIRMED",
            )

        # Mark as confirmed
        EngineerContactLog.objects.filter(pk=instance.pk).update(
            appointment_confirmed=True
        )
        logger.info(
            f"WhatsApp appointment confirmation sent to {instance.engineer.customer.name}"
        )
    except Exception as e:
        logger.error(f"Error sending WhatsApp appointment confirmation: {e}")
