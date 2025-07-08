"""
Gunicorn configuration file for production environment
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
log_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    'logs'
)
accesslog = os.path.join(log_dir, 'gunicorn-access.log')
errorlog = os.path.join(log_dir, 'gunicorn-error.log')
loglevel = 'info'

# Process naming
proc_name = 'homeupdate'

# SSL Configuration (uncomment and modify if using SSL)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Server mechanics
daemon = False
pidfile = 'gunicorn.pid'
user = None
group = None
umask = 0
tmp_upload_dir = None

# Django WSGI application path
wsgi_app = 'crm.wsgi:application'

# Server hooks
def on_starting(server):
    """
    Server startup hook
    """
    pass

def on_reload(server):
    """
    Server reload hook
    """
    pass

def on_exit(server):
    """
    Server exit hook
    """
    pass 