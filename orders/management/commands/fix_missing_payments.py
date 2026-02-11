"""
أمر لإصلاح الطلبات التي لديها paid_amount لكن لا توجد Payment objects
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from orders.models import Order, Payment


class Command(BaseCommand):
    help = "إصلاح الطلبات التي لديها paid_amount لكن لا توجد Payment objects"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض فقط بدون تطبيق التغييرات",
        )
        parser.add_argument(
            "--order",
            type=str,
            help="رقم طلب محدد للإصلاح",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        order_number = options.get("order")

        self.stdout.write(
            self.style.SUCCESS(
                "🔍 البحث عن طلبات بها paid_amount لكن بدون Payment objects..."
            )
        )

        # جلب الطلبات
        if order_number:
            orders = Order.objects.filter(order_number=order_number)
        else:
            orders = Order.objects.filter(paid_amount__gt=0)

        problematic_orders = []

        for order in orders:
            # حساب إجمالي Payment objects
            real_payments = (
                Payment.objects.filter(order=order).aggregate(total=Sum("amount"))[
                    "total"
                ]
                or Decimal("0")
            )

            # إذا كان هناك فرق
            difference = order.paid_amount - real_payments
            if difference > Decimal("0.01"):  # تجاهل الفروق الصغيرة جداً
                problematic_orders.append(
                    {
                        "order": order,
                        "paid_amount": order.paid_amount,
                        "real_payments": real_payments,
                        "difference": difference,
                    }
                )

        if not problematic_orders:
            self.stdout.write(self.style.SUCCESS("✅ لا توجد طلبات تحتاج إصلاح!"))
            return

        self.stdout.write(
            self.style.WARNING(
                f"\n📋 وجدت {len(problematic_orders)} طلب تحتاج إصلاح:\n"
            )
        )

        for item in problematic_orders:
            order = item["order"]
            self.stdout.write(
                f"  • {order.order_number}:"
                f" paid_amount={item['paid_amount']:.2f},"
                f" Payments={item['real_payments']:.2f},"
                f" فرق={item['difference']:.2f}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n⚠️  وضع العرض فقط - لن يتم تطبيق التغييرات")
            )
            return

        # تأكيد من المستخدم
        self.stdout.write(
            self.style.WARNING(
                f"\n⚠️  سيتم إنشاء Payment records للطلبات المذكورة أعلاه"
            )
        )
        confirm = input("هل تريد المتابعة؟ (yes/no): ")

        if confirm.lower() not in ["yes", "y", "نعم"]:
            self.stdout.write(self.style.ERROR("❌ تم الإلغاء"))
            return

        # إصلاح الطلبات
        fixed_count = 0
        for item in problematic_orders:
            order = item["order"]
            difference = item["difference"]

            try:
                # إنشاء Payment record
                payment = Payment.objects.create(
                    order=order,
                    amount=difference,
                    payment_method="تصحيح تلقائي",
                    payment_date=order.order_date,  # استخدام تاريخ الطلب
                    notes=f"دفعة مسجلة تلقائياً لتصحيح paid_amount. تم الإنشاء في {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    created_by=order.created_by,  # استخدام منشئ الطلب
                )

                # التحقق من التحديث
                order.refresh_from_db()
                new_real_payments = (
                    Payment.objects.filter(order=order).aggregate(total=Sum("amount"))[
                        "total"
                    ]
                    or Decimal("0")
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ {order.order_number}: أُنشئت دفعة #{payment.id} بقيمة {difference:.2f}"
                        f" (إجمالي جديد: {new_real_payments:.2f})"
                    )
                )
                fixed_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ خطأ في {order.order_number}: {str(e)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ تم إصلاح {fixed_count} من {len(problematic_orders)} طلب"
            )
        )

        # تحديث الملخصات المالية للعملاء المتأثرين
        self.stdout.write(
            self.style.SUCCESS("\n🔄 تحديث الملخصات المالية للعملاء...")
        )
        from accounting.models import CustomerFinancialSummary

        affected_customers = set([item["order"].customer for item in problematic_orders])
        for customer in affected_customers:
            try:
                summary, _ = CustomerFinancialSummary.objects.get_or_create(
                    customer=customer
                )
                summary.refresh()
                self.stdout.write(f"  ✅ تم تحديث ملخص {customer.name}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ خطأ في تحديث {customer.name}: {str(e)}")
                )

        self.stdout.write(self.style.SUCCESS("\n✅ اكتمل الإصلاح!"))
