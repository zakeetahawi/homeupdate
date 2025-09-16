from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check and display the current sequence status for the accounts_user table'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            try:
                # Get the max ID from the accounts_user table
                cursor.execute("SELECT MAX(id) FROM accounts_user")
                max_id = cursor.fetchone()[0]
                
                # Get the current sequence value
                cursor.execute("SELECT last_value FROM accounts_user_id_seq")
                current_seq = cursor.fetchone()[0]
                
                # Get the sequence name and other details
                cursor.execute("""
                    SELECT c.relname, c.relnamespace::regnamespace as schema, 
                           seqstart, seqincrement, seqmax, seqmin, seqcache, seqcycle
                    FROM pg_sequence s
                    JOIN pg_class c ON s.seqrelid = c.oid
                    WHERE c.relname = 'accounts_user_id_seq'
                """)
                seq_info = cursor.fetchone()
                
                self.stdout.write(self.style.SUCCESS('Accounts User Sequence Information:'))
                self.stdout.write(f"- Current max ID in table: {max_id}")
                self.stdout.write(f"- Current sequence value: {current_seq}")
                
                if seq_info:
                    seq_name, schema, start, increment, max_val, min_val, cache, cycle = seq_info
                    self.stdout.write(f"\nSequence Details:")
                    self.stdout.write(f"- Name: {schema}.{seq_name}")
                    self.stdout.write(f"- Start value: {start}")
                    self.stdout.write(f"- Increment: {increment}")
                    self.stdout.write(f"- Max value: {max_val}")
                    self.stdout.write(f"- Min value: {min_val}")
                    self.stdout.write(f"- Cache: {cache}")
                    self.stdout.write(f"- Cycle: {cycle}")
                
                if max_id is not None and current_seq is not None:
                    gap = current_seq - max_id if max_id is not None else 0
                    self.stdout.write("\nStatus:")
                    self.stdout.write(f"- Gap between sequence and max ID: {gap}")
                    
                    if gap < 0:
                        self.stdout.write(self.style.ERROR("  ⚠️  Sequence is behind the maximum ID! This can cause primary key conflicts."))
                        self.stdout.write(self.style.SUCCESS("  To fix, run: ALTER SEQUENCE accounts_user_id_seq RESTART WITH <new_value>;"))
                        self.stdout.write(f"  Suggested command: ALTER SEQUENCE accounts_user_id_seq RESTART WITH {max_id + 1};")
                    elif gap == 0:
                        self.stdout.write(self.style.SUCCESS("  ✅ Sequence is in sync with the table."))
                    else:
                        self.stdout.write(self.style.WARNING("  ℹ️  Sequence is ahead of the maximum ID. This is normal but may indicate unused sequence values."))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error checking sequence: {str(e)}"))
                logger.exception("Error checking sequence")
