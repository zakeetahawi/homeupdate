from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'List all GoogleSheetMapping entries and sequence status'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get all mappings
            cursor.execute('SELECT id, name FROM odoo_db_manager_googlesheetmapping ORDER BY id')
            mappings = cursor.fetchall()
            
            # Get current sequence value
            cursor.execute('SELECT last_value FROM odoo_db_manager_googlesheetmapping_id_seq')
            current_seq = cursor.fetchone()[0]
            
            self.stdout.write(f'Current sequence value: {current_seq}')
            self.stdout.write('\nExisting mappings:')
            for id, name in mappings:
                self.stdout.write(f'ID: {id}, Name: {name}')
            
            if mappings:
                max_id = max(mapping[0] for mapping in mappings)
                self.stdout.write(f'\nHighest ID in use: {max_id}')
                self.stdout.write(f'Next available ID: {max_id + 1}')
            else:
                self.stdout.write('No mappings found')
