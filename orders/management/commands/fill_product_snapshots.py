"""
🛡️ ملء حقول snapshot للطلبات الموجودة
Fill product snapshot fields for existing orders to protect historical data
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from orders.models import OrderItem, DraftOrderItem


class Command(BaseCommand):
    help = '🛡️ ملء حقول snapshot لحماية البيانات التاريخية للطلبات الموجودة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم عمله بدون تطبيق التغييرات',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('🛡️ ملء حقول Snapshot لحماية البيانات التاريخية'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('⚠️ وضع التجربة - لن يتم حفظ التغييرات'))
        
        # معالجة OrderItem
        self.stdout.write('\n📦 معالجة عناصر الطلبات (OrderItem)...')
        order_items_to_update = []
        order_items_updated = 0
        order_items_missing_product = 0
        
        for item in OrderItem.objects.select_related('product').iterator(chunk_size=500):
            needs_update = False
            
            if not item.product_name_snapshot and item.product:
                item.product_name_snapshot = item.product.name
                needs_update = True
            
            if not item.product_code_snapshot and item.product:
                item.product_code_snapshot = (
                    getattr(item.product, 'code', '') or 
                    getattr(item.product, 'sku', '')
                )
                needs_update = True
            
            if needs_update:
                if not dry_run:
                    order_items_to_update.append(item)
                order_items_updated += 1
                
                # Bulk update كل 500 عنصر
                if len(order_items_to_update) >= 500:
                    with transaction.atomic():
                        OrderItem.objects.bulk_update(
                            order_items_to_update,
                            ['product_name_snapshot', 'product_code_snapshot'],
                            batch_size=500
                        )
                    order_items_to_update.clear()
                    self.stdout.write(f'  ✅ تم تحديث {order_items_updated} عنصر...')
            
            elif not item.product:
                order_items_missing_product += 1
        
        # تحديث العناصر المتبقية
        if order_items_to_update and not dry_run:
            with transaction.atomic():
                OrderItem.objects.bulk_update(
                    order_items_to_update,
                    ['product_name_snapshot', 'product_code_snapshot'],
                    batch_size=500
                )
        
        # معالجة DraftOrderItem
        self.stdout.write('\n📝 معالجة عناصر المسودات (DraftOrderItem)...')
        draft_items_to_update = []
        draft_items_updated = 0
        draft_items_missing_product = 0
        
        for item in DraftOrderItem.objects.select_related('product').iterator(chunk_size=500):
            needs_update = False
            
            if not item.product_name_snapshot and item.product:
                item.product_name_snapshot = item.product.name
                needs_update = True
            
            if not item.product_code_snapshot and item.product:
                item.product_code_snapshot = (
                    getattr(item.product, 'code', '') or 
                    getattr(item.product, 'sku', '')
                )
                needs_update = True
            
            if needs_update:
                if not dry_run:
                    draft_items_to_update.append(item)
                draft_items_updated += 1
                
                # Bulk update كل 500 عنصر
                if len(draft_items_to_update) >= 500:
                    with transaction.atomic():
                        DraftOrderItem.objects.bulk_update(
                            draft_items_to_update,
                            ['product_name_snapshot', 'product_code_snapshot'],
                            batch_size=500
                        )
                    draft_items_to_update.clear()
                    self.stdout.write(f'  ✅ تم تحديث {draft_items_updated} عنصر...')
            
            elif not item.product:
                draft_items_missing_product += 1
        
        # تحديث العناصر المتبقية
        if draft_items_to_update and not dry_run:
            with transaction.atomic():
                DraftOrderItem.objects.bulk_update(
                    draft_items_to_update,
                    ['product_name_snapshot', 'product_code_snapshot'],
                    batch_size=500
                )
        
        # عرض النتائج
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ النتائج:'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'📦 عناصر الطلبات (OrderItem):')
        self.stdout.write(f'   ✅ تم تحديث: {order_items_updated} عنصر')
        if order_items_missing_product > 0:
            self.stdout.write(self.style.WARNING(
                f'   ⚠️ عناصر بدون منتج: {order_items_missing_product}'
            ))
        
        self.stdout.write(f'\n📝 عناصر المسودات (DraftOrderItem):')
        self.stdout.write(f'   ✅ تم تحديث: {draft_items_updated} عنصر')
        if draft_items_missing_product > 0:
            self.stdout.write(self.style.WARNING(
                f'   ⚠️ عناصر بدون منتج: {draft_items_missing_product}'
            ))
        
        if dry_run:
            self.stdout.write('\n' + self.style.NOTICE('⚠️ هذه تجربة - لم يتم حفظ أي تغييرات'))
            self.stdout.write(self.style.NOTICE('   قم بتشغيل الأمر بدون --dry-run للتطبيق الفعلي'))
        else:
            self.stdout.write('\n' + self.style.SUCCESS('🎉 تم الانتهاء بنجاح!'))
        
        self.stdout.write('\n' + '=' * 80)
