"""
نظام تكامل الطلبات مع المخزون
إدارة خصم المخزون التلقائي عند إنشاء الطلبات
"""

import logging
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


class OrderInventoryService:
    """خدمة تكامل الطلبات مع المخزون"""

    @staticmethod
    def deduct_stock_for_order(order, user=None):
        """
        خصم المخزون تلقائياً عند إنشاء أو تأكيد طلب
        """
        from inventory.models import Product, StockTransaction, Warehouse
        from notifications.models import Notification

        try:
            with db_transaction.atomic():
                deducted_items = []
                failed_items = []

                # الحصول على المستودع الافتراضي
                default_warehouse = Warehouse.objects.filter(is_active=True).first()

                if not default_warehouse:
                    logger.error("لا يوجد مستودع نشط للخصم")
                    return {"success": False, "error": "لا يوجد مستودع نشط"}

                for item in order.items.all():
                    if not item.product:
                        continue

                    product = item.product
                    quantity = item.quantity

                    # التحقق من المخزون الحالي
                    current_stock = OrderInventoryService._get_current_stock(
                        product, default_warehouse
                    )

                    # إنشاء حركة صادر
                    try:
                        stock_transaction = StockTransaction.objects.create(
                            product=product,
                            warehouse=default_warehouse,
                            transaction_type="out",
                            reason="sale",
                            quantity=quantity,
                            reference=f"طلب-{order.order_number}",
                            transaction_date=timezone.now(),
                            notes=f"خصم تلقائي للطلب - العميل: {order.customer.name if hasattr(order, 'customer') else 'غير محدد'}",
                            created_by=user,
                        )

                        deducted_items.append(
                            {
                                "product": product.name,
                                "quantity": quantity,
                                "previous_stock": current_stock,
                                "new_stock": current_stock - quantity,
                            }
                        )

                        # إرسال تنبيه إذا أصبح المخزون منخفضاً
                        new_stock = current_stock - quantity
                        if new_stock <= product.minimum_stock and new_stock > 0:
                            OrderInventoryService._create_low_stock_alert(
                                product, new_stock, user
                            )
                        elif new_stock <= 0:
                            OrderInventoryService._create_out_of_stock_alert(
                                product, user
                            )

                    except Exception as e:
                        failed_items.append({"product": product.name, "error": str(e)})
                        logger.error(f"خطأ في خصم المنتج {product.name}: {e}")

                # إنشاء إشعار للمستخدم
                if deducted_items:
                    OrderInventoryService._send_deduction_notification(
                        order, deducted_items, user
                    )

                return {
                    "success": True,
                    "deducted": deducted_items,
                    "failed": failed_items,
                }

        except Exception as e:
            logger.error(f"خطأ في خصم المخزون للطلب {order.order_number}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def reverse_stock_for_order(order, user=None, reason="إلغاء الطلب"):
        """
        إرجاع المخزون عند إلغاء الطلب
        """
        from inventory.models import StockTransaction, Warehouse

        try:
            with db_transaction.atomic():
                restored_items = []

                # الحصول على المستودع الافتراضي
                default_warehouse = Warehouse.objects.filter(is_active=True).first()

                if not default_warehouse:
                    return {"success": False, "error": "لا يوجد مستودع نشط"}

                for item in order.items.all():
                    if not item.product:
                        continue

                    product = item.product
                    quantity = item.quantity

                    # إنشاء حركة وارد لإرجاع المخزون
                    StockTransaction.objects.create(
                        product=product,
                        warehouse=default_warehouse,
                        transaction_type="in",
                        reason="return",
                        quantity=quantity,
                        reference=f"إلغاء-طلب-{order.order_number}",
                        transaction_date=timezone.now(),
                        notes=f"إرجاع المخزون - السبب: {reason}",
                        created_by=user,
                    )

                    restored_items.append(
                        {"product": product.name, "quantity": quantity}
                    )

                return {"success": True, "restored": restored_items}

        except Exception as e:
            logger.error(f"خطأ في إرجاع المخزون للطلب {order.order_number}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_stock_availability(order):
        """
        التحقق من توفر المخزون لجميع عناصر الطلب
        """
        from inventory.models import Warehouse

        availability = {"all_available": True, "items": [], "total_shortage": 0}

        default_warehouse = Warehouse.objects.filter(is_active=True).first()

        if not default_warehouse:
            availability["all_available"] = False
            availability["error"] = "لا يوجد مستودع نشط"
            return availability

        for item in order.items.all():
            if not item.product:
                continue

            product = item.product
            required = item.quantity
            current = OrderInventoryService._get_current_stock(
                product, default_warehouse
            )

            is_available = current >= required
            shortage = max(0, required - current)

            availability["items"].append(
                {
                    "product": product,
                    "product_name": product.name,
                    "required": required,
                    "available": current,
                    "is_available": is_available,
                    "shortage": shortage,
                }
            )

            if not is_available:
                availability["all_available"] = False
                availability["total_shortage"] += shortage

        return availability

    @staticmethod
    def _get_current_stock(product, warehouse):
        """الحصول على المخزون الحالي"""
        from inventory.models import StockTransaction

        last_trans = (
            StockTransaction.objects.filter(product=product, warehouse=warehouse)
            .order_by("-transaction_date", "-id")
            .first()
        )

        return last_trans.running_balance if last_trans else Decimal("0")

    @staticmethod
    def _create_low_stock_alert(product, current_stock, user=None):
        """إنشاء تنبيه مخزون منخفض"""
        from inventory.models import StockAlert

        # التحقق من عدم وجود تنبيه نشط
        existing = StockAlert.objects.filter(
            product=product, alert_type="low_stock", status="active"
        ).first()

        if not existing:
            StockAlert.objects.create(
                product=product,
                alert_type="low_stock",
                priority="medium",
                title=f"مخزون منخفض: {product.name}",
                message=f"الكمية الحالية ({current_stock}) أقل من الحد الأدنى ({product.minimum_stock})",
                quantity_after=current_stock,
                threshold_limit=product.minimum_stock,
                created_by=user,
            )

    @staticmethod
    def _create_out_of_stock_alert(product, user=None):
        """إنشاء تنبيه نفاد المخزون"""
        from inventory.models import StockAlert

        # التحقق من عدم وجود تنبيه نشط
        existing = StockAlert.objects.filter(
            product=product, alert_type="out_of_stock", status="active"
        ).first()

        if not existing:
            StockAlert.objects.create(
                product=product,
                alert_type="out_of_stock",
                priority="high",
                is_urgent=True,
                title=f"نفاد المخزون: {product.name}",
                message=f"المنتج {product.name} نفد من المخزون!",
                quantity_after=0,
                created_by=user,
            )

    @staticmethod
    def _send_deduction_notification(order, deducted_items, user):
        """إرسال إشعار بخصم المخزون"""
        from notifications.models import Notification

        try:
            items_text = ", ".join(
                [
                    f"{item['product']} ({item['quantity']})"
                    for item in deducted_items[:3]
                ]
            )
            if len(deducted_items) > 3:
                items_text += f" و{len(deducted_items) - 3} منتجات أخرى"

            Notification.objects.create(
                title="تم خصم المخزون",
                message=f"تم خصم المخزون تلقائياً للطلب {order.order_number}: {items_text}",
                notification_type="stock_deduction",
                created_by=user,
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار الخصم: {e}")


# دوال مساعدة للاستخدام السريع
def deduct_order_inventory(order, user=None):
    """خصم المخزون للطلب"""
    return OrderInventoryService.deduct_stock_for_order(order, user)


def restore_order_inventory(order, user=None, reason="إلغاء الطلب"):
    """إرجاع المخزون عند إلغاء الطلب"""
    return OrderInventoryService.reverse_stock_for_order(order, user, reason)


def check_order_availability(order):
    """التحقق من توفر المخزون للطلب"""
    return OrderInventoryService.check_stock_availability(order)
