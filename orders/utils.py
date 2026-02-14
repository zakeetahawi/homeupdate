"""
أدوات مساعدة لنظام الطلبات
"""


def set_user_for_status_tracking(instance, user):
    """
    تعيين المستخدم لتتبع تغييرات الحالة

    Args:
        instance: النموذج المراد تتبع تغييراته
        user: المستخدم الذي قام بالتغيير
    """
    if user and user.is_authenticated:
        instance._modified_by = user


def track_inspection_status_change(inspection, user, old_status=None):
    """
    تتبع تغيير حالة المعاينة مع تحديد المستخدم

    Args:
        inspection: نموذج المعاينة
        user: المستخدم الذي قام بالتغيير
        old_status: الحالة السابقة (اختياري)
    """
    if old_status:
        inspection._old_status = old_status
    set_user_for_status_tracking(inspection, user)


def update_inspection_status_with_user(inspection, new_status, user):
    """
    تحديث حالة المعاينة مع ضمان تسجيل المستخدم الصحيح

    Args:
        inspection: نموذج المعاينة
        new_status: الحالة الجديدة
        user: المستخدم الذي قام بالتغيير
    """
    old_status = inspection.status
    inspection.status = new_status
    track_inspection_status_change(inspection, user, old_status)
    return inspection


def track_installation_status_change(installation, user, old_status=None):
    """
    تتبع تغيير حالة التركيب مع تحديد المستخدم

    Args:
        installation: نموذج التركيب
        user: المستخدم الذي قام بالتغيير
        old_status: الحالة السابقة (اختياري)
    """
    if old_status:
        installation._old_status = old_status
    set_user_for_status_tracking(installation, user)


def track_manufacturing_status_change(manufacturing_order, user, old_status=None):
    """
    تتبع تغيير حالة التصنيع مع تحديد المستخدم

    Args:
        manufacturing_order: نموذج التصنيع
        user: المستخدم الذي قام بالتغيير
        old_status: الحالة السابقة (اختياري)
    """
    if old_status:
        manufacturing_order._old_status = old_status
    set_user_for_status_tracking(manufacturing_order, user)


def track_cutting_status_change(cutting_order, user, old_status=None):
    """
    تتبع تغيير حالة التقطيع مع تحديد المستخدم

    Args:
        cutting_order: نموذج التقطيع
        user: المستخدم الذي قام بالتغيير
        old_status: الحالة السابقة (اختياري)
    """
    if old_status:
        cutting_order._old_status = old_status
    set_user_for_status_tracking(cutting_order, user)


# دالة مساعدة لتحديث حالة الطلب مع تتبع المستخدم
def update_order_status(order, new_status, user, status_type="order_status"):
    """
    تحديث حالة الطلب مع تتبع المستخدم

    Args:
        order: نموذج الطلب
        new_status: الحالة الجديدة
        user: المستخدم الذي قام بالتغيير
        status_type: نوع الحالة ('order_status' أو 'inspection_status')
    """
    if status_type == "order_status":
        old_status = order.order_status
        order.order_status = new_status
    elif status_type == "inspection_status":
        old_status = order.inspection_status
        order.inspection_status = new_status
    else:
        return False

    # تعيين المستخدم للتتبع
    set_user_for_status_tracking(order, user)

    return True


# دالة لإنشاء سجل حالة يدوي
def create_manual_status_log(
    order, change_type, old_value, new_value, user, notes=None, field_name=None
):
    """
    إنشاء سجل حالة يدوي

    Args:
        order: الطلب
        change_type: نوع التغيير
        old_value: القيمة السابقة
        new_value: القيمة الجديدة
        user: المستخدم
        notes: ملاحظات إضافية
        field_name: اسم الحقل
    """
    from .models import OrderStatusLog

    return OrderStatusLog.create_detailed_log(
        order=order,
        change_type=change_type,
        old_value=old_value,
        new_value=new_value,
        changed_by=user,
        notes=notes or f'تم تغيير {field_name or "الحالة"}',
        field_name=field_name,
        is_automatic=False,
    )


# دالة للتحقق من صلاحية المستخدم لتعديل الطلب
def can_user_modify_order(user, order):
    """
    التحقق من صلاحية المستخدم لتعديل الطلب

    Args:
        user: المستخدم
        order: الطلب

    Returns:
        bool: True إذا كان المستخدم يمكنه التعديل
    """
    if not user or not user.is_authenticated:
        return False

    # المدير العام يمكنه تعديل كل شيء
    if user.is_superuser:
        return True

    # المستخدم يمكنه تعديل طلبات فرعه فقط
    if hasattr(user, "branch") and hasattr(order, "branch"):
        return user.branch == order.branch

    return True  # افتراضي للمستخدمين الآخرين


# دالة لتسجيل تغييرات متعددة في مرة واحدة
def log_multiple_changes(order, changes_dict, user):
    """
    تسجيل تغييرات متعددة في مرة واحدة

    Args:
        order: الطلب
        changes_dict: قاموس التغييرات {'field_name': {'old': old_value, 'new': new_value, 'type': change_type}}
        user: المستخدم
    """
    from .models import OrderStatusLog

    logs_created = []

    for field_name, change_data in changes_dict.items():
        if change_data["old"] != change_data["new"]:
            log = create_manual_status_log(
                order=order,
                change_type=change_data.get("type", "general"),
                old_value=change_data["old"],
                new_value=change_data["new"],
                user=user,
                field_name=field_name,
            )
            logs_created.append(log)

    return logs_created


# دالة لتنظيف السجلات القديمة (اختيارية)
def update_order_contract_invoice(order, user, **kwargs):
    """
    تحديث أرقام العقود والفواتير مع تتبع المستخدم

    Args:
        order: الطلب
        user: المستخدم
        **kwargs: الحقول المراد تحديثها (contract_number, invoice_number, etc.)
    """
    changes_made = []

    # تعيين المستخدم للتتبع
    set_user_for_status_tracking(order, user)

    # تحديث الحقول
    for field_name, new_value in kwargs.items():
        if hasattr(order, field_name):
            old_value = getattr(order, field_name)
            if old_value != new_value:
                setattr(order, field_name, new_value)
                changes_made.append(
                    {"field": field_name, "old": old_value, "new": new_value}
                )

    return changes_made


def cleanup_old_status_logs(days_to_keep=365):
    """
    تنظيف السجلات القديمة

    Args:
        days_to_keep: عدد الأيام للاحتفاظ بالسجلات
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models import OrderStatusLog

    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    deleted_count = OrderStatusLog.objects.filter(
        created_at__lt=cutoff_date, is_automatic=True  # حذف السجلات التلقائية فقط
    ).delete()

    return deleted_count[0] if deleted_count else 0


# دالة لإنشاء مثال على كيفية استخدام النظام في Views
def example_view_usage():
    """
    مثال على كيفية استخدام النظام في Views
    """
    example_code = """
    # في views.py
    from orders.utils import (
        update_order_status,
        update_inspection_status_with_user,
        update_order_contract_invoice
    )

    def update_order_view(request, order_id):
        order = get_object_or_404(Order, pk=order_id)

        # تحديث حالة الطلب
        if update_order_status(order, 'completed', request.user):
            order.save()

        # تحديث أرقام العقود والفواتير
        changes = update_order_contract_invoice(
            order,
            request.user,
            contract_number='C-2024-001',
            invoice_number='INV-2024-001'
        )
        if changes:
            order.save()

    def update_inspection_view(request, inspection_id):
        inspection = get_object_or_404(Inspection, pk=inspection_id)

        # تحديث حالة المعاينة مع ضمان تسجيل المستخدم
        inspection = update_inspection_status_with_user(
            inspection,
            'completed',
            request.user
        )
        inspection.save()
    """
    return example_code


def update_order_with_tracking(order, user, **field_updates):
    """
    تحديث حقول الطلب مع ضمان التتبع الصحيح

    Args:
        order: نموذج الطلب
        user: المستخدم الذي يقوم بالتحديث
        **field_updates: الحقول المراد تحديثها

    Returns:
        list: قائمة بالتغييرات التي تمت
    """
    changes_made = []

    # تعيين المستخدم للتتبع
    set_user_for_status_tracking(order, user)

    # تحديث الحقول
    for field_name, new_value in field_updates.items():
        if hasattr(order, field_name):
            old_value = getattr(order, field_name)
            if old_value != new_value:
                setattr(order, field_name, new_value)
                changes_made.append(
                    {"field": field_name, "old": old_value, "new": new_value}
                )

    return changes_made


def update_order_items_with_tracking(order, user, items_data):
    """
    تحديث عناصر الطلب مع ضمان التتبع

    Args:
        order: نموذج الطلب
        user: المستخدم
        items_data: بيانات العناصر الجديدة/المحدثة

    Returns:
        dict: ملخص التغييرات
    """
    from .models import OrderItem

    changes = {"added": [], "updated": [], "deleted": []}

    # تعيين المستخدم للتتبع
    set_user_for_status_tracking(order, user)

    # معالجة العناصر الجديدة/المحدثة
    for item_data in items_data:
        item_id = item_data.get("id")

        if item_id:
            # تحديث عنصر موجود
            try:
                item = OrderItem.objects.get(id=item_id, order=order)
                item._modified_by = user

                old_values = {}
                for field in ["quantity", "unit_price", "discount_percentage"]:
                    if field in item_data:
                        old_values[field] = getattr(item, field)
                        setattr(item, field, item_data[field])

                if item_data.get("product_id"):
                    old_values["product"] = item.product.name if item.product else None
                    from inventory.models import Product

                    item.product = Product.objects.get(id=item_data["product_id"])

                item.save()
                changes["updated"].append(
                    {
                        "item_id": item_id,
                        "old_values": old_values,
                        "new_values": item_data,
                    }
                )

            except OrderItem.DoesNotExist:
                pass
        else:
            # إضافة عنصر جديد
            if item_data.get("product_id"):
                from inventory.models import Product

                product = Product.objects.get(id=item_data["product_id"])

                item = OrderItem(
                    order=order,
                    product=product,
                    quantity=item_data.get("quantity", 1),
                    unit_price=item_data.get("unit_price", 0),
                    discount_percentage=item_data.get("discount_percentage", 0),
                )
                # تعيين المستخدم قبل الحفظ
                item._modified_by = user
                item.save()

                changes["added"].append(
                    {
                        "item_id": item.id,
                        "product_name": product.name,
                        "quantity": item.quantity,
                    }
                )

    return changes


def update_contract_invoice_numbers(order, user, **updates):
    """
    تحديث أرقام العقود والفواتير مع ضمان التتبع

    Args:
        order: نموذج الطلب
        user: المستخدم
        **updates: الحقول المراد تحديثها (contract_number, invoice_number, etc.)

    Returns:
        list: قائمة بالتغييرات
    """
    changes = []

    # تعيين المستخدم للتتبع
    set_user_for_status_tracking(order, user)

    # الحقول المدعومة
    supported_fields = [
        "contract_number",
        "contract_number_2",
        "contract_number_3",
        "invoice_number",
        "invoice_number_2",
        "invoice_number_3",
    ]

    for field_name, new_value in updates.items():
        if field_name in supported_fields and hasattr(order, field_name):
            old_value = getattr(order, field_name)
            if old_value != new_value:
                setattr(order, field_name, new_value)
                changes.append(
                    {"field": field_name, "old": old_value, "new": new_value}
                )

    return changes


def quick_update_order(order, user, **updates):
    """
    تحديث سريع للطلب مع ضمان التتبع

    مثال الاستخدام:
    quick_update_order(order, request.user,
                      contract_number='C-2024-001',
                      invoice_number='INV-2024-001',
                      notes='ملاحظات جديدة')
    """
    from accounts.middleware.current_user import set_current_user
    from .tracking import track_order_change

    # تعيين المستخدم الحالي
    set_current_user(user)

    changes = []
    for field_name, new_value in updates.items():
        if hasattr(order, field_name):
            old_value = getattr(order, field_name)
            if old_value != new_value:
                # تسجيل التغيير
                track_order_change(
                    order=order,
                    user=user,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                )

                # تطبيق التغيير
                setattr(order, field_name, new_value)
                changes.append(f"{field_name}: {old_value} → {new_value}")

    if changes:
        # حفظ الطلب بدون تشغيل signals إضافية
        order.save(update_fields=list(updates.keys()))
        return f'تم تحديث {len(changes)} حقل: {", ".join(changes)}'
    else:
        return "لا توجد تغييرات"


def simple_order_update(order, user, **updates):
    """
    تحديث بسيط للطلب مع تتبع تلقائي

    Args:
        order: الطلب
        user: المستخدم
        **updates: الحقول المراد تحديثها

    Returns:
        int: عدد التغييرات المسجلة
    """
    from .tracking import track_order_change

    changes_count = 0

    for field_name, new_value in updates.items():
        if hasattr(order, field_name):
            old_value = getattr(order, field_name)

            # تحويل القيم للمقارنة
            old_str = str(old_value) if old_value not in [None, ""] else "غير محدد"
            new_str = str(new_value) if new_value not in [None, ""] else "غير محدد"

            if old_str != new_str:
                # تسجيل التغيير
                track_order_change(
                    order=order,
                    user=user,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                )

                # تطبيق التغيير
                setattr(order, field_name, new_value)
                changes_count += 1

    # حفظ الطلب إذا كان هناك تغييرات
    if changes_count > 0:
        order.save(update_fields=list(updates.keys()))

    return changes_count
