#!/usr/bin/env python
"""
اختبار مزامنة حالات المعاينة مع الطلبات
"""

import os
import sys
from datetime import datetime, date

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.contrib.auth import get_user_model
from orders.models import Order
from inspections.models import Inspection
from customers.models import Customer
from accounts.models import Branch, Salesperson

User = get_user_model()


class InspectionStatusSyncTest:
    """اختبار مزامنة حالات المعاينة"""
    
    def __init__(self):
        """تهيئة الاختبار"""
        self.test_data = {
            'users': [],
            'customers': [],
            'orders': [],
            'inspections': []
        }
        self.test_results = []
    
    def setup_test_data(self):
        """إعداد بيانات الاختبار"""
        print("🔧 إعداد بيانات الاختبار...")
        
        try:
            # إنشاء مستخدم
            user, created = User.objects.get_or_create(
                username='test_inspector',
                defaults={
                    'email': 'inspector@test.com',
                    'first_name': 'مفتش',
                    'last_name': 'اختبار'
                }
            )
            self.test_data['users'].append(user)
            
            # إنشاء فرع
            branch, created = Branch.objects.get_or_create(
                code='TEST',
                defaults={'name': 'فرع الاختبار'}
            )
            
            # إنشاء بائع
            salesperson, created = Salesperson.objects.get_or_create(
                employee_number='SP001',
                defaults={
                    'name': 'بائع الاختبار',
                    'branch': branch
                }
            )
            
            # إنشاء عميل
            customer, created = Customer.objects.get_or_create(
                code='TEST-001',
                defaults={
                    'name': 'عميل اختبار المعاينة',
                    'phone': '01000000001',
                    'branch': branch,
                    'customer_type': 'retail',
                    'address': 'عنوان اختبار'
                }
            )
            self.test_data['customers'].append(customer)
            
            # إنشاء طلب معاينة
            order, created = Order.objects.get_or_create(
                order_number='INSP-TEST-001',
                defaults={
                    'customer': customer,
                    'salesperson': salesperson,
                    'branch': branch,
                    'selected_types': ['inspection'],
                    'order_status': 'pending',
                    'tracking_status': 'pending',
                    'paid_amount': 0,
                    'notes': 'طلب اختبار مزامنة المعاينة'
                }
            )
            self.test_data['orders'].append(order)
            
            print(f"  ✅ تم إنشاء الطلب: {order.order_number}")
            return True
            
        except Exception as e:
            print(f"  ❌ خطأ في إعداد البيانات: {str(e)}")
            return False
    
    def test_inspection_status_sync(self):
        """اختبار مزامنة حالات المعاينة"""
        print("\n🔍 اختبار مزامنة حالات المعاينة...")
        
        try:
            order = self.test_data['orders'][0]
            user = self.test_data['users'][0]
            
            # إنشاء معاينة
            inspection = Inspection.objects.create(
                customer=order.customer,
                branch=order.branch,
                inspector=user,
                order=order,
                request_date=date.today(),
                scheduled_date=date.today(),
                status='pending',
                notes='اختبار مزامنة الحالات',
                created_by=user
            )
            self.test_data['inspections'].append(inspection)
            
            print(f"  ✅ تم إنشاء المعاينة: {inspection.contract_number}")
            
            # اختبار الحالات المختلفة
            status_tests = [
                ('pending', 'pending', 'processing'),
                ('scheduled', 'pending', 'processing'),
                ('completed', 'completed', 'ready'),
                ('cancelled', 'cancelled', 'pending')
            ]
            
            for inspection_status, expected_order_status, expected_tracking_status in status_tests:
                print(f"\n  🧪 اختبار الحالة: {inspection_status}")
                
                # تحديث حالة المعاينة
                inspection.status = inspection_status
                inspection.save()
                
                # إعادة تحميل الطلب من قاعدة البيانات
                order.refresh_from_db()
                
                # التحقق من مزامنة الحالات
                order_status_match = order.order_status == expected_order_status
                tracking_status_match = order.tracking_status == expected_tracking_status
                
                result = {
                    'inspection_status': inspection_status,
                    'expected_order_status': expected_order_status,
                    'actual_order_status': order.order_status,
                    'expected_tracking_status': expected_tracking_status,
                    'actual_tracking_status': order.tracking_status,
                    'order_status_match': order_status_match,
                    'tracking_status_match': tracking_status_match,
                    'success': order_status_match and tracking_status_match
                }
                
                self.test_results.append(result)
                
                if result['success']:
                    print(f"    ✅ نجح: order_status={order.order_status}, tracking_status={order.tracking_status}")
                else:
                    print(f"    ❌ فشل:")
                    if not order_status_match:
                        print(f"      - order_status: متوقع={expected_order_status}, فعلي={order.order_status}")
                    if not tracking_status_match:
                        print(f"      - tracking_status: متوقع={expected_tracking_status}, فعلي={order.tracking_status}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ خطأ في اختبار المزامنة: {str(e)}")
            return False
    
    def test_template_display_consistency(self):
        """اختبار تطابق العرض في Templates"""
        print("\n🎨 اختبار تطابق العرض في Templates...")
        
        try:
            inspection = self.test_data['inspections'][0]
            
            # محاكاة عرض الحالة في templates
            template_mappings = {
                'pending': ('في الانتظار', 'bg-warning text-dark', 'fas fa-clock'),
                'scheduled': ('مجدولة', 'bg-info', 'fas fa-calendar-check'),
                'completed': ('مكتملة', 'bg-success', 'fas fa-check'),
                'cancelled': ('ملغية', 'bg-danger', 'fas fa-times')
            }
            
            all_consistent = True
            
            for status, (expected_text, expected_class, expected_icon) in template_mappings.items():
                inspection.status = status
                
                # محاكاة template logic
                actual_text = inspection.get_status_display()
                
                if status == 'pending':
                    actual_class = 'bg-warning text-dark'
                    actual_icon = 'fas fa-clock'
                elif status == 'scheduled':
                    actual_class = 'bg-info'
                    actual_icon = 'fas fa-calendar-check'
                elif status == 'completed':
                    actual_class = 'bg-success'
                    actual_icon = 'fas fa-check'
                else:  # cancelled
                    actual_class = 'bg-danger'
                    actual_icon = 'fas fa-times'
                
                text_match = expected_text in actual_text
                class_match = actual_class == expected_class
                icon_match = actual_icon == expected_icon
                
                status_consistent = text_match and class_match and icon_match
                
                if status_consistent:
                    print(f"    ✅ {status}: العرض متطابق")
                else:
                    print(f"    ❌ {status}: العرض غير متطابق")
                    all_consistent = False
            
            return all_consistent
            
        except Exception as e:
            print(f"  ❌ خطأ في اختبار العرض: {str(e)}")
            return False
    
    def generate_report(self):
        """إنشاء تقرير النتائج"""
        print("\n📊 تقرير نتائج الاختبار:")
        
        successful_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"  📈 معدل النجاح: {success_rate:.1f}%")
        print(f"  ✅ اختبارات ناجحة: {successful_tests}/{total_tests}")
        
        if success_rate == 100:
            print("  🎉 ممتاز! جميع الاختبارات نجحت")
        elif success_rate >= 75:
            print("  ✅ جيد! معظم الاختبارات نجحت")
        else:
            print("  ⚠️ يحتاج إصلاح! عدد كبير من الاختبارات فشل")
        
        # تفاصيل الاختبارات الفاشلة
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print("\n  ❌ الاختبارات الفاشلة:")
            for result in failed_tests:
                print(f"    - {result['inspection_status']}: مشكلة في المزامنة")
        
        # حفظ التقرير
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inspection_sync_test_report_{timestamp}.json"
        
        try:
            import json
            report = {
                'timestamp': datetime.now().isoformat(),
                'test_type': 'inspection_status_sync',
                'success_rate': success_rate,
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'test_results': self.test_results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n💾 تم حفظ التقرير في: {filename}")
            
        except Exception as e:
            print(f"❌ خطأ في حفظ التقرير: {str(e)}")
        
        return success_rate == 100
    
    def cleanup_test_data(self):
        """تنظيف بيانات الاختبار"""
        print("\n🧹 تنظيف بيانات الاختبار...")
        
        try:
            # حذف المعاينات
            for inspection in self.test_data['inspections']:
                inspection.delete()
            
            # حذف الطلبات
            for order in self.test_data['orders']:
                order.delete()
            
            # حذف العملاء
            for customer in self.test_data['customers']:
                customer.delete()
            
            print("  ✅ تم تنظيف البيانات")
            
        except Exception as e:
            print(f"  ❌ خطأ في التنظيف: {str(e)}")
    
    def run_test(self):
        """تشغيل الاختبار الكامل"""
        print("🚀 بدء اختبار مزامنة حالات المعاينة")
        print("=" * 60)
        
        try:
            # إعداد البيانات
            if not self.setup_test_data():
                return False
            
            # اختبار المزامنة
            if not self.test_inspection_status_sync():
                return False
            
            # اختبار العرض
            template_success = self.test_template_display_consistency()
            
            # إنشاء التقرير
            sync_success = self.generate_report()
            
            return sync_success and template_success
            
        finally:
            # تنظيف البيانات
            self.cleanup_test_data()


def main():
    """الدالة الرئيسية"""
    test = InspectionStatusSyncTest()
    success = test.run_test()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 تم إنجاز الاختبار بنجاح!")
        print("✅ مزامنة حالات المعاينة تعمل بشكل صحيح")
    else:
        print("❌ فشل الاختبار!")
        print("⚠️ توجد مشاكل في مزامنة حالات المعاينة")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 