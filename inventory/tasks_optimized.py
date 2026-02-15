"""
مهام Celery المحسّنة للمخزون - نظام ذكي يمنع التكرارات
"""

import logging
from decimal import Decimal
from io import BytesIO

import pandas as pd
from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, time_limit=600, soft_time_limit=540, rate_limit=None)
def bulk_upload_products_fast(
    self,
    upload_log_id,
    file_content,
    warehouse_id,
    upload_mode,
    user_id,
    auto_delete_empty=False,
):
    """
    رفع المنتجات بالجملة - نظام ذكي محسّن
    """
    from django.contrib.auth import get_user_model

    from .models import (
        BaseProduct,
        BulkUploadError,
        BulkUploadLog,
        Category,
        Product,
        ProductVariant,
        StockTransaction,
        Warehouse,
    )
    from .smart_upload_logic import (
        add_stock_transaction,
        clean_start_reset,
        delete_empty_warehouses,
        smart_update_product,
    )

    User = get_user_model()
    logger.info(f"🚀 بدء الرفع الذكي - Log: {upload_log_id} - الوضع: {upload_mode}")
    
    # إنشاء ملف لوج للتتبع
    import os
    from django.conf import settings
    
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f'bulk_upload_{upload_log_id}.log')
    
    try:
        log_file = open(log_file_path, 'w', encoding='utf-8')
        
        def log_message(msg):
            """حفظ رسالة في الملف والطباعة"""
            logger.info(msg)
            log_file.write(msg + '\n')
            log_file.flush()
    except Exception as e:
        logger.error(f"فشل إنشاء ملف اللوج: {e}")
        # استخدام logger فقط إذا فشل إنشاء الملف
        def log_message(msg):
            logger.info(msg)

    # تعطيل Cloudflare signals لمنع الاتصالات الزائدة
    from django.db.models.signals import post_save, pre_save

    from .models import BaseProduct, ProductVariant

    # حفظ receivers الأصلية
    original_post_save = list(post_save.receivers)
    original_pre_save = list(pre_save.receivers)

    # تعطيل كل الـ signals
    post_save.receivers = []
    pre_save.receivers = []
    log_message("⚡ تم تعطيل Signals للسرعة")

    try:
        # تحميل البيانات الأساسية
        upload_log = BulkUploadLog.objects.get(id=upload_log_id)
        user = User.objects.get(id=user_id)
        warehouse = Warehouse.objects.get(id=warehouse_id) if warehouse_id else None

        upload_log.status = "processing"
        upload_log.save(update_fields=["status"])

        log_message(f"{'='*80}")
        log_message(f"📁 سجل رفع المنتجات - ID: {upload_log_id}")
        log_message(f"{'='*80}")
        log_message(f"📁 اسم الملف: {upload_log.file_name}")
        log_message(f"🏢 المستودع: {warehouse.name if warehouse else 'غير محدد'}")
        log_message(f"♻️ وضع الرفع: {upload_mode}")
        log_message(f"👤 المستخدم: {user.username}")
        log_message(f"{'='*80}\n")

        # قراءة Excel بسرعة
        log_message("📊 قراءة Excel...")
        df = pd.read_excel(BytesIO(file_content), engine="openpyxl")
        total = len(df)
        # تحديث total_rows مباشرة بعد القراءة لضمان ظهور الـ 0% كبداية حقيقية
        upload_log.total_rows = total
        upload_log.processed_count = 0
        upload_log.status = "processing"
        upload_log.save(update_fields=["total_rows", "processed_count", "status"])

        log_message(f"📋 {total} صف للمعالجة")
        log_message(f"📝 أعمدة الملف: {list(df.columns)}\n")

        # تهيئة كاملة إذا طُلب
        if upload_mode == "clean_start":
            logger.warning("⚠️ وضع المسح الكامل")
            reset_stats = clean_start_reset()
            upload_log.summary = f"مسح كامل: {reset_stats['deleted_products']} منتج، {reset_stats['deleted_transactions']} معاملة"
            upload_log.save(update_fields=["summary"])

        # تنظيف البيانات
        # تنظيف البيانات - البحث عن الأعمدة المتاحة للمسح
        subset_cols = []
        name_cols = ["اسم المنتج", "الاسم", "product_name", "name"]
        code_cols = ["الكود", "كود المنتج", "product_code", "code"]

        for col in name_cols + code_cols:
            if col in df.columns:
                subset_cols.append(col)

        if subset_cols:
            df = df.dropna(how="all", subset=subset_cols).fillna("")
        else:
            df = df.dropna(how="all").fillna("")

        # تحميل البيانات المسبقة في الذاكرة لتسريع البحث (Caching)
        # هذا يقلل عدد الاستعلامات من O(N) إلى O(1)
        logger.info("🧠 بناء التخزين المؤقت للبيانات...")
        categories_cache = {c.name.strip(): c for c in Category.objects.all()}
        warehouses_cache = {
            w.name.strip(): w for w in Warehouse.objects.filter(is_active=True)
        }

        # كاش للمنتجات (Legacy Products) - مع كل نسخ الكود المحتملة
        products_cache = {}
        for p in Product.objects.all():
            if p.code:
                products_cache[p.code] = p
                # إضافة نسخ بأصفار بادئة مختلفة لتجنب IntegrityError
                if p.code.isdigit():
                    for padding in range(len(p.code), 15):
                        padded = p.code.zfill(padding)
                        if padded not in products_cache:
                            products_cache[padded] = p

        # كاش للمنتجات الأساسية (Base Products)
        base_products_cache = {
            bp.code: bp for bp in BaseProduct.objects.all() if bp.code
        }

        # كاش للمتغيرات (Variants) مفهرسة بـ legacy_product_id
        variants_cache = {
            v.legacy_product_id: v
            for v in ProductVariant.objects.filter(
                legacy_product_id__isnull=False
            ).select_related("base_product")
        }

        data_cache = {
            "products": products_cache,
            "base_products": base_products_cache,
            "variants": variants_cache,
        }

        stats = {
            "created": 0,
            "updated": 0,
            "moved": 0,
            "merged": 0,
            "skipped": 0,
            "errors": 0,
            "cutting_updated": 0,
            "cutting_split": 0,
        }

        # تتبع المنتجات المعدلة/المنشأة لخط الإنتاج التلقائي
        affected_product_ids = []

        # معالجة بدفعات متوسطة للتوازن بين السرعة والأمان
        batch_size = 50  # دفعات أصغر لتقليل وقت المعاملات
        results_batch = []
        processed_overall = 0

        logger.info(f"🔄 بدء معالجة {len(df)} صف بسعة تخزين مؤقت كاملة")

        for batch_start in range(0, len(df), batch_size):
            batch_end = min(batch_start + batch_size, len(df))
            batch = df.iloc[batch_start:batch_end]

            logger.info(f"📦 معالجة الدفعة {batch_start}-{batch_end}")

            from django.db import transaction

            # معالجة الصفوف - معاملة لكل 10 صفوف للتوازن
            mini_batch_size = 10
            for mini_start in range(0, len(batch), mini_batch_size):
                mini_end = min(mini_start + mini_batch_size, len(batch))
                mini_batch = batch.iloc[mini_start:mini_end]

                try:
                    with transaction.atomic():
                        for i, (idx, row) in enumerate(mini_batch.iterrows()):
                            processed_overall += 1

                            # قراءة البيانات برقم العمود (من القالب المُولّد)
                            # 0=اسم، 1=كود، 2=فئة، 3=سعر، 4=جملة، 5=كمية، 6=مستودع، 7=وصف

                            def safe_get(index, default=None):
                                """قراءة قيمة من عمود برقمه"""
                                if index < len(row):
                                    val = row.iloc[index]
                                    if pd.notna(val):
                                        val = str(val).strip()
                                        if val and val.lower() not in [
                                            "nan",
                                            "none",
                                            "",
                                        ]:
                                            return val
                                return default

                            # الكود (عمود 1) - الأهم
                            code = safe_get(1)
                            if code and code.isdigit():
                                code = code.lstrip("0") or "0"

                            # اسم المنتج (عمود 0 أو الاسم)
                            name = row.get(
                                "اسم المنتج",
                                row.get(
                                    "الاسم", row.get("product_name", safe_get(0, ""))
                                ),
                            )

                            # السعر (عمود 3 أو السعر)
                            price_val = row.get(
                                "السعر", row.get("price", safe_get(3, None))
                            )
                            try:
                                if (
                                    price_val is not None
                                    and str(price_val).strip() != ""
                                ):
                                    price = float(price_val)
                                else:
                                    price = 0
                            except Exception:
                                price = 0

                            # سعر الجملة - تجربة عدة أعمدة (4 ثم 1 للملفات بعمودين أو بالاسم)
                            wholesale_price = row.get(
                                "سعر الجملة", row.get("wholesale_price")
                            )
                            if pd.isna(wholesale_price) or wholesale_price == "":
                                for ws_col in [4, 1]:  # القالب = 4، ملف بعمودين = 1
                                    try:
                                        ws_val = safe_get(ws_col)
                                        if ws_val:
                                            wholesale_price = float(ws_val)
                                            break
                                    except Exception:
                                        continue
                            try:
                                if wholesale_price is not None:
                                    wholesale_price = float(wholesale_price)
                            except Exception:
                                wholesale_price = None

                            # الكمية (عمود 5 أو حسب الاسم)
                            quantity_val = row.get("الكمية", safe_get(5))
                            try:
                                quantity = float(quantity_val) if quantity_val else 0
                            except Exception:
                                quantity = 0

                            # الوصف (عمود 7)
                            description = safe_get(7, "")
                            
                            # الحد الأدنى (عمود 8 أو حسب الاسم)
                            min_stock_val = row.get("الحد الأدنى", safe_get(8))
                            try:
                                minimum_stock = int(float(min_stock_val)) if min_stock_val is not None else None
                            except Exception:
                                minimum_stock = None

                            # Material (عمود 9 أو حسب الاسم)
                            material = row.get(
                                "Material", row.get("الخامة", safe_get(9, None))
                            )
                            if pd.isna(material):
                                material = ""

                            # Width (عمود 10 أو حسب الاسم)
                            width = row.get(
                                "Width", row.get("العرض", safe_get(10, None))
                            )
                            if pd.isna(width):
                                width = ""
                            
                            # Currency (عمود 11 أو حسب الاسم)
                            currency_val = row.get("العملة", safe_get(11))
                            currency = None
                            if currency_val and pd.notna(currency_val):
                                curr_str = str(currency_val).strip().upper()
                                if curr_str in ["EGP", "USD", "EUR", "SAR"]:
                                    currency = curr_str
                            
                            # Unit (عمود 12 أو حسب الاسم)
                            unit_val = row.get("الوحدة", safe_get(12))
                            unit = None
                            if unit_val and pd.notna(unit_val):
                                unit_str = str(unit_val).strip()
                                valid_units = ["piece", "kg", "gram", "liter", "meter", "box", "pack", "dozen", "roll", "sheet"]
                                unit_map = {
                                    "قطعة": "piece", "كيلوجرام": "kg", "جرام": "gram",
                                    "لتر": "liter", "متر": "meter", "علبة": "box",
                                    "عبوة": "pack", "دستة": "dozen", "لفة": "roll", "ورقة": "sheet",
                                }
                                if unit_str in valid_units:
                                    unit = unit_str
                                elif unit_str in unit_map:
                                    unit = unit_map[unit_str]

                            # DEBUG: طباعة أول 3 صفوف
                            if processed_overall <= 3:
                                logger.warning(f"🔍 DEBUG صف {processed_overall}:")
                                logger.warning(f"   أعمدة الملف: {list(row.index)}")
                                logger.warning(
                                    f"   كود={code}, سعر={price}, جملة={wholesale_price}"
                                )

                            # التحقق من المنتج باستخدام الكاش
                            is_existing = False
                            actual_code = code
                            if code and "products" in data_cache:
                                if code in data_cache["products"]:
                                    is_existing = True
                                    actual_code = code
                                elif code.isdigit():
                                    for p in range(len(code), 15):
                                        padded = code.zfill(p)
                                        if padded in data_cache["products"]:
                                            is_existing = True
                                            actual_code = padded
                                            break

                            if not is_existing and not name:
                                stats["errors"] += 1
                                results_batch.append(
                                    BulkUploadError(
                                        upload_log=upload_log,
                                        row_number=idx + 2,
                                        error_type="missing_data",
                                        result_status="failed",
                                        error_message="منتج جديد ولكن الاسم مفقود - يرجى إضافة الاسم ليتمكن النظام من إنشائه",
                                        row_data={"code": actual_code},
                                    )
                                )
                                continue

                            # تجميع
                            product_data = {
                                "name": name,
                                "code": actual_code,
                                "price": price,
                                "wholesale_price": wholesale_price,
                                "quantity": quantity,
                                "material": material,
                                "width": width,
                                "description": description,
                                "minimum_stock": minimum_stock,
                                "currency": currency,
                                "unit": unit,
                            }

                            # تحديث الفئة والمستودع إذا وجدا
                            cat_name = str(row.get("الفئة", "")).strip()
                            if cat_name:
                                if cat_name in categories_cache:
                                    product_data["category"] = categories_cache[
                                        cat_name
                                    ]
                                else:
                                    cat = Category.objects.create(name=cat_name)
                                    categories_cache[cat_name] = cat
                                    product_data["category"] = cat

                            wh_name = str(row.get("المستودع", "")).strip()
                            target_wh = warehouse
                            if wh_name:
                                if wh_name in warehouses_cache:
                                    target_wh = warehouses_cache[wh_name]
                                else:
                                    from .views_bulk import get_or_create_warehouse

                                    target_wh = get_or_create_warehouse(wh_name, user)
                                    if target_wh:
                                        warehouses_cache[wh_name] = target_wh

                            # حفظ
                            result = smart_update_product(
                                product_data,
                                target_wh,
                                user,
                                upload_mode,
                                cache=data_cache,
                                fast_mode=True,
                            )

                            action = result["action"]
                            if action == "created":
                                stats["created"] += 1
                                if result.get("product"):
                                    affected_product_ids.append(result["product"].id)
                            elif action == "updated":
                                stats["updated"] += 1
                                if result.get("product"):
                                    affected_product_ids.append(result["product"].id)
                            elif action == "moved":
                                stats["moved"] += 1
                                stats["updated"] += 1
                                if result.get("product"):
                                    affected_product_ids.append(result["product"].id)
                            elif action == "skipped":
                                stats["skipped"] += 1

                            # تسجيل النتيجة في التقرير (ثمن معنوي بسيط للأداء مقابل دقة التقارير)
                            results_batch.append(
                                BulkUploadError(
                                    upload_log=upload_log,
                                    row_number=idx + 2,
                                    error_type="other",
                                    result_status=(
                                        action if action != "moved" else "updated"
                                    ),
                                    error_message=result.get("message", ""),
                                    row_data={
                                        "name": name or code or "بدون اسم",
                                        "code": actual_code,
                                    },
                                )
                            )

                except Exception as mini_batch_error:
                    # فشل المعاملة الصغيرة - تسجيل كل الصفوف كأخطاء
                    logger.error(f"❌ فشل mini-batch: {mini_batch_error}")
                    for i, (idx, row) in enumerate(mini_batch.iterrows()):
                        if idx + 2 not in [r.row_number for r in results_batch]:
                            stats["errors"] += 1
                            results_batch.append(
                                BulkUploadError(
                                    upload_log=upload_log,
                                    row_number=idx + 2,
                                    error_type="processing",
                                    result_status="failed",
                                    error_message=str(mini_batch_error)[:500],
                                    row_data={},
                                )
                            )

            # حفظ النتائج بعد كل دفعة كبيرة
            if results_batch:
                try:
                    BulkUploadError.objects.bulk_create(results_batch)
                    results_batch = []
                except Exception as save_error:
                    logger.error(f"⚠️ فشل حفظ الأخطاء: {save_error}")

            # تحديث التقدم *خارج* المعاملة لضمان ظهوره للواجهة فوراً
            percent = int((processed_overall / total) * 100)
            upload_log.processed_count = processed_overall
            upload_log.created_count = stats["created"]
            upload_log.updated_count = stats["updated"]
            upload_log.skipped_count = stats["skipped"]
            upload_log.error_count = stats["errors"]
            upload_log.save(
                update_fields=[
                    "processed_count",
                    "created_count",
                    "updated_count",
                    "skipped_count",
                    "error_count",
                ]
            )

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": processed_overall,
                    "total": total,
                    "percent": percent,
                    "created": stats["created"],
                    "updated": stats["updated"],
                    "skipped": stats["skipped"],
                    "errors": stats["errors"],
                },
            )

        # إكمال
        log_message(f"\n{'='*80}")
        log_message(f"📊 ملخص العملية:")
        log_message(f"   ✅ تم إنشاء: {stats['created']} منتج")
        log_message(f"   🔄 تم تحديث: {stats['updated']} منتج")
        log_message(f"   ⏭️ تم تخطي: {stats['skipped']} منتج")
        log_message(f"   ❌ أخطاء: {stats['errors']}")
        log_message(f"{'='*80}")
        log_message(f"\n📝 ملف اللوج محفوظ في: {log_file_path}")
        log_message(f"يمكنك قراءته بالأمر: cat {log_file_path}")
        
        summary_parts = []
        if stats["created"] > 0:
            summary_parts.append(f"✅ {stats['created']} جديد")
        if stats["updated"] > 0:
            summary_parts.append(f"🔄 {stats['updated']} محدث")
        if stats["errors"] > 0:
            summary_parts.append(f"❌ {stats['errors']} خطأ")

        upload_log.complete(
            summary=" | ".join(summary_parts) if summary_parts else "مكتمل"
        )
        
        # حفظ مسار ملف اللوج
        upload_log.options['log_file'] = log_file_path
        upload_log.save(update_fields=['options'])
        
        # إغلاق ملف اللوج
        try:
            log_file.close()
        except Exception:
            pass

        # 🚀 تشغيل خط الإنتاج التلقائي: ترحيل + QR + مزامنة Cloudflare
        if affected_product_ids:
            try:
                from inventory.auto_product_pipeline import bulk_post_upload_pipeline
                log_message(f"🔄 بدء خط الإنتاج التلقائي لـ {len(affected_product_ids)} منتج...")
                bulk_post_upload_pipeline(affected_product_ids)
                log_message(f"✅ تم تشغيل خط الإنتاج التلقائي (ترحيل + QR + مزامنة Cloudflare)")
            except Exception as pipeline_error:
                log_message(f"⚠️ تحذير: فشل تشغيل خط الإنتاج التلقائي: {pipeline_error}")
                logger.error(f"Auto pipeline error after bulk upload: {pipeline_error}")

        return {"status": "success", "stats": stats}

    except Exception as e:
        log_message(f"\n🚨 خطأ في المعالجة: {str(e)}")
        import traceback
        log_message(f"📍 Traceback:\n{traceback.format_exc()}")
        
        try:
            log_file.close()
        except Exception:
            pass
            
        if "upload_log" in locals():
            upload_log.fail(error_message=str(e))
        raise

    finally:
        # إعادة تفعيل الـ signals
        post_save.receivers = original_post_save
        pre_save.receivers = original_pre_save
        log_message("⚡ تم إعادة تفعيل Signals")
