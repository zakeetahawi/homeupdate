"""
نظام تتبع موحد لجميع التغييرات على الطلبات
"""

import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .middleware import get_current_user
from .models import Order, OrderItem, OrderStatusLog

logger = logging.getLogger(__name__)
User = get_user_model()

# قاموس الحقول المتتبعة مع أسمائها العربية
TRACKED_FIELDS = {
    "contract_number": "رقم العقد الأول",
    "contract_number_2": "رقم العقد الثاني",
    "contract_number_3": "رقم العقد الثالث",
    "invoice_number": "رقم الفاتورة الأولى",
    "invoice_number_2": "رقم الفاتورة الثانية",
    "invoice_number_3": "رقم الفاتورة الثالثة",
    "notes": "الملاحظات",
    "delivery_address": "عنوان التسليم",
    "location_address": "عنوان التركيب",
    "expected_delivery_date": "تاريخ التسليم المتوقع",
    "final_price": "السعر النهائي",
    "paid_amount": "المبلغ المدفوع",
    "order_status": "حالة الطلب",
    "customer": "العميل",
    "branch": "الفرع",
    "salesperson": "البائع",
    "delivery_type": "نوع التسليم",
    "order_date": "تاريخ الطلب",
}


@receiver(pre_save, sender=Order)
def unified_order_tracking_pre_save(sender, instance, **kwargs):
    """
    حفظ الحالة السابقة للطلب قبل التحديث
    """
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_instance = old_instance

            # تحديد المستخدم المسؤول عن التغيير
            if not hasattr(instance, "_modified_by") or not instance._modified_by:
                current_user = get_current_user()
                if current_user and current_user.is_authenticated:
                    instance._modified_by = current_user

        except Order.DoesNotExist:
            instance._old_instance = None


@receiver(post_save, sender=Order)
def unified_order_tracking_post_save(sender, instance, created, **kwargs):
    """
    تسجيل جميع التغييرات على الطلب بعد الحفظ
    """
    # تجاهل التتبع إذا كان الطلب قيد الحذف
    if getattr(instance, "_is_being_deleted", False):
        return

    if created:
        # طلب جديد
        user = getattr(instance, "_modified_by", None) or get_current_user()
        if user and user.is_authenticated:
            OrderStatusLog.create_detailed_log(
                order=instance,
                change_type="creation",
                old_value="",
                new_value=instance.order_number,
                changed_by=user,
                notes="تم إنشاء الطلب",
                field_name="إنشاء طلب",
                is_automatic=False,
            )
        return

    # تحديث طلب موجود
    old_instance = getattr(instance, "_old_instance", None)
    if not old_instance:
        return

    # المستخدم المسؤول عن التغيير
    user = getattr(instance, "_modified_by", None) or get_current_user()
    if not user or not user.is_authenticated:
        return  # لا نسجل التغييرات بدون مستخدم

    # تتبع التغييرات في الحقول المحددة
    for field_name, field_display in TRACKED_FIELDS.items():
        try:
            # الحصول على القيم الأصلية
            old_value_raw = getattr(old_instance, field_name, None)
            new_value_raw = getattr(instance, field_name, None)

            # تحويل القيم للعرض (نسخة منفصلة للعرض)
            old_value_display = old_value_raw
            new_value_display = new_value_raw

            # تحويل ForeignKey للعرض (تحسين للبائع والعميل والفرع)
            if field_name in ["salesperson", "customer", "branch"]:
                # معالجة خاصة للـ ForeignKey
                if old_value_raw:
                    if hasattr(old_value_raw, "name"):
                        old_value_display = old_value_raw.name
                    elif hasattr(old_value_raw, "username"):
                        old_value_display = old_value_raw.username
                    else:
                        old_value_display = str(old_value_raw)
                else:
                    old_value_display = "غير محدد"

                if new_value_raw:
                    if hasattr(new_value_raw, "name"):
                        new_value_display = new_value_raw.name
                    elif hasattr(new_value_raw, "username"):
                        new_value_display = new_value_raw.username
                    else:
                        new_value_display = str(new_value_raw)
                else:
                    new_value_display = "غير محدد"
            elif hasattr(old_value_raw, "pk"):  # ForeignKey عام
                old_value_display = str(old_value_raw) if old_value_raw else "غير محدد"
            elif hasattr(new_value_raw, "pk"):  # ForeignKey عام
                new_value_display = str(new_value_raw) if new_value_raw else "غير محدد"

            # تحويل التواريخ للعرض
            if hasattr(old_value_raw, "strftime"):
                old_value_display = (
                    old_value_raw.strftime("%Y-%m-%d") if old_value_raw else "غير محدد"
                )
            if hasattr(new_value_raw, "strftime"):
                new_value_display = (
                    new_value_raw.strftime("%Y-%m-%d") if new_value_raw else "غير محدد"
                )

            # تحويل القيم الفارغة للعرض
            if old_value_display in [None, ""]:
                old_value_display = "غير محدد"
            if new_value_display in [None, ""]:
                new_value_display = "غير محدد"

            # المقارنة المحسنة للـ ForeignKey
            if field_name in ["salesperson", "customer", "branch"]:
                # للـ ForeignKey، قارن بالـ pk
                old_compare = old_value_raw.pk if old_value_raw else None
                new_compare = new_value_raw.pk if new_value_raw else None
            else:
                # للحقول الأخرى، قارن بالنص
                old_compare = (
                    str(old_value_raw) if old_value_raw not in [None, ""] else ""
                )
                new_compare = (
                    str(new_value_raw) if new_value_raw not in [None, ""] else ""
                )

            # تسجيل التغيير إذا كان هناك اختلاف
            if old_compare != new_compare:
                # تحديد نوع التغيير
                change_type = "general"
                if field_name == "order_status":
                    change_type = "status"
                elif field_name in ["final_price", "paid_amount"]:
                    change_type = "price"
                elif field_name == "expected_delivery_date":
                    change_type = "date"
                elif field_name == "customer":
                    change_type = "customer"

                # إنشاء رسالة واضحة
                if field_name in [
                    "contract_number",
                    "contract_number_2",
                    "contract_number_3",
                ]:
                    notes = f"تم تحديث {field_display}"
                elif field_name in [
                    "invoice_number",
                    "invoice_number_2",
                    "invoice_number_3",
                ]:
                    notes = f"تم تحديث {field_display}"
                elif field_name == "notes":
                    notes = "تم تحديث ملاحظات الطلب"
                elif field_name == "expected_delivery_date":
                    notes = f"تم تغيير تاريخ التسليم المتوقع من {old_value_display} إلى {new_value_display}"
                elif field_name == "order_status":
                    notes = f'تم تغيير حالة الطلب من "{old_value_display}" إلى "{new_value_display}"'
                elif field_name == "customer":
                    notes = f'تم تغيير العميل من "{old_value_display}" إلى "{new_value_display}"'
                elif field_name == "branch":
                    notes = f'تم تغيير الفرع من "{old_value_display}" إلى "{new_value_display}"'
                elif field_name == "salesperson":
                    notes = f'تم تغيير البائع من "{old_value_display}" إلى "{new_value_display}"'
                else:
                    notes = f'تم تحديث {field_display} من "{old_value_display}" إلى "{new_value_display}"'

                # تسجيل التغيير
                OrderStatusLog.create_detailed_log(
                    order=instance,
                    change_type=change_type,
                    old_value=old_value_display,
                    new_value=new_value_display,
                    changed_by=user,
                    notes=notes,
                    field_name=field_display,
                    is_automatic=False,
                )

        except Exception as e:
            logger.error(
                f"خطأ في تتبع تغيير الحقل {field_name} للطلب {instance.pk}: {e}"
            )


def track_order_change(order, user, field_name, old_value, new_value, notes=None):
    """
    دالة مساعدة لتسجيل تغيير محدد في الطلب

    Args:
        order: الطلب
        user: المستخدم
        field_name: اسم الحقل
        old_value: القيمة القديمة
        new_value: القيمة الجديدة
        notes: ملاحظات إضافية
    """
    if not user or not user.is_authenticated:
        return

    field_display = TRACKED_FIELDS.get(field_name, field_name)

    if not notes:
        notes = f"تم تحديث {field_display}"

    change_type = "general"
    if field_name == "order_status":
        change_type = "status"
    elif field_name in ["final_price", "paid_amount"]:
        change_type = "price"
    elif field_name == "expected_delivery_date":
        change_type = "date"
    elif field_name == "customer":
        change_type = "customer"

    OrderStatusLog.create_detailed_log(
        order=order,
        change_type=change_type,
        old_value=str(old_value) if old_value else "غير محدد",
        new_value=str(new_value) if new_value else "غير محدد",
        changed_by=user,
        notes=notes,
        field_name=field_display,
        is_automatic=False,
    )


# ===== تتبع عناصر الطلب (OrderItem) =====


@receiver(pre_save, sender=OrderItem)
def orderitem_tracking_pre_save(sender, instance, **kwargs):
    """حفظ حالة عنصر الطلب قبل التعديل"""
    if instance.pk:
        try:
            old_instance = OrderItem.objects.get(pk=instance.pk)
            instance._old_instance = old_instance

            # تعيين المستخدم المعدل إذا لم يكن محدد
            if not hasattr(instance, "_modified_by") or not instance._modified_by:
                current_user = get_current_user()
                if current_user and current_user.is_authenticated:
                    instance._modified_by = current_user
        except OrderItem.DoesNotExist:
            instance._old_instance = None


@receiver(post_save, sender=OrderItem)
def orderitem_tracking_post_save(sender, instance, created, **kwargs):
    """تتبع التغييرات على عناصر الطلب"""

    # تجاهل التتبع إذا كان الطلب قيد الحذف
    if instance.order and getattr(instance.order, "_is_being_deleted", False):
        return

    # المستخدم المسؤول عن التغيير
    user = getattr(instance, "_modified_by", None) or get_current_user()
    if not user or not user.is_authenticated:
        return  # لا نسجل التغييرات بدون مستخدم

    if created:
        # عنصر جديد تم إضافته
        product_name = str(instance.product) if instance.product else "غير محدد"
        quantity = instance.quantity or 0
        unit_price = instance.unit_price or 0
        notes = instance.notes or "بدون ملاحظات"

        log_notes = f"تم إضافة عنصر جديد: {product_name} (الكمية: {quantity}, السعر: {unit_price} ج.م, ملاحظات: {notes})"

        OrderStatusLog.create_detailed_log(
            order=instance.order,
            change_type="general",
            old_value="غير موجود",
            new_value=f"{product_name} - كمية: {quantity} - سعر: {unit_price}",
            changed_by=user,
            notes=log_notes,
            field_name="إضافة عنصر جديد",
            is_automatic=False,
        )

    elif hasattr(instance, "_old_instance") and instance._old_instance:
        # عنصر موجود تم تعديله
        old_instance = instance._old_instance
        changes = []

        # تتبع التغييرات في الحقول
        fields_to_track = {
            "product": "المنتج",
            "quantity": "الكمية",
            "unit_price": "سعر الوحدة",
            "notes": "الملاحظات",
        }

        for field_name, field_display in fields_to_track.items():
            old_value = getattr(old_instance, field_name, None)
            new_value = getattr(instance, field_name, None)

            # تحويل القيم للمقارنة
            if field_name == "product":
                old_str = str(old_value) if old_value else "غير محدد"
                new_str = str(new_value) if new_value else "غير محدد"
            elif field_name in ["quantity", "unit_price"]:
                old_str = str(old_value) if old_value is not None else "0"
                new_str = str(new_value) if new_value is not None else "0"
            else:
                old_str = str(old_value) if old_value else "غير محدد"
                new_str = str(new_value) if new_value else "غير محدد"

            if old_str != new_str:
                changes.append(f"{field_display}: {old_str} → {new_str}")

        if changes:
            product_name = str(instance.product) if instance.product else "غير محدد"
            changes_text = " | ".join(changes)
            log_notes = f"تم تعديل عنصر الطلب: {product_name} - {changes_text}"

            OrderStatusLog.create_detailed_log(
                order=instance.order,
                change_type="general",
                old_value="عنصر معدل",
                new_value=changes_text,
                changed_by=user,
                notes=log_notes,
                field_name="تعديل عنصر الطلب",
                is_automatic=False,
            )
