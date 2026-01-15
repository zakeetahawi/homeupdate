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
