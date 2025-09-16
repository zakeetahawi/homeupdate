#!/usr/bin/env python3
"""
سكريبت مراقبة صحة النظام في الوقت الفعلي
يراقب قاعدة البيانات، Celery، ورفع الملفات
"""

import os
import sys
import time
import json
import django
from datetime import datetime
from pathlib import Path

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import connection
from django.core.cache import cache
from orders.models import Order
from inspections.models import Inspection
import subprocess

class SystemHealthMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.report_file = f"logs/health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    def check_database_health(self):
        """فحص صحة قاعدة البيانات"""
        try:
            with connection.cursor() as cursor:
                # فحص الاتصالات النشطة
                cursor.execute("""
                    SELECT count(*) as active_connections, state 
                    FROM pg_stat_activity 
                    WHERE datname = %s 
                    GROUP BY state
                """, [connection.settings_dict['NAME']])
                
                connections_by_state = dict(cursor.fetchall())
                
                # فحص إجمالي الاتصالات
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s", 
                             [connection.settings_dict['NAME']])
                total_connections = cursor.fetchone()[0]
                
                # فحص max_connections
                cursor.execute("SHOW max_connections")
                max_connections = int(cursor.fetchone()[0])
                
                return {
                    'status': 'healthy' if total_connections < max_connections * 0.8 else 'warning',
                    'total_connections': total_connections,
                    'max_connections': max_connections,
                    'usage_percentage': round((total_connections / max_connections) * 100, 2),
                    'connections_by_state': connections_by_state,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_celery_health(self):
        """فحص صحة Celery"""
        try:
            # فحص العمال النشطين
            result = subprocess.run(['celery', '-A', 'crm', 'inspect', 'active'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                active_tasks = result.stdout.count('uuid')
                
                # فحص العمال المتاحين
                result2 = subprocess.run(['celery', '-A', 'crm', 'inspect', 'stats'], 
                                       capture_output=True, text=True, timeout=10)
                
                workers_online = result2.stdout.count('worker') if result2.returncode == 0 else 0
                
                return {
                    'status': 'healthy' if workers_online > 0 else 'error',
                    'workers_online': workers_online,
                    'active_tasks': active_tasks,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Celery not responding',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_upload_progress(self):
        """فحص تقدم رفع الملفات"""
        try:
            # فحص ملفات العقود المعلقة
            pending_contracts = Order.objects.filter(
                contract_file__isnull=False,
                is_contract_uploaded_to_drive=False
            ).count()
            
            # فحص ملفات المعاينات المعلقة
            pending_inspections = Inspection.objects.filter(
                inspection_file__isnull=False,
                is_uploaded_to_drive=False
            ).count()
            
            # فحص الملفات المرفوعة اليوم
            today = datetime.now().date()
            uploaded_today_contracts = Order.objects.filter(
                is_contract_uploaded_to_drive=True,
                updated_at__date=today
            ).count()
            
            uploaded_today_inspections = Inspection.objects.filter(
                is_uploaded_to_drive=True,
                updated_at__date=today
            ).count()
            
            return {
                'status': 'healthy' if pending_contracts + pending_inspections < 100 else 'warning',
                'pending_contracts': pending_contracts,
                'pending_inspections': pending_inspections,
                'uploaded_today_contracts': uploaded_today_contracts,
                'uploaded_today_inspections': uploaded_today_inspections,
                'total_pending': pending_contracts + pending_inspections,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_disk_space(self):
        """فحص مساحة القرص"""
        try:
            result = subprocess.run(['df', '-h', '/home/zakee/homeupdate'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    used_percentage = int(parts[4].replace('%', ''))
                    
                    return {
                        'status': 'healthy' if used_percentage < 80 else 'warning',
                        'used_percentage': used_percentage,
                        'available': parts[3],
                        'total': parts[1],
                        'timestamp': datetime.now().isoformat()
                    }
            
            return {
                'status': 'error',
                'error': 'Could not check disk space',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_report(self):
        """إنشاء تقرير شامل"""
        report = {
            'monitoring_start': self.start_time.isoformat(),
            'report_time': datetime.now().isoformat(),
            'database': self.check_database_health(),
            'celery': self.check_celery_health(),
            'uploads': self.check_upload_progress(),
            'disk': self.check_disk_space()
        }
        
        # تحديد الحالة العامة
        statuses = [report['database']['status'], report['celery']['status'], 
                   report['uploads']['status'], report['disk']['status']]
        
        if 'error' in statuses:
            report['overall_status'] = 'error'
        elif 'warning' in statuses:
            report['overall_status'] = 'warning'
        else:
            report['overall_status'] = 'healthy'
        
        return report
    
    def save_report(self, report):
        """حفظ التقرير"""
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def print_summary(self, report):
        """طباعة ملخص التقرير"""
        print(f"\n🔍 تقرير صحة النظام - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # الحالة العامة
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        
        print(f"الحالة العامة: {status_emoji.get(report['overall_status'], '❓')} {report['overall_status'].upper()}")
        print()
        
        # قاعدة البيانات
        db = report['database']
        print(f"📊 قاعدة البيانات: {status_emoji.get(db['status'], '❓')}")
        if 'total_connections' in db:
            print(f"   - الاتصالات: {db['total_connections']}/{db['max_connections']} ({db['usage_percentage']}%)")
        print()
        
        # Celery
        celery = report['celery']
        print(f"⚙️ Celery: {status_emoji.get(celery['status'], '❓')}")
        if 'workers_online' in celery:
            print(f"   - العمال النشطين: {celery['workers_online']}")
            print(f"   - المهام النشطة: {celery['active_tasks']}")
        print()
        
        # رفع الملفات
        uploads = report['uploads']
        print(f"📤 رفع الملفات: {status_emoji.get(uploads['status'], '❓')}")
        if 'total_pending' in uploads:
            print(f"   - ملفات معلقة: {uploads['total_pending']}")
            print(f"   - مرفوع اليوم: {uploads['uploaded_today_contracts'] + uploads['uploaded_today_inspections']}")
        print()
        
        # مساحة القرص
        disk = report['disk']
        print(f"💾 مساحة القرص: {status_emoji.get(disk['status'], '❓')}")
        if 'used_percentage' in disk:
            print(f"   - المستخدم: {disk['used_percentage']}%")
            print(f"   - المتاح: {disk['available']}")
        print()
        
        print(f"📄 التقرير محفوظ في: {self.report_file}")

def main():
    """الدالة الرئيسية"""
    monitor = SystemHealthMonitor()
    
    try:
        print("🚀 بدء مراقبة صحة النظام...")
        
        while True:
            report = monitor.generate_report()
            monitor.save_report(report)
            monitor.print_summary(report)
            
            # انتظار 30 ثانية قبل الفحص التالي
            print("\n⏳ انتظار 30 ثانية للفحص التالي... (اضغط Ctrl+C للإيقاف)")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n🛑 تم إيقاف المراقبة بواسطة المستخدم")
    except Exception as e:
        print(f"\n❌ خطأ في المراقبة: {e}")

if __name__ == "__main__":
    main()
