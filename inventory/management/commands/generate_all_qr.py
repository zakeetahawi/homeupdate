"""
Management command to generate QR codes for all products
أمر إداري لتوليد رموز QR لجميع المنتجات
"""
from django.core.management.base import BaseCommand
from inventory.models import Product


class Command(BaseCommand):
    help = 'Generate QR codes for all products that do not have one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate QR codes even if they already exist',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of products to process at a time (default: 100)',
        )

    def handle(self, *args, **options):
        force = options['force']
        batch_size = options['batch_size']
        
        if force:
            products = Product.objects.exclude(code__isnull=True).exclude(code='')
            self.stdout.write(self.style.WARNING('Force mode: regenerating ALL QR codes...'))
        else:
            products = Product.objects.filter(
                qr_code_base64__isnull=True
            ).exclude(code__isnull=True).exclude(code='')
            self.stdout.write('Generating QR codes for products without one...')
        
        total = products.count()
        self.stdout.write(f'Found {total} products to process')
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('All products already have QR codes!'))
            return
        
        generated = 0
        errors = 0
        
        for i, product in enumerate(products.iterator(chunk_size=batch_size)):
            try:
                if product.generate_qr(force=force):
                    product.save(update_fields=['qr_code_base64'])
                    generated += 1
                
                if (i + 1) % 50 == 0:
                    self.stdout.write(f'Progress: {i + 1}/{total} ({generated} generated)')
                    
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing {product.code}: {str(e)}')
                )
        
        self.stdout.write(self.style.SUCCESS(
            f'Done! Generated {generated} QR codes. Errors: {errors}'
        ))
