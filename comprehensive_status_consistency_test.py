#!/usr/bin/env python
"""
اختبار شامل لتطابق الحالات في جميع أنحاء النظام
يتحقق من تطابق حالات الطلبات في:
- قاعدة البيانات
- واجهات المستخدم (Templates)
- APIs
- خدمات النظام
- واجهة الإدارة
"""

import os
import sys
import json
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.db import transaction
from orders.models import Order
from manufacturing.models import ManufacturingOrder
from crm.services.base_service import StatusSyncService


class ComprehensiveStatusConsistencyTest:
    """اختبار شامل لتطابق الحالات في جميع أنحاء النظام"""
    
    def __init__(self):
        """تهيئة الاختبار"""
        self.test_results = {
            'database_consistency': {'checks': 0, 'errors': []},
            'template_consistency': {'checks': 0, 'errors': []},
            'api_consistency': {'checks': 0, 'errors': []},
            'service_consistency': {'checks': 0, 'errors': []},
            'admin_consistency': {'checks': 0, 'errors': []},
            'cross_system_consistency': {'checks': 0, 'errors': []}
        }
    
    def run_comprehensive_test(self):
        """تشغيل الاختبار الشامل"""
        print("🔍 بدء الاختبار الشامل لتطابق الحالات في جميع أنحاء النظام")
        print("=" * 80)
        
        start_time = datetime.now()
        
        # تشغيل جميع الاختبارات
        test_results = {}
        
        test_results['database_consistency'] = self.test_database_consistency()
        test_results['template_consistency'] = self.test_template_consistency()
        test_results['api_consistency'] = self.test_api_consistency()
        test_results['service_consistency'] = self.test_service_consistency()
        test_results['admin_consistency'] = self.test_admin_consistency()
        test_results['cross_system_consistency'] = self.test_cross_system_consistency()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # حساب النتائج
        successful_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # عرض النتائج
        self.display_results(test_results, duration, success_rate)
        
        # حفظ التقرير
        self.save_report(test_results, duration, success_rate)
        
        return test_results
    
    def test_database_consistency(self):
        """اختبار تطابق الحالات في قاعدة البيانات"""
        print("\n📊 اختبار تطابق الحالات في قاعدة البيانات...")
        
        try:
            errors = []
            checks = 0
            
            # 1. فحص صحة order_status
            print("  🔍 فحص صحة order_status...")
            valid_order_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
            invalid_orders = Order.objects.exclude(order_status__in=valid_order_statuses)
            
            for order in invalid_orders:
                checks += 1
                errors.append({
                    'type': 'invalid_order_status',
                    'order_number': order.order_number,
                    'invalid_status': order.order_status,
                    'valid_statuses': valid_order_statuses
                })
            
            # 2. فحص صحة tracking_status
            print("  🔍 فحص صحة tracking_status...")
            valid_tracking_statuses = [choice[0] for choice in Order.TRACKING_STATUS_CHOICES]
            invalid_tracking_orders = Order.objects.exclude(tracking_status__in=valid_tracking_statuses)
            
            for order in invalid_tracking_orders:
                checks += 1
                errors.append({
                    'type': 'invalid_tracking_status',
                    'order_number': order.order_number,
                    'invalid_status': order.tracking_status,
                    'valid_statuses': valid_tracking_statuses
                })
            
            # 3. فحص تطابق Order مع ManufacturingOrder
            print("  🔍 فحص تطابق Order مع ManufacturingOrder...")
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                checks += 1
                manufacturing_order = order.manufacturing_order
                
                if order.order_status != manufacturing_order.status:
                    errors.append({
                        'type': 'order_manufacturing_mismatch',
                        'order_number': order.order_number,
                        'order_status': order.order_status,
                        'manufacturing_status': manufacturing_order.status
                    })
            
            self.test_results['database_consistency']['checks'] = checks
            self.test_results['database_consistency']['errors'] = errors
            
            if errors:
                print(f"  ❌ تم اكتشاف {len(errors)} خطأ في قاعدة البيانات")
                for error in errors[:5]:  # عرض أول 5 أخطاء
                    self._print_error_details(error)
                if len(errors) > 5:
                    print(f"    ... و {len(errors) - 5} خطأ آخر")
                return False
            else:
                print(f"  ✅ قاعدة البيانات متسقة ({checks} فحص)")
                return True
                
        except Exception as e:
            print(f"  ❌ خطأ في فحص قاعدة البيانات: {str(e)}")
            return False
    
    def test_template_consistency(self):
        """اختبار تطابق الحالات في Templates"""
        print("\n🎨 اختبار تطابق الحالات في واجهات المستخدم...")
        
        try:
            errors = []
            checks = 0
            
            # فحص كل طلب له manufacturing order
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                checks += 1
                
                # محاكاة عرض الحالة في order_list.html
                order_template_display = self._get_order_template_display(order.order_status)
                
                # محاكاة عرض الحالة في manufacturing_list.html
                manufacturing_template_display = self._get_manufacturing_template_display(
                    order.manufacturing_order.status
                )
                
                # يجب أن تكون متطابقة
                if order_template_display != manufacturing_template_display:
                    errors.append({
                        'type': 'template_display_mismatch',
                        'order_number': order.order_number,
                        'order_template_display': order_template_display,
                        'manufacturing_template_display': manufacturing_template_display
                    })
            
            self.test_results['template_consistency']['checks'] = checks
            self.test_results['template_consistency']['errors'] = errors
            
            if errors:
                print(f"  ❌ تم اكتشاف {len(errors)} خطأ في عرض Templates")
                for error in errors[:3]:
                    self._print_error_details(error)
                return False
            else:
                print(f"  ✅ Templates متسقة ({checks} فحص)")
                return True
                
        except Exception as e:
            print(f"  ❌ خطأ في فحص Templates: {str(e)}")
            return False
    
    def test_api_consistency(self):
        """اختبار تطابق الحالات في APIs"""
        print("\n🔗 اختبار تطابق الحالات في APIs...")
        
        try:
            errors = []
            checks = 0
            
            # فحص كل طلب له manufacturing order
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                checks += 1
                
                # محاكاة API response
                api_order_data = {
                    'order_status': order.order_status,
                    'tracking_status': order.tracking_status
                }
                
                api_manufacturing_data = {
                    'status': order.manufacturing_order.status
                }
                
                # يجب أن تكون order_status متطابقة
                if api_order_data['order_status'] != api_manufacturing_data['status']:
                    errors.append({
                        'type': 'api_status_mismatch',
                        'order_number': order.order_number,
                        'api_order_status': api_order_data['order_status'],
                        'api_manufacturing_status': api_manufacturing_data['status']
                    })
            
            self.test_results['api_consistency']['checks'] = checks
            self.test_results['api_consistency']['errors'] = errors
            
            if errors:
                print(f"  ❌ تم اكتشاف {len(errors)} خطأ في APIs")
                for error in errors[:3]:
                    self._print_error_details(error)
                return False
            else:
                print(f"  ✅ APIs متسقة ({checks} فحص)")
                return True
                
        except Exception as e:
            print(f"  ❌ خطأ في فحص APIs: {str(e)}")
            return False
    
    def test_service_consistency(self):
        """اختبار تطابق الحالات في الخدمات"""
        print("\n⚡ اختبار تطابق الحالات في الخدمات...")
        
        try:
            errors = []
            checks = 0
            
            # فحص StatusSyncService
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                checks += 1
                manufacturing_order = order.manufacturing_order
                
                # استخدام StatusSyncService للتحقق
                validation = StatusSyncService.validate_status_consistency(
                    order, manufacturing_order
                )
                
                if not all(validation.values()):
                    errors.append({
                        'type': 'service_validation_failed',
                        'order_number': order.order_number,
                        'validation_details': validation
                    })
            
            self.test_results['service_consistency']['checks'] = checks
            self.test_results['service_consistency']['errors'] = errors
            
            if errors:
                print(f"  ❌ تم اكتشاف {len(errors)} خطأ في الخدمات")
                for error in errors[:3]:
                    self._print_error_details(error)
                return False
            else:
                print(f"  ✅ الخدمات متسقة ({checks} فحص)")
                return True
                
        except Exception as e:
            print(f"  ❌ خطأ في فحص الخدمات: {str(e)}")
            return False
    
    def test_admin_consistency(self):
        """اختبار تطابق الحالات في واجهة الإدارة"""
        print("\n👨‍💼 اختبار تطابق الحالات في واجهة الإدارة...")
        
        try:
            errors = []
            checks = 0
            
            # فحص كل طلب له manufacturing order
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                checks += 1
                
                # محاكاة admin display
                admin_order_display = order.get_order_status_display()
                admin_manufacturing_display = order.manufacturing_order.get_status_display()
                
                # يجب أن تكون متطابقة
                if admin_order_display != admin_manufacturing_display:
                    errors.append({
                        'type': 'admin_display_mismatch',
                        'order_number': order.order_number,
                        'admin_order_display': admin_order_display,
                        'admin_manufacturing_display': admin_manufacturing_display
                    })
            
            self.test_results['admin_consistency']['checks'] = checks
            self.test_results['admin_consistency']['errors'] = errors
            
            if errors:
                print(f"  ❌ تم اكتشاف {len(errors)} خطأ في واجهة الإدارة")
                for error in errors[:3]:
                    self._print_error_details(error)
                return False
            else:
                print(f"  ✅ واجهة الإدارة متسقة ({checks} فحص)")
                return True
                
        except Exception as e:
            print(f"  ❌ خطأ في فحص واجهة الإدارة: {str(e)}")
            return False
    
    def test_cross_system_consistency(self):
        """اختبار التطابق عبر جميع أجزاء النظام"""
        print("\n🌐 اختبار التطابق عبر جميع أجزاء النظام...")
        
        try:
            errors = []
            checks = 0
            
            # فحص شامل لكل طلب
            orders_with_manufacturing = Order.objects.filter(
                manufacturing_order__isnull=False
            ).select_related('manufacturing_order')
            
            for order in orders_with_manufacturing:
                checks += 1
                manufacturing_order = order.manufacturing_order
                
                # جمع جميع التمثيلات المختلفة للحالة
                representations = {
                    'database_order_status': order.order_status,
                    'database_manufacturing_status': manufacturing_order.status,
                    'template_order_display': self._get_order_template_display(order.order_status),
                    'template_manufacturing_display': self._get_manufacturing_template_display(manufacturing_order.status),
                    'admin_order_display': order.get_order_status_display(),
                    'admin_manufacturing_display': manufacturing_order.get_status_display(),
                    'api_order_status': order.order_status,
                    'api_manufacturing_status': manufacturing_order.status
                }
                
                # التحقق من التطابق
                inconsistencies = []
                
                # يجب أن تكون database statuses متطابقة
                if representations['database_order_status'] != representations['database_manufacturing_status']:
                    inconsistencies.append('database_status_mismatch')
                
                # يجب أن تكون template displays متطابقة
                if representations['template_order_display'] != representations['template_manufacturing_display']:
                    inconsistencies.append('template_display_mismatch')
                
                # يجب أن تكون admin displays متطابقة
                if representations['admin_order_display'] != representations['admin_manufacturing_display']:
                    inconsistencies.append('admin_display_mismatch')
                
                # يجب أن تكون API statuses متطابقة
                if representations['api_order_status'] != representations['api_manufacturing_status']:
                    inconsistencies.append('api_status_mismatch')
                
                if inconsistencies:
                    errors.append({
                        'type': 'cross_system_inconsistency',
                        'order_number': order.order_number,
                        'inconsistencies': inconsistencies,
                        'representations': representations
                    })
            
            self.test_results['cross_system_consistency']['checks'] = checks
            self.test_results['cross_system_consistency']['errors'] = errors
            
            if errors:
                print(f"  ❌ تم اكتشاف {len(errors)} خطأ في التطابق عبر النظام")
                for error in errors[:3]:
                    self._print_error_details(error)
                return False
            else:
                print(f"  ✅ النظام متسق عبر جميع الأجزاء ({checks} فحص)")
                return True
                
        except Exception as e:
            print(f"  ❌ خطأ في فحص التطابق عبر النظام: {str(e)}")
            return False
    
    def _get_order_template_display(self, order_status):
        """محاكاة عرض حالة الطلب في Template"""
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
        return self._get_order_template_display(manufacturing_status)
    
    def _print_error_details(self, error):
        """طباعة تفاصيل الخطأ"""
        error_type = error['type']
        order_number = error.get('order_number', 'غير محدد')
        
        if error_type == 'invalid_order_status':
            print(f"    ❌ الطلب {order_number}: حالة طلب غير صحيحة ({error['invalid_status']})")
        
        elif error_type == 'invalid_tracking_status':
            print(f"    ❌ الطلب {order_number}: حالة تتبع غير صحيحة ({error['invalid_status']})")
        
        elif error_type == 'order_manufacturing_mismatch':
            print(f"    ❌ الطلب {order_number}: طلب({error['order_status']}) ≠ تصنيع({error['manufacturing_status']})")
        
        elif error_type == 'template_display_mismatch':
            print(f"    ❌ الطلب {order_number}: عرض مختلف في Templates")
        
        elif error_type == 'api_status_mismatch':
            print(f"    ❌ الطلب {order_number}: عدم تطابق في API")
        
        elif error_type == 'service_validation_failed':
            print(f"    ❌ الطلب {order_number}: فشل في التحقق من الخدمة")
        
        elif error_type == 'admin_display_mismatch':
            print(f"    ❌ الطلب {order_number}: عدم تطابق في واجهة الإدارة")
        
        elif error_type == 'cross_system_inconsistency':
            print(f"    ❌ الطلب {order_number}: عدم تطابق عبر النظام ({len(error['inconsistencies'])} مشكلة)")
    
    def display_results(self, test_results, duration, success_rate):
        """عرض النتائج"""
        print("\n" + "=" * 80)
        print("📊 نتائج الاختبار الشامل لتطابق الحالات:")
        print(f"⏱️  مدة التنفيذ: {duration:.2f} ثانية")
        print(f"📈 معدل النجاح: {success_rate:.1f}%")
        
        # عرض تفاصيل كل اختبار
        test_names = {
            'database_consistency': 'تطابق قاعدة البيانات',
            'template_consistency': 'تطابق Templates',
            'api_consistency': 'تطابق APIs',
            'service_consistency': 'تطابق الخدمات',
            'admin_consistency': 'تطابق واجهة الإدارة',
            'cross_system_consistency': 'التطابق عبر النظام'
        }
        
        for test_key, result in test_results.items():
            test_name = test_names.get(test_key, test_key)
            status = "✅ نجح" if result else "❌ فشل"
            checks = self.test_results[test_key]['checks']
            errors = len(self.test_results[test_key]['errors'])
            print(f"   - {test_name}: {status} ({checks} فحص، {errors} خطأ)")
        
        # تقييم عام
        if success_rate == 100:
            print("\n🎉 ممتاز! النظام متسق تماماً عبر جميع الأجزاء")
        elif success_rate >= 90:
            print("\n✅ جيد جداً! النظام متسق مع بعض التحسينات البسيطة")
        elif success_rate >= 75:
            print("\n⚠️ مقبول! النظام يحتاج إلى بعض الإصلاحات")
        else:
            print("\n❌ يحتاج إصلاح! النظام به مشاكل جوهرية في التطابق")
    
    def save_report(self, test_results, duration, success_rate):
        """حفظ التقرير"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"status_consistency_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'comprehensive_status_consistency',
            'duration_seconds': duration,
            'overall_success_rate': success_rate,
            'test_results': test_results,
            'detailed_results': self.test_results,
            'summary': {
                'total_checks': sum(result['checks'] for result in self.test_results.values()),
                'total_errors': sum(len(result['errors']) for result in self.test_results.values())
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n💾 تم حفظ التقرير المفصل في: {filename}")
            
        except Exception as e:
            print(f"❌ خطأ في حفظ التقرير: {str(e)}")


def main():
    """الدالة الرئيسية"""
    test = ComprehensiveStatusConsistencyTest()
    results = test.run_comprehensive_test()
    
    # إرجاع كود الخروج المناسب
    all_passed = all(results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 