"""
Django management command to optimize complaints database performance
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Optimize complaints database with proper indexes and constraints"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show SQL commands without executing them",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # SQL commands for optimization
        optimization_commands = [
            # Composite indexes for common query patterns
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_status_created 
            ON complaints_complaint(status, created_at DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_customer_status 
            ON complaints_complaint(customer_id, status);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_assigned_status 
            ON complaints_complaint(assigned_to_id, status) 
            WHERE assigned_to_id IS NOT NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_deadline_status 
            ON complaints_complaint(deadline, status) 
            WHERE status IN ('new', 'in_progress');
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_type_created 
            ON complaints_complaint(complaint_type_id, created_at DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_priority_created 
            ON complaints_complaint(priority, created_at DESC);
            """,
            # Indexes for complaint updates
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_update_complaint_created 
            ON complaints_complaintupdate(complaint_id, created_at DESC);
            """,
            # Indexes for attachments
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_attachment_complaint_uploaded 
            ON complaints_complaintattachment(complaint_id, uploaded_at DESC);
            """,
            # Indexes for notifications
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_notification_recipient_created 
            ON complaints_complaintnotification(recipient_id, created_at DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_notification_unread 
            ON complaints_complaintnotification(recipient_id, is_read, created_at DESC) 
            WHERE is_read = FALSE;
            """,
            # Indexes for escalations
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_escalation_complaint_escalated 
            ON complaints_complaintescalation(complaint_id, escalated_at DESC);
            """,
            # Performance indexes for dashboard queries
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_rating_not_null 
            ON complaints_complaint(customer_rating) 
            WHERE customer_rating IS NOT NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_complaint_resolved_at_not_null 
            ON complaints_complaint(resolved_at) 
            WHERE resolved_at IS NOT NULL;
            """,
            # Analyze tables for better query planning
            "ANALYZE complaints_complaint;",
            "ANALYZE complaints_complainttype;",
            "ANALYZE complaints_complaintupdate;",
            "ANALYZE complaints_complaintattachment;",
            "ANALYZE complaints_complaintnotification;",
            "ANALYZE complaints_complaintescalation;",
        ]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
            for cmd in optimization_commands:
                self.stdout.write(f"Would execute: {cmd.strip()}")
            return

        # Execute optimization commands
        with connection.cursor() as cursor:
            for cmd in optimization_commands:
                try:
                    self.stdout.write(f"Executing: {cmd.strip()}")
                    cursor.execute(cmd)
                    self.stdout.write(self.style.SUCCESS(f"✓ Successfully executed"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Error: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS("Database optimization completed successfully!")
        )
