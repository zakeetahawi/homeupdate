#!/usr/bin/env python3
"""
أداة مراقبة العمليات الكبيرة والجسر
Large Operations and Bridge Monitor

هذه الأداة تراقب:
1. حالة الجسر (Cloudflare Tunnel)
2. العمليات الكبيرة (رفع الملفات، المزامنة)
3. استخدام الذاكرة والموارد
4. حالة قاعدة البيانات
"""

import os
import sys
import time
import json
import psutil
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# إضافة مجلد Django للـ Python path
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()

from django.db import connection
from django.core.cache import cache
from celery import Celery

class LargeOperationsMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.celery_app = Celery('crm')
        self.celery_app.config_from_object('django.conf:settings', namespace='CELERY')
        
    def check_bridge_status(self):
        """فحص حالة الجسر (Cloudflare Tunnel)"""
        try:
            # فحص عملية cloudflared
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'cloudflared' in proc.info['name']:
                    return {
                        'status': 'running',
                        'pid': proc.info['pid'],
                        'memory_mb': proc.memory_info().rss / 1024 / 1024,
                        'cpu_percent': proc.cpu_percent(),
                        'uptime_hours': (time.time() - proc.create_time()) / 3600
                    }
            
            return {'status': 'stopped', 'error': 'Process not found'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_connectivity(self):
        """فحص الاتصال بالموقع"""
        try:
            # فحص الاتصال المحلي
            local_response = requests.get('http://localhost:8000', timeout=10)
            local_status = local_response.status_code == 200
            
            # فحص الاتصال عبر الجسر
            bridge_response = requests.get('https://elkhawaga.uk', timeout=30)
            bridge_status = bridge_response.status_code == 200
            bridge_time = bridge_response.elapsed.total_seconds()
            
            return {
                'local': local_status,
                'bridge': bridge_status,
                'bridge_response_time': bridge_time,
                'status': 'ok' if local_status and bridge_status else 'degraded'
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_database_performance(self):
        """فحص أداء قاعدة البيانات"""
        try:
            with connection.cursor() as cursor:
                # فحص عدد الاتصالات النشطة
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                active_connections = cursor.fetchone()[0]
                
                # فحص الاستعلامات البطيئة
                cursor.execute("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE state = 'active' AND now() - query_start > interval '5 minutes';
                """)
                slow_queries = cursor.fetchone()[0]
                
                # فحص حجم قاعدة البيانات
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
                db_size = cursor.fetchone()[0]
                
                return {
                    'active_connections': active_connections,
                    'slow_queries': slow_queries,
                    'database_size': db_size,
                    'status': 'warning' if slow_queries > 0 else 'ok'
                }
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_celery_status(self):
        """فحص حالة Celery"""
        try:
            # فحص Worker
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats()
            active_tasks = inspect.active()
            
            if not stats:
                return {'status': 'no_workers', 'error': 'No Celery workers found'}
            
            total_workers = len(stats)
            total_active_tasks = sum(len(tasks) for tasks in active_tasks.values()) if active_tasks else 0
            
            # فحص المهام المعلقة
            reserved_tasks = inspect.reserved()
            total_reserved = sum(len(tasks) for tasks in reserved_tasks.values()) if reserved_tasks else 0
            
            return {
                'status': 'ok',
                'workers': total_workers,
                'active_tasks': total_active_tasks,
                'reserved_tasks': total_reserved,
                'stats': stats
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_system_resources(self):
        """فحص موارد النظام"""
        try:
            # استخدام الذاكرة
            memory = psutil.virtual_memory()
            
            # استخدام القرص
            disk = psutil.disk_usage('/')
            
            # استخدام المعالج
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # فحص العمليات الكثيفة
            heavy_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                if proc.info['memory_percent'] > 10 or proc.info['cpu_percent'] > 20:
                    heavy_processes.append(proc.info)
            
            return {
                'memory': {
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'percent_used': memory.percent,
                    'status': 'warning' if memory.percent > 80 else 'ok'
                },
                'disk': {
                    'total_gb': disk.total / (1024**3),
                    'free_gb': disk.free / (1024**3),
                    'percent_used': (disk.used / disk.total) * 100,
                    'status': 'warning' if (disk.used / disk.total) > 0.85 else 'ok'
                },
                'cpu': {
                    'percent_used': cpu_percent,
                    'status': 'warning' if cpu_percent > 80 else 'ok'
                },
                'heavy_processes': heavy_processes[:5]  # أكثر 5 عمليات استهلاكاً
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_large_operations(self):
        """فحص العمليات الكبيرة الجارية"""
        try:
            from django.core.cache import cache
            
            # فحص المهام الجارية من Cache
            upload_tasks = cache.get('active_upload_tasks', [])
            sync_tasks = cache.get('active_sync_tasks', [])
            
            # فحص ملفات الرفع المؤقتة
            temp_dir = Path('/home/zakee/homeupdate/temp')
            temp_files = []
            if temp_dir.exists():
                for file_path in temp_dir.glob('*'):
                    if file_path.is_file():
                        stat = file_path.stat()
                        temp_files.append({
                            'name': file_path.name,
                            'size_mb': stat.st_size / (1024**2),
                            'age_minutes': (time.time() - stat.st_mtime) / 60
                        })
            
            return {
                'upload_tasks': len(upload_tasks),
                'sync_tasks': len(sync_tasks),
                'temp_files': len(temp_files),
                'temp_files_details': temp_files[:10],  # أول 10 ملفات
                'status': 'active' if upload_tasks or sync_tasks else 'idle'
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def generate_report(self):
        """إنتاج تقرير شامل"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'uptime_minutes': (datetime.now() - self.start_time).total_seconds() / 60,
            'bridge': self.check_bridge_status(),
            'connectivity': self.check_connectivity(),
            'database': self.check_database_performance(),
            'celery': self.check_celery_status(),
            'system': self.check_system_resources(),
            'large_operations': self.check_large_operations()
        }
        
        # تحديد الحالة العامة
        critical_issues = []
        warnings = []
        
        if report['bridge']['status'] != 'running':
            critical_issues.append('Bridge not running')
        
        if report['connectivity']['status'] != 'ok':
            critical_issues.append('Connectivity issues')
        
        if report['database']['status'] == 'error':
            critical_issues.append('Database error')
        elif report['database']['status'] == 'warning':
            warnings.append('Slow database queries detected')
        
        if report['celery']['status'] != 'ok':
            critical_issues.append('Celery issues')
        
        if report['system']['memory']['status'] == 'warning':
            warnings.append('High memory usage')
        
        if report['system']['disk']['status'] == 'warning':
            warnings.append('Low disk space')
        
        # الحالة العامة
        if critical_issues:
            report['overall_status'] = 'critical'
            report['issues'] = critical_issues
        elif warnings:
            report['overall_status'] = 'warning'
            report['issues'] = warnings
        else:
            report['overall_status'] = 'healthy'
            report['issues'] = []
        
        return report
    
    def save_report(self, report, filename=None):
        """حفظ التقرير"""
        if not filename:
            filename = f"monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_path = Path('/home/zakee/homeupdate/logs') / filename
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path
    
    def print_summary(self, report):
        """طباعة ملخص التقرير"""
        print(f"\n{'='*60}")
        print(f"تقرير مراقبة العمليات الكبيرة - {report['timestamp']}")
        print(f"{'='*60}")
        
        status_colors = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '❌'
        }
        
        print(f"الحالة العامة: {status_colors.get(report['overall_status'], '❓')} {report['overall_status'].upper()}")
        
        if report['issues']:
            print(f"\nالمشاكل المكتشفة:")
            for issue in report['issues']:
                print(f"  • {issue}")
        
        print(f"\n📊 ملخص النظام:")
        print(f"  🌉 الجسر: {report['bridge']['status']}")
        print(f"  🌐 الاتصال: {report['connectivity']['status']}")
        print(f"  🗄️  قاعدة البيانات: {report['database']['status']}")
        print(f"  ⚙️  Celery: {report['celery']['status']}")
        print(f"  💾 الذاكرة: {report['system']['memory']['percent_used']:.1f}%")
        print(f"  💽 القرص: {report['system']['disk']['percent_used']:.1f}%")
        
        if report['large_operations']['status'] == 'active':
            print(f"\n🔄 العمليات الجارية:")
            print(f"  📤 مهام الرفع: {report['large_operations']['upload_tasks']}")
            print(f"  🔄 مهام المزامنة: {report['large_operations']['sync_tasks']}")
        
        print(f"\n{'='*60}")

def main():
    """الدالة الرئيسية"""
    monitor = LargeOperationsMonitor()
    
    # إنتاج التقرير
    print("🔍 فحص النظام...")
    report = monitor.generate_report()
    
    # حفظ التقرير
    report_path = monitor.save_report(report)
    
    # طباعة الملخص
    monitor.print_summary(report)
    
    print(f"\n💾 تم حفظ التقرير الكامل في: {report_path}")
    
    # إرجاع رمز الخروج حسب الحالة
    if report['overall_status'] == 'critical':
        return 2
    elif report['overall_status'] == 'warning':
        return 1
    else:
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  تم إيقاف المراقبة بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ في المراقبة: {e}")
        sys.exit(2)
