"""
إصلاح أكواد المنتجات المؤقتة (_TEMP_) واستبدالها بالأكواد الصحيحة من المنتج القديم
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import BaseProduct, ProductVariant


class Command(BaseCommand):
    help = "Fix BaseProduct codes that start with _TEMP_ by using the legacy product code"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually apply changes (dry-run by default)",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        temp_bps = BaseProduct.objects.filter(code__startswith="_TEMP_")
        total = temp_bps.count()
        self.stdout.write(f"Found {total} BaseProducts with _TEMP_ codes")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to fix."))
            return

        fixed = 0
        skipped = 0
        conflicts = 0

        for bp in temp_bps:
            variant = (
                ProductVariant.objects.filter(base_product=bp)
                .select_related("legacy_product")
                .first()
            )

            if not variant or not variant.legacy_product:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP {bp.code} ({bp.name}): no variant or legacy product"
                    )
                )
                skipped += 1
                continue

            new_code = variant.legacy_product.code
            if not new_code:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP {bp.code} ({bp.name}): legacy product has no code"
                    )
                )
                skipped += 1
                continue

            # Check for conflicts
            if BaseProduct.objects.filter(code=new_code).exclude(id=bp.id).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"  CONFLICT {bp.code} ({bp.name}): code {new_code} already exists"
                    )
                )
                conflicts += 1
                continue

            self.stdout.write(f"  {bp.code} -> {new_code} ({bp.name})")

            if apply:
                bp.code = new_code
                bp.save(update_fields=["code"])

            fixed += 1

        self.stdout.write("")
        self.stdout.write(f"Fixed: {fixed}, Skipped: {skipped}, Conflicts: {conflicts}")

        if not apply and fixed > 0:
            self.stdout.write(
                self.style.WARNING("Dry-run mode. Use --apply to save changes.")
            )
        elif apply:
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {fixed} codes."))
