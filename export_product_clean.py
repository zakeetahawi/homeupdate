#!/usr/bin/env python
"""Export product data as clean JSON for Cloudflare KV"""
import json
import sys
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from inventory.models import BaseProduct
from public.cloudflare_sync import CloudflareSync

def export_product(code):
    """Export product data as clean JSON"""
    sync = CloudflareSync()
    product = BaseProduct.objects.get(code=code)
    formatted = sync.format_base_product(product)
    return json.dumps(formatted, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python export_product_clean.py <product_code>")
        sys.exit(1)
    
    code = sys.argv[1]
    print(export_product(code))
