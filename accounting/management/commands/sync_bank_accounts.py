"""
أمر إداري لمزامنة الحسابات البنكية مع Cloudflare
Management Command to Sync Bank Accounts to Cloudflare
"""

from django.core.management.base import BaseCommand

from accounting.cloudflare_sync import sync_bank_accounts_to_cloudflare
from accounting.models import BankAccount


class Command(BaseCommand):
    help = "مزامنة الحسابات البنكية مع Cloudflare Workers KV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--code",
            type=str,
            help="مزامنة حساب محدد بالكود",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="مزامنة الحسابات النشطة فقط",
        )

    def handle(self, *args, **options):
        code = options.get("code")
        active_only = options.get("active_only", False)

        # بناء الاستعلام
        queryset = BankAccount.objects.all()

        if code:
            queryset = queryset.filter(unique_code=code)
            if not queryset.exists():
                self.stdout.write(
                    self.style.ERROR(f"❌ لم يتم العثور على حساب بالكود: {code}")
                )
                return

        if active_only:
            queryset = queryset.filter(is_active=True)

        total = queryset.count()

        self.stdout.write(
            self.style.WARNING(f"\n☁️  بدء مزامنة {total} حساب بنكي مع Cloudflare...\n")
        )

        try:
            result = sync_bank_accounts_to_cloudflare(list(queryset))

            if result.get("success"):
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ تم مزامنة {result.get("count", 0)} حساب بنكي بنجاح'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'\n❌ فشلت المزامنة: {result.get("error", "خطأ غير معروف")}'
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ خطأ في المزامنة: {str(e)}"))
