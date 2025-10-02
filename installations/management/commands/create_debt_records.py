"""
أمر إدارة لإنشاء سجلات المديونيات للطلبات التي عليها مديونية
"""

from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone

from installations.models import CustomerDebt
from orders.models import Order


class Command(BaseCommand):
    help = "إنشاء سجلات مديونيات للطلبات التي عليها مديونية"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="تحديث السجلات الموجودة أيضاً",
        )
        parser.add_argument(
            "--min-debt",
            type=float,
            default=1.0,
            help="الحد الأدنى لمبلغ المديونية (افتراضي: 1.0)",
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 البحث عن الطلبات التي عليها مديونية...")

        # البحث عن الطلبات التي عليها مديونية
        debt_orders = (
            Order.objects.filter(total_amount__gt=F("paid_amount"))
            .annotate(debt_amount=F("total_amount") - F("paid_amount"))
            .filter(debt_amount__gte=options["min_debt"])
        )

        self.stdout.write(f"📊 تم العثور على {debt_orders.count()} طلب عليه مديونية")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for order in debt_orders:
            debt_amount = float(order.debt_amount)

            # التحقق من وجود سجل مديونية
            debt_record, created = CustomerDebt.objects.get_or_create(
                order=order,
                defaults={
                    "customer": order.customer,
                    "debt_amount": debt_amount,
                    "notes": f"مديونية تلقائية للطلب {order.order_number}",
                    "is_paid": False,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ تم إنشاء سجل مديونية للطلب {order.order_number} - "
                        f"المبلغ: {debt_amount:.2f} ج.م"
                    )
                )
            elif options["update_existing"]:
                # تحديث المبلغ إذا تغير
                if abs(float(debt_record.debt_amount) - debt_amount) > 0.01:
                    old_amount = float(debt_record.debt_amount)
                    debt_record.debt_amount = debt_amount
                    debt_record.updated_at = timezone.now()
                    debt_record.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"🔄 تم تحديث مديونية الطلب {order.order_number} - "
                            f"من {old_amount:.2f} إلى {debt_amount:.2f} ج.م"
                        )
                    )
                else:
                    skipped_count += 1
            else:
                skipped_count += 1
                self.stdout.write(f"⏭️ تم تخطي الطلب {order.order_number} (سجل موجود)")

        # إحصائيات النتائج
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📈 ملخص العملية:")
        self.stdout.write(f"✅ سجلات جديدة: {created_count}")
        if options["update_existing"]:
            self.stdout.write(f"🔄 سجلات محدثة: {updated_count}")
        self.stdout.write(f"⏭️ سجلات متخطاة: {skipped_count}")
        self.stdout.write(f"📊 إجمالي الطلبات المعالجة: {debt_orders.count()}")

        # التحقق من المديونيات المدفوعة
        self.stdout.write("\n🔍 التحقق من المديونيات المدفوعة...")
        paid_orders = CustomerDebt.objects.filter(
            is_paid=False, order__total_amount__lte=F("order__paid_amount")
        )

        if paid_orders.exists():
            paid_count = 0
            for debt in paid_orders:
                debt.is_paid = True
                debt.payment_date = timezone.now()
                debt.notes += (
                    f' - تم الدفع تلقائياً في {timezone.now().strftime("%Y-%m-%d")}'
                )
                debt.save()
                paid_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"💰 تم تحديث حالة المديونية للطلب {debt.order.order_number} إلى مدفوعة"
                    )
                )

            self.stdout.write(f"💰 تم تحديث {paid_count} مديونية إلى حالة مدفوعة")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("🎉 تمت العملية بنجاح!"))

        # عرض إحصائيات المديونيات الحالية
        total_debts = CustomerDebt.objects.filter(is_paid=False).count()
        total_amount = (
            CustomerDebt.objects.filter(is_paid=False).aggregate(
                total=Sum("debt_amount")
            )["total"]
            or 0
        )

        self.stdout.write("\n📊 إحصائيات المديونيات الحالية:")
        self.stdout.write(f"📋 عدد المديونيات غير المدفوعة: {total_debts}")
        self.stdout.write(f"💰 إجمالي المبلغ: {total_amount:.2f} ج.م")
