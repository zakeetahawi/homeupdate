"""
╔══════════════════════════════════════════════════════════════════════╗
║         سكريبت إصلاح البيانات التاريخية للمنتجات الأساسية           ║
╠══════════════════════════════════════════════════════════════════════╣
║  ⚠️  يُشغَّل مرة واحدة فقط لإصلاح البيانات القديمة                  ║
║      النظام الآن يعمل تلقائياً - لا حاجة لتشغيله مجدداً             ║
╠══════════════════════════════════════════════════════════════════════╣
║  ما الذي تغيّر في النظام (variant_services.py):                      ║
║    ✅ link_existing_product: يبحث بالاسم أولاً → لا تكرار جديد       ║
║    ✅ migrate_all_products: يرتب بـ id + يدمج تلقائياً بعد الترحيل   ║
║    ✅ phase1_migrate_products: يدمج تلقائياً بعد اكتماله             ║
║    ✅ consolidate_duplicate_base_products: دالة دمج مستقلة متاحة     ║
╠══════════════════════════════════════════════════════════════════════╣
║  هذا السكريبت يُحل:                                                  ║
║    البيانات القديمة (قبل الإصلاح) حيث كل لون له BaseProduct منفصل   ║
║    BORGO/C1 + BORGO/C2 → BaseProduct واحد "BORGO" بـ 2 variants      ║
╠══════════════════════════════════════════════════════════════════════╣
║  متى تشغّله:                                                          ║
║    مرة واحدة فقط = الآن (لإصلاح الـ 3,245 BaseProduct القديمة)      ║
║    لا تحتاجه بعد ذلك أبداً                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  طريقة التشغيل (إذا احتجت):                                          ║
║    cd /home/zakee/homeupdate                                         ║
║    source venv/bin/activate                                          ║
║    python fix_base_products.py                                       ║
║                                                                      ║
║  آمن للتشغيل المتكرر - يتجاهل ما هو صحيح بالفعل                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.db import transaction, connection
from inventory.models import Product, BaseProduct, ProductVariant

print("=== بدء دمج المنتجات الأساسية ===\n")

# ① بناء مجموعات: base_name → [product_ids, codes]
print("① جمع البيانات...")
all_products = list(
    Product.objects.all().values("id", "name", "code", "price", "category_id")
)

groups = {}
for p in all_products:
    raw_name = (p["name"] or "").strip()
    if not raw_name:
        continue
    # الفصل على / أو \ (بعض المنتجات تستخدم backslash)
    import re as _re
    base_name = _re.split(r'[/\\]', raw_name)[0].strip()
    if not base_name:
        base_name = raw_name
    if base_name not in groups:
        groups[base_name] = []
    groups[base_name].append(p)

print(f"   أسماء أساسية فريدة: {len(groups)}")
print(f"   BaseProducts الحالية: {BaseProduct.objects.count()}")
print(f"   Variants الحالية: {ProductVariant.objects.count()}\n")

# ② الدمج
print("② بدء الدمج...")
stats = {"merged_groups": 0, "deleted_bps": 0, "moved_variants": 0, "skipped": 0, "errors": 0}

processed = 0
for base_name, products in groups.items():
    processed += 1
    if processed % 300 == 0:
        print(f"   تم معالجة {processed}/{len(groups)}...")

    try:
        product_ids = [p["id"] for p in products]

        # إيجاد كل BaseProducts المرتبطة بهذه المنتجات عبر variants
        related_bp_ids = list(
            ProductVariant.objects.filter(legacy_product_id__in=product_ids)
            .values_list("base_product_id", flat=True)
            .distinct()
        )

        if len(related_bp_ids) <= 1:
            # إما لا يوجد أو يوجد واحد فقط - فقط تحديث الكود
            if len(related_bp_ids) == 1:
                bp = BaseProduct.objects.get(id=related_bp_ids[0])
                # تحديث الكود للأصغر
                numeric_codes = [p["code"] for p in products if p["code"] and str(p["code"]).isdigit()]
                if numeric_codes:
                    best_code = min(numeric_codes, key=lambda c: int(c))
                    if str(bp.code) != str(best_code):
                        if not BaseProduct.objects.filter(code=best_code).exclude(id=bp.id).exists():
                            with transaction.atomic():
                                BaseProduct.objects.filter(id=bp.id).update(code=best_code, name=base_name)
            stats["skipped"] += 1
            continue

        # ③ اختيار الـ BaseProduct الرئيسي (أصغر id = الأقدم)
        related_bps = list(BaseProduct.objects.filter(id__in=related_bp_ids).order_by("id"))
        main_bp = related_bps[0]
        duplicates = related_bps[1:]

        # تحديد أفضل كود (أصغر barcode رقمي)
        numeric_codes = [p["code"] for p in products if p["code"] and str(p["code"]).isdigit()]
        if numeric_codes:
            best_code = min(numeric_codes, key=lambda c: int(c))
        else:
            non_empty = [p["code"] for p in products if p["code"]]
            best_code = min(non_empty) if non_empty else base_name

        with transaction.atomic():
            # تحديث الكود والاسم للـ main (مباشرة بـ SQL لتجنب الـ signals)
            # تجنب تعارض الكود إذا كان مستخدماً في bp آخر
            if BaseProduct.objects.filter(code=best_code).exclude(id=main_bp.id).exists():
                # استخدم id مؤقت فريد
                temp_code = f"_TEMP_{main_bp.id}"
                BaseProduct.objects.filter(id=main_bp.id).update(code=temp_code, name=base_name)
                best_code = temp_code
            else:
                BaseProduct.objects.filter(id=main_bp.id).update(code=best_code, name=base_name)

            # نقل variants من كل duplicate للـ main
            for dup_bp in duplicates:
                dup_variants = list(ProductVariant.objects.filter(base_product_id=dup_bp.id))

                for v in dup_variants:
                    # تجنب تكرار variant_code في main_bp
                    vc = v.variant_code
                    if ProductVariant.objects.filter(base_product_id=main_bp.id, variant_code=vc).exclude(id=v.id).exists():
                        vc = f"{vc}_{v.id}"

                    ProductVariant.objects.filter(id=v.id).update(
                        base_product_id=main_bp.id,
                        variant_code=vc,
                    )
                    stats["moved_variants"] += 1

                # حذف الـ duplicate (لا يوجد variants الآن)
                BaseProduct.objects.filter(id=dup_bp.id).delete()
                stats["deleted_bps"] += 1

        stats["merged_groups"] += 1

    except Exception as e:
        print(f"   ❌ خطأ في '{base_name}': {e}")
        stats["errors"] += 1
        continue

print(f"\n=== النتيجة النهائية ===")
print(f"مجموعات مدموجة:      {stats['merged_groups']}")
print(f"BaseProducts محذوفة: {stats['deleted_bps']}")
print(f"Variants منقولة:     {stats['moved_variants']}")
print(f"تجاوز (1 أو 0):      {stats['skipped']}")
print(f"أخطاء:               {stats['errors']}")
print(f"\nBaseProducts الآن: {BaseProduct.objects.count()}")
print(f"Variants الآن:     {ProductVariant.objects.count()}")

# تحقق من RMM-2380
from django.db.models import Count
bp = BaseProduct.objects.filter(name="RMM-2380").first()
if bp:
    print(f"\nRMM-2380: code={bp.code}, variants={bp.variants.count()}")
    for v in bp.variants.order_by("barcode"):
        print(f"  {v.variant_code}: barcode={v.barcode}")

# إحصاء توزيع الـ variants
multi = BaseProduct.objects.annotate(v=Count("variants")).filter(v__gt=1).count()
single = BaseProduct.objects.annotate(v=Count("variants")).filter(v=1).count()
print(f"\nBaseProduct > 1 variant: {multi}")
print(f"BaseProduct = 1 variant: {single}")
