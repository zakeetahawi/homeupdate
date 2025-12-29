"""
Cloudflare Workers Sync Module
Syncs product data from Django to Cloudflare KV
"""
import json
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CloudflareSync:
    """
    Handles synchronization of product data to Cloudflare Workers KV
    """
    
    def __init__(self):
        self.worker_url = getattr(settings, 'CLOUDFLARE_WORKER_URL', 'https://qr.elkhawaga.uk')
        self.api_key = getattr(settings, 'CLOUDFLARE_SYNC_API_KEY', None)
        self.enabled = getattr(settings, 'CLOUDFLARE_SYNC_ENABLED', False)
    
    def is_configured(self):
        """Check if Cloudflare sync is properly configured"""
        return all([self.worker_url, self.api_key, self.enabled])
    
    def _send_request(self, data):
        """Send sync request to Cloudflare Worker"""
        if not self.is_configured():
            logger.warning("Cloudflare sync is not configured")
            return False
            
        try:
            # logger.info(f"Sending sync request to {self.worker_url}/sync")
            response = requests.post(
                f"{self.worker_url}/sync",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'X-Sync-API-Key': self.api_key
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                # logger.info(f"Cloudflare sync successful: {result}")
                return True
            else:
                logger.error(f"Cloudflare sync failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloudflare sync request failed: {e}")
            return False
    
    def format_base_product(self, base_product):
        """Format BaseProduct data including its variants"""
        from inventory.models import ProductVariant
        from django.utils import timezone
        
        def _safe_str(value):
            try:
                return None if value is None else str(value)
            except Exception:
                return None

        # Basic Info
        data = {
            'code': _safe_str(base_product.code),
            'name': _safe_str(base_product.name),
            'description': _safe_str(base_product.description),
            'price': _safe_str(base_product.base_price),
            'currency': _safe_str(base_product.currency),
            'unit': _safe_str(base_product.get_unit_display() if hasattr(base_product, 'get_unit_display') else base_product.unit),
            'category': _safe_str(base_product.category.name if base_product.category else None),
            'updated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'type': 'base_product',
        }
        
        # Get Variants
        variants = []
        # Optimization: use prefetch if possible, but here we assume single item sync usually
        active_variants = base_product.variants.filter(is_active=True).select_related('color')
        
        for v in active_variants:
            color_name = v.color.name if v.color else 'Standard'
            color_hex = v.color.hex_code if (v.color and v.color.hex_code) else '#000000'
            
            variants.append({
                'code': _safe_str(v.full_code),
                'color_name': _safe_str(color_name),
                'color_hex': _safe_str(color_hex),
                'price': _safe_str(v.effective_price),
                'is_available': v.current_stock > 0,
            })
            
        data['variants'] = variants
        return data

    def format_product(self, product):
        """Format legacy/standalone product data"""
        from django.utils import timezone
        def _safe_str(value):
            try: return str(value) if value is not None else None
            except: return None

        unit = getattr(product, 'unit', None)
        category_name = product.category.name if getattr(product, 'category', None) else None

        return {
            'code': _safe_str(product.code),
            'name': _safe_str(product.name),
            'description': _safe_str(product.description),
            'price': _safe_str(product.price),
            'currency': _safe_str(getattr(product, 'currency', None)),
            'unit': _safe_str(unit),
            'category': _safe_str(category_name),
            'updated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'type': 'standalone',
            'variants': [] 
        }
    
    def sync_product(self, product_or_base):
        """Sync a single product (Base or Standard) to Cloudflare KV"""
        from inventory.models import BaseProduct
        from django.utils import timezone
        
        # Handle BaseProduct
        if isinstance(product_or_base, BaseProduct):
            if not product_or_base.code:
                return False
            data = {
                'action': 'sync_product',
                'product': self.format_base_product(product_or_base)
            }
            result = self._send_request(data)
            
            # ✅ Update database fields after successful sync
            if result:
                BaseProduct.objects.filter(pk=product_or_base.pk).update(
                    cloudflare_synced=True,
                    last_synced_at=timezone.now()
                )
                logger.info(f"✅ Updated DB: {product_or_base.code} marked as synced")
            
            return result
            
        # Handle Standard Product
        else:
            if not product_or_base.code:
                return False
            
            data = {
                'action': 'sync_product',
                'product': self.format_product(product_or_base)
            }
            return self._send_request(data)
            
    def sync_all_products(self, batch_size=50):
        """Sync all products (Base + Standalone) to Cloudflare KV"""
        from inventory.models import Product, BaseProduct, ProductVariant
        from django.utils import timezone
        
        synced = 0
        now = timezone.now()
        
        # 1. Sync Base Products
        base_products = BaseProduct.objects.filter(is_active=True)
        total_base = base_products.count()
        
        for i in range(0, total_base, batch_size):
            batch = base_products[i:i+batch_size]
            formatted = [self.format_base_product(p) for p in batch]
            
            data = {
                'action': 'sync_all',
                'products': formatted
            }
            if self._send_request(data):
                synced += len(formatted)
                # ✅ Update database for this batch
                batch_ids = [p.id for p in batch]
                BaseProduct.objects.filter(id__in=batch_ids).update(
                    cloudflare_synced=True,
                    last_synced_at=now
                )
                logger.info(f"✅ Batch {i//batch_size + 1}: Synced {len(formatted)} products")
        
        # 2. Sync Standalone Products (Orphans)
        linked_ids = ProductVariant.objects.filter(legacy_product__isnull=False).values_list('legacy_product_id', flat=True)
        orphans = Product.objects.filter(code__isnull=False).exclude(code='').exclude(id__in=linked_ids)
        total_orphans = orphans.count()
        
        for i in range(0, total_orphans, batch_size):
            batch = orphans[i:i+batch_size]
            formatted = [self.format_product(p) for p in batch]
            
            data = {
                'action': 'sync_all',
                'products': formatted
            }
            if self._send_request(data):
                synced += len(formatted)
                
        logger.info(f"✅ Synced {synced} items (Base+Orphans) to Cloudflare")
        return synced
    
    def delete_product(self, code):
        """Delete a product from Cloudflare KV"""
        data = {
            'action': 'delete_product',
            'code': code
        }
        return self._send_request(data)


# Singleton instance
_cloudflare_sync = None

def get_cloudflare_sync():
    """Get or create CloudflareSync instance"""
    global _cloudflare_sync
    if _cloudflare_sync is None:
        _cloudflare_sync = CloudflareSync()
    return _cloudflare_sync


def sync_product_to_cloudflare(product):
    """Convenience function to sync a product"""
    return get_cloudflare_sync().sync_product(product)


def sync_all_to_cloudflare():
    """Convenience function to sync all products"""
    return get_cloudflare_sync().sync_all_products()
