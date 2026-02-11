"""
أمر لإعداد الإعدادات المحاسبية الافتراضية
"""
from django.core.management.base import BaseCommand

from accounting.models import Account, AccountingSettings


class Command(BaseCommand):
    help = "إعداد الإعدادات المحاسبية الافتراضية"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("⚙️  إعداد الإعدادات المحاسبية..."))

        # البحث عن أو إنشاء الحسابات الأساسية
        cash_account, _ = Account.objects.get_or_create(
            code="1110",
            defaults={"name": "النقدية والبنوك"},
        )

        # استخدام الحساب الصحيح للعملاء (1121 تحت الذمم المدينة)
        receivables_account = Account.objects.filter(code="1121").first()
        if not receivables_account:
            self.stdout.write(
                self.style.ERROR("  ❌ حساب العملاء (1121) غير موجود")
            )
            return

        revenue_account, _ = Account.objects.get_or_create(
            code="4100",
            defaults={"name": "إيرادات المبيعات"},
        )

        advances_account, created = Account.objects.get_or_create(
            code="2110",
            defaults={"name": "عربونات العملاء (التزامات)"},
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS("  ✅ تم إنشاء حساب العربونات (2110)")
            )

        # إنشاء أو تحديث الإعدادات
        settings, created = AccountingSettings.objects.get_or_create(
            id=1,
            defaults={
                "default_cash_account": cash_account,
                "default_receivables_account": receivables_account,
                "default_revenue_account": revenue_account,
                "auto_post_transactions": True,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("  ✅ تم إنشاء الإعدادات المحاسبية")
            )
        else:
            # تحديث الإعدادات الموجودة
            settings.default_cash_account = cash_account
            settings.default_receivables_account = receivables_account
            settings.default_revenue_account = revenue_account
            settings.save()
            self.stdout.write(
                self.style.SUCCESS("  ✅ تم تحديث الإعدادات المحاسبية")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"""
✅ اكتمل الإعداد!

الحسابات الافتراضية:
  • النقدية: {cash_account.code} - {cash_account.name}
  • المدينين: {receivables_account.code} - {receivables_account.name}
  • الإيرادات: {revenue_account.code} - {revenue_account.name}
  • العربونات: {advances_account.code} - {advances_account.name}

الترحيل التلقائي: {'مفعّل' if settings.auto_post_transactions else 'معطّل'}
"""
            )
        )
