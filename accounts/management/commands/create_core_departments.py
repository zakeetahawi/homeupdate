"""
أمر إدارة لإنشاء الأقسام الأساسية
"""
from django.core.management.base import BaseCommand
from accounts.core_departments import create_core_departments

class Command(BaseCommand):
    help = 'Create core departments for the system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating core departments...'))
        create_core_departments()
        self.stdout.write(self.style.SUCCESS('Core departments created successfully.'))
