from django.apps import AppConfig


class PublicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "public"
    verbose_name = "صفحات عامة وإعدادات Cloudflare"

    def ready(self):
        """Register signals for Cloudflare sync"""
        from django.db.models.signals import post_delete, post_save

        from inventory.models import Product

        from . import signals

        # Connect product save signal
        post_save.connect(
            self._on_product_save,
            sender=Product,
            dispatch_uid="cloudflare_sync_product_save",
        )

        # Connect product delete signal
        post_delete.connect(
            self._on_product_delete,
            sender=Product,
            dispatch_uid="cloudflare_sync_product_delete",
        )

    def _on_product_save(self, sender, instance, created, **kwargs):
        """Handle product save - sync to Cloudflare"""
        from . import signals

        # Only sync after the transaction is committed to ensure product is saved
        if instance.code:
            from django.db import transaction

            transaction.on_commit(
                lambda: signals.sync_product_to_cloudflare_async(instance.pk)
            )

    def _on_product_delete(self, sender, instance, **kwargs):
        """Handle product delete - remove from Cloudflare"""
        from . import signals

        if instance.code:
            signals.delete_product_from_cloudflare_async(instance.code)
