import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ManufacturingDeletionLog, Order, OrderItem, OrderStatusLog, Payment

logger = logging.getLogger(__name__)


def _get_order_type_name_for_signal(order_types):
    """إرجاع اسم نوع الطلب بالعربية للاستخدام في الـ signals"""
    if not order_types:
        return "الطلب"

    type_names = {
        "inspection": "المعاينة",
        "installation": "التركيب",
        "products": "المنتجات",
        "accessory": "الإكسسوار",
        "tailoring": "التسليم",
    }

    # إرجاع أول نوع موجود
    for order_type in order_types:
        if order_type in type_names:
            return type_names[order_type]

    return "الطلب"


@receiver(pre_save, sender=Order)
def track_order_changes(sender, instance, **kwargs):
    """تتبع جميع التغييرات على الطلب وتسجيلها في OrderStatusLog"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        # تجاهل التحديثات التلقائية
        if instance.is_auto_update:
            return

        try:
            from .models import OrderStatusLog

            old_instance = Order.objects.get(pk=instance.pk)

            # تتبع تغييرات حالة الطلب فقط (order_status) وليس tracking_status
            # فقط إذا كان التغيير يدوي من قبل مستخدم
            if (
                getattr(old_instance, "order_status", None)
                != getattr(instance, "order_status", None)
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):

                old_status = getattr(old_instance, "order_status", None)
                new_status = getattr(instance, "order_status", None)

                if old_status != new_status:
                    # تحديد نوع الطلب لإنشاء رسالة مناسبة
                    order_types = instance.get_selected_types_list()
                    order_type_name = _get_order_type_name_for_signal(order_types)

                    OrderStatusLog.create_detailed_log(
                        order=instance,
                        change_type="status",
                        old_value=old_status,
                        new_value=new_status,
                        changed_by=instance._modified_by,
                        notes=f"تم تغيير حالة {order_type_name}",
                        order_types=order_types,
                        is_automatic=False,
                    )

            # تتبع تغيير العميل (فقط التعديلات اليدوية)
            if (
                old_instance.customer != instance.customer
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):

                # ⚠️ تحديث رقم الطلب ليتوافق مع كود العميل الجديد
                old_order_number = instance.order_number
                new_order_number = instance.generate_unique_order_number()
                instance.order_number = new_order_number

                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="customer",
                    old_value=old_instance.customer,
                    new_value=instance.customer,
                    changed_by=instance._modified_by,
                    notes=f"تم تغيير العميل - تم تحديث رقم الطلب من {old_order_number} إلى {new_order_number}",
                    is_automatic=False,
                )

            # تتبع تغيير السعر (فقط التعديلات اليدوية)
            if (
                old_instance.final_price != instance.final_price
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="price",
                    old_value=old_instance.final_price,
                    new_value=instance.final_price,
                    changed_by=instance._modified_by,
                    notes="تم تغيير السعر النهائي",
                    is_automatic=False,
                )

            # تتبع تغيير تاريخ التسليم (فقط التعديلات اليدوية)
            if (
                old_instance.expected_delivery_date != instance.expected_delivery_date
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_date = (
                    old_instance.expected_delivery_date.strftime("%Y-%m-%d")
                    if old_instance.expected_delivery_date
                    else "غير محدد"
                )
                new_date = (
                    instance.expected_delivery_date.strftime("%Y-%m-%d")
                    if instance.expected_delivery_date
                    else "غير محدد"
                )
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="date",
                    old_value=old_date,
                    new_value=new_date,
                    changed_by=instance._modified_by,
                    field_name="تاريخ التسليم المتوقع",
                    notes=f"تم تغيير تاريخ التسليم المتوقع من {old_date} إلى {new_date}",
                    is_automatic=False,
                )

            # تتبع تغيير المبلغ المدفوع (فقط التعديلات اليدوية)
            if (
                old_instance.paid_amount != instance.paid_amount
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="payment",
                    old_value=old_instance.paid_amount,
                    new_value=instance.paid_amount,
                    changed_by=instance._modified_by,
                    notes="تم تحديث المبلغ المدفوع",
                    is_automatic=False,
                )

            # تتبع تغيير أنواع الطلب (فقط التعديلات اليدوية)
            if (
                old_instance.selected_types != instance.selected_types
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_types = old_instance.get_selected_types_display()
                new_types = instance.get_selected_types_display()
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_types,
                    new_value=new_types,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير أنواع الطلب من "{old_types}" إلى "{new_types}"',
                    field_name="أنواع الطلب",
                    is_automatic=False,
                )

            # تتبع تغيير الملاحظات (فقط التعديلات اليدوية)
            if (
                old_instance.notes != instance.notes
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_instance.notes or "لا توجد ملاحظات",
                    new_value=instance.notes or "لا توجد ملاحظات",
                    changed_by=instance._modified_by,
                    notes="تم تحديث ملاحظات الطلب",
                    field_name="الملاحظات",
                    is_automatic=False,
                )

            # تتبع تغيير أرقام العقود (فقط التعديلات اليدوية)
            if hasattr(instance, "_modified_by") and instance._modified_by:
                contract_fields = [
                    ("contract_number", "رقم العقد الأول"),
                    ("contract_number_2", "رقم العقد الثاني"),
                    ("contract_number_3", "رقم العقد الثالث"),
                ]

                for field_name, field_display in contract_fields:
                    old_value = getattr(old_instance, field_name, None)
                    new_value = getattr(instance, field_name, None)
                    if old_value != new_value:
                        OrderStatusLog.create_detailed_log(
                            order=instance,
                            change_type="general",
                            old_value=old_value or "غير محدد",
                            new_value=new_value or "غير محدد",
                            changed_by=instance._modified_by,
                            notes=f"تم تحديث {field_display}",
                            field_name=field_display,
                            is_automatic=False,
                        )

            # تتبع تغيير البائع (فقط التعديلات اليدوية)
            if (
                old_instance.salesperson != instance.salesperson
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_salesperson = (
                    old_instance.salesperson.user.get_full_name()
                    if old_instance.salesperson and old_instance.salesperson.user
                    else "غير محدد"
                )
                new_salesperson = (
                    instance.salesperson.user.get_full_name()
                    if instance.salesperson and instance.salesperson.user
                    else "غير محدد"
                )
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_salesperson,
                    new_value=new_salesperson,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير البائع من "{old_salesperson}" إلى "{new_salesperson}"',
                    field_name="البائع",
                    is_automatic=False,
                )

            # تتبع تغيير الفرع (فقط التعديلات اليدوية)
            if (
                old_instance.branch != instance.branch
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_branch = (
                    old_instance.branch.name if old_instance.branch else "غير محدد"
                )
                new_branch = instance.branch.name if instance.branch else "غير محدد"
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_branch,
                    new_value=new_branch,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير الفرع من "{old_branch}" إلى "{new_branch}"',
                    field_name="الفرع",
                    is_automatic=False,
                )

            # تتبع تغيير نوع التسليم (فقط التعديلات اليدوية)
            if (
                old_instance.delivery_type != instance.delivery_type
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_delivery = (
                    old_instance.get_delivery_type_display()
                    if old_instance.delivery_type
                    else "غير محدد"
                )
                new_delivery = (
                    instance.get_delivery_type_display()
                    if instance.delivery_type
                    else "غير محدد"
                )
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_delivery,
                    new_value=new_delivery,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير نوع التسليم من "{old_delivery}" إلى "{new_delivery}"',
                    field_name="نوع التسليم",
                    is_automatic=False,
                )

            # تتبع تغيير أرقام الفواتير (فقط التعديلات اليدوية)
            if hasattr(instance, "_modified_by") and instance._modified_by:
                invoice_fields = [
                    ("invoice_number", "رقم الفاتورة الأولى"),
                    ("invoice_number_2", "رقم الفاتورة الثانية"),
                    ("invoice_number_3", "رقم الفاتورة الثالثة"),
                ]

                for field_name, field_display in invoice_fields:
                    old_value = getattr(old_instance, field_name, None)
                    new_value = getattr(instance, field_name, None)
                    if old_value != new_value:
                        OrderStatusLog.create_detailed_log(
                            order=instance,
                            change_type="general",
                            old_value=old_value or "غير محدد",
                            new_value=new_value or "غير محدد",
                            changed_by=instance._modified_by,
                            notes=f"تم تحديث {field_display}",
                            field_name=field_display,
                            is_automatic=False,
                        )

            # تتبع تغيير العناوين (فقط التعديلات اليدوية)
            if hasattr(instance, "_modified_by") and instance._modified_by:
                address_fields = [
                    ("delivery_address", "عنوان التسليم"),
                    ("location_address", "عنوان الموقع"),
                ]

                for field_name, field_display in address_fields:
                    old_value = getattr(old_instance, field_name, None)
                    new_value = getattr(instance, field_name, None)
                    if old_value != new_value:
                        OrderStatusLog.create_detailed_log(
                            order=instance,
                            change_type="general",
                            old_value=old_value or "غير محدد",
                            new_value=new_value or "غير محدد",
                            changed_by=instance._modified_by,
                            notes=f"تم تحديث {field_display}",
                            field_name=field_display,
                            is_automatic=False,
                        )

            # تتبع تغيير حالة الطلب (VIP/عادي) (فقط التعديلات اليدوية)
            if (
                old_instance.status != instance.status
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_status_display = (
                    old_instance.get_status_display()
                    if old_instance.status
                    else "غير محدد"
                )
                new_status_display = (
                    instance.get_status_display() if instance.status else "غير محدد"
                )
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_status_display,
                    new_value=new_status_display,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير وضع الطلب من "{old_status_display}" إلى "{new_status_display}"',
                    field_name="وضع الطلب",
                    is_automatic=False,
                )

            # تتبع تغيير حالة المعاينة (فقط التعديلات اليدوية)
            if (
                old_instance.inspection_status != instance.inspection_status
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_inspection = (
                    old_instance.get_inspection_status_display()
                    if old_instance.inspection_status
                    else "غير محدد"
                )
                new_inspection = (
                    instance.get_inspection_status_display()
                    if instance.inspection_status
                    else "غير محدد"
                )
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_inspection,
                    new_value=new_inspection,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير حالة المعاينة من "{old_inspection}" إلى "{new_inspection}"',
                    field_name="حالة المعاينة",
                    is_automatic=False,
                )

            # تتبع تغيير رقم الهاتف (إذا كان الحقل موجود)
            if (
                hasattr(old_instance, "phone_number")
                and hasattr(instance, "phone_number")
                and old_instance.phone_number != instance.phone_number
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=old_instance.phone_number or "غير محدد",
                    new_value=instance.phone_number or "غير محدد",
                    changed_by=instance._modified_by,
                    notes="تم تحديث رقم الهاتف",
                    field_name="رقم الهاتف",
                    is_automatic=False,
                )

            # تتبع تغيير تاريخ الطلب (فقط التعديلات اليدوية)
            if (
                old_instance.order_date != instance.order_date
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="date",
                    old_value=old_instance.order_date,
                    new_value=instance.order_date,
                    changed_by=instance._modified_by,
                    field_name="تاريخ الطلب",
                    notes="تم تغيير تاريخ الطلب",
                    is_automatic=False,
                )

            # تتبع تغيير التحقق من الدفع (فقط التعديلات اليدوية)
            if (
                old_instance.payment_verified != instance.payment_verified
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_verified = (
                    "تم التحقق" if old_instance.payment_verified else "لم يتم التحقق"
                )
                new_verified = (
                    "تم التحقق" if instance.payment_verified else "لم يتم التحقق"
                )
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="payment",
                    old_value=old_verified,
                    new_value=new_verified,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير حالة التحقق من الدفع من "{old_verified}" إلى "{new_verified}"',
                    field_name="التحقق من الدفع",
                    is_automatic=False,
                )

            # تتبع تغيير حالة الدفع (إذا كان الحقل موجود)
            if (
                hasattr(old_instance, "payment_status")
                and hasattr(instance, "payment_status")
                and old_instance.payment_status != instance.payment_status
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_payment_status = (
                    old_instance.get_payment_status_display()
                    if old_instance.payment_status
                    else "غير محدد"
                )
                new_payment_status = (
                    instance.get_payment_status_display()
                    if instance.payment_status
                    else "غير محدد"
                )
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="payment",
                    old_value=old_payment_status,
                    new_value=new_payment_status,
                    changed_by=instance._modified_by,
                    notes=f'تم تغيير حالة الدفع من "{old_payment_status}" إلى "{new_payment_status}"',
                    field_name="حالة الدفع",
                    is_automatic=False,
                )

            # تتبع تغيير حالة المعاينة (فقط التعديلات اليدوية)
            if (
                old_instance.inspection_status != instance.inspection_status
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                old_inspection_display = dict(
                    old_instance._meta.get_field("inspection_status").choices
                ).get(old_instance.inspection_status, old_instance.inspection_status)
                new_inspection_display = dict(
                    instance._meta.get_field("inspection_status").choices
                ).get(instance.inspection_status, instance.inspection_status)
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="status",
                    old_value=old_inspection_display,
                    new_value=new_inspection_display,
                    changed_by=instance._modified_by,
                    notes=f"تم تغيير حالة المعاينة من {old_inspection_display} إلى {new_inspection_display}",
                    field_name="حالة المعاينة",
                    is_automatic=False,
                )

            # تتبع تغيير الخصم (فقط التعديلات اليدوية)
            if (
                getattr(old_instance, "discount_amount", 0)
                != getattr(instance, "discount_amount", 0)
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="price",
                    old_value=getattr(old_instance, "discount_amount", 0),
                    new_value=getattr(instance, "discount_amount", 0),
                    changed_by=instance._modified_by,
                    notes="تم تحديث مبلغ الخصم",
                    field_name="مبلغ الخصم",
                    is_automatic=False,
                )

            # تتبع تغيير الضريبة (فقط التعديلات اليدوية)
            if (
                getattr(old_instance, "tax_amount", 0)
                != getattr(instance, "tax_amount", 0)
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="price",
                    old_value=getattr(old_instance, "tax_amount", 0),
                    new_value=getattr(instance, "tax_amount", 0),
                    changed_by=instance._modified_by,
                    notes="تم تحديث مبلغ الضريبة",
                    field_name="مبلغ الضريبة",
                    is_automatic=False,
                )

            # تتبع تغيير الملاحظات الداخلية (فقط التعديلات اليدوية)
            if (
                getattr(old_instance, "internal_notes", "")
                != getattr(instance, "internal_notes", "")
                and hasattr(instance, "_modified_by")
                and instance._modified_by
            ):
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type="general",
                    old_value=getattr(old_instance, "internal_notes", "")
                    or "لا توجد ملاحظات داخلية",
                    new_value=getattr(instance, "internal_notes", "")
                    or "لا توجد ملاحظات داخلية",
                    changed_by=instance._modified_by,
                    notes="تم تحديث الملاحظات الداخلية",
                    field_name="الملاحظات الداخلية",
                    is_automatic=False,
                )

        except Order.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(pre_save, sender="orders.Order")
def track_price_changes(sender, instance, **kwargs):
    """تتبع تغييرات الأسعار في الطلبات"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        # تجاهل التحديثات التلقائية
        if instance.is_auto_update:
            return

        try:
            Order = instance.__class__
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.final_price != instance.final_price:
                # لا نسجل التعديلات إذا كان هذا تحديث تلقائي (غير من قبل المستخدم)
                if not instance.is_auto_update:
                    instance.price_changed = True
                    instance.modified_at = timezone.now()
                    # حفظ القيمة القديمة للتتبع
                    instance._old_total_amount = old_instance.final_price
        except Order.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(post_save, sender=Order)
def create_manufacturing_order_on_order_creation(sender, instance, created, **kwargs):
    """
    Creates a ManufacturingOrder automatically when a new Order is created
    with specific types ('installation', 'tailoring', 'accessory').

    ⚠️ IMPORTANT: 'products' and 'inspection' orders should NEVER create manufacturing orders.
    They follow a different workflow (cutting for products, inspection for inspections).
    """
    if created:
        # استخدام transaction.on_commit للتأكد من اكتمال المعاملة قبل إنشاء أمر التصنيع
        def create_manufacturing_order():
            # print(f"--- SIGNAL TRIGGERED for Order PK: {instance.pk} ---")
            # print(f"Raw selected_types from instance: {instance.selected_types}")

            # فقط هذه الأنواع تنشئ أوامر تصنيع - المنتجات والمعاينات مستثناة تماماً
            MANUFACTURING_TYPES = {"installation", "tailoring", "accessory"}

            order_types = set()

            # selected_types is a JSONField that returns a Python list directly
            if isinstance(instance.selected_types, list):
                order_types = set(instance.selected_types)
            elif isinstance(instance.selected_types, str):
                # Fallback: try to parse as JSON string
                try:
                    parsed_types = json.loads(instance.selected_types)
                    if isinstance(parsed_types, list):
                        order_types = set(parsed_types)
                    else:
                        order_types = {instance.selected_types}
                except (json.JSONDecodeError, TypeError, ValueError):
                    # Single string value
                    order_types = {instance.selected_types}

            # print(f"Parsed order_types: {order_types}")

            if order_types.intersection(MANUFACTURING_TYPES):
                # print(f"MATCH FOUND: Order types {order_types} intersect with {MANUFACTURING_TYPES}. Creating manufacturing order...")

                # Determine the appropriate order_type for manufacturing
                manufacturing_order_type = ""
                if "installation" in order_types:
                    manufacturing_order_type = "installation"
                elif "tailoring" in order_types:
                    manufacturing_order_type = "custom"
                elif "accessory" in order_types:
                    manufacturing_order_type = "accessory"

                # Use a transaction to ensure both creations happen or neither.
                from django.db import transaction

                with transaction.atomic():
                    from datetime import timedelta

                    expected_date = (
                        instance.expected_delivery_date
                        or (instance.created_at + timedelta(days=15)).date()
                    )

                    # import ManufacturingOrder here to avoid circular import at module load
                    from manufacturing.models import ManufacturingOrder

                    mfg_order, created_mfg = ManufacturingOrder.objects.get_or_create(
                        order=instance,
                        defaults={
                            "order_type": manufacturing_order_type,
                            "status": "pending_approval",
                            "notes": instance.notes,
                            "order_date": instance.created_at.date(),
                            "expected_delivery_date": expected_date,
                            "contract_number": instance.contract_number,
                            "invoice_number": instance.invoice_number,
                        },
                    )

                    # Also update the original order's tracking status
                    if created_mfg:
                        # تحديث بدون إطلاق الإشارات لتجنب الrecursion
                        Order.objects.filter(pk=instance.pk).update(
                            tracking_status="factory", order_status="pending_approval"
                        )
                        # print(f"SUCCESS: Created ManufacturingOrder PK: {mfg_order.pk} and updated Order PK: {instance.pk} tracking_status to 'factory'")
                    else:
                        pass  # ManufacturingOrder already existed

        from django.db import transaction

        transaction.on_commit(create_manufacturing_order)


@receiver(post_save, sender="manufacturing.ManufacturingOrder")
def sync_order_from_manufacturing(sender, instance, created, **kwargs):
    """Ensure the linked Order has its order_status and tracking_status updated
    when the ManufacturingOrder changes. This prevents display mismatches where
    manufacturing is completed but Order still shows an older manufacturing state.
    """
    try:
        order = getattr(instance, "order", None)
        if not order:
            return

        # Map manufacturing status to order.tracking_status (same mapping as management command)
        status_mapping = {
            "pending_approval": "factory",
            "pending": "factory",
            "in_progress": "factory",
            "ready_install": "ready",
            "completed": "ready",
            "delivered": "delivered",
            "rejected": "factory",
            "cancelled": "factory",
        }

        new_order_status = instance.status
        new_tracking_status = status_mapping.get(instance.status, order.tracking_status)

        # Only update if something changed to avoid recursion/noise
        update_fields = []
        if order.order_status != new_order_status:
            order.order_status = new_order_status
            update_fields.append("order_status")
        if order.tracking_status != new_tracking_status:
            order.tracking_status = new_tracking_status
            update_fields.append("tracking_status")

        if update_fields:
            # Use update to avoid triggering heavy save logic where appropriate
            from django.db import transaction

            with transaction.atomic():
                Order.objects.filter(pk=order.pk).update(
                    **{f: getattr(order, f) for f in update_fields}
                )

            # لا نقوم بإنشاء OrderStatusLog هنا لأننا نريد فقط السجلات الحقيقية
            # التي يتم إنشاؤها من قبل المستخدمين في manufacturing/views.py
            # (السطر 1539-1545 في update_order_status)
    except Exception:
        # avoid letting signal exceptions break the caller
        import logging

        logging.getLogger(__name__).exception(
            "خطأ أثناء مزامنة حالة الطلب من ManufacturingOrder"
        )


@receiver(post_save, sender=Order)
def create_inspection_on_order_creation(sender, instance, created, **kwargs):
    """
    إنشاء معاينة تلقائية عند إنشاء طلب من نوع معاينة
    """
    if created:
        # استخدام transaction.on_commit للتأكد من اكتمال المعاملة قبل إنشاء المعاينة
        def create_inspection():
            order_types = instance.get_selected_types_list()

            # تسجيل مختصر فقط
            if "inspection" in order_types:
                logger.info(f"Creating inspection for order {instance.order_number}")
                try:
                    from django.db import transaction

                    with transaction.atomic():
                        from inspections.models import Inspection

                        # استخدم تاريخ الطلب كـ request_date
                        request_date = (
                            instance.order_date.date()
                            if instance.order_date
                            else timezone.now().date()
                        )
                        # لا نحدد تاريخ مجدول - سيتم تحديده يدوياً من قسم المعاينات
                        scheduled_date = None
                        # التحقق من البائع وإعداد المعاين
                        inspector = instance.created_by
                        responsible_employee = None

                        # إذا كان البائع له حساب مستخدم، استخدمه كمعاين
                        if instance.salesperson and instance.salesperson.user:
                            inspector = instance.salesperson.user
                            responsible_employee = instance.salesperson
                        elif instance.salesperson:
                            # البائع موجود لكن بدون حساب مستخدم
                            responsible_employee = instance.salesperson
                            inspector = instance.created_by  # استخدم منشئ الطلب كمعاين

                        inspection = Inspection.objects.create(
                            customer=instance.customer,
                            branch=instance.branch,
                            inspector=inspector,
                            responsible_employee=responsible_employee,
                            order=instance,
                            contract_number=instance.contract_number,  # إضافة رقم العقد
                            is_from_orders=True,
                            request_date=request_date,
                            scheduled_date=scheduled_date,  # None - غير مجدولة
                            status="pending",  # قيد الانتظار - يتم الجدولة يدوياً
                            notes=f"معاينة للطلب رقم {instance.order_number}",
                            order_notes=instance.notes,
                            created_by=instance.created_by,
                            windows_count=1,  # قيمة افتراضية
                        )
                        logger.info(
                            f"✅ Inspection created for order {instance.order_number} (ID: {inspection.id})"
                        )
                        Order.objects.filter(pk=instance.pk).update(
                            tracking_status="processing", order_status="pending"
                        )
                except Exception as e:
                    import traceback

                    error_msg = f"❌ خطأ في إنشاء معاينة للطلب {instance.order_number}: {str(e)}"
                    print(f"\033[31m{error_msg}\033[0m")
                    traceback.print_exc()
            else:
                pass

        from django.db import transaction

        transaction.on_commit(create_inspection)


def set_default_delivery_option(order):
    """تحديد خيار التسليم الافتراضي حسب نوع الطلب"""
    if not hasattr(order, "delivery_option"):
        return

    # إذا كان الطلب يحتوي على تركيب، تحديد التسليم مع التركيب
    if hasattr(order, "selected_types") and order.selected_types:
        if "installation" in order.selected_types or "تركيب" in order.selected_types:
            Order.objects.filter(pk=order.pk).update(
                delivery_option="with_installation"
            )
    # إذا كان الطلب تسليم في الفرع
    elif hasattr(order, "delivery_type") and order.delivery_type == "branch":
        Order.objects.filter(pk=order.pk).update(delivery_option="branch_pickup")
    # إذا كان الطلب توصيل منزلي
    elif hasattr(order, "delivery_type") and order.delivery_type == "home":
        Order.objects.filter(pk=order.pk).update(delivery_option="home_delivery")


def find_available_team(target_date, branch=None):
    """البحث عن فريق متاح في تاريخ محدد"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء نظام التركيبات
    return None


def calculate_windows_count(order):
    """حساب عدد الشبابيك من عناصر الطلب"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء النظام
    return 1


def create_production_order(order):
    """إنشاء طلب إنتاج"""
    # هذه الوظيفة سيتم تحديثها بعد إعادة بناء نظام المصنع
    return None


@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """معالج حفظ الطلب"""
    if created:
        # استخدام transaction.on_commit للتأكد من اكتمال المعاملة قبل إنشاء السجلات
        def create_status_log():
            # إنشاء سجل حالة أولية باستخدام النموذج المحسن
            OrderStatusLog.create_detailed_log(
                order=instance,
                change_type="creation",
                changed_by=getattr(instance, "created_by", None),
                notes="تم إنشاء الطلب",
            )

        from django.db import transaction

        transaction.on_commit(create_status_log)
    else:
        # التحقق من تغيير الحالة
        if (
            hasattr(instance, "_tracking_status_changed")
            and instance._tracking_status_changed
        ):
            # الحصول على الحالة السابقة من tracker
            old_status = instance.tracker.previous("tracking_status")
            if old_status is None:
                old_status = "pending"  # قيمة افتراضية إذا لم تكن موجودة

            OrderStatusLog.objects.create(
                order=instance,
                old_status=old_status,
                new_status=getattr(instance, "order_status", instance.tracking_status),
                changed_by=getattr(instance, "_modified_by", None),
                notes="تم تغيير حالة الطلب",
            )

        # تتبع التغييرات في المبلغ الإجمالي
        from .models import OrderModificationLog

        if (
            hasattr(instance, "_old_total_amount")
            and instance._old_total_amount != instance.final_price
        ):
            OrderModificationLog.objects.create(
                order=instance,
                modification_type="تعديلات البيانات الأساسية",
                old_total_amount=instance._old_total_amount,
                new_total_amount=instance.final_price,
                modified_by=getattr(instance, "_modified_by", None),
                details=f"تم تغيير إجمالي المبلغ من {instance._old_total_amount} إلى {instance.final_price}",
                notes="تعديل في المبلغ الإجمالي للطلب",
            )

        # تتبع التغييرات في حقول الطلب الأساسية إذا كان هناك مستخدم محدد
        modified_by = getattr(instance, "_modified_by", None)
        if modified_by:
            order_fields_to_track = [
                "contract_number",
                "contract_number_2",
                "contract_number_3",
                "invoice_number",
                "invoice_number_2",
                "invoice_number_3",
                "notes",
                "delivery_address",
                "location_address",
                "expected_delivery_date",
            ]

            field_changes = []
            field_labels = {
                "contract_number": "رقم العقد",
                "contract_number_2": "رقم العقد الإضافي 2",
                "contract_number_3": "رقم العقد الإضافي 3",
                "invoice_number": "رقم الفاتورة",
                "invoice_number_2": "رقم الفاتورة الإضافي 2",
                "invoice_number_3": "رقم الفاتورة الإضافي 3",
                "notes": "الملاحظات",
                "delivery_address": "عنوان التسليم",
                "location_address": "عنوان التركيب",
                "expected_delivery_date": "تاريخ التسليم المتوقع",
            }

            modified_fields_data = {}

            for field_name in order_fields_to_track:
                try:
                    if instance.tracker.has_changed(field_name):
                        old_value = instance.tracker.previous(field_name)
                        new_value = getattr(instance, field_name)
                        field_changes.append(
                            f"{field_labels[field_name]}: {old_value or 'غير محدد'} → {new_value or 'غير محدد'}"
                        )
                        # تحويل التواريخ إلى نص للتسلسل في JSON
                        old_value_serializable = old_value
                        new_value_serializable = new_value

                        if hasattr(old_value, "strftime"):  # تاريخ أو وقت
                            old_value_serializable = (
                                old_value.strftime("%Y-%m-%d") if old_value else None
                            )
                        if hasattr(new_value, "strftime"):  # تاريخ أو وقت
                            new_value_serializable = (
                                new_value.strftime("%Y-%m-%d") if new_value else None
                            )

                        modified_fields_data[field_name] = {
                            "old": old_value_serializable,
                            "new": new_value_serializable,
                        }
                except Exception:
                    # تخطي الحقول غير المتتبعة
                    continue

            if field_changes:
                OrderModificationLog.objects.create(
                    order=instance,
                    modification_type="تعديل حقول الطلب الأساسية",
                    modified_by=modified_by,
                    details=" | ".join(field_changes),
                    notes="تعديل يدوي في حقول الطلب الأساسية",
                    is_manual_modification=True,
                    modified_fields=modified_fields_data,
                )

            # تحديث ManufacturingOrder عند تغيير invoice_number
            if instance.tracker.has_changed("invoice_number"):
                try:
                    from django.db import transaction

                    from manufacturing.models import ManufacturingOrder

                    # حفظ القيمة الجديدة
                    new_invoice_number = instance.invoice_number
                    old_invoice = instance.tracker.previous("invoice_number")
                    order_number = instance.order_number
                    order_pk = instance.pk

                    print(
                        f"🔍 [order_post_save] تغيير رقم الفاتورة من '{old_invoice}' إلى '{new_invoice_number}' للطلب {order_number}"
                    )

                    # استخدام on_commit لضمان التحديث بعد اكتمال الحفظ
                    def update_manufacturing_orders():
                        try:
                            manufacturing_orders = ManufacturingOrder.objects.filter(
                                order_id=order_pk
                            )
                            if manufacturing_orders.exists():
                                updated_count = manufacturing_orders.update(
                                    invoice_number=new_invoice_number
                                )
                                logger.info(
                                    f"✅ [on_commit] تم تحديث رقم الفاتورة من '{old_invoice}' إلى '{new_invoice_number}' في {updated_count} أمر تصنيع للطلب {order_number}"
                                )
                                print(
                                    f"✅ [on_commit] تم تحديث {updated_count} أمر تصنيع بالرقم {new_invoice_number}"
                                )
                            else:
                                print(f"⚠️ لا توجد أوامر تصنيع للطلب {order_number}")
                        except Exception as e:
                            logger.error(f"❌ خطأ في تحديث رقم الفاتورة: {e}")
                            print(f"❌ خطأ: {e}")

                    transaction.on_commit(update_manufacturing_orders)
                except Exception as e:
                    logger.error(f"❌ خطأ في تحديث رقم الفاتورة في أوامر التصنيع: {e}")
                    print(f"❌ خطأ في تحديث ManufacturingOrder: {e}")


@receiver(post_save, sender=Order)
def deduct_inventory_on_order_creation(sender, instance, created, **kwargs):
    """
    خصم المخزون تلقائياً عند إنشاء طلب منتجات
    يتم الخصم فقط للطلبات من نوع 'products'
    """
    if created:

        def process_inventory_deduction():
            try:
                order_types = instance.get_selected_types_list()

                # خصم المخزون فقط للطلبات من نوع منتجات
                if "products" in order_types:
                    from .inventory_integration import OrderInventoryService

                    # التحقق من توفر المخزون أولاً
                    availability = OrderInventoryService.check_stock_availability(
                        instance
                    )

                    if not availability["all_available"]:
                        # إرسال تنبيه بنقص المخزون لكن الاستمرار بالخصم
                        logger.warning(
                            f"⚠️ نقص في المخزون للطلب {instance.order_number}: "
                            f"إجمالي النقص: {availability['total_shortage']}"
                        )

                    # خصم المخزون
                    result = OrderInventoryService.deduct_stock_for_order(
                        instance, getattr(instance, "created_by", None)
                    )

                    if result["success"]:
                        logger.info(
                            f"✅ تم خصم المخزون للطلب {instance.order_number}: "
                            f"{len(result.get('deducted', []))} منتج"
                        )
                    else:
                        logger.error(
                            f"❌ فشل خصم المخزون للطلب {instance.order_number}: "
                            f"{result.get('error', 'خطأ غير معروف')}"
                        )

            except Exception as e:
                logger.error(f"خطأ في خصم المخزون للطلب {instance.order_number}: {e}")

        from django.db import transaction

        transaction.on_commit(process_inventory_deduction)


@receiver(post_save, sender=OrderItem)
def order_item_post_save(sender, instance, created, **kwargs):
    """معالج حفظ عنصر الطلب"""
    if created:
        # تحديث المبلغ الإجمالي للطلب (للطلبات الجديدة فقط)
        try:
            # Force recalculation to ensure stored final_price matches items
            instance.order.calculate_final_price(force_update=True)
            # تحديث مباشر في قاعدة البيانات لضمان دقة الأرقام فوراً
            instance.order._is_auto_update = True
            Order.objects.filter(pk=instance.order.pk).update(
                final_price=instance.order.final_price,
                total_amount=instance.order.total_amount,
            )
        except Exception as e:
            logger.error(
                f"Error in synchronous recalculation for order {instance.order.id}: {e}"
            )
        # لا نسجل تعديلات عند الإنشاء الأولي
        return
    else:
        # تتبع التغييرات في عنصر الطلب
        from .models import OrderItemModificationLog, OrderModificationLog

        # التحقق من التغييرات في الكمية
        if instance.tracker.has_changed("quantity"):
            old_quantity = instance.tracker.previous("quantity")
            new_quantity = instance.quantity

            OrderItemModificationLog.objects.create(
                order_item=instance,
                field_name="quantity",
                old_value=str(old_quantity) if old_quantity is not None else "",
                new_value=str(new_quantity) if new_quantity is not None else "",
                modified_by=getattr(instance, "_modified_by", None),
                notes=f"تم تغيير كمية المنتج {instance.product.name}",
            )

        # التحقق من التغييرات في سعر الوحدة
        if instance.tracker.has_changed("unit_price"):
            old_price = instance.tracker.previous("unit_price")
            new_price = instance.unit_price

            OrderItemModificationLog.objects.create(
                order_item=instance,
                field_name="unit_price",
                old_value=str(old_price) if old_price is not None else "",
                new_value=str(new_price) if new_price is not None else "",
                modified_by=getattr(instance, "_modified_by", None),
                notes=f"تم تغيير سعر الوحدة للمنتج {instance.product.name}",
            )

        # التحقق من التغييرات في المنتج
        if instance.tracker.has_changed("product"):
            old_product_id = instance.tracker.previous("product")
            new_product_id = instance.product.id

            try:
                from inventory.models import Product

                old_product = (
                    Product.objects.get(id=old_product_id) if old_product_id else None
                )
                new_product = instance.product

                OrderItemModificationLog.objects.create(
                    order_item=instance,
                    field_name="product",
                    old_value=old_product.name if old_product else "",
                    new_value=new_product.name,
                    modified_by=getattr(instance, "_modified_by", None),
                    notes=f'تم تغيير المنتج من {old_product.name if old_product else "غير محدد"} إلى {new_product.name}',
                )
            except Product.DoesNotExist:
                pass

        # التحقق من التغييرات في نسبة الخصم
        if instance.tracker.has_changed("discount_percentage"):
            old_discount = instance.tracker.previous("discount_percentage")
            new_discount = instance.discount_percentage

            OrderItemModificationLog.objects.create(
                order_item=instance,
                field_name="discount_percentage",
                old_value=f"{old_discount}%" if old_discount is not None else "0%",
                new_value=f"{new_discount}%" if new_discount is not None else "0%",
                modified_by=getattr(instance, "_modified_by", None),
                notes=f"تم تغيير نسبة الخصم للمنتج {instance.product.name}",
            )

        # إنشاء سجل تعديل شامل للطلب
        # الاحتفاظ بتسجيل السجل فقط إن وُجد مستخدم محدد، لكن دعنا نسمح دائماً بإعادة الحساب
        has_user_modifier = bool(getattr(instance, "_modified_by", None))

        if any(
            [
                instance.tracker.has_changed("quantity"),
                instance.tracker.has_changed("unit_price"),
                instance.tracker.has_changed("product"),
                instance.tracker.has_changed("discount_percentage"),
            ]
        ):
            # الحصول على المبلغ القديم قبل التعديل
            old_total = instance.order.final_price

            # حساب المبلغ الجديد بعد التعديل
            # نحتاج إلى حساب المبلغ الجديد يدوياً بناءً على التغييرات
            total_change = 0
            modification_details = []

            if instance.tracker.has_changed("quantity"):
                old_quantity = instance.tracker.previous("quantity")
                new_quantity = instance.quantity
                current_price = instance.unit_price
                quantity_change = (new_quantity - old_quantity) * current_price
                total_change += quantity_change
                modification_details.append(f"الكمية: {old_quantity} → {new_quantity}")

            if instance.tracker.has_changed("unit_price"):
                old_price = instance.tracker.previous("unit_price")
                new_price = instance.unit_price
                current_quantity = instance.quantity
                # التأكد من أن الأنواع متوافقة
                old_price = (
                    Decimal(str(old_price)) if old_price is not None else Decimal("0")
                )
                new_price = (
                    Decimal(str(new_price)) if new_price is not None else Decimal("0")
                )
                current_quantity = (
                    Decimal(str(current_quantity))
                    if current_quantity is not None
                    else Decimal("0")
                )
                price_change = (new_price - old_price) * current_quantity
                total_change += price_change
                modification_details.append(f"السعر: {old_price} → {new_price} ج.م")

            if instance.tracker.has_changed("product"):
                old_product_id = instance.tracker.previous("product")
                try:
                    from inventory.models import Product

                    old_product = (
                        Product.objects.get(id=old_product_id)
                        if old_product_id
                        else None
                    )
                    modification_details.append(
                        f"المنتج: {old_product.name if old_product else 'غير محدد'} → {instance.product.name}"
                    )
                except Product.DoesNotExist:
                    modification_details.append(
                        f"المنتج: غير محدد → {instance.product.name}"
                    )

            if instance.tracker.has_changed("discount_percentage"):
                old_discount = instance.tracker.previous("discount_percentage")
                new_discount = instance.discount_percentage
                modification_details.append(f"الخصم: {old_discount}% → {new_discount}%")

            new_total = old_total + total_change

            # إنشاء سجل تعديل شامل مع تفاصيل العناصر (فقط إذا وُجد مستخدم محدد)
            if has_user_modifier:
                OrderModificationLog.objects.create(
                    order=instance.order,
                    modification_type="تعديل الأصناف الموجودة",
                    old_total_amount=old_total,
                    new_total_amount=new_total,
                    modified_by=getattr(instance, "_modified_by", None),
                    details=f"تعديل {instance.product.name}: {' | '.join(modification_details)}",
                    notes="تعديل في عناصر الطلب",
                    is_manual_modification=True,
                    modified_fields={
                        "order_items": [
                            {
                                "item_id": instance.pk,
                                "product": instance.product.name,
                                "changes": modification_details,
                            }
                        ]
                    },
                )
            # بعد تسجيل التعديل، نعيد حساب إجماليات الطلب ونحدث الحقول المخزنة فوراً بشكل متزامن
            try:
                instance.order.calculate_final_price(force_update=True)
                instance.order._is_auto_update = True
                Order.objects.filter(pk=instance.order.pk).update(
                    final_price=instance.order.final_price,
                    total_amount=instance.order.total_amount,
                )
            except Exception as e:
                logger.error(
                    f"Error in synchronous update recalculation for order {instance.order.id}: {e}"
                )


@receiver(post_save, sender=Payment)
def payment_post_save(sender, instance, created, **kwargs):
    """معالج حفظ الدفعة"""
    if created:
        order = instance.order
        if order:
            # تحديث المبلغ المدفوع للطلب
            paid_amount = order.payments.aggregate(total=models.Sum("amount"))["total"] or 0
            # تحديث مباشر في قاعدة البيانات لتجنب التكرار الذاتي
            Order.objects.filter(pk=order.pk).update(
                paid_amount=paid_amount, payment_verified=True
            )


# إشارات تحديث حالة الطلب من الأقسام الأخرى
# تم إزالة signal التركيب لتجنب الحلقة اللانهائية - يتم التعامل معه في orders/models.py

# تم تعطيل هذا signal لتجنب التضارب مع inspections/signals.py
# @receiver(post_save, sender='inspections.Inspection')
# def update_order_inspection_status(sender, instance, created, **kwargs):
#     """تحديث حالة الطلب عند تغيير حالة المعاينة - معطل لتجنب التضارب"""
#     try:
#         if instance.order:
#             order = instance.order
#             order.update_inspection_status()
#             order.update_completion_status()
#     except Exception as e:
#         logger.error(f"خطأ في تحديث حالة المعاينة للطلب: {str(e)}")


@receiver(post_save, sender="manufacturing.ManufacturingOrder")
def update_order_manufacturing_status(sender, instance, created, **kwargs):
    """تحديث حالة الطلب عند تغيير حالة التصنيع"""
    try:
        order = instance.order

        # تجاهل التحديث إذا كان إنشاء جديد لتجنب التضارب
        if created:
            return

        # مطابقة مباشرة بين حالات التصنيع والطلب
        status_mapping = {
            "pending_approval": "pending_approval",
            "pending": "pending",
            "in_progress": "in_progress",
            "ready_install": "ready_install",
            "completed": "completed",
            "delivered": "delivered",
            "rejected": "rejected",
            "cancelled": "cancelled",
        }

        new_status = status_mapping.get(instance.status)

        # تحديث الحالة فقط إذا تغيرت لتجنب التكرار الذاتي
        if new_status and new_status != order.order_status:
            Order.objects.filter(pk=order.pk).update(order_status=new_status)
            order.refresh_from_db()
            order.update_completion_status()
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة التصنيع للطلب {instance.order.id}: {str(e)}")


# إشارة حذف أوامر التصنيع
@receiver(post_delete, sender="manufacturing.ManufacturingOrder")
def log_manufacturing_order_deletion(sender, instance, **kwargs):
    """تسجيل حذف أمر التصنيع"""
    try:
        # حفظ بيانات أمر التصنيع قبل الحذف
        manufacturing_data = {
            "id": instance.id,
            "status": instance.status,
            "order_type": instance.order_type,
            "contract_number": instance.contract_number,
            "created_at": (
                instance.created_at.isoformat() if instance.created_at else None
            ),
        }

        ManufacturingDeletionLog.objects.create(
            order=instance.order,
            manufacturing_order_id=instance.id,
            manufacturing_order_data=manufacturing_data,
            reason="تم حذف أمر التصنيع",
        )

        # تحديث حالة الطلب
        Order.objects.filter(pk=instance.order.pk).update(
            order_status="manufacturing_deleted"
        )

    except Exception as e:
        logger.error(f"خطأ في تسجيل حذف أمر التصنيع: {str(e)}")


# ==================== 🎨 إشعارات الطلبات التلقائية ====================

# تم إزالة signal إنشاء الإشعارات المكررة - يتم التعامل مع الإشعارات في Order.save()
# تم إزالة signal إنشاء الإشعارات المكررة - يتم التعامل مع الإشعارات في Order.save()
# @receiver(post_save, sender=Order)
# def order_created_notification(sender, instance, created, **kwargs):
#     """إنشاء إشعارات عند إنشاء طلب جديد - تم تعطيله لتجنب التكرار"""
#     pass


# تم إزالة signal تغيير حالة الطلب المكرر - يتم التعامل مع الإشعارات في Order.save()
# @receiver(pre_save, sender=Order)
# def order_status_change_notification(sender, instance, **kwargs):
#     """إنشاء إشعارات عند تغيير حالة الطلب - تم تعطيله لتجنب التكرار"""
#     pass


# تم إزالة signal تغيير حالة الطلب الشامل المكرر - يتم التعامل مع الإشعارات في Order.save()
# @receiver(pre_save, sender=Order)
# def comprehensive_order_status_change_notification(sender, instance, **kwargs):
#     """إنشاء إشعارات شاملة عند تغيير حالة الطلب - تم تعطيله لتجنب التكرار"""
#     pass

# تم إزالة الكود المتبقي من signal تغيير الحالة المحذوف


# تم إزالة دالة manufacturing_order_notification


# ===== إشارات التخزين المؤقت =====


@receiver(pre_save, sender="orders.OrderItem")
def track_order_item_changes(sender, instance, **kwargs):
    """تتبع تغييرات عناصر الطلب"""
    if instance.pk:  # تحقق من أن هذا تحديث وليس إنشاء جديد
        try:
            OrderItem = instance.__class__
            old_instance = OrderItem.objects.get(pk=instance.pk)
            # حفظ القيم القديمة للتتبع
            instance._old_quantity = old_instance.quantity
            instance._old_unit_price = old_instance.unit_price
            instance._old_product_id = old_instance.product.id
            instance._old_discount_percentage = old_instance.discount_percentage
        except OrderItem.DoesNotExist:
            pass  # حالة الإنشاء الجديد


@receiver(post_save, sender="orders.OrderItem")
def log_order_item_changes(sender, instance, created, **kwargs):
    """تسجيل تغييرات عناصر الطلب في سجل الحالة"""
    if (
        not created
        and instance.order
        and hasattr(instance, "_modified_by")
        and instance._modified_by
    ):  # فقط للتحديثات اليدوية
        try:
            from .models import OrderStatusLog

            changes = []

            # تتبع تغيير الكمية
            if (
                hasattr(instance, "_old_quantity")
                and instance._old_quantity != instance.quantity
            ):
                changes.append(
                    f"الكمية: {instance._old_quantity} → {instance.quantity}"
                )

            # تتبع تغيير سعر الوحدة
            if (
                hasattr(instance, "_old_unit_price")
                and instance._old_unit_price != instance.unit_price
            ):
                changes.append(
                    f"سعر الوحدة: {instance._old_unit_price} → {instance.unit_price}"
                )

            # تتبع تغيير المنتج
            if (
                hasattr(instance, "_old_product_id")
                and instance._old_product_id != instance.product.id
            ):
                try:
                    from inventory.models import Product

                    old_product = Product.objects.get(id=instance._old_product_id)
                    changes.append(
                        f"المنتج: {old_product.name} → {instance.product.name}"
                    )
                except:
                    changes.append(f"المنتج: تم التغيير")

            # تتبع تغيير نسبة الخصم
            if (
                hasattr(instance, "_old_discount_percentage")
                and instance._old_discount_percentage != instance.discount_percentage
            ):
                changes.append(
                    f"نسبة الخصم: {instance._old_discount_percentage}% → {instance.discount_percentage}%"
                )

            # إنشاء سجل إذا كان هناك تغييرات
            if changes:
                OrderStatusLog.create_detailed_log(
                    order=instance.order,
                    change_type="general",
                    old_value="",
                    new_value="",
                    changed_by=getattr(instance, "_modified_by", None),
                    notes=f'تم تعديل عنصر الطلب: {instance.product.name} - {" | ".join(changes)}',
                    field_name="عناصر الطلب",
                )

        except Exception as e:
            logger.error(f"خطأ في تسجيل تغييرات عنصر الطلب {instance.pk}: {e}")


@receiver(post_save, sender="orders.OrderItem")
def log_order_item_creation(sender, instance, created, **kwargs):
    """تسجيل إضافة عناصر جديدة للطلب"""
    if (
        created
        and instance.order
        and hasattr(instance, "_modified_by")
        and instance._modified_by
    ):  # فقط الإضافة اليدوية
        try:
            from .models import OrderStatusLog

            OrderStatusLog.create_detailed_log(
                order=instance.order,
                change_type="general",
                old_value="",
                new_value=f"{instance.product.name} - الكمية: {instance.quantity}",
                changed_by=getattr(instance, "_modified_by", None),
                notes=f"تم إضافة عنصر جديد: {instance.product.name} (الكمية: {instance.quantity}، السعر: {instance.unit_price})",
                field_name="عناصر الطلب",
            )
        except Exception as e:
            logger.error(f"خطأ في تسجيل إضافة عنصر الطلب {instance.pk}: {e}")


@receiver(post_delete, sender="orders.OrderItem")
def log_order_item_deletion(sender, instance, **kwargs):
    """تسجيل حذف عناصر من الطلب"""
    # عدم تسجيل أي شيء إذا لم يكن هناك طلب مرتبط
    if not instance.order:
        return

    # التحقق من أن الطلب ليس قيد الحذف
    if getattr(instance.order, "_is_being_deleted", False):
        return

    try:
        # التحقق من أن الطلب لا يزال موجوداً في قاعدة البيانات
        from .models import Order, OrderStatusLog

        if not Order.objects.filter(pk=instance.order.pk).exists():
            # الطلب تم حذفه، لا نسجل شيء
            return

        OrderStatusLog.create_detailed_log(
            order=instance.order,
            change_type="general",
            old_value=f"{instance.product.name} - الكمية: {instance.quantity}",
            new_value="",
            changed_by=getattr(instance, "_modified_by", None),
            notes=f"تم حذف عنصر: {instance.product.name} (الكمية: {instance.quantity}، السعر: {instance.unit_price})",
            field_name="عناصر الطلب",
        )

        # إعادة حساب إجماليات الطلب بعد الحذف لضمان دقة الأرقام
        try:
            instance.order.calculate_final_price(force_update=True)
            instance.order._is_auto_update = True
            Order.objects.filter(pk=instance.order.pk).update(
                final_price=instance.order.final_price,
                total_amount=instance.order.total_amount,
            )
        except Exception as e:
            logger.error(
                f"Error in recalculation after deletion for order {instance.order.id}: {e}"
            )
    except Exception as e:
        # تجاهل الأخطاء بصمت إذا كان الطلب قيد الحذف
        pass


@receiver(post_save, sender=Order)
def invalidate_order_cache_on_save(sender, instance, created, **kwargs):
    """إلغاء التخزين المؤقت عند حفظ طلب"""
    try:
        from .cache import OrderCache

        # إلغاء إحصائيات الطلبات
        OrderCache.invalidate_order_stats_cache()

        # إلغاء بيانات العميل إذا تم تحديثها
        if instance.customer_id:
            OrderCache.invalidate_customer_cache(instance.customer_id)

        logger.debug(f"تم إلغاء التخزين المؤقت للطلب {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للطلب {instance.pk}: {str(e)}")


@receiver(post_delete, sender=Order)
def invalidate_order_cache_on_delete(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت عند حذف طلب"""
    try:
        from .cache import OrderCache

        # إلغاء إحصائيات الطلبات
        OrderCache.invalidate_order_stats_cache()

        logger.debug(f"تم إلغاء التخزين المؤقت بعد حذف الطلب {instance.pk}")

    except Exception as e:
        logger.error(
            f"خطأ في إلغاء التخزين المؤقت بعد حذف الطلب {instance.pk}: {str(e)}"
        )


@receiver(post_save, sender="orders.DeliveryTimeSettings")
def invalidate_delivery_settings_cache_on_save(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت لإعدادات التسليم عند التحديث"""
    try:
        from .cache import OrderCache

        OrderCache.invalidate_delivery_settings_cache()
        logger.debug("تم إلغاء التخزين المؤقت لإعدادات التسليم")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت لإعدادات التسليم: {str(e)}")


@receiver(post_save, sender="customers.Customer")
def invalidate_customer_cache_on_save(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت لبيانات العميل عند التحديث"""
    try:
        from .cache import OrderCache

        OrderCache.invalidate_customer_cache(instance.pk)
        logger.debug(f"تم إلغاء التخزين المؤقت للعميل {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للعميل {instance.pk}: {str(e)}")


@receiver(post_save, sender="inventory.Product")
def invalidate_product_cache_on_save(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت للمنتجات عند التحديث"""
    try:
        from .cache import OrderCache

        OrderCache.invalidate_product_search_cache()
        logger.debug(f"تم إلغاء التخزين المؤقت للمنتجات بعد تحديث المنتج {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للمنتجات: {str(e)}")


@receiver(post_delete, sender="inventory.Product")
def invalidate_product_cache_on_delete(sender, instance, **kwargs):
    """إلغاء التخزين المؤقت للمنتجات عند الحذف"""
    try:
        from .cache import OrderCache

        OrderCache.invalidate_product_search_cache()
        logger.debug(f"تم إلغاء التخزين المؤقت للمنتجات بعد حذف المنتج {instance.pk}")

    except Exception as e:
        logger.error(f"خطأ في إلغاء التخزين المؤقت للمنتجات بعد الحذف: {str(e)}")


# إضافة signals لتتبع تغييرات حالات أنواع الطلبات المختلفة
try:

    @receiver(post_save, sender="inspections.Inspection")
    def track_inspection_status_changes(sender, instance, created, **kwargs):
        """تتبع تغييرات حالة المعاينة"""
        if not created and instance.order:
            try:
                from inspections.models import Inspection

                # محاولة الحصول على الحالة السابقة
                old_status = None
                if hasattr(instance, "_old_status"):
                    old_status = instance._old_status
                elif hasattr(Inspection, "tracker") and hasattr(instance, "tracker"):
                    old_status = instance.tracker.previous("status")

                if old_status and old_status != instance.status:
                    # البحث عن المستخدم من مصادر مختلفة
                    changed_by = None

                    # 1. من instance المعاينة (_modified_by - الأولوية الأولى والأهم)
                    if hasattr(instance, "_modified_by") and instance._modified_by:
                        changed_by = instance._modified_by

                    # 2. إذا لم نجد _modified_by، نستخدم منشئ المعاينة كبديل
                    elif hasattr(instance, "created_by") and instance.created_by:
                        changed_by = instance.created_by

                    # 3. كحل أخير، نستخدم فني المعاينة
                    elif hasattr(instance, "inspector") and instance.inspector:
                        changed_by = instance.inspector

                    # 4. البائع المسؤول كحل أخير
                    elif (
                        hasattr(instance, "responsible_employee")
                        and instance.responsible_employee
                    ):
                        # تحويل Salesperson إلى User إذا لزم الأمر
                        if hasattr(instance.responsible_employee, "user"):
                            changed_by = instance.responsible_employee.user
                        else:
                            changed_by = instance.responsible_employee

                    # إنشاء السجل مع تحديد أنه ليس تلقائي إذا وُجد مستخدم
                    OrderStatusLog.create_detailed_log(
                        order=instance.order,
                        change_type="status",
                        old_value=old_status,
                        new_value=instance.status,
                        changed_by=changed_by,
                        notes=f"تم تغيير حالة المعاينة",
                        is_automatic=changed_by is None,  # تلقائي فقط إذا لم نجد مستخدم
                    )
            except Exception as e:
                logger.error(f"خطأ في تتبع تغييرات المعاينة {instance.pk}: {e}")

    @receiver(pre_save, sender="inspections.Inspection")
    def track_inspection_changes_pre_save(sender, instance, **kwargs):
        """حفظ الحالة السابقة للمعاينة قبل التحديث"""
        if instance.pk:
            try:
                from inspections.models import Inspection

                old_instance = Inspection.objects.get(pk=instance.pk)
                instance._old_status = old_instance.status
            except Inspection.DoesNotExist:
                pass

except ImportError:
    logger.info("نموذج المعاينة غير متوفر")

try:

    @receiver(post_save, sender="cutting.CuttingOrder")
    def track_cutting_status_changes(sender, instance, created, **kwargs):
        """تتبع تغييرات حالة التقطيع"""
        if not created and instance.order:
            try:
                from cutting.models import CuttingOrder

                # استخدام الطريقة المباشرة للحصول على الحالة السابقة
                if (
                    hasattr(instance, "_old_status")
                    and instance._old_status != instance.status
                ):
                    # البحث عن المستخدم من مصادر مختلفة
                    changed_by = None

                    # 1. من instance التقطيع
                    if hasattr(instance, "_modified_by") and instance._modified_by:
                        changed_by = instance._modified_by

                    # 2. من حقول أخرى في نموذج التقطيع
                    elif hasattr(instance, "cutter_name") and instance.cutter_name:
                        # محاولة العثور على المستخدم من اسم القاطع
                        try:
                            from accounts.models import User

                            changed_by = User.objects.filter(
                                username__icontains=instance.cutter_name
                            ).first()
                        except:
                            pass
                    elif hasattr(instance, "created_by") and instance.created_by:
                        changed_by = instance.created_by

                    OrderStatusLog.create_detailed_log(
                        order=instance.order,
                        change_type="status",
                        old_value=instance._old_status,
                        new_value=instance.status,
                        changed_by=changed_by,
                        notes=f"تم تغيير حالة التقطيع",
                        is_automatic=changed_by is None,
                    )
            except Exception as e:
                logger.error(f"خطأ في تتبع تغييرات التقطيع {instance.pk}: {e}")

    @receiver(pre_save, sender="cutting.CuttingOrder")
    def track_cutting_changes_pre_save(sender, instance, **kwargs):
        """حفظ الحالة السابقة للتقطيع قبل التحديث"""
        if instance.pk:
            try:
                from cutting.models import CuttingOrder

                old_instance = CuttingOrder.objects.get(pk=instance.pk)
                instance._old_status = old_instance.status
            except CuttingOrder.DoesNotExist:
                pass

except ImportError:
    logger.info("نموذج التقطيع غير متوفر")

# إضافة signals للتركيب
try:

    @receiver(pre_save, sender="installations.InstallationSchedule")
    def track_installation_changes_pre_save(sender, instance, **kwargs):
        """حفظ الحالة السابقة للتركيب قبل التحديث"""
        if instance.pk:
            try:
                from installations.models import InstallationSchedule

                old_instance = InstallationSchedule.objects.get(pk=instance.pk)
                instance._old_status = old_instance.status
            except InstallationSchedule.DoesNotExist:
                pass

    @receiver(post_save, sender="installations.InstallationSchedule")
    def track_installation_status_changes(sender, instance, created, **kwargs):
        """تتبع تغييرات حالة التركيب"""
        if not created and instance.order:
            try:
                if (
                    hasattr(instance, "_old_status")
                    and instance._old_status != instance.status
                ):
                    # البحث عن المستخدم
                    changed_by = None

                    if hasattr(instance, "_modified_by") and instance._modified_by:
                        changed_by = instance._modified_by
                    elif hasattr(instance, "team") and instance.team:
                        # محاولة الحصول على قائد الفريق أو أول عضو
                        if hasattr(instance.team, "leader") and instance.team.leader:
                            changed_by = instance.team.leader
                        elif (
                            hasattr(instance.team, "members")
                            and instance.team.members.exists()
                        ):
                            changed_by = instance.team.members.first()
                    elif hasattr(instance, "created_by") and instance.created_by:
                        changed_by = instance.created_by

                    OrderStatusLog.create_detailed_log(
                        order=instance.order,
                        change_type="status",
                        old_value=instance._old_status,
                        new_value=instance.status,
                        changed_by=changed_by,
                        notes=f"تم تغيير حالة التركيب",
                        is_automatic=changed_by is None,
                    )
            except Exception as e:
                logger.error(f"خطأ في تتبع تغييرات التركيب {instance.pk}: {e}")

except ImportError:
    logger.info("نموذج التركيب غير متوفر")

# إضافة signals للتصنيع
try:

    @receiver(pre_save, sender="manufacturing.ManufacturingOrder")
    def track_manufacturing_changes_pre_save(sender, instance, **kwargs):
        """حفظ الحالة السابقة للتصنيع قبل التحديث"""
        if instance.pk:
            try:
                from manufacturing.models import ManufacturingOrder

                old_instance = ManufacturingOrder.objects.get(pk=instance.pk)
                instance._old_status = old_instance.status
            except ManufacturingOrder.DoesNotExist:
                pass

    @receiver(post_save, sender="manufacturing.ManufacturingOrder")
    def track_manufacturing_status_changes(sender, instance, created, **kwargs):
        """تتبع تغييرات حالة التصنيع - معطل لأننا ننشئ السجل يدوياً في manufacturing/views.py"""
        # تم تعطيل هذا الـ signal لأننا نريد فقط السجلات الحقيقية
        # التي يتم إنشاؤها من قبل المستخدمين في manufacturing/views.py
        # (السطر 1533-1565 في update_order_status)
        pass

except ImportError:
    logger.info("نموذج التصنيع غير متوفر")

logger.info("تم تحميل إشارات التخزين المؤقت للطلبات")
