from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Department, User
from inventory.models import Product, Category, Supplier, StockTransaction, PurchaseOrder, PurchaseOrderItem

class Command(BaseCommand):
    help = 'Set up inventory department permissions'

    def handle(self, *args, **options):
        # Get or create inventory department
        inventory_dept, created = Department.objects.get_or_create(
            code='inventory',
            defaults={
                'name': 'قسم المخزون',
                'description': 'إدارة المخزون والمنتجات والموردين',
                'icon': 'fas fa-warehouse',
                'url_name': 'inventory:inventory_list',
                'is_active': True,
                'order': 4,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created inventory department: {inventory_dept.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Found existing inventory department: {inventory_dept.name}'))
        
        # Get content types for inventory models
        product_ct = ContentType.objects.get_for_model(Product)
        category_ct = ContentType.objects.get_for_model(Category)
        supplier_ct = ContentType.objects.get_for_model(Supplier)
        stock_transaction_ct = ContentType.objects.get_for_model(StockTransaction)
        purchase_order_ct = ContentType.objects.get_for_model(PurchaseOrder)
        purchase_order_item_ct = ContentType.objects.get_for_model(PurchaseOrderItem)
        
        # Create permissions for inventory models
        permissions = []
        
        # Product permissions
        for action in ['add', 'change', 'delete', 'view']:
            codename = f'{action}_product'
            name = f'Can {action} product'
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=product_ct,
                defaults={'name': name}
            )
            permissions.append(perm)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {name}'))
        
        # Category permissions
        for action in ['add', 'change', 'delete', 'view']:
            codename = f'{action}_category'
            name = f'Can {action} category'
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=category_ct,
                defaults={'name': name}
            )
            permissions.append(perm)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {name}'))
        
        # Supplier permissions
        for action in ['add', 'change', 'delete', 'view']:
            codename = f'{action}_supplier'
            name = f'Can {action} supplier'
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=supplier_ct,
                defaults={'name': name}
            )
            permissions.append(perm)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {name}'))
        
        # StockTransaction permissions
        for action in ['add', 'change', 'delete', 'view']:
            codename = f'{action}_stocktransaction'
            name = f'Can {action} stock transaction'
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=stock_transaction_ct,
                defaults={'name': name}
            )
            permissions.append(perm)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {name}'))
        
        # PurchaseOrder permissions
        for action in ['add', 'change', 'delete', 'view']:
            codename = f'{action}_purchaseorder'
            name = f'Can {action} purchase order'
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=purchase_order_ct,
                defaults={'name': name}
            )
            permissions.append(perm)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {name}'))
        
        # PurchaseOrderItem permissions
        for action in ['add', 'change', 'delete', 'view']:
            codename = f'{action}_purchaseorderitem'
            name = f'Can {action} purchase order item'
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=purchase_order_item_ct,
                defaults={'name': name}
            )
            permissions.append(perm)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created permission: {name}'))
        
        # Find users in inventory department
        inventory_users = User.objects.filter(departments=inventory_dept)
        
        # Assign permissions to inventory users
        for user in inventory_users:
            for perm in permissions:
                user.user_permissions.add(perm)
            self.stdout.write(self.style.SUCCESS(f'Assigned inventory permissions to user: {user.username}'))
        
        self.stdout.write(self.style.SUCCESS('Inventory permissions setup completed successfully!'))
