from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Resets the sequence for a given table"

    def add_arguments(self, parser):
        parser.add_argument("table_name", type=str, help="Name of the table")
        parser.add_argument("column", type=str, help="Name of the column")

    def handle(self, *args, **options):
        table_name = options["table_name"]
        column = options["column"]

        with connection.cursor() as cursor:
            # Get the current max ID
            cursor.execute(f"SELECT MAX({column}) FROM {table_name}")
            max_id = cursor.fetchone()[0] or 0

            # Reset the sequence to the next available ID
            cursor.execute(
                f"""
                SELECT setval(pg_get_serial_sequence('{table_name}', '{column}'), 
                COALESCE((SELECT MAX({column}) FROM {table_name}), 1), true);
            """
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully reset sequence for {table_name}.{column} to {max_id + 1}"
                )
            )
