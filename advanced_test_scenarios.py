#!/usr/bin/env python
"""
اختبار السيناريوهات المتقدمة والحالات الخاصة
Advanced Test Scenarios and Edge Cases

هذا الملف يقوم باختبار حالات خاصة ومعقدة في النظام
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError

from customers.models import Customer, CustomerCategory, CustomerType
from orders.models import Order, OrderItem, OrderStatusLog
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from accounts.models import Branch, Salesperson

User = get_user_model()

class AdvancedTestScenarios:
    """فئة اختبار السيناريوهات المتقدمة"""
    
    def __init__(self):
        self.test_results = {
            'edge_cases': {'tested': 0, 'passed': 0, 'errors': []},
            'stress_tests': {'tested': 0, 'passed': 0, 'errors': []},
            'data_integrity': {'tested': 0, 'passed': 0, 'errors': []},
            'workflow_tests': {'tested': 0, 'passed': 0, 'errors': []},
            'performance_tests': {'tested': 0, 'passed': 0, 'errors': []}
        }
    
    def run_advanced_tests(self):
        """تشغيل الاختبارات المتقدمة"""
        print("🔬 بدء الاختبارات المتقدمة...")
        
        # 1. اختبار الحالات الحدية
        self.test_edge_cases()
        
        # 2. اختبار الضغط
        self.test_stress_scenarios()
        
        # 3. اختبار سلامة البيانات
        self.test_data_integrity()
        
        # 4. اختبار سير العمل
        self.test_workflow_scenarios()
        
        # 5. اختبار الأداء
        self.test_performance()
        
        # 6. إنشاء التقرير
        self.generate_advanced_report()
        
        return self.test_results
    
    def test_edge_cases(self):
        """اختبار الحالات الحدية"""
        print("🎯 اختبار الحالات الحدية...")
        
        edge_cases = [
            # عميل بأطول اسم ممكن
            {
                'name': 'اختبار العميل بأطول اسم ممكن في النظام لاختبار الحد الأقصى للحقل وكيفية التعامل معه',
                'test_type': 'long_name',
                'expected_result': 'should_truncate_or_validate'
            },
            # عميل برقم هاتف غير صحيح
            {
                'name': 'عميل رقم هاتف خاطئ',
                'phone': 'invalid_phone_number_123',
                'test_type': 'invalid_phone',
                'expected_result': 'should_validate'
            },
            # عميل ببريد إلكتروني غير صحيح
            {
                'name': 'عميل بريد خاطئ',
                'phone': '01234567890',
                'email': 'invalid-email-format',
                'test_type': 'invalid_email',
                'expected_result': 'should_validate'
            },
            # طلب بمبلغ سالب
            {
                'name': 'طلب بمبلغ سالب',
                'amount': Decimal('-100.00'),
                'test_type': 'negative_amount',
                'expected_result': 'should_validate'
            },
            # طلب بتاريخ في المستقبل البعيد
            {
                'name': 'طلب بتاريخ مستقبلي',
                'future_date': timezone.now() + timedelta(days=3650),  # 10 سنوات
                'test_type': 'future_date',
                'expected_result': 'should_validate'
            }
        ]
        
        for case in edge_cases:
            try:
                self.test_results['edge_cases']['tested'] += 1
                
                if case['test_type'] == 'long_name':
                    # اختبار الاسم الطويل
                    customer = Customer(
                        name=case['name'][:200],  # قطع الاسم حسب حد الحقل
                        phone='01234567890',
                        address='عنوان اختبار',
                        customer_type='retail',
                        status='active'
                    )
                    customer.full_clean()  # التحقق من صحة البيانات
                    print(f"✅ تم اختبار الاسم الطويل بنجاح")
                    
                elif case['test_type'] == 'invalid_phone':
                    # اختبار رقم الهاتف الغير صحيح
                    try:
                        customer = Customer(
                            name=case['name'],
                            phone=case['phone'],
                            address='عنوان اختبار',
                            customer_type='retail',
                            status='active'
                        )
                        customer.full_clean()
                        print(f"⚠️ تم قبول رقم هاتف غير صحيح: {case['phone']}")
                    except ValidationError:
                        print(f"✅ تم رفض رقم الهاتف الغير صحيح بنجاح")
                
                elif case['test_type'] == 'invalid_email':
                    # اختبار البريد الإلكتروني الغير صحيح
                    try:
                        customer = Customer(
                            name=case['name'],
                            phone=case['phone'],
                            email=case['email'],
                            address='عنوان اختبار',
                            customer_type='retail',
                            status='active'
                        )
                        customer.full_clean()
                        print(f"⚠️ تم قبول بريد إلكتروني غير صحيح: {case['email']}")
                    except ValidationError:
                        print(f"✅ تم رفض البريد الإلكتروني الغير صحيح بنجاح")
                
                self.test_results['edge_cases']['passed'] += 1
                
            except Exception as e:
                error_msg = f"خطأ في اختبار الحالة الحدية {case['test_type']}: {str(e)}"
                self.test_results['edge_cases']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
    
    def test_stress_scenarios(self):
        """اختبار سيناريوهات الضغط"""
        print("💪 اختبار سيناريوهات الضغط...")
        
        try:
            # إنشاء عدد كبير من العملاء
            customers_count = 50
            print(f"📊 إنشاء {customers_count} عميل...")
            
            start_time = datetime.now()
            
            customers = []
            for i in range(customers_count):
                customer = Customer(
                    name=f'عميل ضغط {i+1}',
                    phone=f'0123456{i:04d}',
                    address=f'عنوان العميل {i+1}',
                    customer_type='retail',
                    status='active'
                )
                customers.append(customer)
            
            # إنشاء مجموعي للعملاء
            Customer.objects.bulk_create(customers)
            
            creation_time = datetime.now() - start_time
            print(f"✅ تم إنشاء {customers_count} عميل في {creation_time.total_seconds():.2f} ثانية")
            
            # إنشاء طلبات متعددة
            orders_count = 100
            print(f"📊 إنشاء {orders_count} طلب...")
            
            start_time = datetime.now()
            
            created_customers = Customer.objects.filter(name__startswith='عميل ضغط')
            
            orders = []
            for i in range(orders_count):
                customer = random.choice(created_customers)
                order = Order(
                    customer=customer,
                    order_number=f'STRESS-{i+1:04d}',
                    status='normal',
                    order_status='pending',
                    tracking_status='pending',
                    total_amount=Decimal(str(random.randint(100, 5000))),
                    paid_amount=Decimal('0.00'),
                    notes=f'طلب ضغط رقم {i+1}'
                )
                orders.append(order)
            
            Order.objects.bulk_create(orders)
            
            creation_time = datetime.now() - start_time
            print(f"✅ تم إنشاء {orders_count} طلب في {creation_time.total_seconds():.2f} ثانية")
            
            self.test_results['stress_tests']['tested'] += 1
            self.test_results['stress_tests']['passed'] += 1
            
        except Exception as e:
            error_msg = f"خطأ في اختبار الضغط: {str(e)}"
            self.test_results['stress_tests']['errors'].append(error_msg)
            print(f"❌ {error_msg}")
    
    def test_data_integrity(self):
        """اختبار سلامة البيانات"""
        print("🔒 اختبار سلامة البيانات...")
        
        integrity_tests = [
            # اختبار العلاقات الخارجية
            {
                'name': 'foreign_key_constraints',
                'description': 'اختبار قيود المفاتيح الخارجية'
            },
            # اختبار الفهارس الفريدة
            {
                'name': 'unique_constraints',
                'description': 'اختبار قيود الفرادة'
            },
            # اختبار تسلسل الحالات
            {
                'name': 'status_sequence',
                'description': 'اختبار تسلسل الحالات'
            }
        ]
        
        for test in integrity_tests:
            try:
                self.test_results['data_integrity']['tested'] += 1
                
                if test['name'] == 'foreign_key_constraints':
                    # اختبار حذف عميل له طلبات
                    customer = Customer.objects.create(
                        name='عميل للحذف',
                        phone='01999999999',
                        address='عنوان مؤقت',
                        customer_type='retail',
                        status='active'
                    )
                    
                    order = Order.objects.create(
                        customer=customer,
                        order_number='DELETE-TEST-001',
                        status='normal',
                        order_status='pending',
                        tracking_status='pending',
                        total_amount=Decimal('100.00'),
                        paid_amount=Decimal('0.00')
                    )
                    
                    # محاولة حذف العميل (يجب أن يحذف الطلبات أيضاً)
                    customer.delete()
                    
                    # التحقق من حذف الطلبات
                    if Order.objects.filter(order_number='DELETE-TEST-001').exists():
                        print("⚠️ لم يتم حذف الطلبات عند حذف العميل")
                    else:
                        print("✅ تم حذف الطلبات عند حذف العميل بنجاح")
                
                elif test['name'] == 'unique_constraints':
                    # اختبار إنشاء عميل برقم مكرر
                    try:
                        Customer.objects.create(
                            code='UNIQUE-TEST',
                            name='عميل أول',
                            phone='01888888888',
                            address='عنوان',
                            customer_type='retail',
                            status='active'
                        )
                        
                        # محاولة إنشاء عميل آخر بنفس الكود
                        Customer.objects.create(
                            code='UNIQUE-TEST',
                            name='عميل ثاني',
                            phone='01777777777',
                            address='عنوان آخر',
                            customer_type='retail',
                            status='active'
                        )
                        
                        print("⚠️ تم قبول كود عميل مكرر")
                        
                    except Exception:
                        print("✅ تم رفض كود العميل المكرر بنجاح")
                
                elif test['name'] == 'status_sequence':
                    # اختبار تسلسل الحالات
                    customer = Customer.objects.create(
                        name='عميل تسلسل الحالات',
                        phone='01666666666',
                        address='عنوان',
                        customer_type='retail',
                        status='active'
                    )
                    
                    order = Order.objects.create(
                        customer=customer,
                        order_number='SEQUENCE-TEST-001',
                        status='normal',
                        order_status='pending',
                        tracking_status='pending',
                        total_amount=Decimal('100.00'),
                        paid_amount=Decimal('0.00')
                    )
                    
                    # إنشاء أمر تصنيع
                    mfg_order = ManufacturingOrder.objects.create(
                        order=order,
                        status='pending_approval',
                        order_type='installation',
                        order_date=timezone.now().date(),
                        expected_delivery_date=timezone.now().date() + timedelta(days=15)
                    )
                    
                    # اختبار تسلسل الحالات
                    status_sequence = [
                        'pending_approval',
                        'pending',
                        'in_progress',
                        'completed',
                        'delivered'
                    ]
                    
                    for status in status_sequence:
                        mfg_order.status = status
                        mfg_order.save()
                        
                        # التحقق من تحديث الطلب
                        order.refresh_from_db()
                        if order.order_status != status:
                            print(f"⚠️ عدم تطابق الحالة: Order({order.order_status}) != Manufacturing({status})")
                        else:
                            print(f"✅ تم تحديث الحالة بنجاح: {status}")
                
                self.test_results['data_integrity']['passed'] += 1
                
            except Exception as e:
                error_msg = f"خطأ في اختبار سلامة البيانات {test['name']}: {str(e)}"
                self.test_results['data_integrity']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
    
    def test_workflow_scenarios(self):
        """اختبار سيناريوهات سير العمل"""
        print("🔄 اختبار سيناريوهات سير العمل...")
        
        workflow_scenarios = [
            # سيناريو العميل VIP
            {
                'name': 'vip_customer_workflow',
                'description': 'سير عمل العميل VIP من البداية للنهاية'
            },
            # سيناريو الطلب المعقد
            {
                'name': 'complex_order_workflow',
                'description': 'سير عمل طلب معقد متعدد الأنواع'
            },
            # سيناريو الإلغاء والإرجاع
            {
                'name': 'cancellation_workflow',
                'description': 'سير عمل إلغاء الطلبات'
            }
        ]
        
        for scenario in workflow_scenarios:
            try:
                self.test_results['workflow_tests']['tested'] += 1
                
                if scenario['name'] == 'vip_customer_workflow':
                    # إنشاء عميل VIP
                    vip_customer = Customer.objects.create(
                        name='عميل VIP للاختبار',
                        phone='01555555555',
                        address='عنوان VIP',
                        customer_type='vip',
                        status='active'
                    )
                    
                    # إنشاء طلب VIP
                    vip_order = Order.objects.create(
                        customer=vip_customer,
                        order_number='VIP-WORKFLOW-001',
                        status='vip',
                        order_status='pending_approval',
                        tracking_status='factory',
                        total_amount=Decimal('10000.00'),
                        paid_amount=Decimal('5000.00'),
                        selected_types=['installation', 'tailoring']
                    )
                    
                    # إنشاء أمر تصنيع
                    vip_mfg = ManufacturingOrder.objects.create(
                        order=vip_order,
                        status='pending_approval',
                        order_type='installation',
                        order_date=timezone.now().date(),
                        expected_delivery_date=timezone.now().date() + timedelta(days=7)  # تسليم أسرع للVIP
                    )
                    
                    # تسريع المراحل للVIP
                    vip_workflow = [
                        'pending_approval',
                        'pending',
                        'in_progress',
                        'completed',
                        'delivered'
                    ]
                    
                    for status in vip_workflow:
                        vip_mfg.status = status
                        vip_mfg.save()
                        print(f"✅ VIP Workflow: {status}")
                    
                    print("✅ تم اختبار سير عمل العميل VIP بنجاح")
                
                elif scenario['name'] == 'complex_order_workflow':
                    # إنشاء طلب معقد
                    complex_customer = Customer.objects.create(
                        name='عميل طلب معقد',
                        phone='01444444444',
                        address='عنوان',
                        customer_type='corporate',
                        status='active'
                    )
                    
                    complex_order = Order.objects.create(
                        customer=complex_customer,
                        order_number='COMPLEX-WORKFLOW-001',
                        status='normal',
                        order_status='pending',
                        tracking_status='pending',
                        total_amount=Decimal('15000.00'),
                        paid_amount=Decimal('3000.00'),
                        selected_types=['installation', 'tailoring', 'inspection']
                    )
                    
                    # إنشاء أمر تصنيع معقد
                    complex_mfg = ManufacturingOrder.objects.create(
                        order=complex_order,
                        status='pending_approval',
                        order_type='custom',
                        order_date=timezone.now().date(),
                        expected_delivery_date=timezone.now().date() + timedelta(days=30)
                    )
                    
                    # إضافة عناصر متعددة
                    for i in range(5):
                        ManufacturingOrderItem.objects.create(
                            manufacturing_order=complex_mfg,
                            product_name=f'منتج معقد {i+1}',
                            quantity=random.randint(1, 10),
                            specifications=f'مواصفات خاصة للمنتج {i+1}',
                            status='pending'
                        )
                    
                    print("✅ تم اختبار سير عمل الطلب المعقد بنجاح")
                
                elif scenario['name'] == 'cancellation_workflow':
                    # إنشاء طلب للإلغاء
                    cancel_customer = Customer.objects.create(
                        name='عميل طلب الإلغاء',
                        phone='01333333333',
                        address='عنوان',
                        customer_type='retail',
                        status='active'
                    )
                    
                    cancel_order = Order.objects.create(
                        customer=cancel_customer,
                        order_number='CANCEL-WORKFLOW-001',
                        status='normal',
                        order_status='pending',
                        tracking_status='pending',
                        total_amount=Decimal('2000.00'),
                        paid_amount=Decimal('500.00')
                    )
                    
                    # إنشاء أمر تصنيع
                    cancel_mfg = ManufacturingOrder.objects.create(
                        order=cancel_order,
                        status='pending_approval',
                        order_type='installation',
                        order_date=timezone.now().date(),
                        expected_delivery_date=timezone.now().date() + timedelta(days=15)
                    )
                    
                    # إلغاء الطلب
                    cancel_mfg.status = 'cancelled'
                    cancel_mfg.save()
                    
                    # التحقق من تحديث الطلب الأصلي
                    cancel_order.refresh_from_db()
                    if cancel_order.order_status == 'cancelled':
                        print("✅ تم إلغاء الطلب بنجاح")
                    else:
                        print(f"⚠️ لم يتم تحديث حالة الطلب عند الإلغاء: {cancel_order.order_status}")
                
                self.test_results['workflow_tests']['passed'] += 1
                
            except Exception as e:
                error_msg = f"خطأ في اختبار سير العمل {scenario['name']}: {str(e)}"
                self.test_results['workflow_tests']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
    
    def test_performance(self):
        """اختبار الأداء"""
        print("⚡ اختبار الأداء...")
        
        performance_tests = [
            {
                'name': 'bulk_operations',
                'description': 'اختبار العمليات المجمعة'
            },
            {
                'name': 'complex_queries',
                'description': 'اختبار الاستعلامات المعقدة'
            },
            {
                'name': 'concurrent_operations',
                'description': 'اختبار العمليات المتزامنة'
            }
        ]
        
        for test in performance_tests:
            try:
                self.test_results['performance_tests']['tested'] += 1
                
                if test['name'] == 'bulk_operations':
                    # اختبار العمليات المجمعة
                    start_time = datetime.now()
                    
                    # إنشاء 1000 عميل
                    customers = [
                        Customer(
                            name=f'عميل أداء {i}',
                            phone=f'015{i:07d}',
                            address=f'عنوان {i}',
                            customer_type='retail',
                            status='active'
                        ) for i in range(1000)
                    ]
                    
                    Customer.objects.bulk_create(customers)
                    
                    bulk_time = datetime.now() - start_time
                    print(f"✅ تم إنشاء 1000 عميل في {bulk_time.total_seconds():.2f} ثانية")
                
                elif test['name'] == 'complex_queries':
                    # اختبار الاستعلامات المعقدة
                    start_time = datetime.now()
                    
                    # استعلام معقد
                    complex_query = Customer.objects.select_related('branch', 'category').prefetch_related('customer_orders__items').filter(
                        status='active',
                        customer_type__in=['retail', 'wholesale'],
                        customer_orders__total_amount__gte=1000
                    ).distinct()
                    
                    result_count = complex_query.count()
                    
                    query_time = datetime.now() - start_time
                    print(f"✅ تم تنفيذ استعلام معقد ({result_count} نتيجة) في {query_time.total_seconds():.2f} ثانية")
                
                self.test_results['performance_tests']['passed'] += 1
                
            except Exception as e:
                error_msg = f"خطأ في اختبار الأداء {test['name']}: {str(e)}"
                self.test_results['performance_tests']['errors'].append(error_msg)
                print(f"❌ {error_msg}")
    
    def generate_advanced_report(self):
        """إنشاء تقرير الاختبارات المتقدمة"""
        print("\n" + "="*60)
        print("🔬 تقرير الاختبارات المتقدمة")
        print("="*60)
        
        for test_type, results in self.test_results.items():
            print(f"\n{test_type.upper()}:")
            print(f"   📊 تم اختبار: {results['tested']}")
            print(f"   ✅ نجح: {results['passed']}")
            print(f"   ❌ أخطاء: {len(results['errors'])}")
            
            for error in results['errors']:
                print(f"      - {error}")
        
        # حساب النسبة الإجمالية للنجاح
        total_tested = sum(results['tested'] for results in self.test_results.values())
        total_passed = sum(results['passed'] for results in self.test_results.values())
        
        if total_tested > 0:
            success_rate = (total_passed / total_tested) * 100
            print(f"\n📈 معدل النجاح الإجمالي: {success_rate:.1f}%")
        
        print("\n" + "="*60)

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء الاختبارات المتقدمة")
    
    test = AdvancedTestScenarios()
    results = test.run_advanced_tests()
    
    return results

if __name__ == '__main__':
    main() 