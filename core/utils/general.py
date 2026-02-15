"""
Core utility functions for the entire system
دوال مساعدة عامة للنظام بأكمله
"""


def convert_arabic_numbers_to_english(text):
    """
    تحويل الأرقام العربية إلى إنجليزية في النص
    Convert Arabic numerals (٠-٩) to English numerals (0-9)

    Args:
        text: النص المراد تحويله

    Returns:
        النص بعد تحويل الأرقام العربية إلى إنجليزية
    """
    if not text:
        return text

    arabic_to_english = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return text.translate(arabic_to_english)


def convert_model_arabic_numbers(instance, field_names):
    """
    تحويل الأرقام العربية إلى إنجليزية في حقول النموذج المحددة
    Convert Arabic numbers to English in specified model fields

    Args:
        instance: نسخة النموذج
        field_names: قائمة أسماء الحقول المراد تحويلها

    Usage:
        # في save method للنموذج
        from core.utils import convert_model_arabic_numbers

        def save(self, *args, **kwargs):
            convert_model_arabic_numbers(self, ['invoice_number', 'contract_number'])
            super().save(*args, **kwargs)
    """
    for field_name in field_names:
        field_value = getattr(instance, field_name, None)
        if field_value:
            converted_value = convert_arabic_numbers_to_english(field_value)
            setattr(instance, field_name, converted_value)


# ── مساعدات التحقق من الهاتف ──────────────────────────────────
import re


def clean_phone_number(value):
    """
    تنظيف رقم هاتف والتحقق من صيغته (Egypt: 01xxxxxxxxx).

    يُنظِّف الرقم من أي رموز أو مسافات ثم يُحقّق أنه 11 رقماً يبدأ بـ 01.
    يُرجع الرقم المُنظَّف أو يرفع ValidationError.

    Usage:
        from core.utils.general import clean_phone_number
        phone = clean_phone_number(raw_input)  # returns cleaned value or raises
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext_lazy as _

    if not value:
        return value

    # تحويل الأرقام العربية إلى إنجليزية أولاً
    value = convert_arabic_numbers_to_english(str(value))
    # إزالة جميع الرموز والمسافات
    value = re.sub(r"[^\d]", "", value)

    if not re.match(r"^01[0-9]{9}$", value):
        raise ValidationError(
            _("رقم الهاتف يجب أن يكون 11 رقم ويبدأ بـ 01 (مثال: 01234567890)"),
            code="invalid_phone_format",
        )

    return value
