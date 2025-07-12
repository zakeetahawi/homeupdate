#!/usr/bin/env python3
"""
Script لاختبار أداء النظام
"""

import time
import requests
import json
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class PerformanceTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.session = requests.Session()
        
        # إعداد headers
        self.session.headers.update({
            'User-Agent': 'PerformanceTester/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ar,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

    def test_page_load(self, url_path, name="صفحة"):
        """اختبار تحميل صفحة"""
        full_url = f"{self.base_url}{url_path}"
        
        try:
            start_time = time.time()
            response = self.session.get(full_url, timeout=30)
            end_time = time.time()
            
            duration = end_time - start_time
            success = response.status_code == 200
            
            result = {
                'name': name,
                'url': full_url,
                'duration': duration,
                'status_code': response.status_code,
                'success': success,
                'size': len(response.content),
                'timestamp': datetime.now().isoformat()
            }
            
            self.results.append(result)
            
            if success:
                print(f"✅ {name}: {duration:.3f}s ({response.status_code})")
            else:
                print(f"❌ {name}: {duration:.3f}s ({response.status_code})")
                
            return result
            
        except Exception as e:
            result = {
                'name': name,
                'url': full_url,
                'duration': 0,
                'status_code': 0,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            self.results.append(result)
            print(f"❌ {name}: خطأ - {e}")
            return result

    def test_concurrent_load(self, url_path, name="صفحة", concurrent_users=10):
        """اختبار التحميل المتزامن"""
        print(f"\n🔄 اختبار التحميل المتزامن: {name} ({concurrent_users} مستخدم)")
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(self.test_page_load, url_path, f"{name} - مستخدم {i+1}")
                for i in range(concurrent_users)
            ]
            
            concurrent_results = []
            for future in as_completed(futures):
                result = future.result()
                concurrent_results.append(result)
        
        return concurrent_results

    def test_api_endpoints(self):
        """اختبار نقاط API"""
        print("\n🔗 اختبار نقاط API")
        
        api_endpoints = [
            ('/api/notifications/', 'قائمة الإشعارات'),
            ('/api/orders/', 'قائمة الطلبات'),
            ('/api/inventory/', 'قائمة المخزون'),
            ('/api/customers/', 'قائمة العملاء'),
        ]
        
        for endpoint, name in api_endpoints:
            self.test_page_load(endpoint, name)

    def test_admin_pages(self):
        """اختبار صفحات Admin"""
        print("\n⚙️ اختبار صفحات Admin")
        
        admin_pages = [
            ('/admin/', 'لوحة التحكم'),
            ('/admin/accounts/', 'إدارة الحسابات'),
            ('/admin/orders/', 'إدارة الطلبات'),
            ('/admin/inventory/', 'إدارة المخزون'),
            ('/admin/customers/', 'إدارة العملاء'),
            ('/admin/manufacturing/', 'إدارة التصنيع'),
            ('/admin/inspections/', 'إدارة الفحص'),
        ]
        
        for page, name in admin_pages:
            self.test_page_load(page, name)

    def test_main_pages(self):
        """اختبار الصفحات الرئيسية"""
        print("\n🏠 اختبار الصفحات الرئيسية")
        
        main_pages = [
            ('/', 'الصفحة الرئيسية'),
            ('/orders/', 'الطلبات'),
            ('/inventory/', 'المخزون'),
            ('/customers/', 'العملاء'),
            ('/manufacturing/', 'التصنيع'),
            ('/inspections/', 'الفحص'),
            ('/reports/', 'التقارير'),
        ]
        
        for page, name in main_pages:
            self.test_page_load(page, name)

    def generate_report(self):
        """إنشاء تقرير الأداء"""
        if not self.results:
            print("لا توجد نتائج لإنشاء تقرير")
            return
        
        successful_results = [r for r in self.results if r['success']]
        failed_results = [r for r in self.results if not r['success']]
        
        if successful_results:
            durations = [r['duration'] for r in successful_results]
            
            report = {
                'summary': {
                    'total_tests': len(self.results),
                    'successful_tests': len(successful_results),
                    'failed_tests': len(failed_results),
                    'success_rate': (len(successful_results) / len(self.results)) * 100,
                    'average_duration': statistics.mean(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'median_duration': statistics.median(durations),
                    'std_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
                },
                'performance_grades': self._calculate_performance_grades(durations),
                'slowest_pages': self._get_slowest_pages(successful_results),
                'fastest_pages': self._get_fastest_pages(successful_results),
                'failed_pages': failed_results,
                'recommendations': self._generate_recommendations(durations, failed_results),
                'timestamp': datetime.now().isoformat()
            }
        else:
            report = {
                'summary': {
                    'total_tests': len(self.results),
                    'successful_tests': 0,
                    'failed_tests': len(failed_results),
                    'success_rate': 0,
                },
                'failed_pages': failed_results,
                'timestamp': datetime.now().isoformat()
            }
        
        return report

    def _calculate_performance_grades(self, durations):
        """حساب درجات الأداء"""
        if not durations:
            return {}
        
        avg_duration = statistics.mean(durations)
        
        grades = {
            'excellent': len([d for d in durations if d < 0.5]),
            'good': len([d for d in durations if 0.5 <= d < 1.0]),
            'fair': len([d for d in durations if 1.0 <= d < 2.0]),
            'poor': len([d for d in durations if d >= 2.0])
        }
        
        return grades

    def _get_slowest_pages(self, results, top=5):
        """الحصول على أبطأ الصفحات"""
        return sorted(results, key=lambda x: x['duration'], reverse=True)[:top]

    def _get_fastest_pages(self, results, top=5):
        """الحصول على أسرع الصفحات"""
        return sorted(results, key=lambda x: x['duration'])[:top]

    def _generate_recommendations(self, durations, failed_results):
        """إنشاء التوصيات"""
        recommendations = []
        
        if failed_results:
            recommendations.append({
                'type': 'error',
                'priority': 'high',
                'message': f'هناك {len(failed_results)} صفحة فشلت في التحميل'
            })
        
        if durations:
            avg_duration = statistics.mean(durations)
            
            if avg_duration > 2.0:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'high',
                    'message': 'متوسط وقت التحميل بطيء جداً (>2s)'
                })
            elif avg_duration > 1.0:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'message': 'متوسط وقت التحميل بطيء (>1s)'
                })
            
            slow_pages = [d for d in durations if d > 2.0]
            if slow_pages:
                recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'message': f'هناك {len(slow_pages)} صفحة بطيئة جداً (>2s)'
                })
        
        return recommendations

    def print_report(self, report):
        """طباعة التقرير"""
        print("\n" + "="*60)
        print("📊 تقرير اختبار الأداء")
        print("="*60)
        
        summary = report['summary']
        print(f"\n📈 ملخص الأداء:")
        print(f"  إجمالي الاختبارات: {summary['total_tests']}")
        print(f"  الاختبارات الناجحة: {summary['successful_tests']}")
        print(f"  الاختبارات الفاشلة: {summary['failed_tests']}")
        print(f"  نسبة النجاح: {summary['success_rate']:.1f}%")
        
        if 'average_duration' in summary:
            print(f"  متوسط وقت التحميل: {summary['average_duration']:.3f}s")
            print(f"  أسرع تحميل: {summary['min_duration']:.3f}s")
            print(f"  أبطأ تحميل: {summary['max_duration']:.3f}s")
            print(f"  متوسط التحميل: {summary['median_duration']:.3f}s")
        
        if 'performance_grades' in report:
            grades = report['performance_grades']
            print(f"\n🏆 درجات الأداء:")
            print(f"  ممتاز (<0.5s): {grades['excellent']}")
            print(f"  جيد (0.5-1s): {grades['good']}")
            print(f"  مقبول (1-2s): {grades['fair']}")
            print(f"  بطيء (>2s): {grades['poor']}")
        
        if 'slowest_pages' in report:
            print(f"\n🐌 أبطأ الصفحات:")
            for page in report['slowest_pages'][:3]:
                print(f"  {page['name']}: {page['duration']:.3f}s")
        
        if 'fastest_pages' in report:
            print(f"\n⚡ أسرع الصفحات:")
            for page in report['fastest_pages'][:3]:
                print(f"  {page['name']}: {page['duration']:.3f}s")
        
        if 'recommendations' in report:
            print(f"\n💡 التوصيات:")
            for rec in report['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
                print(f"  {priority_icon} {rec['message']}")
        
        print("\n" + "="*60)

    def save_report(self, report, filename=None):
        """حفظ التقرير في ملف"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'performance_report_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"💾 تم حفظ التقرير في: {filename}")

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار أداء النظام")
    
    # إنشاء مثيل الاختبار
    tester = PerformanceTester()
    
    try:
        # اختبار الصفحات الرئيسية
        tester.test_main_pages()
        
        # اختبار صفحات Admin
        tester.test_admin_pages()
        
        # اختبار نقاط API
        tester.test_api_endpoints()
        
        # اختبار التحميل المتزامن للصفحة الرئيسية
        tester.test_concurrent_load('/', 'الصفحة الرئيسية', 5)
        
        # إنشاء التقرير
        report = tester.generate_report()
        tester.print_report(report)
        tester.save_report(report)
        
        print("\n✅ تم الانتهاء من اختبار الأداء")
        
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف الاختبار بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ في الاختبار: {e}")

if __name__ == "__main__":
    main() 