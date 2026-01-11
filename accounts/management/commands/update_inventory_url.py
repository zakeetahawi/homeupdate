from django.core.management.base import BaseCommand

from accounts.models import Department


class Command(BaseCommand):
    help = "Updates the inventory department URL name"

    def handle(self, *args, **kwargs):
        try:
            dept = Department.objects.get(code="inventory")
            dept.url_name = "inventory:dashboard"  # Update to use the dashboard view
            dept.save()
            self.stdout.write(
                self.style.SUCCESS("Successfully updated inventory department URL")
            )
        except Department.DoesNotExist:
            self.stdout.write(self.style.ERROR("Inventory department not found"))
