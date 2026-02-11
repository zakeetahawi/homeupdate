"""
التحقق من دقة أرصدة العملاء
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal
from accounting.models import CustomerFinancialSummary
from customers.models import Customer
from orders.models import Order


class Command(BaseCommand):
    help = "التحقق من دقة أرصدة العملاء ومقارنتها بالقيم المحسوبة"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إصلاح الأرصدة الخاطئة تلقائياً',
        )
        parser.add_argument(
            '--customer-id',
            type=int,
            help='فحص عميل محدد فقط',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(" التحقق من أرصدة العملاء "))
        self.stdout.write("=" * 80)

        # تحديد العملاء للفحص
        if options['customer_id']:
            customers = Customer.objects.filter(id=options['customer_id'])
        else:
            customers = Customer.objects.all()

        total_customers = customers.count()
        self.stdout.write(f"\nإجمالي العملاء: {total_customers:,}\n")

        correct = 0
        incorrect = []
        missing_summary = []

        for customer in customers:
            # الحصول على الملخص
            try:
                summary = CustomerFinancialSummary.objects.get(customer=customer)
            except CustomerFinancialSummary.DoesNotExist:
                missing_summary.append(customer)
                continue

            # حساب من الطلبات والدفعات
            orders_total = Order.objects.filter(
                customer=customer
            ).aggregate(total=Sum('final_price'))['total'] or Decimal('0')

            orders_paid = Order.objects.filter(
                customer=customer
            ).aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')

            calculated_debt = orders_total - orders_paid

            # مقارنة
            recorded_debt = summary.total_debt
            diff = abs(calculated_debt - recorded_debt)

            # اعتبر صحيح إذا الفرق أقل من 1 جنيه (للتعامل مع فروقات التقريب)
            if diff < Decimal('1.0'):
                correct += 1
            else:
                incorrect.append({
                    'customer': customer,
                    'summary': summary,
                    'calculated': calculated_debt,
                    'recorded': recorded_debt,
                    'diff': diff
                })

        # عرض النتائج
        self.stdout.write("=" * 80)
        self.stdout.write("النتائج:")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"✅ صحيحة: {correct:,}"))
        self.stdout.write(self.style.ERROR(f"❌ خاطئة: {len(incorrect):,}"))
        self.stdout.write(self.style.WARNING(f"⚠️  بدون ملخص: {len(missing_summary):,}"))

        # عرض الأرصدة الخاطئة
        if incorrect:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("الأرصدة الخاطئة:"))
            self.stdout.write("=" * 80)

            for item in incorrect[:20]:
                self.stdout.write(f"\n❌ {item['customer'].name}")
                self.stdout.write(f"   المحسوب: {item['calculated']:,.2f} ج.م")
                self.stdout.write(f"   المسجل: {item['recorded']:,.2f} ج.م")
                self.stdout.write(self.style.ERROR(f"   الفرق: {item['diff']:,.2f} ج.م"))

        # عرض العملاء بدون ملخص
        if missing_summary:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("العملاء بدون ملخص مالي:"))
            self.stdout.write("=" * 80)
            for customer in missing_summary[:10]:
                self.stdout.write(f"⚠️  {customer.name} (#{customer.id})")

        # الإصلاح التلقائي
        if options['fix']:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("بدء الإصلاح..."))
            self.stdout.write("=" * 80)

            # إنشاء ملخصات للعملاء الناقصين
            for customer in missing_summary:
                summary = CustomerFinancialSummary.objects.create(customer=customer)
                summary.refresh()
                self.stdout.write(f"✅ تم إنشاء ملخص: {customer.name}")

            # إعادة حساب الأرصدة الخاطئة
            for item in incorrect:
                item['summary'].refresh()
                self.stdout.write(f"✅ تم تحديث: {item['customer'].name}")

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ تم إصلاح {len(missing_summary) + len(incorrect)} رصيد"
            ))

        # الإحصائيات النهائية
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("الإحصائيات:")
        self.stdout.write("=" * 80)
        
        accuracy = (correct / total_customers * 100) if total_customers > 0 else 0
        self.stdout.write(f"نسبة الدقة: {accuracy:.1f}%")

        if accuracy == 100:
            self.stdout.write(self.style.SUCCESS("\n🎉 جميع الأرصدة صحيحة!"))
        elif accuracy >= 95:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  {len(incorrect)} رصيد يحتاج تحديث"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"\n❌ {len(incorrect)} رصيد خاطئ - استخدم --fix للإصلاح"
            ))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ اكتمل التحقق!"))
        self.stdout.write("=" * 80)
