#!/usr/bin/env python
"""
Script to update existing factory cards with calculated data
تحديث البطاقات الموجودة بالبيانات المحسوبة

Usage:
    python manage.py shell < scripts/update_existing_factory_cards.py
    OR
    python scripts/update_existing_factory_cards.py
"""

import os
import sys

import django

# Setup Django environment if running as standalone script
if __name__ == "__main__":
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Setup Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

from factory_accounting.models import FactoryCard


def update_existing_cards():
    """
    Update existing factory cards with calculated meter and cutter cost data
    تحديث البطاقات الموجودة بالبيانات المحسوبة
    """
    print("Starting factory cards update...")
    print("=" * 60)
    
    # Get all cards with zero meters (likely not calculated)
    cards_to_update = FactoryCard.objects.filter(total_billable_meters=0)
    total_cards = cards_to_update.count()
    
    print(f"Found {total_cards} cards with zero meters to update")
    
    if total_cards == 0:
        print("No cards need updating. All cards have calculated data.")
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
                print(f"Progress: {i}/{total_cards} cards processed...")
                
        except Exception as e:
            error_count += 1
            print(f"❌ Error updating card {card.id} (Order: {card.order_number}): {e}")
    
    print("=" * 60)
    print(f"✅ Update completed!")
    print(f"   - Successfully updated: {updated_count} cards")
    print(f"   - Errors: {error_count} cards")
    print(f"   - Total processed: {total_cards} cards")
    
    # Show sample of updated cards
    if updated_count > 0:
        print("\n📊 Sample of updated cards:")
        sample_cards = FactoryCard.objects.filter(
            total_billable_meters__gt=0
        ).order_by('-updated_at')[:5]
        
        for card in sample_cards:
            print(f"   - Order {card.order_number}: "
                  f"{card.total_billable_meters}m, "
                  f"Cutter Cost: {card.total_cutter_cost}, "
                  f"Production Date: {card.production_date}")


if __name__ == "__main__":
    update_existing_cards()
