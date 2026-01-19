"""
Django management command to update existing factory cards
تحديث البطاقات الموجودة بالبيانات المحسوبة

Usage:
    python manage.py update_factory_cards
"""

from django.core.management.base import BaseCommand

from factory_accounting.models import FactoryCard


class Command(BaseCommand):
    help = "Update existing factory cards with calculated meter and cutter cost data"

    def handle(self, *args, **options):
        self.stdout.write("Starting factory cards update...")
        self.stdout.write("=" * 60)
        
        # Get all cards with zero meters (likely not calculated)
        cards_to_update = FactoryCard.objects.filter(total_billable_meters=0)
        total_cards = cards_to_update.count()
        
        self.stdout.write(f"Found {total_cards} cards with zero meters to update")
        
        if total_cards == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No cards need updating. All cards have calculated data."
                )
            )
            return
        
        updated_count = 0
        error_count = 0
        
        for i, card in enumerate(cards_to_update, 1):
            try:
                # Calculate total meters and cutter costs
                card.calculate_total_meters()
                
                # Update production date if missing
                if not card.production_date:
                    card.update_production_date()
                
                updated_count += 1
                
                # Progress indicator
                if i % 10 == 0 or i == total_cards:
                    self.stdout.write(f"Progress: {i}/{total_cards} cards processed...")
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error updating card {card.id} (Order: {card.order_number}): {e}"
                    )
                )
        
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("Update completed!"))
        self.stdout.write(f"   - Successfully updated: {updated_count} cards")
        self.stdout.write(f"   - Errors: {error_count} cards")
        self.stdout.write(f"   - Total processed: {total_cards} cards")
        
        # Show sample of updated cards
        if updated_count > 0:
            self.stdout.write("\n📊 Sample of updated cards:")
            sample_cards = FactoryCard.objects.filter(
                total_billable_meters__gt=0
            ).order_by('-updated_at')[:5]
            
            for card in sample_cards:
                self.stdout.write(
                    f"   - Order {card.order_number}: "
                    f"{card.total_billable_meters}m, "
                    f"Cutter Cost: {card.total_cutter_cost}, "
                    f"Production Date: {card.production_date}"
                )
