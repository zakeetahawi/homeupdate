"""
خط الإنتاج التلقائي للمنتجات
Automatic Product Pipeline: Migration + QR + Cloudflare Sync

عند إضافة أو تعديل منتج في النظام القديم (Product):
1. ترحيل تلقائي → إنشاء BaseProduct + ProductVariant
2. توليد QR تلقائي للـ BaseProduct
3. مزامنة تلقائية مع Cloudflare KV
4. تحديث خريطة الأسماء (Name Map) إذا لزم الأمر

كل شيء يعمل في الخلفية بدون تأثير على أداء النظام أو قاعدة البيانات
"""

import logging
import threading
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================
# قفل لمنع التشغيل المتزامن لنفس المنتج
# ============================================================
_product_locks = {}
_lock_manager = threading.Lock()


def _get_product_lock(product_id):
    """الحصول على قفل خاص بمنتج معين"""
    with _lock_manager:
        if product_id not in _product_locks:
            _product_locks[product_id] = threading.Lock()
        return _product_locks[product_id]


def _cleanup_lock(product_id):
    """تنظيف القفل بعد الانتهاء"""
    with _lock_manager:
        _product_locks.pop(product_id, None)


# ============================================================
# الخط الرئيسي: ترحيل + QR + مزامنة
# ============================================================
def auto_migrate_and_sync(product_id, fields_changed=None):
    """
    خط الإنتاج الكامل: ترحيل المنتج وتوليد QR ومزامنة Cloudflare

    يعمل في background thread بدون أي تأثير على النظام.

    Args:
        product_id: معرف المنتج في النظام القديم
        fields_changed: قائمة الحقول المتغيرة (للتحسين)
    """
    thread = threading.Thread(
        target=_run_pipeline,
        args=(product_id, fields_changed),
        daemon=True,
        name=f"product-pipeline-{product_id}",
    )
    thread.start()


def _run_pipeline(product_id, fields_changed=None):
    """
    تنفيذ خط الإنتاج الكامل (يعمل في thread منفصل)
    """
    lock = _get_product_lock(product_id)

    # إذا كان هناك thread آخر يعمل على نفس المنتج، ننتظر
    if not lock.acquire(timeout=30):
        logger.warning(f"⏳ Pipeline timeout for product {product_id}, skipping")
        return

    try:
        from inventory.models import BaseProduct, Product, ProductVariant

        # 1. جلب المنتج
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            logger.warning(f"Product {product_id} not found, skipping pipeline")
            return

        if not product.code:
            return

        # 2. التحقق من وجود BaseProduct مرتبط
        variant = ProductVariant.objects.filter(
            legacy_product=product
        ).select_related("base_product").first()

        base_product = variant.base_product if variant else None

        # 3. إذا لم يكن مرتبطاً → ترحيل
        if not base_product:
            base_product = _auto_migrate_product(product)
            if not base_product:
                logger.error(f"❌ Failed to migrate product {product.code}")
                return
            logger.info(f"✅ Auto-migrated: {product.code} → BaseProduct {base_product.code}")
        else:
            # 4. إذا كان مرتبطاً → مزامنة البيانات المتغيرة
            _sync_product_data_to_base(product, base_product, fields_changed)

        # 5. توليد QR إذا لم يكن موجوداً
        if not base_product.qr_code_base64:
            _generate_qr_for_base(base_product)

        # 6. مزامنة مع Cloudflare
        _sync_to_cloudflare(base_product)

    except Exception as e:
        logger.error(f"❌ Pipeline error for product {product_id}: {e}")
    finally:
        lock.release()
        _cleanup_lock(product_id)


# ============================================================
# المرحلة 1: الترحيل التلقائي
# ============================================================
def _auto_migrate_product(product):
    """
    ترحيل منتج واحد من النظام القديم إلى النظام الجديد
    إنشاء BaseProduct + ProductVariant بأقل عدد من الاستعلامات

    يستخدم flags لمنع الـ signals من عمل مزامنة مكررة
    (المزامنة تتم مرة واحدة فقط في نهاية خط الإنتاج)

    Returns:
        BaseProduct or None
    """
    from django.db import transaction as db_transaction

    from inventory.models import BaseProduct, ProductVariant
    from inventory.variant_services import VariantService

    try:
        with db_transaction.atomic():
            # تحليل اسم المنتج
            base_name, variant_code = VariantService.parse_product_code(product.name)
            if not base_name:
                base_name = product.name
                variant_code = "DEFAULT"

            # التحقق من وجود BaseProduct
            base_product = BaseProduct.objects.filter(code=product.code).first()
            bp_created = False

            if not base_product:
                # إنشاء يدوي مع flags لمنع signals المكررة
                base_product = BaseProduct(
                    code=product.code,
                    name=base_name,
                    base_price=product.price,
                    wholesale_price=product.wholesale_price,
                    currency=product.currency,
                    unit=product.unit,
                    category=product.category,
                    minimum_stock=product.minimum_stock,
                    material=product.material or "",
                    width=product.width or "",
                )
                # Flags لمنع التكرار - المزامنة تتم في نهاية Pipeline
                base_product._skip_cloudflare_sync = True
                base_product._skip_qr_generation = True
                base_product._skip_auto_pipeline = True
                base_product._skip_legacy_sync = True
                base_product.save()
                bp_created = True

            # إنشاء المتغير
            if not variant_code:
                variant_code = "DEFAULT"

            # التحقق من وجود variant مرتبط بهذا المنتج
            existing_variant = ProductVariant.objects.filter(
                legacy_product=product
            ).first()
            if existing_variant:
                return existing_variant.base_product

            # التحقق من وجود variant بنفس الكود
            existing_by_code = ProductVariant.objects.filter(
                base_product=base_product, variant_code=variant_code
            ).first()

            if existing_by_code and existing_by_code.legacy_product and existing_by_code.legacy_product != product:
                # المتغير موجود ومرتبط بمنتج آخر → كود فريد
                variant_code = f"{variant_code}_{product.id}"

            # إنشاء المتغير مع flags
            variant = ProductVariant(
                base_product=base_product,
                variant_code=variant_code,
                legacy_product=product,
                barcode=product.code,
                color_code=VariantService.extract_color_code(
                    variant_code.split("_")[0] if "_" in variant_code else variant_code
                ),
            )
            variant._skip_cloudflare_sync = True
            variant._skip_legacy_sync = True
            variant.save()

            return base_product

    except Exception as e:
        logger.error(f"❌ Migration error for {product.code}: {e}")
        return None


# ============================================================
# المرحلة 2: مزامنة البيانات المتغيرة
# ============================================================
def _sync_product_data_to_base(product, base_product, fields_changed=None):
    """
    مزامنة التغييرات من Product إلى BaseProduct

    Args:
        product: المنتج القديم
        base_product: المنتج الأساسي
        fields_changed: قائمة الحقول المتغيرة (للتحسين)
    """
    update_fields = []

    # تحديد الحقول التي يجب مزامنتها
    field_mapping = {
        "price": ("base_price", lambda: product.price),
        "wholesale_price": ("wholesale_price", lambda: product.wholesale_price),
        "name": ("name", lambda: _extract_base_name(product.name)),
        "category": ("category", lambda: product.category),
        "currency": ("currency", lambda: product.currency),
        "unit": ("unit", lambda: product.unit),
        "minimum_stock": ("minimum_stock", lambda: product.minimum_stock),
        "material": ("material", lambda: product.material or ""),
        "width": ("width", lambda: product.width or ""),
        "description": ("description", lambda: product.description or ""),
    }

    # إذا حددنا الحقول المتغيرة، نزامن فقط تلك الحقول
    fields_to_check = fields_changed if fields_changed else field_mapping.keys()

    for field in fields_to_check:
        if field in field_mapping:
            base_field, value_getter = field_mapping[field]
            new_value = value_getter()
            current_value = getattr(base_product, base_field, None)

            if new_value != current_value:
                setattr(base_product, base_field, new_value)
                update_fields.append(base_field)

    if update_fields:
        # إضافة updated_at
        from django.utils import timezone
        base_product.updated_at = timezone.now()
        update_fields.append("updated_at")

        # تحديث بـ update() لتجنب تشغيل signals
        from inventory.models import BaseProduct
        BaseProduct.objects.filter(pk=base_product.pk).update(
            **{f: getattr(base_product, f) for f in update_fields}
        )
        logger.info(
            f"🔄 Synced {len(update_fields)} fields for BaseProduct {base_product.code}: "
            f"{', '.join(update_fields)}"
        )


def _extract_base_name(full_name):
    """استخراج الاسم الأساسي من اسم المنتج الكامل"""
    from inventory.variant_services import VariantService
    base_name, _ = VariantService.parse_product_code(full_name)
    return base_name or full_name


# ============================================================
# المرحلة 3: توليد QR
# ============================================================
def _generate_qr_for_base(base_product):
    """
    توليد QR للمنتج الأساسي وحفظه مباشرة

    يستخدم update() بدلاً من save() لتجنب أي signals
    """
    try:
        if base_product.generate_qr(force=True):
            from inventory.models import BaseProduct
            BaseProduct.objects.filter(pk=base_product.pk).update(
                qr_code_base64=base_product.qr_code_base64
            )
            logger.info(f"📊 QR generated for BaseProduct {base_product.code}")
            return True
    except Exception as e:
        logger.error(f"❌ QR generation error for {base_product.code}: {e}")
    return False


# ============================================================
# المرحلة 4: مزامنة Cloudflare
# ============================================================
def _sync_to_cloudflare(base_product):
    """
    مزامنة المنتج مع Cloudflare KV

    تشمل:
    - مزامنة بيانات المنتج
    - تحديث خريطة الأسماء (Name Map) إذا لزم الأمر
    """
    try:
        from public.cloudflare_sync import get_cloudflare_sync
        from public.models import CloudflareSettings

        # التحقق من تفعيل المزامنة
        try:
            cf_settings = CloudflareSettings.get_settings()
            if not cf_settings.is_enabled or not cf_settings.auto_sync_on_save:
                return
        except Exception:
            if not getattr(settings, "CLOUDFLARE_SYNC_ENABLED", False):
                return

        sync = get_cloudflare_sync()
        if not sync.is_configured():
            return

        # مزامنة المنتج
        result = sync.sync_product(base_product)
        if result:
            logger.info(f"☁️ Cloudflare synced: {base_product.code}")

            # تحديث خريطة الأسماء إذا كان للمنتج اسم مختلف عن الكود
            _update_name_map_entry(base_product, sync)
        else:
            logger.warning(f"⚠️ Cloudflare sync failed for {base_product.code}")

    except Exception as e:
        logger.error(f"❌ Cloudflare sync error for {base_product.code}: {e}")


def _update_name_map_entry(base_product, sync=None):
    """
    تحديث إدخال واحد في خريطة الأسماء (Name Map) في Cloudflare KV

    هذا يضمن أن QR codes القديمة (التي تحمل الاسم) تعمل مع الأكواد الجديدة
    """
    try:
        if sync is None:
            from public.cloudflare_sync import get_cloudflare_sync
            sync = get_cloudflare_sync()

        if not sync.is_configured():
            return

        # جلب الأسماء القديمة من المتغيرات المرتبطة
        from inventory.models import ProductVariant
        variants = ProductVariant.objects.filter(
            base_product=base_product,
            legacy_product__isnull=False
        ).select_related("legacy_product")

        names_to_add = {}

        # اسم المنتج الأساسي كمفتاح → الكود كقيمة
        if base_product.name and base_product.name != base_product.code:
            names_to_add[base_product.name] = base_product.code
            names_to_add[base_product.name.upper()] = base_product.code

        # أسماء المنتجات القديمة المرتبطة
        for variant in variants:
            if variant.legacy_product and variant.legacy_product.name:
                old_name = variant.legacy_product.name
                if old_name != base_product.code:
                    names_to_add[old_name] = base_product.code
                    names_to_add[old_name.upper()] = base_product.code

        if not names_to_add:
            return

        # إرسال تحديث خريطة الأسماء الجزئي
        import requests
        try:
            response = requests.post(
                f"{sync.worker_url}/sync",
                json={
                    "action": "update_name_map",
                    "entries": names_to_add,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Sync-API-Key": sync.api_key,
                },
                timeout=15,
            )
            if response.status_code == 200:
                logger.info(
                    f"📝 Name map updated for {base_product.code}: "
                    f"{len(names_to_add)} entries"
                )
            else:
                logger.warning(
                    f"⚠️ Name map update failed: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Name map update request failed: {e}")

    except Exception as e:
        logger.error(f"❌ Name map update error: {e}")


# ============================================================
# نقاط الدخول للـ Signals
# ============================================================
def on_product_saved(product_id, created=False, update_fields=None):
    """
    يُستدعى عند حفظ منتج في النظام القديم

    Args:
        product_id: معرف المنتج
        created: هل هو منتج جديد
        update_fields: الحقول المحدثة (إذا كان تحديثاً جزئياً)
    """
    # تخطي إذا كان التحديث لحقول غير مهمة فقط
    if update_fields:
        important_fields = {
            "name", "code", "price", "wholesale_price", "currency",
            "unit", "category", "category_id", "minimum_stock",
            "material", "width", "description",
        }
        if not any(f in important_fields for f in update_fields):
            return

    auto_migrate_and_sync(product_id, fields_changed=update_fields)


def on_product_deleted(product_code):
    """
    يُستدعى عند حذف منتج

    Args:
        product_code: كود المنتج المحذوف
    """
    if not product_code:
        return

    thread = threading.Thread(
        target=_handle_product_deletion,
        args=(product_code,),
        daemon=True,
        name=f"product-delete-{product_code}",
    )
    thread.start()


def _handle_product_deletion(product_code):
    """حذف المنتج من Cloudflare"""
    try:
        from public.cloudflare_sync import get_cloudflare_sync
        from public.models import CloudflareSettings

        try:
            cf_settings = CloudflareSettings.get_settings()
            if not cf_settings.is_enabled:
                return
        except Exception:
            if not getattr(settings, "CLOUDFLARE_SYNC_ENABLED", False):
                return

        sync = get_cloudflare_sync()
        if sync.is_configured():
            sync.delete_product(product_code)
            logger.info(f"🗑️ Product {product_code} deleted from Cloudflare")

    except Exception as e:
        logger.error(f"❌ Delete from Cloudflare error for {product_code}: {e}")


# ============================================================
# مزامنة BaseProduct مباشرة (للحالات التي يتم فيها تعديل BaseProduct)
# ============================================================
def on_base_product_saved(base_product_id, update_fields=None):
    """
    يُستدعى عند حفظ BaseProduct مباشرة (من الأدمن أو البرمجة)

    Args:
        base_product_id: معرف المنتج الأساسي
        update_fields: الحقول المحدثة
    """
    # تخطي حالات التحديث غير المهمة
    if update_fields:
        important_fields = {
            "name", "code", "base_price", "wholesale_price", "currency",
            "unit", "category", "category_id", "minimum_stock",
            "material", "width", "description", "is_active",
        }
        if not any(f in important_fields for f in update_fields):
            return

    thread = threading.Thread(
        target=_run_base_product_sync,
        args=(base_product_id,),
        daemon=True,
        name=f"base-product-sync-{base_product_id}",
    )
    thread.start()


def _run_base_product_sync(base_product_id):
    """مزامنة BaseProduct مع Cloudflare في الخلفية"""
    try:
        from inventory.models import BaseProduct

        base_product = BaseProduct.objects.get(pk=base_product_id)
        if not base_product.code or not base_product.is_active:
            return

        # توليد QR إذا لم يكن موجوداً
        if not base_product.qr_code_base64:
            _generate_qr_for_base(base_product)

        # مزامنة Cloudflare
        _sync_to_cloudflare(base_product)

    except Exception as e:
        logger.error(f"❌ BaseProduct sync error for {base_product_id}: {e}")


# ============================================================
# مزامنة جماعية بعد الرفع الجماعي (Bulk Upload)
# ============================================================
def bulk_post_upload_pipeline(product_ids):
    """
    خط إنتاج جماعي بعد الرفع الجماعي من Excel

    يعمل في thread منفصل ويعالج المنتجات بدفعات صغيرة
    لتقليل الحمل على قاعدة البيانات و Cloudflare

    Args:
        product_ids: قائمة معرفات المنتجات المضافة/المعدلة
    """
    if not product_ids:
        return

    thread = threading.Thread(
        target=_run_bulk_pipeline,
        args=(list(product_ids),),
        daemon=True,
        name="bulk-product-pipeline",
    )
    thread.start()


def _run_bulk_pipeline(product_ids):
    """
    تنفيذ خط الإنتاج الجماعي

    يعالج المنتجات بدفعات صغيرة مع تأخير بين الدفعات
    """
    import time

    from inventory.models import BaseProduct, Product, ProductVariant
    from public.cloudflare_sync import get_cloudflare_sync
    from public.models import CloudflareSettings

    logger.info(f"🚀 Bulk pipeline started for {len(product_ids)} products")

    # التحقق من تفعيل Cloudflare
    cf_enabled = False
    try:
        cf_settings = CloudflareSettings.get_settings()
        cf_enabled = cf_settings.is_enabled
    except Exception:
        cf_enabled = getattr(settings, "CLOUDFLARE_SYNC_ENABLED", False)

    sync = get_cloudflare_sync() if cf_enabled else None

    migrated_count = 0
    qr_count = 0
    synced_count = 0
    batch_size = 20
    name_map_entries = {}

    for i in range(0, len(product_ids), batch_size):
        batch_ids = product_ids[i:i + batch_size]

        try:
            products = Product.objects.filter(
                pk__in=batch_ids, code__isnull=False
            ).exclude(code="")

            # جلب المتغيرات الموجودة لهذه المنتجات
            existing_variants = {
                v.legacy_product_id: v
                for v in ProductVariant.objects.filter(
                    legacy_product_id__in=batch_ids
                ).select_related("base_product")
            }

            base_products_to_sync = []

            for product in products:
                try:
                    # التحقق من وجود ربط
                    if product.id in existing_variants:
                        variant = existing_variants[product.id]
                        base_product = variant.base_product

                        # مزامنة البيانات
                        _sync_product_data_to_base(product, base_product)
                    else:
                        # ترحيل
                        base_product = _auto_migrate_product(product)
                        if base_product:
                            migrated_count += 1

                    if base_product:
                        # توليد QR
                        if not base_product.qr_code_base64:
                            if _generate_qr_for_base(base_product):
                                qr_count += 1

                        base_products_to_sync.append(base_product)

                        # تجميع إدخالات خريطة الأسماء
                        if base_product.name and base_product.name != base_product.code:
                            name_map_entries[base_product.name] = base_product.code
                            name_map_entries[base_product.name.upper()] = base_product.code

                except Exception as e:
                    logger.error(f"❌ Bulk pipeline error for product {product.code}: {e}")

            # مزامنة الدفعة مع Cloudflare
            if sync and sync.is_configured() and base_products_to_sync:
                try:
                    formatted = [sync.format_base_product(bp) for bp in base_products_to_sync]
                    data = {"action": "sync_all", "products": formatted}
                    if sync._send_request(data):
                        synced_count += len(formatted)
                        # تحديث حالة المزامنة
                        from django.utils import timezone
                        bp_ids = [bp.pk for bp in base_products_to_sync]
                        BaseProduct.objects.filter(pk__in=bp_ids).update(
                            cloudflare_synced=True,
                            last_synced_at=timezone.now()
                        )
                except Exception as e:
                    logger.error(f"❌ Bulk Cloudflare sync error: {e}")

        except Exception as e:
            logger.error(f"❌ Bulk pipeline batch error: {e}")

        # تأخير قصير بين الدفعات لتقليل الحمل
        if i + batch_size < len(product_ids):
            time.sleep(0.5)

    # إرسال خريطة الأسماء دفعة واحدة
    if sync and sync.is_configured() and name_map_entries:
        try:
            import requests
            response = requests.post(
                f"{sync.worker_url}/sync",
                json={
                    "action": "update_name_map",
                    "entries": name_map_entries,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Sync-API-Key": sync.api_key,
                },
                timeout=30,
            )
            if response.status_code == 200:
                logger.info(f"📝 Bulk name map updated: {len(name_map_entries)} entries")
        except Exception as e:
            logger.warning(f"⚠️ Bulk name map update failed: {e}")

    logger.info(
        f"✅ Bulk pipeline complete: "
        f"{migrated_count} migrated, {qr_count} QR generated, "
        f"{synced_count} synced to Cloudflare"
    )
