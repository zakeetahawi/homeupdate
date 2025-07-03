#!/usr/bin/env python
"""
إنشاء بيانات اختبارية شاملة من العميل إلى التركيب
"""
import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from customers.models import Customer, Branch
from orders.models import Order, OrderItem
from accounts.models import Salesperson
from installations.models_new import InstallationNew, InstallationTeamNew
from factory.models import ProductionOrder, ProductionLine
from inventory.models import Product, Category

User = get_user_model()

def create_complete_workflow():
    print("🚀 إنشاء سير عمل كامل من العميل إلى التركيب...")
    
    # 1. إنشاء مستخدم إداري
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'مدير',
            'last_name': 'النظام',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ تم إنشاء المستخدم الإداري")
    
    # 2. إنشاء فرع
    branch, created = Branch.objects.get_or_create(
        name='الفرع الرئيسي',
        defaults={
            'address': 'القاهرة - مصر الجديدة - شارع الحجاز',
            'phone': '01234567890',
            'manager_name': 'أحمد مدير الفرع'
        }
    )
    if created:
        print("✅ تم إنشاء الفرع الرئيسي")
    
    # 3. إنشاء مندوب مبيعات
    salesperson, created = Salesperson.objects.get_or_create(
        employee_number='SP001',
        defaults={
            'name': 'أحمد محمد المندوب',
            'phone': '01111111111',
            'branch': branch
        }
    )
    if created:
        print("✅ تم إنشاء مندوب المبيعات")
    
    # 4. إنشاء عملاء
    customers_data = [
        {
            'name': 'محمد أحمد السيد',
            'phone': '01500000001',
            'address': 'القاهرة - مدينة نصر - شارع مصطفى النحاس 15',
            'email': 'mohamed.ahmed@example.com',
            'customer_type': 'individual',
            'status': 'active'
        },
        {
            'name': 'شركة الخواجة للمقاولات',
            'phone': '01500000002',
            'address': 'الجيزة - المهندسين - شارع جامعة الدول العربية 25',
            'email': 'info@khawaga.com',
            'customer_type': 'company',
            'status': 'vip'
        },
        {
            'name': 'سارة محمود علي',
            'phone': '01500000003',
            'address': 'الإسكندرية - سيدي جابر - شارع الحرية 8',
            'email': 'sara.mahmoud@example.com',
            'customer_type': 'individual',
            'status': 'active'
        }
    ]
    
    customers = []
    for customer_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            phone=customer_data['phone'],
            defaults=customer_data
        )
        customers.append(customer)
        if created:
            print(f"✅ تم إنشاء عميل: {customer.name}")
    
    # 5. إنشاء فئات ومنتجات
    category, created = Category.objects.get_or_create(
        name='شبابيك ألومنيوم',
        defaults={'description': 'شبابيك من الألومنيوم عالي الجودة'}
    )
    if created:
        print("✅ تم إنشاء فئة المنتجات")
    
    products_data = [
        {
            'name': 'شباك ألومنيوم 120x100',
            'description': 'شباك ألومنيوم مقاس 120x100 سم',
            'category': category,
            'price': Decimal('1500.00'),
            'cost': Decimal('1200.00'),
            'stock_quantity': 50,
            'unit': 'قطعة'
        },
        {
            'name': 'باب ألومنيوم 200x90',
            'description': 'باب ألومنيوم مقاس 200x90 سم',
            'category': category,
            'price': Decimal('2500.00'),
            'cost': Decimal('2000.00'),
            'stock_quantity': 30,
            'unit': 'قطعة'
        }
    ]
    
    products = []
    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            name=product_data['name'],
            defaults=product_data
        )
        products.append(product)
        if created:
            print(f"✅ تم إنشاء منتج: {product.name}")
    
    # 6. إنشاء خط إنتاج
    production_line, created = ProductionLine.objects.get_or_create(
        name='خط إنتاج الشبابيك الرئيسي',
        defaults={
            'description': 'خط متخصص في إنتاج الشبابيك والأبواب',
            'is_active': True
        }
    )
    if created:
        print("✅ تم إنشاء خط الإنتاج")
    
    # 7. إنشاء طلبات مع عناصر
    orders_data = [
        {
            'customer': customers[0],
            'order_type': 'installation',
            'items': [
                {'product': products[0], 'quantity': 4, 'unit_price': products[0].price},
                {'product': products[1], 'quantity': 1, 'unit_price': products[1].price}
            ],
            'notes': 'طلب تركيب 4 شبابيك وباب واحد'
        },
        {
            'customer': customers[1],
            'order_type': 'installation',
            'items': [
                {'product': products[0], 'quantity': 8, 'unit_price': products[0].price},
                {'product': products[1], 'quantity': 2, 'unit_price': products[1].price}
            ],
            'notes': 'مشروع تجاري - 8 شبابيك و2 باب'
        },
        {
            'customer': customers[2],
            'order_type': 'installation',
            'items': [
                {'product': products[0], 'quantity': 3, 'unit_price': products[0].price}
            ],
            'notes': 'تركيب 3 شبابيك للشقة'
        }
    ]
    
    orders = []
    for i, order_data in enumerate(orders_data):
        # إنشاء الطلب
        order = Order.objects.create(
            customer=order_data['customer'],
            salesperson=salesperson,
            branch=branch,
            order_number=f'ORD-{date.today().strftime("%Y%m%d")}-{i+1:03d}',
            selected_types=order_data['order_type'],
            delivery_option='home',
            delivery_address=order_data['customer'].address,
            expected_delivery_date=date.today() + timedelta(days=15),
            notes=order_data['notes'],
            status='confirmed',
            created_by=admin_user
        )
        
        # إضافة عناصر الطلب
        total_amount = Decimal('0.00')
        for item_data in order_data['items']:
            item = OrderItem.objects.create(
                order=order,
                product=item_data['product'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['quantity'] * item_data['unit_price']
            )
            total_amount += item.total_price
        
        # تحديث إجمالي الطلب
        order.total_amount = total_amount
        order.save()
        
        orders.append(order)
        print(f"✅ تم إنشاء طلب: {order.order_number} للعميل {order.customer.name}")
        
        # إنشاء طلب إنتاج (سيتم تلقائياً عبر الإشارات)
        # لكن دعنا نتأكد من وجوده
        production_order, created = ProductionOrder.objects.get_or_create(
            order=order,
            defaults={
                'production_line': production_line,
                'start_date': date.today(),
                'expected_completion_date': date.today() + timedelta(days=10),
                'status': 'pending',
                'priority': 'high' if order.customer.status == 'vip' else 'normal'
            }
        )
        if created:
            print(f"✅ تم إنشاء طلب إنتاج: {production_order.pk}")
    
    print(f"\n🎉 تم إنشاء سير عمل كامل!")
    print(f"📊 الإحصائيات:")
    print(f"   - العملاء: {len(customers)}")
    print(f"   - الطلبات: {len(orders)}")
    print(f"   - طلبات الإنتاج: {ProductionOrder.objects.count()}")
    print(f"   - التركيبات: {InstallationNew.objects.count()}")

if __name__ == '__main__':
    create_complete_workflow()
