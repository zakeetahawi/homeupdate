import os
import logging
from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

class CrmConfig(AppConfig):
    """Configuration for the CRM application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    verbose_name = 'إدارة النظام'
    
    def ready(self):
        """Initialize application when Django starts."""
        # Skip if this is a management command that doesn't need the sequence monitor
        if len(os.sys.argv) > 1 and os.sys.argv[1] in [
            'makemigrations', 'migrate', 'collectstatic', 'test', 'shell'
        ]:
            return

        # Only run in the main process, not during auto-reload
        is_runserver = 'runserver' in os.sys.argv
        is_main_process = not os.environ.get('RUN_MAIN')

        if is_runserver and is_main_process:
            # Let the auto-reload process handle initialization
            return
            
        try:
            # Import signals to connect them
            from . import signals  # noqa: F401
            
            # Initialize sequence monitor after all apps are loaded
            from django.db.models.signals import post_migrate
            from .signals import initialize_sequence_monitor
            
            # Connect to post_migrate to ensure the database is ready
            post_migrate.connect(
                self._delayed_init,
                sender=self,
                dispatch_uid='crm_sequence_monitor_init'
            )
            
            # Only run initialization immediately if not in a management command
            if not any(cmd in os.sys.argv for cmd in ['migrate', 'makemigrations']):
                self._delayed_init()

        except (ImportError, OperationalError, ProgrammingError) as e:
            logger.warning("Could not initialize sequence monitor: %s", e)

        # In development, handle the auto-reload case
        if is_runserver and not is_main_process and not hasattr(self, '_initialized'):
            self._initialized = True
            self._delayed_init()
    
    def _delayed_init(self, **kwargs):
        """Delayed initialization to ensure all models are loaded.
        
        Args:
            **kwargs: Additional keyword arguments, including 'app_config'.
        """
        # Skip if this is a migration for another app
        if kwargs.get('app_config') and kwargs['app_config'].name != self.name:
            return

        # Skip if already initialized in this process
        if hasattr(self, '_sequence_monitor_initialized'):
            return

        from .signals import initialize_sequence_monitor
        try:
            # Check if the sequence table exists before initializing
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_sequences LIMIT 1")

            # If we got here, the database is ready
            if initialize_sequence_monitor():
                self._sequence_monitor_initialized = True
                logger.info("Sequence monitor initialized successfully")

        except Exception as e:
            logger.error(
                "Error initializing sequence monitor: %s",
                e,
                exc_info=True
            )
