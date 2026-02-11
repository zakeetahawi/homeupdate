"""
Management command للتحقق من القيود المالية للطلبات من 2026
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import datetime, date
from orders.models import Order, Payment
from accounting.models import Transaction, TransactionLine, Account


class Command(BaseCommand):
    help = 'فحص القيود المالية لطلبات 2026'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إنشاء القيود الناقصة تلقائياً',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("🔍 فحص القيود المالية لطلبات 2026")
        self.stdout.write("=" * 100)

        # جلب طلبات 2026
        year_2026_start = timezone.make_aware(datetime(2026, 1, 1))
        orders_2026 = Order.objects.filter(
            created_at__gte=year_2026_start
        ).select_related('customer').order_by('id')

        total_orders = orders_2026.count()
        self.stdout.write(f"\nإجمالي طلبات 2026: {total_orders:,}")

        if total_orders == 0:
            self.stdout.write(self.style.WARNING("\n⚠️  لا توجد طلبات من 2026"))
            return

        # تحليل الطلبات
        self.analyze_orders(orders_2026, options.get('fix', False))

    def analyze_orders(self, orders, fix=False):
        """تحليل الطلبات"""
        
        issues = {
            'no_transactions': [],
            'unbalanced_transactions': [],
            'no_payments': [],
            'amount_mismatch': [],
            'no_customer_account': [],
        }

        stats = {
            'total': 0,
            'with_transactions': 0,
            'with_payments': 0,
            'correct': 0,
        }

        self.stdout.write("\n📊 جاري الفحص...")
        self.stdout.write("-" * 100)

        for order in orders:
            stats['total'] += 1
            has_issues = False

            # 1. فحص وجود حساب للعميل
            if not hasattr(order.customer, 'accounting_account') or order.customer.accounting_account is None:
                issues['no_customer_account'].append({
                    'order_id': order.id,
                    'customer': order.customer.name,
                    'amount': order.final_price_after_discount
                })
                has_issues = True
                continue

            # 2. فحص وجود معاملات محاسبية
            transactions = Transaction.objects.filter(
                Q(description__icontains=f'طلب #{order.id}') |
                Q(description__icontains=f'Order #{order.id}') |
                Q(reference__icontains=str(order.id)) |
                Q(order=order)
            )

            if not transactions.exists():
                issues['no_transactions'].append({
                    'order_id': order.id,
                    'date': order.created_at,
                    'customer': order.customer.name,
                    'amount': order.final_price_after_discount,
                    'paid': order.paid_amount
                })
                has_issues = True
            else:
                stats['with_transactions'] += 1
                
                # 3. فحص توازن المعاملات
                for trans in transactions:
                    total_debit = trans.lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
                    total_credit = trans.lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
                    
                    if total_debit != total_credit:
                        issues['unbalanced_transactions'].append({
                            'order_id': order.id,
                            'trans_id': trans.id,
                            'debit': total_debit,
                            'credit': total_credit,
                            'diff': total_debit - total_credit
                        })
                        has_issues = True

            # 4. فحص الدفعات
            payments = Payment.objects.filter(order=order)
            if payments.exists():
                stats['with_payments'] += 1
                
                # فحص تطابق المبالغ
                total_payments = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                if abs(total_payments - order.paid_amount) > Decimal('0.01'):
                    issues['amount_mismatch'].append({
                        'order_id': order.id,
                        'order_paid': order.paid_amount,
                        'payments_total': total_payments,
                        'diff': order.paid_amount - total_payments
                    })
                    has_issues = True
            elif order.paid_amount > 0:
                issues['no_payments'].append({
                    'order_id': order.id,
                    'customer': order.customer.name,
                    'paid_amount': order.paid_amount
                })
                has_issues = True

            if not has_issues:
                stats['correct'] += 1

        # عرض النتائج
        self.display_results(issues, stats)

        # الإصلاح إذا طُلب
        if fix and any(len(v) > 0 for v in issues.values()):
            self.fix_issues(issues)

    def display_results(self, issues, stats):
        """عرض النتائج"""
        
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("📊 نتائج الفحص")
        self.stdout.write("=" * 100)

        # الإحصائيات
        self.stdout.write(f"\n📈 الإحصائيات:")
        self.stdout.write(f"  إجمالي الطلبات: {stats['total']:,}")
        self.stdout.write(f"  طلبات لها معاملات: {stats['with_transactions']:,}")
        self.stdout.write(f"  طلبات لها دفعات: {stats['with_payments']:,}")
        self.stdout.write(f"  طلبات صحيحة: {stats['correct']:,}")

        total_issues = sum(len(v) for v in issues.values())
        
        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS("\n🎉 جميع الطلبات لها قيود مالية صحيحة!"))
            return

        self.stdout.write(self.style.ERROR(f"\n❌ وجدت {total_issues} مشكلة"))

        # 1. طلبات بدون معاملات
        if issues['no_transactions']:
            self.stdout.write("\n" + "-" * 100)
            self.stdout.write(f"❌ طلبات بدون معاملات محاسبية: {len(issues['no_transactions'])}")
            self.stdout.write("-" * 100)
            self.stdout.write(
                f"{'ID الطلب':<10} | {'التاريخ':<12} | {'العميل':<30} | "
                f"{'المبلغ':>15} | {'المدفوع':>15}"
            )
            self.stdout.write("-" * 100)
            
            for item in issues['no_transactions'][:20]:
                self.stdout.write(
                    f"{item['order_id']:<10} | {str(item['date'])[:10]:<12} | "
                    f"{item['customer'][:30]:<30} | "
                    f"{item['amount']:>15,.2f} | {item['paid']:>15,.2f}"
                )

        # 2. معاملات غير متوازنة
        if issues['unbalanced_transactions']:
            self.stdout.write("\n" + "-" * 100)
            self.stdout.write(f"❌ معاملات غير متوازنة: {len(issues['unbalanced_transactions'])}")
            self.stdout.write("-" * 100)
            
            for item in issues['unbalanced_transactions'][:10]:
                self.stdout.write(
                    f"  الطلب {item['order_id']} | المعاملة {item['trans_id']} | "
                    f"مدين: {item['debit']:,.2f} | دائن: {item['credit']:,.2f} | "
                    f"الفرق: {item['diff']:,.2f}"
                )

        # 3. طلبات بدون دفعات
        if issues['no_payments']:
            self.stdout.write("\n" + "-" * 100)
            self.stdout.write(f"❌ طلبات بدون دفعات (لكن paid_amount > 0): {len(issues['no_payments'])}")
            self.stdout.write("-" * 100)
            
            for item in issues['no_payments'][:10]:
                self.stdout.write(
                    f"  الطلب {item['order_id']} | العميل: {item['customer']} | "
                    f"المبلغ المدفوع: {item['paid_amount']:,.2f}"
                )

        # 4. عدم تطابق المبالغ
        if issues['amount_mismatch']:
            self.stdout.write("\n" + "-" * 100)
            self.stdout.write(f"❌ عدم تطابق المبالغ: {len(issues['amount_mismatch'])}")
            self.stdout.write("-" * 100)
            
            for item in issues['amount_mismatch'][:10]:
                self.stdout.write(
                    f"  الطلب {item['order_id']} | "
                    f"paid_amount: {item['order_paid']:,.2f} | "
                    f"إجمالي الدفعات: {item['payments_total']:,.2f} | "
                    f"الفرق: {item['diff']:,.2f}"
                )

        # 5. عملاء بدون حسابات
        if issues['no_customer_account']:
            self.stdout.write("\n" + "-" * 100)
            self.stdout.write(f"❌ طلبات لعملاء بدون حسابات محاسبية: {len(issues['no_customer_account'])}")
            self.stdout.write("-" * 100)
            
            for item in issues['no_customer_account'][:10]:
                self.stdout.write(
                    f"  الطلب {item['order_id']} | العميل: {item['customer']} | "
                    f"المبلغ: {item['amount']:,.2f}"
                )

        self.stdout.write("\n" + "=" * 100)

    def fix_issues(self, issues):
        """محاولة إصلاح المشاكل"""
        self.stdout.write("\n🔧 جاري محاولة الإصلاح...")
        
        # إصلاح العملاء بدون حسابات
        if issues['no_customer_account']:
            self.stdout.write(f"\n⚠️  يجب إنشاء حسابات للعملاء يدوياً")
            self.stdout.write(f"   استخدم: python manage.py create_customer_accounts")

        # إصلاح الطلبات بدون معاملات
        if issues['no_transactions']:
            self.stdout.write(f"\n⚠️  يجب إنشاء المعاملات المحاسبية يدوياً")
            self.stdout.write(f"   استخدم signals أو أعد حفظ الطلبات")

        # إصلاح الطلبات بدون دفعات
        if issues['no_payments']:
            self.stdout.write(f"\n⚠️  يجب إنشاء سجلات الدفعات يدوياً")

        self.stdout.write("\n⚠️  للحصول على أفضل النتائج، راجع البيانات يدوياً")
