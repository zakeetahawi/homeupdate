from django.apps import AppConfig


class InstallationAccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "installation_accounting"
    verbose_name = "محاسبة التركيبات"

    def ready(self):
        import installation_accounting.signals
