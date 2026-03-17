import logging

from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.middleware.current_user import get_current_user
from orders.models import Order

from .models import CustomerDebt, InstallationArchive, InstallationSchedule

logger = logging.getLogger(__name__)


@receiver(post_save, sender="manufacturing.ManufacturingOrder")
def sync_modification_status_from_manufacturing(sender, instance, created, **kwargs):
    """
    مزامنة حالة التعديل عند تغيير حالة أمر التصنيع من النوع 'modification'
    """
    if instance.order_type != "modification" or not instance.modification_request_id:
        return

    old_status = getattr(instance, "_old_status", None)
    if created or (old_status is not None and old_status == instance.status):
        return

    try:
        from .models import ModificationItem, ModificationRequest

        mod_request = ModificationRequest.objects.get(pk=instance.modification_request_id)

        if instance.status == "in_progress":
            mod_request.status = "manufacturing"
            mod_request.save(update_fields=["status"])

        elif instance.status in ("ready_install", "completed", "delivered"):
            # تحديث عناصر التعديل المرتبطة
            ModificationItem.objects.filter(
                modification_request=mod_request,
                manufacturing_order_item__manufacturing_order=instance,
            ).update(status="completed")

            # إذا كل العناصر مكتملة، تحديث حالة الطلب
            all_items = mod_request.modification_items.filter(needs_manufacturing=True)
            completed_items = all_items.filter(status="completed")
            if all_items.count() == completed_items.count():
                mod_request.status = "completed"
                mod_request.save(update_fields=["status"])

                # تحديث حالة OrderItem
                for item in mod_request.modification_items.all():
                    if item.order_item_id:
                        item.order_item.modification_status = "completed"
                        item.order_item.save(update_fields=["modification_status"])

    except Exception as e:
        logger.error(f"خطأ في مزامنة حالة التعديل من أمر التصنيع {instance.pk}: {e}")


@receiver(post_save, sender=InstallationSchedule)
def installation_status_changed(sender, instance, created, **kwargs):
    """معالجة تغيير حالة التركيب"""
    # الحصول على المستخدم الحالي من thread local storage
    current_user = get_current_user()

    old_status = getattr(instance, "_original_status", None)

    # مزامنة حالة طلبات التعديل المرتبطة عند اكتمال التعديل أو التركيب
    if not created and old_status and old_status != instance.status:
        if instance.status in ("modification_completed", "completed"):
            try:
                updated = instance.modification_requests.filter(
                    status__in=["pending", "manufacturing"]
                ).update(status="completed")
                if updated:
                    logger.info(
                        f"تم تحديث {updated} طلب تعديل إلى مكتمل تلقائياً للتركيب {instance.pk}"
                    )
            except Exception as e:
                logger.error(f"خطأ في مزامنة طلبات التعديل للتركيب {instance.pk}: {e}")

    # إنشاء أرشيف تلقائي إذا تم إكمال التركيب
    if not created and instance.status == "completed":
        # التحقق من أن الحالة تغيرت إلى مكتملة
        if old_status and old_status != "completed":
            archive, created = InstallationArchive.objects.get_or_create(
                installation=instance,
                defaults={
                    "archived_by": current_user,
                    "archive_notes": f'تم الأرشفة تلقائياً عند إكمال التركيب بواسطة {current_user.get_full_name() or current_user.username if current_user else "نظام تلقائي"}',
                },
            )

            # تسجيل الأرشفة في سجل الأحداث
            if created and current_user:
                from .models import InstallationEventLog

                InstallationEventLog.objects.create(
                    installation=instance,
                    event_type="completion",
                    description=f"تم إكمال التركيب وأرشفته تلقائياً",
                    user=current_user,
                    metadata={
                        "auto_archived": True,
                        "completion_date": str(instance.completion_date),
                        "archived_by": current_user.get_full_name()
                        or current_user.username,
                    },
                )


@receiver(post_save, sender=Order)
def manage_customer_debt_on_order_save(sender, instance, created, **kwargs):
    """
    إدارة مديونية العميل تلقائياً عند إنشاء أو تحديث الطلب
    """
    try:
        # حساب المديونية الحالية
        debt_amount = float(instance.total_amount - instance.paid_amount)

        # البحث عن سجل مديونية موجود
        debt_record = CustomerDebt.objects.filter(order=instance).first()

        if debt_amount > 0:
            # يوجد مديونية
            if debt_record:
                # تحديث السجل الموجود
                if not debt_record.is_paid:
                    old_amount = float(debt_record.debt_amount)
                    if abs(old_amount - debt_amount) > 0.01:  # تغيير في المبلغ
                        debt_record.debt_amount = debt_amount
                        debt_record.updated_at = timezone.now()
                        debt_record.save()
                        logger.info(
                            f"تم تحديث مديونية الطلب {instance.order_number} من {old_amount:.2f} إلى {debt_amount:.2f}"
                        )
            else:
                # إنشاء سجل جديد
                CustomerDebt.objects.create(
                    customer=instance.customer,
                    order=instance,
                    debt_amount=debt_amount,
                    notes=f"مديونية تلقائية للطلب {instance.order_number}",
                    is_paid=False,
                )
                logger.info(
                    f"تم إنشاء سجل مديونية جديد للطلب {instance.order_number} بمبلغ {debt_amount:.2f}"
                )

        else:
            # لا توجد مديونية (تم الدفع كاملاً)
            # لكن لا نقوم بإقفال المديونية تلقائياً إذا كانت مدفوعة من لوحة التحكم
            if debt_record and not debt_record.is_paid:
                # فقط إذا لم يكن هناك تاريخ دفع مسجل (أي لم يتم الدفع من لوحة التحكم)
                if not debt_record.payment_date:
                    # تحديث السجل إلى مدفوع
                    debt_record.is_paid = True
                    debt_record.payment_date = timezone.now()
                    debt_record.notes += f' - تم الدفع كاملاً تلقائياً في {timezone.now().strftime("%Y-%m-%d %H:%M")}'
                    debt_record.save()
                    logger.info(
                        f"تم تحديث مديونية الطلب {instance.order_number} إلى مدفوعة تلقائياً"
                    )

    except Exception as e:
        logger.error(f"خطأ في إدارة مديونية الطلب {instance.order_number}: {str(e)}")


@receiver(pre_save, sender=CustomerDebt)
def update_debt_payment_date(sender, instance, **kwargs):
    """
    تحديث تاريخ الدفع تلقائياً عند تغيير حالة الدفع
    """
    if instance.pk:
        try:
            old_instance = CustomerDebt.objects.get(pk=instance.pk)
            # إذا تم تغيير الحالة من غير مدفوع إلى مدفوع
            if not old_instance.is_paid and instance.is_paid:
                if not instance.payment_date:
                    instance.payment_date = timezone.now()
                logger.info(
                    f"تم تحديث تاريخ دفع المديونية للطلب {instance.order.order_number}"
                )
        except CustomerDebt.DoesNotExist:
            pass
    else:
        # سجل جديد
        if instance.is_paid and not instance.payment_date:
            instance.payment_date = timezone.now()


@receiver(post_delete, sender=InstallationSchedule)
def installation_deleted(sender, instance, **kwargs):
    """معالجة حذف التركيب"""
    # يمكن إضافة منطق إضافي هنا عند الحاجة
    pass
