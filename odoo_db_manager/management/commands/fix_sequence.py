from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fix the sequence for the GoogleSheetMapping table"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get the current max ID
            cursor.execute("SELECT MAX(id) FROM odoo_db_manager_googlesheetmapping")
            max_id = cursor.fetchone()[0] or 0

            # Reset the sequence to max_id + 1
            cursor.execute(
                "SELECT setval('odoo_db_manager_googlesheetmapping_id_seq', %s, false)",
                [max_id + 1],
            )

            self.stdout.write(
                self.style.SUCCESS(f"Successfully set sequence to {max_id + 1}")
            )
