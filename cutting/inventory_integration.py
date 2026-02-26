"""
نظام تكامل التقطيع مع المخزون
إدارة خصم المخزون التلقائي وحركة الأصناف
"""

import logging
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from inventory.models import Product, StockTransaction
from inventory.models import Warehouse as InventoryWarehouse
from django.contrib.contenttypes.models import ContentType

from notifications.models import Notification

from .models import CuttingOrderItem

logger = logging.getLogger(__name__)


class InventoryIntegrationService:
    """خدمة تكامل التقطيع مع المخزون"""

    @staticmethod
    def process_cutting_completion(cutting_item, user):
        """
        معالجة اكتمال التقطيع وخصم المخزون
        """
        # ✅ BUG-017: التحقق من العناصر الخارجية (order_item = None)
        # عناصر القماش الخارجي (is_external=True) ليس لها order_item → تخطي الخصم
        if not cutting_item.order_item:
            logger.info(
                f"⏭️ تخطي خصم المخزون للعنصر {cutting_item.id} — "
                f"قماش خارجي بدون order_item"
            )
            return None

        if not cutting_item.order_item.product:
            logger.warning(
                f"⚠️ العنصر {cutting_item.id} — order_item موجود لكن بدون product، تخطي الخصم"
            )
            return None

        try:
            with transaction.atomic():
                # التحقق من توفر الكمية في المخزون
                product = cutting_item.order_item.product
                required_quantity = (
                    cutting_item.order_item.quantity + cutting_item.additional_quantity
                )

                # الحصول على المستودع المناسب
                warehouse = InventoryIntegrationService._get_warehouse_for_cutting(
                    cutting_item
                )

                if not warehouse:
                    raise ValueError("لا يمكن تحديد المستودع المناسب للخصم")

                # التحقق من توفر الكمية
                current_stock = InventoryIntegrationService._get_current_stock(
                    product, warehouse
                )

                if current_stock < required_quantity:
                    # إرسال إشعار نقص المخزون
                    InventoryIntegrationService._send_stock_shortage_notification(
                        cutting_item, current_stock, required_quantity, user
                    )

                    # يمكن اختيار إما رفض العملية أو السماح بالخصم مع رصيد سالب
                    # هنا سنسمح بالخصم مع إشعار
                    logger.warning(
                        f"خصم من المخزون بكمية أكبر من المتوفر. "
                        f"المنتج: {product.name}, المطلوب: {required_quantity}, "
                        f"المتوفر: {current_stock}"
                    )

                # إنشاء حركة صادر للمخزون
                stock_transaction = StockTransaction.objects.create(
                    product=product,
                    warehouse=warehouse,
                    transaction_type="out",
                    reason="production",  # سبب الإنتاج/التقطيع
                    quantity=required_quantity,
                    reference=f"تقطيع-{cutting_item.cutting_order.cutting_code}",
                    transaction_date=timezone.now(),
                    notes=f"خصم تلقائي للتقطيع - العميل: {cutting_item.cutting_order.order.customer.name}",
                    created_by=user,
                )

                # تحديث الرصيد المتحرك
                InventoryIntegrationService._update_running_balance(stock_transaction)

                # تسجيل العملية في سجل التقطيع
                cutting_item.inventory_deducted = True
                cutting_item.inventory_transaction = stock_transaction
                cutting_item.save()

                # إرسال إشعار نجاح العملية
                InventoryIntegrationService._send_deduction_success_notification(
                    cutting_item, stock_transaction, user
                )

                logger.info(
                    f"تم خصم المخزون بنجاح. المنتج: {product.name}, "
                    f"الكمية: {required_quantity}, المعاملة: {stock_transaction.id}"
                )

                return stock_transaction

        except Exception as e:
            logger.error(f"خطأ في خصم المخزون: {str(e)}")
            raise

    @staticmethod
    def reverse_cutting_deduction(cutting_item, user, reason="إلغاء التقطيع"):
        """
        عكس عملية خصم المخزون (في حالة إلغاء التقطيع)
        """
        try:
            with transaction.atomic():
                if (
                    not hasattr(cutting_item, "inventory_transaction")
                    or not cutting_item.inventory_transaction
                ):
                    logger.warning(
                        f"لا توجد معاملة مخزون لعكسها للعنصر {cutting_item.id}"
                    )
                    return None

                original_transaction = cutting_item.inventory_transaction
                # ✅ BUG-017: تحقق من order_item قبل الوصول إلى product
                if not cutting_item.order_item or not cutting_item.order_item.product:
                    logger.warning(
                        f"⚠️ عكس خصم العنصر {cutting_item.id} — order_item أو product غير موجود"
                    )
                    return None
                product = cutting_item.order_item.product
                warehouse = original_transaction.warehouse
                quantity = original_transaction.quantity

                # إنشاء حركة وارد لعكس الخصم
                reverse_transaction = StockTransaction.objects.create(
                    product=product,
                    warehouse=warehouse,
                    transaction_type="in",
                    reason="adjustment",
                    quantity=quantity,
                    reference=f"عكس-{original_transaction.reference}",
                    transaction_date=timezone.now(),
                    notes=f"عكس خصم التقطيع - السبب: {reason}",
                    created_by=user,
                )

                # تحديث الرصيد المتحرك
                InventoryIntegrationService._update_running_balance(reverse_transaction)

                # تحديث حالة التقطيع
                cutting_item.inventory_deducted = False
                cutting_item.inventory_transaction = None
                cutting_item.save()

                logger.info(
                    f"تم عكس خصم المخزون. المنتج: {product.name}, "
                    f"الكمية: {quantity}, المعاملة الأصلية: {original_transaction.id}"
                )

                return reverse_transaction

        except Exception as e:
            logger.error(f"خطأ في عكس خصم المخزون: {str(e)}")
            raise

    @staticmethod
    def check_stock_availability(cutting_order):
        """
        التحقق من توفر المخزون لجميع عناصر أمر التقطيع
        """
        availability_report = {"all_available": True, "items": [], "total_shortage": 0}

        for item in cutting_order.items.all():
            # ✅ BUG-017: تخطي العناصر الخارجية بدون order_item
            if not item.order_item or not item.order_item.product:
                availability_report["items"].append(
                    {
                        "item": item,
                        "product": None,
                        "required_quantity": item.additional_quantity,
                        "current_stock": 0,
                        "is_available": True,  # العناصر الخارجية لا تحتاج مخزون
                        "shortage": 0,
                        "warehouse": None,
                        "note": "قماش خارجي — لا يُخصم من المخزون",
                    }
                )
                continue

            product = item.order_item.product
            required_quantity = item.order_item.quantity + item.additional_quantity
            warehouse = InventoryIntegrationService._get_warehouse_for_cutting(item)

            if warehouse:
                current_stock = InventoryIntegrationService._get_current_stock(
                    product, warehouse
                )
                is_available = current_stock >= required_quantity
                shortage = max(0, required_quantity - current_stock)

                item_info = {
                    "item": item,
                    "product": product,
                    "required_quantity": required_quantity,
                    "current_stock": current_stock,
                    "is_available": is_available,
                    "shortage": shortage,
                    "warehouse": warehouse,
                }

                availability_report["items"].append(item_info)

                if not is_available:
                    availability_report["all_available"] = False
                    availability_report["total_shortage"] += shortage
            else:
                # لا يمكن تحديد المستودع
                availability_report["all_available"] = False
                availability_report["items"].append(
                    {
                        "item": item,
                        "product": product,
                        "required_quantity": required_quantity,
                        "current_stock": 0,
                        "is_available": False,
                        "shortage": required_quantity,
                        "warehouse": None,
                        "error": "لا يمكن تحديد المستودع",
                    }
                )

        return availability_report

    @staticmethod
    def _get_warehouse_for_cutting(cutting_item):
        """
        ✅ BUG-013: تحديد المستودع المناسب للخصم مع البحث عن المستودع الذي يحتوي على مخزون
        الأولوية:
        1. المستودع المحدد في الأمر — إذا كان نشطاً وله مخزون
        2. المستودع الذي يحتوي على أعلى رصيد للمنتج
        3. أول مستودع نشط كاحتياطي
        """
        try:
            product = None
            if cutting_item.order_item and cutting_item.order_item.product:
                product = cutting_item.order_item.product

            # 1. المستودع المحدد في الأمر
            if cutting_item.cutting_order and cutting_item.cutting_order.warehouse:
                wh = cutting_item.cutting_order.warehouse
                if getattr(wh, 'is_active', True):
                    if product:
                        # تحقق من وجود رصيد فعلي في هذا المستودع
                        last = (
                            StockTransaction.objects.filter(
                                product=product, warehouse=wh
                            )
                            .order_by("-transaction_date", "-id")
                            .first()
                        )
                        if last and last.running_balance > 0:
                            return wh
                        # لا رصيد في المستودع المحدد — ابحث في مستودعات أخرى
                        logger.warning(
                            f"⚠️ المستودع المحدد ({wh.name}) لا يحتوي على رصيد للمنتج "
                            f"{product.name} — البحث في مستودعات أخرى"
                        )
                    else:
                        return wh  # للعناصر الخارجية: أعد مستودع الأمر مباشرة

            # 2. البحث عن المستودع الذي يحتوي على أعلى رصيد للمنتج
            if product:
                best_wh_trans = (
                    StockTransaction.objects.filter(
                        product=product,
                        warehouse__is_active=True,
                    )
                    .select_related("warehouse")
                    .order_by("-running_balance", "-transaction_date")
                    .first()
                )
                if best_wh_trans and best_wh_trans.running_balance > 0:
                    logger.info(
                        f"✅ تم اختيار المستودع {best_wh_trans.warehouse.name} "
                        f"للمنتج {product.name} (رصيد: {best_wh_trans.running_balance})"
                    )
                    return best_wh_trans.warehouse

            # 3. احتياطي: أول مستودع نشط
            return InventoryWarehouse.objects.filter(is_active=True).first()
        except Exception as e:
            logger.error(f"❌ خطأ في تحديد مستودع التقطيع: {e}")
            return None

    @staticmethod
    def _get_current_stock(product, warehouse):
        """الحصول على المخزون الحالي للمنتج في المستودع"""
        try:
            # حساب الرصيد الحالي من آخر معاملة
            last_transaction = (
                StockTransaction.objects.filter(product=product, warehouse=warehouse)
                .order_by("-transaction_date", "-id")
                .first()
            )

            if last_transaction:
                return last_transaction.running_balance
            else:
                return Decimal("0")
        except Exception:
            return Decimal("0")

    @staticmethod
    def _update_running_balance(transaction):
        """تحديث الرصيد المتحرك للمعاملة"""
        try:
            # الحصول على آخر رصيد
            previous_transaction = (
                StockTransaction.objects.filter(
                    product=transaction.product,
                    warehouse=transaction.warehouse,
                    transaction_date__lt=transaction.transaction_date,
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            previous_balance = (
                previous_transaction.running_balance
                if previous_transaction
                else Decimal("0")
            )

            # حساب الرصيد الجديد
            if transaction.transaction_type == "in":
                new_balance = previous_balance + transaction.quantity
            else:  # out, transfer, adjustment
                new_balance = previous_balance - transaction.quantity

            transaction.running_balance = new_balance
            transaction.save()

            # تحديث الأرصدة للمعاملات اللاحقة
            subsequent_transactions = StockTransaction.objects.filter(
                product=transaction.product,
                warehouse=transaction.warehouse,
                transaction_date__gt=transaction.transaction_date,
            ).order_by("transaction_date", "id")

            current_balance = new_balance
            for trans in subsequent_transactions:
                if trans.transaction_type == "in":
                    current_balance += trans.quantity
                else:
                    current_balance -= trans.quantity

                if trans.running_balance != current_balance:
                    trans.running_balance = current_balance
                    trans.save()

        except Exception as e:
            logger.error(f"خطأ في تحديث الرصيد المتحرك: {str(e)}")

    @staticmethod
    def _send_stock_shortage_notification(
        cutting_item, current_stock, required_quantity, user
    ):
        """إرسال إشعار نقص المخزون"""
        try:
            order_creator = cutting_item.cutting_order.order.created_by
            if order_creator:
                ct = ContentType.objects.get_for_model(cutting_item)
                # ✅ BUG-017: استخدم product من المعامل (تم التحقق منه مسبقاً)
                product_name = (
                    cutting_item.order_item.product.name
                    if cutting_item.order_item and cutting_item.order_item.product
                    else f"عنصر #{cutting_item.id}"
                )
                notification = Notification.objects.create(
                    title="نقص في المخزون",
                    message=f"الصنف {product_name} غير متوفر بالكمية المطلوبة. "
                            f"المطلوب: {required_quantity}, المتوفر: {current_stock}",
                    notification_type="stock_shortage",
                    content_type=ct,
                    object_id=cutting_item.id,
                    created_by=order_creator,
                )
                notification.visible_to.add(order_creator)
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار نقص المخزون: {str(e)}")

    @staticmethod
    def _send_deduction_success_notification(cutting_item, stock_transaction, user):
        """إرسال إشعار نجاح خصم المخزون عند اكتمال التقطيع"""
        try:
            order_creator = cutting_item.cutting_order.order.created_by
            if order_creator:
                ct = ContentType.objects.get_for_model(stock_transaction)
                # ✅ BUG-017: استخدم product_name بشكل آمن
                product_name = (
                    cutting_item.order_item.product.name
                    if cutting_item.order_item and cutting_item.order_item.product
                    else f"عنصر #{cutting_item.id}"
                )
                notification = Notification.objects.create(
                    title="تم خصم المخزون",
                    message=f"تم خصم {stock_transaction.quantity} من {product_name} "
                            f"لأمر التقطيع {cutting_item.cutting_order.cutting_code}",
                    notification_type="cutting_completed",
                    content_type=ct,
                    object_id=stock_transaction.id,
                    created_by=order_creator,
                )
                notification.visible_to.add(order_creator)
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار خصم المخزون: {str(e)}")


def complete_inventory_deduction(cutting_item, user):
    """دالة مساعدة لخصم المخزون عند إكمال التقطيع"""
    return InventoryIntegrationService.process_cutting_completion(cutting_item, user)


def reverse_inventory_deduction(cutting_item, user, reason="إلغاء التقطيع"):
    """دالة مساعدة لعكس خصم المخزون"""
    return InventoryIntegrationService.reverse_cutting_deduction(
        cutting_item, user, reason
    )


def check_cutting_stock_availability(cutting_order):
    """دالة مساعدة للتحقق من توفر المخزون"""
    return InventoryIntegrationService.check_stock_availability(cutting_order)
