from django.apps import AppConfig


class ModernChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modern_chat'
    verbose_name = 'نظام الدردشة الحديث'
    
    def ready(self):
        import modern_chat.signals
