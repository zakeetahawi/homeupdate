"""
خدمات نظام المتغيرات والتسعير - المراحل المنفصلة
Variant and Pricing Services - Separate Phases
"""

@classmethod
def phase1_migrate_products(cls, batch_size=100):
    """
    المرحلة 1: ترحيل المنتجات فقط (بدون QR أو مزامنة)
    
    Returns:
        dict: {
            'total': int,
            'migrated': int,
            'skipped': int,
            'errors': list,
            'base_product_ids': list  # IDs للمراحل التالية
        }
    """
    from .models import Product, ProductVariant
    
    stats = {
        'total': 0,
        'migrated': 0,
        'skipped': 0,
        'errors': [],
        'base_products_created': 0,
        'variants_created': 0,
        'base_product_ids': [],
    }
    
    # المنتجات غير المرتبطة
    unlinked_products = Product.objects.exclude(
        id__in=ProductVariant.objects.filter(
            legacy_product__isnull=False
        ).values_list('legacy_product_id', flat=True)
    )
    
    stats['total'] = unlinked_products.count()
    logger.info(f"🚀 المرحلة 1: بدء ترحيل {stats['total']} منتج")
    
    for product in unlinked_products.iterator(chunk_size=batch_size):
        try:
            base, variant, created = cls.link_existing_product(product)
            if created:
                stats['migrated'] += 1
                if base:
                    stats['base_products_created'] += 1
                    stats['base_product_ids'].append(base.id)
                stats['variants_created'] += 1
            else:
                stats['skipped'] += 1
        except Exception as e:
            stats['errors'].append({
                'product_id': product.id,
                'code': product.code,
                'error': str(e)
            })
            logger.error(f"خطأ في ترحيل المنتج {product.id}: {e}")
    
    logger.info(f"✅ المرحلة 1 اكتملت: {stats['migrated']} منتج")
    return stats


@classmethod
def phase2_generate_qr(cls, base_product_ids):
    """
    المرحلة 2: توليد QR للمنتجات المرحلة
    
    Args:
        base_product_ids: list of BaseProduct IDs
        
    Returns:
        dict: {'generated': int, 'failed': int, 'errors': list}
    """
    from .models import BaseProduct
    
    stats = {
        'total': len(base_product_ids),
        'generated': 0,
        'failed': 0,
        'errors': []
    }
    
    logger.info(f"📊 المرحلة 2: بدء توليد QR لـ {stats['total']} منتج")
    
    for base_id in base_product_ids:
        try:
            base = BaseProduct.objects.get(id=base_id)
            if base.generate_qr(force=True):
                stats['generated'] += 1
            else:
                stats['failed'] += 1
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append({
                'base_product_id': base_id,
                'error': str(e)
            })
            logger.error(f"خطأ في توليد QR للمنتج {base_id}: {e}")
    
    logger.info(f"✅ المرحلة 2 اكتملت: {stats['generated']} QR")
    return stats


@classmethod
def phase3_sync_cloudflare(cls, base_product_ids):
    """
    المرحلة 3: مزامنة Cloudflare للمنتجات المرحلة
    
    Args:
        base_product_ids: list of BaseProduct IDs
        
    Returns:
        dict: {'synced': int, 'failed': int, 'errors': list}
    """
    from .models import BaseProduct
    
    stats = {
        'total': len(base_product_ids),
        'synced': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    logger.info(f"☁️ المرحلة 3: بدء مزامنة Cloudflare لـ {stats['total']} منتج")
    
    try:
        from public.cloudflare_sync import sync_product_to_cloudflare, get_cloudflare_sync
        
        if not get_cloudflare_sync().is_configured():
            logger.warning("⚠️ Cloudflare غير مُعد - تم تخطي المزامنة")
            stats['skipped'] = stats['total']
            return stats
        
        for base_id in base_product_ids:
            try:
                base = BaseProduct.objects.get(id=base_id)
                sync_product_to_cloudflare(base)
                stats['synced'] += 1
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append({
                    'base_product_id': base_id,
                    'error': str(e)
                })
                logger.error(f"خطأ في مزامنة المنتج {base_id}: {e}")
        
        logger.info(f"✅ المرحلة 3 اكتملت: {stats['synced']} منتج")
        
    except Exception as e:
        logger.error(f"خطأ عام في مزامنة Cloudflare: {e}")
        stats['failed'] = stats['total']
        stats['errors'].append({'error': str(e)})
    
    return stats
