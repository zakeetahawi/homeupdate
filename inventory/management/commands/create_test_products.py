from django.core.management.base import BaseCommand
from inventory.models import Category, Product

class Command(BaseCommand):
    help = 'Creates test products'

    def handle(self, *args, **kwargs):
        # Get or create fabric category
        try:
            fabric_category = Category.objects.filter(name='قماش').first()
            if not fabric_category:
                fabric_category = Category.objects.create(name='قماش')
                self.stdout.write(f'Created category: {fabric_category.name}')
            else:
                self.stdout.write(f'Using existing category: {fabric_category.name}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error with fabric category: {str(e)}'))
            fabric_category = Category.objects.create(name='قماش-new')
            self.stdout.write(f'Created new category: {fabric_category.name}')

        # Create fabric products if they don't exist
        fabric_products = [
            {
                'name': 'قماش قطن',
                'code': 'FAB001',
                'unit': 'meter',
                'price': 50
            },
            {
                'name': 'قماش حرير',
                'code': 'FAB002',
                'unit': 'meter',
                'price': 75
            }
        ]
        
        for product_data in fabric_products:
            product, created = Product.objects.get_or_create(
                code=product_data['code'],
                defaults={
                    'name': product_data['name'],
                    'category': fabric_category,
                    'unit': product_data['unit'],
                    'price': product_data['price']
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')
            else:
                self.stdout.write(f'Using existing product: {product.name}')

        # Get or create accessories category
        try:
            acc_category = Category.objects.filter(name='إكسسوار').first()
            if not acc_category:
                acc_category = Category.objects.create(name='إكسسوار')
                self.stdout.write(f'Created category: {acc_category.name}')
            else:
                self.stdout.write(f'Using existing category: {acc_category.name}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error with accessory category: {str(e)}'))
            acc_category = Category.objects.create(name='إكسسوار-new')
            self.stdout.write(f'Created new category: {acc_category.name}')

        # Create accessory products if they don't exist
        accessory_products = [
            {
                'name': 'زراير',
                'code': 'ACC001',
                'unit': 'piece',
                'price': 2
            },
            {
                'name': 'خيط',
                'code': 'ACC002',
                'unit': 'piece',
                'price': 1
            }
        ]
        
        for product_data in accessory_products:
            product, created = Product.objects.get_or_create(
                code=product_data['code'],
                defaults={
                    'name': product_data['name'],
                    'category': acc_category,
                    'unit': product_data['unit'],
                    'price': product_data['price']
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')
            else:
                self.stdout.write(f'Using existing product: {product.name}')
