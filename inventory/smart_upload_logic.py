"""
منطق الرفع الذكي للمخزون - يمنع التكرارات وينقل للمستودعات الصحيحة
"""

from django.db import transaction
from django.db.models import Sum
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
                # تحديث بيانات المنتج
                product.name = name
                product.price = product_data.get('price', product.price)
                product.category = product_data.get('category', product.category)
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
    
    # إنشاء منتج جديد
    product = Product.objects.create(
        name=name,
        code=code,
        price=product_data.get('price'),
        category=product_data.get('category'),
        currency=product_data.get('currency', 'EGP'),
        unit=product_data.get('unit', 'piece')
    )
    
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
        
        return result
    
    return result


def add_stock_transaction(product, warehouse, quantity, user, notes):
    """إضافة معاملة مخزون (دخول)"""
    from .models import StockTransaction
    
    if quantity <= 0:
        return
    
    # الحصول على آخر رصيد
    last_trans = StockTransaction.objects.filter(
        product=product,
        warehouse=warehouse
    ).order_by('-transaction_date', '-id').first()
    
    previous_balance = last_trans.running_balance if last_trans else 0
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
        running_balance=float(new_balance)
    )


def remove_stock_transaction(product, warehouse, quantity, user, notes):
    """إزالة معاملة مخزون (خروج)"""
    from .models import StockTransaction
    
    if quantity <= 0:
        return
    
    # الحصول على آخر رصيد
    last_trans = StockTransaction.objects.filter(
        product=product,
        warehouse=warehouse
    ).order_by('-transaction_date', '-id').first()
    
    previous_balance = last_trans.running_balance if last_trans else 0
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
        running_balance=float(new_balance)
    )


def find_duplicate_products():
    """
    البحث عن المنتجات المكررة في عدة مستودعات
    
    Returns:
        list - قائمة المنتجات المكررة
    """
    from .models import Product, StockTransaction
    from django.db.models import Count
    
    duplicates = []
    
    # جميع المنتجات
    products = Product.objects.all()
    
    for product in products:
        # المستودعات التي فيها المنتج
        warehouses_with_stock = StockTransaction.objects.filter(
            product=product
        ).values('warehouse__name').annotate(
            total=Sum('quantity')
        ).filter(total__gt=0)
        
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
