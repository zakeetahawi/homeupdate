from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from customers.models import Customer
from orders.models import Order
from accounts.models import Branch
from datetime import datetime

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a test order with inspection service'

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
        
        # Create order with inspection service
        try:
            order = Order.objects.create(
                customer=customer,
                created_by=user,
                branch=branch,
                status='normal',
                order_type='service',
                service_types=['inspection'],
                notes='Test inspection order created via management command',
                delivery_type='branch',
                invoice_number='INS-001'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created inspection order: {order.order_number}'))
            
            # Calculate total amount (service fee)
            order.total_amount = 150  # Example service fee
            order.save()
            
            # Update last notification date
            order.last_notification_date = datetime.now()
            order.save()
            
            self.stdout.write(self.style.SUCCESS(f'Inspection order created successfully. Total amount: {order.total_amount}'))
            
            # Create inspection record manually
            from inspections.models import Inspection
            from datetime import date, timedelta
            
            inspection = Inspection.objects.create(
                customer=customer,
                branch=branch,
                request_date=date.today(),
                scheduled_date=date.today() + timedelta(days=3),
                status='pending',
                notes=f'تم إنشاء هذه المعاينة من طلب رقم {order.order_number}',
                created_by=user
            )
            
            self.stdout.write(self.style.SUCCESS(f'Inspection record created manually: {inspection.id}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating inspection order: {str(e)}'))
