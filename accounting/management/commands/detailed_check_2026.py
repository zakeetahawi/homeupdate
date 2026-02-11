"""
Management command لفحص تفصيلي لقيود طلبات 2026
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q, Count, F
from django.utils import timezone
from datetime import datetime
from orders.models import Order, Payment, PaymentAllocation
from accounting.models import Transaction, TransactionLine, Account


class Command(BaseCommand):
    help = 'فحص تفصيلي للقيود المالية لطلبات 2026'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 120)
        self.stdout.write("🔍 فحص تفصيلي للقيود المالية لطلبات 2026")
        self.stdout.write("=" * 120)

        # جلب طلبات 2026
        year_2026_start = timezone.make_aware(datetime(2026, 1, 1))
        orders_2026 = Order.objects.filter(
            created_at__gte=year_2026_start,
            final_price__gt=0
        ).select_related('customer').order_by('id')

        total_orders = orders_2026.count()
        self.stdout.write(f"\nإجمالي طلبات 2026 النشطة (بمبلغ > 0): {total_orders:,}\n")

        if total_orders == 0:
            self.stdout.write(self.style.WARNING("\n⚠️  لا توجد طلبات نشطة"))
            return

        # التحليل التفصيلي
        self.detailed_analysis(orders_2026)

    def detailed_analysis(self, orders):
        """تحليل تفصيلي"""
        
        stats = {
            'total_orders': 0,
            'total_amount': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'with_transactions': 0,
            'with_balanced_transactions': 0,
            'with_payments': 0,
            'with_customer_account_debit': 0,
            'with_revenue_credit': 0,
            'fully_correct': 0,
        }

        issues = []

        self.stdout.write("📊 جاري الفحص التفصيلي...\n")
        
        for order in orders[:100]:  # فحص أول 100 طلب للسرعة
            stats['total_orders'] += 1
            stats['total_amount'] += order.final_price_after_discount
            stats['total_paid'] += order.paid_amount or Decimal('0.00')

            order_issues = []
            
            # 1. فحص وجود حساب العميل
            if not hasattr(order.customer, 'accounting_account'):
                order_issues.append("لا يوجد حساب للعميل")
                continue

            customer_account = order.customer.accounting_account

            # 2. فحص المعاملات
            transactions = Transaction.objects.filter(
                Q(order=order) |
                Q(description__icontains=f'طلب #{order.id}')
            )

            if not transactions.exists():
                order_issues.append("لا توجد معاملات محاسبية")
            else:
                stats['with_transactions'] += 1
                
                # فحص تفصيلي للمعاملات
                for trans in transactions:
                    # التوازن
                    total_debit = trans.lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
                    total_credit = trans.lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
                    
                    if total_debit == total_credit:
                        stats['with_balanced_transactions'] += 1
                    else:
                        order_issues.append(f"معاملة {trans.id} غير متوازنة: مدين={total_debit}, دائن={total_credit}")

                    # فحص حساب العميل (مدين)
                    customer_debit = trans.lines.filter(
                        account=customer_account,
                        debit__gt=0
                    ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

                    if customer_debit > 0:
                        stats['with_customer_account_debit'] += 1
                    else:
                        order_issues.append(f"لا يوجد مدين لحساب العميل في المعاملة {trans.id}")

                    # فحص حساب الإيرادات (دائن)
                    revenue_lines = trans.lines.filter(
                        account__account_type__category='revenue',
                        credit__gt=0
                    )

                    if revenue_lines.exists():
                        stats['with_revenue_credit'] += 1
                    else:
                        order_issues.append(f"لا يوجد دائن لحساب إيرادات في المعاملة {trans.id}")

            # 3. فحص الدفعات
            payments = Payment.objects.filter(order=order)
            
            if payments.exists():
                stats['with_payments'] += 1
                
                # فحص سجلات الدفع
                for payment in payments:
                    # فحص وجود معاملة للدفعة
                    payment_trans = Transaction.objects.filter(payment=payment)
                    if not payment_trans.exists():
                        order_issues.append(f"الدفعة {payment.id} بدون معاملة محاسبية")

            # تصنيف الطلب
            if not order_issues:
                stats['fully_correct'] += 1
            else:
                issues.append({
                    'order_id': order.id,
                    'customer': order.customer.name,
                    'amount': order.final_price_after_discount,
                    'paid': order.paid_amount,
                    'issues': order_issues
                })

        # عرض النتائج
        self.display_detailed_results(stats, issues)

    def display_detailed_results(self, stats, issues):
        """عرض النتائج التفصيلية"""
        
        self.stdout.write("\n" + "=" * 120)
        self.stdout.write("📊 نتائج الفحص التفصيلي")
        self.stdout.write("=" * 120)

        # الإحصائيات
        self.stdout.write(f"\n📈 الإحصائيات الشاملة:")
        self.stdout.write("-" * 120)
        self.stdout.write(f"  إجمالي الطلبات المفحوصة: {stats['total_orders']:,}")
        self.stdout.write(f"  إجمالي قيمة الطلبات: {stats['total_amount']:,.2f} ج.م")
        self.stdout.write(f"  إجمالي المدفوع: {stats['total_paid']:,.2f} ج.م")
        self.stdout.write(f"  المتبقي: {stats['total_amount'] - stats['total_paid']:,.2f} ج.م")
        
        self.stdout.write(f"\n📊 القيود المحاسبية:")
        self.stdout.write("-" * 120)
        self.stdout.write(f"  طلبات لها معاملات: {stats['with_transactions']:,} "
                         f"({stats['with_transactions']/stats['total_orders']*100:.1f}%)")
        self.stdout.write(f"  معاملات متوازنة: {stats['with_balanced_transactions']:,} "
                         f"({stats['with_balanced_transactions']/max(stats['total_orders'], 1)*100:.1f}%)")
        self.stdout.write(f"  قيود بمدين لحساب العميل: {stats['with_customer_account_debit']:,} "
                         f"({stats['with_customer_account_debit']/max(stats['total_orders'], 1)*100:.1f}%)")
        self.stdout.write(f"  قيود بدائن لحساب الإيرادات: {stats['with_revenue_credit']:,} "
                         f"({stats['with_revenue_credit']/max(stats['total_orders'], 1)*100:.1f}%)")
        
        self.stdout.write(f"\n💰 الدفعات:")
        self.stdout.write("-" * 120)
        self.stdout.write(f"  طلبات لها دفعات: {stats['with_payments']:,} "
                         f"({stats['with_payments']/stats['total_orders']*100:.1f}%)")
        
        self.stdout.write(f"\n✅ النتيجة:")
        self.stdout.write("-" * 120)
        self.stdout.write(f"  طلبات صحيحة 100%: {stats['fully_correct']:,} "
                         f"({stats['fully_correct']/stats['total_orders']*100:.1f}%)")
        self.stdout.write(f"  طلبات بها مشاكل: {len(issues):,} "
                         f"({len(issues)/stats['total_orders']*100:.1f}%)")

        if len(issues) > 0:
            self.stdout.write(f"\n❌ تفاصيل المشاكل:")
            self.stdout.write("=" * 120)
            
            for item in issues[:20]:
                self.stdout.write(f"\n🔴 الطلب #{item['order_id']} - {item['customer']}")
                self.stdout.write(f"   المبلغ: {item['amount']:,.2f} ج.م | المدفوع: {item['paid']:,.2f} ج.م")
                self.stdout.write(f"   المشاكل:")
                for issue in item['issues']:
                    self.stdout.write(f"     • {issue}")
                self.stdout.write("-" * 120)

        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n🎉 جميع الطلبات المفحوصة ({stats['total_orders']:,}) لها قيود مالية صحيحة 100%!"
            ))

        self.stdout.write("\n" + "=" * 120)
