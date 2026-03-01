"""
مهام Celery للخلفية - نظام المخزون
"""

import logging
from decimal import Decimal

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, time_limit=600)
def process_bulk_upload_async(
    self, upload_log_id, file_data, default_warehouse_id, upload_mode, user_id
):
    """
    معالجة رفع المنتجات بالجملة في الخلفية - محسّنة للسرعة
    """
    import time
    from io import BytesIO

    import pandas as pd
    from django.db import connection, transaction

    from .cache_utils import invalidate_product_cache
    from .models import (
        BulkUploadError,
        BulkUploadLog,
        Category,
        Product,
        StockTransaction,
        Warehouse,
    )
    from .views_bulk import get_or_create_warehouse

    logger.info(f"🚀 بدء معالجة رفع المنتجات - Log ID: {upload_log_id}")

    try:
        upload_log = BulkUploadLog.objects.get(id=upload_log_id)
        user = User.objects.get(id=user_id)
        default_warehouse = (
            Warehouse.objects.get(id=default_warehouse_id)
            if default_warehouse_id
            else None
        )

        # تحديث الحالة
        upload_log.status = "processing"
        upload_log.save(update_fields=["status"])

        # قراءة الملف بشكل مبسط وسريع
        logger.info("📊 قراءة ملف Excel...")
        try:
            df = pd.read_excel(BytesIO(file_data), engine="openpyxl")
        except Exception as e:
            logger.error(f"خطأ في قراءة الملف: {str(e)}")
            df = pd.read_excel(BytesIO(file_data))

        total_rows = len(df)
        upload_log.total_rows = total_rows
        upload_log.save(update_fields=["total_rows"])
        logger.info(f"📋 تم تحليل {total_rows} صف")

        # معالجة وضع التهيئة الكاملة
        if upload_mode == "full_reset":
            with transaction.atomic():
                from .models import StockTransfer

                StockTransfer.objects.all().delete()
                StockTransaction.objects.all().delete()
                Product.objects.all().delete()

                upload_log.notes = "تهيئة كاملة: تم حذف جميع البيانات القديمة"
                upload_log.save()

        result = {
            "total_processed": 0,
            "created_count": 0,
            "updated_count": 0,
            "created_warehouses": [],
            "errors": [],
        }

        df = df.dropna(subset=["اسم المنتج", "السعر"])
        df = df.fillna("")

        errors_to_create = []
        skipped_count = 0

        with transaction.atomic():
            for index, row in df.iterrows():
                row_number = index + 2

                # تحديث التقدم كل 10 منتجات
                if index % 10 == 0:
                    upload_log.processed_count = result["total_processed"]
                    upload_log.save()
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": result["total_processed"],
                            "total": len(df),
                            "percent": int((result["total_processed"] / len(df)) * 100),
                        },
                    )

                try:
                    name = str(row["اسم المنتج"]).strip()
                    code = str(row["الكود"]).strip() if pd.notna(row["الكود"]) else None
                    category_name = str(row["الفئة"]).strip()
                    warehouse_name = (
                        str(row.get("المستودع", "")).strip()
                        if pd.notna(row.get("المستودع"))
                        else ""
                    )

                    # معالجة السعر والكمية
                    try:
                        price = (
                            float(str(row["السعر"]).strip()) if row["السعر"] else 0.0
                        )
                    except Exception:
                        price = 0.0

                    try:
                        quantity = (
                            float(str(row["الكمية"]).strip())
                            if pd.notna(row["الكمية"])
                            else 0.0
                        )
                    except Exception:
                        quantity = 0.0

                    description = str(row.get("الوصف", "")).strip()

                    try:
                        minimum_stock = (
                            int(float(str(row.get("الحد الأدنى", 0)).strip()))
                            if pd.notna(row.get("الحد الأدنى"))
                            else 0
                        )
                    except Exception:
                        minimum_stock = 0

                    currency = str(row.get("العملة", "EGP")).strip().upper()
                    unit = str(row.get("الوحدة", "piece")).strip()

                    if currency not in ["EGP", "USD", "EUR"]:
                        currency = "EGP"

                    valid_units = [
                        "piece",
                        "kg",
                        "gram",
                        "liter",
                        "meter",
                        "box",
                        "pack",
                        "dozen",
                        "roll",
                        "sheet",
                    ]
                    if unit not in valid_units:
                        unit_map = {
                            "قطعة": "piece",
                            "كيلوجرام": "kg",
                            "جرام": "gram",
                            "لتر": "liter",
                            "متر": "meter",
                            "علبة": "box",
                            "عبوة": "pack",
                            "دستة": "dozen",
                            "لفة": "roll",
                            "ورقة": "sheet",
                        }
                        unit = unit_map.get(unit, "piece")

                    if not name or price <= 0:
                        error_msg = "اسم المنتج والسعر مطلوبان"
                        result["errors"].append(f"الصف {row_number}: {error_msg}")
                        errors_to_create.append(
                            BulkUploadError(
                                upload_log=upload_log,
                                row_number=row_number,
                                error_type="missing_data",
                                result_status="failed",
                                error_message=error_msg,
                                row_data=row.to_dict(),
                            )
                        )
                        continue

                    # الفئة
                    category = None
                    if category_name:
                        category, created = Category.objects.get_or_create(
                            name=category_name,
                            defaults={"description": "تم إنشاؤها تلقائياً"},
                        )

                    # المنتج
                    product = None
                    created = False
                    product_exists = False

                    if code:
                        try:
                            product = Product.objects.get(code=code)
                            product_exists = True

                            if upload_mode == "new_only":
                                skipped_count += 1
                                errors_to_create.append(
                                    BulkUploadError(
                                        upload_log=upload_log,
                                        row_number=row_number,
                                        error_type="duplicate",
                                        result_status="skipped",
                                        error_message=f"منتج موجود - تم التخطي",
                                        row_data=row.to_dict(),
                                    )
                                )
                                continue

                            elif upload_mode in ["add_to_existing", "replace_quantity"]:
                                product.name = name
                                product.category = category
                                product.description = description
                                product.price = price
                                product.currency = currency
                                product.unit = unit
                                product.minimum_stock = minimum_stock
                                product.save()
                                result["updated_count"] += 1

                        except Product.DoesNotExist:
                            product = Product.objects.create(
                                name=name,
                                code=code,
                                category=category,
                                description=description,
                                price=price,
                                currency=currency,
                                unit=unit,
                                minimum_stock=minimum_stock,
                            )
                            created = True
                            result["created_count"] += 1
                    else:
                        product = Product.objects.create(
                            name=name,
                            category=category,
                            description=description,
                            price=price,
                            currency=currency,
                            unit=unit,
                            minimum_stock=minimum_stock,
                        )
                        created = True
                        result["created_count"] += 1

                    # المخزون
                    if quantity > 0 and product:
                        target_warehouse = default_warehouse

                        if warehouse_name:
                            target_warehouse = get_or_create_warehouse(
                                warehouse_name, user
                            )
                            if (
                                target_warehouse
                                and target_warehouse.name
                                not in result["created_warehouses"]
                            ):
                                result["created_warehouses"].append(
                                    target_warehouse.name
                                )

                        if not target_warehouse:
                            continue

                        # استبدال الكمية
                        if upload_mode == "replace_quantity" and product_exists:
                            last_transaction = (
                                StockTransaction.objects.filter(
                                    product=product, warehouse=target_warehouse
                                )
                                .order_by("-transaction_date")
                                .first()
                            )

                            if (
                                last_transaction
                                and last_transaction.running_balance
                                and last_transaction.running_balance > 0
                            ):
                                current_balance = Decimal(
                                    str(last_transaction.running_balance)
                                )
                                StockTransaction.objects.create(
                                    product=product,
                                    warehouse=target_warehouse,
                                    transaction_type="out",
                                    reason="adjustment",
                                    quantity=current_balance,
                                    reference="تصفير قبل الاستبدال",
                                    notes=f"تصفير الرصيد (كان: {current_balance})",
                                    created_by=user,
                                    transaction_date=timezone.now(),
                                )

                        # إضافة الكمية
                        StockTransaction.objects.create(
                            product=product,
                            warehouse=target_warehouse,
                            transaction_type="in",
                            reason="purchase",
                            quantity=quantity,
                            reference="رفع من ملف إكسل",
                            notes=f"المستودع: {target_warehouse.name}",
                            created_by=user,
                            transaction_date=timezone.now(),
                        )

                    result["total_processed"] += 1
                    if product:
                        invalidate_product_cache(product.id)

                except Exception as e:
                    error_msg = str(e)
                    result["errors"].append(f"الصف {row_number}: {error_msg}")
                    errors_to_create.append(
                        BulkUploadError(
                            upload_log=upload_log,
                            row_number=row_number,
                            error_type="processing",
                            result_status="failed",
                            error_message=error_msg,
                            row_data=row.to_dict() if hasattr(row, "to_dict") else {},
                        )
                    )

        # حفظ الأخطاء
        if errors_to_create:
            BulkUploadError.objects.bulk_create(errors_to_create)

        # تحديث السجل
        actual_errors = len(result["errors"]) - skipped_count
        upload_log.processed_count = result["total_processed"]
        upload_log.created_count = result["created_count"]
        upload_log.updated_count = result["updated_count"]
        upload_log.skipped_count = skipped_count
        upload_log.error_count = actual_errors
        upload_log.created_warehouses = result["created_warehouses"]

        summary_parts = []
        if result["created_count"] > 0:
            summary_parts.append(f"تم إنشاء {result['created_count']} منتج")
        if result["updated_count"] > 0:
            summary_parts.append(f"تم تحديث {result['updated_count']} منتج")
        if skipped_count > 0:
            summary_parts.append(f"تم تخطي {skipped_count} منتج")
        if actual_errors > 0:
            summary_parts.append(f"فشل {actual_errors} صف")

        summary = ". ".join(summary_parts) if summary_parts else "لا توجد بيانات"
        upload_log.complete(summary=summary)

        return {"status": "success", "upload_log_id": upload_log_id, "result": result}

    except Exception as e:
        logger.error(f"خطأ في معالجة الرفع: {str(e)}")
        upload_log.fail(error_message=str(e))
        raise self.retry(exc=e, countdown=60)


@shared_task(
    bind=True, max_retries=3, default_retry_delay=180, autoretry_for=(Exception,)
)
def cleanup_old_warehouse_data(self, days=90):
    """
    تنظيف بيانات المستودعات القديمة غير المستخدمة
    """
    from datetime import timedelta

    from django.db import models
    from django.utils import timezone

    from .models import StockTransaction, Warehouse

    cutoff_date = timezone.now() - timedelta(days=days)

    # البحث عن مستودعات بدون معاملات حديثة
    inactive_warehouses = (
        Warehouse.objects.filter(is_active=True)
        .exclude(stock_transactions__transaction_date__gte=cutoff_date)
        .annotate(transaction_count=models.Count("stock_transactions"))
        .filter(transaction_count=0)
    )

    count = inactive_warehouses.count()

    logger.info(f"تم العثور على {count} مستودع غير نشط")

    return {"status": "success", "inactive_count": count}


@shared_task(
    bind=True, max_retries=2, default_retry_delay=300, autoretry_for=(Exception,)
)
def sync_official_fabric_warehouses(self):
    """
    مزامنة المستودعات الرسمية للأقمشة
    """
    from .models import Category, Warehouse

    # المستودعات الرسمية للأقمشة
    official_warehouses = [
        {"name": "مستودع الأقمشة الرئيسي", "code": "FABRIC_MAIN"},
        {"name": "مستودع أقمشة الستائر", "code": "FABRIC_CURTAIN"},
        {"name": "مستودع أقمشة التنجيد", "code": "FABRIC_UPHOLSTERY"},
    ]

    created = []
    updated = []

    for wh_data in official_warehouses:
        warehouse, was_created = Warehouse.objects.update_or_create(
            code=wh_data["code"],
            defaults={
                "name": wh_data["name"],
                "is_active": True,
                "is_official_fabric_warehouse": True,
                "notes": "مستودع رسمي للأقمشة",
            },
        )

        if was_created:
            created.append(warehouse.name)
        else:
            updated.append(warehouse.name)

    return {"status": "success", "created": created, "updated": updated}


@shared_task(
    bind=True,
    max_retries=1,
    queue="default",
    name="inventory.tasks.cleanup_old_bulk_upload_errors",
)
def cleanup_old_bulk_upload_errors(self, keep_days=30, keep_per_log=100):
    """
    تنظيف سجلات BulkUploadError القديمة والمكتظة.

    - يحذف الأخطاء التابعة لسجلات أقدم من `keep_days` يوماً
    - يحتفظ بأول `keep_per_log` خطأ لكل سجل رفع (للتشخيص)
    - يُشغَّل أسبوعياً عبر Celery Beat

    الإعدادات الافتراضية:
        keep_days=30  → يحذف الأخطاء الأقدم من 30 يوم
        keep_per_log=100 → يحتفظ بـ 100 خطأ لكل عملية رفع
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models import BulkUploadError, BulkUploadLog

    cutoff = timezone.now() - timedelta(days=keep_days)
    total_deleted = 0

    # 1. حذف أخطاء السجلات القديمة بالكامل
    old_logs = BulkUploadLog.objects.filter(created_at__lt=cutoff)
    if old_logs.exists():
        deleted, _ = BulkUploadError.objects.filter(upload_log__in=old_logs).delete()
        total_deleted += deleted
        logger.info(
            f"✅ حُذف {deleted} خطأ رفع قديم (أقدم من {keep_days} يوم)"
        )

    # 2. للسجلات الحديثة: احتفظ بأول keep_per_log خطأ فقط
    recent_logs = BulkUploadLog.objects.filter(created_at__gte=cutoff)
    for log in recent_logs:
        error_ids = (
            BulkUploadError.objects.filter(upload_log=log)
            .order_by("id")
            .values_list("id", flat=True)
        )
        if error_ids.count() > keep_per_log:
            ids_to_keep = list(error_ids[:keep_per_log])
            deleted, _ = (
                BulkUploadError.objects.filter(upload_log=log)
                .exclude(id__in=ids_to_keep)
                .delete()
            )
            total_deleted += deleted

    if total_deleted:
        logger.info(f"✅ إجمالي سجلات BulkUploadError المحذوفة: {total_deleted}")
    else:
        logger.info("ℹ️ لا توجد سجلات BulkUploadError تحتاج حذفاً")

    return {"status": "success", "deleted": total_deleted}
