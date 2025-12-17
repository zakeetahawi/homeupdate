from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Import signal handlers
        from . import signals  # noqa
        from .signals import department_signals  # noqa
        # Note: Database operations have been moved to management commands
        # that should be run manually or during deployment
