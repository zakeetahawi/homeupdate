"""
منطق الرفع الذكي للمخزون - يمنع التكرارات وينقل للمستودعات الصحيحة
ويحدث أوامر التقطيع تلقائياً
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


def smart_update_product(
    product_data, warehouse, user, upload_mode, cache=None, fast_mode=True
):
    """
    تحديث ذكي للمنتج - ينقله للمستودع الصحيح ويمنع التكرار

    Args:
        product_data: dict - بيانات المنتج من Excel
        warehouse: Warehouse - المستودع المحدد في الملف
        user: User - المستخدم
        upload_mode: str - وضع الرفع

    Returns:
        dict - نتيجة العملية
    """
    from .models import (
        BaseProduct,
        Product,
        ProductVariant,
        StockTransaction,
        Warehouse,
    )

    result = {
        "action": None,  # created, updated, moved, skipped
        "product": None,
        "old_warehouse": None,
        "new_warehouse": warehouse,
        "message": "",
    }

    code = product_data.get("code")
    name = product_data.get("name")

    try:
        # البحث عن المنتج - في fast_mode نعتمد على الكاش فقط للسرعة القصوى
        product = None

        if cache and "products" in cache:
            # بحث سريع في الكاش فقط
            if code and code in cache["products"]:
                product = cache["products"][code]
            elif code and code.isdigit():
                # بحث ذكي بالأصفار البادئة في الكاش
                for padding in [3, 4, 5, 6]:
                    padded = code.zfill(padding)
                    if padded in cache["products"]:
                        product = cache["products"][padded]
                        break

        # البحث في قاعدة البيانات إذا لم يُجد في الكاش
        if not product and code:
            try:
                product = Product.objects.get(code=code)
            except Product.DoesNotExist:
                if code.isdigit():
                    for padding in [3, 4, 5, 6]:
                        padded_code = code.zfill(padding)
                        try:
                            product = Product.objects.get(code=padded_code)
                            break
                        except Product.DoesNotExist:
                            continue

        # إذا تم العثور على المنتج (سواء من الكاش أو من قاعدة البيانات)
        if product:

            result["product"] = product

            # وضع: إضافة فقط - تجاهل الموجود
            if upload_mode == "add_only":
                result["action"] = "skipped"
                result["message"] = f"منتج موجود: {code}"
                return result

            # التحديث الذكي أو الدمج
            if upload_mode in ["smart_update", "merge_warehouses"]:
                # ✅ تحديث انتقائي - فقط الحقول الممتلئة في الملف
                update_fields_legacy = []

                # تحديث الاسم (فقط إذا كان ممتلئاً)
                if name is not None:
                    name_str = str(name).strip()
                    if name_str and name_str.lower() not in ["nan", "none"]:
                        product.name = name_str
                        update_fields_legacy.append("name")

                # تحديث السعر (فقط إذا كان > 0)
                price_val = product_data.get("price")
                if price_val is not None and price_val > 0:
                    product.price = price_val
                    update_fields_legacy.append("price")

                # تحديث سعر الجملة (فقط إذا كان ممتلئاً وأكبر من 0)
                ws_price = product_data.get("wholesale_price")
                if ws_price is not None and ws_price > 0:
                    try:
                        product.wholesale_price = Decimal(str(ws_price))
                        update_fields_legacy.append("wholesale_price")
                    except:
                        pass

                # تحديث الفئة (فقط إذا كانت موجودة)
                if product_data.get("category") is not None:
                    product.category = product_data["category"]
                    update_fields_legacy.append("category")

                # تحديث الوصف (فقط إذا كان ممتلئاً)
                desc_val = product_data.get("description")
                if desc_val is not None:
                    desc_str = str(desc_val).strip()
                    if desc_str and desc_str.lower() not in ["nan", "none"]:
                        product.description = desc_str
                        update_fields_legacy.append("description")

                # تحديث الحد الأدنى (يقبل 0 لكن يجب أن يكون موجوداً)
                min_stock = product_data.get("minimum_stock")
                if min_stock is not None:
                    try:
                        product.minimum_stock = int(float(str(min_stock)))
                        update_fields_legacy.append("minimum_stock")
                    except:
                        pass

                # تحديث العملة (فقط إذا كانت ممتلئة)
                curr_val = product_data.get("currency")
                if curr_val is not None:
                    curr_str = str(curr_val).strip()
                    if curr_str and curr_str.lower() not in ["nan", "none"]:
                        product.currency = curr_str
                        update_fields_legacy.append("currency")

                # تحديث الوحدة (فقط إذا كانت ممتلئة)
                unit_val = product_data.get("unit")
                if unit_val is not None:
                    unit_str = str(unit_val).strip()
                    if unit_str and unit_str.lower() not in ["nan", "none"]:
                        product.unit = unit_str
                        update_fields_legacy.append("unit")

                # تحديث الخامة (فقط إذا كانت ممتلئة)
                mat_val = product_data.get("material")
                if mat_val is not None:
                    mat_str = str(mat_val).strip()
                    if mat_str and mat_str.lower() not in ["nan", "none"]:
                        product.material = mat_str
                        update_fields_legacy.append("material")

                # تحديث العرض (فقط إذا كان ممتلئاً)
                width_val = product_data.get("width")
                if width_val is not None:
                    width_str = str(width_val).strip()
                    if width_str and width_str.lower() not in ["nan", "none"]:
                        # إضافة cm تلقائياً إذا كان رقماً فقط
                        if width_str.replace(".", "", 1).isdigit():
                            width_str = f"{width_str} cm"
                        product.width = width_str
                        update_fields_legacy.append("width")

                if update_fields_legacy:
                    product.save(update_fields=update_fields_legacy)

                # ===== مزامنة الأسعار مع النظام الجديد BaseProduct =====

                # البحث عن المنتج الأساسي المرتبط
                base_product = None

                # التقاط من الكاش أولاً
                if cache and "variants" in cache and product.id in cache["variants"]:
                    variant = cache["variants"][product.id]
                    base_product = variant.base_product
                else:
                    variant = ProductVariant.objects.filter(
                        legacy_product=product
                    ).first()
                    if variant and variant.base_product:
                        base_product = variant.base_product

                if not base_product:
                    # البحث مباشرة في BaseProduct بالكود (من الكاش أو قاعدة البيانات)
                    if (
                        code
                        and cache
                        and "base_products" in cache
                        and code in cache["base_products"]
                    ):
                        base_product = cache["base_products"][code]
                    else:
                        base_product = BaseProduct.objects.filter(
                            code=product.code
                        ).first()

                    if not base_product and product.code and "/" in product.code:
                        # تجربة بدون الجزء بعد /
                        base_code = product.code.split("/")[0]
                        if (
                            cache
                            and "base_products" in cache
                            and base_code in cache["base_products"]
                        ):
                            base_product = cache["base_products"][base_code]
                        else:
                            base_product = BaseProduct.objects.filter(
                                code=base_code
                            ).first()

                if base_product:
                    update_fields = []

                    # مزامنة الاسم (فقط إذا كان ممتلئاً)
                    if name is not None and name.strip():
                        name_str = str(name).strip()
                        if name_str.lower() not in ["nan", "none"] and base_product.name != name_str:
                            base_product.name = name_str
                            update_fields.append("name")

                    # مزامنة الوصف (فقط إذا كان ممتلئاً)
                    desc = product_data.get("description")
                    if desc is not None:
                        desc_str = str(desc).strip()
                        if desc_str and desc_str.lower() not in ["nan", "none"]:
                            if base_product.description != desc_str:
                                base_product.description = desc_str
                                update_fields.append("description")

                    # مزامنة الفئة
                    category = product_data.get("category")
                    if category is not None and base_product.category != category:
                        base_product.category = category
                        update_fields.append("category")

                    # مزامنة السعر القطاعي (فقط إذا كان > 0)
                    price = product_data.get("price")
                    if price is not None and price > 0:
                        price_decimal = Decimal(str(price))
                        if base_product.base_price != price_decimal:
                            base_product.base_price = price_decimal
                            update_fields.append("base_price")

                    # مزامنة سعر الجملة (فقط إذا كان > 0)
                    wholesale_price = product_data.get("wholesale_price")
                    if wholesale_price is not None and wholesale_price > 0:
                        ws_decimal = Decimal(str(wholesale_price))
                        if base_product.wholesale_price != ws_decimal:
                            base_product.wholesale_price = ws_decimal
                            update_fields.append("wholesale_price")

                    # مزامنة الخامة (فقط إذا كانت ممتلئة)
                    mat = product_data.get("material")
                    if mat is not None:
                        mat_str = str(mat).strip()
                        if mat_str and mat_str.lower() not in ["nan", "none"]:
                            if base_product.material != mat_str:
                                base_product.material = mat_str
                                update_fields.append("material")

                    # مزامنة العرض (فقط إذا كان ممتلئاً)
                    wth = product_data.get("width")
                    if wth is not None:
                        wth_str = str(wth).strip()
                        if wth_str and wth_str.lower() not in ["nan", "none"]:
                            # التنسيق التلقائي للعرض
                            if wth_str.replace(".", "", 1).isdigit():
                                wth_str = f"{wth_str} cm"
                            if base_product.width != wth_str:
                                base_product.width = wth_str
                                update_fields.append("width")

                    # مزامنة العملة (فقط إذا كانت ممتلئة)
                    curr = product_data.get("currency")
                    if curr is not None:
                        curr_str = str(curr).strip()
                        if curr_str and curr_str.lower() not in ["nan", "none"]:
                            if base_product.currency != curr_str:
                                base_product.currency = curr_str
                                update_fields.append("currency")

                    # مزامنة الوحدة (فقط إذا كانت ممتلئة)
                    unit = product_data.get("unit")
                    if unit is not None:
                        unit_str = str(unit).strip()
                        if unit_str and unit_str.lower() not in ["nan", "none"]:
                            if base_product.unit != unit_str:
                                base_product.unit = unit_str
                                update_fields.append("unit")

                    # مزامنة الحد الأدنى (يقبل 0)
                    min_stock = product_data.get("minimum_stock")
                    if min_stock is not None:
                        try:
                            min_stock_int = int(float(str(min_stock)))
                            if base_product.minimum_stock != min_stock_int:
                                base_product.minimum_stock = min_stock_int
                                update_fields.append("minimum_stock")
                        except:
                            pass

                    if update_fields:
                        base_product.save(update_fields=update_fields)

                # نقل المخزون وتوحيد المستودعات (Consolidation + Addition)
                # ✅ تغيير: الكمية تُضاف للرصيد الموجود (وليس استبدال)
                if warehouse:
                    moved = move_product_to_correct_warehouse(
                        product,
                        warehouse,
                        product_data.get("quantity", 0),
                        user,
                        merge_all=True,  # دمج كل المستودعات القديمة لضمان عمل نظيف
                        fast_mode=fast_mode,
                        replacement_mode=False,  # ✅ إضافة الكمية (وليس استبدال)
                    )

                    if moved["moved"]:
                        result["action"] = "moved"
                        result["old_warehouse"] = moved["from_warehouse"]
                        result["message"] = (
                            f"نُقل من {moved['from_warehouse']} إلى {warehouse}"
                        )
                    else:
                        if not result["action"]:
                            result["action"] = "updated"
                        result["message"] = "تم التحديث"
                else:
                    # لا يوجد مستودع محدد - لكن نضيف الكمية إلى أي مستودع موجود
                    quantity = product_data.get("quantity", 0)
                    if quantity > 0:
                        # البحث عن آخر مستودع استخدمه المنتج
                        from .models import StockTransaction
                        last_transaction = StockTransaction.objects.filter(
                            product=product
                        ).order_by("-transaction_date").first()
                        
                        if last_transaction and last_transaction.warehouse:
                            # إضافة للمستودع الأخير
                            add_stock_transaction(
                                product, 
                                last_transaction.warehouse, 
                                quantity, 
                                user, 
                                "إضافة من Excel - بدون تحديد مستودع"
                            )
                            logger.info(f"✅ تم إضافة {quantity} من {product.code} إلى {last_transaction.warehouse.name}")
                        else:
                            # لا يوجد تاريخ مخزون - نحتاج مستودع افتراضي
                            from .models import Warehouse
                            default_wh = Warehouse.objects.filter(is_active=True).first()
                            if default_wh:
                                add_stock_transaction(
                                    product, 
                                    default_wh, 
                                    quantity, 
                                    user, 
                                    "إضافة من Excel - مستودع افتراضي"
                                )
                                logger.info(f"✅ تم إضافة {quantity} من {product.code} إلى المستودع الافتراضي {default_wh.name}")
                            else:
                                logger.warning(f"⚠️ لا يمكن إضافة الكمية {quantity} للمنتج {product.code} - لا يوجد مستودع")
                    
                    if not result["action"]:
                        result["action"] = "updated"
                    result["message"] = "تم التحديث"

                return result

        # إنشاء منتج جديد بجميع البيانات
        # التأكد من وجود اسم للمنتج الجديد
        final_name = name or code or "منتج جديد بدون اسم"

        # إنشاء المنتج الجديد
        product = Product.objects.create(
            name=final_name,
            code=code,
            price=product_data.get("price", 0),
            wholesale_price=product_data.get("wholesale_price", 0),
            category=product_data.get("category"),
            description=product_data.get("description", ""),
            minimum_stock=product_data.get("minimum_stock", 0),
            currency=product_data.get("currency", "EGP"),
            unit=product_data.get("unit", "piece"),
            material=product_data.get("material", ""),
            width=product_data.get("width", ""),
        )
        result["action"] = "created"
        result["message"] = "تم الإنشاء"

    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء/تحديث المنتج {code}: {e}")
        raise

    # إضافة الكمية الأولية للمنتج الجديد
    quantity = product_data.get("quantity", 0)
    if quantity > 0 and warehouse and result["action"] == "created":
        add_stock_transaction(product, warehouse, quantity, user, "إنشاء من Excel")

    result["product"] = product

    return result


def move_product_to_correct_warehouse(
    product,
    target_warehouse,
    new_quantity,
    user,
    merge_all=False,
    fast_mode=False,
    replacement_mode=False,
):
    """
    نقل المنتج للمستودع الصحيح

    Args:
        product: Product
        target_warehouse: Warehouse - المستودع المستهدف
        new_quantity: float - الكمية الجديدة
        user: User
        merge_all: bool - دمج كل المستودعات

    Returns:
        dict - تفاصيل النقل
    """
    from .models import StockTransaction, Warehouse

    result = {
        "moved": False,
        "from_warehouse": None,
        "merged_warehouses": [],
        "total_merged_quantity": 0,
    }

    # تخطي المنطق المعقد في الرفع السريع تماماً قبل أي استعلامات
    if fast_mode:
        if new_quantity > 0 and target_warehouse:
            add_stock_transaction(
                product, target_warehouse, new_quantity, user, "رفع سريع من Excel"
            )
        return result

    from django.db.models import Sum

    # الحصول على كل المعاملات الحالية
    current_stocks = (
        StockTransaction.objects.filter(product=product)
        .values("warehouse")
        .annotate(total=Sum("quantity"))
        .filter(total__gt=0)
    )

    if not current_stocks:
        # لا يوجد مخزون - إضافة مباشرة
        if new_quantity > 0 and target_warehouse:
            add_stock_transaction(
                product, target_warehouse, new_quantity, user, "رفع من Excel"
            )
        return result

    # إذا كان في مستودع واحد فقط
    if len(current_stocks) == 1:
        current_wh_id = current_stocks[0]["warehouse"]
        current_qty = current_stocks[0]["total"]

        # إذا كان في نفس المستودع المطلوب
        if current_wh_id == target_warehouse.id:
            # تحديث الكمية فقط
            if new_quantity > 0:
                add_stock_transaction(
                    product, target_warehouse, new_quantity, user, "تحديث من Excel"
                )
            return result

        # نقل من مستودع لآخر
        current_wh = Warehouse.objects.get(id=current_wh_id)

        # إخراج من المستودع القديم
        remove_stock_transaction(
            product, current_wh, current_qty, user, f"نقل إلى {target_warehouse.name}"
        )

        # إضافة للمستودع الجديد (الكمية القديمة + الجديدة)
        total_qty = Decimal(str(current_qty)) + Decimal(str(new_quantity))
        add_stock_transaction(
            product,
            target_warehouse,
            float(total_qty),
            user,
            f"نُقل من {current_wh.name}",
        )

        result["moved"] = True
        result["from_warehouse"] = current_wh.name

        # تحديث أوامر التقطيع 🔥
        cutting_update = update_cutting_orders_after_move(
            product, current_wh, target_warehouse, user
        )
        result["cutting_orders_updated"] = cutting_update.get("updated", 0)
        result["cutting_orders_split"] = cutting_update.get("split", 0)

        # إعادة حساب الأرصدة للتأكد من الصحة
        recalculate_product_balances(product)

        return result

    # المنتج موجود في عدة مستودعات أو تم طلب الدمج الكامل (Consolidation)
    if merge_all or len(current_stocks) > 1:
        # إفراغ كل المستودعات الأخرى أولاً
        total_source_quantity = Decimal("0")

        for stock in current_stocks:
            wh_id = stock["warehouse"]
            wh_qty = Decimal(str(stock["total"]))

            # إذا كان هو المستودع المستهدف، لن نفرغه الآن بل سنعدله لاحقاً
            if wh_id == target_warehouse.id:
                total_source_quantity += wh_qty
                continue

            wh = Warehouse.objects.get(id=wh_id)

            # إخراج كل الكمية من المستودع القديم
            remove_stock_transaction(
                product,
                wh,
                float(wh_qty),
                user,
                f"دمج وتوحيد في {target_warehouse.name}",
            )

            total_source_quantity += wh_qty
            result["merged_warehouses"].append(wh.name)

            # تحديث أوامر التقطيع لهذا المستودع المفرغ
            update_cutting_orders_after_move(product, wh, target_warehouse, user)

        # التعامل مع الكمية في المستودع المستهدف
        if replacement_mode:
            # وضع الاستبدال: يجب أن يكون الرصيد النهائي = new_quantity
            final_target_qty = Decimal(str(new_quantity))

            # الحصول على الرصيد الحالي في المستودع المستهدف تحديداً
            target_current_qty = Decimal("0")
            for s in current_stocks:
                if s["warehouse"] == target_warehouse.id:
                    target_current_qty = Decimal(str(s["total"]))
                    break

            adjustment = final_target_qty - target_current_qty
            if adjustment > 0:
                add_stock_transaction(
                    product,
                    target_warehouse,
                    float(adjustment),
                    user,
                    "تحديث وجرد من Excel (زيادة)",
                )
            elif adjustment < 0:
                remove_stock_transaction(
                    product,
                    target_warehouse,
                    float(abs(adjustment)),
                    user,
                    "تحديث وجرد من Excel (خصم)",
                )
        else:
            # وضع الإضافة العادي (القديم)
            if new_quantity > 0:
                add_stock_transaction(
                    product, target_warehouse, new_quantity, user, "إضافة من Excel"
                )

        result["moved"] = True
        result["from_warehouse"] = f"{len(result['merged_warehouses'])} مستودعات"
        result["total_merged_quantity"] = float(total_source_quantity)

        # تحديث أوامر التقطيع لكل المستودعات المدموجة 🔥
        total_cutting_updated = 0
        total_cutting_split = 0

        for stock in current_stocks:
            old_wh = Warehouse.objects.get(id=stock["warehouse"])
            if old_wh.id != target_warehouse.id:
                cutting_update = update_cutting_orders_after_move(
                    product, old_wh, target_warehouse, user
                )
                total_cutting_updated += cutting_update.get("updated", 0)
                total_cutting_split += cutting_update.get("split", 0)

        result["cutting_orders_updated"] = total_cutting_updated
        result["cutting_orders_split"] = total_cutting_split

        # إعادة حساب الأرصدة للتأكد من الصحة بعد الدمج
        recalculate_product_balances(product)

        return result

    return result


def add_stock_transaction(product, warehouse, quantity, user, notes):
    """إضافة معاملة مخزون (دخول) - محسّن للسرعة"""
    from django.db import connection

    from .models import StockTransaction

    if quantity <= 0:
        return

    # استعلام مباشر أسرع من ORM
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT running_balance 
            FROM inventory_stocktransaction 
            WHERE product_id = %s AND warehouse_id = %s 
            ORDER BY transaction_date DESC, id DESC 
            LIMIT 1
        """,
            [product.id, warehouse.id],
        )
        row = cursor.fetchone()
        previous_balance = row[0] if row else 0

    new_balance = Decimal(str(previous_balance)) + Decimal(str(quantity))

    StockTransaction.objects.create(
        product=product,
        warehouse=warehouse,
        transaction_type="in",
        reason="purchase",
        quantity=quantity,
        reference="رفع سريع",
        notes=notes,
        created_by=user,
        running_balance=float(new_balance),
        transaction_date=timezone.now(),
    )


def remove_stock_transaction(product, warehouse, quantity, user, notes):
    """إزالة معاملة مخزون (خروج) - محسّن للسرعة"""
    from django.db import connection

    from .models import StockTransaction

    if quantity <= 0:
        return

    # استعلام مباشر أسرع
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT running_balance 
            FROM inventory_stocktransaction 
            WHERE product_id = %s AND warehouse_id = %s 
            ORDER BY transaction_date DESC, id DESC 
            LIMIT 1
        """,
            [product.id, warehouse.id],
        )
        row = cursor.fetchone()
        previous_balance = row[0] if row else 0

    new_balance = Decimal(str(previous_balance)) - Decimal(str(quantity))

    StockTransaction.objects.create(
        product=product,
        warehouse=warehouse,
        transaction_type="out",
        reason="transfer",
        quantity=quantity,
        reference="نقل ذكي",
        notes=notes,
        created_by=user,
        running_balance=float(new_balance),
        transaction_date=timezone.now(),
    )


def find_duplicate_products():
    """
    البحث عن المنتجات المكررة في عدة مستودعات
    محسّن بالكامل: يستخدم استعلامات قليلة جداً بدلاً من آلاف الاستعلامات

    Returns:
        list - قائمة المنتجات المكررة
    """
    from collections import defaultdict

    from django.db.models import F, OuterRef, Subquery

    from .models import Product, StockTransaction

    # استعلام فرعي للحصول على آخر رصيد لكل منتج ومستودع
    last_transaction_subquery = (
        StockTransaction.objects.filter(
            product_id=OuterRef("product_id"), warehouse_id=OuterRef("warehouse_id")
        )
        .order_by("-transaction_date", "-id")
        .values("running_balance")[:1]
    )

    # استعلام فرعي للحصول على تاريخ آخر معاملة
    last_date_subquery = (
        StockTransaction.objects.filter(
            product_id=OuterRef("product_id"), warehouse_id=OuterRef("warehouse_id")
        )
        .order_by("-transaction_date", "-id")
        .values("transaction_date")[:1]
    )

    # الحصول على جميع الأزواج الفريدة (منتج، مستودع) مع آخر رصيد
    # في استعلام واحد فقط
    warehouse_stocks = (
        StockTransaction.objects.values("product_id", "warehouse_id")
        .distinct()
        .annotate(
            last_balance=Subquery(last_transaction_subquery),
            last_date=Subquery(last_date_subquery),
            warehouse_name=F("warehouse__name"),
            product_code=F("product__code"),
            product_name=F("product__name"),
        )
        .filter(last_balance__gt=0)  # فقط المستودعات ذات الرصيد الموجب
        .order_by("product_id")
    )

    # تجميع البيانات حسب المنتج في الذاكرة
    product_data = defaultdict(
        lambda: {
            "warehouses": [],
            "warehouse_ids": [],
            "quantities": {},
            "code": None,
            "name": None,
            "last_transaction_dates": {},
        }
    )

    for stock in warehouse_stocks:
        product_id = stock["product_id"]
        warehouse_id = stock["warehouse_id"]
        warehouse_name = stock["warehouse_name"]
        balance = stock["last_balance"]
        last_date = stock["last_date"]

        # حفظ معلومات المنتج (أول مرة فقط)
        if product_data[product_id]["code"] is None:
            product_data[product_id]["code"] = stock["product_code"]
            product_data[product_id]["name"] = stock["product_name"]

        # إضافة المستودع والكمية
        product_data[product_id]["warehouses"].append(warehouse_name)
        product_data[product_id]["warehouse_ids"].append(warehouse_id)
        product_data[product_id]["quantities"][warehouse_name] = balance
        
        # حفظ تاريخ آخر معاملة (من الاستعلام الفرعي - بدون query إضافي)
        if last_date:
            product_data[product_id]["last_transaction_dates"][warehouse_name] = last_date

    # تصفية المنتجات المكررة فقط (أكثر من مستودع واحد)
    duplicate_ids = [
        pid for pid, data in product_data.items() if len(data["warehouses"]) > 1
    ]

    # الحصول على كائنات المنتجات دفعة واحدة (استعلام واحد)
    if not duplicate_ids:
        return []

    products_dict = {
        p.id: p
        for p in Product.objects.filter(id__in=duplicate_ids).only("id", "code", "name")
    }

    # بناء النتيجة النهائية
    duplicates = []
    for product_id in duplicate_ids:
        if product_id in products_dict:
            data = product_data[product_id]

            # تحديد المستودع الأخير (الذي حصل فيه آخر تحويل)
            last_warehouse = None
            last_warehouse_id = None
            if data["last_transaction_dates"]:
                # الترتيب حسب التاريخ - الأحدث أولاً
                sorted_warehouses = sorted(
                    data["last_transaction_dates"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                last_warehouse = sorted_warehouses[0][0]  # اسم المستودع
                # العثور على ID المستودع
                last_warehouse_idx = data["warehouses"].index(last_warehouse)
                last_warehouse_id = data["warehouse_ids"][last_warehouse_idx]

            duplicates.append(
                {
                    "product": products_dict[product_id],
                    "code": data["code"],
                    "name": data["name"],
                    "warehouses_count": len(data["warehouses"]),
                    "warehouses": data["warehouses"],
                    "warehouse_ids": data["warehouse_ids"],
                    "quantities": data["quantities"],
                    "suggested_warehouse": last_warehouse,  # المستودع المقترح للدمج
                    "suggested_warehouse_id": last_warehouse_id,
                }
            )

    return duplicates


def clean_start_reset():
    """
    مسح كامل للنظام - حذف كل المنتجات والمعاملات
    ⚠️ خطير - استخدم بحذر!
    """
    from installations.models import StockTransfer

    from .models import Product, StockTransaction

    logger.warning("⚠️ بدء المسح الكامل للنظام!")

    with transaction.atomic():
        # حذف التحويلات أولاً
        deleted_transfers = StockTransfer.objects.all().count()
        StockTransfer.objects.all().delete()
        # logger.info(f"✅ حُذف {deleted_transfers} تحويل")

        # حذف المعاملات
        deleted_transactions = StockTransaction.objects.all().count()
        StockTransaction.objects.all().delete()
        # logger.info(f"✅ حُذف {deleted_transactions} معاملة")

        # حذف المنتجات
        deleted_products = Product.objects.all().count()
        Product.objects.all().delete()
        # logger.info(f"✅ حُذف {deleted_products} منتج")

    logger.warning("✅ اكتمل المسح الكامل!")

    return {
        "deleted_products": deleted_products,
        "deleted_transactions": deleted_transactions,
        "deleted_transfers": deleted_transfers,
    }


def update_cutting_orders_after_move(product, old_warehouse, new_warehouse, user):
    """
    تحديث أوامر التقطيع بعد نقل المنتج للمستودع الصحيح

    Args:
        product: Product - المنتج المنقول
        old_warehouse: Warehouse - المستودع القديم
        new_warehouse: Warehouse - المستودع الجديد
        user: User - المستخدم

    Returns:
        dict - إحصائيات التحديث
    """
    try:
        from cutting.models import CuttingOrder, CuttingOrderItem

        # أوامر التقطيع المتأثرة (غير المكتملة فقط)
        affected_orders = CuttingOrder.objects.filter(
            items__order_item__product=product,
            status__in=["pending", "in_progress"],
            warehouse=old_warehouse,
        ).distinct()

        if not affected_orders.exists():
            return {
                "updated": 0,
                "split": 0,
                "total_affected": 0,
                "message": "لا توجد أوامر تقطيع متأثرة",
                "affected_order_ids": [],
            }

        updated_count = 0
        split_count = 0

        # logger.info(f"🔍 فحص {affected_orders.count()} أمر تقطيع متأثر...")

        for cutting_order in affected_orders:
            # فحص: هل كل المنتجات في الأمر يجب أن تكون في المستودع الجديد؟
            all_items_should_be_in_new_warehouse = True

            for item in cutting_order.items.all():
                item_product = item.order_item.product

                # إذا كان المنتج هو المنتج المنقول → نعم
                if item_product.id == product.id:
                    continue

                # إذا كان منتج آخر، نفحص مستودعه الحالي
                from .models import StockTransaction

                latest_stock = (
                    StockTransaction.objects.filter(product=item_product)
                    .values("warehouse")
                    .annotate(total=Sum("quantity"))
                    .filter(total__gt=0)
                    .order_by("-total")
                    .first()
                )

                if latest_stock and latest_stock["warehouse"] != new_warehouse.id:
                    all_items_should_be_in_new_warehouse = False
                    break

            if all_items_should_be_in_new_warehouse:
                # حالة بسيطة: نقل الأمر بالكامل للمستودع الجديد
                cutting_order.warehouse = new_warehouse
                cutting_order.notes = (
                    (cutting_order.notes or "")
                    + f"\n📦 [تحديث تلقائي] تم تحديث المستودع من '{old_warehouse.name}' إلى '{new_warehouse.name}' - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                )
                cutting_order.save()
                updated_count += 1

                # logger.info(f"✅ تحديث أمر تقطيع {cutting_order.cutting_code}: {old_warehouse.name} → {new_warehouse.name}")
            else:
                # حالة معقدة: تقسيم الأمر
                new_order = split_cutting_order(
                    cutting_order, product, new_warehouse, user
                )
                split_count += 1

                logger.info(
                    f"🔀 تقسيم أمر تقطيع {cutting_order.cutting_code} → {new_order.cutting_code}"
                )

        # جمع IDs الأوامر المتأثرة
        affected_order_ids = list(affected_orders.values_list("id", flat=True))

        result = {
            "updated": updated_count,
            "split": split_count,
            "total_affected": affected_orders.count(),
            "message": f"تم تحديث {updated_count} أمر، تقسيم {split_count} أمر",
            "affected_order_ids": affected_order_ids,
        }

        # إرسال إشعار إذا تم التحديث 🔔
        if updated_count > 0 or split_count > 0:
            try:
                from django.contrib.auth import get_user_model

                from notifications.models import Notification

                User = get_user_model()

                notification_msg = f"تم تحديث {updated_count + split_count} أمر تقطيع بعد نقل '{product.name}' من '{old_warehouse.name}' إلى '{new_warehouse.name}'"

                notification = Notification.objects.create(
                    title="تحديث أوامر التقطيع تلقائياً",
                    message=notification_msg,
                    notification_type="cutting_order_created",  # استخدام نوع موجود
                    priority="normal",
                    created_by=user,
                )

                # إضافة visibility للمستخدمين المعنيين (cutting staff + admins)
                cutting_users = User.objects.filter(
                    groups__name__in=["Cutting", "Admin", "Manager"]
                ).distinct()

                notification.visible_to.set(cutting_users)

                logger.info(f"✅ تم إرسال إشعار لـ {cutting_users.count()} مستخدم")
            except Exception as e:
                logger.warning(f"⚠️ فشل إرسال الإشعار: {e}")

        # logger.info(f"📊 نتيجة تحديث أوامر التقطيع: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ خطأ في تحديث أوامر التقطيع: {e}")
        import traceback

        traceback.print_exc()
        return {
            "updated": 0,
            "split": 0,
            "total_affected": 0,
            "error": str(e),
            "affected_order_ids": [],
        }


def split_cutting_order(original_order, moved_product, new_warehouse, user):
    """
    تقسيم أمر تقطيع عند نقل منتج لمستودع مختلف

    Args:
        original_order: CuttingOrder - الأمر الأصلي
        moved_product: Product - المنتج المنقول
        new_warehouse: Warehouse - المستودع الجديد
        user: User - المستخدم

    Returns:
        CuttingOrder - الأمر الجديد
    """
    import uuid

    from cutting.models import CuttingOrder, CuttingOrderItem

    # إنشاء كود فريد للأمر الجديد
    new_code = f"{original_order.cutting_code}-S{uuid.uuid4().hex[:4].upper()}"

    # إنشاء أمر جديد للمستودع الجديد
    new_order = CuttingOrder.objects.create(
        cutting_code=new_code,
        order=original_order.order,
        warehouse=new_warehouse,
        status="pending",
        assigned_to=original_order.assigned_to,
        notes=f"🔀 منقول من أمر {original_order.cutting_code} بعد نقل منتج '{moved_product.name}' للمستودع '{new_warehouse.name}'",
    )

    # نقل العناصر المتعلقة بالمنتج المنقول
    items_to_move = original_order.items.filter(order_item__product=moved_product)

    moved_items_count = 0
    for item in items_to_move:
        # إنشاء نسخة في الأمر الجديد
        CuttingOrderItem.objects.create(
            cutting_order=new_order,
            order_item=item.order_item,
            status=item.status,
            cutter_name=item.cutter_name,
            permit_number=item.permit_number,
            receiver_name=item.receiver_name,
            notes=item.notes,
        )

        # حذف من الأمر القديم
        item.delete()
        moved_items_count += 1

    # تحديث ملاحظات الأمر القديم
    original_order.notes = (
        (original_order.notes or "")
        + f"\n🔀 [تقسيم تلقائي] تم نقل {moved_items_count} عنصر لأمر جديد {new_order.cutting_code} - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    )
    original_order.save()

    logger.info(
        f"🔀 تقسيم ناجح: {original_order.cutting_code} → {new_order.cutting_code} ({moved_items_count} عنصر)"
    )

    return new_order


def delete_empty_warehouses(user):
    """
    حذف المستودعات الفارغة التي لا تحتوي على مخزون ولا أوامر نشطة

    Args:
        user: User - المستخدم الذي يقوم بالحذف

    Returns:
        dict - إحصائيات الحذف
    """
    from django.db.models import Sum

    from cutting.models import CuttingOrder

    from .models import StockTransaction, Warehouse

    try:
        logger.info("🔍 البحث عن المستودعات الفارغة...")

        # البحث عن المستودعات الفارغة
        empty_warehouses = []

        for warehouse in Warehouse.objects.all():
            # حساب المخزون الحالي
            total_stock = (
                StockTransaction.objects.filter(warehouse=warehouse).aggregate(
                    total=Sum("quantity")
                )["total"]
                or 0
            )

            # عد أوامر التقطيع النشطة
            active_cutting = CuttingOrder.objects.filter(
                warehouse=warehouse, status__in=["pending", "in_progress"]
            ).count()

            # إذا كان فارغاً ولا يوجد له أوامر تقطيع نشطة
            if total_stock == 0 and active_cutting == 0:
                # تأكد أنه ليس مستودع أقمشة رسمي
                if not warehouse.is_official_fabric_warehouse:
                    empty_warehouses.append(
                        {
                            "warehouse": warehouse,
                            "name": warehouse.name,
                            "last_activity": warehouse.updated_at,
                        }
                    )

        if not empty_warehouses:
            logger.info("✅ لا توجد مستودعات فارغة للحذف")
            return {"deleted": 0, "warehouses": [], "message": "لا توجد مستودعات فارغة"}

        # حذف المستودعات الفارغة
        deleted_names = []
        for item in empty_warehouses:
            warehouse = item["warehouse"]
            deleted_names.append(warehouse.name)

            logger.warning(f"🗑️ حذف مستودع فارغ: {warehouse.name}")
            warehouse.delete()

        result = {
            "deleted": len(deleted_names),
            "warehouses": deleted_names,
            "message": f"تم حذف {len(deleted_names)} مستودع فارغ",
        }

        logger.info(f"✅ {result['message']}: {', '.join(deleted_names)}")
        return result

    except Exception as e:
        logger.error(f"❌ خطأ في حذف المستودعات الفارغة: {e}")
        import traceback

        traceback.print_exc()
        return {"deleted": 0, "warehouses": [], "error": str(e)}


def recalculate_product_balances(product):
    """
    إعادة حساب أرصدة منتج معين في جميع مستودعاته
    يتم استدعاء هذه الدالة بعد عمليات النقل والدمج للتأكد من صحة الأرصدة
    
    Args:
        product: Product - المنتج المراد إعادة حساب أرصدته
    
    Returns:
        bool - True إذا نجحت العملية
    """
    from django.db import connection
    from decimal import Decimal
    
    try:
        with connection.cursor() as cursor:
            # الحصول على جميع المستودعات التي تحتوي على معاملات لهذا المنتج
            cursor.execute("""
                SELECT DISTINCT warehouse_id
                FROM inventory_stocktransaction
                WHERE product_id = %s
                ORDER BY warehouse_id
            """, [product.id])
            
            warehouse_ids = [row[0] for row in cursor.fetchall()]
            
            for warehouse_id in warehouse_ids:
                # جلب جميع المعاملات مرتبة
                cursor.execute("""
                    SELECT id, quantity
                    FROM inventory_stocktransaction
                    WHERE product_id = %s AND warehouse_id = %s
                    ORDER BY transaction_date ASC, id ASC
                """, [product.id, warehouse_id])
                
                transactions = cursor.fetchall()
                running_balance = Decimal('0')
                
                # تحديث كل معاملة
                for tx_id, quantity in transactions:
                    running_balance += Decimal(str(quantity))
                    
                    cursor.execute("""
                        UPDATE inventory_stocktransaction
                        SET running_balance = %s
                        WHERE id = %s
                    """, [float(running_balance), tx_id])
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في إعادة حساب أرصدة المنتج {product.code}: {e}")
        return False
