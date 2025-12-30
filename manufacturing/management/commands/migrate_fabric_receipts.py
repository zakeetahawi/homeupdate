"""
أمر إدارة Django لترحيل بيانات استلام الأقمشة القديمة
يقوم بإنشاء سجلات FabricReceipt و FabricReceiptItem للعناصر المستلمة سابقاً
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from manufacturing.models import ManufacturingOrderItem, FabricReceipt, FabricReceiptItem


class Command(BaseCommand):
    help = 'ترحيل بيانات استلام الأقمشة القديمة إلى نظام FabricReceipt'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم فعله بدون تنفيذ فعلي',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # الحصول على جميع العناصر المستلمة التي ليس لها سجل FabricReceipt
        received_items = ManufacturingOrderItem.objects.filter(
            fabric_received=True
        ).select_related(
            'manufacturing_order',
            'manufacturing_order__order',
            'manufacturing_order__order__customer',
            'order_item',
            'cutting_item',
            'cutting_item__cutting_order',
            'fabric_received_by'
        )

        self.stdout.write(f'\n📊 تم العثور على {received_items.count()} عنصر مستلم\n')

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  وضع المعاينة - لن يتم حفظ أي تغييرات\n'))

        # تجميع العناصر حسب الطلب ورقم الشنطة
        receipts_to_create = {}
        
        for item in received_items:
            # مفتاح فريد لكل مجموعة استلام
            key = (
                item.manufacturing_order.id if item.manufacturing_order else None,
                item.bag_number or 'NO_BAG'
            )

            if key not in receipts_to_create:
                receipts_to_create[key] = {
                    'manufacturing_order': item.manufacturing_order,
                    'bag_number': item.bag_number or '',
                    'items': [],
                    'received_by': item.fabric_received_by,
                    'received_date': item.fabric_received_date or timezone.now(),
                    'cutting_order': item.cutting_item.cutting_order if item.cutting_item else None,
                }

            receipts_to_create[key]['items'].append(item)

        self.stdout.write(f'📦 سيتم إنشاء {len(receipts_to_create)} سجل استلام\n')

        if dry_run:
            # عرض التفاصيل فقط
            for idx, (key, data) in enumerate(receipts_to_create.items(), 1):
                mfg_order = data['manufacturing_order']
                customer_name = mfg_order.order.customer.name if mfg_order and mfg_order.order else 'غير محدد'
                
                self.stdout.write(
                    f"\n{idx}. سجل استلام:"
                    f"\n   - العميل: {customer_name}"
                    f"\n   - رقم الشنطة: {data['bag_number'] or 'غير محدد'}"
                    f"\n   - عدد العناصر: {len(data['items'])}"
                    f"\n   - المستلم: {data['received_by'].get_full_name() if data['received_by'] else 'غير محدد'}"
                )
                
                for item in data['items']:
                    self.stdout.write(f"     • {item.product_name} - {item.quantity}")

            self.stdout.write(self.style.SUCCESS('\n✅ المعاينة اكتملت. استخدم الأمر بدون --dry-run للتنفيذ الفعلي\n'))
            return

        # التنفيذ الفعلي
        created_receipts = 0
        created_items = 0

        with transaction.atomic():
            for key, data in receipts_to_create.items():
                mfg_order = data['manufacturing_order']
                
                # التحقق من عدم وجود سجل مكرر
                existing_receipt = FabricReceipt.objects.filter(
                    manufacturing_order=mfg_order,
                    bag_number=data['bag_number']
                ).first()

                if existing_receipt:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  سجل استلام موجود بالفعل للطلب {mfg_order.id if mfg_order else 'N/A'} "
                            f"والشنطة {data['bag_number']} - تخطي"
                        )
                    )
                    fabric_receipt = existing_receipt
                else:
                    # إنشاء سجل FabricReceipt
                    fabric_receipt = FabricReceipt.objects.create(
                        receipt_type='manufacturing_order',
                        order=mfg_order.order if mfg_order else None,
                        cutting_order=data['cutting_order'],
                        manufacturing_order=mfg_order,
                        bag_number=data['bag_number'],
                        received_by=data['received_by'],
                        receipt_date=data['received_date'],
                        notes='تم الترحيل من النظام القديم'
                    )
                    created_receipts += 1

                # إنشاء عناصر الاستلام
                for item in data['items']:
                    # التحقق من عدم وجود عنصر مكرر
                    if not FabricReceiptItem.objects.filter(
                        fabric_receipt=fabric_receipt,
                        order_item=item.order_item
                    ).exists():
                        FabricReceiptItem.objects.create(
                            fabric_receipt=fabric_receipt,
                            order_item=item.order_item,
                            cutting_item=item.cutting_item,
                            product_name=item.product_name,
                            quantity_received=item.quantity,
                            item_notes=item.fabric_notes or ''
                        )
                        created_items += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ اكتمل الترحيل بنجاح!'
                f'\n   - تم إنشاء {created_receipts} سجل استلام'
                f'\n   - تم إنشاء {created_items} عنصر استلام\n'
            )
        )
