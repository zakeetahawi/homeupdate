from django.core.management.base import BaseCommand
from accounts.models import Department

class Command(BaseCommand):
    help = 'Fixes the inventory department code to use English instead of Arabic'

    def handle(self, *args, **kwargs):
        try:
            # Get the inventory department with Arabic code
            dept = Department.objects.get(code='المخزون')
            
            # Update the code to English
            old_code = dept.code
            dept.code = 'inventory'
            dept.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully updated inventory department code from "{old_code}" to "inventory"'))
        except Department.DoesNotExist:
            self.stdout.write(self.style.ERROR('Inventory department with Arabic code not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating inventory department code: {str(e)}'))
