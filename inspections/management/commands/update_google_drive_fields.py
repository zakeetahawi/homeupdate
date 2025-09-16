"""
أمر Django لتحديث حقول Google Drive للمعاينات الموجودة
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from inspections.models import Inspection
import os


class Command(BaseCommand):
    help = 'تحديث حقول Google Drive للمعاينات الموجودة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض التغييرات دون تطبيقها',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='تحديث جميع المعاينات حتى لو كانت محدثة',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS('🚀 بدء تحديث حقول Google Drive للمعاينات...')
        )
        
        # الحصول على المعاينات التي تحتوي على ملفات
        if force:
            inspections = Inspection.objects.filter(
                inspection_file__isnull=False
            ).exclude(inspection_file='')
        else:
            inspections = Inspection.objects.filter(
                inspection_file__isnull=False,
                google_drive_file_name__isnull=True
            ).exclude(inspection_file='')
        
        total_count = inspections.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('⚠️ لا توجد معاينات تحتاج إلى تحديث.')
            )
            return
        
        self.stdout.write(
            f'📊 تم العثور على {total_count} معاينة تحتاج إلى تحديث.'
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 وضع المعاينة - لن يتم تطبيق التغييرات.')
            )
        
        updated_count = 0
        error_count = 0
        
        for inspection in inspections:
            try:
                # توليد اسم الملف الجديد
                old_filename = inspection.google_drive_file_name
                new_filename = inspection.generate_drive_filename()
                
                # التحقق من وجود الملف
                file_exists = False
                if inspection.inspection_file:
                    file_path = inspection.inspection_file.path
                    file_exists = os.path.exists(file_path)
                
                # عرض معلومات المعاينة
                self.stdout.write(f'\n📋 معاينة #{inspection.id}:')
                self.stdout.write(f'   العميل: {inspection.customer.name if inspection.customer else "غير محدد"}')
                self.stdout.write(f'   الفرع: {inspection.branch.name if inspection.branch else "غير محدد"}')
                self.stdout.write(f'   التاريخ: {inspection.scheduled_date}')
                self.stdout.write(f'   الملف الحالي: {inspection.inspection_file.name if inspection.inspection_file else "لا يوجد"}')
                self.stdout.write(f'   الملف موجود: {"✅" if file_exists else "❌"}')
                self.stdout.write(f'   الاسم القديم: {old_filename or "لا يوجد"}')
                self.stdout.write(f'   الاسم الجديد: {new_filename}')
                
                if not dry_run:
                    # تحديث البيانات
                    inspection.google_drive_file_name = new_filename
                    inspection.is_uploaded_to_drive = False  # سيتم تحديثها عند الرفع
                    inspection.save(update_fields=[
                        'google_drive_file_name', 
                        'is_uploaded_to_drive'
                    ])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'   ✅ تم تحديث المعاينة #{inspection.id}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'   🔍 سيتم تحديث المعاينة #{inspection.id}')
                    )
                
                updated_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'   ❌ خطأ في المعاينة #{inspection.id}: {str(e)}')
                )
        
        # عرض النتائج النهائية
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'📊 ملخص العملية:')
        )
        self.stdout.write(f'   إجمالي المعاينات: {total_count}')
        self.stdout.write(f'   تم التحديث: {updated_count}')
        self.stdout.write(f'   الأخطاء: {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 هذه كانت معاينة فقط. لتطبيق التغييرات، قم بتشغيل الأمر بدون --dry-run')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ تم الانتهاء من تحديث حقول Google Drive بنجاح!')
            )
            
            if updated_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'💡 يمكنك الآن رفع الملفات إلى Google Drive من واجهة المعاينات.'
                    )
                )

    def _format_filename(self, filename):
        """تنسيق اسم الملف للعرض"""
        if not filename:
            return "لا يوجد"
        
        if len(filename) > 50:
            return filename[:47] + "..."
        
        return filename
