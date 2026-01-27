from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from installations.models import InstallationPayment
from orders.models import Order
from orders.models import Payment as OrderPayment

User = get_user_model()

class Command(BaseCommand):
    help = 'Syncs Installation Payments to Order Payments'

    def handle(self, *args, **options):
        self.stdout.write("Starting sync of Installation Payments to Order Payments...")
        
        count = 0
        errors = 0
        
        # Get all installation payments
        inst_payments = InstallationPayment.objects.all()
        
        for inst_pay in inst_payments:
            try:
                order = inst_pay.installation.order
                
                # Check if a matching OrderPayment already exists (deduplication)
                # We use a heuristic based on order, amount, and date proximity (if needed)
                # or simplified: assume if amount matches and created within 1 minute, it's a match?
                # Actually, for existing data, it's safer to just create them if they don't exist.
                # Since the system WAS NOT creating them before, we can assume any InstallationPayment
                # that doesn't have a clear counterpart needs a sync.
                # However, since there was no link, we can't be 100% sure.
                # Let's verify if an OrderPayment exists with the exact same amount created around the same time.
                
                exists = OrderPayment.objects.filter(
                    order=order,
                    amount=inst_pay.amount,
                    # payment_date__date=inst_pay.created_at.date() # created_at might be different
                ).exists()
                
                if not exists:
                    with transaction.atomic():
                        # Determine user (fallback to first superuser if None)
                        user = inst_pay.created_by
                        if not user:
                            user = User.objects.filter(is_superuser=True).first()
                            
                        # Create OrderPayment
                        OrderPayment.objects.create(
                            order=order,
                            amount=inst_pay.amount,
                            payment_method=inst_pay.payment_method or "cash",
                            reference_number=inst_pay.receipt_number or f"SYNC-INST-{inst_pay.id}",
                            notes=f"دفعة تركيب (مزامنة): {inst_pay.get_payment_type_display()} - {inst_pay.notes}",
                            created_by=user,
                            # We can't easily set created_at on creation for auto_now_add fields without trickery,
                            # but OrderPayment.payment_date is auto_now_add.
                            # We will let it set to NOW, but mention the original date in notes if needed.
                        )
                        
                        # Update Order Paid Amount
                        # We trigger the save() method of OrderPayment which updates the order.
                        # But to be safe, we can manually ensure order is updated.
                        
                        count += 1
                        self.stdout.write(self.style.SUCCESS(f"Synced payment {inst_pay.id} for Order {order.order_number}"))
                        
                else:
                    self.stdout.write(f"Skipping payment {inst_pay.id} (already likely exists)")
                    
                # Fix created_by if None on InstallationPayment
                if not inst_pay.created_by:
                     default_user = User.objects.filter(is_superuser=True).first()
                     inst_pay.created_by = default_user
                     inst_pay.save(update_fields=['created_by'])

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error syncing payment {inst_pay.id}: {e}"))
                errors += 1

        # Force update all orders involved to ensure totals are correct
        for inst_pay in inst_payments:
             try:
                 order = inst_pay.installation.order
                 # Recalculate total paid
                 total_paid = OrderPayment.objects.filter(order=order).aggregate(models.Sum('amount'))['amount__sum'] or 0
                 order.paid_amount = total_paid
                 order.save(update_fields=['paid_amount'])
                 
                 # Check debt
                 if order.remaining_amount <= 0:
                     from installations.models import CustomerDebt
                     CustomerDebt.objects.filter(order=order, is_paid=False).update(is_paid=True)
                     
             except Exception:
                 pass

        self.stdout.write(self.style.SUCCESS(f"Sync Complete. Created {count} payments. Errors: {errors}"))
