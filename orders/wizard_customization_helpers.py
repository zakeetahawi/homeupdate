"""
دالة مساعدة لدمج خيارات الويزارد المخصصة مع النماذج
Helper function to integrate custom wizard options with forms
"""
from .wizard_customization_models import WizardFieldOption


def get_wizard_field_choices(field_type, include_empty=False):
    """
    الحصول على خيارات حقل من نظام التخصيص
    Get field choices from customization system
    
    Args:
        field_type (str): نوع الحقل (مثل: 'tailoring_type', 'installation_type')
        include_empty (bool): هل نضيف خيار فارغ في البداية؟
    
    Returns:
        list: قائمة الخيارات [(value, display_name), ...]
    """
    try:
        choices = WizardFieldOption.get_choices_for_field(field_type)
        
        if include_empty and choices:
            choices.insert(0, ('', '---------'))
        
        return choices
    except Exception as e:
        # في حالة الخطأ، إرجاع قائمة فارغة
        print(f"Error getting wizard field choices for {field_type}: {e}")
        return []


def get_wizard_field_default(field_type):
    """
    الحصول على القيمة الافتراضية لحقل
    Get default value for a field
    
    Args:
        field_type (str): نوع الحقل
    
    Returns:
        str or None: القيمة الافتراضية أو None
    """
    try:
        default_option = WizardFieldOption.get_default_for_field(field_type)
        return default_option.value if default_option else None
    except Exception as e:
        print(f"Error getting wizard field default for {field_type}: {e}")
        return None


def get_wizard_settings():
    """
    الحصول على إعدادات الويزارد العامة
    Get global wizard settings
    
    Returns:
        WizardGlobalSettings: كائن الإعدادات
    """
    from .wizard_customization_models import WizardGlobalSettings
    return WizardGlobalSettings.get_settings()


def update_form_field_choices(form, field_name, field_type):
    """
    تحديث خيارات حقل في نموذج Django
    Update field choices in a Django form
    
    Args:
        form: نموذج Django
        field_name (str): اسم الحقل في النموذج
        field_type (str): نوع الحقل في نظام التخصيص
    """
    if field_name in form.fields:
        choices = get_wizard_field_choices(field_type)
        if choices:
            form.fields[field_name].choices = choices
            
            # تحديث القيمة الافتراضية إذا لم تكن محددة
            default = get_wizard_field_default(field_type)
            if default and not form.fields[field_name].initial:
                form.fields[field_name].initial = default


# خريطة ربط أسماء الحقول بأنواعها في نظام التخصيص
FIELD_TYPE_MAPPING = {
    'tailoring_type': 'tailoring_type',
    'installation_type': 'installation_type',
    'fabric_type': 'fabric_type',
    'payment_method': 'payment_method',
    'status': 'order_status',
    'selected_type': 'order_type',
}


def auto_update_wizard_form_fields(form):
    """
    تحديث جميع حقول النموذج تلقائياً من نظام التخصيص
    Auto-update all form fields from customization system
    
    Args:
        form: نموذج Django
    """
    for field_name, field_type in FIELD_TYPE_MAPPING.items():
        update_form_field_choices(form, field_name, field_type)
