from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Reset the sequence to a very high number to avoid conflicts"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Set sequence to a very high number
            new_sequence_value = 1000
            cursor.execute(
                "SELECT setval('odoo_db_manager_googlesheetmapping_id_seq', %s, false)",
                [new_sequence_value],
            )

            self.stdout.write(
                self.style.SUCCESS(f"Successfully set sequence to {new_sequence_value}")
            )

            # Verify the change
            cursor.execute(
                "SELECT last_value FROM odoo_db_manager_googlesheetmapping_id_seq"
            )
            current_value = cursor.fetchone()[0]
            self.stdout.write(f"Current sequence value is now: {current_value}")
