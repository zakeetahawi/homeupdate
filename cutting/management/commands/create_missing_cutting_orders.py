from django.core.management.base import BaseCommand

from cutting.signals import create_missing_cutting_orders


class Command(BaseCommand):
    help = "إنشاء أوامر تقطيع للطلبات التي تحتوي على عناصر ولا تحتوي على أوامر تقطيع"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🔍 البحث عن الطلبات التي تحتاج أوامر تقطيع...")
        )

        created_count = create_missing_cutting_orders()

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ تم إنشاء أوامر تقطيع لـ {created_count} طلب بنجاح!"
                )
            )
        else:
            self.stdout.write(self.style.WARNING("ℹ️ لا توجد طلبات تحتاج أوامر تقطيع"))
