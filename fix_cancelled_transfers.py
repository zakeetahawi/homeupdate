#!/usr/bin/env python
"""
سكريبت إصلاح التحويلات الملغية والمرفوضة
يبحث عن جميع التحويلات التي تم إلغاؤها أو رفضها وتم خصم المخزون منها
ويقوم بإرجاع المخزون تلقائياً

الاستخدام:
python fix_cancelled_transfers.py --dry-run    # معاينة فقط بدون تطبيق
python fix_cancelled_transfers.py --apply      # تطبيق الإصلاح
"""
import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import StockTransfer, StockTransaction, StockTransferItem
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

User = get_user_model()


def find_problematic_transfers():
    """البحث عن التحويلات التي تحتاج إصلاح"""
    print("\n" + "="*80)
    print("🔍 البحث عن التحويلات الملغية/المرفوضة التي تحتاج إصلاح...")
    print("="*80)
    
    # البحث عن التحويلات الملغية أو المرفوضة
    cancelled_transfers = StockTransfer.objects.filter(
        Q(status='cancelled') | Q(status='rejected')
    ).select_related('from_warehouse', 'to_warehouse', 'approved_by').prefetch_related(
        'items__product'
    ).order_by('created_at')
    
    print(f"\n📊 عدد التحويلات الملغية/المرفوضة: {cancelled_transfers.count()}")
    
    problematic_transfers = []
    
    for transfer in cancelled_transfers:
        # التحقق من أنه تمت الموافقة على التحويل (أي تم خصم المخزون)
        if not transfer.approved_at:
            # لم تتم الموافقة، لا حاجة للإصلاح
            continue
        
        # التحقق من وجود حركات خصم للتحويل
        outgoing_transactions = StockTransaction.objects.filter(
            reference=transfer.transfer_number,
            transaction_type='out',
            reason='transfer'
        )
        
        if not outgoing_transactions.exists():
            # لا توجد حركات خصم، لا حاجة للإصلاح
            continue
        
        # التحقق من عدم وجود حركات إرجاع
        return_transactions = StockTransaction.objects.filter(
            reference=transfer.transfer_number,
            transaction_type='in',
            reason='return'
        )
        
        if return_transactions.exists():
            # تم الإرجاع بالفعل
            continue
        
        # هذا التحويل يحتاج إصلاح
        problematic_transfers.append({
            'transfer': transfer,
            'outgoing_count': outgoing_transactions.count(),
            'items_count': transfer.items.count()
        })
    
    return problematic_transfers


def display_transfer_details(transfer_data):
    """عرض تفاصيل التحويل"""
    transfer = transfer_data['transfer']
    
    print(f"\n{'─'*80}")
    print(f"📦 رقم التحويل: {transfer.transfer_number}")
    print(f"📅 تاريخ الإنشاء: {transfer.created_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"📍 من: {transfer.from_warehouse.name} ➡️ إلى: {transfer.to_warehouse.name}")
    print(f"⚠️  الحالة: {transfer.get_status_display()}")
    if transfer.approved_at:
        print(f"✅ تمت الموافقة: {transfer.approved_at.strftime('%Y-%m-%d %H:%M')} بواسطة {transfer.approved_by}")
    
    print(f"\n   📋 عناصر التحويل ({transfer.items.count()}):")
    
    total_value = 0
    for item in transfer.items.all():
        # الحصول على آخر رصيد في المستودع المصدر
        last_trans = StockTransaction.objects.filter(
            product=item.product,
            warehouse=transfer.from_warehouse
        ).order_by('-transaction_date', '-id').first()
        
        current_balance = last_trans.running_balance if last_trans else 0
        
        print(f"      • {item.product.name}")
        print(f"        الكمية المفقودة: {item.quantity}")
        print(f"        الرصيد الحالي: {current_balance}")
        print(f"        سيصبح: {current_balance + item.quantity} بعد الإرجاع")


def fix_transfer(transfer_data, admin_user, dry_run=True):
    """إصلاح تحويل واحد"""
    transfer = transfer_data['transfer']
    
    if dry_run:
        return True
    
    try:
        # إرجاع المخزون لكل عنصر
        for item in transfer.items.all():
            # الحصول على آخر رصيد في المستودع المصدر
            last_transaction = StockTransaction.objects.filter(
                product=item.product, 
                warehouse=transfer.from_warehouse
            ).order_by('-transaction_date', '-id').first()

            previous_balance = last_transaction.running_balance if last_transaction else 0
            new_balance = previous_balance + item.quantity

            # إنشاء حركة مخزون لإرجاع الكمية
            StockTransaction.objects.create(
                product=item.product,
                warehouse=transfer.from_warehouse,
                transaction_type="in",
                reason="return",
                quantity=item.quantity,
                reference=transfer.transfer_number,
                transaction_date=timezone.now(),
                notes=f"إصلاح تلقائي: إرجاع بسبب {transfer.get_status_display()} التحويل {transfer.transfer_number}",
                running_balance=new_balance,
                created_by=admin_user,
            )
        
        return True
        
    except Exception as e:
        print(f"      ❌ خطأ في إصلاح التحويل: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """الدالة الرئيسية"""
    
    # التحقق من المعامل
    if len(sys.argv) < 2:
        print("\n❌ يجب تحديد وضع التشغيل:")
        print("   python fix_cancelled_transfers.py --dry-run    (معاينة فقط)")
        print("   python fix_cancelled_transfers.py --apply      (تطبيق الإصلاح)")
        sys.exit(1)
    
    mode = sys.argv[1]
    dry_run = mode == '--dry-run'
    
    if mode not in ['--dry-run', '--apply']:
        print(f"\n❌ معامل غير صحيح: {mode}")
        print("   استخدم --dry-run أو --apply")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("🔧 سكريبت إصلاح التحويلات الملغية/المرفوضة")
    print("="*80)
    
    if dry_run:
        print("⚠️  وضع المعاينة: لن يتم تطبيق التغييرات")
    else:
        print("✅ وضع التطبيق: سيتم إرجاع المخزون فعلياً")
        
        # طلب التأكيد
        confirm = input("\n⚠️  هل أنت متأكد من المتابعة؟ (نعم/لا): ")
        if confirm.lower() not in ['نعم', 'yes', 'y']:
            print("❌ تم الإلغاء")
            sys.exit(0)
    
    # البحث عن التحويلات المشكلة
    problematic_transfers = find_problematic_transfers()
    
    if not problematic_transfers:
        print("\n✅ لا توجد تحويلات تحتاج إصلاح!")
        return
    
    print(f"\n⚠️  تم العثور على {len(problematic_transfers)} تحويل يحتاج إصلاح:")
    
    # عرض التفاصيل
    for i, transfer_data in enumerate(problematic_transfers, 1):
        print(f"\n\n{'='*80}")
        print(f"التحويل {i} من {len(problematic_transfers)}")
        print(f"{'='*80}")
        display_transfer_details(transfer_data)
    
    if dry_run:
        print("\n" + "="*80)
        print("💡 هذه معاينة فقط. لتطبيق الإصلاح، استخدم:")
        print("   python fix_cancelled_transfers.py --apply")
        print("="*80)
        return
    
    # تطبيق الإصلاح
    print("\n" + "="*80)
    print("🔧 بدء عملية الإصلاح...")
    print("="*80)
    
    # الحصول على المستخدم الإداري
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("❌ لا يوجد مستخدم إداري!")
        sys.exit(1)
    
    fixed_count = 0
    failed_count = 0
    
    for i, transfer_data in enumerate(problematic_transfers, 1):
        transfer = transfer_data['transfer']
        print(f"\n[{i}/{len(problematic_transfers)}] معالجة {transfer.transfer_number}...")
        
        if fix_transfer(transfer_data, admin_user, dry_run=False):
            fixed_count += 1
            print(f"   ✅ تم الإصلاح بنجاح")
        else:
            failed_count += 1
            print(f"   ❌ فشل الإصلاح")
    
    # الملخص النهائي
    print("\n" + "="*80)
    print("📊 ملخص النتائج:")
    print("="*80)
    print(f"   ✅ تم إصلاحها: {fixed_count}")
    print(f"   ❌ فشل: {failed_count}")
    print(f"   📦 الإجمالي: {len(problematic_transfers)}")
    print("="*80)
    
    # حفظ التقرير
    report_file = f"transfer_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("تقرير إصلاح التحويلات الملغية/المرفوضة\n")
        f.write("="*80 + "\n")
        f.write(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"عدد التحويلات المصلحة: {fixed_count}\n")
        f.write(f"عدد الفشل: {failed_count}\n\n")
        
        for transfer_data in problematic_transfers:
            transfer = transfer_data['transfer']
            f.write(f"\n{transfer.transfer_number}\n")
            f.write(f"  الحالة: {transfer.get_status_display()}\n")
            f.write(f"  من: {transfer.from_warehouse.name}\n")
            f.write(f"  إلى: {transfer.to_warehouse.name}\n")
            f.write(f"  عدد العناصر: {transfer.items.count()}\n")
    
    print(f"\n💾 تم حفظ التقرير في: {report_file}")


if __name__ == '__main__':
    main()
