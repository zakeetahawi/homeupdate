"""
Django management command لمراقبة اتصالات قاعدة البيانات
"""

import signal
import sys
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.monitoring import performance_monitor


class Command(BaseCommand):
    help = "مراقبة اتصالات قاعدة البيانات والأداء"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitoring_active = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="فترة المراقبة بالثواني (افتراضي: 30)",
        )

        parser.add_argument("--once", action="store_true", help="تشغيل فحص واحد فقط")

        parser.add_argument(
            "--cleanup", action="store_true", help="تنظيف الاتصالات الخاملة"
        )

        parser.add_argument(
            "--emergency",
            action="store_true",
            help="تنظيف طوارئ لجميع الاتصالات الخاملة",
        )

        parser.add_argument(
            "--status", action="store_true", help="عرض الحالة الحالية فقط"
        )

    def handle(self, *args, **options):
        # إعداد signal handler للإيقاف النظيف
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if options["status"]:
            self._show_status()
            return

        if options["cleanup"]:
            self._cleanup_connections(emergency=options["emergency"])
            return

        if options["once"]:
            self._single_check()
            return

        # بدء المراقبة المستمرة
        self._start_monitoring(options["interval"])

    def _signal_handler(self, signum, frame):
        """معالج الإشارات للإيقاف النظيف"""
        self.stdout.write(
            self.style.WARNING("\n⚠️  تم استلام إشارة الإيقاف، جاري إيقاف المراقبة...")
        )
        self.monitoring_active = False
        performance_monitor.stop_monitoring_service()
        sys.exit(0)

    def _show_status(self):
        """عرض الحالة الحالية"""
        self.stdout.write(self.style.SUCCESS("📊 حالة النظام الحالية:"))
        self.stdout.write("-" * 50)

        status = performance_monitor.get_current_status()

        # إحصائيات قاعدة البيانات
        db_stats = status.get("database")
        if db_stats:
            self.stdout.write(self.style.SUCCESS("\n🗄️  قاعدة البيانات:"))
            self.stdout.write(f"   إجمالي الاتصالات: {db_stats['total_connections']}")
            self.stdout.write(f"   الاتصالات النشطة: {db_stats['active_connections']}")
            self.stdout.write(f"   الاتصالات الخاملة: {db_stats['idle_connections']}")
            self.stdout.write(f"   معلقة في معاملة: {db_stats['idle_in_transaction']}")

            # تحديد لون التحذير
            total = db_stats["total_connections"]
            if total >= 90:
                color = self.style.ERROR
                status_text = "🔴 حرج"
            elif total >= 70:
                color = self.style.WARNING
                status_text = "🟡 تحذير"
            else:
                color = self.style.SUCCESS
                status_text = "🟢 طبيعي"

            self.stdout.write(f"   الحالة: {color(status_text)}")
        else:
            self.stdout.write(self.style.ERROR("❌ لا توجد بيانات قاعدة البيانات"))

        # إحصائيات النظام
        system_stats = status.get("system")
        if system_stats:
            self.stdout.write(self.style.SUCCESS("\n💻 النظام:"))
            memory = system_stats["memory"]
            cpu = system_stats["cpu"]
            process = system_stats["process"]

            self.stdout.write(f"   الذاكرة: {memory['percent']:.1f}% مستخدمة")
            self.stdout.write(f"   المعالج: {cpu['percent']:.1f}% مستخدم")
            self.stdout.write(
                f"   العملية: {process['memory_percent']:.1f}% ذاكرة، {process['num_threads']} خيط"
            )

        # التحذيرات
        alerts = status.get("alerts", {})
        active_alerts = [k for k, v in alerts.items() if v]

        if active_alerts:
            self.stdout.write(self.style.WARNING("\n⚠️  التحذيرات النشطة:"))
            for alert_type in active_alerts:
                alert_data = alerts[alert_type]
                self.stdout.write(f"   {alert_type}: {alert_data['connections']} اتصال")
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ لا توجد تحذيرات نشطة"))

        # حالة المراقبة
        monitoring_active = status.get("monitoring_active", False)
        if monitoring_active:
            self.stdout.write(self.style.SUCCESS("\n🔍 المراقبة: نشطة"))
        else:
            self.stdout.write(self.style.WARNING("\n🔍 المراقبة: غير نشطة"))

    def _cleanup_connections(self, emergency=False):
        """تنظيف الاتصالات"""
        cleanup_type = "طوارئ" if emergency else "عادي"
        self.stdout.write(
            self.style.WARNING(f"🧹 بدء تنظيف {cleanup_type} للاتصالات...")
        )

        cleaned = performance_monitor.db_monitor.cleanup_connections(force=emergency)

        if cleaned > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ تم تنظيف {cleaned} اتصال"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ لا توجد اتصالات تحتاج تنظيف"))

    def _single_check(self):
        """فحص واحد"""
        self.stdout.write(self.style.SUCCESS("🔍 تشغيل فحص واحد..."))

        # فحص قاعدة البيانات
        db_stats = performance_monitor.db_monitor.get_connection_stats()
        if db_stats:
            alert_level = performance_monitor.db_monitor.check_alerts(db_stats)

            self.stdout.write(f"إجمالي الاتصالات: {db_stats['total_connections']}")
            self.stdout.write(f"الاتصالات النشطة: {db_stats['active_connections']}")
            self.stdout.write(f"الاتصالات الخاملة: {db_stats['idle_connections']}")

            if alert_level:
                color = (
                    self.style.ERROR
                    if alert_level == "critical"
                    else self.style.WARNING
                )
                self.stdout.write(color(f"⚠️  تحذير: {alert_level}"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ الحالة طبيعية"))
        else:
            self.stdout.write(
                self.style.ERROR("❌ فشل في الحصول على إحصائيات قاعدة البيانات")
            )

    def _start_monitoring(self, interval):
        """بدء المراقبة المستمرة"""
        self.stdout.write(
            self.style.SUCCESS(f"🔍 بدء المراقبة المستمرة (كل {interval} ثانية)...")
        )
        self.stdout.write(self.style.WARNING("اضغط Ctrl+C للإيقاف"))
        self.stdout.write("-" * 50)

        self.monitoring_active = True
        performance_monitor.start_monitoring(interval)

        try:
            while self.monitoring_active:
                # عرض الحالة الحالية
                status = performance_monitor.get_current_status()
                db_stats = status.get("database")

                if db_stats:
                    timestamp = timezone.now().strftime("%H:%M:%S")
                    total = db_stats["total_connections"]
                    active = db_stats["active_connections"]
                    idle = db_stats["idle_connections"]

                    # تحديد لون الحالة
                    if total >= 90:
                        color = self.style.ERROR
                        status_icon = "🔴"
                    elif total >= 70:
                        color = self.style.WARNING
                        status_icon = "🟡"
                    else:
                        color = self.style.SUCCESS
                        status_icon = "🟢"

                    self.stdout.write(
                        f"[{timestamp}] {status_icon} "
                        f"إجمالي: {color(str(total))} | "
                        f"نشط: {active} | "
                        f"خامل: {idle}"
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"[{timezone.now().strftime('%H:%M:%S')}] ❌ خطأ في البيانات"
                        )
                    )

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n⚠️  تم إيقاف المراقبة"))
        finally:
            performance_monitor.stop_monitoring_service()
            self.stdout.write(self.style.SUCCESS("✅ تم إيقاف المراقبة بنجاح"))
