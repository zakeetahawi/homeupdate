#!/usr/bin/env python
"""
أداة مراقبة تسلسل ID بشكل دوري
تستخدم لمراقبة حالة التسلسل والتنبيه عند وجود مشاكل
"""

import json
import logging
import os
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "مراقبة تسلسل ID بشكل دوري والتنبيه عند وجود مشاكل"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="فترة المراقبة بالدقائق (افتراضي: 60)",
        )
        parser.add_argument(
            "--email-alerts",
            action="store_true",
            help="إرسال تنبيهات بالبريد الإلكتروني",
        )
        parser.add_argument(
            "--auto-fix", action="store_true", help="إصلاح تلقائي عند اكتشاف مشاكل"
        )
        parser.add_argument("--report-file", type=str, help="ملف تقرير المراقبة")
        parser.add_argument(
            "--daemon", action="store_true", help="تشغيل كخدمة في الخلفية"
        )

    def handle(self, *args, **options):
        self.interval = options.get("interval", 60)
        self.email_alerts = options.get("email_alerts", False)
        self.auto_fix = options.get("auto_fix", False)
        self.report_file = options.get("report_file")
        self.daemon = options.get("daemon", False)

        if self.daemon:
            self.run_daemon()
        else:
            self.run_single_check()

    def run_single_check(self):
        """تشغيل فحص واحد"""
        self.stdout.write(self.style.SUCCESS("🔍 بدء مراقبة تسلسل ID..."))

        try:
            report = self.check_all_sequences()
            self.process_report(report)

        except Exception as e:
            logger.error(f"خطأ في مراقبة التسلسل: {str(e)}")
            self.stdout.write(self.style.ERROR(f"❌ فشل في المراقبة: {str(e)}"))

    def run_daemon(self):
        """تشغيل المراقبة كخدمة في الخلفية"""
        import time

        self.stdout.write(
            self.style.SUCCESS(f"🔄 بدء مراقبة دورية كل {self.interval} دقيقة...")
        )

        try:
            while True:
                try:
                    report = self.check_all_sequences()
                    self.process_report(report)

                    # انتظار الفترة المحددة
                    time.sleep(self.interval * 60)

                except KeyboardInterrupt:
                    self.stdout.write(self.style.WARNING("⏹️  تم إيقاف المراقبة"))
                    break
                except Exception as e:
                    logger.error(f"خطأ في دورة المراقبة: {str(e)}")
                    time.sleep(60)  # انتظار دقيقة قبل المحاولة مرة أخرى

        except Exception as e:
            logger.error(f"خطأ في خدمة المراقبة: {str(e)}")
            raise

    def check_all_sequences(self):
        """فحص جميع التسلسلات وإنشاء تقرير"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "problems": [],
            "warnings": [],
            "healthy_tables": [],
            "statistics": {
                "total_tables": 0,
                "problem_tables": 0,
                "warning_tables": 0,
                "healthy_tables": 0,
            },
        }

        with connection.cursor() as cursor:
            try:
                # الحصول على جميع الجداول مع التسلسل (IDENTITY أو SERIAL)
                cursor.execute(
                    """
                    SELECT
                        t.table_name,
                        c.column_name,
                        c.column_default,
                        c.is_identity
                    FROM information_schema.tables t
                    JOIN information_schema.columns c ON t.table_name = c.table_name
                    WHERE t.table_schema = 'public'
                    AND (c.column_default LIKE 'nextval%%' OR c.is_identity = 'YES')
                    ORDER BY t.table_name
                """
                )

                tables_with_sequences = cursor.fetchall()
                report["statistics"]["total_tables"] = len(tables_with_sequences)

                for (
                    table_name,
                    column_name,
                    column_default,
                    is_identity,
                ) in tables_with_sequences:
                    if is_identity == "YES":
                        # IDENTITY column - استخدام اسم التسلسل المتوقع
                        sequence_name = f"{table_name}_{column_name}_seq"
                    else:
                        # SERIAL column - استخراج اسم التسلسل من column_default
                        sequence_name = self.extract_sequence_name(column_default)

                    if sequence_name:
                        table_status = self.check_table_sequence_status(
                            table_name, column_name, sequence_name
                        )

                        if table_status["severity"] == "critical":
                            report["problems"].append(table_status)
                            report["status"] = "critical"
                            report["statistics"]["problem_tables"] += 1
                        elif table_status["severity"] == "warning":
                            report["warnings"].append(table_status)
                            if report["status"] == "healthy":
                                report["status"] = "warning"
                            report["statistics"]["warning_tables"] += 1
                        else:
                            report["healthy_tables"].append(table_status)
                            report["statistics"]["healthy_tables"] += 1

                return report

            except Exception as e:
                logger.error(f"خطأ في فحص التسلسلات: {str(e)}")
                raise

    def extract_sequence_name(self, column_default):
        """استخراج اسم التسلسل من column_default"""
        import re

        match = re.search(r"nextval\('([^']+)'", column_default)
        if match:
            return match.group(1)
        return None

    def check_table_sequence_status(self, table_name, column_name, sequence_name):
        """فحص حالة تسلسل جدول محدد"""
        with connection.cursor() as cursor:
            try:
                # التحقق من وجود التسلسل
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_sequences
                        WHERE sequencename = %s
                    )
                """,
                    [sequence_name],
                )

                if not cursor.fetchone()[0]:
                    return {
                        "table": table_name,
                        "severity": "error",
                        "message": f"التسلسل {sequence_name} غير موجود",
                        "error": f"Sequence {sequence_name} not found",
                    }

                # الحصول على أعلى ID موجود
                cursor.execute(
                    f"SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}"
                )
                max_id_result = cursor.fetchone()
                max_id = max_id_result[0] if max_id_result else 0

                # الحصول على القيمة الحالية للتسلسل
                cursor.execute(f"SELECT last_value FROM {sequence_name}")
                seq_result = cursor.fetchone()
                current_seq = seq_result[0] if seq_result else 0

                # حساب عدد الصفوف
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count_result = cursor.fetchone()
                row_count = count_result[0] if count_result else 0

                # تحليل الحالة
                gap = current_seq - max_id
                next_value = max_id + 1

                status = {
                    "table": table_name,
                    "column": column_name,
                    "sequence": sequence_name,
                    "max_id": max_id,
                    "current_seq": current_seq,
                    "next_value": next_value,
                    "row_count": row_count,
                    "gap": gap,
                    "timestamp": datetime.now().isoformat(),
                }

                if current_seq < next_value:
                    status.update(
                        {
                            "severity": "critical",
                            "message": f"تسلسل منخفض! قد يحدث تضارب في ID التالي",
                            "risk_level": "high",
                        }
                    )
                elif gap > 10000:
                    status.update(
                        {
                            "severity": "warning",
                            "message": f"فجوة كبيرة جداً في التسلسل ({gap:,})",
                            "risk_level": "medium",
                        }
                    )
                elif gap > 1000:
                    status.update(
                        {
                            "severity": "warning",
                            "message": f"فجوة كبيرة في التسلسل ({gap:,})",
                            "risk_level": "low",
                        }
                    )
                else:
                    status.update(
                        {
                            "severity": "healthy",
                            "message": "التسلسل يعمل بشكل صحيح",
                            "risk_level": "none",
                        }
                    )

                return status

            except Exception as e:
                logger.error(f"خطأ في فحص {table_name}: {str(e)}")
                return {
                    "table": table_name,
                    "severity": "error",
                    "message": f"خطأ في الفحص: {str(e)}",
                    "error": str(e),
                }

    def process_report(self, report):
        """معالجة تقرير المراقبة"""
        status = report["status"]
        problems = report["problems"]
        warnings = report["warnings"]

        # عرض النتائج
        if status == "critical":
            self.stdout.write(self.style.ERROR(f"🚨 مشاكل حرجة: {len(problems)}"))
            for problem in problems:
                self.stdout.write(
                    self.style.ERROR(f'   - {problem["table"]}: {problem["message"]}')
                )
        elif status == "warning":
            self.stdout.write(self.style.WARNING(f"⚠️  تحذيرات: {len(warnings)}"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ جميع التسلسلات تعمل بشكل صحيح"))

        # الإصلاح التلقائي
        if self.auto_fix and (problems or warnings):
            self.stdout.write(self.style.SUCCESS("🔧 بدء الإصلاح التلقائي..."))
            try:
                call_command("fix_all_sequences", verbosity=0)
                self.stdout.write(self.style.SUCCESS("✅ تم الإصلاح التلقائي"))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ فشل الإصلاح التلقائي: {str(e)}")
                )

        # حفظ التقرير
        if self.report_file:
            self.save_report(report)

        # إرسال تنبيهات بالبريد الإلكتروني
        if self.email_alerts and status in ["critical", "warning"]:
            self.send_email_alert(report)

    def save_report(self, report):
        """حفظ تقرير المراقبة"""
        try:
            report_dir = os.path.dirname(self.report_file)
            if report_dir and not os.path.exists(report_dir):
                os.makedirs(report_dir)

            with open(self.report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            self.stdout.write(
                self.style.SUCCESS(f"📄 تم حفظ التقرير: {self.report_file}")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ فشل في حفظ التقرير: {str(e)}"))

    def send_email_alert(self, report):
        """إرسال تنبيه بالبريد الإلكتروني"""
        try:
            if not hasattr(settings, "EMAIL_HOST") or not settings.EMAIL_HOST:
                return

            status = report["status"]
            problems = report["problems"]
            warnings = report["warnings"]

            subject = f"تنبيه تسلسل ID - {status.upper()}"

            message = f"""
تم اكتشاف مشاكل في تسلسل ID:

الحالة: {status}
المشاكل الحرجة: {len(problems)}
التحذيرات: {len(warnings)}
وقت الفحص: {report['timestamp']}

المشاكل الحرجة:
"""

            for problem in problems:
                message += f"- {problem['table']}: {problem['message']}\n"

            if warnings:
                message += "\nالتحذيرات:\n"
                for warning in warnings:
                    message += f"- {warning['table']}: {warning['message']}\n"

            # إرسال البريد الإلكتروني
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMINS[0][1]] if settings.ADMINS else [],
                fail_silently=False,
            )

            self.stdout.write(
                self.style.SUCCESS("📧 تم إرسال تنبيه بالبريد الإلكتروني")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ فشل في إرسال التنبيه: {str(e)}"))
