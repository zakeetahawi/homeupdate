
import os

import django
from django.db.models import F
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from factory_accounting.models import ProductionStatusLog
from manufacturing.models import ManufacturingOrder
from orders.models import OrderStatusLog


def repair_missing_users():
    print("🛠️ Repairing Missing Users in Production Logs...")
    print("=" * 60)
    
    # 1. Find ProductionStatusLogs with no user
    missing_user_logs = ProductionStatusLog.objects.filter(changed_by__isnull=True).order_by('-timestamp')
    
    count = missing_user_logs.count()
    if count == 0:
        print("✅ No logs found with missing users.")
        return

    print(f"⚠️ Found {count} logs with missing user. Attempting repair...")
    
    repaired_count = 0
    
    for plog in missing_user_logs:
        # Define a tight time window (e.g., +/- 10 seconds)
        # We observed logs are usually within milliseconds
        start_time = plog.timestamp - timezone.timedelta(seconds=10)
        end_time = plog.timestamp + timezone.timedelta(seconds=10)
        
        order = plog.manufacturing_order.order
        if not order:
            continue
            
        # Look for matching OrderStatusLog
        # We check if the new_status roughly matches the manufacturing status logic
        # But primarily rely on timestamp and order
        
        match = OrderStatusLog.objects.filter(
            order=order,
            created_at__range=(start_time, end_time),
            changed_by__isnull=False
        ).first()
        
        if match:
            print(f"   🔧 Repairing Log {plog.id} for Order {plog.manufacturing_order.manufacturing_code}...")
            print(f"      Found Match: User {match.changed_by} at {match.created_at}")
            
            plog.changed_by = match.changed_by
            plog.save()
            repaired_count += 1
        else:
            # print(f"   ❌ No match found for Log {plog.id} (Time: {plog.timestamp})")
            pass

    print("\n" + "=" * 60)
    print(f"🎉 Repair Complete! Fixed {repaired_count} out of {count} logs.")

if __name__ == "__main__":
    repair_missing_users()
