from django.core.management.base import BaseCommand
from inventory.models import Product, StockTransaction

class Command(BaseCommand):
    help = 'Adds test stock to products'

    def handle(self, *args, **kwargs):
        # Get all products
        products = Product.objects.all()
        
        if not products.exists():
            self.stdout.write(self.style.ERROR('No products found. Run create_test_products first.'))
            return
        
        # Add stock to each product
        for product in products:
            # Check if product already has stock
            current_stock = product.current_stock
            
            if current_stock < 10:
                # Add stock to bring it up to at least 10
                quantity_to_add = 10 - current_stock
                
                # Create stock transaction
                transaction = StockTransaction.objects.create(
                    product=product,
                    transaction_type='in',
                    reason='purchase',
                    quantity=quantity_to_add,
                    reference='INIT-STOCK',
                    notes='Initial stock for testing'
                )
                
                self.stdout.write(f'Added {quantity_to_add} units to {product.name}. New stock: {product.current_stock}')
            else:
                self.stdout.write(f'Product {product.name} already has sufficient stock: {current_stock}')
