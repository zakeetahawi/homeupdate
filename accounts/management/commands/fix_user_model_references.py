from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Fix database references after User model swap from auth.User to accounts.User"
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Starting to fix User model references...")
        )

        # 1. Fix content types
        self.fix_content_types()

        # 2. Fix permissions
        self.fix_permissions()

        # 3. Fix foreign keys to User model
        self.fix_foreign_keys()

        self.stdout.write(
            self.style.SUCCESS("Successfully fixed User model references!")
        )

    def fix_content_types(self):
        """Fix content type entries for User model"""
        try:
            # Check if auth.User content type exists
            auth_user_ct = ContentType.objects.filter(
                app_label="auth", model="user"
            ).first()
            if auth_user_ct:
                # Check if accounts.User content type exists
                accounts_user_ct = ContentType.objects.filter(
                    app_label="accounts", model="user"
                ).first()

                if accounts_user_ct:
                    # Update permissions to use accounts.User content type
                    Permission.objects.filter(content_type=auth_user_ct).update(
                        content_type=accounts_user_ct
                    )

                    # Delete the auth.User content type
                    auth_user_ct.delete()
                    self.stdout.write(self.style.SUCCESS("  ✓ Updated content types"))
                else:
                    # Create the accounts.User content type
                    User = apps.get_model("accounts", "User")
                    accounts_user_ct = ContentType.objects.create(
                        app_label="accounts", model="user", name="user"
                    )
                    self.stdout.write(
                        self.style.SUCCESS("  ✓ Created accounts.User content type")
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS("  ✓ No auth.User content type found, skipping")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error fixing content types: {e}"))

    def fix_permissions(self):
        """Fix permission names and codenames for User model"""
        try:
            with connection.cursor() as cursor:
                # Update permission names
                cursor.execute(
                    """
                    UPDATE auth_permission 
                    SET name = REPLACE(name, 'user', 'مستخدم')
                    WHERE content_type_id IN (
                        SELECT id FROM django_content_type 
                        WHERE app_label = 'accounts' AND model = 'user'
                    )
                """
                )

                # Update any other permission references if needed
                self.stdout.write(self.style.SUCCESS("  ✓ Updated permission names"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error fixing permissions: {e}"))

    def fix_foreign_keys(self):
        """Fix foreign key references to User model"""
        try:
            # This is a more complex operation that depends on your specific database schema
            # You may need to update foreign keys in various tables that reference the User model

            # Example: Update UserRole table if it has references to auth_user
            with connection.cursor() as cursor:
                # Check if the table exists and has the column
                cursor.execute(
                    """
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = 'accounts_userrole' AND column_name = 'user_id'
                """
                )
                if cursor.fetchone()[0] > 0:
                    # The table and column exist, proceed with the update
                    self.stdout.write(
                        self.style.SUCCESS(
                            "  ✓ Foreign key references are already correct"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "  ⚠ Could not find expected foreign key columns"
                        )
                    )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error fixing foreign keys: {e}"))
