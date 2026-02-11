"""
أمر لتحديث أرصدة جميع الحسابات من القيود المحاسبية
"""

from django.core.management.base import BaseCommand
from accounting.models import Account


class Command(BaseCommand):
    help = 'تحديث أرصدة جميع الحسابات من القيود المحاسبية'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING("🔄 بدء تحديث أرصدة الحسابات..."))
        self.stdout.write("="*60 + "\n")

        accounts = Account.objects.all()
        total = accounts.count()
        updated = 0
        errors = 0

        for account in accounts:
            try:
                old_balance = account.current_balance
                account.update_balance()
                new_balance = account.current_balance
                
                if old_balance != new_balance:
                    updated += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ {account.code} - {account.name}: "
                            f"{old_balance} → {new_balance}"
                        )
                    )
                else:
                    self.stdout.write(
                        f"   {account.code} - {account.name}: {new_balance} (لم يتغير)"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ خطأ في تحديث {account.code}: {e}"
                    )
                )

        self.stdout.write("\n" + "="*60)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ اكتمل! إجمالي الحسابات: {total} | "
                f"محدّثة: {updated} | أخطاء: {errors}"
            )
        )
        self.stdout.write("="*60 + "\n")
