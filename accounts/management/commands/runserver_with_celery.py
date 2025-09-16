import os
import signal
import subprocess
import sys
from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line


class Command(BaseCommand):
    help = 'Run Django development server with Celery Worker and Beat'

    def add_arguments(self, parser):
        # إضافة نفس الوسائط مثل runserver
        parser.add_argument(
            'addrport',
            nargs='?',
            default='127.0.0.1:8000',
            help='Optional port number, or ipaddr:port'
        )
        parser.add_argument(
            '--noreload',
            action='store_false',
            dest='use_reloader',
            help='Tells Django to NOT use the auto-reloader.',
        )
        parser.add_argument(
            '--nothreading',
            action='store_false',
            dest='use_threading',
            default=True,
            help='Tells Django to NOT use threading.',
        )

    def handle(self, *args, **options):
        # تشغيل Celery Worker في الخلفية
        self.stdout.write('🔄 Starting Celery Worker...')
        worker_process = subprocess.Popen([
            'celery', '-A', 'crm', 'worker',
            '--loglevel=info',
            '--logfile=/tmp/celery_worker_dev.log'
        ])

        # تشغيل Celery Beat في الخلفية
        self.stdout.write('⏰ Starting Celery Beat...')
        beat_process = subprocess.Popen([
            'celery', '-A', 'crm', 'beat',
            '--loglevel=info',
            '--logfile=/tmp/celery_beat_dev.log'
        ])

        def cleanup(signum, frame):
            self.stdout.write('🛑 Stopping Celery services...')
            worker_process.terminate()
            beat_process.terminate()
            worker_process.wait()
            beat_process.wait()
            sys.exit(0)

        # التقاط إشارة SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

        try:
            # تشغيل Django runserver
            self.stdout.write('🚀 Starting Django development server...')
            execute_from_command_line(['manage.py', 'runserver'] + sys.argv[2:])
        except KeyboardInterrupt:
            cleanup(None, None)
