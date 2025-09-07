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
    if not created:  # فقط عند التحديث وليس الإنشاء
        try:
            # التحقق من تغيير السعر
            if instance.tracker.has_changed('price'):
                old_price = instance.tracker.previous('price')
                new_price = instance.price

                # البحث عن الطلبات المدفوعة التي تحتوي على هذا المنتج
                from orders.models import OrderItem, Order

                paid_orders_with_product = OrderItem.objects.filter(
                    product=instance,
                    order__paid_amount__gt=0
                ).select_related('order')

                if paid_orders_with_product.exists():
                    import logging
                    logger = logging.getLogger(__name__)

                    affected_orders = [item.order.order_number for item in paid_orders_with_product]
                    logger.warning(
                        f"تم تغيير سعر المنتج '{instance.name}' من {old_price} إلى {new_price}. "
                        f"الطلبات المدفوعة المتأثرة: {', '.join(affected_orders)}"
                    )

                    # يمكن إضافة منع التحديث هنا إذا أردت
                    # raise ValidationError('لا يمكن تغيير سعر منتج موجود في طلبات مدفوعة')

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في فحص حماية الأسعار للمنتج {instance.name}: {str(e)}")

@receiver(post_save, sender=StockTransaction)
def update_running_balance(sender, instance, created, **kwargs):
    """تحديث الرصيد المتحرك للمعاملات"""
    if created:
        def update_balances():
            # حساب الرصيد المتحرك
            previous_balance = StockTransaction.objects.filter(
                product=instance.product,
                transaction_date__lt=instance.transaction_date
            ).exclude(id=instance.id).order_by('-transaction_date').first()

            current_balance = previous_balance.running_balance if previous_balance else 0

            if instance.transaction_type == 'in':
                instance.running_balance = current_balance + instance.quantity
            else:
                instance.running_balance = current_balance - instance.quantity

            # تجنب التكرار عند الحفظ
            StockTransaction.objects.filter(id=instance.id).update(
                running_balance=instance.running_balance
            )

            # تحديث الأرصدة اللاحقة
            subsequent_transactions = StockTransaction.objects.filter(
                product=instance.product,
                transaction_date__gt=instance.transaction_date
            ).exclude(id=instance.id).order_by('transaction_date')

            current_balance = instance.running_balance
            for trans in subsequent_transactions:
                if trans.transaction_type == 'in':
                    current_balance += trans.quantity
                else:
                    current_balance -= trans.quantity
                StockTransaction.objects.filter(id=trans.id).update(
                    running_balance=current_balance
                )
        
        transaction.on_commit(update_balances)