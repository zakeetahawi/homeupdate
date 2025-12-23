"""
أمر إداري لتوليد QR Codes للحسابات البنكية
Management Command to Generate QR Codes for Bank Accounts
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounting.models import BankAccount


class Command(BaseCommand):
    help = 'توليد QR Codes لجميع الحسابات البنكية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='إعادة توليد QR حتى للحسابات التي لديها QR بالفعل',
        )
        parser.add_argument(
            '--code',
            type=str,
            help='توليد QR لحساب محدد بالكود',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='توليد QR للحسابات النشطة فقط',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        code = options.get('code')
        active_only = options.get('active_only', False)

        # بناء الاستعلام
        queryset = BankAccount.objects.all()
        
        if code:
            queryset = queryset.filter(unique_code=code)
            if not queryset.exists():
                self.stdout.write(
                    self.style.ERROR(f'❌ لم يتم العثور على حساب بالكود: {code}')
                )
                return
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        if not force:
            queryset = queryset.filter(qr_code_base64='')

        total = queryset.count()
        
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  لا توجد حسابات تحتاج إلى توليد QR Code\n'
                    '    استخدم --force لإعادة التوليد للجميع'
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(f'\n🔄 بدء توليد QR Code لـ {total} حساب بنكي...\n')
        )

        success_count = 0
        error_count = 0
        
        for i, account in enumerate(queryset, 1):
            try:
                # توليد QR Code
                account.generate_qr_code()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ [{i}/{total}] {account.bank_name} ({account.unique_code})'
                    )
                )
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ [{i}/{total}] {account.bank_name} - خطأ: {str(e)}'
                    )
                )
                error_count += 1

        # النتيجة النهائية
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ تم توليد QR Code لـ {success_count} حساب بنكي بنجاح'
            )
        )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ فشل توليد {error_count} حساب')
            )
        
        self.stdout.write('\n' + '=' * 60 + '\n')
