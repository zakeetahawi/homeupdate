"""
أمر إداري لإنشاء حسابات محاسبية للعملاء الذين ليس لديهم حسابات
Management Command to Create Accounting Accounts for Customers
"""

from django.core.management.base import BaseCommand

from accounting.models import Account, AccountType
from customers.models import Customer


class Command(BaseCommand):
    help = "إنشاء حسابات محاسبية لجميع العملاء الذين ليس لديهم حسابات"

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer-id",
            type=int,
            help="إنشاء حساب لعميل محدد فقط",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="إعادة إنشاء الحسابات حتى للعملاء الذين لديهم حسابات",
        )

    def handle(self, *args, **options):
        customer_id = options.get("customer_id")
        force = options.get("force", False)

        # الحصول على نوع حساب المدينين والحساب الأب
        try:
            receivables_type = AccountType.objects.filter(code_prefix="1200").first()
            if not receivables_type:
                self.stdout.write(
                    self.style.ERROR("❌ نوع حساب المدينين غير موجود (1200)")
                )
                return

            parent_account = Account.objects.filter(code="1121").first()
            if not parent_account:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  الحساب الأب (1121 - العملاء) غير موجود - سيتم إنشاء الحسابات بدون حساب أب"
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ خطأ في الحصول على الإعدادات: {e}"))
            return

        # تحديد العملاء
        if customer_id:
            customers = Customer.objects.filter(id=customer_id)
            if not customers.exists():
                self.stdout.write(
                    self.style.ERROR(f"❌ العميل رقم {customer_id} غير موجود")
                )
                return
        else:
            if force:
                customers = Customer.objects.all()
            else:
                # العملاء الذين ليس لديهم حساب محاسبي
                customers = Customer.objects.filter(accounting_account__isnull=True)

        total = customers.count()

        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  لا يوجد عملاء يحتاجون لإنشاء حسابات\n"
                    "    استخدم --force لإعادة إنشاء الحسابات للجميع"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(f"\n🔄 بدء إنشاء حسابات لـ {total} عميل...\n")
        )

        success_count = 0
        skip_count = 0
        error_count = 0

        for i, customer in enumerate(customers, 1):
            try:
                # التحقق من وجود حساب
                existing_account = Account.objects.filter(customer=customer).first()

                if existing_account and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⏭️  [{i}/{total}] {customer.name} - حساب موجود مسبقاً"
                        )
                    )
                    skip_count += 1
                    continue

                # توليد كود الحساب
                customer_code = f"1121{customer.id:05d}"

                # إنشاء أو تحديث الحساب
                account, created = Account.objects.update_or_create(
                    customer=customer,
                    defaults={
                        "code": customer_code,
                        "name": f"حساب العميل - {customer.name}",
                        "name_en": f"Customer Account - {customer.name}",
                        "account_type": receivables_type,
                        "parent": parent_account,
                        "is_customer_account": True,
                        "is_active": True,
                        "allow_transactions": True,
                    },
                )

                action = "✓ تم إنشاء" if created else "↻ تم تحديث"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {action} [{i}/{total}] {customer.name} ({customer_code})"
                    )
                )
                success_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ [{i}/{total}] {customer.name} - خطأ: {str(e)}"
                    )
                )
                error_count += 1

        # النتيجة النهائية
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(f"\n✅ تم إنشاء/تحديث {success_count} حساب بنجاح")
        )

        if skip_count > 0:
            self.stdout.write(
                self.style.WARNING(f"⏭️  تم تخطي {skip_count} حساب موجود مسبقاً")
            )

        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ فشل {error_count} حساب"))

        self.stdout.write("\n")
