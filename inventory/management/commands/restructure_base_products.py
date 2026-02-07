"""
Management command لإعادة هيكلة المنتجات الأساسية
يقوم بتحويل:
- الاسم: من DORIS/C WINE إلى DORIS
- الكود: من DORIS إلى باركود أول متغير (مثل 10100300253)
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventory.models import BaseProduct, ProductVariant

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    إعادة هيكلة المنتجات الأساسية:
    - استخدام الكود القديم (مثل DORIS) كاسم جديد
    - استخدام باركود أول متغير كرمز جديد
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض التغييرات بدون تطبيقها",
        )
        parser.add_argument(
            "--base-product-id",
            type=int,
            help="معرف منتج أساسي محدد للتحديث (اختياري)",
        )
        parser.add_argument(
            "--skip-check",
            action="store_true",
            help="تخطي فحص الباركود المكرر",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        base_product_id = options.get("base_product_id")
        skip_check = options["skip_check"]

        self.stdout.write(
            self.style.SUCCESS(
                "="*70
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "🔄 بدء عملية إعادة هيكلة المنتجات الأساسية"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "="*70
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  وضع DRY RUN - لن يتم حفظ التغييرات\n"
                )
            )

        # الحصول على المنتجات المراد تحديثها
        if base_product_id:
            base_products = BaseProduct.objects.filter(id=base_product_id)
            if not base_products.exists():
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ لم يتم العثور على منتج برقم {base_product_id}"
                    )
                )
                return
        else:
            base_products = BaseProduct.objects.all()

        total = base_products.count()
        self.stdout.write(f"\n📊 عدد المنتجات: {total}\n")

        # الإحصائيات
        stats = {
            "total": total,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "no_variants": 0,
            "no_barcode": 0,
            "duplicate_barcode": 0,
            "no_legacy_for_fix": 0,  # منتجات بأسماء خاطئة لكن لا يوجد legacy لإصلاحها
            "fixed": 0,  # عدد المنتجات التي تم إصلاح أسمائها
        }

        for idx, base_product in enumerate(base_products, 1):
            self.stdout.write(
                f"\n[{idx}/{total}] معالجة: {base_product.code} - {base_product.name}"
            )

            try:
                result = self._restructure_base_product(
                    base_product, dry_run, skip_check
                )

                if result["status"] == "updated":
                    stats["updated"] += 1
                    
                    # تحديد نوع التحديث
                    fix_type = ""
                    if result.get("was_fixed"):
                        stats["fixed"] += 1
                        fix_type = " (تم إصلاح اسم خاطئ)"
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ تم التحديث{fix_type}:\n"
                            f"     الاسم القديم: {result['old_name']}\n"
                            f"     الاسم الجديد: {result['new_name']}\n"
                            f"     الكود القديم: {result['old_code']}\n"
                            f"     الكود الجديد: {result['new_code']}"
                        )
                    )
                elif result["status"] == "skipped":
                    stats["skipped"] += 1
                    self.stdout.write(
                        self.style.WARNING(f"  ⏭️  تم التخطي: {result['reason']}")
                    )
                    
                    # تحديث إحصائية معينة
                    if result.get("reason_code") == "no_variants":
                        stats["no_variants"] += 1
                    elif result.get("reason_code") == "no_barcode":
                        stats["no_barcode"] += 1
                    elif result.get("reason_code") == "duplicate_barcode":
                        stats["duplicate_barcode"] += 1
                    elif result.get("reason_code") == "no_legacy_for_fix":
                        stats["no_legacy_for_fix"] += 1

            except Exception as e:
                stats["errors"] += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ خطأ: {str(e)}")
                )
                logger.error(
                    f"خطأ في معالجة BaseProduct {base_product.id}: {e}",
                    exc_info=True,
                )

        # عرض التقرير النهائي
        self._print_summary(stats, dry_run)

    def _restructure_base_product(self, base_product, dry_run=False, skip_check=False):
        """
        إعادة هيكلة منتج أساسي واحد + إصلاح تلقائي للأسماء الخاطئة

        Returns:
            dict مع حالة العملية
        """
        # الحصول على أول متغير
        first_variant = (
            base_product.variants.filter(is_active=True)
            .order_by("created_at")
            .first()
        )

        if not first_variant:
            return {
                "status": "skipped",
                "reason": "لا يوجد متغيرات",
                "reason_code": "no_variants",
            }

        # الحصول على الباركود من المنتج القديم المرتبط
        new_code = None
        
        if first_variant.legacy_product:
            new_code = first_variant.legacy_product.code
        elif first_variant.barcode:
            new_code = first_variant.barcode

        if not new_code:
            return {
                "status": "skipped",
                "reason": "لا يوجد باركود في أول متغير",
                "reason_code": "no_barcode",
            }

        # التحقق من عدم وجود تكرار في الباركود
        if not skip_check:
            existing = BaseProduct.objects.filter(code=new_code).exclude(
                id=base_product.id
            ).first()
            
            if existing:
                return {
                    "status": "skipped",
                    "reason": f"الباركود {new_code} مستخدم بالفعل في {existing.name}",
                    "reason_code": "duplicate_barcode",
                }

        old_name = base_product.name
        old_code = base_product.code

        # ==================== منطق استخراج الاسم الذكي ====================
        from inventory.variant_services import VariantService
        
        was_fixed = False  # علامة للمنتجات التي تم إصلاحها
        
        # الحالة 1: الاسم الحالي = الكود الحالي (كلاهما رقمي) - خطأ يحتاج إصلاح
        if old_name == old_code and old_name.isdigit():
            # محاولة الاستخراج من المنتج القديم
            if first_variant.legacy_product:
                legacy_name = first_variant.legacy_product.name
                base_name, _ = VariantService.parse_product_code(legacy_name)
                
                if not base_name or base_name == legacy_name:
                    # إذا لم ينجح التحليل، استخدم الاسم القديم كاملاً
                    base_name = legacy_name
                
                was_fixed = True  # تم إصلاح المنتج
            else:
                # لا يوجد منتج قديم للإصلاح منه
                return {
                    "status": "skipped",
                    "reason": f"اسم خاطئ ({old_name}) ولا يوجد منتج قديم للإصلاح منه",
                    "reason_code": "no_legacy_for_fix",
                }
        else:
            # الحالة 2: استخراج من الاسم الحالي (الطريقة العادية)
            base_name, _ = VariantService.parse_product_code(old_name)
            
            # إذا لم يُستخرج شيء، استخدم الاسم القديم
            if not base_name or base_name == old_name:
                base_name = old_name
        
        new_name = base_name
        # new_code تم تعيينه بالأعلى

        # التحقق من وجود تغيير فعلي
        if old_name == new_name and old_code == new_code:
            return {
                "status": "skipped",
                "reason": "لا يوجد تغيير مطلوب",
                "reason_code": "no_change",
            }

        if not dry_run:
            # ✅ استخدام update() بدلاً من save() لتجنب:
            # 1. تفعيل signals (Cloudflare sync)
            # 2. إعادة توليد QR
            # 3. فتح اتصالات database إضافية
            # هذا أسرع وأكفأ ولا يسبب "too many clients"
            BaseProduct.objects.filter(pk=base_product.pk).update(
                name=new_name,
                code=new_code,
            )

        return {
            "status": "updated",
            "old_name": old_name,
            "new_name": new_name,
            "old_code": old_code,
            "new_code": new_code,
            "was_fixed": was_fixed,
        }

    def _print_summary(self, stats, dry_run):
        """طباعة ملخص النتائج"""
        self.stdout.write("\n" + "="*70)
        self.stdout.write(
            self.style.SUCCESS("📊 ملخص النتائج")
        )
        self.stdout.write("="*70)

        self.stdout.write(f"\n📦 إجمالي المنتجات: {stats['total']}")
        self.stdout.write(
            self.style.SUCCESS(f"✅ تم التحديث: {stats['updated']}")
        )
        if stats["fixed"] > 0:
            self.stdout.write(
                self.style.SUCCESS(f"   🔧 منها تم إصلاحها: {stats['fixed']}")
            )
        self.stdout.write(
            self.style.WARNING(f"⏭️  تم التخطي: {stats['skipped']}")
        )
        
        if stats["no_variants"] > 0:
            self.stdout.write(f"   - بدون متغيرات: {stats['no_variants']}")
        if stats["no_barcode"] > 0:
            self.stdout.write(f"   - بدون باركود: {stats['no_barcode']}")
        if stats["duplicate_barcode"] > 0:
            self.stdout.write(f"   - باركود مكرر: {stats['duplicate_barcode']}")
        if stats["no_legacy_for_fix"] > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"   - ⚠️  أسماء خاطئة بدون منتج قديم للإصلاح: {stats['no_legacy_for_fix']}"
                )
            )
            
        self.stdout.write(
            self.style.ERROR(f"❌ أخطاء: {stats['errors']}")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  هذا كان DRY RUN - لم يتم حفظ أي تغييرات"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "لتطبيق التغييرات، قم بتشغيل الأمر بدون --dry-run"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✨ تم تحديث {stats['updated']} منتج بنجاح!"
                )
            )

        self.stdout.write("\n" + "="*70 + "\n")
