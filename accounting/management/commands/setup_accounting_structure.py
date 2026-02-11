"""
أمر لإنشاء البنية التحتية المحاسبية (AccountTypes والحسابات الأساسية)
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from accounting.models import Account, AccountType


class Command(BaseCommand):
    help = "إنشاء البنية التحتية المحاسبية الأساسية"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🏗️  إنشاء البنية التحتية المحاسبية...")
        )

        # إنشاء أنواع الحسابات الأساسية
        account_types = [
            {
                "code_prefix": "1",
                "name": "الأصول",
                "description": "حسابات الأصول",
                "category": "asset",
            },
            {
                "code_prefix": "11",
                "name": "الأصول المتداولة",
                "description": "أصول يمكن تحويلها لنقد خلال سنة",
                "category": "asset",
            },
            {
                "code_prefix": "12",
                "name": "الذمم المدينة",
                "description": "المستحقات على العملاء",
                "category": "asset",
            },
            {
                "code_prefix": "1200",
                "name": "حسابات العملاء",
                "description": "حسابات المدينين (العملاء)",
                "category": "asset",
            },
            {
                "code_prefix": "2",
                "name": "الخصوم",
                "description": "حسابات الخصوم",
                "category": "liability",
            },
            {
                "code_prefix": "3",
                "name": "حقوق الملكية",
                "description": "رأس المال والأرباح المحتجزة",
                "category": "equity",
            },
            {
                "code_prefix": "4",
                "name": "الإيرادات",
                "description": "حسابات الإيرادات",
                "category": "revenue",
            },
            {
                "code_prefix": "5",
                "name": "المصروفات",
                "description": "حسابات المصروفات",
                "category": "expense",
            },
        ]

        created_types = 0
        for type_data in account_types:
            account_type, created = AccountType.objects.get_or_create(
                code_prefix=type_data["code_prefix"],
                defaults={
                    "name": type_data["name"],
                    "description": type_data["description"],
                    "category": type_data["category"],
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ نوع حساب: {type_data['code_prefix']} - {type_data['name']}"
                    )
                )
                created_types += 1
            else:
                self.stdout.write(
                    f"  ⏭️  موجود مسبقاً: {type_data['code_prefix']} - {type_data['name']}"
                )

        # إنشاء الحسابات الأساسية
        accounts = [
            {
                "code": "1210",
                "name": "ذمم العملاء",
                "account_type_prefix": "1200",
                "parent": None,
                "is_active": True,
            },
            {
                "code": "1",
                "name": "الأصول",
                "account_type_prefix": "1",
                "parent": None,
                "is_active": True,
            },
            {
                "code": "11",
                "name": "الأصول المتداولة",
                "account_type_prefix": "11",
                "parent_code": "1",
                "is_active": True,
            },
            {
                "code": "12",
                "name": "الذمم المدينة",
                "account_type_prefix": "12",
                "parent_code": "11",
                "is_active": True,
            },
        ]

        created_accounts = 0
        for acc_data in accounts:
            # الحصول على نوع الحساب
            account_type = AccountType.objects.filter(
                code_prefix=acc_data["account_type_prefix"]
            ).first()

            if not account_type:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ نوع حساب {acc_data['account_type_prefix']} غير موجود"
                    )
                )
                continue

            # الحصول على الحساب الأب إذا وجد
            parent = None
            if acc_data.get("parent_code"):
                parent = Account.objects.filter(code=acc_data["parent_code"]).first()

            # إنشاء الحساب - مع معالجة حالة وجود اسم مكرر بكود مختلف
            existing_by_name = Account.objects.filter(
                name=acc_data["name"], is_customer_account=False
            ).first()
            existing_by_code = Account.objects.filter(code=acc_data["code"]).first()

            if existing_by_code:
                self.stdout.write(
                    f"  ⏭️  موجود مسبقاً: {existing_by_code.code} - {existing_by_code.name}"
                )
                continue
            elif existing_by_name:
                self.stdout.write(
                    f"  ⏭️  موجود بكود مختلف: {existing_by_name.code} - {existing_by_name.name} (تخطي إنشاء {acc_data['code']})"
                )
                continue

            try:
                account = Account.objects.create(
                    code=acc_data["code"],
                    name=acc_data["name"],
                    account_type=account_type,
                    parent=parent,
                    is_active=acc_data["is_active"],
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ حساب: {acc_data['code']} - {acc_data['name']}"
                    )
                )
                created_accounts += 1
            except IntegrityError as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  تخطي {acc_data['code']} - {acc_data['name']}: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ اكتمل! تم إنشاء {created_types} نوع حساب و{created_accounts} حساب"
            )
        )
