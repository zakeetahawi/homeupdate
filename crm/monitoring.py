"""
نظام مراقبة متقدم لاتصالات قاعدة البيانات والأداء
Advanced monitoring system for database connections and performance
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta

import psutil
import psycopg2
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

logger = logging.getLogger("monitoring")


class DatabaseMonitor:
    """
    مراقب اتصالات قاعدة البيانات
    """

    def __init__(self):
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "idle_in_transaction": 0,
            "max_connections_seen": 0,
            "alerts_sent": 0,
            "last_cleanup": None,
            "monitoring_start": timezone.now(),
        }
        self.alert_thresholds = {
            "warning": 70,
            "critical": 90,
            "emergency": 120,
        }
        self.monitoring_active = False
        self._lock = threading.Lock()

    def get_connection_stats(self):
        """الحصول على إحصائيات الاتصالات الحالية"""
        try:
            # استخدام PgBouncer إذا كان متاحاً
            db_config = settings.DATABASES["default"]

            conn = psycopg2.connect(
                host=db_config["HOST"],
                port=db_config["PORT"],
                database=db_config["NAME"],
                user=db_config["USER"],
                password=db_config["PASSWORD"],
                connect_timeout=5,
            )

            with conn.cursor() as cursor:
                # إحصائيات الاتصالات
                cursor.execute(
                    """
                    SELECT 
                        count(*) as total,
                        count(*) FILTER (WHERE state = 'active') as active,
                        count(*) FILTER (WHERE state = 'idle') as idle,
                        count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
                        count(*) FILTER (WHERE state = 'idle in transaction (aborted)') as aborted
                    FROM pg_stat_activity 
                    WHERE datname = %s;
                """,
                    (db_config["NAME"],),
                )

                result = cursor.fetchone()

                current_stats = {
                    "total_connections": result[0] or 0,
                    "active_connections": result[1] or 0,
                    "idle_connections": result[2] or 0,
                    "idle_in_transaction": result[3] or 0,
                    "aborted_connections": result[4] or 0,
                    "timestamp": timezone.now(),
                }

                # تحديث الإحصائيات
                with self._lock:
                    self.stats.update(current_stats)
                    if (
                        current_stats["total_connections"]
                        > self.stats["max_connections_seen"]
                    ):
                        self.stats["max_connections_seen"] = current_stats[
                            "total_connections"
                        ]

                conn.close()
                return current_stats

        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
            return None

    def check_alerts(self, stats):
        """فحص التحذيرات"""
        if not stats:
            return None

        total = stats["total_connections"]
        alert_level = None

        if total >= self.alert_thresholds["emergency"]:
            alert_level = "emergency"
        elif total >= self.alert_thresholds["critical"]:
            alert_level = "critical"
        elif total >= self.alert_thresholds["warning"]:
            alert_level = "warning"

        if alert_level:
            self.stats["alerts_sent"] += 1
            logger.warning(
                f"Database connection alert: {alert_level} - {total} connections"
            )

            # حفظ التحذير في cache للعرض في لوحة التحكم
            alert_data = {
                "level": alert_level,
                "connections": total,
                "timestamp": timezone.now().isoformat(),
                "stats": stats,
            }
            cache.set(f"db_alert_{alert_level}", alert_data, 3600)

        return alert_level

    def cleanup_connections(self, force=False):
        """تنظيف الاتصالات الخاملة"""
        try:
            db_config = settings.DATABASES["default"]

            # استخدام الاتصال المباشر للتنظيف
            direct_config = getattr(settings, "DATABASES_DIRECT", {}).get(
                "default", db_config
            )

            conn = psycopg2.connect(
                host=direct_config["HOST"],
                port=direct_config["PORT"],
                database=direct_config["NAME"],
                user=direct_config["USER"],
                password=direct_config["PASSWORD"],
                connect_timeout=5,
            )

            with conn.cursor() as cursor:
                if force:
                    # تنظيف طوارئ - قتل جميع الاتصالات الخاملة
                    cursor.execute(
                        """
                        SELECT count(pg_terminate_backend(pid))
                        FROM pg_stat_activity 
                        WHERE datname = %s 
                        AND state IN ('idle', 'idle in transaction')
                        AND pid != pg_backend_pid();
                    """,
                        (db_config["NAME"],),
                    )
                else:
                    # تنظيف عادي - قتل الاتصالات الخاملة لأكثر من 5 دقائق
                    cursor.execute(
                        """
                        SELECT count(pg_terminate_backend(pid))
                        FROM pg_stat_activity 
                        WHERE datname = %s 
                        AND state = 'idle'
                        AND state_change < now() - interval '5 minutes'
                        AND pid != pg_backend_pid();
                    """,
                        (db_config["NAME"],),
                    )

                killed = cursor.fetchone()[0] or 0

                if killed > 0:
                    logger.info(f"Cleaned up {killed} idle connections")
                    self.stats["last_cleanup"] = timezone.now()

                conn.close()
                return killed

        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")
            return 0


class SystemMonitor:
    """
    مراقب النظام العام
    """

    def __init__(self):
        self.process = psutil.Process()
        self.stats = {}

    def get_system_stats(self):
        """الحصول على إحصائيات النظام"""
        try:
            # إحصائيات الذاكرة
            memory = psutil.virtual_memory()

            # إحصائيات المعالج
            cpu_percent = psutil.cpu_percent(interval=1)

            # إحصائيات القرص
            disk = psutil.disk_usage("/")

            # إحصائيات العملية الحالية
            process_memory = self.process.memory_info()

            stats = {
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                },
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "memory_percent": self.process.memory_percent(),
                    "cpu_percent": self.process.cpu_percent(),
                    "num_threads": self.process.num_threads(),
                },
                "timestamp": timezone.now(),
            }

            self.stats = stats
            return stats

        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return None


class PerformanceMonitor:
    """
    مراقب الأداء العام
    """

    def __init__(self):
        self.db_monitor = DatabaseMonitor()
        self.system_monitor = SystemMonitor()
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()

    def start_monitoring(self, interval=30):
        """بدء المراقبة"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Monitoring already running")
            return

        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(interval,), daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Performance monitoring started with {interval}s interval")

    def stop_monitoring_service(self):
        """إيقاف المراقبة"""
        self.stop_monitoring.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self, interval):
        """حلقة المراقبة الرئيسية"""
        while not self.stop_monitoring.wait(interval):
            try:
                # مراقبة قاعدة البيانات
                db_stats = self.db_monitor.get_connection_stats()
                if db_stats:
                    alert_level = self.db_monitor.check_alerts(db_stats)

                    # تنظيف تلقائي في حالة التحذير
                    if alert_level in ["critical", "emergency"]:
                        cleaned = self.db_monitor.cleanup_connections(
                            force=(alert_level == "emergency")
                        )
                        logger.info(
                            f"Auto-cleanup triggered: {cleaned} connections cleaned"
                        )

                # مراقبة النظام
                system_stats = self.system_monitor.get_system_stats()

                # حفظ الإحصائيات في cache
                cache.set("monitoring_db_stats", db_stats, 300)
                cache.set("monitoring_system_stats", system_stats, 300)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    def get_current_status(self):
        """الحصول على الحالة الحالية"""
        return {
            "database": cache.get("monitoring_db_stats"),
            "system": cache.get("monitoring_system_stats"),
            "alerts": {
                "warning": cache.get("db_alert_warning"),
                "critical": cache.get("db_alert_critical"),
                "emergency": cache.get("db_alert_emergency"),
            },
            "monitoring_active": self.monitoring_thread
            and self.monitoring_thread.is_alive(),
        }


# إنشاء نسخة عامة
performance_monitor = PerformanceMonitor()


def start_monitoring():
    """بدء المراقبة - للاستخدام في startup"""
    performance_monitor.start_monitoring()


def stop_monitoring():
    """إيقاف المراقبة - للاستخدام في shutdown"""
    performance_monitor.stop_monitoring_service()


def get_monitoring_status():
    """الحصول على حالة المراقبة - للاستخدام في API"""
    return performance_monitor.get_current_status()
