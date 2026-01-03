"""
Management command to sync all products to Cloudflare KV
Usage: python manage.py sync_to_cloudflare
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from public.cloudflare_sync import get_cloudflare_sync


class Command(BaseCommand):
    help = 'Sync all products to Cloudflare Workers KV'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of products to sync per batch (default: 500 for paid plan)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing'
        )
    
    def handle(self, *args, **options):
        from inventory.models import Product, BaseProduct, ProductVariant
        from public.models import CloudflareSettings
        
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        # Check settings
        try:
            settings = CloudflareSettings.get_settings()
        except Exception:
            settings = None
        
        if settings and not settings.is_enabled:
            self.stdout.write(
                self.style.WARNING('⚠️  المزامنة معطلة في الإعدادات. استخدم --force لتجاوز ذلك.')
            )
        
        # Get accurate counts
        base_products = BaseProduct.objects.filter(is_active=True)
        total_base = base_products.count()
        
        # Get standalone products (orphans)
        linked_ids = ProductVariant.objects.filter(legacy_product__isnull=False).values_list('legacy_product_id', flat=True)
        orphans = Product.objects.filter(code__isnull=False).exclude(code='').exclude(id__in=linked_ids)
        total_orphans = orphans.count()
        
        total = total_base + total_orphans
        
        self.stdout.write(f"\n📦 المنتجات الأساسية: {total_base}")
        self.stdout.write(f"📦 المنتجات المستقلة: {total_orphans}")
        self.stdout.write(f"📦 الإجمالي: {total}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 وضع المعاينة - لن يتم إرسال أي بيانات\n'))
            
            sync = get_cloudflare_sync()
            for base_product in base_products[:5]:
                formatted = sync.format_base_product(base_product)
                variants_count = len(formatted.get('variants', []))
                self.stdout.write(
                    f"  - {formatted['code']}: {formatted['name']} "
                    f"({variants_count} متغير) - {formatted['price']} {formatted['currency']}"
                )
            
            if total_base > 5:
                self.stdout.write(f"  ... و {total_base - 5} منتج أساسي آخر")
            
            return
        
        # Sync
        self.stdout.write('\n🔄 جاري المزامنة...\n')
        
        sync = get_cloudflare_sync()
        
        if not sync.is_configured():
            self.stdout.write(
                self.style.ERROR('❌ إعدادات Cloudflare غير مكتملة!')
            )
            self.stdout.write('تأكد من تحديد:')
            self.stdout.write('  - CLOUDFLARE_WORKER_URL في .env')
            self.stdout.write('  - CLOUDFLARE_SYNC_API_KEY في .env')
            self.stdout.write('  - CLOUDFLARE_SYNC_ENABLED=true في .env')
            return
        
        try:
            synced = 0
            now = timezone.now()
            
            # 1. Sync Base Products with progress
            self.stdout.write(f'\n📦 مزامنة المنتجات الأساسية ({total_base} منتج)...')
            for i in range(0, total_base, batch_size):
                batch = base_products[i:i+batch_size]
                formatted = [sync.format_base_product(p) for p in batch]
                
                data = {
                    'action': 'sync_all',
                    'products': formatted
                }
                if sync._send_request(data):
                    synced += len(formatted)
                    # Update database for this batch
                    batch_ids = [p.id for p in batch]
                    BaseProduct.objects.filter(id__in=batch_ids).update(
                        cloudflare_synced=True,
                        last_synced_at=now
                    )
                    # Show progress
                    progress = min(i + batch_size, total_base)
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✅ تمت مزامنة {progress}/{total_base} منتج أساسي'),
                        ending='\n'
                    )
                    self.stdout.flush()
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ فشلت مزامنة الدفعة {i//batch_size + 1}')
                    )
            
            # 2. Sync Standalone Products (Orphans) with progress
            if total_orphans > 0:
                self.stdout.write(f'\n📦 مزامنة المنتجات المستقلة ({total_orphans} منتج)...')
                for i in range(0, total_orphans, batch_size):
                    batch = orphans[i:i+batch_size]
                    formatted = [sync.format_product(p) for p in batch]
                    
                    data = {
                        'action': 'sync_all',
                        'products': formatted
                    }
                    if sync._send_request(data):
                        synced += len(formatted)
                        progress = min(i + batch_size, total_orphans)
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ تمت مزامنة {progress}/{total_orphans} منتج مستقل'),
                            ending='\n'
                        )
                        self.stdout.flush()
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  ❌ فشلت مزامنة الدفعة {i//batch_size + 1}')
                        )
            
            # Update settings
            if settings:
                settings.products_synced = synced
                settings.last_full_sync = timezone.now()
                settings.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ تم مزامنة {synced} منتج بنجاح!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ فشلت المزامنة: {e}')
            )
