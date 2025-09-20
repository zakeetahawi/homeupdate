#!/usr/bin/env python
"""
Script to clean up duplicate InstallationSchedule records.
Keeps only the most recent record for each order.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append('/home/zakee/homeupdate')
django.setup()

from installations.models import InstallationSchedule
from django.db.models import Count, Max
from django.db import transaction

def cleanup_duplicate_installation_schedules():
    """Clean up duplicate InstallationSchedule records, keeping only the most recent one per order."""

    print("🔍 Analyzing duplicate InstallationSchedule records...")

    # Find orders with multiple InstallationSchedule records
    duplicates = InstallationSchedule.objects.values('order').annotate(
        count=Count('id')
    ).filter(count__gt=1).order_by('-count')

    if not duplicates:
        print("✅ No duplicate records found!")
        return

    print(f"📊 Found {len(duplicates)} orders with duplicate records:")
    total_duplicates = 0

    with transaction.atomic():
        for dup in duplicates:
            order_id = dup['order']
            count = dup['count']

            # Get all InstallationSchedule records for this order
            installations = InstallationSchedule.objects.filter(order_id=order_id).order_by('-updated_at')

            # Keep the most recent one (first in the list)
            keep_installation = installations.first()
            delete_installations = installations[1:]  # All others to delete

            print(f"  Order {keep_installation.order.order_number}: keeping 1, deleting {len(delete_installations)}")

            # Delete the duplicates
            for installation in delete_installations:
                print(f"    🗑️ Deleting InstallationSchedule ID {installation.id} (status: {installation.status})")
                installation.delete()

            total_duplicates += len(delete_installations)

    print("\n✅ Cleanup completed!")
    print(f"🗑️ Deleted {total_duplicates} duplicate records")
    print(f"📋 Kept {len(duplicates)} records (one per order)")

if __name__ == '__main__':
    cleanup_duplicate_installation_schedules()