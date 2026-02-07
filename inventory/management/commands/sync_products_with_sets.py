"""
Management command to sync product sets to Cloudflare
"""
from django.core.management.base import BaseCommand
from inventory.models import BaseProduct
from public.cloudflare_sync import CloudflareSync


class Command(BaseCommand):
    help = 'Sync specific products with their product sets to Cloudflare'

    def add_arguments(self, parser):
        parser.add_argument('codes', nargs='+', type=str, help='Product codes to sync')

    def handle(self, *args, **options):
        codes = options['codes']
        sync = CloudflareSync()
        
        for code in codes:
            product = BaseProduct.objects.filter(code=code).first()
            if not product:
                self.stdout.write(self.style.ERROR(f'❌ {code}: المنتج غير موجود'))
                continue
            
            # Format with product_set data
            data = sync.format_base_product(product)
            
            # Show product_set info
            if 'product_set' in data:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ {code}: يحتوي على مجموعة ({data["product_set"]["name"]}) مع {len(data["product_set"]["products"])} منتج'
                ))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ {code}: لا يوجد في أي مجموعة'))
            
            # Sync to Cloudflare
            result = sync.sync_product(product)
            if result:
                self.stdout.write(self.style.SUCCESS(f'   ✅ تمت المزامنة بنجاح'))
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ فشلت المزامنة'))
