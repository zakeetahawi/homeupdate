#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import atexit
import os
import signal
import subprocess
import sys
import time


def print_colored(message, color="green"):
    """طباعة رسائل ملونة"""
    colors = {
        "green": "\033[0;32m",
        "red": "\033[0;31m",
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "cyan": "\033[0;36m",
        "reset": "\033[0m",
    }
    print(f"{colors.get(color, colors['green'])}✅ {message}{colors['reset']}")


def start_redis():
    """تشغيل Redis/Valkey"""
    try:
        # فحص إذا كان يعمل بالفعل
        result = subprocess.run(
            ["pgrep", "-x", "valkey-server|redis-server"],
            capture_output=True,
            text=True,
            shell=True,
        )
        if result.returncode == 0:
            print_colored("Redis/Valkey يعمل بالفعل", "cyan")
            return True
    except Exception:
        pass

    # محاولة تشغيل Valkey أولاً
    try:
        result = subprocess.run(
            ["which", "valkey-server"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print_colored("تشغيل valkey-server...", "blue")
            subprocess.Popen(["valkey-server", "--daemonize", "yes", "--port", "6379"])
            time.sleep(2)
            return True
    except Exception:
        pass

    # محاولة تشغيل Redis التقليدي
    try:
        result = subprocess.run(
            ["which", "redis-server"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print_colored("تشغيل redis-server...", "blue")
            subprocess.Popen(["redis-server", "--daemonize", "yes", "--port", "6379"])
            time.sleep(2)
            return True
    except Exception:
        pass

    print_colored("تحذير: Redis/Valkey غير متاح", "yellow")
    return False


def start_celery():
    """تشغيل Celery Worker و Beat"""
    try:
        # فحص إذا كان Celery Worker يعمل بالفعل
        worker_pid_file = "/tmp/celery_worker_dev.pid"
        beat_pid_file = "/tmp/celery_beat_dev.pid"

        worker_running = False
        beat_running = False

        # فحص Worker
        if os.path.exists(worker_pid_file):
            try:
                with open(worker_pid_file, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)  # فحص إذا كان العملية تعمل
                worker_running = True
                print_colored("Celery Worker يعمل بالفعل", "cyan")
            except (OSError, ValueError):
                os.remove(worker_pid_file)

        # فحص Beat
        if os.path.exists(beat_pid_file):
            try:
                with open(beat_pid_file, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)  # فحص إذا كان العملية تعمل
                beat_running = True
                print_colored("Celery Beat يعمل بالفعل", "cyan")
            except (OSError, ValueError):
                os.remove(beat_pid_file)

        # تشغيل Worker إذا لم يكن يعمل
        if not worker_running:
            print_colored("تشغيل Celery Worker...", "blue")
            worker_name = f"worker-{os.getpid()}"
            subprocess.Popen(
                [
                    "celery",
                    "-A",
                    "crm",
                    "worker",
                    "--loglevel=info",
                    "--detach",
                    f"--hostname={worker_name}@%h",
                    f"--pidfile={worker_pid_file}",
                    "--logfile=/tmp/celery_worker_dev.log",
                ]
            )

        # تشغيل Beat إذا لم يكن يعمل
        if not beat_running:
            print_colored("تشغيل Celery Beat...", "blue")
            subprocess.Popen(
                [
                    "celery",
                    "-A",
                    "crm",
                    "beat",
                    "--loglevel=info",
                    "--detach",
                    f"--pidfile={beat_pid_file}",
                    "--logfile=/tmp/celery_beat_dev.log",
                    "--schedule=/tmp/celerybeat-schedule-dev",
                ]
            )

        time.sleep(2)
        print_colored("Celery Worker و Beat يعملان", "green")
        return True

    except Exception as e:
        print_colored(f"تحذير: مشكلة في Celery - {str(e)}", "yellow")
        return False


def cleanup_processes():
    """تنظيف العمليات عند الإغلاق"""
    print_colored("إيقاف العمليات...", "yellow")

    # إيقاف Celery
    for pid_file in ["/tmp/celery_worker_dev.pid", "/tmp/celery_beat_dev.pid"]:
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                os.remove(pid_file)
            except Exception:
                pass


# تسجيل دالة التنظيف
atexit.register(cleanup_processes)
signal.signal(signal.SIGINT, lambda s, f: cleanup_processes())
signal.signal(signal.SIGTERM, lambda s, f: cleanup_processes())


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")

    # تشغيل الخدمات عند runserver
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        print_colored("🚀 بدء تشغيل النظام", "cyan")

        # تشغيل Redis
        start_redis()

        # تشغيل Celery
        start_celery()

        print_colored("=" * 50, "cyan")
        print_colored("🎉 النظام جاهز للعمل!", "green")
        print_colored("🌐 الموقع: http://localhost:8000", "blue")
        print_colored("=" * 50, "cyan")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
