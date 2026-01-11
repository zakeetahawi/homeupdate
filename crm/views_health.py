import logging

import psutil
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


def health_check(request):
    """
    فحص صحة التطبيق
    يتحقق من:
    1. اتصال قاعدة البيانات (فقط للطلبات المفصلة)
    2. استخدام الذاكرة (فقط للطلبات المفصلة)
    3. استخدام وحدة المعالجة المركزية (فقط للطلبات المفصلة)
    4. مساحة القرص (فقط للطلبات المفصلة)
    """
    # إذا كان المسار هو '/health/' بالضبط، نعيد استجابة بسيطة وسريعة
    if request.path == "/health/" or request.path == "/health":
        # طباعة رسالة تأكيد
        print("تم استدعاء فحص الصحة")
        return HttpResponse("OK", content_type="text/plain")

    # تسجيل طلب فحص الصحة المفصل فقط
    logger.info(
        f"Detailed health check requested from {request.META.get('REMOTE_ADDR')} - Path: {request.path}"
    )

    # التحقق من اتصال قاعدة البيانات (فقط للطلبات المفصلة)
    db_status = "healthy"
    db_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
        logger.error(f"Database connection error: {str(e)}")

    # معلومات النظام (مبسطة وأسرع)
    try:
        # استخدام interval=None لتجنب التأخير
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        # فحص القرص (اختياري)
        disk = None
        try:
            disk = psutil.disk_usage("/")
        except Exception:
            pass  # تجاهل أخطاء فحص القرص
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        memory = None
        disk = None
        cpu = None

    response_data = {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": {
            "status": db_status,
            "error": db_error,
        },
    }

    # إضافة معلومات النظام إذا كانت متاحة (بشكل مبسط)
    if memory and cpu is not None:
        response_data["system"] = {
            "memory_usage_percent": memory.percent,
            "cpu_usage_percent": cpu,
        }
        if disk:
            response_data["system"]["disk_usage_percent"] = disk.percent

    response_data["environment"] = "production" if not settings.DEBUG else "development"

    # دائمًا نعيد 200 OK
    return JsonResponse(response_data, status=200)
