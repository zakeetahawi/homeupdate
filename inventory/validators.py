"""
مدققات مخصصة لقسم المخزون
تتضمن التحقق من البيانات وضمان سلامتها
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_positive_number(value):
    """التحقق من أن الرقم موجب"""
    if value <= 0:
        raise ValidationError(_("القيمة يجب أن تكون أكبر من الصفر"))


def validate_non_negative_number(value):
    """التحقق من أن الرقم غير سالب"""
    if value < 0:
        raise ValidationError(_("القيمة لا يمكن أن تكون سالبة"))


def validate_code_format(value):
    """التحقق من صحة تنسيق الكود (حروف وأرقام وشرطات فقط)"""
    if not re.match(r"^[A-Za-z0-9\-_]+$", value):
        raise ValidationError(
            _(
                "الكود يجب أن يحتوي على حروف وأرقام وشرطات فقط (بدون مسافات أو رموز خاصة)"
            )
        )


def validate_barcode_format(value):
    """التحقق من صحة تنسيق الباركود"""
    if not re.match(r"^[A-Za-z0-9\-]+$", value):
        raise ValidationError(_("الباركود يجب أن يحتوي على حروف وأرقام وشرطات فقط"))


def validate_phone_number(value):
    """التحقق من صحة رقم الهاتف"""
    # إزالة المسافات والرموز
    cleaned = value.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    # التحقق من أن الرقم يحتوي على أرقام فقط (مع السماح بعلامة + في البداية)
    if not re.match(r"^\+?[0-9]{8,15}$", cleaned):
        raise ValidationError(_("رقم الهاتف غير صحيح. يجب أن يحتوي على 8-15 رقماً"))


def validate_email_domain(value):
    """التحقق من صحة نطاق البريد الإلكتروني"""
    # قائمة بالنطاقات المحظورة (يمكن تخصيصها)
    blocked_domains = ["tempmail.com", "throwaway.email", "10minutemail.com"]

    domain = value.split("@")[-1].lower()
    if domain in blocked_domains:
        raise ValidationError(
            _("هذا النطاق غير مسموح به. يرجى استخدام بريد إلكتروني حقيقي")
        )


def validate_stock_quantity(product, warehouse, quantity, transaction_type="out"):
    """
    التحقق من توفر الكمية المطلوبة في المخزون

    Args:
        product: المنتج
        warehouse: المستودع
        quantity: الكمية المطلوبة
        transaction_type: نوع الحركة (in أو out)
    """
    from .models import StockTransaction

    if transaction_type == "out":
        # الحصول على آخر رصيد
        last_transaction = (
            StockTransaction.objects.filter(product=product, warehouse=warehouse)
            .order_by("-transaction_date", "-id")
            .first()
        )

        current_stock = last_transaction.running_balance if last_transaction else 0

        if quantity > current_stock:
            raise ValidationError(
                _(
                    "الكمية المطلوبة ({requested}) أكبر من المتوفر في المخزون ({available})"
                ).format(requested=quantity, available=current_stock)
            )


def validate_transfer_warehouses(from_warehouse, to_warehouse):
    """التحقق من أن مستودعات التحويل مختلفة"""
    if from_warehouse == to_warehouse:
        raise ValidationError(_("لا يمكن التحويل من وإلى نفس المستودع"))


def validate_file_size(file, max_size_mb=10):
    """التحقق من حجم الملف"""
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            _("حجم الملف كبير جداً. الحد الأقصى {max_size} ميجابايت").format(
                max_size=max_size_mb
            )
        )


def validate_excel_file(file):
    """التحقق من صحة ملف Excel"""
    allowed_extensions = [".xlsx", ".xls"]
    file_ext = file.name[file.name.rfind(".") :].lower()

    if file_ext not in allowed_extensions:
        raise ValidationError(
            _("نوع الملف غير مدعوم. يرجى رفع ملف Excel بصيغة .xlsx أو .xls")
        )

    # التحقق من حجم الملف
    validate_file_size(file)


def validate_date_range(date_from, date_to):
    """التحقق من صحة نطاق التاريخ"""
    if date_from and date_to and date_from > date_to:
        raise ValidationError(_("تاريخ البداية يجب أن يكون قبل تاريخ النهاية"))


def validate_price_range(price_min, price_max):
    """التحقق من صحة نطاق السعر"""
    if price_min and price_max and price_min > price_max:
        raise ValidationError(_("السعر الأدنى يجب أن يكون أقل من السعر الأعلى"))


def validate_unique_code(model_class, code, instance=None):
    """
    التحقق من عدم تكرار الكود

    Args:
        model_class: فئة النموذج
        code: الكود المراد التحقق منه
        instance: الكائن الحالي (في حالة التعديل)
    """
    existing = model_class.objects.filter(code__iexact=code)
    if instance and instance.pk:
        existing = existing.exclude(pk=instance.pk)

    if existing.exists():
        raise ValidationError(_("يوجد سجل بنفس الكود بالفعل"))


def validate_warehouse_capacity(warehouse_location, additional_quantity=0):
    """
    التحقق من عدم تجاوز السعة القصوى للموقع

    Args:
        warehouse_location: موقع المستودع
        additional_quantity: الكمية الإضافية المراد إضافتها
    """
    if warehouse_location.capacity:
        available_capacity = warehouse_location.available_capacity
        if additional_quantity > available_capacity:
            raise ValidationError(
                _(
                    "السعة المتاحة ({available}) غير كافية للكمية المطلوبة ({requested})"
                ).format(available=available_capacity, requested=additional_quantity)
            )


def validate_expiry_date(manufacturing_date, expiry_date):
    """التحقق من أن تاريخ الصلاحية بعد تاريخ التصنيع"""
    if manufacturing_date and expiry_date and expiry_date <= manufacturing_date:
        raise ValidationError(_("تاريخ الصلاحية يجب أن يكون بعد تاريخ التصنيع"))


def validate_category_parent(category, parent):
    """
    التحقق من عدم إنشاء ارتباط دائري بين الفئات

    Args:
        category: الفئة الحالية
        parent: الفئة الأب المقترحة
    """
    if parent and category.pk:
        if parent.pk == category.pk:
            raise ValidationError(_("لا يمكن تعيين الفئة كأب لنفسها"))

        # التحقق من عدم إنشاء دائرة
        current_parent = parent
        while current_parent:
            if current_parent.pk == category.pk:
                raise ValidationError(_("لا يمكن إنشاء ارتباط دائري بين الفئات"))
            current_parent = current_parent.parent
