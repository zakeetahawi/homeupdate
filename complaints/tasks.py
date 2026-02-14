"""
مهام Celery لنظام الشكاوى
"""

import gc
import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db import connection, connections
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True, max_retries=3, default_retry_delay=120, autoretry_for=(Exception,)
)
def cleanup_database_connections(self):
    """
    تنظيف اتصالات قاعدة البيانات الخاملة
    """
    try:
        cleaned_connections = 0

        # إغلاق جميع الاتصالات الخاملة
        for alias in connections:
            conn = connections[alias]
            if conn.connection is not None:
                if hasattr(conn.connection, "get_transaction_status"):
                    # PostgreSQL specific
                    import psycopg2.extensions

                    if (
                        conn.connection.get_transaction_status()
                        == psycopg2.extensions.TRANSACTION_STATUS_IDLE
                    ):
                        conn.close()
                        cleaned_connections += 1
                else:
                    # عام لجميع قواعد البيانات
                    conn.close()
                    cleaned_connections += 1

        # تنظيف الذاكرة
        gc.collect()

        logger.info(f"تم تنظيف {cleaned_connections} اتصال خامل")

        return {
            "success": True,
            "cleaned_connections": cleaned_connections,
            "message": f"تم تنظيف {cleaned_connections} اتصال خامل",
        }

    except Exception as e:
        logger.error(f"خطأ في تنظيف الاتصالات: {str(e)}")
        return {"success": False, "error": str(e), "message": "فشل في تنظيف الاتصالات"}


@shared_task(
    bind=True, max_retries=2, default_retry_delay=60, autoretry_for=(Exception,)
)
def cleanup_expired_cache(self):
    """
    تنظيف التخزين المؤقت المنتهي الصلاحية
    """
    try:
        # تنظيف cache الافتراضي
        cache.clear()

        logger.info("تم تنظيف التخزين المؤقت")

        return {"success": True, "message": "تم تنظيف التخزين المؤقت بنجاح"}

    except Exception as e:
        logger.error(f"خطأ في تنظيف التخزين المؤقت: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "فشل في تنظيف التخزين المؤقت",
        }


@shared_task(
    bind=True, max_retries=3, default_retry_delay=120, autoretry_for=(Exception,)
)
def monitor_database_connections(self):
    """
    مراقبة اتصالات قاعدة البيانات
    """
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            # فحص عدد الاتصالات النشطة
            cursor.execute(
                """
                SELECT count(*) as total_connections,
                       count(*) FILTER (WHERE state = 'active') as active_connections,
                       count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """
            )

            result = cursor.fetchone()
            total_connections = result[0]
            active_connections = result[1]
            idle_connections = result[2]

            logger.info(
                f"اتصالات قاعدة البيانات - المجموع: {total_connections}, النشطة: {active_connections}, الخاملة: {idle_connections}"
            )

            # تحذير إذا كان عدد الاتصالات مرتفع
            if total_connections > 50:
                logger.warning(f"عدد الاتصالات مرتفع: {total_connections}")

                # تنظيف الاتصالات الخاملة إذا كان العدد مرتفع
                if idle_connections > 20:
                    cleanup_database_connections.delay()

            return {
                "success": True,
                "total_connections": total_connections,
                "active_connections": active_connections,
                "idle_connections": idle_connections,
                "message": f"المجموع: {total_connections}, النشطة: {active_connections}, الخاملة: {idle_connections}",
            }

    except Exception as e:
        logger.error(f"خطأ في مراقبة الاتصالات: {str(e)}")
        return {"success": False, "error": str(e), "message": "فشل في مراقبة الاتصالات"}


@shared_task(
    bind=True, max_retries=2, default_retry_delay=300, autoretry_for=(Exception,)
)
def restart_celery_workers_if_needed(self):
    """
    إعادة تشغيل عمال Celery إذا لزم الأمر
    """
    try:
        from celery import current_app

        # فحص حالة العمال
        inspect = current_app.control.inspect()
        stats = inspect.stats()

        if not stats:
            logger.warning("لا يوجد عمال Celery نشطين")
            return {"success": False, "message": "لا يوجد عمال Celery نشطين"}

        # فحص استهلاك الذاكرة
        high_memory_workers = []
        for worker, worker_stats in stats.items():
            memory_usage = worker_stats.get("rusage", {}).get("maxrss", 0)
            # إذا كان استهلاك الذاكرة أكثر من 150MB
            if memory_usage > 150000:
                high_memory_workers.append(worker)

        if high_memory_workers:
            logger.info(
                f"إعادة تشغيل العمال ذوي الاستهلاك العالي للذاكرة: {high_memory_workers}"
            )
            # إرسال أمر إعادة التشغيل
            current_app.control.broadcast("pool_restart", arguments={"reload": True})

            return {
                "success": True,
                "restarted_workers": high_memory_workers,
                "message": f"تم إعادة تشغيل {len(high_memory_workers)} عامل",
            }

        return {"success": True, "message": "جميع العمال يعملون بشكل طبيعي"}

    except Exception as e:
        logger.error(f"خطأ في فحص العمال: {str(e)}")
        return {"success": False, "error": str(e), "message": "فشل في فحص العمال"}


@shared_task(
    bind=True, max_retries=2, default_retry_delay=300, autoretry_for=(Exception,)
)
def system_health_check(self):
    """
    فحص صحة النظام الشامل
    """
    try:
        results = {}

        # فحص قاعدة البيانات
        db_result = monitor_database_connections()
        results["database"] = db_result

        # فحص Redis
        try:
            import redis

            r = redis.Redis(host="localhost", port=6379, db=0)
            r.ping()
            results["redis"] = {"success": True, "message": "Redis يعمل بشكل طبيعي"}
        except Exception as e:
            results["redis"] = {"success": False, "error": str(e)}

        # فحص Celery
        celery_result = restart_celery_workers_if_needed()
        results["celery"] = celery_result

        # تنظيف إذا لزم الأمر
        if results["database"].get("idle_connections", 0) > 10:
            cleanup_result = cleanup_database_connections()
            results["cleanup"] = cleanup_result

        logger.info("تم إجراء فحص صحة النظام")

        return {
            "success": True,
            "results": results,
            "message": "تم إجراء فحص صحة النظام بنجاح",
        }

    except Exception as e:
        logger.error(f"خطأ في فحص صحة النظام: {str(e)}")
        return {"success": False, "error": str(e), "message": "فشل في فحص صحة النظام"}


@shared_task(
    bind=True, max_retries=2, default_retry_delay=120, autoretry_for=(Exception,)
)
def check_complaint_deadlines_task(self):
    """
    مهمة Celery لفحص المواعيد النهائية للشكاوى وإرسال إشعارات
    يتم تشغيلها كل ساعة عبر Celery Beat
    """
    try:
        from django.db.models import Q
        from django.utils import timezone

        from complaints.models import Complaint
        from complaints.services.notification_service import ComplaintNotificationService

        notification_svc = ComplaintNotificationService()
        results = {"approaching_deadline": 0, "overdue": 0, "escalated": 0}

        # 1. الشكاوى التي يقترب موعدها النهائي (خلال 24 ساعة)
        deadline_approaching = Complaint.objects.filter(
            Q(status__in=["new", "in_progress"])
            & Q(deadline__lte=timezone.now() + timedelta(hours=24))
            & Q(deadline__gt=timezone.now())
        ).select_related("assigned_to", "customer", "complaint_type")

        for complaint in deadline_approaching:
            notification_svc.notify_deadline_approaching(complaint)
            results["approaching_deadline"] += 1

        # 2. الشكاوى المتأخرة - تحديث حالتها
        overdue_complaints = Complaint.objects.filter(
            status__in=["new", "in_progress"],
            deadline__lt=timezone.now(),
        ).select_related("assigned_to", "customer", "complaint_type", "assigned_department")

        for complaint in overdue_complaints:
            if complaint.status != "overdue":
                complaint.status = "overdue"
                complaint.save(update_fields=["status", "updated_at"])
                results["overdue"] += 1

            # إرسال تنبيهات للمستخدمين المعنيين
            notification_svc.notify_overdue(complaint)
            notification_svc.notify_overdue_to_escalation_users(complaint)

        # 3. تنظيف الإشعارات القديمة (أكثر من 30 يوم)
        notification_svc.cleanup_old_notifications(days=30)

        logger.info(
            f"فحص المواعيد النهائية: {results['approaching_deadline']} اقتراب موعد، "
            f"{results['overdue']} متأخرة"
        )

        return {
            "success": True,
            "results": results,
            "message": f"تم فحص المواعيد النهائية بنجاح",
        }

    except Exception as e:
        logger.error(f"خطأ في فحص المواعيد النهائية: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task(bind=True, max_retries=1, autoretry_for=(Exception,))
def daily_complaints_report_task(self):
    """
    مهمة يومية لإرسال تقرير الشكاوى المتأخرة
    """
    try:
        from complaints.services.notification_service import ComplaintNotificationService

        notification_svc = ComplaintNotificationService()
        notification_svc.notify_overdue_complaints_daily()

        logger.info("تم إرسال تقرير الشكاوى اليومي")
        return {"success": True, "message": "تم إرسال التقرير اليومي"}

    except Exception as e:
        logger.error(f"خطأ في التقرير اليومي: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task(
    bind=True, max_retries=2, default_retry_delay=300, autoretry_for=(Exception,)
)
def auto_create_delay_complaints(self):
    """
    إنشاء شكاوى تلقائية للطلبات المتأخرة عن تاريخ التسليم المتوقع
    والتركيبات المتأخرة عن مواعيدها المجدولة

    يتم تشغيلها يومياً عبر Celery Beat
    """
    try:
        from django.contrib.contenttypes.models import ContentType

        from complaints.models import Complaint, ComplaintType
        from installations.models import InstallationSchedule
        from orders.models import Order

        results = {"order_complaints": 0, "installation_complaints": 0, "skipped": 0}
        today = timezone.now().date()

        # ---- 1. طلبات متأخرة عن تاريخ التسليم ----
        # طلبات لها تاريخ تسليم متوقع مضى عليه أكثر من 3 أيام ولم تُسلَّم
        delayed_orders = Order.objects.filter(
            expected_delivery_date__lt=today - timedelta(days=3),
            order_status__in=["pending", "in_progress", "ready_install"],
        ).select_related("customer", "branch", "salesperson")

        # الحصول على نوع الشكوى الخاص بالتأخير أو إنشاؤه
        delay_type, _ = ComplaintType.objects.get_or_create(
            name="تأخير تسليم",
            defaults={
                "description": "شكوى تلقائية بسبب تأخر تسليم الطلب عن الموعد المتوقع",
                "default_priority": "high",
                "default_deadline_hours": 48,
            },
        )
        install_delay_type, _ = ComplaintType.objects.get_or_create(
            name="تأخير تركيب",
            defaults={
                "description": "شكوى تلقائية بسبب تأخر التركيب عن الموعد المجدول",
                "default_priority": "high",
                "default_deadline_hours": 48,
            },
        )

        order_ct = ContentType.objects.get_for_model(Order)

        for order in delayed_orders:
            # تجاهل إذا توجد شكوى مفتوحة لنفس الطلب من نوع التأخير
            existing = Complaint.objects.filter(
                related_order=order,
                complaint_type=delay_type,
                status__in=["new", "in_progress", "escalated", "overdue"],
            ).exists()
            if existing:
                results["skipped"] += 1
                continue

            days_late = (today - order.expected_delivery_date).days
            Complaint.objects.create(
                customer=order.customer,
                complaint_type=delay_type,
                title=f"تأخير تسليم الطلب {order.order_number}",
                description=(
                    f"تم إنشاء هذه الشكوى تلقائياً بسبب تأخر تسليم الطلب رقم {order.order_number} "
                    f"بمقدار {days_late} يوم عن تاريخ التسليم المتوقع "
                    f"({order.expected_delivery_date.strftime('%Y-%m-%d')}).\n"
                    f"حالة الطلب الحالية: {order.get_order_status_display()}"
                ),
                related_order=order,
                content_type=order_ct,
                object_id=order.pk,
                priority="high" if days_late > 7 else "medium",
                source="auto",
            )
            results["order_complaints"] += 1
            logger.info(
                f"✅ شكوى تأخير تلقائية للطلب {order.order_number} - متأخر {days_late} يوم"
            )

        # ---- 2. تركيبات متأخرة عن مواعيدها المجدولة ----
        install_ct = ContentType.objects.get_for_model(InstallationSchedule)

        delayed_installs = InstallationSchedule.objects.filter(
            scheduled_date__lt=today - timedelta(days=2),
            status__in=["scheduled", "needs_scheduling"],
        ).select_related("order", "order__customer")

        for install in delayed_installs:
            if not install.order or not install.order.customer:
                continue

            existing = Complaint.objects.filter(
                content_type=install_ct,
                object_id=install.pk,
                complaint_type=install_delay_type,
                status__in=["new", "in_progress", "escalated", "overdue"],
            ).exists()
            if existing:
                results["skipped"] += 1
                continue

            days_late = (today - install.scheduled_date).days
            Complaint.objects.create(
                customer=install.order.customer,
                complaint_type=install_delay_type,
                title=f"تأخير تركيب الطلب {install.order.order_number}",
                description=(
                    f"تم إنشاء هذه الشكوى تلقائياً بسبب تأخر تركيب الطلب رقم {install.order.order_number} "
                    f"بمقدار {days_late} يوم عن الموعد المجدول "
                    f"({install.scheduled_date.strftime('%Y-%m-%d')}).\n"
                    f"حالة التركيب الحالية: {install.get_status_display()}"
                ),
                related_order=install.order,
                content_type=install_ct,
                object_id=install.pk,
                priority="high" if days_late > 5 else "medium",
                source="auto",
            )
            results["installation_complaints"] += 1
            logger.info(
                f"✅ شكوى تأخير تركيب تلقائية للطلب {install.order.order_number} - متأخر {days_late} يوم"
            )

        logger.info(
            f"فحص التأخيرات: {results['order_complaints']} شكوى طلب، "
            f"{results['installation_complaints']} شكوى تركيب، "
            f"{results['skipped']} تم تجاهلها"
        )
        return {"success": True, "results": results}

    except Exception as e:
        logger.error(f"خطأ في إنشاء شكاوى التأخير التلقائية: {str(e)}")
        return {"success": False, "error": str(e)}
