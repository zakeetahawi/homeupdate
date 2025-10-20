from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from accounts.models import SystemSettings
from .models import Product, StockTransaction

@receiver(post_save, sender=SystemSettings)
def update_currency_on_settings_change(sender, instance, **kwargs):
    """تحديث العملة لجميع المنتجات عند تغيير إعدادات النظام"""
    def update_products():
        if hasattr(instance, 'currency') and instance.currency:
            Product.objects.all().update(currency=instance.currency)

    transaction.on_commit(update_products)


@receiver(post_save, sender=Product)
def protect_paid_orders_from_price_changes(sender, instance, created, **kwargs):
    """حماية الطلبات المدفوعة من تغيير أسعار المنتجات"""
    # ✅ تم تعطيل هذه الوظيفة مؤقتاً لأن Product model لا يحتوي على tracker
    # إذا أردت تفعيلها، يجب إضافة FieldTracker من django-model-utils
    # من المكتبة: from model_utils import FieldTracker
    # ثم إضافة في Product model: tracker = FieldTracker()
    pass

@receiver(post_save, sender=StockTransaction)
def update_running_balance(sender, instance, created, **kwargs):
    """تحديث الرصيد المتحرك للمعاملات"""
    if created:
        # ✅ حماية: منع السحب من مستودع فارغ
        if instance.transaction_type == 'out':
            # التحقق من وجود رصيد قبل السحب
            last_trans = StockTransaction.objects.filter(
                product=instance.product,
                warehouse=instance.warehouse
            ).exclude(id=instance.id).order_by('-transaction_date').first()
            
            if not last_trans:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"❌ محاولة سحب من مستودع فارغ! "
                    f"المنتج: {instance.product.name} ({instance.product.code}) "
                    f"المستودع: {instance.warehouse.name} "
                    f"الكمية: {instance.quantity}"
                )
                # حذف المعاملة الخاطئة
                instance.delete()
                return
            
            if last_trans.running_balance < instance.quantity:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"❌ رصيد غير كافٍ! "
                    f"المنتج: {instance.product.name} ({instance.product.code}) "
                    f"المستودع: {instance.warehouse.name} "
                    f"الرصيد المتاح: {last_trans.running_balance} "
                    f"الكمية المطلوبة: {instance.quantity}"
                )
        
        # ✅ حماية: منع إدخال منتج في مستودع جديد إذا كان موجوداً في مستودع آخر
        # (إلا إذا كانت معاملة نقل)
        if instance.transaction_type == 'in':
            # التحقق من عدم وجود المنتج في مستودع آخر
            other_warehouse_trans = StockTransaction.objects.filter(
                product=instance.product
            ).exclude(
                warehouse=instance.warehouse
            ).order_by('-transaction_date').first()
            
            if other_warehouse_trans and other_warehouse_trans.running_balance > 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"⚠️ المنتج {instance.product.name} ({instance.product.code}) "
                    f"موجود بالفعل في مستودع {other_warehouse_trans.warehouse.name} "
                    f"برصيد {other_warehouse_trans.running_balance}. "
                    f"يتم الآن إدخاله في مستودع {instance.warehouse.name}. "
                    f"يُفضل استخدام عملية نقل (transfer) بدلاً من الإدخال المباشر."
                )
        def update_balances():
            from decimal import Decimal
            
            # حساب الرصيد المتحرك
            previous_balance = StockTransaction.objects.filter(
                product=instance.product,
                transaction_date__lt=instance.transaction_date
            ).exclude(id=instance.id).order_by('-transaction_date').first()

            # ✅ تحويل إلى Decimal لتجنب خطأ الجمع
            if previous_balance and previous_balance.running_balance is not None:
                current_balance = Decimal(str(previous_balance.running_balance))
            else:
                current_balance = Decimal('0')
            
            # ✅ تحويل الكمية إلى Decimal
            quantity_decimal = Decimal(str(instance.quantity))

            if instance.transaction_type == 'in':
                instance.running_balance = current_balance + quantity_decimal
            else:
                instance.running_balance = current_balance - quantity_decimal

            # تجنب التكرار عند الحفظ
            StockTransaction.objects.filter(id=instance.id).update(
                running_balance=instance.running_balance
            )

            # تحديث الأرصدة اللاحقة
            subsequent_transactions = StockTransaction.objects.filter(
                product=instance.product,
                transaction_date__gt=instance.transaction_date
            ).exclude(id=instance.id).order_by('transaction_date')

            current_balance = Decimal(str(instance.running_balance))
            for trans in subsequent_transactions:
                trans_quantity = Decimal(str(trans.quantity))
                if trans.transaction_type == 'in':
                    current_balance += trans_quantity
                else:
                    current_balance -= trans_quantity
                StockTransaction.objects.filter(id=trans.id).update(
                    running_balance=current_balance
                )
        
        transaction.on_commit(update_balances)