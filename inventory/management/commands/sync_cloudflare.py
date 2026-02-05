"""
Management command لمزامنة المنتجات مع Cloudflare KV
يعمل في process منفصل تماماً عن Django الرئيسي

الاستخدام:
    # مزامنة كل المنتجات
    python manage.py sync_cloudflare --all
    
    # مزامنة منتجات محددة بالـ IDs
    python manage.py sync_cloudflare --ids 1,2,3,4,5
    
    # مزامنة المنتجات غير المزامنة فقط
    python manage.py sync_cloudflare --unsynced
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import BaseProduct
from public.cloudflare_sync import get_cloudflare_sync

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "مزامنة المنتجات مع Cloudflare KV (يعمل في الخلفية)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="مزامنة جميع المنتجات النشطة",
        )
        parser.add_argument(
            "--unsynced",
            action="store_true",
            help="مزامنة المنتجات غير المزامنة فقط",
        )
        parser.add_argument(
            "--ids",
            type=str,
            help="IDs المنتجات مفصولة بفواصل (مثال: 1,2,3,4)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="حجم الدفعة (افتراضي: 50)",
        )

    def handle(self, *args, **options):
        cloudflare = get_cloudflare_sync()

        if not cloudflare.is_configured():
            self.stdout.write(
                self.style.ERROR("❌ مزامنة Cloudflare غير مفعّلة في الإعدادات")
            )
            return

        batch_size = options["batch_size"]
        now = timezone.now()

        # تحديد المنتجات المطلوبة
        if options["ids"]:
            # مزامنة منتجات محددة
            ids = [int(x.strip()) for x in options["ids"].split(",")]
            products = BaseProduct.objects.filter(id__in=ids, is_active=True)
            self.stdout.write(f"📦 سيتم مزامنة {products.count()} منتج محدد...")
        elif options["unsynced"]:
            # مزامنة غير المزامنة فقط
            products = BaseProduct.objects.filter(
                is_active=True, cloudflare_synced=False
            )
            self.stdout.write(
                f"📦 سيتم مزامنة {products.count()} منتج غير مزامن..."
            )
        elif options["all"]:
            # مزامنة الكل
            products = BaseProduct.objects.filter(is_active=True)
            self.stdout.write(f"📦 سيتم مزامنة {products.count()} منتج...")
        else:
            self.stdout.write(
                self.style.ERROR(
                    "❌ يجب تحديد --all أو --unsynced أو --ids"
                )
            )
            return

        if products.count() == 0:
            self.stdout.write(self.style.WARNING("⚠️  لا توجد منتجات للمزامنة"))
            return

        # تحميل المنتجات مع العلاقات
        products = products.select_related("category").prefetch_related(
            "variants__color"
        )
        products_list = list(products)
        total = len(products_list)
        synced = 0
        failed = 0

        self.stdout.write(
            self.style.SUCCESS(f"🚀 بدء المزامنة... (حجم الدفعة: {batch_size})")
        )

        # معالجة الدفعات
        for i in range(0, total, batch_size):
            batch = products_list[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size

            self.stdout.write(
                f"⏳ معالجة الدفعة {batch_num}/{total_batches} ({len(batch)} منتج)..."
            )

            try:
                # تنسيق المنتجات
                formatted_products = [
                    cloudflare.format_base_product(p) for p in batch
                ]

                # إرسال الدفعة
                data = {"action": "sync_all", "products": formatted_products}

                if cloudflare._send_request(data):
                    # تحديث قاعدة البيانات
                    batch_ids = [p.id for p in batch]
                    BaseProduct.objects.filter(id__in=batch_ids).update(
                        cloudflare_synced=True, last_synced_at=now
                    )
                    synced += len(batch)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ نجح: {len(batch)} منتج (إجمالي: {synced}/{total})"
                        )
                    )
                else:
                    failed += len(batch)
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ❌ فشل: {len(batch)} منتج (إجمالي فاشل: {failed})"
                        )
                    )

            except Exception as e:
                failed += len(batch)
                self.stdout.write(
                    self.style.ERROR(f"  ❌ خطأ في الدفعة: {str(e)}")
                )
                logger.error(f"Batch sync error: {e}", exc_info=True)

        # ملخص النتائج
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 ملخص المزامنة:"))
        self.stdout.write(f"  • المنتجات المعالجة: {total}")
        self.stdout.write(
            self.style.SUCCESS(f"  • نجح: {synced} ({synced*100//total if total>0 else 0}%)")
        )
        if failed > 0:
            self.stdout.write(
                self.style.ERROR(f"  • فشل: {failed} ({failed*100//total if total>0 else 0}%)")
            )
        self.stdout.write("=" * 60)

        if synced > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ اكتملت المزامنة بنجاح!")
            )
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ فشلت المزامنة بالكامل"))
