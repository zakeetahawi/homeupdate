"""
Management command to mark already-synced products in database
This fixes products that were synced before the database update feature was added
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import BaseProduct


class Command(BaseCommand):
    help = 'Mark all active products as synced (for products synced before DB update feature)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force mark all active products as synced',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🔄 Marking Synced Products in Database'))
        self.stdout.write('='*60 + '\n')
        
        # Get all active products that are not marked as synced
        unsynced = BaseProduct.objects.filter(
            is_active=True,
            cloudflare_synced=False
        )
        
        total = unsynced.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ All active products are already marked as synced!'))
            return
        
        self.stdout.write(f'Found {total} active products not marked as synced in DB\n')
        
        if not force and not dry_run:
            self.stdout.write(self.style.WARNING(
                '⚠️  This will mark all active products as synced.\n'
                '   Use --force to proceed or --dry-run to preview.\n'
            ))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes will be made\n'))
            self.stdout.write('Products that would be marked as synced:')
            for product in unsynced[:10]:  # Show first 10
                self.stdout.write(f'  • {product.code} - {product.name}')
            if total > 10:
                self.stdout.write(f'  ... and {total - 10} more')
            self.stdout.write('')
            return
        
        # Update all unsynced products
        now = timezone.now()
        updated = unsynced.update(
            cloudflare_synced=True,
            last_synced_at=now
        )
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully marked {updated} products as synced!'))
        self.stdout.write(f'   Timestamp: {now}\n')
