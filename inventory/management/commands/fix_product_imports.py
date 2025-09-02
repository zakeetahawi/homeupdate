from django.core.management.base import BaseCommand
from inventory.models import Product, Category
from django.db import transaction

class Command(BaseCommand):
    help = 'Fix products with missing category by assigning a default category'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-category',
            action='store_true',
            help='Create a default category if none exists',
        )
        parser.add_argument(
            '--category-name',
            type=str,
            default='عام',
            help='Name of the default category to create or use',
        )

    def handle(self, *args, **options):
        create_category = options['create_category']
        category_name = options['category_name']

        with transaction.atomic():
            # Get or create default category
            default_category = Category.objects.filter(name=category_name).first()
            
            if not default_category and create_category:
                default_category = Category.objects.create(
                    name=category_name,
                    description='فئة افتراضية للمنتجات المستوردة بدون فئة'
                )
                self.stdout.write(self.style.SUCCESS(f'Created default category: {default_category.name}'))
            elif not default_category:
                default_category = Category.objects.first()
                if not default_category:
                    self.stdout.write(self.style.ERROR('No categories found and create-category not specified'))
                    return
                self.stdout.write(self.style.SUCCESS(f'Using existing category: {default_category.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing category: {default_category.name}'))

            # Find products with null category
            products_with_null_category = Product.objects.filter(category__isnull=True)
            count = products_with_null_category.count()
            
            if count == 0:
                self.stdout.write(self.style.SUCCESS('No products with missing category found'))
                return
                
            # Update products with default category
            products_with_null_category.update(category=default_category)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {count} products with default category: {default_category.name}')
            )
