"""
Middleware لإضافة متغيرات النظام إلى كل طلب
System Settings Context Middleware
"""
from django.utils.functional import SimpleLazyObject
from .models_settings import SystemSettings


def get_system_settings(request):
    """الحصول على إعدادات النظام"""
    if not hasattr(request, '_cached_system_settings'):
        request._cached_system_settings = SystemSettings.get_settings()
    return request._cached_system_settings


class SystemSettingsMiddleware:
    """
    Middleware لإضافة إعدادات النظام لكل طلب
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # إضافة الإعدادات للطلب
        request.system_settings = SimpleLazyObject(lambda: get_system_settings(request))
        
        # معالجة الطلب
        response = self.get_response(request)
        
        return response


def system_settings_context(request):
    """
    Context processor لإضافة إعدادات النظام للقوالب
    """
    settings = SystemSettings.get_settings()
    
    return {
        'system_settings': settings,
        'wizard_enabled': settings.order_system in ['wizard', 'both'] and not settings.hide_wizard_system,
        'legacy_enabled': settings.order_system in ['legacy', 'both'] and not settings.hide_legacy_system,
        'show_wizard_button': settings.order_system in ['wizard', 'both'] and not settings.hide_wizard_system,
        'show_legacy_button': settings.order_system in ['legacy', 'both'] and not settings.hide_legacy_system,
    }
