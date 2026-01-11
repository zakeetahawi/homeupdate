"""
Signals for automatic Cloudflare sync
"""

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def sync_product_to_cloudflare_async(product_id):
    """
    Sync product to Cloudflare in background
    Uses threading to avoid blocking the save operation
    """
    import threading

    def do_sync():
        try:
            from inventory.models import Product
            from public.cloudflare_sync import sync_product_to_cloudflare
            from public.models import CloudflareSettings

            # Check if sync is enabled in admin settings
            try:
                cf_settings = CloudflareSettings.get_settings()
                if not cf_settings.is_enabled or not cf_settings.auto_sync_on_save:
                    return
            except Exception:
                # If settings don't exist, check environment
                if not getattr(settings, "CLOUDFLARE_SYNC_ENABLED", False):
                    return

            product = Product.objects.get(pk=product_id)
            if product.code:
                result = sync_product_to_cloudflare(product)
                if result:
                    logger.info(f"Product {product.code} synced to Cloudflare")
                else:
                    logger.warning(
                        f"Failed to sync product {product.code} to Cloudflare"
                    )

        except Exception as e:
            logger.error(f"Error syncing product {product_id} to Cloudflare: {e}")

    # Run in background thread
    thread = threading.Thread(target=do_sync, daemon=True)
    thread.start()


def delete_product_from_cloudflare_async(product_code):
    """
    Delete product from Cloudflare in background
    """
    import threading

    def do_delete():
        try:
            from public.cloudflare_sync import get_cloudflare_sync
            from public.models import CloudflareSettings

            # Check if sync is enabled
            try:
                cf_settings = CloudflareSettings.get_settings()
                if not cf_settings.is_enabled:
                    return
            except Exception:
                if not getattr(settings, "CLOUDFLARE_SYNC_ENABLED", False):
                    return

            sync = get_cloudflare_sync()
            if sync.is_configured():
                result = sync.delete_product(product_code)
                if result:
                    logger.info(f"Product {product_code} deleted from Cloudflare")

        except Exception as e:
            logger.error(f"Error deleting product {product_code} from Cloudflare: {e}")

    thread = threading.Thread(target=do_delete, daemon=True)
    thread.start()
