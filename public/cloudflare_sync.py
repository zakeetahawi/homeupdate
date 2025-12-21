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
        self.worker_url = getattr(settings, 'CLOUDFLARE_WORKER_URL', None)
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
            response = requests.post(
                f"{self.worker_url}/sync",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'X-Sync-API-Key': self.api_key
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Cloudflare sync successful: {result}")
                return True
            else:
                logger.error(f"Cloudflare sync failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Cloudflare sync request failed: {e}")
            return False
    
    def format_product(self, product):
        """Format product data for Cloudflare KV"""
        from django.utils import timezone
        
        return {
            'code': product.code,
            'name': product.name,
            'price': str(product.price),
            'currency': product.currency,
            'unit': product.get_unit_display() if hasattr(product, 'get_unit_display') else product.unit,
            'category': product.category.name if product.category else None,
            'updated_at': timezone.now().strftime('%Y-%m-%d %H:%M'),
        }
    
    def sync_product(self, product):
        """Sync a single product to Cloudflare KV"""
        if not product.code:
            return False
        
        data = {
            'action': 'sync_product',
            'product': self.format_product(product)
        }
        
        return self._send_request(data)
    
    def sync_all_products(self, batch_size=100):
        """Sync all products to Cloudflare KV"""
        from inventory.models import Product
        
        products = Product.objects.exclude(code__isnull=True).exclude(code='').select_related('category')
        total = products.count()
        synced = 0
        
        for i in range(0, total, batch_size):
            batch = products[i:i+batch_size]
            formatted_products = [self.format_product(p) for p in batch]
            
            data = {
                'action': 'sync_all',
                'products': formatted_products
            }
            
            if self._send_request(data):
                synced += len(formatted_products)
        
        logger.info(f"Synced {synced}/{total} products to Cloudflare")
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
