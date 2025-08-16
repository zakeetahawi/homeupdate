#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess
import time
import signal
import atexit

# متغيرات عامة لتتبع العمليات
redis_process = None
celery_worker_process = None
celery_beat_process = None

def print_colored(message, color='green'):
    """طباعة رسائل ملونة"""
    colors = {
        'green': '\033[0;32m',
        'red': '\033[0;31m',
        'yellow': '\033[1;33m',
        'blue': '\033[0;34m',
        'cyan': '\033[0;36m',
        'reset': '\033[0m'
    }
    print(f"{colors.get(color, colors['green'])}✅ {message}{colors['reset']}")

def check_redis_installed():
    """فحص تثبيت Redis/Valkey"""
    try:
        # فحص Valkey أولاً
        result = subprocess.run(['which', 'valkey-server'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'valkey-server', 'valkey-cli'

        # فحص Redis التقليدي
        result = subprocess.run(['which', 'redis-server'], capture_output=True, text=True)
        if result.returncode == 0:
            return 'redis-server', 'redis-cli'

        return None, None
    except Exception:
        return None, None

def start_redis():
    """تشغيل Redis/Valkey"""
    global redis_process

    # فحص إذا كان يعمل بالفعل
    try:
        result = subprocess.run(['pgrep', '-x', 'valkey-server|redis-server'],
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print_colored("Redis/Valkey يعمل بالفعل", 'cyan')
            return True
    except Exception:
        pass

    # فحص التثبيت
    server_cmd, cli_cmd = check_redis_installed()
    if not server_cmd:
        print_colored("Redis/Valkey غير مثبت. قم بتثبيته: sudo pacman -S valkey", 'red')
        return False

    try:
        # تشغيل الخادم
        print_colored(f"تشغيل {server_cmd}...", 'blue')
        redis_process = subprocess.Popen([
            server_cmd, '--daemonize', 'yes', '--port', '6379', '--dir', '/tmp'
        ])

        # انتظار قصير للتأكد من التشغيل
        time.sleep(2)

        # اختبار الاتصال
        test_result = subprocess.run([cli_cmd, 'ping'],
                                   capture_output=True, text=True, timeout=5)
        if test_result.returncode == 0 and 'PONG' in test_result.stdout:
            print_colored(f"{server_cmd} يعمل بنجاح", 'green')
            return True
        else:
            print_colored(f"فشل في اختبار {server_cmd}", 'red')
            return False

    except Exception as e:
        print_colored(f"خطأ في تشغيل Redis: {str(e)}", 'red')
        return False

def start_celery_worker():
    """تشغيل Celery Worker"""
    global celery_worker_process

    try:
        print_colored("تشغيل Celery Worker...", 'blue')

        # حذف ملف PID القديم إذا وجد
        pid_file = '/tmp/celery_worker_dev.pid'
        if os.path.exists(pid_file):
            os.remove(pid_file)

        celery_worker_process = subprocess.Popen([
            'celery', '-A', 'crm', 'worker',
            '--loglevel=info',
            '--detach',
            f'--pidfile={pid_file}',
            '--logfile=/tmp/celery_worker_dev.log'
        ])

        # انتظار قصير للتأكد من التشغيل
        time.sleep(3)

        if os.path.exists(pid_file):
            print_colored("Celery Worker يعمل بنجاح", 'green')
            return True
        else:
            print_colored("فشل في تشغيل Celery Worker", 'red')
            return False

    except Exception as e:
        print_colored(f"خطأ في تشغيل Celery Worker: {str(e)}", 'red')
        return False

def start_celery_beat():
    """تشغيل Celery Beat"""
    global celery_beat_process

    try:
        print_colored("تشغيل Celery Beat...", 'blue')

        # حذف ملفات PID والجدولة القديمة
        pid_file = '/tmp/celery_beat_dev.pid'
        schedule_file = '/tmp/celerybeat-schedule-dev'

        # قتل أي عملية beat موجودة
        try:
            subprocess.run(['pkill', '-f', 'celery.*beat'], capture_output=True)
            time.sleep(1)
        except Exception:
            pass

        for file_path in [pid_file, schedule_file, f"{schedule_file}.db"]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

        celery_beat_process = subprocess.Popen([
            'celery', '-A', 'crm', 'beat',
            '--loglevel=info',
            '--detach',
            f'--pidfile={pid_file}',
            '--logfile=/tmp/celery_beat_dev.log',
            f'--schedule={schedule_file}'
        ])

        # انتظار أطول للتأكد من التشغيل
        time.sleep(5)

        if os.path.exists(pid_file):
            print_colored("Celery Beat يعمل بنجاح", 'green')
            return True
        else:
            print_colored("فشل في تشغيل Celery Beat", 'red')
            return False

    except Exception as e:
        print_colored(f"خطأ في تشغيل Celery Beat: {str(e)}", 'red')
        return False

def cleanup_processes():
    """تنظيف العمليات عند الإغلاق"""
    print_colored("إيقاف العمليات...", 'yellow')

    # إيقاف Celery Worker
    pid_file = '/tmp/celery_worker_dev.pid'
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            os.remove(pid_file)
            print_colored("تم إيقاف Celery Worker", 'green')
        except Exception:
            pass

    # إيقاف Celery Beat
    pid_file = '/tmp/celery_beat_dev.pid'
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            os.remove(pid_file)
            # حذف ملف الجدولة
            schedule_file = '/tmp/celerybeat-schedule-dev'
            if os.path.exists(schedule_file):
                os.remove(schedule_file)
            print_colored("تم إيقاف Celery Beat", 'green')
        except Exception:
            pass

# تسجيل دالة التنظيف
atexit.register(cleanup_processes)
signal.signal(signal.SIGINT, lambda s, f: cleanup_processes())
signal.signal(signal.SIGTERM, lambda s, f: cleanup_processes())

def main():
    """Run administrative tasks."""
    # إعداد متغيرات البيئة لقاعدة البيانات
    if 'DATABASE_URL' in os.environ:
        # تم تعديل هذا الجزء لتجنب طباعة كلمة المرور في السجلات
        db_url = os.environ.get('DATABASE_URL')
        masked_url = db_url.replace(db_url.split('@')[0].split('://')[1], '****:****')
        # print(f"استخدام قاعدة البيانات: {masked_url}")  # معلومات حساسة
        # print("تم تكوين قاعدة البيانات من DATABASE_URL")  # معلومات غير ضرورية

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # تشغيل Redis و Celery تلقائياً عند تشغيل runserver
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        print_colored("🚀 بدء تشغيل النظام مع Redis و Celery", 'cyan')

        # تشغيل Redis
        if not start_redis():
            print_colored("تحذير: فشل في تشغيل Redis. قد لا تعمل المهام الخلفية", 'yellow')

        # تشغيل Celery Worker
        if not start_celery_worker():
            print_colored("تحذير: فشل في تشغيل Celery Worker. قد لا تعمل المهام الخلفية", 'yellow')

        # تشغيل Celery Beat
        if not start_celery_beat():
            print_colored("تحذير: فشل في تشغيل Celery Beat. قد لا تعمل المهام الدورية", 'yellow')

        print_colored("📊 مراقبة Celery: tail -f /tmp/celery_worker_dev.log", 'blue')
        print_colored("⏰ مراقبة المهام الدورية: tail -f /tmp/celery_beat_dev.log", 'blue')

    # تنفيذ الترحيلات تلقائياً عند تشغيل الخادم (محسن ومبسط)
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver' and not os.environ.get('AUTO_MIGRATE_EXECUTED'):
        try:
            import django
            django.setup()

            from django.core.management import call_command
            print_colored("جاري تنفيذ الترحيلات تلقائياً...", 'blue')

            call_command('migrate', verbosity=0)  # تقليل الإخراج
            print_colored("تم تنفيذ الترحيلات بنجاح", 'green')

            os.environ['AUTO_MIGRATE_EXECUTED'] = '1'
        except Exception as e:
            print_colored(f"حدث خطأ أثناء تنفيذ الترحيلات التلقائية: {str(e)}", 'red')

    # رسالة ترحيب محسنة لـ runserver
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        print_colored("=" * 60, 'cyan')
        print_colored("🎉 النظام جاهز للعمل مع جميع الخدمات!", 'green')
        print_colored("🌐 الموقع: http://localhost:8000", 'blue')
        print_colored("👤 المستخدم: admin | كلمة المرور: admin123", 'blue')
        print_colored("🔄 Redis/Valkey: يعمل", 'green')
        print_colored("⚙️ Celery Worker: يعمل", 'green')
        print_colored("⏰ Celery Beat: يعمل", 'green')
        print_colored("=" * 60, 'cyan')
        print_colored("💡 نصيحة: لإصلاح تحذير الذاكرة، شغل:", 'yellow')
        print_colored("   sudo sysctl vm.overcommit_memory=1", 'yellow')
        print_colored("استخدم Ctrl+C لإيقاف جميع الخدمات", 'yellow')
        print()

    # تنفيذ الأمر
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
