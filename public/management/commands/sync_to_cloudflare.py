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
            default=100,
            help='Number of products to sync per batch (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing'
        )
    
    def handle(self, *args, **options):
        from inventory.models import Product
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
        
        # Get products
        products = Product.objects.exclude(code__isnull=True).exclude(code='').select_related('category')
        total = products.count()
        
        self.stdout.write(f"\n📦 إجمالي المنتجات: {total}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 وضع المعاينة - لن يتم إرسال أي بيانات\n'))
            
            sync = get_cloudflare_sync()
            for product in products[:5]:
                formatted = sync.format_product(product)
                self.stdout.write(f"  - {formatted['code']}: {formatted['name']} - {formatted['price']} {formatted['currency']}")
            
            if total > 5:
                self.stdout.write(f"  ... و {total - 5} منتج آخر")
            
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
            synced = sync.sync_all_products(batch_size=batch_size)
            
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
