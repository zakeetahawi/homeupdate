from django.core.management.base import BaseCommand
from django.db import transaction

from orders.models import Order


class Command(BaseCommand):
    help = (
        "Recompute order totals from OrderItem rows and persist them on each Order.\n"
        "Useful after changing calculation logic so stored fields reflect item data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Don't save, just report"
        )
        parser.add_argument(
            "--limit", type=int, default=None, help="Limit number of orders to process"
        )
        parser.add_argument(
            "--batch", type=int, default=500, help="Iterator chunk size"
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        limit = options["limit"]
        batch = options["batch"]

        qs = Order.objects.all().order_by("id")
        if limit:
            qs = qs[:limit]

        total = qs.count() if not limit else min(limit, qs.count())
        self.stdout.write(f"Processing {total} orders (dry-run={dry})...")

        processed = 0
        changed = 0

        for order in qs.iterator(chunk_size=batch):
            with transaction.atomic():
                processed += 1
                old_final = order.final_price
                old_total_amount = order.total_amount

                # calculate_final_price should set final_price & total_amount to subtotal (pre-discount)
                try:
                    subtotal = order.calculate_final_price()
                except Exception as e:
                    self.stderr.write(
                        f"Order {order.id}: calculate_final_price raised: {e}"
                    )
                    continue

                if dry:
                    # show what would change
                    if (
                        old_final != order.final_price
                        or old_total_amount != order.total_amount
                    ):
                        self.stdout.write(
                            f"[DRY] Order {order.id}: final_price {old_final} -> {order.final_price}, "
                            f"total_amount {old_total_amount} -> {order.total_amount}"
                        )
                        changed += 1
                else:
                    # persist only if changed to reduce writes
                    if (
                        old_final != order.final_price
                        or old_total_amount != order.total_amount
                    ):
                        order.save(update_fields=["final_price", "total_amount"])
                        self.stdout.write(
                            f"Order {order.id}: final_price {old_final} -> {order.final_price}, "
                            f"total_amount {old_total_amount} -> {order.total_amount}"
                        )
                        changed += 1

        self.stdout.write(f"Done. Processed={processed}, Changed={changed}.")
