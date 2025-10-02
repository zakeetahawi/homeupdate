import os
import signal
import subprocess
import sys
import threading
import time

from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    help = "Run Django development server with Celery Worker and Beat running in background"

    def handle(self, *args, **options):
        # تشغيل Celery Worker في thread منفصل
        def start_celery_worker():
            try:
                self.stdout.write("🔄 Starting Celery Worker in background...")
                worker_process = subprocess.Popen(
                    [
                        "celery",
                        "-A",
                        "crm",
                        "worker",
                        "--loglevel=info",
                        "--logfile=/tmp/celery_worker_dev.log",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return worker_process
            except Exception as e:
                self.stderr.write(f"❌ Failed to start Celery Worker: {e}")
                return None

        # تشغيل Celery Beat في thread منفصل
        def start_celery_beat():
            try:
                self.stdout.write("⏰ Starting Celery Beat in background...")
                beat_process = subprocess.Popen(
                    [
                        "celery",
                        "-A",
                        "crm",
                        "beat",
                        "--loglevel=info",
                        "--logfile=/tmp/celery_beat_dev.log",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return beat_process
            except Exception as e:
                self.stderr.write(f"❌ Failed to start Celery Beat: {e}")
                return None

        # بدء Celery Worker
        worker_process = start_celery_worker()

        # انتظار قليل ثم بدء Celery Beat
        time.sleep(2)
        beat_process = start_celery_beat()

        # دالة لإيقاف Celery عند الخروج
        def cleanup(signum=None, frame=None):
            self.stdout.write("🛑 Stopping Celery services...")
            if worker_process:
                worker_process.terminate()
                worker_process.wait()
            if beat_process:
                beat_process.terminate()
                beat_process.wait()

        # التقاط إشارات الإيقاف
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

        try:
            # تشغيل Django runserver العادي
            super().handle(*args, **options)
        except KeyboardInterrupt:
            cleanup()
        finally:
            cleanup()
