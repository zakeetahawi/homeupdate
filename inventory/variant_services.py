"""
خدمات نظام المتغيرات والتسعير
Variant and Pricing Services
"""

import logging
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class VariantService:
    """
    خدمة إدارة المتغيرات
    """

    # الأنماط الشائعة لفصل كود المتغير
    SEPARATOR_PATTERNS = ["/", "\\", "-C", "/C", "\\C"]

    @staticmethod
    def parse_product_code(full_code: str) -> Tuple[str, str]:
        """
        تحليل كود المنتج إلى كود أساسي وكود متغير

        Args:
            full_code: الكود الكامل مثل "ORION/C 004"

        Returns:
            (base_code, variant_code) مثل ("ORION", "C 004")
        """
        if not full_code:
            return ("", "")

        full_code = full_code.strip()

        # محاولة التقسيم بالأنماط المختلفة
        for separator in ["/", "\\"]:
            if separator in full_code:
                parts = full_code.split(separator, 1)
                if len(parts) == 2:
                    base = parts[0].strip()
                    variant = parts[1].strip()
                    return (base, variant)

        # إذا لم يوجد فاصل، نعتبر الكود كاملاً كأساسي
        return (full_code, "")

    @staticmethod
    def extract_color_code(variant_code: str) -> str:
        """
        استخراج كود اللون من كود المتغير

        Args:
            variant_code: مثل "C 004" أو "C1" أو "OFF WHITE"

        Returns:
            كود اللون مثل "C 004"
        """
        if not variant_code:
            return ""

        # إزالة المسافات الزائدة
        return variant_code.strip()

    @classmethod
    def get_or_create_base_product(cls, code: str, name: str = None, **kwargs):
        """
        الحصول على أو إنشاء منتج أساسي
        """
        from .models import BaseProduct

        base_code, _ = cls.parse_product_code(code)
        if not base_code:
            base_code = code

        base_product, created = BaseProduct.objects.get_or_create(
            code=base_code, defaults={"name": name or base_code, **kwargs}
        )

        return base_product, created

    @classmethod
    def get_or_create_variant(cls, base_product, variant_code: str, **kwargs):
        """
        الحصول على أو إنشاء متغير
        """
        from .models import ColorAttribute, ProductVariant

        if not variant_code:
            variant_code = "DEFAULT"

        # محاولة ربط اللون
        color = None
        color_code = cls.extract_color_code(variant_code)

        # البحث عن اللون في جدول الألوان
        if color_code:
            color = ColorAttribute.objects.filter(
                Q(code__iexact=color_code) | Q(name__iexact=color_code)
            ).first()

        variant, created = ProductVariant.objects.get_or_create(
            base_product=base_product,
            variant_code=variant_code,
            defaults={
                "color": color,
                "color_code": color_code if not color else "",
                **kwargs,
            },
        )

        return variant, created

    @classmethod
    def link_existing_product(cls, product, force_relink=False):
        """
        ربط منتج موجود بنظام المتغيرات الجديد

        Args:
            product: المنتج الموجود
            force_relink: إعادة الربط حتى لو كان مرتبطاً

        Returns:
            (base_product, variant, created)
        """
        from .models import BaseProduct, ProductVariant

        # التحقق من عدم وجود ربط سابق
        if not force_relink:
            existing_variant = ProductVariant.objects.filter(
                legacy_product=product
            ).first()
            if existing_variant:
                return existing_variant.base_product, existing_variant, False

        # تحليل اسم المنتج (وليس الكود)
        base_name, variant_code = cls.parse_product_code(product.name)

        if not base_name:
            # إذا لم يمكن تحليل الاسم، استخدم الاسم كاملاً
            base_name = product.name
            variant_code = "DEFAULT"

        # إنشاء أو الحصول على المنتج الأساسي
        # نستخدم filter().first() بدلاً من get_or_create لنتحكم في الـ flags قبل save()
        base_product = BaseProduct.objects.filter(code=base_name).first()
        bp_created = False

        if not base_product:
            # إنشاء يدوي مع تعيين الـ flags قبل save()
            base_product = BaseProduct(
                code=base_name,
                name=base_name,
                base_price=product.price,
                currency=product.currency,
                unit=product.unit,
                category=product.category,
                minimum_stock=product.minimum_stock,
            )
            # تعيين الـ flags قبل save()
            base_product._skip_cloudflare_sync = True
            base_product._skip_qr_generation = True
            base_product.save()
            bp_created = True
        else:
            # تعيين الـ flags على المنتج الموجود
            base_product._skip_cloudflare_sync = True
            base_product._skip_qr_generation = True

        # إنشاء أو الحصول على المتغير
        if not variant_code:
            variant_code = "DEFAULT"

        # التحقق من عدم وجود متغير بنفس الكود مرتبط بمنتج آخر
        existing_variant = ProductVariant.objects.filter(
            base_product=base_product, variant_code=variant_code
        ).first()

        if existing_variant:
            # إذا كان المتغير موجود ومرتبط بمنتج مختلف
            if (
                existing_variant.legacy_product
                and existing_variant.legacy_product != product
            ):
                # إنشاء variant_code فريد بإضافة الـ ID
                variant_code = f"{variant_code}_{product.id}"

        # إنشاء أو تحديث المتغير - يدوياً للتحكم في الـ flags
        variant = ProductVariant.objects.filter(
            base_product=base_product, variant_code=variant_code
        ).first()

        v_created = False
        if not variant:
            # إنشاء جديد
            variant = ProductVariant(
                base_product=base_product,
                variant_code=variant_code,
                legacy_product=product,
                color_code=cls.extract_color_code(variant_code.split("_")[0]),
                barcode=product.code,
            )
            # تعيين الـ flag قبل save()
            variant._skip_cloudflare_sync = True
            variant.save()
            v_created = True
        else:
            # تحديث موجود
            variant.legacy_product = product
            variant.color_code = cls.extract_color_code(variant_code.split("_")[0])
            variant.barcode = product.code
            # تعيين الـ flag قبل save()
            variant._skip_cloudflare_sync = True
            variant.save()

        return base_product, variant, (bp_created or v_created)

    @classmethod
    def migrate_all_products(cls, batch_size=100, dry_run=False):
        """
        ترحيل جميع المنتجات الموجودة إلى نظام المتغيرات

        Args:
            batch_size: حجم الدفعة
            dry_run: تجربة بدون حفظ

        Returns:
            dict مع إحصائيات الترحيل
        """
        from .models import Product, ProductVariant

        stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": [],
            "base_products_created": 0,
            "variants_created": 0,
        }

        # المنتجات غير المرتبطة
        unlinked_products = Product.objects.exclude(
            id__in=ProductVariant.objects.filter(
                legacy_product__isnull=False
            ).values_list("legacy_product_id", flat=True)
        )

        stats["total"] = unlinked_products.count()

        if dry_run:
            logger.info(f"[DRY RUN] سيتم ترحيل {stats['total']} منتج")
            return stats

        logger.info(f"🚀 بدء ترحيل {stats['total']} منتج (بدون QR أو مزامنة)")

        migrated_base_products = []

        for product in unlinked_products.iterator(chunk_size=batch_size):
            try:
                base, variant, created = cls.link_existing_product(product)
                if created:
                    stats["migrated"] += 1
                    if base:
                        stats["base_products_created"] += 1
                        migrated_base_products.append(base.id)
                    stats["variants_created"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                stats["errors"].append(
                    {"product_id": product.id, "code": product.code, "error": str(e)}
                )
                logger.error(f"خطأ في ترحيل المنتج {product.id}: {e}")

        logger.info(f"✅ اكتمل الترحيل: {stats['migrated']} منتج")

        # المرحلة 2: توليد QR للمنتجات الأساسية
        if migrated_base_products:
            from .models import BaseProduct

            logger.info(
                f"📊 بدء توليد QR لـ {len(migrated_base_products)} منتج أساسي..."
            )
            qr_generated = 0
            for base_id in migrated_base_products:
                try:
                    base = BaseProduct.objects.get(id=base_id)
                    if base.generate_qr(force=True):
                        qr_generated += 1
                except Exception as e:
                    logger.error(f"خطأ في توليد QR للمنتج {base_id}: {e}")

            logger.info(f"✅ تم توليد {qr_generated} QR")
            stats["qr_generated"] = qr_generated

        # المرحلة 3: مزامنة Cloudflare
        if migrated_base_products:
            from .models import BaseProduct

            logger.info(
                f"☁️ بدء مزامنة Cloudflare لـ {len(migrated_base_products)} منتج..."
            )
            try:
                from public.cloudflare_sync import (
                    get_cloudflare_sync,
                    sync_product_to_cloudflare,
                )

                if get_cloudflare_sync().is_configured():
                    synced = 0
                    for base_id in migrated_base_products:
                        try:
                            base = BaseProduct.objects.get(id=base_id)
                            sync_product_to_cloudflare(base)
                            synced += 1
                        except Exception as e:
                            logger.error(f"خطأ في مزامنة المنتج {base_id}: {e}")

                    logger.info(f"✅ تم مزامنة {synced} منتج مع Cloudflare")
                    stats["cloudflare_synced"] = synced
                else:
                    logger.warning("⚠️ Cloudflare غير مُعد - تم تخطي المزامنة")
                    stats["cloudflare_synced"] = 0
            except Exception as e:
                logger.error(f"خطأ في مزامنة Cloudflare: {e}")
                stats["cloudflare_synced"] = 0

        return stats

    @classmethod
    def phase1_migrate_products(cls, batch_size=100):
        """
        المرحلة 1: ترحيل المنتجات فقط (بدون QR أو مزامنة)

        Returns:
            dict مع إحصائيات + base_product_ids للمراحل التالية
        """
        from .models import Product, ProductVariant

        stats = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "errors": [],
            "base_product_ids": [],
        }

        unlinked_products = Product.objects.exclude(
            id__in=ProductVariant.objects.filter(
                legacy_product__isnull=False
            ).values_list("legacy_product_id", flat=True)
        )

        stats["total"] = unlinked_products.count()
        logger.info(f"🚀 المرحلة 1: بدء ترحيل {stats['total']} منتج")

        for product in unlinked_products.iterator(chunk_size=batch_size):
            try:
                base, variant, created = cls.link_existing_product(product)
                if created:
                    stats["migrated"] += 1
                    if base:
                        stats["base_product_ids"].append(base.id)
                else:
                    stats["skipped"] += 1
            except Exception as e:
                stats["errors"].append(
                    {"product_id": product.id, "code": product.code, "error": str(e)}
                )
                logger.error(f"خطأ في ترحيل المنتج {product.id}: {e}")

        logger.info(f"✅ المرحلة 1 اكتملت: {stats['migrated']} منتج")
        return stats

    @classmethod
    def phase2_generate_qr(cls, base_product_ids):
        """
        المرحلة 2: توليد QR للمنتجات المرحلة
        """
        from .models import BaseProduct

        stats = {
            "total": len(base_product_ids),
            "generated": 0,
            "failed": 0,
            "errors": [],
        }

        logger.info(f"📊 المرحلة 2: بدء توليد QR لـ {stats['total']} منتج")

        for base_id in base_product_ids:
            try:
                base = BaseProduct.objects.get(id=base_id)
                if base.generate_qr(force=True):
                    stats["generated"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append({"base_product_id": base_id, "error": str(e)})
                logger.error(f"خطأ في توليد QR للمنتج {base_id}: {e}")

        logger.info(f"✅ المرحلة 2 اكتملت: {stats['generated']} QR")
        return stats

    @classmethod
    def phase3_sync_cloudflare(cls, base_product_ids):
        """
        المرحلة 3: مزامنة Cloudflare للمنتجات المرحلة
        """
        from .models import BaseProduct

        stats = {
            "total": len(base_product_ids),
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        logger.info(f"☁️ المرحلة 3: بدء مزامنة Cloudflare لـ {stats['total']} منتج")

        try:
            from public.cloudflare_sync import (
                get_cloudflare_sync,
                sync_product_to_cloudflare,
            )

            if not get_cloudflare_sync().is_configured():
                logger.warning("⚠️ Cloudflare غير مُعد - تم تخطي المزامنة")
                stats["skipped"] = stats["total"]
                return stats

            for base_id in base_product_ids:
                try:
                    base = BaseProduct.objects.get(id=base_id)
                    sync_product_to_cloudflare(base)
                    stats["synced"] += 1
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append(
                        {"base_product_id": base_id, "error": str(e)}
                    )
                    logger.error(f"خطأ في مزامنة المنتج {base_id}: {e}")

            logger.info(f"✅ المرحلة 3 اكتملت: {stats['synced']} منتج")
        except Exception as e:
            logger.error(f"خطأ عام في مزامنة Cloudflare: {e}")
            stats["failed"] = stats["total"]
            stats["errors"].append({"error": str(e)})

        return stats

    @classmethod
    def find_related_variants(cls, product_code: str):
        """
        البحث عن المتغيرات المرتبطة بمنتج معين

        Args:
            product_code: كود المنتج (أساسي أو كامل)

        Returns:
            QuerySet من ProductVariant
        """
        from .models import BaseProduct, ProductVariant

        base_code, _ = cls.parse_product_code(product_code)

        try:
            base_product = BaseProduct.objects.get(code=base_code)
            return base_product.variants.filter(is_active=True)
        except BaseProduct.DoesNotExist:
            return ProductVariant.objects.none()

    @classmethod
    def get_variant_stock_summary(cls, variant):
        """
        الحصول على ملخص مخزون المتغير
        """
        from .models import Warehouse

        summary = {
            "total_stock": 0,
            "warehouses": [],
            "status": "out_of_stock",
        }

        stock_by_warehouse = variant.get_stock_by_warehouse()

        for wh_id, data in stock_by_warehouse.items():
            summary["warehouses"].append(
                {
                    "id": wh_id,
                    "name": data["warehouse"].name,
                    "quantity": data["quantity"],
                }
            )
            summary["total_stock"] += data["quantity"]

        # تحديد الحالة
        min_stock = variant.base_product.minimum_stock
        if summary["total_stock"] <= 0:
            summary["status"] = "out_of_stock"
        elif summary["total_stock"] <= min_stock:
            summary["status"] = "low_stock"
        else:
            summary["status"] = "in_stock"

        return summary


class PricingService:
    """
    خدمة إدارة التسعير
    """

    @staticmethod
    def get_variant_price(variant, include_history=False):
        """
        الحصول على سعر المتغير مع تفاصيل
        """
        result = {
            "effective_price": float(variant.effective_price),
            "base_price": float(variant.base_product.base_price),
            "has_override": variant.has_custom_price,
            "price_override": (
                float(variant.price_override) if variant.price_override else None
            ),
            "currency": variant.base_product.currency,
        }

        if include_history:
            result["history"] = list(
                variant.price_history.order_by("-changed_at")[:10].values(
                    "old_price", "new_price", "change_type", "changed_at"
                )
            )

        return result

    @classmethod
    def update_variant_price(
        cls, variant, new_price, user=None, notes="", sync_legacy=True
    ):
        """
        تحديث سعر متغير محدد

        Args:
            sync_legacy: مزامنة السعر مع المنتج القديم
        """
        from .models import PriceHistory

        old_price = variant.effective_price

        with transaction.atomic():
            variant.price_override = Decimal(str(new_price))
            variant.save()

            # تسجيل التغيير
            PriceHistory.objects.create(
                variant=variant,
                old_price=old_price,
                new_price=new_price,
                change_type="manual",
                changed_by=user,
                notes=notes,
            )

            # مزامنة مع المنتج القديم
            if sync_legacy and variant.legacy_product:
                cls._sync_legacy_product_price(variant, new_price)

        return {
            "success": True,
            "old_price": float(old_price),
            "new_price": float(new_price),
        }

    @classmethod
    def _sync_legacy_product_price(cls, variant, new_price=None):
        """
        مزامنة السعر مع المنتج القديم (Product)
        يشمل السعر القطاعي وسعر الجملة
        """
        try:
            legacy = variant.legacy_product
            if legacy:
                # تحديث السعر القطاعي
                retail_price = (
                    Decimal(str(new_price))
                    if new_price is not None
                    else variant.effective_price
                )
                legacy.price = retail_price

                # تحديث سعر الجملة
                legacy.wholesale_price = variant.effective_wholesale_price

                legacy.save(update_fields=["price", "wholesale_price"])
                logger.info(
                    f"✅ تم مزامنة الأسعار للمنتج القديم {legacy.code}: "
                    f"قطاعي({legacy.price}), جملة({legacy.wholesale_price})"
                )
        except Exception as e:
            logger.error(f"❌ خطأ في مزامنة أسعار المنتج القديم: {e}")

    @classmethod
    def reset_variant_price(cls, variant, user=None, notes="", sync_legacy=True):
        """
        إعادة سعر المتغير للسعر الأساسي
        """
        from .models import PriceHistory

        old_price = variant.effective_price
        base_price = variant.base_product.base_price

        with transaction.atomic():
            variant.price_override = None
            variant.save()

            PriceHistory.objects.create(
                variant=variant,
                old_price=old_price,
                new_price=base_price,
                change_type="reset",
                changed_by=user,
                notes=notes,
            )

            # مزامنة مع المنتج القديم
            if sync_legacy and variant.legacy_product:
                cls._sync_legacy_product_price(variant, base_price)

        return {
            "success": True,
            "old_price": float(old_price),
            "new_price": float(base_price),
        }

    @classmethod
    def bulk_update_prices(
        cls,
        base_product,
        update_type: str,
        value: float,
        variant_ids: List[int] = None,
        user=None,
        notes="",
        sync_legacy=True,
    ):
        """
        تحديث أسعار متعددة بالجملة

        Args:
            base_product: المنتج الأساسي
            update_type: 'percentage' | 'fixed' | 'reset' | 'increase' | 'decrease'
            value: القيمة
            variant_ids: قائمة معرفات المتغيرات (None = الكل)
            user: المستخدم
            notes: ملاحظات
            sync_legacy: مزامنة الأسعار مع المنتجات القديمة
        """
        from .models import PriceHistory

        variants = base_product.variants.filter(is_active=True).select_related(
            "legacy_product"
        )
        if variant_ids:
            variants = variants.filter(id__in=variant_ids)

        results = {"updated": 0, "failed": 0, "synced": 0, "details": []}

        with transaction.atomic():
            for variant in variants:
                try:
                    old_price = variant.effective_price

                    if update_type == "percentage":
                        # نسبة مئوية من السعر الحالي
                        percentage = Decimal(str(value))
                        new_price = old_price * (1 + percentage / 100)
                    elif update_type == "increase":
                        # زيادة بمبلغ ثابت
                        new_price = old_price + Decimal(str(value))
                    elif update_type == "decrease":
                        # نقصان بمبلغ ثابت
                        new_price = old_price - Decimal(str(value))
                    elif update_type == "fixed":
                        # سعر ثابت
                        new_price = Decimal(str(value))
                    elif update_type == "reset":
                        # إعادة للأساسي
                        new_price = base_product.base_price
                        variant.price_override = None
                        variant.save()

                        PriceHistory.objects.create(
                            variant=variant,
                            old_price=old_price,
                            new_price=new_price,
                            change_type="reset",
                            changed_by=user,
                            notes=notes,
                        )

                        # مزامنة مع المنتج القديم
                        if sync_legacy and variant.legacy_product:
                            cls._sync_legacy_product_price(variant, new_price)
                            results["synced"] += 1

                        results["updated"] += 1
                        continue
                    else:
                        continue

                    # التأكد من أن السعر موجب
                    if new_price < 0:
                        new_price = Decimal("0")

                    variant.price_override = new_price
                    variant.save()

                    PriceHistory.objects.create(
                        variant=variant,
                        old_price=old_price,
                        new_price=new_price,
                        change_type="bulk",
                        change_value=Decimal(str(value)),
                        changed_by=user,
                        notes=f"{update_type}: {value}"
                        + (f" | {notes}" if notes else ""),
                    )

                    # مزامنة مع المنتج القديم
                    if sync_legacy and variant.legacy_product:
                        cls._sync_legacy_product_price(variant, new_price)
                        results["synced"] += 1

                    results["updated"] += 1
                    results["details"].append(
                        {
                            "variant_id": variant.id,
                            "code": variant.full_code,
                            "old_price": float(old_price),
                            "new_price": float(new_price),
                        }
                    )

                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"خطأ في تحديث سعر المتغير {variant.id}: {e}")

        return results

    @classmethod
    def update_base_price(
        cls, base_product, new_price, apply_to_variants=False, user=None
    ):
        """
        تحديث السعر الأساسي

        Args:
            base_product: المنتج الأساسي
            new_price: السعر الجديد
            apply_to_variants: تطبيق على المتغيرات التي ليس لها سعر مخصص
            user: المستخدم
        """
        from .models import PriceHistory

        old_base_price = base_product.base_price

        with transaction.atomic():
            base_product.base_price = Decimal(str(new_price))
            base_product.save()

            if apply_to_variants:
                # تحديث المتغيرات التي ليس لها سعر مخصص
                variants_to_update = base_product.variants.filter(
                    is_active=True, price_override__isnull=True
                )

                for variant in variants_to_update:
                    PriceHistory.objects.create(
                        variant=variant,
                        old_price=old_base_price,
                        new_price=new_price,
                        change_type="bulk",
                        changed_by=user,
                        notes="تحديث السعر الأساسي",
                    )

                    # مزامنة مع المنتج القديم
                    if variant.legacy_product:
                        cls._sync_legacy_product_price(variant, new_price)

        return {
            "success": True,
            "old_price": float(old_base_price),
            "new_price": float(new_price),
        }


class StockService:
    """
    خدمة إدارة المخزون للمتغيرات
    """

    @classmethod
    def get_variant_stock(cls, variant, warehouse=None):
        """
        الحصول على مخزون المتغير
        """
        if warehouse:
            stock = variant.warehouse_stocks.filter(warehouse=warehouse).first()
            return float(stock.current_quantity) if stock else 0

        return variant.current_stock

    @classmethod
    def update_variant_stock(
        cls,
        variant,
        warehouse,
        quantity_change,
        transaction_type="adjustment",
        reason="other",
        user=None,
        notes="",
    ):
        """
        تحديث مخزون المتغير

        Args:
            variant: المتغير
            warehouse: المستودع
            quantity_change: التغيير في الكمية (موجب للوارد، سالب للصادر)
            transaction_type: نوع الحركة
            reason: السبب
            user: المستخدم
            notes: ملاحظات
        """
        from .models import StockTransaction, VariantStock

        with transaction.atomic():
            # تحديث VariantStock
            stock, created = VariantStock.objects.get_or_create(
                variant=variant, warehouse=warehouse, defaults={"current_quantity": 0}
            )

            new_quantity = stock.current_quantity + Decimal(str(quantity_change))
            if new_quantity < 0:
                raise ValueError(f"الكمية المتاحة غير كافية: {stock.current_quantity}")

            stock.current_quantity = new_quantity
            stock.save()

            # إذا كان المتغير مرتبطاً بمنتج قديم، تحديث StockTransaction أيضاً
            if variant.legacy_product:
                StockTransaction.objects.create(
                    product=variant.legacy_product,
                    warehouse=warehouse,
                    transaction_type="in" if quantity_change > 0 else "out",
                    reason=reason,
                    quantity=abs(quantity_change),
                    notes=notes,
                    created_by=user,
                )

        return {
            "success": True,
            "new_quantity": float(new_quantity),
            "variant": variant.full_code,
            "warehouse": warehouse.name,
        }

    @classmethod
    def transfer_variant_stock(
        cls, variant, from_warehouse, to_warehouse, quantity, user=None, notes=""
    ):
        """
        نقل مخزون متغير بين مستودعين
        """
        from .models import VariantStock

        with transaction.atomic():
            # التحقق من توفر الكمية في المستودع المصدر
            source_stock = VariantStock.objects.filter(
                variant=variant, warehouse=from_warehouse
            ).first()

            if not source_stock or source_stock.current_quantity < quantity:
                available = source_stock.current_quantity if source_stock else 0
                raise ValueError(
                    f"الكمية المتاحة ({available}) أقل من المطلوبة ({quantity})"
                )

            # خصم من المصدر
            source_stock.current_quantity -= Decimal(str(quantity))
            source_stock.save()

            # إضافة للوجهة
            dest_stock, created = VariantStock.objects.get_or_create(
                variant=variant,
                warehouse=to_warehouse,
                defaults={"current_quantity": 0},
            )
            dest_stock.current_quantity += Decimal(str(quantity))
            dest_stock.save()

            # إذا مرتبط بمنتج قديم
            if variant.legacy_product:
                from .models import StockTransaction

                # صادر من المصدر
                StockTransaction.objects.create(
                    product=variant.legacy_product,
                    warehouse=from_warehouse,
                    transaction_type="out",
                    reason="transfer",
                    quantity=quantity,
                    notes=f"نقل إلى {to_warehouse.name}"
                    + (f" | {notes}" if notes else ""),
                    created_by=user,
                )

                # وارد للوجهة
                StockTransaction.objects.create(
                    product=variant.legacy_product,
                    warehouse=to_warehouse,
                    transaction_type="in",
                    reason="transfer",
                    quantity=quantity,
                    notes=f"نقل من {from_warehouse.name}"
                    + (f" | {notes}" if notes else ""),
                    created_by=user,
                )

        return {
            "success": True,
            "quantity": float(quantity),
            "from_warehouse": from_warehouse.name,
            "to_warehouse": to_warehouse.name,
        }

    @classmethod
    def get_low_stock_variants(cls, threshold_percentage=100):
        """
        الحصول على المتغيرات ذات المخزون المنخفض

        Args:
            threshold_percentage: نسبة الحد الأدنى (100 = على الحد، 50 = نصف الحد)
        """
        from .models import ProductVariant

        low_stock = []

        for variant in ProductVariant.objects.filter(is_active=True).select_related(
            "base_product"
        ):
            current = variant.current_stock
            minimum = variant.base_product.minimum_stock
            threshold = minimum * threshold_percentage / 100

            if current <= threshold:
                low_stock.append(
                    {
                        "variant": variant,
                        "current_stock": current,
                        "minimum_stock": minimum,
                        "percentage": (current / minimum * 100) if minimum > 0 else 0,
                    }
                )

        return sorted(low_stock, key=lambda x: x["percentage"])
