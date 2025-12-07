"""
منطق الرفع الذكي للمخزون - يمنع التكرارات وينقل للمستودعات الصحيحة
ويحدث أوامر التقطيع تلقائياً
"""

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def smart_update_product(product_data, warehouse, user, upload_mode):
    """
    تحديث ذكي للمنتج - ينقله للمستودع الصحيح ويمنع التكرار
    
    Args:
        product_data: dict - بيانات المنتج من Excel
        warehouse: Warehouse - المستودع المحدد في الملف
        user: User - المستخدم
        upload_mode: str - وضع الرفع
        
    Returns:
        dict - نتيجة العملية
    """
    from .models import Product, StockTransaction, Warehouse
    
    result = {
        'action': None,  # created, updated, moved, skipped
        'product': None,
        'old_warehouse': None,
        'new_warehouse': warehouse,
        'message': ''
    }
    
    code = product_data.get('code')
    name = product_data['name']
    
    # البحث عن المنتج
    if code:
        try:
            product = Product.objects.get(code=code)
            result['product'] = product
            
            # وضع: إضافة فقط - تجاهل الموجود
            if upload_mode == 'add_only':
                result['action'] = 'skipped'
                result['message'] = f'منتج موجود: {code}'
                return result
            
            # التحديث الذكي أو الدمج
            if upload_mode in ['smart_update', 'merge_warehouses']:
                # تحديث بيانات المنتج بجميع الحقول
                product.name = name
                product.price = product_data.get('price', product.price)
                product.category = product_data.get('category', product.category)
                
                # تحديث الحقول الإضافية
                if 'description' in product_data and product_data['description']:
                    product.description = product_data['description']
                if 'minimum_stock' in product_data:
                    product.minimum_stock = product_data['minimum_stock']
                if 'currency' in product_data:
                    product.currency = product_data['currency']
                if 'unit' in product_data:
                    product.unit = product_data['unit']
                
                product.save()
                
                # نقل المخزون للمستودع الصحيح إذا لزم الأمر
                moved = move_product_to_correct_warehouse(
                    product, 
                    warehouse, 
                    product_data.get('quantity', 0),
                    user,
                    upload_mode == 'merge_warehouses'
                )
                
                if moved['moved']:
                    result['action'] = 'moved'
                    result['old_warehouse'] = moved['from_warehouse']
                    result['message'] = f"نُقل من {moved['from_warehouse']} إلى {warehouse}"
                else:
                    result['action'] = 'updated'
                    result['message'] = 'تم التحديث'
                
                return result
                
        except Product.DoesNotExist:
            pass  # سيتم إنشاؤه أدناه
    
    # إنشاء منتج جديد بجميع البيانات
    product = Product.objects.create(
        name=name,
        code=code,
        price=product_data.get('price'),
        category=product_data.get('category'),
        description=product_data.get('description', ''),
        minimum_stock=product_data.get('minimum_stock', 0),
        currency=product_data.get('currency', 'EGP'),
        unit=product_data.get('unit', 'piece')
    )
    
    # إضافة الكمية الأولية للمنتج الجديد
    quantity = product_data.get('quantity', 0)
    if quantity > 0 and warehouse:
        add_stock_transaction(product, warehouse, quantity, user, 'إنشاء من Excel')
    
    result['action'] = 'created'
    result['product'] = product
    result['message'] = 'تم الإنشاء'
    
    return result


def move_product_to_correct_warehouse(product, target_warehouse, new_quantity, user, merge_all=False):
    """
    نقل المنتج للمستودع الصحيح
    
    Args:
        product: Product
        target_warehouse: Warehouse - المستودع المستهدف
        new_quantity: float - الكمية الجديدة
        user: User
        merge_all: bool - دمج كل المستودعات
        
    Returns:
        dict - تفاصيل النقل
    """
    from .models import StockTransaction, Warehouse
    
    result = {
        'moved': False,
        'from_warehouse': None,
        'merged_warehouses': [],
        'total_merged_quantity': 0
    }
    
    # الحصول على كل المعاملات الحالية
    current_stocks = StockTransaction.objects.filter(
        product=product
    ).values('warehouse').annotate(
        total=Sum('quantity')
    ).filter(total__gt=0)
    
    if not current_stocks:
        # لا يوجد مخزون - إضافة مباشرة
        if new_quantity > 0 and target_warehouse:
            add_stock_transaction(product, target_warehouse, new_quantity, user, 'رفع من Excel')
        return result
    
    # إذا كان في مستودع واحد فقط
    if len(current_stocks) == 1:
        current_wh_id = current_stocks[0]['warehouse']
        current_qty = current_stocks[0]['total']
        
        # إذا كان في نفس المستودع المطلوب
        if current_wh_id == target_warehouse.id:
            # تحديث الكمية فقط
            if new_quantity > 0:
                add_stock_transaction(product, target_warehouse, new_quantity, user, 'تحديث من Excel')
            return result
        
        # نقل من مستودع لآخر
        current_wh = Warehouse.objects.get(id=current_wh_id)
        
        # إخراج من المستودع القديم
        remove_stock_transaction(product, current_wh, current_qty, user, f'نقل إلى {target_warehouse.name}')
        
        # إضافة للمستودع الجديد (الكمية القديمة + الجديدة)
        total_qty = Decimal(str(current_qty)) + Decimal(str(new_quantity))
        add_stock_transaction(product, target_warehouse, float(total_qty), user, f'نُقل من {current_wh.name}')
        
        result['moved'] = True
        result['from_warehouse'] = current_wh.name
        
        # تحديث أوامر التقطيع 🔥
        cutting_update = update_cutting_orders_after_move(product, current_wh, target_warehouse, user)
        result['cutting_orders_updated'] = cutting_update.get('updated', 0)
        result['cutting_orders_split'] = cutting_update.get('split', 0)
        
        return result
    
    # المنتج موجود في عدة مستودعات (تكرار!)
    if merge_all or len(current_stocks) > 1:
        logger.warning(f"⚠️ منتج مكرر في {len(current_stocks)} مستودعات: {product.code}")
        
        # دمج كل المستودعات
        total_quantity = Decimal('0')
        
        for stock in current_stocks:
            wh = Warehouse.objects.get(id=stock['warehouse'])
            qty = Decimal(str(stock['total']))
            
            # إخراج من كل مستودع
            remove_stock_transaction(product, wh, float(qty), user, f'دمج في {target_warehouse.name}')
            
            total_quantity += qty
            result['merged_warehouses'].append(wh.name)
        
        # إضافة الكمية الجديدة
        total_quantity += Decimal(str(new_quantity))
        
        # إضافة المجموع للمستودع المستهدف
        add_stock_transaction(
            product, 
            target_warehouse, 
            float(total_quantity), 
            user, 
            f'دُمج من {len(current_stocks)} مستودعات'
        )
        
        result['moved'] = True
        result['from_warehouse'] = f"{len(current_stocks)} مستودعات"
        result['total_merged_quantity'] = float(total_quantity)
        
        # تحديث أوامر التقطيع لكل المستودعات المدموجة 🔥
        total_cutting_updated = 0
        total_cutting_split = 0
        
        for stock in current_stocks:
            old_wh = Warehouse.objects.get(id=stock['warehouse'])
            cutting_update = update_cutting_orders_after_move(product, old_wh, target_warehouse, user)
            total_cutting_updated += cutting_update.get('updated', 0)
            total_cutting_split += cutting_update.get('split', 0)
        
        result['cutting_orders_updated'] = total_cutting_updated
        result['cutting_orders_split'] = total_cutting_split
        
        return result
    
    return result


def add_stock_transaction(product, warehouse, quantity, user, notes):
    """إضافة معاملة مخزون (دخول) - محسّن للسرعة"""
    from .models import StockTransaction
    from django.db import connection
    
    if quantity <= 0:
        return
    
    # استعلام مباشر أسرع من ORM
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT running_balance 
            FROM inventory_stocktransaction 
            WHERE product_id = %s AND warehouse_id = %s 
            ORDER BY transaction_date DESC, id DESC 
            LIMIT 1
        """, [product.id, warehouse.id])
        row = cursor.fetchone()
        previous_balance = row[0] if row else 0
    
    new_balance = Decimal(str(previous_balance)) + Decimal(str(quantity))
    
    StockTransaction.objects.create(
        product=product,
        warehouse=warehouse,
        transaction_type='in',
        reason='purchase',
        quantity=quantity,
        reference='رفع سريع',
        notes=notes,
        created_by=user,
        running_balance=float(new_balance),
        transaction_date=timezone.now()
    )


def remove_stock_transaction(product, warehouse, quantity, user, notes):
    """إزالة معاملة مخزون (خروج) - محسّن للسرعة"""
    from .models import StockTransaction
    from django.db import connection
    
    if quantity <= 0:
        return
    
    # استعلام مباشر أسرع
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT running_balance 
            FROM inventory_stocktransaction 
            WHERE product_id = %s AND warehouse_id = %s 
            ORDER BY transaction_date DESC, id DESC 
            LIMIT 1
        """, [product.id, warehouse.id])
        row = cursor.fetchone()
        previous_balance = row[0] if row else 0
    
    new_balance = Decimal(str(previous_balance)) - Decimal(str(quantity))
    
    StockTransaction.objects.create(
        product=product,
        warehouse=warehouse,
        transaction_type='out',
        reason='transfer',
        quantity=quantity,
        reference='نقل ذكي',
        notes=notes,
        created_by=user,
        running_balance=float(new_balance),
        transaction_date=timezone.now()
    )


def find_duplicate_products():
    """
    البحث عن المنتجات المكررة في عدة مستودعات
    
    Returns:
        list - قائمة المنتجات المكررة
    """
    from .models import Product, StockTransaction
    from django.db.models import Count, Case, When, F, Max, Subquery, OuterRef
    
    duplicates = []
    
    # جميع المنتجات
    products = Product.objects.all()
    
    for product in products:
        # المستودعات التي فيها المنتج - باستخدام آخر running_balance لكل مستودع
        warehouses_with_stock = []
        
        # الحصول على المستودعات الفريدة للمنتج (set لإزالة التكرار)
        warehouse_ids = set(StockTransaction.objects.filter(
            product=product
        ).values_list('warehouse_id', flat=True))
        
        for warehouse_id in warehouse_ids:
            # آخر حركة مخزون للمنتج في هذا المستودع
            last_transaction = StockTransaction.objects.filter(
                product=product,
                warehouse_id=warehouse_id
            ).order_by('-transaction_date', '-id').first()
            
            if last_transaction and last_transaction.running_balance > 0:
                warehouses_with_stock.append({
                    'warehouse__name': last_transaction.warehouse.name,
                    'total': last_transaction.running_balance
                })
        
        # فقط إذا كان المنتج موجود في أكثر من مستودع واحد
        if len(warehouses_with_stock) > 1:
            duplicates.append({
                'product': product,
                'code': product.code,
                'name': product.name,
                'warehouses_count': len(warehouses_with_stock),
                'warehouses': [w['warehouse__name'] for w in warehouses_with_stock],
                'quantities': {w['warehouse__name']: w['total'] for w in warehouses_with_stock}
            })
    
    return duplicates


def clean_start_reset():
    """
    مسح كامل للنظام - حذف كل المنتجات والمعاملات
    ⚠️ خطير - استخدم بحذر!
    """
    from .models import Product, StockTransaction
    from installations.models import StockTransfer
    
    logger.warning("⚠️ بدء المسح الكامل للنظام!")
    
    with transaction.atomic():
        # حذف التحويلات أولاً
        deleted_transfers = StockTransfer.objects.all().count()
        StockTransfer.objects.all().delete()
        logger.info(f"✅ حُذف {deleted_transfers} تحويل")
        
        # حذف المعاملات
        deleted_transactions = StockTransaction.objects.all().count()
        StockTransaction.objects.all().delete()
        logger.info(f"✅ حُذف {deleted_transactions} معاملة")
        
        # حذف المنتجات
        deleted_products = Product.objects.all().count()
        Product.objects.all().delete()
        logger.info(f"✅ حُذف {deleted_products} منتج")
    
    logger.warning("✅ اكتمل المسح الكامل!")
    
    return {
        'deleted_products': deleted_products,
        'deleted_transactions': deleted_transactions,
        'deleted_transfers': deleted_transfers
    }


def update_cutting_orders_after_move(product, old_warehouse, new_warehouse, user):
    """
    تحديث أوامر التقطيع بعد نقل المنتج للمستودع الصحيح
    
    Args:
        product: Product - المنتج المنقول
        old_warehouse: Warehouse - المستودع القديم
        new_warehouse: Warehouse - المستودع الجديد
        user: User - المستخدم
        
    Returns:
        dict - إحصائيات التحديث
    """
    try:
        from cutting.models import CuttingOrder, CuttingOrderItem
        
        # أوامر التقطيع المتأثرة (غير المكتملة فقط)
        affected_orders = CuttingOrder.objects.filter(
            items__order_item__product=product,
            status__in=['pending', 'in_progress'],
            warehouse=old_warehouse
        ).distinct()
        
        if not affected_orders.exists():
            return {
                'updated': 0,
                'split': 0,
                'total_affected': 0,
                'message': 'لا توجد أوامر تقطيع متأثرة'
            }
        
        updated_count = 0
        split_count = 0
        
        logger.info(f"🔍 فحص {affected_orders.count()} أمر تقطيع متأثر...")
        
        for cutting_order in affected_orders:
            # فحص: هل كل المنتجات في الأمر يجب أن تكون في المستودع الجديد؟
            all_items_should_be_in_new_warehouse = True
            
            for item in cutting_order.items.all():
                item_product = item.order_item.product
                
                # إذا كان المنتج هو المنتج المنقول → نعم
                if item_product.id == product.id:
                    continue
                
                # إذا كان منتج آخر، نفحص مستودعه الحالي
                from .models import StockTransaction
                latest_stock = StockTransaction.objects.filter(
                    product=item_product
                ).values('warehouse').annotate(
                    total=Sum('quantity')
                ).filter(total__gt=0).first()
                
                if latest_stock and latest_stock['warehouse'] != new_warehouse.id:
                    all_items_should_be_in_new_warehouse = False
                    break
            
            if all_items_should_be_in_new_warehouse:
                # حالة بسيطة: نقل الأمر بالكامل للمستودع الجديد
                cutting_order.warehouse = new_warehouse
                cutting_order.notes = (cutting_order.notes or '') + \
                    f"\n📦 [تحديث تلقائي] تم تحديث المستودع من '{old_warehouse.name}' إلى '{new_warehouse.name}' - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                cutting_order.save()
                updated_count += 1
                
                logger.info(f"✅ تحديث أمر تقطيع {cutting_order.cutting_code}: {old_warehouse.name} → {new_warehouse.name}")
            else:
                # حالة معقدة: تقسيم الأمر
                new_order = split_cutting_order(cutting_order, product, new_warehouse, user)
                split_count += 1
                
                logger.info(f"🔀 تقسيم أمر تقطيع {cutting_order.cutting_code} → {new_order.cutting_code}")
        
        result = {
            'updated': updated_count,
            'split': split_count,
            'total_affected': affected_orders.count(),
            'message': f'تم تحديث {updated_count} أمر، تقسيم {split_count} أمر'
        }
        
        # إرسال إشعار إذا تم التحديث 🔔
        if updated_count > 0 or split_count > 0:
            try:
                from notifications.models import Notification
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                notification_msg = f"تم تحديث {updated_count + split_count} أمر تقطيع بعد نقل '{product.name}' من '{old_warehouse.name}' إلى '{new_warehouse.name}'"
                
                notification = Notification.objects.create(
                    title='تحديث أوامر التقطيع تلقائياً',
                    message=notification_msg,
                    notification_type='cutting_order_created',  # استخدام نوع موجود
                    priority='normal',
                    created_by=user
                )
                
                # إضافة visibility للمستخدمين المعنيين (cutting staff + admins)
                cutting_users = User.objects.filter(
                    groups__name__in=['Cutting', 'Admin', 'Manager']
                ).distinct()
                
                notification.visible_to.set(cutting_users)
                
                logger.info(f"✅ تم إرسال إشعار لـ {cutting_users.count()} مستخدم")
            except Exception as e:
                logger.warning(f"⚠️ فشل إرسال الإشعار: {e}")
        
        logger.info(f"📊 نتيجة تحديث أوامر التقطيع: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث أوامر التقطيع: {e}")
        import traceback
        traceback.print_exc()
        return {
            'updated': 0,
            'split': 0,
            'total_affected': 0,
            'error': str(e)
        }


def split_cutting_order(original_order, moved_product, new_warehouse, user):
    """
    تقسيم أمر تقطيع عند نقل منتج لمستودع مختلف
    
    Args:
        original_order: CuttingOrder - الأمر الأصلي
        moved_product: Product - المنتج المنقول
        new_warehouse: Warehouse - المستودع الجديد
        user: User - المستخدم
        
    Returns:
        CuttingOrder - الأمر الجديد
    """
    from cutting.models import CuttingOrder, CuttingOrderItem
    import uuid
    
    # إنشاء كود فريد للأمر الجديد
    new_code = f"{original_order.cutting_code}-S{uuid.uuid4().hex[:4].upper()}"
    
    # إنشاء أمر جديد للمستودع الجديد
    new_order = CuttingOrder.objects.create(
        cutting_code=new_code,
        order=original_order.order,
        warehouse=new_warehouse,
        status='pending',
        created_by=user,
        assigned_to=original_order.assigned_to,
        notes=f"🔀 منقول من أمر {original_order.cutting_code} بعد نقل منتج '{moved_product.name}' للمستودع '{new_warehouse.name}'"
    )
    
    # نقل العناصر المتعلقة بالمنتج المنقول
    items_to_move = original_order.items.filter(order_item__product=moved_product)
    
    moved_items_count = 0
    for item in items_to_move:
        # إنشاء نسخة في الأمر الجديد
        CuttingOrderItem.objects.create(
            cutting_order=new_order,
            order_item=item.order_item,
            status=item.status,
            cutter_name=item.cutter_name,
            permit_number=item.permit_number,
            receiver_name=item.receiver_name,
            notes=item.notes
        )
        
        # حذف من الأمر القديم
        item.delete()
        moved_items_count += 1
    
    # تحديث ملاحظات الأمر القديم
    original_order.notes = (original_order.notes or '') + \
        f"\n🔀 [تقسيم تلقائي] تم نقل {moved_items_count} عنصر لأمر جديد {new_order.cutting_code} - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    original_order.save()
    
    logger.info(f"🔀 تقسيم ناجح: {original_order.cutting_code} → {new_order.cutting_code} ({moved_items_count} عنصر)")
    
    return new_order


def delete_empty_warehouses(user):
    """
    حذف المستودعات الفارغة التي لا تحتوي على مخزون ولا أوامر نشطة
    
    Args:
        user: User - المستخدم الذي يقوم بالحذف
        
    Returns:
        dict - إحصائيات الحذف
    """
    from .models import Warehouse, StockTransaction
    from django.db.models import Sum
    from cutting.models import CuttingOrder
    
    try:
        logger.info("🔍 البحث عن المستودعات الفارغة...")
        
        # البحث عن المستودعات الفارغة
        empty_warehouses = []
        
        for warehouse in Warehouse.objects.all():
            # حساب المخزون الحالي
            total_stock = StockTransaction.objects.filter(
                warehouse=warehouse
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # عد أوامر التقطيع النشطة
            active_cutting = CuttingOrder.objects.filter(
                warehouse=warehouse,
                status__in=['pending', 'in_progress']
            ).count()
            
            # إذا كان فارغاً ولا يوجد له أوامر تقطيع نشطة
            if total_stock == 0 and active_cutting == 0:
                # تأكد أنه ليس مستودع أقمشة رسمي
                if not warehouse.is_official_fabric_warehouse:
                    empty_warehouses.append({
                        'warehouse': warehouse,
                        'name': warehouse.name,
                        'last_activity': warehouse.updated_at
                    })
        
        if not empty_warehouses:
            logger.info("✅ لا توجد مستودعات فارغة للحذف")
            return {
                'deleted': 0,
                'warehouses': [],
                'message': 'لا توجد مستودعات فارغة'
            }
        
        # حذف المستودعات الفارغة
        deleted_names = []
        for item in empty_warehouses:
            warehouse = item['warehouse']
            deleted_names.append(warehouse.name)
            
            logger.warning(f"🗑️ حذف مستودع فارغ: {warehouse.name}")
            warehouse.delete()
        
        result = {
            'deleted': len(deleted_names),
            'warehouses': deleted_names,
            'message': f'تم حذف {len(deleted_names)} مستودع فارغ'
        }
        
        logger.info(f"✅ {result['message']}: {', '.join(deleted_names)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ خطأ في حذف المستودعات الفارغة: {e}")
        import traceback
        traceback.print_exc()
        return {
            'deleted': 0,
            'warehouses': [],
            'error': str(e)
        }
