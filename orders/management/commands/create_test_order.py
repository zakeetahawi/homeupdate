from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from customers.models import Customer
from inventory.models import Product
from orders.models import Order, OrderItem
from accounts.models import Branch
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a test order with items'

    def handle(self, *args, **kwargs):
        # Get a user
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
            return
        
        # Get a branch
        branch = Branch.objects.first()
        if not branch:
            self.stdout.write(self.style.ERROR('No branches found. Please create a branch first.'))
            return
        
        # Get a customer
        customer = Customer.objects.first()
        if not customer:
            self.stdout.write(self.style.ERROR('No customers found. Please create a customer first.'))
            return
        
        # Get some products
        products = list(Product.objects.all()[:5])
        if not products:
            self.stdout.write(self.style.ERROR('No products found. Please create products first.'))
            return
        
        # Create order
        try:
            order = Order.objects.create(
                customer=customer,
                created_by=user,
                branch=branch,
                status='normal',
                order_type='product',
                notes='Test order created via management command',
                delivery_type='branch'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created order: {order.order_number}'))
            
            # Create order items
            for product in products:
                quantity = random.randint(1, 5)
                item_type = 'fabric' if product.category and 'قماش' in product.category.name.lower() else 'accessory'
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=product.price or 0,
                    item_type=item_type
                )
                
                self.stdout.write(f'Added item: {product.name} x {quantity}')
            
            # Calculate total amount
            total_amount = sum(item.quantity * item.unit_price for item in order.items.all())
            order.total_amount = total_amount
            order.save()
            
            self.stdout.write(self.style.SUCCESS(f'Order created successfully with {len(products)} items. Total amount: {total_amount}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating order: {str(e)}'))
