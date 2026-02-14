"""
مهام Celery لنظام التدقيق المركزي
Core Audit System Celery Tasks
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="maintenance",
    name="core.tasks.cleanup_old_audit_logs",
)
def cleanup_old_audit_logs(self):
    """
    تنظيف سجلات التدقيق القديمة تلقائياً
    - AuditLog: الاحتفاظ بآخر 365 يوم
    - SecurityEvent: الاحتفاظ بآخر 180 يوم
    - UserActivityLog: الاحتفاظ بآخر 180 يوم
    - UserSession/UserLoginHistory: الاحتفاظ بآخر 90 يوم
    - OnlineUser: حذف الجلسات غير النشطة (أكثر من 24 ساعة)
    """
    try:
        results = {}
        now = timezone.now()

        # 1. تنظيف AuditLog (أكثر من 365 يوم)
        try:
            from core.audit import AuditLog

            threshold = now - timedelta(days=365)
            count = AuditLog.objects.filter(
                timestamp__lt=threshold, severity="INFO"
            ).count()
            if count > 0:
                # حذف على دفعات لتقليل الضغط على DB
                deleted = 0
                while deleted < count:
                    batch = list(
                        AuditLog.objects.filter(
                            timestamp__lt=threshold, severity="INFO"
                        )
                        .values_list("id", flat=True)[:5000]
                    )
                    if not batch:
                        break
                    AuditLog.objects.filter(id__in=batch).delete()
                    deleted += len(batch)
                results["audit_log_info"] = deleted
            # لا نحذف WARNING/ERROR/CRITICAL أبداً
        except Exception as e:
            logger.error(f"خطأ في تنظيف AuditLog: {e}")

        # 2. تنظيف SecurityEvent (أكثر من 180 يوم)
        try:
            from core.audit import SecurityEvent

            threshold = now - timedelta(days=180)
            count, _ = SecurityEvent.objects.filter(
                timestamp__lt=threshold
            ).delete()
            results["security_events"] = count
        except Exception as e:
            logger.error(f"خطأ في تنظيف SecurityEvent: {e}")

        # 3. تنظيف UserActivityLog (أكثر من 180 يوم)
        try:
            from user_activity.models import UserActivityLog

            threshold = now - timedelta(days=180)
            count, _ = UserActivityLog.objects.filter(
                timestamp__lt=threshold
            ).delete()
            results["user_activity_log"] = count
        except Exception as e:
            logger.error(f"خطأ في تنظيف UserActivityLog: {e}")

        # 4. تنظيف UserSession (أكثر من 90 يوم)
        try:
            from user_activity.models import UserSession

            threshold = now - timedelta(days=90)
            count, _ = UserSession.objects.filter(
                login_time__lt=threshold
            ).delete()
            results["user_sessions"] = count
        except Exception as e:
            logger.error(f"خطأ في تنظيف UserSession: {e}")

        # 5. تنظيف UserLoginHistory (أكثر من 90 يوم)
        try:
            from user_activity.models import UserLoginHistory

            threshold = now - timedelta(days=90)
            count, _ = UserLoginHistory.objects.filter(
                login_time__lt=threshold
            ).delete()
            results["user_login_history"] = count
        except Exception as e:
            logger.error(f"خطأ في تنظيف UserLoginHistory: {e}")

        # 6. تنظيف OnlineUser غير النشطين (أكثر من 24 ساعة)
        try:
            from user_activity.models import OnlineUser

            threshold = now - timedelta(hours=24)
            count, _ = OnlineUser.objects.filter(
                last_seen__lt=threshold
            ).delete()
            results["stale_online_users"] = count
        except Exception as e:
            logger.error(f"خطأ في تنظيف OnlineUser: {e}")

        total_deleted = sum(results.values())
        logger.info(
            f"✅ تنظيف سجلات التدقيق: تم حذف {total_deleted} سجل قديم — التفاصيل: {results}"
        )
        return {
            "status": "success",
            "total_deleted": total_deleted,
            "details": results,
        }

    except Exception as exc:
        logger.error(f"❌ فشل تنظيف سجلات التدقيق: {exc}")
        raise self.retry(exc=exc)
