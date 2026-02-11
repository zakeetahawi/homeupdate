"""
فحص القيود المعلقة (Draft Transactions)
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal
from accounting.models import Transaction


class Command(BaseCommand):
    help = "فحص جميع القيود بحالة 'مسودة' والتحقق من توازنها"

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto-post',
            action='store_true',
            help='ترحيل القيود المتوازنة تلقائياً',
        )
        parser.add_argument(
            '--delete-unbalanced',
            action='store_true',
            help='حذف القيود غير المتوازنة (خطير!)',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(" فحص القيود المعلقة "))
        self.stdout.write("=" * 80)

        # جلب جميع القيود المعلقة
        draft_trans = Transaction.objects.filter(status='draft')
        total = draft_trans.count()

        self.stdout.write(f"\nإجمالي القيود المعلقة: {total}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ لا توجد قيود معلقة!"))
            return

        # تصنيف القيود
        balanced = []
        unbalanced = []
        empty = []

        for trans in draft_trans:
            lines_count = trans.lines.count()
            
            if lines_count == 0:
                empty.append(trans)
                continue

            total_debit = trans.lines.aggregate(
                total=Sum('debit')
            )['total'] or Decimal('0')
            
            total_credit = trans.lines.aggregate(
                total=Sum('credit')
            )['total'] or Decimal('0')

            if total_debit == total_credit and total_debit > 0:
                balanced.append((trans, total_debit))
            else:
                unbalanced.append((trans, total_debit, total_credit))

        # عرض التصنيف
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("التصنيف:")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"✅ متوازنة: {len(balanced)}"))
        self.stdout.write(self.style.ERROR(f"❌ غير متوازنة: {len(unbalanced)}"))
        self.stdout.write(self.style.WARNING(f"⚠️  فارغة: {len(empty)}"))

        # عرض القيود المتوازنة
        if balanced:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS("القيود المتوازنة (جاهزة للترحيل):"))
            self.stdout.write("=" * 80)
            for trans, amount in balanced[:10]:
                self.stdout.write(f"\n✅ المعاملة #{trans.id}")
                self.stdout.write(f"   النوع: {trans.get_transaction_type_display()}")
                self.stdout.write(f"   التاريخ: {trans.date}")
                self.stdout.write(f"   المبلغ: {amount:,.2f} ج.م")
                self.stdout.write(f"   البيان: {trans.description[:60]}...")

        # عرض القيود غير المتوازنة
        if unbalanced:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("القيود غير المتوازنة:"))
            self.stdout.write("=" * 80)
            for trans, debit, credit in unbalanced[:10]:
                diff = abs(debit - credit)
                self.stdout.write(f"\n❌ المعاملة #{trans.id}")
                self.stdout.write(f"   النوع: {trans.get_transaction_type_display()}")
                self.stdout.write(f"   التاريخ: {trans.date}")
                self.stdout.write(f"   المدين: {debit:,.2f} ج.م")
                self.stdout.write(f"   الدائن: {credit:,.2f} ج.م")
                self.stdout.write(self.style.ERROR(f"   الفرق: {diff:,.2f} ج.م"))

        # عرض القيود الفارغة
        if empty:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("القيود الفارغة (بدون بنود):"))
            self.stdout.write("=" * 80)
            for trans in empty[:10]:
                self.stdout.write(f"\n⚠️  المعاملة #{trans.id}")
                self.stdout.write(f"   النوع: {trans.get_transaction_type_display()}")
                self.stdout.write(f"   التاريخ: {trans.date}")
                self.stdout.write(f"   البيان: {trans.description[:60]}...")

        # الترحيل التلقائي
        if options['auto_post'] and balanced:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("ترحيل القيود المتوازنة..."))
            self.stdout.write("=" * 80)
            
            posted_count = 0
            for trans, _ in balanced:
                trans.status = 'posted'
                trans.save()
                posted_count += 1
                self.stdout.write(f"✅ تم ترحيل المعاملة #{trans.id}")

            self.stdout.write(self.style.SUCCESS(f"\n✅ تم ترحيل {posted_count} قيد"))

        # حذف غير المتوازنة
        if options['delete_unbalanced'] and unbalanced:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("⚠️  حذف القيود غير المتوازنة... (خطير!)"))
            self.stdout.write("=" * 80)
            
            deleted_count = 0
            for trans, _, _ in unbalanced:
                trans_id = trans.id
                trans.delete()
                deleted_count += 1
                self.stdout.write(f"❌ تم حذف المعاملة #{trans_id}")

            self.stdout.write(self.style.ERROR(f"\n❌ تم حذف {deleted_count} قيد"))

        # التوصيات
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("التوصيات:"))
        self.stdout.write("=" * 80)
        
        if balanced:
            self.stdout.write(f"• استخدم --auto-post لترحيل {len(balanced)} قيد متوازن")
        if unbalanced:
            self.stdout.write(self.style.ERROR(
                f"• راجع {len(unbalanced)} قيد غير متوازن وصححهم يدوياً"
            ))
        if empty:
            self.stdout.write(f"• احذف {len(empty)} قيد فارغ")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ اكتمل الفحص!"))
        self.stdout.write("=" * 80)
