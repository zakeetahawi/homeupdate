from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Reset database sequence for accounts_user table"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get the maximum ID from the table
            cursor.execute("SELECT MAX(id) FROM accounts_user")
            max_id = cursor.fetchone()[0] or 1

            # Set the sequence to the next available ID
            cursor.execute(
                "SELECT setval('accounts_user_id_seq', %s, false)", [max_id + 1]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully reset sequence for accounts_user to {max_id + 1}"
                )
            )
