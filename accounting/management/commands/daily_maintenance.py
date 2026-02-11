"""
صيانة دورية يومية للنظام المحاسبي
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from accounting.models import CustomerFinancialSummary, Transaction


class Command(BaseCommand):
    help = "الصيانة اليومية للنظام المحاسبي"

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(" الصيانة اليومية "))
        self.stdout.write("=" * 80)

        today = timezone.now().date()
        self.stdout.write(f"\nالتاريخ: {today}")

        # 1. تحديث أرصدة العملاء
        self.stdout.write("\n1️⃣  تحديث أرصدة العملاء...")
        summaries = CustomerFinancialSummary.objects.all()
        count = summaries.count()
        
        for i, summary in enumerate(summaries, 1):
            summary.refresh()
            if i % 100 == 0:
                self.stdout.write(f"   تم: {i}/{count}")
        
        self.stdout.write(self.style.SUCCESS(f"   ✅ تم تحديث {count} رصيد"))

        # 2. معاملات اليوم
        self.stdout.write("\n2️⃣  معاملات اليوم...")
        today_trans = Transaction.objects.filter(
            date=today,
            status='posted'
        ).count()
        self.stdout.write(f"   المعاملات المرحلة: {today_trans}")

        # 3. القيود المعلقة
        self.stdout.write("\n3️⃣  القيود المعلقة...")
        draft_trans = Transaction.objects.filter(status='draft').count()
        
        if draft_trans > 0:
            self.stdout.write(self.style.WARNING(
                f"   ⚠️  {draft_trans} قيد معلق"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ لا توجد قيود معلقة"))

        # 4. الملخص
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ اكتملت الصيانة اليومية"))
        self.stdout.write("=" * 80)
