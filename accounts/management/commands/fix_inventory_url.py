from django.core.management.base import BaseCommand
from accounts.models import Department

class Command(BaseCommand):
    help = 'Fixes the inventory department URL to point to the dashboard'

    def handle(self, *args, **kwargs):
        try:
            # Get the inventory department
            dept = Department.objects.get(code='المخزون')

            # Update the URL name to point to the dashboard
            dept.url_name = 'inventory:dashboard'
            dept.save()

            self.stdout.write(self.style.SUCCESS(f'Successfully updated inventory department URL from {dept.url_name} to inventory:dashboard'))
        except Department.DoesNotExist:
            self.stdout.write(self.style.ERROR('Inventory department not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating inventory department URL: {str(e)}'))
