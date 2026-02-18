import logging
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

# تعريف logger مبكراً لتجنب NameError
logger = logging.getLogger(__name__)

from accounts.models import SystemSettings, User
from notifications.models import Notification

from .models import BaseProduct, Product, ProductVariant, StockAlert, StockTransaction


@receiver(post_save, sender=SystemSettings)
def update_currency_on_settings_change(sender, instance, **kwargs):
    """تحديث العملة لجميع المنتجات عند تغيير إعدادات النظام"""

    def update_products():
        if hasattr(instance, "currency") and instance.currency:
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
def stock_manager_handler(sender, instance, created, **kwargs):
    """
    المعالج الرئيسي لكل المعاملات المخزنية: تحديث الأرصدة والتنبيهات
    """
    if not created:
        return

    current_balance = instance.running_balance

    # ✅ حماية: منع السحب من مستودع فارغ
    if instance.transaction_type == "out":
        last_trans = (
            StockTransaction.objects.filter(
                product=instance.product, warehouse=instance.warehouse
            )
            .exclude(id=instance.id)
            .order_by("-transaction_date")
            .first()
        )

        if not last_trans:
            logger.error(
                f"❌ محاولة سحب من مستودع فارغ! "
                f"المنتج: {instance.product.name} ({instance.product.code}) "
                f"المستودع: {instance.warehouse.name} "
                f"الكمية: {instance.quantity}"
            )
            instance.delete()
            return

        if last_trans.running_balance < instance.quantity:
            logger.error(
                f"❌ رصيد غير كافٍ! "
                f"المنتج: {instance.product.name} ({instance.product.code}) "
                f"المستودع: {instance.warehouse.name} "
                f"الرصيد المتاح: {last_trans.running_balance} "
                f"الكمية المطلوبة: {instance.quantity}"
            )

    # ✅ حماية: منع إدخال منتج في مستودع جديد إذا كان موجوداً في مستودع آخر
    if instance.transaction_type == "in":
        other_warehouse_trans = (
            StockTransaction.objects.filter(product=instance.product)
            .exclude(warehouse=instance.warehouse)
            .select_related('warehouse')  # ✅ تحميل المستودع مسبقاً
            .order_by("-transaction_date")
            .first()
        )

        if other_warehouse_trans and other_warehouse_trans.running_balance > 0:
            warehouse_name = other_warehouse_trans.warehouse.name if other_warehouse_trans.warehouse else "غير معروف"
            logger.warning(
                f"⚠️ المنتج {instance.product.name} ({instance.product.code}) "
                f"موجود بالفعل في مستودع {warehouse_name} "
                f"برصيد {other_warehouse_trans.running_balance}. "
                f"يتم الآن إدخاله في مستودع {instance.warehouse.name}. "
                f"يُفضل استخدام عملية نقل (transfer) بدلاً من الإدخال المباشر."
            )

    def process_transaction():
        from decimal import Decimal

        from .models import Warehouse

        # ✅ تحديث الأرصدة المتحركة - مع اعتبار المستودع
        previous_balance = (
            StockTransaction.objects.filter(
                product=instance.product,
                warehouse=instance.warehouse,  # إضافة فلتر المستودع
                transaction_date__lt=instance.transaction_date,
            )
            .exclude(id=instance.id)
            .order_by("-transaction_date", "-id")
            .first()
        )

        if previous_balance and previous_balance.running_balance is not None:
            current_balance = Decimal(str(previous_balance.running_balance))
        else:
            current_balance = Decimal("0")

        quantity_decimal = Decimal(str(instance.quantity))

        if instance.transaction_type == "in":
            new_balance = current_balance + quantity_decimal
        else:
            new_balance = current_balance - quantity_decimal

        # تحديث الرصيد للمعاملة الحالية
        StockTransaction.objects.filter(id=instance.id).update(
            running_balance=new_balance
        )

        # ✅ تحديث الأرصدة اللاحقة - لنفس المستودع فقط
        subsequent_transactions = (
            StockTransaction.objects.filter(
                product=instance.product,
                warehouse=instance.warehouse,  # إضافة فلتر المستودع
                transaction_date__gt=instance.transaction_date,
            )
            .exclude(id=instance.id)
            .order_by("transaction_date", "id")
        )

        running_balance = new_balance
        for trans in subsequent_transactions:
            trans_quantity = Decimal(str(trans.quantity))
            if trans.transaction_type == "in":
                running_balance += trans_quantity
            else:
                running_balance -= trans_quantity
            StockTransaction.objects.filter(id=trans.id).update(
                running_balance=running_balance
            )

        # ✅ فحص مستويات المخزون وإنشاء/حل التنبيهات
        # حساب المخزون الكلي من جميع المستودعات
        total_stock = 0
        for warehouse in Warehouse.objects.filter(is_active=True):
            last_trans = (
                StockTransaction.objects.filter(
                    product=instance.product, warehouse=warehouse
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            if last_trans and last_trans.running_balance:
                total_stock += float(last_trans.running_balance)

        # ✅ حل التنبيهات الخاطئة أولاً (إذا أصبح المنتج متوفراً)
        if total_stock > 0:
            from django.utils import timezone

            resolved_count = StockAlert.objects.filter(
                product=instance.product, alert_type="out_of_stock", status="active"
            ).update(
                status="resolved",
                resolved_at=timezone.now(),
                resolved_by=getattr(instance, "created_by", None),
            )
            if resolved_count > 0:
                logger.info(
                    f"✅ تم حل {resolved_count} تنبيه نفاذ للمنتج {instance.product.name} (المخزون الجديد: {total_stock})"
                )

        # إنشاء تنبيه جديد إذا لزم الأمر
        alert_data = should_create_stock_alert(instance.product.id, total_stock)

        if alert_data:
            create_stock_alert_and_notification(
                product=instance.product,
                alert_data=alert_data,
                user=getattr(instance, "created_by", None),
            )

    transaction.on_commit(process_transaction)


# ========== نظام التنبيهات التلقائية للمخزون ========== *


def should_create_stock_alert(product_id, new_balance):
    """
    التحقق مما إذا كان يجب إنشاء تنبيه مخزون
    """
    try:
        product = Product.objects.get(id=product_id)

        # إذا نفد المخزون تماماً
        if new_balance <= 0:
            return {
                "type": "out_of_stock",
                "priority": "high",
                "title": f"نفذ المخزون: {product.name}",
                "message": f"المنتج {product.name} ({product.code}) نفد من المخزون تماماً",
                "threshold": 0,
                "current_balance": new_balance,
            }

        # إذا كان المخزون منخفض
        elif new_balance <= product.minimum_stock:
            return {
                "type": "low_stock",
                "priority": "medium" if new_balance > 0 else "high",
                "title": f"مخزون منخفض: {product.name}",
                "message": f"المنتج {product.name} ({product.code}) وصل للمستوى الحد الأدنى. الكمية الحالية: {new_balance}",
                "threshold": product.minimum_stock,
                "current_balance": new_balance,
            }

        # إذا كان المخزون فائضاً (مرتفع جداً)
        elif (
            hasattr(product, "maximum_stock")
            and product.maximum_stock
            and new_balance > product.maximum_stock
        ):
            return {
                "type": "overstock",
                "priority": "low",
                "title": f"فائض في المخزون: {product.name}",
                "message": f"المنتج {product.name} ({product.code}) تجاوز الحد الأعلى. الكمية الحالية: {new_balance}",
                "threshold": product.maximum_stock,
                "current_balance": new_balance,
            }

        return None

    except Exception as e:
        logger.error(f"Error in should_create_stock_alert: {e}")
        return None


def create_stock_alert_and_notification(product, alert_data, user=None):
    """
    إنشاء تنبيه المخزون والإشعار المقابل
    """
    try:
        # ✅ أولاً: حل التنبيهات الخاطئة (المنتج متوفر لكن عليه تنبيه نفاذ)
        if alert_data["type"] != "out_of_stock" and alert_data["current_balance"] > 0:
            # حل تنبيهات النفاذ إذا أصبح المنتج متوفراً
            StockAlert.objects.filter(
                product=product, alert_type="out_of_stock", status="active"
            ).update(status="resolved", resolved_at=timezone.now(), resolved_by=user)

        # التحقق من عدم وجود تنبيه نشط مؤخر من نفس النوع
        existing_alert = StockAlert.objects.filter(
            product=product, alert_type=alert_data["type"], status="active"
        ).first()

        if existing_alert:
            # تحديث التنبيه الموجود بدلاً من إنشاء جديد
            existing_alert.message = alert_data["message"]
            existing_alert.created_at = timezone.now()
            existing_alert.quantity_after = alert_data["current_balance"]
            existing_alert.save()
            return existing_alert

        # إنشاء تنبيه جديد
        alert = StockAlert.objects.create(
            product=product,
            alert_type=alert_data["type"],
            priority=alert_data["priority"],
            title=alert_data["title"],
            message=alert_data["message"],
            description=alert_data["message"],  # إضافة الوصف
            quantity_before=alert_data["current_balance"],
            quantity_after=alert_data["current_balance"],
            threshold_limit=alert_data.get("threshold", 0),
            created_by=user,
        )

        # إنشاء الإشعار المقابل
        create_notification_for_alert(alert, product, alert_data, user)

        return alert

    except Exception as e:
        logger.error(f"Error creating stock alert: {e}")
        return None


def create_notification_for_alert(alert, product, alert_data, user=None):
    """
    إنشاء إشعار للمسؤولين والمستخدمين المعنيين
    """
    try:
        if user:
            message_body = f"{alert_data['message']} (تم إنشاؤه بواسطة: {user.get_full_name() or user.username})"
        else:
            message_body = alert_data["message"]

        # الحصول على المحتوى المرتبط (المنتج)
        try:
            product_content_type = ContentType.objects.get_for_model(Product)
        except Exception:
            product_content_type = None

        # إنشاء الإشعار الرئيسي
        notification = Notification.objects.create(
            title=alert_data["title"],
            message=message_body,
            notification_type="stock_shortage",
            created_by=user,
            # ربط بالمنتج إذا أمكن
            content_type=product_content_type,
            object_id=product.id,
        )

        # تحديد المستخدمين الذين سيظهرون لهم الإشعار
        notified_users = []

        # إشعار مدير المستودع إذا كان المنتج مرتبط بمستودع محدد
        if (
            hasattr(product, "warehouse")
            and product.warehouse
            and product.warehouse.manager
        ):
            notified_users.append(product.warehouse.manager)

        # إشعار مسؤولي المخزون
        warehouse_managers = User.objects.filter(
            groups__name__in=["مسؤول مستودع", "مسؤول المخازن", "Warehouse Manager"],
            is_active=True,
        ).distinct()
        notified_users.extend(warehouse_managers)

        # إشعار المسؤولين
        admins = User.objects.filter(is_superuser=True, is_active=True)
        notified_users.extend(admins)

        # إشعار المستخدم الذي قام بالعملية (إذا لم يكن مدرجاً بالفعل)
        if user and user not in notified_users:
            notification.visible_to.set(notified_users)

        # تحديد أولوية الإشعار بناءً على أولوية التنبيه
        if alert_data["priority"] == "high":
            notification.is_urgent = True
            notification.is_pinned = True

        notification.save()

        logger.info(
            f"✅ Created stock notification for {product.name}: {alert_data['title']}"
        )

    except Exception as e:
        logger.error(f"Error creating notification: {e}")


@staticmethod
def create_bulk_stock_alerts():
    """
    دالة مساعدة للتحقق من جميع المنتجات وإنشاء التنبيهات اللازمة
    """
    try:
        from inventory.inventory_utils import get_cached_stock_level

        alerts_created = 0

        products = Product.objects.all()
        for product in products:
            current_stock = get_cached_stock_level(product.id)
            alert_data = should_create_stock_alert(product.id, current_stock)

            if alert_data:
                alert = create_stock_alert_and_notification(product, alert_data)
                if alert:
                    alerts_created += 1

        logger.info(f"✅ Created {alerts_created} stock alerts from bulk check")
        return alerts_created

    except Exception as e:
        logger.error(f"Error in create_bulk_stock_alerts: {e}")
        return 0


# ========== Cloudflare Auto-Sync Signals ==========


@receiver(post_save, sender=BaseProduct)
def sync_base_product_to_cloudflare(sender, instance, **kwargs):
    """
    مزامنة المنتج الأساسي تلقائياً مع Cloudflare عند التعديل
    Sync BaseProduct explicitly on save (triggers on price change, name change, etc.)
    """
    # تخطي المزامنة أثناء عمليات الترحيل الجماعي
    if getattr(instance, "_skip_cloudflare_sync", False):
        return

    # تجنب المزامنة إذا لم يكن هناك كود
    if not instance.code:
        return

    def do_sync():
        try:
            # Import inside function to avoid circular imports
            from public.cloudflare_sync import (
                get_cloudflare_sync,
                sync_product_to_cloudflare,
            )

            # Check if sync is enabled globally
            if not get_cloudflare_sync().is_configured():
                return

            sync_product_to_cloudflare(instance)
            logger.info(f"✅ Auto-synced BaseProduct {instance.code} to Cloudflare")
        except Exception as e:
            logger.error(f"❌ Failed to auto-sync BaseProduct {instance.code}: {e}")

    # Use on_commit to ensure DB transaction is finished
    transaction.on_commit(do_sync)


@receiver(post_save, sender=BaseProduct)
def sync_base_product_prices_to_legacy(sender, instance, **kwargs):
    """
    مزامنة أسعار المنتج الأساسي (قطاعي وجملة) مع المنتجات القديمة
    عندما يتغير السعر الأساسي، نقوم بمزامنة كل المتغيرات التي تعتمد عليه.
    """
    # تخطي المزامنة أثناء عمليات الترحيل الجماعي
    if getattr(instance, "_skip_legacy_sync", False):
        return

    def do_sync():
        try:
            from .variant_services import PricingService

            # تحديث كل المتغيرات المرتبطة التي ليس لها سعر مخصص
            variants = instance.variants.filter(
                is_active=True,
                price_override__isnull=True,
                wholesale_price_override__isnull=True,
            ).select_related("legacy_product")

            for variant in variants:
                if variant.legacy_product:
                    PricingService._sync_legacy_product_price(variant)

            logger.info(
                f"✅ تم مزامنة أسعار {variants.count()} من المنتجات القديمة لـ {instance.code}"
            )
        except Exception as e:
            logger.error(
                f"❌ فشل في مزامنة أسعار BaseProduct {instance.code} مع القديم: {e}"
            )

    transaction.on_commit(do_sync)


@receiver(post_save, sender=ProductVariant)
def sync_variant_prices_to_legacy(sender, instance, **kwargs):
    """
    مزامنة أسعار المتغير (قطاعي وجملة) مع المنتج القديم المرتبط به مباشرة
    """
    # تخطي المزامنة أثناء عمليات الترحيل الجماعي
    if getattr(instance, "_skip_legacy_sync", False):
        return

    if not instance.legacy_product:
        return

    def do_sync():
        try:
            from .variant_services import PricingService

            PricingService._sync_legacy_product_price(instance)
            logger.info(
                f"✅ تم مزامنة أسعار المتغير {instance.variant_code} مع المنتج القديم {instance.legacy_product.code}"
            )
        except Exception as e:
            logger.error(
                f"❌ فشل في مزامنة أسعار Variant {instance.variant_code} مع القديم: {e}"
            )

    transaction.on_commit(do_sync)


@receiver(post_save, sender=ProductVariant)
def sync_variant_parent_to_cloudflare(sender, instance, **kwargs):
    """
    عند تعديل متغير (سعر، مخزون، الخ)، يتم تحديث المنتج الأساسي في Cloudflare
    Sync parent BaseProduct when variant is updated
    """
    # تخطي المزامنة أثناء عمليات الترحيل الجماعي
    if getattr(instance, "_skip_cloudflare_sync", False):
        return

    if not instance.base_product or not instance.base_product.code:
        return

    def do_sync():
        try:
            from public.cloudflare_sync import (
                get_cloudflare_sync,
                sync_product_to_cloudflare,
            )

            if not get_cloudflare_sync().is_configured():
                return

            # Sync the PARENT BaseProduct because KV structure is based on BaseProduct
            sync_product_to_cloudflare(instance.base_product)
            logger.info(
                f"✅ Auto-synced BaseProduct {instance.base_product.code} (triggered by Variant {instance.variant_code})"
            )
        except Exception as e:
            logger.error(f"❌ Failed to auto-sync BaseProduct from Variant update: {e}")

    transaction.on_commit(do_sync)
