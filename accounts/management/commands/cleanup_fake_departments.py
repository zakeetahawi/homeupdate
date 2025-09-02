"""
أمر إدارة لحذف الأقسام الوهمية التي لا تحتوي على تطبيقات فعلية
"""
from django.core.management.base import BaseCommand
from accounts.models import Department

class Command(BaseCommand):
    help = 'Clean up fake departments that do not have actual Django apps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # قائمة الأقسام الوهمية التي يجب حذفها
        fake_departments = [
            'google_sync',
            'excel_import_export', 
            'backup',
            'db_manager'
        ]
        
        self.stdout.write("🔍 البحث عن الأقسام الوهمية...")
        
        # البحث عن الأقسام الموجودة
        departments_to_delete = Department.objects.filter(code__in=fake_departments)
        
        if not departments_to_delete.exists():
            self.stdout.write(
                self.style.SUCCESS("✅ لا توجد أقسام وهمية للحذف")
            )
            return
        
        self.stdout.write(f"📋 تم العثور على {departments_to_delete.count()} قسم وهمي:")
        
        for dept in departments_to_delete:
            self.stdout.write(f"  - {dept.name} ({dept.code}) - أساسي: {dept.is_core}")
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("🔍 وضع المعاينة - لن يتم حذف أي شيء")
            )
            return
        
        # طلب التأكيد
        if not options['force']:
            confirm = input("\n❓ هل تريد حذف هذه الأقسام الوهمية؟ (yes/no): ")
            if confirm.lower() not in ['yes', 'y', 'نعم']:
                self.stdout.write("❌ تم إلغاء العملية")
                return
        
        # حذف الأقسام
        deleted_count = 0
        for dept in departments_to_delete:
            dept_name = dept.name
            dept_code = dept.code
            
            try:
                dept.delete()
                deleted_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ تم حذف: {dept_name} ({dept_code})")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ فشل حذف {dept_name}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 تم حذف {deleted_count} قسم وهمي بنجاح!"
            )
        )
        
        # تحديث قسم إدارة البيانات
        try:
            data_management = Department.objects.get(code='data_management')
            data_management.url_name = 'odoo_db_manager:dashboard'
            data_management.save()
            
            self.stdout.write(
                self.style.SUCCESS("✅ تم تحديث رابط قسم إدارة البيانات")
            )
        except Department.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("⚠️ لم يتم العثور على قسم إدارة البيانات")
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                "\n🔄 يُنصح بإعادة تشغيل السيرفر لتطبيق التغييرات"
            )
        )
