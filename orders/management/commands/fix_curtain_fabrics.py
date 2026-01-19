"""
Django management command to fix old curtain fabrics without order_item
تحديث الأقمشة القديمة التي لا تملك order_item

Usage:
    python manage.py fix_curtain_fabrics
"""

from django.core.management.base import BaseCommand

from orders.contract_models import CurtainFabric


class Command(BaseCommand):
    help = "Fix old curtain fabrics by linking them to order_item where possible"

    def handle(self, *args, **options):
        self.stdout.write("Starting curtain fabrics fix...")
        self.stdout.write("=" * 60)
        
        # Get all fabrics without order_item but with draft_order_item
        fabrics_to_fix = CurtainFabric.objects.filter(
            order_item__isnull=True,
            draft_order_item__isnull=False,
            curtain__order__isnull=False  # Only final orders, not drafts
        )
        
        total_fabrics = fabrics_to_fix.count()
        self.stdout.write(f"Found {total_fabrics} fabrics to fix")
        
        if total_fabrics == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No fabrics need fixing. All fabrics are correctly linked."
                )
            )
            return
        
        fixed_count = 0
        error_count = 0
        
        for i, fabric in enumerate(fabrics_to_fix, 1):
            try:
                # Try to find matching OrderItem
                order = fabric.curtain.order
                draft_item = fabric.draft_order_item
                
                if order and draft_item and draft_item.product:
                    # Search for OrderItem with same product
                    from orders.models import OrderItem
                    
                    matching_item = OrderItem.objects.filter(
                        order=order,
                        product=draft_item.product
                    ).first()
                    
                    if matching_item:
                        fabric.order_item = matching_item
                        fabric.save(update_fields=['order_item'])
                        fixed_count += 1
                        
                        if i % 10 == 0 or i == total_fabrics:
                            self.stdout.write(f"Progress: {i}/{total_fabrics} fabrics processed...")
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"No matching OrderItem found for fabric in order {order.order_number}"
                            )
                        )
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error fixing fabric {fabric.id}: {e}"
                    )
                )
        
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("Fix completed!"))
        self.stdout.write(f"   - Successfully fixed: {fixed_count} fabrics")
        self.stdout.write(f"   - Errors: {error_count} fabrics")
        self.stdout.write(f"   - Total processed: {total_fabrics} fabrics")
