from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from orders.models import Order, OrderItem
from inventory.models import Warehouse
from .models import CuttingOrder, CuttingOrderItem
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def create_cutting_orders_on_order_save(sender, instance, created, **kwargs):
    """إنشاء أوامر تقطيع تلقائياً عند حفظ الطلب"""
    
    # التحقق من أن الطلب جديد وليس من نوع معاينة
    if not created:
        return
    
    # التحقق من نوع الطلب - لا ننشئ أوامر تقطيع للمعاينة
    selected_types = instance.get_selected_types_list()
    logger.info(f"🔍 فحص الطلب {instance.order_number} - الأنواع: {selected_types}")

    if 'inspection' in selected_types:
        logger.info(f"⏭️ تخطي إنشاء أمر تقطيع للطلب {instance.order_number} - يحتوي على معاينة")
        return
    
    try:
        with transaction.atomic():
            # الحصول على جميع المستودعات النشطة
            active_warehouses = Warehouse.objects.filter(is_active=True)
            logger.info(f"📦 المستودعات النشطة: {active_warehouses.count()}")

            if not active_warehouses.exists():
                logger.warning(f"❌ لا توجد مستودعات نشطة لإنشاء أوامر تقطيع للطلب {instance.order_number}")
                return
            
            # تجميع عناصر الطلب حسب المستودع (بناءً على فئة المنتج أو توزيع افتراضي)
            warehouse_items = {}
            order_items = instance.items.all()
            logger.info(f"📋 عدد عناصر الطلب: {order_items.count()}")

            for item in order_items:
                # تحديد المستودع المناسب للعنصر
                target_warehouse = determine_warehouse_for_item(item, active_warehouses)
                
                if target_warehouse:
                    if target_warehouse.id not in warehouse_items:
                        warehouse_items[target_warehouse.id] = {
                            'warehouse': target_warehouse,
                            'items': []
                        }
                    warehouse_items[target_warehouse.id]['items'].append(item)
            
            # إنشاء أمر تقطيع لكل مستودع له عناصر
            for warehouse_data in warehouse_items.values():
                warehouse = warehouse_data['warehouse']
                items = warehouse_data['items']
                
                # إنشاء أمر التقطيع
                cutting_order = CuttingOrder.objects.create(
                    order=instance,
                    warehouse=warehouse,
                    status='pending',
                    notes=f'أمر تقطيع تلقائي للطلب {instance.contract_number or instance.id}'
                )
                
                # إنشاء عناصر التقطيع باستخدام bulk_create لتحسين الأداء
                cutting_items = [
                    CuttingOrderItem(
                        cutting_order=cutting_order,
                        order_item=item,
                        status='pending'
                    ) for item in items
                ]
                CuttingOrderItem.objects.bulk_create(cutting_items)
                
                logger.info(f"✅ تم إنشاء أمر تقطيع {cutting_order.cutting_code} للمستودع {warehouse.name} مع {len(items)} عنصر")
    
    except Exception as e:
        logger.error(f"خطأ في إنشاء أوامر التقطيع للطلب {instance.id}: {str(e)}")


def determine_warehouse_for_item(order_item, warehouses):
    """تحديد المستودع المناسب لعنصر الطلب بناءً على المخزون الفعلي"""

    if not order_item.product:
        logger.warning(f"عنصر الطلب {order_item.id} لا يحتوي على منتج محدد")
        return warehouses.first()

    try:
        from inventory.models import StockTransaction

        # البحث عن المستودعات التي تحتوي على المنتج بناءً على آخر المعاملات
        warehouse_stocks = {}

        for warehouse in warehouses:
            # حساب المخزون الحالي للمنتج في هذا المستودع
            latest_transaction = StockTransaction.objects.filter(
                product=order_item.product,
                warehouse=warehouse
            ).order_by('-transaction_date').first()

            if latest_transaction and latest_transaction.running_balance > 0:
                warehouse_stocks[warehouse] = latest_transaction.running_balance

        if warehouse_stocks:
            # اختيار المستودع الذي يحتوي على أكبر كمية
            best_warehouse = max(warehouse_stocks.keys(), key=lambda w: warehouse_stocks[w])
            logger.info(f"📦 تم اختيار مستودع {best_warehouse.name} للمنتج {order_item.product.name} (كمية متاحة: {warehouse_stocks[best_warehouse]})")
            return best_warehouse

        # ⚠️ لا يوجد رصيد متاح في أي مستودع
        # لا نبحث عن آخر معاملة لأنها قد تكون معاملة خروج (out)
        # مما يؤدي لإرسال المنتج لمستودع فارغ!
        logger.warning(f"⚠️ المنتج {order_item.product.name} (كود: {order_item.product.code}) - الرصيد صفر في جميع المستودعات!")
        
        # محاولة البحث عن آخر مستودع كان فيه رصيد قبل نفاذه
        last_positive_transaction = StockTransaction.objects.filter(
            product=order_item.product,
            warehouse__in=warehouses,
            running_balance__gt=0  # فقط المعاملات التي كان فيها رصيد موجب
        ).select_related('warehouse').order_by('-transaction_date').first()

        if last_positive_transaction:
            logger.info(f"📋 تم اختيار مستودع {last_positive_transaction.warehouse.name} للمنتج {order_item.product.name} (آخر رصيد موجب)")
            return last_positive_transaction.warehouse

        # البحث بناءً على فئة المنتج
        if order_item.product.category:
            category_name = order_item.product.category.name.lower()

            # ربط الفئات بالمستودعات
            category_warehouse_mapping = {
                'اكسسوار': ['اكسسوار', 'accessories'],
                'أقمشة': ['بافلي', 'fabrics', 'textile'],
                'خيوط': ['بافلي', 'threads'],
                'أزرار': ['اكسسوار', 'buttons'],
                'سحابات': ['اكسسوار', 'zippers'],
                'منتجات': ['بافلي', 'products'],
                'تفصيل': ['بافلي', 'tailoring']
            }

            for category_key, warehouse_names in category_warehouse_mapping.items():
                if category_key in category_name:
                    for warehouse_name in warehouse_names:
                        matching_warehouse = warehouses.filter(
                            name__icontains=warehouse_name
                        ).first()
                        if matching_warehouse:
                            logger.info(f"🏷️ تم اختيار مستودع {matching_warehouse.name} للمنتج {order_item.product.name} بناءً على الفئة ({order_item.product.category.name})")
                            return matching_warehouse

        # البحث بناءً على اسم المنتج
        product_name = order_item.product.name.lower()
        if any(keyword in product_name for keyword in ['قماش', 'fabric', 'textile', 'خيط', 'thread']):
            fabric_warehouse = warehouses.filter(name__icontains='بافلي').first()
            if fabric_warehouse:
                logger.info(f"🧵 تم اختيار مستودع {fabric_warehouse.name} للمنتج {order_item.product.name} (منتج نسيجي)")
                return fabric_warehouse

        elif any(keyword in product_name for keyword in ['اكسسوار', 'accessory', 'زر', 'button', 'سحاب', 'zipper']):
            accessory_warehouse = warehouses.filter(name__icontains='اكسسوار').first()
            if accessory_warehouse:
                logger.info(f"💎 تم اختيار مستودع {accessory_warehouse.name} للمنتج {order_item.product.name} (إكسسوار)")
                return accessory_warehouse

    except Exception as e:
        logger.error(f"خطأ في تحديد المستودع للمنتج {order_item.product.name}: {str(e)}")

    # ⚠️ لم يتم العثور على مستودع يحتوي على المنتج
    # لا نرسل المنتج لمستودع عشوائي - يجب نقله أولاً
    logger.warning(f"⚠️ المنتج {order_item.product.name} (كود: {order_item.product.code}) غير موجود في أي مستودع!")
    logger.warning(f"⚠️ يجب نقل المنتج إلى أحد المستودعات النشطة أولاً")
    
    # إرجاع None لعدم إنشاء أمر تقطيع حتى يتم نقل المنتج
    return None


@receiver(post_save, sender=OrderItem)
def handle_order_item_creation(sender, instance, created, **kwargs):
    """معالجة إنشاء عناصر الطلب وإنشاء أوامر التقطيع إذا لزم الأمر"""

    if created:
        order = instance.order
        logger.info(f"🔍 تم إضافة عنصر جديد للطلب {order.order_number}")

        # التحقق من نوع الطلب - لا ننشئ أوامر تقطيع للمعاينة
        selected_types = order.get_selected_types_list()
        if 'inspection' in selected_types:
            logger.info(f"⏭️ تخطي إنشاء أمر تقطيع للطلب {order.order_number} - يحتوي على معاينة")
            return

        # التحقق من وجود أوامر تقطيع للطلب
        existing_cutting_orders = CuttingOrder.objects.filter(order=order)

        if existing_cutting_orders.exists():
            # إضافة العنصر الجديد لأمر التقطيع المناسب
            target_warehouse = determine_warehouse_for_item(
                instance,
                Warehouse.objects.filter(is_active=True)
            )

            if target_warehouse:
                cutting_order = existing_cutting_orders.filter(warehouse=target_warehouse).first()

                if cutting_order:
                    CuttingOrderItem.objects.create(
                        cutting_order=cutting_order,
                        order_item=instance,
                        status='pending'
                    )
                    logger.info(f"✅ تم إضافة عنصر جديد لأمر التقطيع {cutting_order.cutting_code}")
                else:
                    # إنشاء أمر تقطيع جديد لهذا المستودع
                    cutting_order = CuttingOrder.objects.create(
                        order=order,
                        warehouse=target_warehouse,
                        status='pending',
                        notes=f'أمر تقطيع تلقائي للطلب {order.order_number} - مستودع {target_warehouse.name}'
                    )

                    CuttingOrderItem.objects.create(
                        cutting_order=cutting_order,
                        order_item=instance,
                        status='pending'
                    )
                    logger.info(f"✅ تم إنشاء أمر تقطيع جديد {cutting_order.cutting_code} للمستودع {target_warehouse.name}")
            else:
                # المنتج غير موجود في أي مستودع - لا ننشئ أمر تقطيع
                product_info = f"{instance.product.name} (كود: {instance.product.code})" if instance.product else "غير محدد"
                logger.error(f"❌ تعذر إنشاء أمر تقطيع للعنصر: {product_info} - المنتج غير موجود في أي مستودع!")
                logger.error(f"❌ يرجى نقل المنتج إلى أحد المستودعات أولاً")
        else:
            # لا توجد أوامر تقطيع، ننشئ أوامر جديدة للطلب كاملاً
            logger.info(f"🔄 إنشاء أوامر تقطيع جديدة للطلب {order.order_number}")
            create_cutting_orders_on_order_save(Order, order, created=True)

            # تحديث حالة الطلب إلى قيد التنفيذ للمنتجات
            # استخدم الحقل canonical `order_status` بدلاً من `status` حتى لا نكتب فوق علم VIP
            if order.order_status != 'in_progress':
                order.order_status = 'in_progress'
                order.save(update_fields=['order_status'])
                logger.info(f"📋 تم تحديث order_status للطلب {order.order_number} إلى in_progress")


@receiver(post_save, sender=CuttingOrderItem)
def update_cutting_order_status(sender, instance, **kwargs):
    """تحديث حالة أمر التقطيع بناءً على حالة العناصر"""

    cutting_order = instance.cutting_order

    # حساب إحصائيات العناصر
    total_items = cutting_order.items.count()
    completed_items = cutting_order.items.filter(status='completed').count()
    pending_items = cutting_order.items.filter(status='pending').count()

    # تحديث حالة أمر التقطيع
    if completed_items == total_items and total_items > 0:
        cutting_order.status = 'completed'
        cutting_order.completed_at = timezone.now()
    elif completed_items > 0 and pending_items > 0:
        cutting_order.status = 'partially_completed'
    elif pending_items == total_items:
        cutting_order.status = 'pending'

    cutting_order.save()

    # إرسال إشعار لمنشئ الطلب إذا اكتمل التقطيع
    if cutting_order.status == 'completed':
        send_completion_notification(cutting_order)


@receiver(post_save, sender=CuttingOrderItem)
def create_manufacturing_item_on_cutting_completion(sender, instance, created, **kwargs):
    """ربط عناصر التصنيع بعناصر التقطيع المكتملة لتتبع حالة التقطيع
    
    ⚠️ IMPORTANT: 
    - لا ينشئ أمر تصنيع جديد (يُنشأ تلقائياً عند إنشاء الطلب فقط)
    - فقط يربط عنصر التصنيع الموجود بعنصر التقطيع المكتمل
    - يستثني طلبات المنتجات والمعاينات تماماً
    """

    # التحقق من أن العنصر مكتمل ولديه بيانات التسليم
    if instance.status != 'completed' or not instance.receiver_name or not instance.permit_number:
        return

    # استثناء طلبات المنتجات والمعاينات - لا تحتاج أوامر تصنيع
    order_types = instance.cutting_order.order.get_selected_types_list()
    if 'products' in order_types or 'inspection' in order_types:
        logger.info(f"⏭️ تخطي ربط عنصر التصنيع لعنصر التقطيع {instance.id} - الطلب نوع {order_types}")
        return

    # التحقق من عدم وجود عنصر تصنيع مرتبط بالفعل
    try:
        from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem

        # التحقق من وجود عنصر تصنيع مرتبط بهذا العنصر
        if ManufacturingOrderItem.objects.filter(cutting_item=instance).exists():
            logger.info(f"✅ عنصر التصنيع موجود بالفعل لعنصر التقطيع {instance.id}")
            return

        # البحث عن أمر تصنيع موجود فقط - لا ننشئ جديد
        try:
            manufacturing_order = ManufacturingOrder.objects.get(order=instance.cutting_order.order)
        except ManufacturingOrder.DoesNotExist:
            logger.warning(f"⚠️ لا يوجد أمر تصنيع للطلب {instance.cutting_order.order.order_number} - سيتم إنشاؤه عند إنشاء الطلب")
            return
        except ManufacturingOrder.MultipleObjectsReturned:
            # إذا كان هناك أكثر من أمر، نأخذ الأول
            manufacturing_order = ManufacturingOrder.objects.filter(order=instance.cutting_order.order).first()

        # إنشاء عنصر التصنيع مرتبط بعنصر التقطيع
        manufacturing_item = ManufacturingOrderItem.objects.create(
            manufacturing_order=manufacturing_order,
            cutting_item=instance,
            order_item=instance.order_item,
            product_name=instance.order_item.product.name if instance.order_item.product else 'منتج غير محدد',
            quantity=instance.order_item.quantity + instance.additional_quantity,
            receiver_name=instance.receiver_name,
            permit_number=instance.permit_number,
            cutting_date=instance.cutting_date,
            delivery_date=instance.delivery_date,
            fabric_received=False,  # لم يتم الاستلام بعد
            fabric_notes=f'تم ربطه من عنصر التقطيع {instance.id}'
        )

        logger.info(f"✅ تم ربط عنصر التصنيع {manufacturing_item.id} بعنصر التقطيع {instance.id}")

    except Exception as e:
        logger.error(f"❌ خطأ في ربط عنصر التصنيع لعنصر التقطيع {instance.id}: {str(e)}")


def send_completion_notification(cutting_order):
    """إرسال إشعار اكتمال التقطيع"""
    try:
        from notifications.models import Notification
        
        # إنشاء إشعار لمنشئ الطلب
        if cutting_order.order.created_by:
            Notification.objects.create(
                user=cutting_order.order.created_by,
                title='اكتمال التقطيع',
                message=f'تم اكتمال تقطيع الطلب {cutting_order.order.contract_number} في المستودع {cutting_order.warehouse.name}',
                notification_type='cutting_completed',
                related_object_type='cutting_order',
                related_object_id=cutting_order.id
            )
            
        logger.info(f"تم إرسال إشعار اكتمال التقطيع لأمر {cutting_order.cutting_code}")
        
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار اكتمال التقطيع: {str(e)}")


def send_stock_shortage_notification(order_item, warehouse):
    """إرسال إشعار نقص المخزون"""
    try:
        from notifications.models import Notification

        if order_item.order.created_by:
            Notification.objects.create(
                user=order_item.order.created_by,
                title='نقص في المخزون',
                message=f'الصنف {order_item.product.name} غير متوفر بالكمية المطلوبة في المستودع {warehouse.name}',
                notification_type='stock_shortage',
                related_object_type='order_item',
                related_object_id=order_item.id
            )

        logger.info(f"تم إرسال إشعار نقص المخزون للصنف {order_item.product.name}")

    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار نقص المخزون: {str(e)}")


def create_missing_cutting_orders():
    """إنشاء أوامر تقطيع للطلبات التي تحتوي على عناصر ولا تحتوي على أوامر تقطيع"""
    from orders.models import Order

    # البحث عن الطلبات التي تحتوي على عناصر ولا تحتوي على أوامر تقطيع
    orders_without_cutting = Order.objects.filter(
        items__isnull=False
    ).exclude(
        cutting_orders__isnull=False
    ).distinct()

    created_count = 0
    for order in orders_without_cutting:
        # التحقق من نوع الطلب
        selected_types = order.get_selected_types_list()
        if 'inspection' not in selected_types:
            try:
                create_cutting_orders_on_order_save(Order, order, created=True)
                created_count += 1
                logger.info(f"✅ تم إنشاء أوامر تقطيع للطلب {order.order_number}")
            except Exception as e:
                logger.error(f"❌ خطأ في إنشاء أوامر تقطيع للطلب {order.order_number}: {str(e)}")

    logger.info(f"🎉 تم إنشاء أوامر تقطيع لـ {created_count} طلب")
    return created_count


@receiver(post_save, sender='cutting.CuttingOrderItem')
def update_cutting_order_status_on_item_completion(sender, instance, **kwargs):
    """تحديث حالة أمر التقطيع عند إكمال جميع العناصر"""
    cutting_order = instance.cutting_order

    # التحقق من حالة جميع العناصر
    total_items = cutting_order.items.count()
    completed_items = cutting_order.items.filter(status='completed').count()
    in_progress_items = cutting_order.items.filter(status='in_progress').count()

    if total_items == 0:
        return

    # تحديد الحالة الجديدة
    new_status = None

    if completed_items == total_items:
        # جميع العناصر مكتملة
        new_status = 'completed'
        if not cutting_order.completed_at:
            cutting_order.completed_at = timezone.now()
    elif completed_items > 0 or in_progress_items > 0:
        # بعض العناصر مكتملة أو قيد التنفيذ
        new_status = 'in_progress'
    else:
        # لم يبدأ أي عنصر
        new_status = 'pending'

    # تحديث الحالة إذا تغيرت
    if new_status and cutting_order.status != new_status:
        old_status = cutting_order.status
        cutting_order.status = new_status
        cutting_order.save()

        logger.info(f"🔄 تم تحديث حالة أمر التقطيع {cutting_order.cutting_code} من {old_status} إلى {new_status}")

        # تحديث حالة الطلب الأساسي
        update_order_status_based_on_cutting_orders(cutting_order.order)


def update_order_status_based_on_cutting_orders(order):
    """تحديث حالة الطلب بناءً على حالة أوامر التقطيع"""
    cutting_orders = CuttingOrder.objects.filter(order=order)

    if not cutting_orders.exists():
        return

    total_orders = cutting_orders.count()
    completed_orders = cutting_orders.filter(status='completed').count()
    in_progress_orders = cutting_orders.filter(status='in_progress').count()

    # تحديد الحالة الجديدة للطلب
    if completed_orders == total_orders:
        # جميع أوامر التقطيع مكتملة
        new_status = 'in_progress'  # قيد التنفيذ (جاهز للتصنيع)
    elif completed_orders > 0 or in_progress_orders > 0:
        # بعض أوامر التقطيع مكتملة أو قيد التنفيذ
        new_status = 'in_progress'  # قيد التنفيذ
    else:
        # لم يبدأ أي أمر تقطيع
        new_status = 'in_progress'  # قيد التنفيذ (للمنتجات)

    # تحديث حالة الطلب إذا تغيرت
    # اكتب في الحقل canonical `order_status` بدلاً من `status` لتجنب حذف وسم الـ VIP
    if order.order_status != new_status:
        old_status = order.order_status
        order.order_status = new_status
        order.save(update_fields=['order_status'])

        logger.info(f"📋 تم تحديث order_status للطلب {order.order_number} من {old_status} إلى {new_status}")
