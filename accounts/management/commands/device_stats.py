"""
Management command لعرض إحصائيات الأجهزة المسجلة
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Branch, BranchDevice


class Command(BaseCommand):
    help = "عرض إحصائيات الأجهزة المسجلة في النظام"

    def add_arguments(self, parser):
        parser.add_argument(
            "--branch",
            type=str,
            help="عرض أجهزة فرع محدد فقط",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="عرض الأجهزة النشطة فقط",
        )
        parser.add_argument(
            "--unused",
            action="store_true",
            help="عرض الأجهزة غير المستخدمة",
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("📊 إحصائيات أجهزة الفروع"))
        self.stdout.write("=" * 70 + "\n")

        # فلترة الأجهزة
        devices = BranchDevice.objects.all()

        if options["branch"]:
            try:
                branch = Branch.objects.get(name=options["branch"])
                devices = devices.filter(branch=branch)
                self.stdout.write(f"🔍 الفرع: {branch.name}\n")
            except Branch.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"❌ الفرع '{options['branch']}' غير موجود")
                )
                return

        if options["active_only"]:
            devices = devices.filter(is_active=True)

        if options["unused"]:
            devices = devices.filter(last_used__isnull=True)

        # إحصائيات عامة
        total_devices = devices.count()
        active_devices = devices.filter(is_active=True).count()
        inactive_devices = devices.filter(is_active=False).count()
        used_devices = devices.filter(last_used__isnull=False).count()
        never_used = devices.filter(last_used__isnull=True).count()

        self.stdout.write(f"📈 الإحصائيات العامة:")
        self.stdout.write(f"   • إجمالي الأجهزة: {total_devices}")
        self.stdout.write(f"   • نشط: {active_devices}")
        self.stdout.write(f"   • غير نشط: {inactive_devices}")
        self.stdout.write(f"   • تم استخدامه: {used_devices}")
        self.stdout.write(f"   • لم يُستخدم أبداً: {never_used}")
        self.stdout.write("")

        # إحصائيات حسب الفرع
        if not options["branch"]:
            self.stdout.write("📍 الأجهزة حسب الفرع:")
            for branch in Branch.objects.filter(is_active=True):
                branch_devices = devices.filter(branch=branch)
                count = branch_devices.count()
                active_count = branch_devices.filter(is_active=True).count()

                if count > 0:
                    self.stdout.write(
                        f"   • {branch.name}: {count} جهاز " f"({active_count} نشط)"
                    )
            self.stdout.write("")

        # عرض تفاصيل الأجهزة
        if total_devices > 0:
            self.stdout.write("📋 قائمة الأجهزة:")
            self.stdout.write("-" * 70)

            for device in devices.select_related("branch", "last_used_by"):
                status = "✅ نشط" if device.is_active else "❌ غير نشط"

                self.stdout.write(f"\n🖥️  {device.device_name}")
                self.stdout.write(f"   الفرع: {device.branch.name}")
                self.stdout.write(f"   الحالة: {status}")
                self.stdout.write(f"   البصمة: {device.device_fingerprint[:16]}...")

                if device.ip_address:
                    self.stdout.write(f"   IP: {device.ip_address}")

                if device.last_used:
                    time_ago = timezone.now() - device.last_used
                    days = time_ago.days
                    hours = time_ago.seconds // 3600

                    if days > 0:
                        time_str = f"{days} يوم"
                    else:
                        time_str = f"{hours} ساعة"

                    self.stdout.write(f"   آخر استخدام: منذ {time_str}")

                    if device.last_used_by:
                        self.stdout.write(
                            f"   آخر مستخدم: {device.last_used_by.username}"
                        )
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  لم يُستخدم أبداً"))

                if device.notes:
                    self.stdout.write(f"   ملاحظات: {device.notes[:50]}...")

            self.stdout.write("\n" + "-" * 70)

        self.stdout.write("\n" + "=" * 70 + "\n")

        # توصيات
        if never_used > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠️  تنبيه: يوجد {never_used} جهاز لم يُستخدم أبداً")
            )

        if inactive_devices > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠️  تنبيه: يوجد {inactive_devices} جهاز غير نشط")
            )
