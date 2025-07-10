#!/usr/bin/env python
"""
اختبار شامل للنظام - العملاء والطلبات والتصنيع
Comprehensive System Test - Customers, Orders, and Manufacturing

هذا الملف يقوم بإنشاء بيانات اختبارية شاملة واختبار جميع الحالات والسيناريوهات
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError

# استيراد النماذج
from customers.models import Customer, CustomerCategory, CustomerType
from orders.models import Order, OrderItem, OrderStatusLog
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from accounts.models import Branch, Salesperson
from inventory.models import Product, Category

User = get_user_model()

class ComprehensiveSystemTest:
    """فئة الاختبار الشامل للنظام"""
    
    def __init__(self):
        """تهيئة اختبار النظام الشامل"""
        self.test_results = {
            'customers': {'created': 0, 'errors': []},
            'orders': {'created': 0, 'errors': []},
            'manufacturing': {'created': 0, 'errors': []},
            'status_transitions': {'tested': 0, 'errors': []},
            'state_consistency': {'checks': 0, 'errors': []}
        }
        self.test_data = {
            'customers': [],
            'orders': [],
            'manufacturing_orders': [],
            'branches': [],
            'salespersons': [],
            'categories': [],
            'products': []
        }
        
    def run_comprehensive_test(self):
        """تشغيل الاختبار الشامل"""
        print("🔄 بدء الاختبار الشامل للنظام...")
        
        try:
            # 1. إنشاء البيانات الأساسية
            self.setup_basic_data()
            
            # 2. اختبار العملاء
            self.test_customers_with_branches_and_codes()
            
            # 3. اختبار الطلبات
            self.test_orders_with_unique_numbers_and_validation()
            
            # 4. اختبار التصنيع
            self.test_manufacturing_and_status_sync()
            
            # 5. اختبار تطابق الحالات
            self.test_state_consistency()
            
            # 6. اختبار انتقال الحالات
            self.test_status_transitions()
            
            # 7. إنشاء التقرير
            self.generate_report()
            
        except Exception as e:
            print(f"❌ خطأ في الاختبار الشامل: {str(e)}")
            self.test_results['general_error'] = str(e)
        
        return self.test_results
    
    def setup_basic_data(self):
        """إعداد البيانات الأساسية للاختبار"""
        print("🔧 إعداد البيانات الأساسية...")
        
        try:
            # إنشاء الفروع
            branches_data = [
                {'name': 'الفرع الرئيسي', 'code': 'MAIN'},
                {'name': 'فرع الشمال', 'code': 'NORTH'},
                {'name': 'فرع الجنوب', 'code': 'SOUTH'}
            ]
            
            branches = []
            for branch_data in branches_data:
                branch, created = Branch.objects.get_or_create(
                    code=branch_data['code'],
                    defaults={'name': branch_data['name']}
                )
                branches.append(branch)
                print(f"  ✅ تم إنشاء {branch.name}")
            
            # إنشاء مستخدمين للفروع
            users = []
            for i, branch in enumerate(branches):
                user, created = User.objects.get_or_create(
                    username=f'user_{branch.code.lower()}',
                    defaults={
                        'first_name': f'مستخدم {branch.name}',
                        'branch': branch,
                        'is_active': True
                    }
                )
                users.append(user)
                print(f"  ✅ تم إنشاء مستخدم لـ {branch.name}")
            
            # إنشاء بائعين
            salespersons = []
            for branch in branches:
                for i in range(2):  # بائعين لكل فرع
                    salesperson, created = Salesperson.objects.get_or_create(
                        employee_number=f'SP{branch.code}{i+1}',
                        defaults={
                            'name': f'بائع {i+1} - {branch.name}',
                            'branch': branch,
                            'is_active': True
                        }
                    )
                    salespersons.append(salesperson)
                    print(f"  ✅ تم إنشاء {salesperson.name}")
            
            # إنشاء التصنيفات
            categories_data = [
                {'name': 'ستائر', 'description': 'جميع أنواع الستائر'},
                {'name': 'مفروشات', 'description': 'المفروشات والأثاث'},
                {'name': 'إكسسوارات', 'description': 'الإكسسوارات والديكورات'}
            ]
            
            categories = []
            for cat_data in categories_data:
                category, created = Category.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={'description': cat_data['description']}
                )
                categories.append(category)
                print(f"  ✅ تم إنشاء تصنيف {category.name}")
            
            # إنشاء المنتجات
            products_data = [
                {'name': 'ستارة قطنية', 'price': 150.00, 'category': categories[0]},
                {'name': 'ستارة حريرية', 'price': 250.00, 'category': categories[0]},
                {'name': 'كنبة جلدية', 'price': 1200.00, 'category': categories[1]},
                {'name': 'طاولة خشبية', 'price': 800.00, 'category': categories[1]},
                {'name': 'حامل ستائر', 'price': 75.00, 'category': categories[2]},
                {'name': 'خطاف معدني', 'price': 25.00, 'category': categories[2]}
            ]
            
            products = []
            for prod_data in products_data:
                product, created = Product.objects.get_or_create(
                    name=prod_data['name'],
                    defaults={
                        'price': prod_data['price'],
                        'category': prod_data['category'],
                        'minimum_stock': 10
                    }
                )
                products.append(product)
                print(f"  ✅ تم إنشاء منتج {product.name}")
            
            # حفظ البيانات في test_data
            self.test_data.update({
                'branches': branches,
                'users': users,
                'salespersons': salespersons,
                'categories': categories,
                'products': products
            })
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إعداد البيانات الأساسية: {str(e)}")
            return False

    def test_customers_with_branches_and_codes(self):
        """اختبار العملاء مع الفروع والأكواد الفريدة"""
        print("\n🧪 اختبار العملاء مع الفروع والأكواد...")
        
        customers_data = [
            {
                'name': 'أحمد محمد علي',
                'phone': '0501234567',
                'email': 'ahmed@example.com',
                'customer_type': 'retail',
                'branch_index': 0  # الفرع الرئيسي
            },
            {
                'name': 'شركة النور للديكور',
                'phone': '0501234568',
                'email': 'alnoor@company.com',
                'customer_type': 'corporate',
                'branch_index': 1  # فرع الشمال
            },
            {
                'name': 'فاطمة أحمد',
                'phone': '0501234569',
                'email': 'fatima@example.com',
                'customer_type': 'vip',
                'branch_index': 2  # فرع الجنوب
            },
            {
                'name': 'متجر الأناقة',
                'phone': '0501234570',
                'email': 'elegance@shop.com',
                'customer_type': 'wholesale',
                'branch_index': 0  # الفرع الرئيسي
            },
            {
                'name': 'المهندس سالم',
                'phone': '0501234571',
                'email': 'salem@designer.com',
                'customer_type': 'designer',
                'branch_index': 1  # فرع الشمال
            },
            {
                'name': 'موزع الخليج',
                'phone': '0501234572',
                'email': 'gulf@distributor.com',
                'customer_type': 'distributor',
                'branch_index': 2  # فرع الجنوب
            }
        ]
        
        created_customers = []
        customer_codes = set()  # لتتبع الأكواد المستخدمة
        
        for customer_data in customers_data:
            try:
                branch = self.test_data['branches'][customer_data['branch_index']]
                user = self.test_data['users'][customer_data['branch_index']]
                
                customer = Customer.objects.create(
                    name=customer_data['name'],
                    phone=customer_data['phone'],
                    email=customer_data['email'],
                    address=f'عنوان {customer_data["name"]}',
                    customer_type=customer_data['customer_type'],
                    branch=branch,
                    created_by=user
                )
                
                # التحقق من فرادة الكود
                if customer.code in customer_codes:
                    print(f"  ❌ كود مكرر للعميل {customer.name}: {customer.code}")
                    return False
                
                customer_codes.add(customer.code)
                created_customers.append(customer)
                
                print(f"  ✅ تم إنشاء العميل: {customer.name} (كود: {customer.code}, فرع: {branch.name})")
                
            except Exception as e:
                print(f"  ❌ فشل إنشاء العميل {customer_data['name']}: {str(e)}")
                return False
        
        self.test_data['customers'] = created_customers
        
        # التحقق من عدم تكرار الأكواد في قاعدة البيانات
        all_codes = Customer.objects.values_list('code', flat=True)
        unique_codes = set(all_codes)
        
        if len(all_codes) != len(unique_codes):
            print(f"  ❌ توجد أكواد مكررة في قاعدة البيانات!")
            return False
        
        print(f"✅ تم إنشاء {len(created_customers)} عميل بأكواد فريدة")
        return True

    def test_orders_with_unique_numbers_and_validation(self):
        """اختبار الطلبات مع أرقام فريدة والتحقق من الصحة"""
        print("\n🧪 اختبار الطلبات مع أرقام فريدة...")
        
        orders_scenarios = [
            {
                'customer_index': 0,
                'branch_index': 0,
                'salesperson_index': 0,
                'selected_types': ['inspection'],
                'contract_required': False,
                'invoice_required': False
            },
            {
                'customer_index': 1,
                'branch_index': 1,
                'salesperson_index': 2,
                'selected_types': ['accessory'],
                'contract_required': True,
                'invoice_required': True
            },
            {
                'customer_index': 2,
                'branch_index': 2,
                'salesperson_index': 4,
                'selected_types': ['installation'],
                'contract_required': True,
                'invoice_required': True
            },
            {
                'customer_index': 3,
                'branch_index': 0,
                'salesperson_index': 1,
                'selected_types': ['tailoring'],
                'contract_required': True,
                'invoice_required': True
            },
            {
                'customer_index': 4,
                'branch_index': 1,
                'salesperson_index': 3,
                'selected_types': ['accessory', 'installation'],
                'contract_required': True,
                'invoice_required': True
            }
        ]
        
        created_orders = []
        order_numbers = set()
        invoice_numbers = set()
        contract_numbers = set()
        
        for i, scenario in enumerate(orders_scenarios):
            try:
                customer = self.test_data['customers'][scenario['customer_index']]
                branch = self.test_data['branches'][scenario['branch_index']]
                salesperson = self.test_data['salespersons'][scenario['salesperson_index']]
                user = self.test_data['users'][scenario['branch_index']]
                
                # إنشاء أرقام فريدة للاختبار
                test_invoice_number = None
                test_contract_number = None
                
                if scenario['invoice_required']:
                    test_invoice_number = f"TEST-INV-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}"
                    if test_invoice_number in invoice_numbers:
                        print(f"  ❌ رقم فاتورة مكرر: {test_invoice_number}")
                        return False
                    invoice_numbers.add(test_invoice_number)
                
                if scenario['contract_required']:
                    test_contract_number = f"TEST-CT-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}"
                    if test_contract_number in contract_numbers:
                        print(f"  ❌ رقم عقد مكرر: {test_contract_number}")
                        return False
                    contract_numbers.add(test_contract_number)
                
                order = Order.objects.create(
                    customer=customer,
                    salesperson=salesperson,
                    branch=branch,
                    created_by=user,
                    selected_types=scenario['selected_types'],
                    invoice_number=test_invoice_number,
                    contract_number=test_contract_number,
                    notes=f'طلب اختباري رقم {i+1}'
                )
                
                # التحقق من فرادة رقم الطلب
                if order.order_number in order_numbers:
                    print(f"  ❌ رقم طلب مكرر: {order.order_number}")
                    return False
                
                order_numbers.add(order.order_number)
                created_orders.append(order)
                
                # إضافة منتجات للطلب
                for j in range(2):  # إضافة منتجين لكل طلب
                    product = self.test_data['products'][j % len(self.test_data['products'])]
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=random.randint(1, 5),
                        unit_price=product.price
                    )
                
                print(f"  ✅ تم إنشاء الطلب: {order.order_number}")
                print(f"    - العميل: {customer.name}")
                print(f"    - البائع: {salesperson.name}")
                print(f"    - الفرع: {branch.name}")
                if test_invoice_number:
                    print(f"    - رقم الفاتورة: {test_invoice_number}")
                if test_contract_number:
                    print(f"    - رقم العقد: {test_contract_number}")
                
            except Exception as e:
                print(f"  ❌ فشل إنشاء الطلب {i+1}: {str(e)}")
                return False
        
        self.test_data['orders'] = created_orders
        
        # التحقق من عدم تكرار أرقام الطلبات في قاعدة البيانات
        all_order_numbers = Order.objects.values_list('order_number', flat=True)
        unique_order_numbers = set(all_order_numbers)
        
        if len(all_order_numbers) != len(unique_order_numbers):
            print(f"  ❌ توجد أرقام طلبات مكررة في قاعدة البيانات!")
            return False
        
        print(f"✅ تم إنشاء {len(created_orders)} طلب بأرقام فريدة")
        return True

    def test_manufacturing_and_status_sync(self):
        """اختبار التصنيع ومزامنة الحالات"""
        print("\n🧪 اختبار التصنيع ومزامنة الحالات...")
        
        created_manufacturing_orders = []
        status_mismatches = []
        
        # إنشاء أوامر تصنيع للطلبات التي تتطلب تصنيعاً
        manufacturing_orders_data = [
            {
                'order_index': 1,  # طلب accessory
                'order_type': 'accessory',
                'initial_status': 'pending_approval'
            },
            {
                'order_index': 2,  # طلب installation
                'order_type': 'installation',
                'initial_status': 'pending'
            },
            {
                'order_index': 3,  # طلب tailoring
                'order_type': 'custom',
                'initial_status': 'in_progress'
            }
        ]
        
        for mo_data in manufacturing_orders_data:
            try:
                order = self.test_data['orders'][mo_data['order_index']]
                
                manufacturing_order = ManufacturingOrder.objects.create(
                    order=order,
                    order_type=mo_data['order_type'],
                    contract_number=order.contract_number,
                    invoice_number=order.invoice_number,
                    order_date=order.order_date or timezone.now().date(),
                    expected_delivery_date=(timezone.now() + timedelta(days=30)).date(),
                    status=mo_data['initial_status'],
                    notes=f'أمر تصنيع اختباري للطلب {order.order_number}'
                )
                
                created_manufacturing_orders.append(manufacturing_order)
                
                print(f"  ✅ تم إنشاء أمر تصنيع للطلب: {order.order_number}")
                print(f"    - حالة التصنيع: {manufacturing_order.get_status_display()}")
                
                # التحقق من مطابقة الحالات
                order.refresh_from_db()
                
                # استخدام خدمة مزامنة الحالات للتحقق
                from crm.services.base_service import StatusSyncService
                
                validation = StatusSyncService.validate_status_consistency(
                    order, manufacturing_order
                )
                
                if not all(validation.values()):
                    status_mismatches.append({
                        'order_id': order.id,
                        'order_status': order.order_status,
                        'manufacturing_status': manufacturing_order.status,
                        'tracking_status': order.tracking_status,
                        'validation': validation
                    })
                    
                    print(f"    ⚠️ عدم تطابق في الحالات:")
                    print(f"      - حالة الطلب: {order.order_status}")
                    print(f"      - حالة التصنيع: {manufacturing_order.status}")
                    print(f"      - حالة التتبع: {order.tracking_status}")
                    
                    # مزامنة الحالات
                    StatusSyncService.sync_manufacturing_to_order(
                        manufacturing_order, order
                    )
                    
                    order.refresh_from_db()
                    print(f"    ✅ تم تصحيح الحالات:")
                    print(f"      - حالة الطلب الجديدة: {order.order_status}")
                    print(f"      - حالة التتبع الجديدة: {order.tracking_status}")
                else:
                    print(f"    ✅ الحالات متطابقة")
                
            except Exception as e:
                print(f"  ❌ فشل إنشاء أمر التصنيع: {str(e)}")
                return False
        
        self.test_data['manufacturing_orders'] = created_manufacturing_orders
        
        # اختبار تغيير الحالات ومزامنتها
        print("\n🔄 اختبار تغيير الحالات ومزامنتها...")
        
        status_transitions = [
            {'mo_index': 0, 'new_status': 'in_progress'},
            {'mo_index': 1, 'new_status': 'completed'},
            {'mo_index': 2, 'new_status': 'ready_install'}
        ]
        
        for transition in status_transitions:
            try:
                mo = created_manufacturing_orders[transition['mo_index']]
                old_status = mo.status
                
                mo.status = transition['new_status']
                mo.save()
                
                # تحديث حالة الطلب المرتبط
                mo.update_order_status()
                
                order = mo.order
                order.refresh_from_db()
                
                print(f"  ✅ تم تغيير حالة التصنيع من {old_status} إلى {mo.status}")
                print(f"    - حالة الطلب المحدثة: {order.order_status}")
                print(f"    - حالة التتبع المحدثة: {order.tracking_status}")
                
            except Exception as e:
                print(f"  ❌ فشل في تغيير الحالة: {str(e)}")
                return False
        
        print(f"✅ تم إنشاء {len(created_manufacturing_orders)} أمر تصنيع مع مزامنة الحالات")
        
        if status_mismatches:
            print(f"⚠️ تم اكتشاف {len(status_mismatches)} حالة عدم تطابق وتم إصلاحها")
        
        return True
    
    def test_customers(self):
        """اختبار إنشاء العملاء بجميع الأنواع والحالات"""
        print("👥 اختبار العملاء...")
        
        customer_data_sets = [
            # عميل VIP
            {
                'name': 'أحمد محمد علي',
                'phone': '01234567890',
                'phone2': '01987654321',
                'email': 'ahmed@example.com',
                'address': 'القاهرة - مصر الجديدة',
                'customer_type': 'vip',
                'status': 'active',
                'interests': 'ستائر فاخرة، ديكور مودرن'
            },
            # عميل جملة
            {
                'name': 'شركة النور للديكور',
                'phone': '01111111111',
                'email': 'info@alnoor.com',
                'address': 'الجيزة - المهندسين',
                'customer_type': 'wholesale',
                'status': 'active',
                'interests': 'طلبات كبيرة، ستائر مكاتب'
            },
            # عميل شركة
            {
                'name': 'مؤسسة الخليج للمقاولات',
                'phone': '01222222222',
                'email': 'contracts@gulf.com',
                'address': 'الإسكندرية - سيدي جابر',
                'customer_type': 'corporate',
                'status': 'active',
                'interests': 'مشاريع كبيرة، عقود حكومية'
            },
            # مهندس ديكور
            {
                'name': 'م. سارة أحمد',
                'phone': '01333333333',
                'email': 'sara.designer@example.com',
                'address': 'القاهرة - الزمالك',
                'customer_type': 'designer',
                'status': 'active',
                'interests': 'تصميمات حديثة، ألوان عصرية'
            },
            # عميل عادي
            {
                'name': 'فاطمة محمود',
                'phone': '01444444444',
                'address': 'الجيزة - فيصل',
                'customer_type': 'retail',
                'status': 'active',
                'interests': 'ستائر منزلية بسيطة'
            },
            # عميل غير نشط
            {
                'name': 'عميل متوقف',
                'phone': '01555555555',
                'address': 'القاهرة',
                'customer_type': 'retail',
                'status': 'inactive',
                'interests': ''
            }
        ]
        
        for i, data in enumerate(customer_data_sets):
            try:
                # إضافة بيانات إضافية
                data.update({
                    'branch': self.test_branch,
                    'category': random.choice(self.customer_categories),
                    'created_by': self.test_user,
                    'notes': f'عميل اختبار رقم {i+1}'
                })
                
                customer = Customer.objects.create(**data)
                self.test_data['customers'].append(customer)
                self.test_results['customers']['created'] += 1
                
                print(f"✅ تم إنشاء العميل: {customer.name} ({customer.get_customer_type_display()})")
                
            except Exception as e:
                error_msg = f"خطأ في إنشاء العميل {data['name']}: {str(e)}"
                self.test_results['customers']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        print(f"📊 تم إنشاء {self.test_results['customers']['created']} عميل بنجاح")
    
    def test_orders(self):
        """اختبار إنشاء الطلبات بجميع الأنواع والحالات"""
        print("🛒 اختبار الطلبات...")
        
        if not self.test_data['customers']:
            print("❌ لا توجد عملاء لإنشاء طلبات")
            return
        
        order_scenarios = [
            # طلب تركيب VIP
            {
                'types': ['installation'],
                'status': 'vip',
                'order_status': 'pending_approval',
                'tracking_status': 'factory',
                'delivery_type': 'home',
                'payment_verified': True,
                'total_amount': Decimal('5000.00'),
                'paid_amount': Decimal('2500.00')
            },
            # طلب تفصيل عادي
            {
                'types': ['tailoring'],
                'status': 'normal',
                'order_status': 'pending',
                'tracking_status': 'pending',
                'delivery_type': 'branch',
                'payment_verified': False,
                'total_amount': Decimal('1500.00'),
                'paid_amount': Decimal('500.00')
            },
            # طلب إكسسوار
            {
                'types': ['accessory'],
                'status': 'normal',
                'order_status': 'in_progress',
                'tracking_status': 'warehouse',
                'delivery_type': 'home',
                'payment_verified': True,
                'total_amount': Decimal('800.00'),
                'paid_amount': Decimal('800.00')
            },
            # طلب معاينة
            {
                'types': ['inspection'],
                'status': 'normal',
                'order_status': 'completed',
                'tracking_status': 'ready',
                'delivery_type': 'branch',
                'payment_verified': True,
                'total_amount': Decimal('200.00'),
                'paid_amount': Decimal('200.00')
            },
            # طلب مختلط (تركيب + تفصيل)
            {
                'types': ['installation', 'tailoring'],
                'status': 'vip',
                'order_status': 'ready_install',
                'tracking_status': 'ready',
                'delivery_type': 'home',
                'payment_verified': True,
                'total_amount': Decimal('8000.00'),
                'paid_amount': Decimal('6000.00')
            }
        ]
        
        for i, scenario in enumerate(order_scenarios):
            try:
                customer = random.choice(self.test_data['customers'])
                
                # إنشاء رقم طلب فريد
                order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}"
                
                order_data = {
                    'customer': customer,
                    'order_number': order_number,
                    'salesperson': self.test_salesperson,
                    'branch': self.test_branch,
                    'created_by': self.test_user,
                    'selected_types': scenario['types'],
                    'status': scenario['status'],
                    'order_status': scenario['order_status'],
                    'tracking_status': scenario['tracking_status'],
                    'delivery_type': scenario['delivery_type'],
                    'payment_verified': scenario['payment_verified'],
                    'total_amount': scenario['total_amount'],
                    'paid_amount': scenario['paid_amount'],
                    'notes': f'طلب اختبار رقم {i+1} - أنواع: {", ".join(scenario["types"])}',
                    'expected_delivery_date': timezone.now().date() + timedelta(days=random.randint(7, 30))
                }
                
                if scenario['delivery_type'] == 'home':
                    order_data['delivery_address'] = f'عنوان التسليم للطلب {i+1}'
                
                order = Order.objects.create(**order_data)
                
                # إضافة عناصر الطلب
                for j, product in enumerate(random.sample(self.test_products, min(3, len(self.test_products)))):
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=random.randint(1, 5),
                        unit_price=product.price,
                        item_type=random.choice(['fabric', 'accessory']),
                        notes=f'عنصر {j+1} من الطلب {order_number}'
                    )
                
                self.test_data['orders'].append(order)
                self.test_results['orders']['created'] += 1
                
                print(f"✅ تم إنشاء الطلب: {order_number} للعميل {customer.name}")
                
            except Exception as e:
                error_msg = f"خطأ في إنشاء الطلب رقم {i+1}: {str(e)}"
                self.test_results['orders']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        print(f"📊 تم إنشاء {self.test_results['orders']['created']} طلب بنجاح")
    
    def test_manufacturing(self):
        """اختبار إنشاء أوامر التصنيع"""
        print("🏭 اختبار التصنيع...")
        
        # البحث عن الطلبات التي تحتاج تصنيع
        manufacturing_orders = []
        for order in self.test_data['orders']:
            if hasattr(order, 'manufacturing_order'):
                manufacturing_orders.append(order.manufacturing_order)
        
        # إنشاء أوامر تصنيع إضافية للطلبات التي لا تحتوي على أوامر تصنيع
        for order in self.test_data['orders']:
            if not hasattr(order, 'manufacturing_order'):
                try:
                    manufacturing_order = ManufacturingOrder.objects.create(
                        order=order,
                        status='pending_approval',
                        order_type=random.choice(['installation', 'custom', 'accessory']),
                        order_date=order.created_at.date(),
                        expected_delivery_date=order.expected_delivery_date or (timezone.now().date() + timedelta(days=15)),
                        contract_number=f"CON-{order.order_number}",
                        invoice_number=f"INV-{order.order_number}",
                        notes=f'أمر تصنيع للطلب {order.order_number}'
                    )
                    
                    # إضافة عناصر أمر التصنيع
                    for item in order.items.all():
                        ManufacturingOrderItem.objects.create(
                            manufacturing_order=manufacturing_order,
                            product_name=item.product.name,
                            quantity=item.quantity,
                            specifications=f'مواصفات {item.product.name}',
                            status='pending'
                        )
                    
                    manufacturing_orders.append(manufacturing_order)
                    self.test_results['manufacturing']['created'] += 1
                    
                    print(f"✅ تم إنشاء أمر التصنيع للطلب: {order.order_number}")
                    
                except Exception as e:
                    error_msg = f"خطأ في إنشاء أمر التصنيع للطلب {order.order_number}: {str(e)}"
                    self.test_results['manufacturing']['errors'].append(error_msg)
                    print(f"❌ {error_msg}")
        
        self.test_data['manufacturing_orders'] = manufacturing_orders
        print(f"📊 تم إنشاء {self.test_results['manufacturing']['created']} أمر تصنيع بنجاح")
    
    def test_status_transitions(self):
        """اختبار انتقال الحالات"""
        print("🔄 اختبار انتقال الحالات...")
        
        # تعريف انتقالات الحالات الصحيحة
        valid_transitions = {
            'pending_approval': ['pending', 'rejected', 'cancelled'],
            'pending': ['in_progress', 'cancelled'],
            'in_progress': ['completed', 'ready_install', 'cancelled'],
            'completed': ['ready_install', 'delivered'],
            'ready_install': ['completed', 'delivered'],
            'delivered': [],
            'rejected': [],
            'cancelled': []
        }
        
        for mfg_order in self.test_data['manufacturing_orders']:
            try:
                current_status = mfg_order.status
                possible_transitions = valid_transitions.get(current_status, [])
                
                if possible_transitions:
                    # اختبار انتقال صحيح
                    new_status = random.choice(possible_transitions)
                    old_status = mfg_order.status
                    
                    mfg_order.status = new_status
                    mfg_order.save()
                    
                    # التحقق من تحديث الطلب الأصلي
                    mfg_order.refresh_from_db()
                    order = mfg_order.order
                    order.refresh_from_db()
                    
                    self.test_results['status_transitions']['tested'] += 1
                    print(f"✅ تم اختبار انتقال الحالة: {old_status} -> {new_status} للطلب {order.order_number}")
                    
                    # التحقق من تطابق الحالات
                    if order.order_status != mfg_order.status:
                        error_msg = f"عدم تطابق الحالة بين الطلب ({order.order_status}) والتصنيع ({mfg_order.status})"
                        self.test_results['status_transitions']['errors'].append(error_msg)
                        print(f"⚠️ {error_msg}")
                
            except Exception as e:
                error_msg = f"خطأ في اختبار انتقال الحالة للطلب {mfg_order.order.order_number}: {str(e)}"
                self.test_results['status_transitions']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        print(f"📊 تم اختبار {self.test_results['status_transitions']['tested']} انتقال حالة")
        
        # إرجاع True إذا لم تكن هناك أخطاء، False إذا كانت هناك أخطاء
        return len(self.test_results['status_transitions']['errors']) == 0
    
    def test_state_consistency(self):
        """اختبار تطابق الحالات في النظام"""
        print("🔍 اختبار تطابق الحالات...")
        
        for order in self.test_data['orders']:
            try:
                self.test_results['state_consistency']['checks'] += 1
                
                # التحقق من وجود أمر تصنيع للطلبات التي تحتاج تصنيع
                manufacturing_types = {'installation', 'tailoring', 'custom'}
                order_types = set(order.selected_types)
                
                needs_manufacturing = bool(order_types.intersection(manufacturing_types))
                has_manufacturing = hasattr(order, 'manufacturing_order')
                
                if needs_manufacturing and not has_manufacturing:
                    error_msg = f"الطلب {order.order_number} يحتاج تصنيع لكن لا يوجد أمر تصنيع"
                    self.test_results['state_consistency']['errors'].append(error_msg)
                    print(f"⚠️ {error_msg}")
                
                elif has_manufacturing:
                    mfg_order = order.manufacturing_order
                    
                    # التحقق من تطابق الحالات
                    if order.order_status != mfg_order.status:
                        error_msg = f"عدم تطابق حالة الطلب {order.order_number}: Order({order.order_status}) != Manufacturing({mfg_order.status})"
                        self.test_results['state_consistency']['errors'].append(error_msg)
                        print(f"⚠️ {error_msg}")
                    
                    # التحقق من tracking_status
                    expected_tracking = {
                        'pending_approval': 'factory',
                        'pending': 'factory',
                        'in_progress': 'factory',
                        'ready_install': 'ready',
                        'completed': 'ready',
                        'delivered': 'delivered',
                        'rejected': 'factory',
                        'cancelled': 'factory'
                    }
                    
                    expected = expected_tracking.get(mfg_order.status)
                    if expected and order.tracking_status != expected:
                        error_msg = f"عدم تطابق tracking_status للطلب {order.order_number}: Expected({expected}) != Actual({order.tracking_status})"
                        self.test_results['state_consistency']['errors'].append(error_msg)
                        print(f"⚠️ {error_msg}")
                
                print(f"✅ تم فحص تطابق الحالات للطلب: {order.order_number}")
                
            except Exception as e:
                error_msg = f"خطأ في فحص تطابق الحالات للطلب {order.order_number}: {str(e)}"
                self.test_results['state_consistency']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        print(f"📊 تم فحص {self.test_results['state_consistency']['checks']} طلب لتطابق الحالات")
    
    def generate_report(self):
        """إنشاء تقرير مفصل عن نتائج الاختبار"""
        print("\n" + "="*60)
        print("📋 تقرير الاختبار الشامل للنظام")
        print("="*60)
        
        # إحصائيات العملاء
        print(f"\n👥 العملاء:")
        print(f"   ✅ تم إنشاء: {self.test_results['customers']['created']} عميل")
        print(f"   ❌ أخطاء: {len(self.test_results['customers']['errors'])}")
        for error in self.test_results['customers']['errors']:
            print(f"      - {error}")
        
        # إحصائيات الطلبات
        print(f"\n🛒 الطلبات:")
        print(f"   ✅ تم إنشاء: {self.test_results['orders']['created']} طلب")
        print(f"   ❌ أخطاء: {len(self.test_results['orders']['errors'])}")
        for error in self.test_results['orders']['errors']:
            print(f"      - {error}")
        
        # إحصائيات التصنيع
        print(f"\n🏭 التصنيع:")
        print(f"   ✅ تم إنشاء: {self.test_results['manufacturing']['created']} أمر تصنيع")
        print(f"   ❌ أخطاء: {len(self.test_results['manufacturing']['errors'])}")
        for error in self.test_results['manufacturing']['errors']:
            print(f"      - {error}")
        
        # إحصائيات انتقال الحالات
        print(f"\n🔄 انتقال الحالات:")
        print(f"   ✅ تم اختبار: {self.test_results['status_transitions']['tested']} انتقال")
        print(f"   ❌ أخطاء: {len(self.test_results['status_transitions']['errors'])}")
        for error in self.test_results['status_transitions']['errors']:
            print(f"      - {error}")
        
        # إحصائيات تطابق الحالات
        print(f"\n🔍 تطابق الحالات:")
        print(f"   ✅ تم فحص: {self.test_results['state_consistency']['checks']} طلب")
        print(f"   ❌ أخطاء: {len(self.test_results['state_consistency']['errors'])}")
        for error in self.test_results['state_consistency']['errors']:
            print(f"      - {error}")
        
        # الملخص العام
        total_errors = (
            len(self.test_results['customers']['errors']) +
            len(self.test_results['orders']['errors']) +
            len(self.test_results['manufacturing']['errors']) +
            len(self.test_results['status_transitions']['errors']) +
            len(self.test_results['state_consistency']['errors'])
        )
        
        print(f"\n📊 الملخص العام:")
        print(f"   إجمالي الأخطاء: {total_errors}")
        
        if total_errors == 0:
            print("   🎉 تم اجتياز جميع الاختبارات بنجاح!")
        else:
            print("   ⚠️ يوجد أخطاء تحتاج إلى إصلاح")
        
        # حفظ التقرير في ملف
        self.save_report_to_file()
        
        print("\n" + "="*60)
    
    def save_report_to_file(self):
        """حفظ التقرير في ملف"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_test_report_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"💾 تم حفظ التقرير المفصل في: {filename}")
            
        except Exception as e:
            print(f"❌ خطأ في حفظ التقرير: {str(e)}")

    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("🚀 بدء الاختبار الشامل المحدث لنظام إدارة الخواجة")
        print("=" * 70)
        
        start_time = datetime.now()
        
        # إعداد البيانات الأساسية
        if not self.setup_basic_data():
            print("❌ فشل في إعداد البيانات الأساسية")
            return self.generate_detailed_report({}, 0, 0)
        
        # تشغيل الاختبارات
        test_results = {}
        
        # اختبار العملاء مع الفروع والأكواد
        test_results['customers_with_codes'] = self.test_customers_with_branches_and_codes()
        
        # اختبار الطلبات مع أرقام فريدة
        test_results['orders_with_unique_numbers'] = self.test_orders_with_unique_numbers_and_validation()
        
        # اختبار التصنيع ومزامنة الحالات
        test_results['manufacturing_and_sync'] = self.test_manufacturing_and_status_sync()
        
        # اختبار انتقال الحالات
        test_results['status_transitions'] = self.test_status_transitions()
        
        # اختبار تطابق الحالات النهائي
        test_results['final_status_validation'] = self.test_final_status_validation()
        
        # اختبار شامل لتطابق الحالات في جميع أنحاء النظام
        test_results['comprehensive_status_consistency'] = self.test_comprehensive_status_consistency()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # حساب معدل النجاح
        successful_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # عرض النتائج
        print("\n" + "=" * 70)
        print("📊 نتائج الاختبار الشامل المحدث:")
        print(f"⏱️  مدة التنفيذ: {duration:.2f} ثانية")
        print(f"📈 معدل النجاح: {success_rate:.1f}%")
        print(f"✅ اختبارات ناجحة: {successful_tests}/{total_tests}")
        
        for test_name, result in test_results.items():
            status = "✅ نجح" if result else "❌ فشل"
            print(f"   - {test_name}: {status}")
        
        if success_rate >= 90:
            print("🎉 النظام يعمل بكفاءة عالية!")
        elif success_rate >= 75:
            print("✅ النظام يعمل بشكل جيد مع بعض التحسينات المطلوبة")
        else:
            print("⚠️ النظام يحتاج إلى إصلاحات جوهرية")
        
        # إنشاء التقرير المفصل
        report = self.generate_detailed_report(test_results, duration, success_rate)
        
        return report

    def test_final_status_validation(self):
        """اختبار التحقق النهائي من تطابق الحالات"""
        print("\n🔍 التحقق النهائي من تطابق الحالات...")
        
        try:
            from crm.services.base_service import StatusSyncService
            
            mismatched_orders = []
            total_orders_checked = 0
            
            # فحص جميع الطلبات التي لها أوامر تصنيع
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                total_orders_checked += 1
                manufacturing_order = order.manufacturing_order
                
                validation = StatusSyncService.validate_status_consistency(
                    order, manufacturing_order
                )
                
                if not all(validation.values()):
                    mismatched_orders.append({
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'order_status': order.order_status,
                        'manufacturing_status': manufacturing_order.status,
                        'tracking_status': order.tracking_status,
                        'validation': validation
                    })
            
            if mismatched_orders:
                print(f"  ❌ تم اكتشاف {len(mismatched_orders)} طلب بحالات غير متطابقة:")
                for mismatch in mismatched_orders:
                    print(f"    - الطلب {mismatch['order_number']}: طلب({mismatch['order_status']}) ≠ تصنيع({mismatch['manufacturing_status']})")
                return False
            else:
                print(f"  ✅ جميع الطلبات ({total_orders_checked}) لها حالات متطابقة")
                return True
                
        except Exception as e:
            print(f"  ❌ خطأ في التحقق من الحالات: {str(e)}")
            return False

    def generate_detailed_report(self, test_results, duration, success_rate):
        """إنشاء تقرير مفصل للاختبار"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'comprehensive_updated',
            'duration_seconds': duration,
            'overall_success_rate': success_rate,
            'test_results': test_results,
            'statistics': {
                'customers_created': len(self.test_data.get('customers', [])),
                'orders_created': len(self.test_data.get('orders', [])),
                'manufacturing_orders_created': len(self.test_data.get('manufacturing_orders', [])),
                'branches_used': len(self.test_data.get('branches', [])),
                'salespersons_used': len(self.test_data.get('salespersons', [])),
            },
            'data_integrity': {
                'unique_customer_codes': self.check_unique_customer_codes(),
                'unique_order_numbers': self.check_unique_order_numbers(),
                'status_consistency': self.check_status_consistency()
            },
            'recommendations': self.generate_recommendations(test_results, success_rate)
        }
        
        return report

    def check_unique_customer_codes(self):
        """التحقق من فرادة أكواد العملاء"""
        try:
            all_codes = Customer.objects.values_list('code', flat=True)
            unique_codes = set(all_codes)
            return {
                'total_codes': len(all_codes),
                'unique_codes': len(unique_codes),
                'has_duplicates': len(all_codes) != len(unique_codes),
                'duplicate_count': len(all_codes) - len(unique_codes)
            }
        except:
            return {'error': 'فشل في التحقق من أكواد العملاء'}

    def check_unique_order_numbers(self):
        """التحقق من فرادة أرقام الطلبات"""
        try:
            all_numbers = Order.objects.values_list('order_number', flat=True)
            unique_numbers = set(all_numbers)
            return {
                'total_numbers': len(all_numbers),
                'unique_numbers': len(unique_numbers),
                'has_duplicates': len(all_numbers) != len(unique_numbers),
                'duplicate_count': len(all_numbers) - len(unique_numbers)
            }
        except:
            return {'error': 'فشل في التحقق من أرقام الطلبات'}

    def check_status_consistency(self):
        """التحقق من تطابق الحالات"""
        try:
            from crm.services.base_service import StatusSyncService
            
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            total_orders = orders_with_manufacturing.count()
            mismatched_orders = 0
            
            for order in orders_with_manufacturing:
                validation = StatusSyncService.validate_status_consistency(
                    order, order.manufacturing_order
                )
                if not all(validation.values()):
                    mismatched_orders += 1
            
            return {
                'total_orders_checked': total_orders,
                'mismatched_orders': mismatched_orders,
                'consistency_rate': ((total_orders - mismatched_orders) / total_orders * 100) if total_orders > 0 else 100
            }
        except:
            return {'error': 'فشل في التحقق من تطابق الحالات'}

    def generate_recommendations(self, test_results, success_rate):
        """إنشاء توصيات بناءً على نتائج الاختبار"""
        recommendations = []
        
        if success_rate < 90:
            recommendations.append("يُنصح بمراجعة الاختبارات الفاشلة وإصلاح المشاكل")
        
        if not test_results.get('customers_with_codes', True):
            recommendations.append("يجب إصلاح مشكلة أكواد العملاء المكررة")
        
        if not test_results.get('orders_with_unique_numbers', True):
            recommendations.append("يجب إصلاح مشكلة أرقام الطلبات المكررة")
        
        if not test_results.get('manufacturing_and_sync', True):
            recommendations.append("يجب تحسين مزامنة الحالات بين الطلبات والتصنيع")
        
        if success_rate >= 95:
            recommendations.append("النظام يعمل بكفاءة عالية - يُنصح بالمراقبة الدورية")
        elif success_rate >= 85:
            recommendations.append("النظام يعمل بشكل جيد - يُنصح بتحسينات طفيفة")
        else:
            recommendations.append("النظام يحتاج إصلاحات جوهرية قبل الإنتاج")
        
        return recommendations

    def test_comprehensive_status_consistency(self):
        """اختبار شامل لتطابق الحالات في جميع أنحاء النظام"""
        print("\n🔍 اختبار شامل لتطابق الحالات في جميع أنحاء النظام...")
        
        try:
            from crm.services.base_service import StatusSyncService
            from manufacturing.models import ManufacturingOrder
            
            all_issues = []
            total_checks = 0
            
            # 1. فحص تطابق الحالات بين Order و ManufacturingOrder
            print("  📋 فحص تطابق الحالات بين الطلبات والتصنيع...")
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                total_checks += 1
                manufacturing_order = order.manufacturing_order
                
                # فحص تطابق order_status
                if order.order_status != manufacturing_order.status:
                    all_issues.append({
                        'type': 'order_manufacturing_mismatch',
                        'order_number': order.order_number,
                        'order_status': order.order_status,
                        'manufacturing_status': manufacturing_order.status,
                        'severity': 'critical'
                    })
                
                # فحص تطابق tracking_status
                expected_tracking = StatusSyncService.TRACKING_STATUS_MAPPING.get(
                    manufacturing_order.status
                )
                if expected_tracking and order.tracking_status != expected_tracking:
                    all_issues.append({
                        'type': 'tracking_status_mismatch',
                        'order_number': order.order_number,
                        'current_tracking': order.tracking_status,
                        'expected_tracking': expected_tracking,
                        'manufacturing_status': manufacturing_order.status,
                        'severity': 'high'
                    })
            
            # 2. فحص الحالات في قاعدة البيانات
            print("  🗃️ فحص صحة الحالات في قاعدة البيانات...")
            
            # فحص order_status صحيحة
            valid_order_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
            invalid_order_statuses = Order.objects.exclude(
                order_status__in=valid_order_statuses
            )
            
            for order in invalid_order_statuses:
                total_checks += 1
                all_issues.append({
                    'type': 'invalid_order_status',
                    'order_number': order.order_number,
                    'invalid_status': order.order_status,
                    'severity': 'critical'
                })
            
            # فحص tracking_status صحيحة
            valid_tracking_statuses = [choice[0] for choice in Order.TRACKING_STATUS_CHOICES]
            invalid_tracking_statuses = Order.objects.exclude(
                tracking_status__in=valid_tracking_statuses
            )
            
            for order in invalid_tracking_statuses:
                total_checks += 1
                all_issues.append({
                    'type': 'invalid_tracking_status',
                    'order_number': order.order_number,
                    'invalid_status': order.tracking_status,
                    'severity': 'critical'
                })
            
            # 3. فحص تطابق الحالات في Templates
            print("  🎨 فحص تطابق الحالات في واجهات المستخدم...")
            
            # فحص كل طلب له manufacturing order
            for order in orders_with_manufacturing:
                total_checks += 1
                
                # محاكاة ما يظهر في order_list.html
                template_display = self._get_template_status_display(order.order_status)
                
                # محاكاة ما يظهر في manufacturing_list.html
                manufacturing_display = self._get_manufacturing_template_display(
                    order.manufacturing_order.status
                )
                
                if template_display != manufacturing_display:
                    all_issues.append({
                        'type': 'template_display_mismatch',
                        'order_number': order.order_number,
                        'order_template_display': template_display,
                        'manufacturing_template_display': manufacturing_display,
                        'severity': 'medium'
                    })
            
            # 4. فحص تطابق الحالات في API responses
            print("  🔗 فحص تطابق الحالات في API...")
            
            for order in orders_with_manufacturing:
                total_checks += 1
                
                # محاكاة API response
                api_order_status = order.order_status
                api_manufacturing_status = order.manufacturing_order.status
                
                if api_order_status != api_manufacturing_status:
                    all_issues.append({
                        'type': 'api_status_mismatch',
                        'order_number': order.order_number,
                        'api_order_status': api_order_status,
                        'api_manufacturing_status': api_manufacturing_status,
                        'severity': 'high'
                    })
            
            # 5. فحص تطابق الحالات في Signals و Services
            print("  ⚡ فحص تطابق الحالات في الخدمات والإشارات...")
            
            for order in orders_with_manufacturing:
                total_checks += 1
                manufacturing_order = order.manufacturing_order
                
                # فحص StatusSyncService
                validation = StatusSyncService.validate_status_consistency(
                    order, manufacturing_order
                )
                
                if not all(validation.values()):
                    all_issues.append({
                        'type': 'service_validation_failed',
                        'order_number': order.order_number,
                        'validation_details': validation,
                        'severity': 'high'
                    })
            
            # 6. فحص Admin Interface
            print("  👨‍💼 فحص تطابق الحالات في واجهة الإدارة...")
            
            for order in orders_with_manufacturing:
                total_checks += 1
                
                # محاكاة admin display
                admin_order_display = order.get_order_status_display()
                admin_manufacturing_display = order.manufacturing_order.get_status_display()
                
                # يجب أن تكون متطابقة
                if admin_order_display != admin_manufacturing_display:
                    all_issues.append({
                        'type': 'admin_display_mismatch',
                        'order_number': order.order_number,
                        'admin_order_display': admin_order_display,
                        'admin_manufacturing_display': admin_manufacturing_display,
                        'severity': 'medium'
                    })
            
            # تجميع النتائج
            critical_issues = [issue for issue in all_issues if issue['severity'] == 'critical']
            high_issues = [issue for issue in all_issues if issue['severity'] == 'high']
            medium_issues = [issue for issue in all_issues if issue['severity'] == 'medium']
            
            print(f"\n📊 نتائج الفحص الشامل:")
            print(f"  📈 إجمالي الفحوصات: {total_checks}")
            print(f"  🔴 مشاكل حرجة: {len(critical_issues)}")
            print(f"  🟡 مشاكل عالية الأهمية: {len(high_issues)}")
            print(f"  🟠 مشاكل متوسطة الأهمية: {len(medium_issues)}")
            
            # عرض تفاصيل المشاكل
            if critical_issues:
                print(f"\n🔴 المشاكل الحرجة:")
                for issue in critical_issues:
                    self._print_issue_details(issue)
            
            if high_issues:
                print(f"\n🟡 المشاكل عالية الأهمية:")
                for issue in high_issues:
                    self._print_issue_details(issue)
            
            if medium_issues:
                print(f"\n🟠 المشاكل متوسطة الأهمية:")
                for issue in medium_issues:
                    self._print_issue_details(issue)
            
            if not all_issues:
                print("  ✅ لا توجد مشاكل في تطابق الحالات!")
                return True
            else:
                print(f"  ❌ تم اكتشاف {len(all_issues)} مشكلة في تطابق الحالات")
                return False
                
        except Exception as e:
            print(f"  ❌ خطأ في الفحص الشامل: {str(e)}")
            return False
    
    def _get_template_status_display(self, order_status):
        """محاكاة عرض الحالة في Template"""
        template_mapping = {
            'pending_approval': 'قيد الموافقة',
            'pending': 'قيد الانتظار',
            'in_progress': 'قيد التصنيع',
            'ready_install': 'جاهز للتركيب',
            'completed': 'مكتمل',
            'delivered': 'تم التسليم',
            'rejected': 'مرفوض',
            'cancelled': 'ملغي'
        }
        return template_mapping.get(order_status, order_status)
    
    def _get_manufacturing_template_display(self, manufacturing_status):
        """محاكاة عرض حالة التصنيع في Template"""
        # نفس التطابق المطلوب
        return self._get_template_status_display(manufacturing_status)
    
    def _print_issue_details(self, issue):
        """طباعة تفاصيل المشكلة"""
        issue_type = issue['type']
        order_number = issue.get('order_number', 'غير محدد')
        
        if issue_type == 'order_manufacturing_mismatch':
            print(f"    - الطلب {order_number}: طلب({issue['order_status']}) ≠ تصنيع({issue['manufacturing_status']})")
        
        elif issue_type == 'tracking_status_mismatch':
            print(f"    - الطلب {order_number}: تتبع({issue['current_tracking']}) ≠ متوقع({issue['expected_tracking']})")
        
        elif issue_type == 'invalid_order_status':
            print(f"    - الطلب {order_number}: حالة طلب غير صحيحة ({issue['invalid_status']})")
        
        elif issue_type == 'invalid_tracking_status':
            print(f"    - الطلب {order_number}: حالة تتبع غير صحيحة ({issue['invalid_status']})")
        
        elif issue_type == 'template_display_mismatch':
            print(f"    - الطلب {order_number}: عرض مختلف في Templates")
        
        elif issue_type == 'api_status_mismatch':
            print(f"    - الطلب {order_number}: عدم تطابق في API")
        
        elif issue_type == 'service_validation_failed':
            print(f"    - الطلب {order_number}: فشل في التحقق من الخدمة")
        
        elif issue_type == 'admin_display_mismatch':
            print(f"    - الطلب {order_number}: عدم تطابق في واجهة الإدارة")

def main():
    """الدالة الرئيسية لتشغيل الاختبار"""
    print("🚀 بدء الاختبار الشامل للنظام")
    print("="*60)
    
    test = ComprehensiveSystemTest()
    results = test.run_comprehensive_test()
    
    return results

if __name__ == '__main__':
    main() 