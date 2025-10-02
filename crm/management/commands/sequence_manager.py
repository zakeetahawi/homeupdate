#!/usr/bin/env python
"""
أداة إدارة شاملة لتسلسل ID
تجمع جميع وظائف إدارة التسلسل في أداة واحدة
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "أداة إدارة شاملة لتسلسل ID - فحص، إصلاح، مراقبة"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", help="الإجراء المطلوب")

        # فحص التسلسل
        check_parser = subparsers.add_parser("check", help="فحص حالة التسلسل")
        check_parser.add_argument("--app", type=str, help="فحص تطبيق محدد")
        check_parser.add_argument("--table", type=str, help="فحص جدول محدد")
        check_parser.add_argument(
            "--show-all", action="store_true", help="عرض جميع الجداول"
        )
        check_parser.add_argument("--export", type=str, help="تصدير النتائج")

        # إصلاح التسلسل
        fix_parser = subparsers.add_parser("fix", help="إصلاح التسلسل")
        fix_parser.add_argument("--app", type=str, help="إصلاح تطبيق محدد")
        fix_parser.add_argument("--table", type=str, help="إصلاح جدول محدد")
        fix_parser.add_argument("--dry-run", action="store_true", help="معاينة فقط")
        fix_parser.add_argument("--verbose", action="store_true", help="تفاصيل أكثر")

        # مراقبة التسلسل
        monitor_parser = subparsers.add_parser("monitor", help="مراقبة التسلسل")
        monitor_parser.add_argument(
            "--interval", type=int, default=60, help="فترة المراقبة بالدقائق"
        )
        monitor_parser.add_argument(
            "--email-alerts", action="store_true", help="تنبيهات البريد الإلكتروني"
        )
        monitor_parser.add_argument(
            "--auto-fix", action="store_true", help="إصلاح تلقائي"
        )
        monitor_parser.add_argument("--daemon", action="store_true", help="تشغيل كخدمة")

        # إصلاح تلقائي
        auto_parser = subparsers.add_parser("auto", help="إصلاح تلقائي")
        auto_parser.add_argument("--check-only", action="store_true", help="فحص فقط")
        auto_parser.add_argument("--force", action="store_true", help="إجبار الإصلاح")

        # معلومات التسلسل
        info_parser = subparsers.add_parser("info", help="معلومات التسلسل")
        info_parser.add_argument(
            "--detailed", action="store_true", help="معلومات مفصلة"
        )

        # إعادة تعيين التسلسل
        reset_parser = subparsers.add_parser("reset", help="إعادة تعيين التسلسل")
        reset_parser.add_argument("table", type=str, help="اسم الجدول")
        reset_parser.add_argument("--start-value", type=int, help="القيمة الابتدائية")
        reset_parser.add_argument(
            "--confirm", action="store_true", help="تأكيد العملية"
        )

    def handle(self, *args, **options):
        action = options.get("action")

        if not action:
            self.print_help()
            return

        try:
            if action == "check":
                self.handle_check(options)
            elif action == "fix":
                self.handle_fix(options)
            elif action == "monitor":
                self.handle_monitor(options)
            elif action == "auto":
                self.handle_auto(options)
            elif action == "info":
                self.handle_info(options)
            elif action == "reset":
                self.handle_reset(options)
            else:
                raise CommandError(f"إجراء غير معروف: {action}")

        except Exception as e:
            logger.error(f"خطأ في تنفيذ {action}: {str(e)}")
            raise CommandError(f"فشل في تنفيذ {action}: {str(e)}")

    def handle_check(self, options):
        """تنفيذ فحص التسلسل"""
        self.stdout.write(self.style.SUCCESS("🔍 تنفيذ فحص التسلسل..."))

        cmd_options = ["check_sequences"]

        if options.get("app"):
            cmd_options.extend(["--app", options["app"]])
        if options.get("table"):
            cmd_options.extend(["--table", options["table"]])
        if options.get("show_all"):
            cmd_options.append("--show-all")
        if options.get("export"):
            cmd_options.extend(["--export", options["export"]])

        call_command(*cmd_options)

    def handle_fix(self, options):
        """تنفيذ إصلاح التسلسل"""
        self.stdout.write(self.style.SUCCESS("🔧 تنفيذ إصلاح التسلسل..."))

        cmd_options = ["fix_all_sequences"]

        if options.get("app"):
            cmd_options.extend(["--app", options["app"]])
        if options.get("table"):
            cmd_options.extend(["--table", options["table"]])
        if options.get("dry_run"):
            cmd_options.append("--dry-run")
        if options.get("verbose"):
            cmd_options.append("--verbose")

        call_command(*cmd_options)

    def handle_monitor(self, options):
        """تنفيذ مراقبة التسلسل"""
        self.stdout.write(self.style.SUCCESS("👁️  تنفيذ مراقبة التسلسل..."))

        cmd_options = ["monitor_sequences"]

        if options.get("interval"):
            cmd_options.extend(["--interval", str(options["interval"])])
        if options.get("email_alerts"):
            cmd_options.append("--email-alerts")
        if options.get("auto_fix"):
            cmd_options.append("--auto-fix")
        if options.get("daemon"):
            cmd_options.append("--daemon")

        call_command(*cmd_options)

    def handle_auto(self, options):
        """تنفيذ الإصلاح التلقائي"""
        self.stdout.write(self.style.SUCCESS("🤖 تنفيذ الإصلاح التلقائي..."))

        cmd_options = ["auto_fix_sequences"]

        if options.get("check_only"):
            cmd_options.append("--check-only")
        if options.get("force"):
            cmd_options.append("--force")

        call_command(*cmd_options)

    def handle_info(self, options):
        """عرض معلومات التسلسل"""
        self.stdout.write(self.style.SUCCESS("ℹ️  معلومات التسلسل:"))

        with connection.cursor() as cursor:
            try:
                # الحصول على معلومات جميع التسلسلات
                cursor.execute(
                    """
                    SELECT 
                        schemaname,
                        sequencename,
                        last_value,
                        start_value,
                        increment_by,
                        max_value,
                        min_value,
                        cache_value,
                        is_cycled
                    FROM pg_sequences
                    WHERE schemaname = 'public'
                    ORDER BY sequencename
                """
                )

                sequences = cursor.fetchall()

                if not sequences:
                    self.stdout.write(
                        self.style.WARNING("⚠️  لا توجد تسلسلات في قاعدة البيانات")
                    )
                    return

                self.stdout.write(f"\n📊 إجمالي التسلسلات: {len(sequences)}")
                self.stdout.write("=" * 80)

                for seq in sequences:
                    (
                        schema,
                        name,
                        last_val,
                        start_val,
                        increment,
                        max_val,
                        min_val,
                        cache,
                        cycled,
                    ) = seq

                    self.stdout.write(f"\n🔢 {name}")
                    self.stdout.write(f"   القيمة الحالية: {last_val:,}")
                    self.stdout.write(f"   القيمة الابتدائية: {start_val:,}")
                    self.stdout.write(f"   الزيادة: {increment}")

                    if options.get("detailed"):
                        self.stdout.write(f"   القيمة العظمى: {max_val:,}")
                        self.stdout.write(f"   القيمة الصغرى: {min_val:,}")
                        self.stdout.write(f"   التخزين المؤقت: {cache}")
                        self.stdout.write(f'   دوري: {"نعم" if cycled else "لا"}')

                        # البحث عن الجدول المرتبط
                        table_name = self.find_table_for_sequence(name)
                        if table_name:
                            self.stdout.write(f"   الجدول المرتبط: {table_name}")

                            # فحص حالة الجدول
                            max_id = self.get_max_id_for_table(table_name)
                            if max_id is not None:
                                gap = last_val - max_id
                                self.stdout.write(f"   أعلى ID في الجدول: {max_id:,}")
                                self.stdout.write(f"   الفجوة: {gap:,}")

                                if gap < 1:
                                    self.stdout.write(
                                        self.style.ERROR("   ⚠️  مشكلة محتملة!")
                                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ خطأ في جلب معلومات التسلسل: {str(e)}")
                )

    def handle_reset(self, options):
        """إعادة تعيين تسلسل محدد"""
        table_name = options["table"]
        start_value = options.get("start_value")
        confirm = options.get("confirm", False)

        if not confirm:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  إعادة تعيين التسلسل عملية خطيرة! " "استخدم --confirm للتأكيد"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(f"🔄 إعادة تعيين تسلسل الجدول: {table_name}")
        )

        with connection.cursor() as cursor:
            try:
                # البحث عن التسلسل المرتبط بالجدول
                sequence_name = f"{table_name}_id_seq"

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
                    raise CommandError(f"التسلسل {sequence_name} غير موجود")

                # تحديد القيمة الابتدائية
                if start_value is None:
                    # استخدام أعلى ID موجود + 1
                    cursor.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}")
                    start_value = cursor.fetchone()[0]

                # إعادة تعيين التسلسل
                cursor.execute(
                    f"SELECT setval('{sequence_name}', %s, false)", [start_value]
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ تم إعادة تعيين {sequence_name} إلى {start_value}"
                    )
                )

            except Exception as e:
                raise CommandError(f"فشل في إعادة تعيين التسلسل: {str(e)}")

    def find_table_for_sequence(self, sequence_name):
        """البحث عن الجدول المرتبط بالتسلسل"""
        # استخراج اسم الجدول من اسم التسلسل
        if sequence_name.endswith("_id_seq"):
            return sequence_name[:-7]  # إزالة '_id_seq'
        return None

    def get_max_id_for_table(self, table_name):
        """الحصول على أعلى ID في الجدول"""
        with connection.cursor() as cursor:
            try:
                cursor.execute(f"SELECT MAX(id) FROM {table_name}")
                result = cursor.fetchone()
                return result[0] if result and result[0] is not None else 0
            except Exception:
                return None

    def print_help(self):
        """عرض مساعدة الأداة"""
        help_text = """
🔧 أداة إدارة تسلسل ID الشاملة

الاستخدام:
  python manage.py sequence_manager <action> [options]

الإجراءات المتاحة:
  check     - فحص حالة التسلسل
  fix       - إصلاح التسلسل
  monitor   - مراقبة التسلسل
  auto      - إصلاح تلقائي
  info      - معلومات التسلسل
  reset     - إعادة تعيين التسلسل

أمثلة:
  # فحص جميع التسلسلات
  python manage.py sequence_manager check --show-all

  # إصلاح جميع التسلسلات
  python manage.py sequence_manager fix

  # مراقبة دورية مع إصلاح تلقائي
  python manage.py sequence_manager monitor --auto-fix --daemon

  # معلومات مفصلة عن التسلسلات
  python manage.py sequence_manager info --detailed

للمساعدة في إجراء محدد:
  python manage.py sequence_manager <action> --help
"""
        self.stdout.write(help_text)
