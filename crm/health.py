from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import psutil
import os

def health_check(request):
    """
    فحص صحة التطبيق لـ Railway
    يتحقق من:
    1. اتصال قاعدة البيانات
    2. استخدام الذاكرة
    3. استخدام وحدة المعالجة المركزية
    4. مساحة القرص
    """
    # التحقق من اتصال قاعدة البيانات
    db_status = "healthy"
    db_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    # معلومات النظام
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    response_data = {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": {
            "status": db_status,
            "error": db_error,
            "engine": settings.DATABASES['default']['ENGINE'] if 'ENGINE' in settings.DATABASES['default'] else "dj_database_url (PostgreSQL)",
        },
        "system": {
            "memory_usage_percent": memory.percent,
            "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
            "disk_usage_percent": disk.percent,
        },
        "environment": "production" if not settings.DEBUG else "development",
    }
    
    status_code = 200 if response_data["status"] == "healthy" else 500
    return JsonResponse(response_data, status=status_code)
