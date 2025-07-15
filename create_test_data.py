#!/usr/bin/env python
"""
سكريبت إنشاء بيانات اختبارية شاملة للنظام
"""
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from accounts.models import User, Department
from customers.models import Customer
from orders.models import Order
from installations.models import InstallationSchedule, InstallationTeam, Technician
from django.utils import timezone
from installations.models import (
    ModificationRequest, ModificationImage, ManufacturingOrder as InstallationManufacturingOrder,
    ModificationReport, ReceiptMemo, InstallationPayment, InstallationArchive, CustomerDebt,
    InstallationAnalytics, ModificationErrorAnalysis, ModificationErrorType
)


def create_test_users():
    """إنشاء مستخدمين اختبار"""
    print("إنشاء مستخدمين اختبار...")
    
    # إنشاء مدير النظام
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
        print("✓ تم إنشاء مدير النظام")
    
    # إنشاء مستخدمين عاديين
    users_data = [
        {'username': 'sales1', 'first_name': 'أحمد', 'last_name': 'محمد', 'email': 'sales1@example.com'},
        {'username': 'sales2', 'first_name': 'فاطمة', 'last_name': 'علي', 'email': 'sales2@example.com'},
        {'username': 'technician1', 'first_name': 'محمد', 'last_name': 'حسن', 'email': 'tech1@example.com'},
        {'username': 'technician2', 'first_name': 'علي', 'last_name': 'أحمد', 'email': 'tech2@example.com'},
        {'username': 'inspector1', 'first_name': 'سارة', 'last_name': 'محمد', 'email': 'inspector1@example.com'},
    ]
    
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults=user_data
        )
        if created:
            user.set_password('test123')
            user.save()
            print(f"✓ تم إنشاء المستخدم: {user_data['username']}")


def create_test_departments():
    """إنشاء أقسام اختبار"""
    print("إنشاء أقسام اختبار...")
    
    departments_data = [
        {'name': 'المبيعات', 'description': 'قسم المبيعات والتسويق'},
        {'name': 'التصنيع', 'description': 'قسم التصنيع والإنتاج'},
        {'name': 'التركيبات', 'description': 'قسم التركيبات والخدمات'},
        {'name': 'المعاينات', 'description': 'قسم المعاينات والجودة'},
        {'name': 'المخزون', 'description': 'قسم إدارة المخزون'},
        {'name': 'الحسابات', 'description': 'قسم الحسابات والمالية'},
    ]
    
    for dept_data in departments_data:
        dept, created = Department.objects.get_or_create(
            name=dept_data['name'],
            defaults=dept_data
        )
        if created:
            print(f"✓ تم إنشاء القسم: {dept_data['name']}")


def create_test_customers():
    """إنشاء عملاء اختبار"""
    print("إنشاء عملاء اختبار...")
    
    customers_data = [
        {
            'name': 'أحمد محمد علي',
            'phone': '01012345678',
            'email': 'ahmed@example.com',
            'address': 'شارع النيل، القاهرة',
            'customer_type': 'individual'
        },
        {
            'name': 'شركة النور للمقاولات',
            'phone': '01087654321',
            'email': 'info@alnour.com',
            'address': 'شارع التحرير، الجيزة',
            'customer_type': 'company'
        },
        {
            'name': 'فاطمة حسن أحمد',
            'phone': '01011223344',
            'email': 'fatima@example.com',
            'address': 'شارع الهرم، الجيزة',
            'customer_type': 'individual'
        },
        {
            'name': 'مؤسسة الخير للخدمات',
            'phone': '01055667788',
            'email': 'info@alkhair.org',
            'address': 'شارع المعادي، القاهرة',
            'customer_type': 'company'
        },
        {
            'name': 'محمد علي حسن',
            'phone': '01099887766',
            'email': 'mohamed@example.com',
            'address': 'شارع العباسية، القاهرة',
            'customer_type': 'individual'
        },
    ]
    
    for customer_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            phone=customer_data['phone'],
            defaults=customer_data
        )
        if created:
            print(f"✓ تم إنشاء العميل: {customer_data['name']}")


def create_test_orders():
    """إنشاء طلبات اختبار"""
    print("إنشاء طلبات اختبار...")
    
    customers = list(Customer.objects.all())
    users = list(User.objects.filter(is_staff=True))
    
    order_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
    order_types = ['kitchen', 'bathroom', 'bedroom', 'living_room', 'office']
    
    for i in range(20):
        customer = random.choice(customers)
        salesperson = random.choice(users)
        status = random.choice(order_statuses)
        order_type = random.choice(order_types)
        
        # إنشاء طلب
        order = Order.objects.create(
            customer=customer,
            salesperson=salesperson,
            order_type=order_type,
            order_status=status,
            total_amount=Decimal(random.randint(5000, 50000)),
            paid_amount=Decimal(random.randint(1000, 20000)),
            description=f'طلب اختبار رقم {i+1}',
            created_at=timezone.now() - timedelta(days=random.randint(1, 30))
        )
        print(f"✓ تم إنشاء الطلب: {order.order_number}")


def create_test_installation_teams():
    """إنشاء فرق تركيب اختبار"""
    print("إنشاء فرق تركيب اختبار...")
    
    teams_data = [
        {'name': 'فريق القاهرة', 'description': 'فريق التركيبات في القاهرة'},
        {'name': 'فريق الجيزة', 'description': 'فريق التركيبات في الجيزة'},
        {'name': 'فريق الإسكندرية', 'description': 'فريق التركيبات في الإسكندرية'},
    ]
    
    for team_data in teams_data:
        team, created = InstallationTeam.objects.get_or_create(
            name=team_data['name'],
            defaults=team_data
        )
        if created:
            print(f"✓ تم إنشاء الفريق: {team_data['name']}")


def create_test_technicians():
    """إنشاء فنيين اختبار"""
    print("إنشاء فنيين اختبار...")
    
    technicians_data = [
        {'name': 'أحمد فني', 'phone': '01011111111', 'specialization': 'تركيب مطابخ'},
        {'name': 'محمد فني', 'phone': '01022222222', 'specialization': 'تركيب حمامات'},
        {'name': 'علي فني', 'phone': '01033333333', 'specialization': 'تركيب غرف نوم'},
        {'name': 'حسن فني', 'phone': '01044444444', 'specialization': 'تركيب غرف معيشة'},
    ]
    
    for tech_data in technicians_data:
        tech, created = Technician.objects.get_or_create(
            phone=tech_data['phone'],
            defaults=tech_data
        )
        if created:
            print(f"✓ تم إنشاء الفني: {tech_data['name']}")


def create_test_installations():
    """إنشاء تركيبات اختبار"""
    print("إنشاء تركيبات اختبار...")
    
    orders = list(Order.objects.filter(order_status='completed'))
    teams = list(InstallationTeam.objects.all())
    technicians = list(Technician.objects.all())
    
    installation_statuses = ['pending', 'scheduled', 'in_progress', 'completed', 'cancelled']
    
    for i in range(15):
        if orders:
            order = random.choice(orders)
            team = random.choice(teams)
            technician = random.choice(technicians)
            status = random.choice(installation_statuses)
            
            installation = InstallationSchedule.objects.create(
                order=order,
                team=team,
                technician=technician,
                status=status,
                scheduled_date=timezone.now().date() + timedelta(days=random.randint(1, 30)),
                estimated_duration=random.randint(2, 8),
                notes=f'تركيب اختبار رقم {i+1}',
                created_at=timezone.now() - timedelta(days=random.randint(1, 20))
            )
            print(f"✓ تم إنشاء التركيب: {installation.id}")


def create_test_modification_error_types():
    """إنشاء أنواع أسباب التعديلات"""
    print("إنشاء أنواع أسباب التعديلات...")
    
    error_types_data = [
        {'name': 'خطأ في القياسات', 'description': 'أخطاء في قياسات العميل أو الموقع'},
        {'name': 'خطأ في التصميم', 'description': 'أخطاء في التصميم أو الرسومات'},
        {'name': 'خطأ في المواد', 'description': 'أخطاء في نوع أو جودة المواد المستخدمة'},
        {'name': 'خطأ في التركيب', 'description': 'أخطاء أثناء عملية التركيب'},
        {'name': 'طلب تعديل من العميل', 'description': 'تعديلات مطلوبة من العميل'},
        {'name': 'مشكلة في الجودة', 'description': 'مشاكل في جودة المنتج أو التركيب'},
        {'name': 'مشكلة في الشحن', 'description': 'أضرار أثناء الشحن أو النقل'},
        {'name': 'مشكلة في التخزين', 'description': 'أضرار أثناء التخزين'},
    ]
    
    for error_type_data in error_types_data:
        error_type, created = ModificationErrorType.objects.get_or_create(
            name=error_type_data['name'],
            defaults=error_type_data
        )
        if created:
            print(f"✓ تم إنشاء نوع السبب: {error_type_data['name']}")


def create_test_modifications():
    """إنشاء تعديلات اختبار"""
    print("إنشاء تعديلات اختبار...")
    
    installations = list(InstallationSchedule.objects.all())
    customers = list(Customer.objects.all())
    
    modification_types = ['design', 'measurement', 'material', 'installation', 'customer_request']
    priorities = ['low', 'medium', 'high', 'urgent']
    
    for i in range(10):
        if installations:
            installation = random.choice(installations)
            customer = installation.order.customer
            modification_type = random.choice(modification_types)
            priority = random.choice(priorities)
            
            modification = ModificationRequest.objects.create(
                installation=installation,
                customer=customer,
                modification_type=modification_type,
                priority=priority,
                description=f'طلب تعديل اختبار رقم {i+1} - {modification_type}',
                estimated_cost=Decimal(random.randint(500, 5000)),
                customer_approval=random.choice([True, False]),
                created_at=timezone.now() - timedelta(days=random.randint(1, 15))
            )
            print(f"✓ تم إنشاء التعديل: {modification.id}")


def create_test_error_analyses():
    """إنشاء تحليلات أخطاء اختبار"""
    print("إنشاء تحليلات أخطاء اختبار...")
    
    modifications = list(ModificationRequest.objects.all())
    error_types = list(ModificationErrorType.objects.all())
    
    for i in range(8):
        if modifications and error_types:
            modification = random.choice(modifications)
            error_type = random.choice(error_types)
            
            analysis = ModificationErrorAnalysis.objects.create(
                modification_request=modification,
                error_type=error_type,
                error_description=f'وصف خطأ اختبار رقم {i+1}',
                root_cause=f'السبب الجذري للخطأ رقم {i+1}',
                solution_applied=f'الحل المطبق للخطأ رقم {i+1}',
                prevention_measures=f'إجراءات الوقاية للخطأ رقم {i+1}',
                cost_impact=Decimal(random.randint(200, 2000)),
                time_impact_hours=random.randint(2, 12),
                created_at=timezone.now() - timedelta(days=random.randint(1, 10))
            )
            print(f"✓ تم إنشاء تحليل الخطأ: {analysis.id}")


def create_test_analytics():
    """إنشاء بيانات تحليلية اختبار"""
    print("إنشاء بيانات تحليلية اختبار...")
    
    # إنشاء بيانات للشهور الستة الماضية
    for i in range(6):
        month_date = timezone.now().date().replace(day=1) - timedelta(days=30*i)
        
        analytics = InstallationAnalytics.objects.create(
            month=month_date,
            total_installations=random.randint(10, 50),
            completed_installations=random.randint(5, 30),
            pending_installations=random.randint(2, 15),
            in_progress_installations=random.randint(3, 20),
            total_customers=random.randint(8, 25),
            new_customers=random.randint(2, 10),
            total_visits=random.randint(20, 80),
            total_modifications=random.randint(2, 12),
        )
        analytics.calculate_rates()
        print(f"✓ تم إنشاء تحليل شهري: {month_date.strftime('%Y-%m')}")


def main():
    """الوظيفة الرئيسية"""
    print("بدء إنشاء بيانات اختبارية شاملة...")
    print("=" * 50)
    
    try:
        create_test_users()
        create_test_departments()
        create_test_customers()
        create_test_orders()
        create_test_installation_teams()
        create_test_technicians()
        create_test_installations()
        create_test_modification_error_types()
        create_test_modifications()
        create_test_error_analyses()
        create_test_analytics()
        
        print("=" * 50)
        print("✓ تم إنشاء جميع البيانات الاختبارية بنجاح!")
        print("\nملخص البيانات المنشأة:")
        print(f"- المستخدمين: {User.objects.count()}")
        print(f"- الأقسام: {Department.objects.count()}")
        print(f"- العملاء: {Customer.objects.count()}")
        print(f"- الطلبات: {Order.objects.count()}")
        print(f"- فرق التركيب: {InstallationTeam.objects.count()}")
        print(f"- الفنيين: {Technician.objects.count()}")
        print(f"- التركيبات: {InstallationSchedule.objects.count()}")
        print(f"- أنواع أسباب التعديلات: {ModificationErrorType.objects.count()}")
        print(f"- التعديلات: {ModificationRequest.objects.count()}")
        print(f"- تحليلات الأخطاء: {ModificationErrorAnalysis.objects.count()}")
        print(f"- البيانات التحليلية: {InstallationAnalytics.objects.count()}")
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main() 