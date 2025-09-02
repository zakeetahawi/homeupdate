from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InstallationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'installations'
    verbose_name = _('قسم التركيبات')

    def ready(self):
        import installations.signals 