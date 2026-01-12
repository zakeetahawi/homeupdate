"""
نظام الرفع TURBO - فائق السرعة
================================
- بدون signals أو cloudflare sync
- bulk operations فقط
- تحديث أسعار سريع
"""

import logging
from decimal import Decimal
from io import BytesIO

import pandas as pd
from celery import shared_task
from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def disable_all_signals():
    """تعطيل جميع signals لسرعة الرفع"""
    from django.db.models.signals import post_save, pre_save

    from inventory.models import BaseProduct, Product, ProductVariant

    # حفظ الـ receivers الحالية
    saved_receivers = {
        "post_save_product": (
            post_save.receivers[:] if hasattr(post_save, "receivers") else []
        ),
        "pre_save_product": (
            pre_save.receivers[:] if hasattr(pre_save, "receivers") else []
        ),
    }

    # تعطيل كل الـ receivers
    post_save.receivers = []
    pre_save.receivers = []

    return saved_receivers


def restore_signals(saved_receivers):
    """إعادة الـ signals"""
    from django.db.models.signals import post_save, pre_save

    post_save.receivers = saved_receivers.get("post_save_product", [])
    pre_save.receivers = saved_receivers.get("pre_save_product", [])


@shared_task(bind=True, time_limit=1800, soft_time_limit=1700)
def turbo_upload_products(
    self,
    upload_log_id,
    file_content,
    warehouse_id,
    user_id,
):
    """
    رفع TURBO - أسرع ما يمكن
    - بدون signals
    - بدون cloudflare
    - bulk operations فقط
    """
    from django.contrib.auth import get_user_model

    from inventory.models import (
        BulkUploadLog,
        Category,
        Product,
        StockTransaction,
        Warehouse,
    )

    User = get_user_model()
    logger.info(f"🚀 TURBO START - Log: {upload_log_id}")
    start_time = timezone.now()

    # تعطيل الـ signals
    saved_signals = disable_all_signals()
    logger.info("⚡ Signals DISABLED")

    try:
        upload_log = BulkUploadLog.objects.get(id=upload_log_id)
        user = User.objects.get(id=user_id)
        warehouse = Warehouse.objects.get(id=warehouse_id) if warehouse_id else None

        upload_log.status = "processing"
        upload_log.save(update_fields=["status"])

        # قراءة Excel
        df = pd.read_excel(BytesIO(file_content), engine="openpyxl")
        total = len(df)
        upload_log.total_rows = total
        upload_log.save(update_fields=["total_rows"])

        logger.info(f"📋 {total} rows to process")

        # تنظيف
        df = df.dropna(how="all").fillna("")

        # بناء كاش المنتجات
        products_by_code = {p.code: p for p in Product.objects.all() if p.code}
        categories_cache = {c.name.strip(): c for c in Category.objects.all()}

        # إحصائيات
        created = 0
        updated = 0
        errors = 0

        # معالجة بدفعات كبيرة
        batch_size = 500
        to_create = []
        to_update = []

        for i, row in df.iterrows():
            try:
                # استخراج البيانات
                code = str(row.get("الكود", row.get("code", ""))).strip()
                name = str(
                    row.get("اسم المنتج", row.get("الاسم", row.get("name", "")))
                ).strip()

                if not code and not name:
                    continue

                # السعر
                try:
                    price_str = str(row.get("السعر", row.get("price", 0))).strip()
                    price = (
                        float(price_str)
                        if price_str and price_str.lower() not in ["", "nan", "none"]
                        else 0
                    )
                except:
                    price = 0

                # سعر الجملة
                try:
                    wp_str = str(
                        row.get("سعر الجملة", row.get("wholesale_price", ""))
                    ).strip()
                    wholesale_price = (
                        float(wp_str)
                        if wp_str and wp_str.lower() not in ["", "nan", "none"]
                        else None
                    )
                except:
                    wholesale_price = None

                # الفئة
                cat_name = str(row.get("الفئة", row.get("category", ""))).strip()
                category = None
                if cat_name and cat_name.lower() not in ["", "nan", "none"]:
                    if cat_name in categories_cache:
                        category = categories_cache[cat_name]
                    else:
                        category = Category.objects.create(name=cat_name)
                        categories_cache[cat_name] = category

                # بحث سريع
                product = products_by_code.get(code)

                if product:
                    # تحديث
                    changed = False
                    if name and name != product.name:
                        product.name = name
                        changed = True
                    if price > 0 and Decimal(str(price)) != product.price:
                        product.price = Decimal(str(price))
                        changed = True
                    if wholesale_price is not None:
                        product.wholesale_price = Decimal(str(wholesale_price))
                        changed = True
                    if category and category != product.category:
                        product.category = category
                        changed = True

                    if changed:
                        to_update.append(product)
                        updated += 1
                else:
                    # جديد
                    product = Product(
                        code=code or None,
                        name=name or code or "منتج",
                        price=Decimal(str(price)) if price > 0 else Decimal("0"),
                        wholesale_price=(
                            Decimal(str(wholesale_price)) if wholesale_price else None
                        ),
                        category=category,
                    )
                    to_create.append(product)
                    if code:
                        products_by_code[code] = product
                    created += 1

            except Exception as e:
                errors += 1
                logger.error(f"Row {i}: {e}")

            # حفظ كل دفعة
            if len(to_create) >= batch_size or len(to_update) >= batch_size:
                with transaction.atomic():
                    if to_create:
                        Product.objects.bulk_create(to_create, ignore_conflicts=True)
                        to_create = []
                    if to_update:
                        Product.objects.bulk_update(
                            to_update,
                            ["name", "price", "wholesale_price", "category"],
                            batch_size=500,
                        )
                        to_update = []

                # تحديث التقدم
                processed = i + 1
                percent = int((processed / total) * 100)
                upload_log.processed_count = processed
                upload_log.created_count = created
                upload_log.updated_count = updated
                upload_log.error_count = errors
                upload_log.save(
                    update_fields=[
                        "processed_count",
                        "created_count",
                        "updated_count",
                        "error_count",
                    ]
                )

                self.update_state(
                    state="PROGRESS",
                    meta={"current": processed, "total": total, "percent": percent},
                )
                logger.info(f"⚡ {processed}/{total} ({percent}%)")

        # حفظ المتبقي
        with transaction.atomic():
            if to_create:
                Product.objects.bulk_create(to_create, ignore_conflicts=True)
            if to_update:
                Product.objects.bulk_update(
                    to_update,
                    ["name", "price", "wholesale_price", "category"],
                    batch_size=500,
                )

        # إكمال
        duration = (timezone.now() - start_time).total_seconds()
        summary = f"✅ {created} جديد، {updated} محدث - {duration:.1f}ث"

        upload_log.status = "completed"
        upload_log.processed_count = total
        upload_log.created_count = created
        upload_log.updated_count = updated
        upload_log.error_count = errors
        upload_log.summary = summary
        upload_log.save()

        logger.info(f"🎉 TURBO DONE: {summary}")

        return {
            "success": True,
            "created": created,
            "updated": updated,
            "duration": duration,
        }

    except Exception as e:
        logger.error(f"❌ TURBO FAIL: {e}")
        import traceback

        traceback.print_exc()

        try:
            upload_log.status = "failed"
            upload_log.summary = f"فشل: {str(e)}"
            upload_log.save()
        except:
            pass

        return {"success": False, "error": str(e)}

    finally:
        # إعادة الـ signals
        restore_signals(saved_signals)
        logger.info("⚡ Signals RESTORED")
