from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Branch
from customers.models import Customer

class Command(BaseCommand):
    help = 'Create main branch and link existing customers to it'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                # Get or create main branch
                branch, created = Branch.objects.get_or_create(
                    code='001',
                    defaults={'name': 'الفرع الرئيسي'}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created branch: {branch.name}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Using existing branch: {branch.name}'))

                # Update existing customers
                customers_updated = Customer.objects.filter(branch__isnull=True).update(branch=branch)
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {customers_updated} customers with main branch')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
