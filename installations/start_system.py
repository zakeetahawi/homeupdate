#!/usr/bin/env python
"""
سكريبت تشغيل النظام الكامل للتركيبات
"""
import os
import sys
import subprocess
import threading
import time
import signal
from pathlib import Path


class InstallationSystemManager:
    """مدير النظام الكامل للتركيبات"""
    
    def __init__(self):
        self.processes = {}
        self.running = False
        self.base_dir = Path(__file__).parent.parent
    
    def start_system(self):
        """بدء النظام الكامل"""
        print("🚀 بدء تشغيل نظام التركيبات المتقدم...")
        print("=" * 60)
        
        self.running = True
        
        try:
            # 1. فحص المتطلبات
            if not self.check_requirements():
                return False
            
            # 2. إعداد قاعدة البيانات
            if not self.setup_database():
                return False
            
            # 3. بدء خادم Django
            if not self.start_django_server():
                return False
            
            # 4. بدء مجدول المهام
            if not self.start_scheduler():
                return False
            
            # 5. عرض معلومات النظام
            self.display_system_status()
            
            # 6. انتظار الإيقاف
            self.wait_for_shutdown()
            
            return True
            
        except KeyboardInterrupt:
            print("\n🛑 تم طلب إيقاف النظام...")
            self.stop_system()
            return True
        
        except Exception as e:
            print(f"❌ خطأ في تشغيل النظام: {e}")
            self.stop_system()
            return False
    
    def check_requirements(self):
        """فحص المتطلبات"""
        print("🔍 فحص المتطلبات...")
        
        # فحص Python
        if sys.version_info < (3, 8):
            print("❌ يتطلب Python 3.8 أو أحدث")
            return False
        print("   ✅ Python")
        
        # فحص Django
        try:
            import django
            print(f"   ✅ Django {django.get_version()}")
        except ImportError:
            print("   ❌ Django غير مثبت")
            return False
        
        # فحص المكتبات المطلوبة
        required_packages = ['reportlab', 'openpyxl', 'schedule', 'psutil']
        missing = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ❌ {package}")
                missing.append(package)
        
        if missing:
            print(f"\n⚠️ المكتبات المفقودة: {', '.join(missing)}")
            print("قم بتثبيتها باستخدام:")
            print(f"pip install {' '.join(missing)}")
            return False
        
        # فحص ملفات النظام
        required_files = [
            'installations/models_new.py',
            'installations/views_new.py',
            'installations/urls_new.py',
            'installations/scheduler.py',
        ]
        
        for file_path in required_files:
            if not (self.base_dir / file_path).exists():
                print(f"   ❌ ملف مفقود: {file_path}")
                return False
        
        print("✅ جميع المتطلبات متوفرة")
        return True
    
    def setup_database(self):
        """إعداد قاعدة البيانات"""
        print("\n📦 إعداد قاعدة البيانات...")
        
        try:
            # تطبيق الهجرات
            result = subprocess.run([
                sys.executable, 'manage.py', 'migrate'
            ], cwd=self.base_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ خطأ في تطبيق الهجرات: {result.stderr}")
                return False
            
            print("✅ تم إعداد قاعدة البيانات")
            return True
            
        except Exception as e:
            print(f"❌ خطأ في إعداد قاعدة البيانات: {e}")
            return False
    
    def start_django_server(self):
        """بدء خادم Django"""
        print("\n🌐 بدء خادم Django...")
        
        try:
            # بدء خادم Django في خيط منفصل
            django_process = subprocess.Popen([
                sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'
            ], cwd=self.base_dir)
            
            self.processes['django'] = django_process
            
            # انتظار بدء الخادم
            time.sleep(3)
            
            # فحص حالة الخادم
            if django_process.poll() is None:
                print("✅ خادم Django يعمل على http://localhost:8000")
                return True
            else:
                print("❌ فشل في بدء خادم Django")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في بدء خادم Django: {e}")
            return False
    
    def start_scheduler(self):
        """بدء مجدول المهام"""
        print("\n⏰ بدء مجدول المهام...")
        
        try:
            # بدء المجدول في خيط منفصل
            scheduler_process = subprocess.Popen([
                sys.executable, 'installations/scheduler.py'
            ], cwd=self.base_dir)
            
            self.processes['scheduler'] = scheduler_process
            
            # انتظار بدء المجدول
            time.sleep(2)
            
            # فحص حالة المجدول
            if scheduler_process.poll() is None:
                print("✅ مجدول المهام يعمل")
                return True
            else:
                print("❌ فشل في بدء مجدول المهام")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في بدء مجدول المهام: {e}")
            return False
    
    def display_system_status(self):
        """عرض حالة النظام"""
        print("\n" + "=" * 60)
        print("🎉 نظام التركيبات المتقدم يعمل بنجاح!")
        print("=" * 60)
        
        print("\n🌐 الخدمات النشطة:")
        for service, process in self.processes.items():
            status = "🟢 يعمل" if process.poll() is None else "🔴 متوقف"
            print(f"   - {service}: {status}")
        
        print("\n🔗 الروابط المهمة:")
        print("   - الصفحة الرئيسية: http://localhost:8000/")
        print("   - لوحة التحكم: http://localhost:8000/installations/")
        print("   - لوحة الإدارة: http://localhost:8000/admin/")
        
        print("\n👥 حسابات الدخول:")
        print("   - المدير: admin / admin123")
        print("   - فني 1: technician1 / tech123")
        
        print("\n📊 الميزات المتاحة:")
        print("   ✅ إدارة التركيبات الشاملة")
        print("   ✅ التقويم الذكي والجدولة")
        print("   ✅ نظام الإنذارات المتقدم")
        print("   ✅ تحليل أداء الفنيين")
        print("   ✅ واجهة المصنع")
        print("   ✅ التصدير والطباعة")
        print("   ✅ التقارير والتحليلات")
        
        print("\n⚠️ ملاحظات:")
        print("   - يرجى تغيير كلمات المرور الافتراضية")
        print("   - راجع QUICK_START.md للمزيد من التفاصيل")
        
        print("\n⏹️ اضغط Ctrl+C لإيقاف النظام")
    
    def wait_for_shutdown(self):
        """انتظار إيقاف النظام"""
        try:
            while self.running:
                # فحص حالة العمليات
                for service, process in list(self.processes.items()):
                    if process.poll() is not None:
                        print(f"⚠️ الخدمة {service} توقفت")
                        del self.processes[service]
                
                # إذا توقفت جميع العمليات، أوقف النظام
                if not self.processes:
                    print("⚠️ جميع الخدمات توقفت")
                    break
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            pass
    
    def stop_system(self):
        """إيقاف النظام"""
        print("\n🛑 إيقاف النظام...")
        
        self.running = False
        
        # إيقاف جميع العمليات
        for service, process in self.processes.items():
            print(f"   ⏹️ إيقاف {service}...")
            try:
                process.terminate()
                process.wait(timeout=10)
                print(f"   ✅ تم إيقاف {service}")
            except subprocess.TimeoutExpired:
                print(f"   ⚠️ إجبار إيقاف {service}...")
                process.kill()
                process.wait()
            except Exception as e:
                print(f"   ❌ خطأ في إيقاف {service}: {e}")
        
        self.processes.clear()
        print("✅ تم إيقاف النظام بنجاح")
    
    def restart_service(self, service_name):
        """إعادة تشغيل خدمة محددة"""
        if service_name in self.processes:
            print(f"🔄 إعادة تشغيل {service_name}...")
            
            # إيقاف الخدمة
            process = self.processes[service_name]
            process.terminate()
            process.wait(timeout=10)
            del self.processes[service_name]
            
            # إعادة تشغيل الخدمة
            if service_name == 'django':
                self.start_django_server()
            elif service_name == 'scheduler':
                self.start_scheduler()
            
            print(f"✅ تم إعادة تشغيل {service_name}")
    
    def get_system_status(self):
        """الحصول على حالة النظام"""
        status = {
            'running': self.running,
            'services': {}
        }
        
        for service, process in self.processes.items():
            status['services'][service] = {
                'running': process.poll() is None,
                'pid': process.pid
            }
        
        return status


def main():
    """الدالة الرئيسية"""
    
    # التحقق من المعاملات
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'status':
            # عرض حالة النظام
            manager = InstallationSystemManager()
            status = manager.get_system_status()
            print(f"حالة النظام: {'يعمل' if status['running'] else 'متوقف'}")
            for service, info in status['services'].items():
                print(f"  {service}: {'يعمل' if info['running'] else 'متوقف'} (PID: {info.get('pid', 'N/A')})")
            return
        
        elif command == 'stop':
            # إيقاف النظام
            print("🛑 إيقاف النظام...")
            # يمكن إضافة منطق إيقاف العمليات الجارية هنا
            return
        
        elif command == 'help':
            # عرض المساعدة
            print("استخدام:")
            print("  python start_system.py        - تشغيل النظام")
            print("  python start_system.py status - عرض حالة النظام")
            print("  python start_system.py stop   - إيقاف النظام")
            print("  python start_system.py help   - عرض هذه المساعدة")
            return
    
    # تشغيل النظام
    manager = InstallationSystemManager()
    
    # إعداد معالج الإشارات
    def signal_handler(signum, frame):
        manager.stop_system()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # بدء النظام
    success = manager.start_system()
    
    if success:
        print("\n🎉 تم إيقاف النظام بنجاح")
        sys.exit(0)
    else:
        print("\n💥 فشل في تشغيل النظام")
        sys.exit(1)


if __name__ == '__main__':
    main()
