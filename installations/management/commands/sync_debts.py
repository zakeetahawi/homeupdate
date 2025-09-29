"""
أمر إدارة لمزامنة المديونيات مع الطلبات بشكل دوري
"""

from django.core.management.base import BaseCommand
from django.db.models import F, Sum
from django.db import models
from orders.models import Order
from installations.models import CustomerDebt
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'مزامنة المديونيات مع الطلبات الحالية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='تشغيل تجريبي بدون حفظ التغييرات',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل أكثر',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🧪 تشغيل تجريبي - لن يتم حفظ التغييرات'))
        
        self.stdout.write('🔄 بدء مزامنة المديونيات...')
        
        # إحصائيات قبل المزامنة
        before_stats = self.get_debt_stats()
        
        # مزامنة المديونيات الجديدة
        new_debts = self.sync_new_debts(dry_run, verbose)
        
        # تحديث المديونيات الموجودة
        updated_debts = self.update_existing_debts(dry_run, verbose)
        
        # تحديث المديونيات المدفوعة
        paid_debts = self.mark_paid_debts(dry_run, verbose)
        
        # إحصائيات بعد المزامنة
        after_stats = self.get_debt_stats()
        
        # عرض النتائج
        self.display_results(before_stats, after_stats, new_debts, updated_debts, paid_debts)

    def get_debt_stats(self):
        """الحصول على إحصائيات المديونيات"""
        return {
            'total_debts': CustomerDebt.objects.filter(is_paid=False).count(),
            'total_amount': CustomerDebt.objects.filter(is_paid=False).aggregate(
                total=Sum('debt_amount')
            )['total'] or 0,
            'paid_debts': CustomerDebt.objects.filter(is_paid=True).count(),
        }

    def sync_new_debts(self, dry_run, verbose):
        """مزامنة المديونيات الجديدة"""
        # البحث عن الطلبات التي عليها مديونية وليس لها سجل مديونية
        debt_orders = Order.objects.filter(
            total_amount__gt=F('paid_amount')
        ).annotate(
            debt_amount=F('total_amount') - F('paid_amount')
        ).exclude(
            customerdebt__isnull=False
        )
        
        new_count = 0
        for order in debt_orders:
            debt_amount = float(order.debt_amount)
            
            if verbose:
                self.stdout.write(f'📝 إنشاء مديونية جديدة للطلب {order.order_number} - {debt_amount:.2f} ج.م')
            
            if not dry_run:
                CustomerDebt.objects.create(
                    customer=order.customer,
                    order=order,
                    debt_amount=debt_amount,
                    notes=f'مديونية تلقائية للطلب {order.order_number} - مزامنة {timezone.now().strftime("%Y-%m-%d")}',
                    is_paid=False,
                )
            
            new_count += 1
        
        return new_count

    def update_existing_debts(self, dry_run, verbose):
        """تحديث المديونيات الموجودة"""
        updated_count = 0
        
        # البحث عن المديونيات غير المدفوعة التي تحتاج تحديث
        existing_debts = CustomerDebt.objects.filter(is_paid=False).select_related('order')
        
        for debt in existing_debts:
            current_debt = float(debt.order.total_amount - debt.order.paid_amount)
            old_debt = float(debt.debt_amount)
            
            if abs(current_debt - old_debt) > 0.01:  # تغيير في المبلغ
                if verbose:
                    self.stdout.write(
                        f'🔄 تحديث مديونية الطلب {debt.order.order_number} من {old_debt:.2f} إلى {current_debt:.2f} ج.م'
                    )
                
                if not dry_run:
                    debt.debt_amount = current_debt
                    debt.updated_at = timezone.now()
                    debt.notes += f' - تحديث تلقائي {timezone.now().strftime("%Y-%m-%d %H:%M")}'
                    debt.save()
                
                updated_count += 1
        
        return updated_count

    def mark_paid_debts(self, dry_run, verbose):
        """تحديث المديونيات المدفوعة"""
        # البحث عن المديونيات غير المدفوعة للطلبات المدفوعة كاملاً
        paid_orders_debts = CustomerDebt.objects.filter(
            is_paid=False,
            order__total_amount__lte=F('order__paid_amount')
        )
        
        paid_count = 0
        for debt in paid_orders_debts:
            if verbose:
                self.stdout.write(f'💰 تحديث مديونية الطلب {debt.order.order_number} إلى مدفوعة')
            
            if not dry_run:
                debt.is_paid = True
                debt.payment_date = timezone.now()
                debt.notes += f' - تم الدفع تلقائياً في المزامنة {timezone.now().strftime("%Y-%m-%d %H:%M")}'
                debt.save()
            
            paid_count += 1
        
        return paid_count

    def display_results(self, before_stats, after_stats, new_debts, updated_debts, paid_debts):
        """عرض نتائج المزامنة"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📊 نتائج المزامنة:')
        self.stdout.write('='*60)
        
        self.stdout.write(f'✅ مديونيات جديدة: {new_debts}')
        self.stdout.write(f'🔄 مديونيات محدثة: {updated_debts}')
        self.stdout.write(f'💰 مديونيات مدفوعة: {paid_debts}')
        
        self.stdout.write('\n📈 الإحصائيات:')
        self.stdout.write(f'قبل المزامنة: {before_stats["total_debts"]} مديونية بمبلغ {before_stats["total_amount"]:.2f} ج.م')
        self.stdout.write(f'بعد المزامنة: {after_stats["total_debts"]} مديونية بمبلغ {after_stats["total_amount"]:.2f} ج.م')
        
        change_in_count = after_stats["total_debts"] - before_stats["total_debts"]
        change_in_amount = after_stats["total_amount"] - before_stats["total_amount"]
        
        if change_in_count != 0:
            self.stdout.write(f'التغيير في العدد: {change_in_count:+d}')
        if abs(change_in_amount) > 0.01:
            self.stdout.write(f'التغيير في المبلغ: {change_in_amount:+.2f} ج.م')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 تمت المزامنة بنجاح!'))
