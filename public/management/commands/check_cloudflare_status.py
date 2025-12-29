"""
Management command to check Cloudflare KV sync status and limits
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import requests


class Command(BaseCommand):
    help = 'Check Cloudflare KV sync status and usage limits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🔍 Cloudflare KV Status Check'))
        self.stdout.write('='*60 + '\n')
        
        # Check configuration
        self.stdout.write(self.style.WARNING('📋 Configuration:'))
        self.stdout.write(f'  Worker URL: {settings.CLOUDFLARE_WORKER_URL}')
        self.stdout.write(f'  Sync Enabled: {settings.CLOUDFLARE_SYNC_ENABLED}')
        self.stdout.write(f'  API Key: {"✓ Set" if settings.CLOUDFLARE_SYNC_API_KEY else "✗ Not Set"}')
        self.stdout.write(f'  KV Namespace ID: {settings.CLOUDFLARE_KV_NAMESPACE_ID}')
        self.stdout.write('')
        
        # Check worker health
        self.stdout.write(self.style.WARNING('🏥 Worker Health Check:'))
        try:
            response = requests.get(
                f"{settings.CLOUDFLARE_WORKER_URL}/health",
                timeout=10
            )
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('  ✓ Worker is online and responding'))
                if verbose:
                    data = response.json()
                    self.stdout.write(f'    Response: {data}')
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ Worker returned status {response.status_code}'))
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Worker is unreachable: {e}'))
        self.stdout.write('')
        
        # Check database sync status
        self.stdout.write(self.style.WARNING('📊 Database Sync Status:'))
        from inventory.models import BaseProduct
        
        total = BaseProduct.objects.count()
        synced = BaseProduct.objects.filter(cloudflare_synced=True).count()
        not_synced = total - synced
        
        self.stdout.write(f'  Total Base Products: {total}')
        self.stdout.write(f'  Synced: {synced} ({synced/total*100:.1f}%)' if total > 0 else '  Synced: 0')
        self.stdout.write(f'  Not Synced: {not_synced}')
        
        if synced > 0:
            recent = BaseProduct.objects.filter(
                cloudflare_synced=True,
                last_synced_at__isnull=False
            ).order_by('-last_synced_at').first()
            
            if recent:
                time_diff = timezone.now() - recent.last_synced_at
                hours = time_diff.total_seconds() / 3600
                self.stdout.write(f'  Last Sync: {recent.last_synced_at} ({hours:.1f} hours ago)')
        
        self.stdout.write('')
        
        # Recommendations
        self.stdout.write(self.style.WARNING('💡 Recommendations:'))
        
        if not_synced > 0:
            self.stdout.write(f'  • {not_synced} products need syncing')
            self.stdout.write('  • Use: python manage.py sync_to_cloudflare --batch-size=10')
        
        if not settings.CLOUDFLARE_SYNC_ENABLED:
            self.stdout.write(self.style.ERROR('  • Sync is DISABLED - enable in settings'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Status check complete\n'))
