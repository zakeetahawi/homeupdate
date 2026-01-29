
import os
import sys
import django
from django.db import transaction
from django.db.models import Q

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from customers.models import Customer
from orders.models import Order
from cutting.models import CuttingOrder
from django.utils import timezone
from datetime import timedelta

def is_bad_code(code):
    if not code:
        return True
    parts = code.split('-')
    if len(parts) < 2:
        return True
    # Check if last part is numeric
    if not parts[-1].isdigit():
        return True
    # Additional check: legacy UUIDs or hex usually look like '7-50cad931' (hex part is not digits)
    return False

def fix_related_records():
    print("Starting COMPREHENSIVE repair (Customers + Orders + Cutting)...")
    
    # 3 Days Lookback
    three_days_ago = timezone.now() - timedelta(days=3)
    print(f"Processing customers created after: {three_days_ago}")
    
    # Fetch ALL customers in this range to ensure even "good" customers 
    # don't have "bad" related records (from before they were fixed).
    customers = Customer.objects.filter(created_at__gte=three_days_ago)
    
    count = customers.count()
    print(f"Found {count} customers to scan.")
    
    fixed_customers = 0
    fixed_orders = 0
    fixed_cutting = 0
    
    # Sort by creation to process sequentially
    customers_list = list(customers)
    customers_list.sort(key=lambda x: x.created_at)

    for i, customer in enumerate(customers_list):
        with transaction.atomic():
            # 1. Check/Fix Customer Code
            original_code = customer.code
            final_code = original_code
            
            if is_bad_code(original_code):
                try:
                    # Generate new VALID code
                    new_code = customer.generate_unique_code()
                    customer.code = new_code
                    customer.save(update_fields=['code'])
                    print(f"[{i+1}/{count}] Fixed Customer: {original_code} -> {new_code}")
                    final_code = new_code
                    fixed_customers += 1
                except Exception as e:
                    print(f"Error fixing customer {original_code}: {e}")
                    continue
            else:
                # Code is fine, but we still check relations
                pass

            # 2. Check/Fix Related Orders
            # Use 'final_code' as the source of truth
            related_orders = Order.objects.filter(customer=customer)
            for order in related_orders:
                old_order_num = order.order_number
                
                # Check if order number matches the pattern "{final_code}-XXXX"
                if not old_order_num or not old_order_num.startswith(final_code + "-"):
                    # Mismatch found!
                    
                    # Extract sequence or default to 0001
                    # Logic: Split old number, try to find last numeric part
                    parts = old_order_num.split('-')
                    if len(parts) >= 1 and parts[-1].isdigit():
                        seq_str = parts[-1]
                        # Validate it's likely a sequence (length 4 is standard but could be any)
                        # We just reuse it.
                    else:
                        # Fallback: calculate sequence based on existing orders?
                        # Or just force 0001 if it's the only order
                        # Let's count earlier orders for this customer to guess?
                        # Simpler: just use '0001' and handle collision
                        seq_str = "0001"
                    
                    new_order_num = f"{final_code}-{seq_str}"
                    
                    # Collision Check (e.g. if we defaulted to 0001 but 0001 already exists correctly?)
                    # If this customer has multiple orders, we need to be careful.
                    # If 2 orders were both bad: 'UUID1' and 'UUID2', both might map to '0001' if we default.
                    
                    # Robust Sequence Finder if collision:
                    collision_check = 0
                    base_seq = int(seq_str) if seq_str.isdigit() else 1
                    
                    while Order.objects.filter(order_number=new_order_num).exclude(pk=order.pk).exists():
                         collision_check += 1
                         new_seq = base_seq + collision_check
                         new_order_num = f"{final_code}-{new_seq:04d}"
                    
                    try:
                        order.order_number = new_order_num
                        order.save(update_fields=['order_number'])
                        print(f"   -> Fixed Order: {old_order_num} -> {new_order_num}")
                        fixed_orders += 1
                        
                        # 3. Check/Fix Cutting Orders for this Order
                        cutting_orders = CuttingOrder.objects.filter(order=order)
                        for co in cutting_orders:
                            old_cut_code = co.cutting_code
                            
                            # Expected format: C-{new_order_num} [-suffix]
                            # Try to preserve suffix from old code if exists
                            # Old: C-OLD-1  -> suffix '-1'
                            # New: C-NEW-1
                            
                            # Simple approach: C-NEW is base. 
                            # If old code had extra parts compared to old order num parts?
                            # Usually Cutting Code is just C-{OrderNum}
                            # Sometimes C-{OrderNum}-{Counter}
                            
                            new_cut_code = f"C-{new_order_num}"
                            
                            # Assume cutting order also needs unique check
                            counter = 0
                            final_cut_code = new_cut_code
                            
                            # If old code had a counter (e.g. was C-XXX-1), we try to keep it 1
                            # But if we just reset to C-NEW, and check collision, it's safer.
                            
                            while CuttingOrder.objects.filter(cutting_code=final_cut_code).exclude(pk=co.pk).exists():
                                counter += 1
                                final_cut_code = f"{new_cut_code}-{counter}"
                                
                            if old_cut_code != final_cut_code:
                                co.cutting_code = final_cut_code
                                co.save(update_fields=['cutting_code'])
                                print(f"      -> Fixed Cutting: {old_cut_code} -> {final_cut_code}")
                                fixed_cutting += 1
                                
                    except Exception as e:
                        print(f"   Error fixing order {old_order_num}: {e}")

    print("-" * 30)
    print(f"Summary:")
    print(f"  Fixed Customers: {fixed_customers}")
    print(f"  Fixed Orders:    {fixed_orders}")
    print(f"  Fixed Cutting:   {fixed_cutting}")
    print("Done.")

if __name__ == "__main__":
    fix_related_records()
