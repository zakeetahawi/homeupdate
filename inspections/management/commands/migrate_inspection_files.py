"""
Management command to migrate old inspection_file to new InspectionFile model.
This unifies the file storage system.
"""
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from inspections.models import Inspection, InspectionFile


class Command(BaseCommand):
    help = 'Migrate old inspection_file to new InspectionFile model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all inspections with old file but no new files
        inspections_to_migrate = Inspection.objects.exclude(
            inspection_file=''
        ).exclude(
            inspection_file__isnull=True
        ).filter(
            files__isnull=True
        )
        
        total = inspections_to_migrate.count()
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"Found {total} inspections to migrate")
        self.stdout.write(f"{'='*50}\n")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made\n"))
        
        migrated = 0
        errors = 0
        
        for inspection in inspections_to_migrate:
            try:
                if dry_run:
                    self.stdout.write(
                        f"  Would migrate: Inspection #{inspection.id} - {inspection.inspection_file.name}"
                    )
                else:
                    with transaction.atomic():
                        # Create new InspectionFile from old inspection_file
                        new_file = InspectionFile(
                            inspection=inspection,
                            file=inspection.inspection_file,
                            original_filename=os.path.basename(inspection.inspection_file.name),
                            google_drive_file_id=inspection.google_drive_file_id,
                            google_drive_file_url=inspection.google_drive_file_url,
                            google_drive_file_name=inspection.google_drive_file_name,
                            is_uploaded_to_drive=inspection.is_uploaded_to_drive,
                            order=0,
                        )
                        new_file.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Migrated: Inspection #{inspection.id} -> InspectionFile #{new_file.id}"
                            )
                        )
                migrated += 1
                
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error migrating Inspection #{inspection.id}: {str(e)}")
                )
        
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"Migration Summary:")
        self.stdout.write(f"  Total found: {total}")
        self.stdout.write(f"  Migrated: {migrated}")
        self.stdout.write(f"  Errors: {errors}")
        self.stdout.write(f"{'='*50}\n")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("Run without --dry-run to actually migrate the files")
            )
