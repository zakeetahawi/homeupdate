# -*- coding: utf-8 -*-
"""
إعدادات Gunicorn لنظام الخواجة التجاري
Gunicorn configuration for Elkhawaga Trading System
"""

import os
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes - محسن بقوة لتجنب مشكلة "too many clients"
workers = 2  # تقليل إلى 2 عمال فقط (بدلاً من 4)
worker_class = "sync"
worker_connections = 25  # تقليل كبير من 100 إلى 25
timeout = 30
keepalive = 2  # تقليل keepalive

# Restart workers after this many requests, with up to this much jitter
max_requests = 100  # تقليل كبير من 500 إلى 100 لإعادة تشغيل أسرع
max_requests_jitter = 20  # تقليل التباين

# Restart workers after this much time has passed
max_worker_age = 600  # 10 دقائق (مخفض بقوة من 30 دقيقة)

# Preload application code before forking worker processes
preload_app = True

# Server mechanics
user = None
group = None
tmp_upload_dir = None
daemon = False
raw_env = []
pidfile = "/tmp/gunicorn.pid"
worker_tmp_dir = "/dev/shm"

# Logging
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
loglevel = "info"
access_log_format = ('%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
                     '"%(f)s" "%(a)s" %(D)s')

# Process naming
proc_name = "elkhawaga_crm"

# Server hooks


def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 Starting Elkhawaga Trading System...")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("🔄 Reloading Elkhawaga Trading System...")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("✅ Elkhawaga Trading System is ready to serve requests")


def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("⚠️  Worker received INT or QUIT signal")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"👷 Worker {worker.pid} is being forked")


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"✨ Worker {worker.pid} has been forked successfully")


def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"💥 Worker {worker.pid} received SIGABRT signal")


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("🔄 Re-executing master process")


# SSL Configuration (if needed)
# keyfile = None
# certfile = None
# ssl_version = ssl.PROTOCOL_TLS
# cert_reqs = ssl.CERT_NONE
# ca_certs = None
# suppress_ragged_eofs = True

# Environment variables
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# Memory optimization
# Enable copy-on-write memory optimization
if hasattr(os, 'fork'):
    def post_fork_memory(server, worker):
        # تحسين استخدام الذاكرة
        import gc
        gc.collect() 