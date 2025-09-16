"""
أمر Django لتشغيل النسخ الاحتياطية المجدولة يدوياً
يمكن استخدامه في بيئة الإنتاج حيث لا يعمل المجدول التلقائي
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from odoo_db_manager.models import BackupSchedule
from odoo_db_manager.services.scheduled_backup_service import create_backup_job
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'تشغيل النسخ الاحتياطية المجدولة المستحقة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='تشغيل جميع النسخ الاحتياطية النشطة بغض النظر عن الجدولة',
        )
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='تشغيل جدولة محددة فقط',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض النسخ الاحتياطية المستحقة دون تشغيلها',
        )

    def handle(self, *args, **options):
        force = options['force']
        schedule_id = options['schedule_id']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('🔄 بدء فحص النسخ الاحتياطية المجدولة...')
        )
        
        # الحصول على الجدولات
        if schedule_id:
            try:
                schedules = [BackupSchedule.objects.get(id=schedule_id, is_active=True)]
                self.stdout.write(f'📋 تشغيل الجدولة المحددة: {schedule_id}')
            except BackupSchedule.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ الجدولة {schedule_id} غير موجودة أو غير نشطة')
                )
                return
        else:
            schedules = BackupSchedule.objects.filter(is_active=True)
            self.stdout.write(f'📊 تم العثور على {schedules.count()} جدولة نشطة')
        
        if not schedules:
            self.stdout.write(
                self.style.WARNING('⚠️ لا توجد جدولات نسخ احتياطية نشطة')
            )
            return
        
        now = timezone.now()
        executed_count = 0
        skipped_count = 0
        error_count = 0
        
        for schedule in schedules:
            try:
                # التحقق من استحقاق التشغيل
                should_run = force or self._should_run_now(schedule, now)
                
                self.stdout.write(f'\n📋 جدولة: {schedule.name} (ID: {schedule.id})')
                self.stdout.write(f'   قاعدة البيانات: {schedule.database.name}')
                self.stdout.write(f'   التكرار: {schedule.get_frequency_display()}')
                self.stdout.write(f'   آخر تشغيل: {schedule.last_run or "لم يتم التشغيل بعد"}')
                self.stdout.write(f'   التشغيل القادم: {schedule.next_run or "غير محدد"}')
                
                if should_run:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING('   🔍 سيتم تشغيل هذه الجدولة (وضع المعاينة)')
                        )
                        executed_count += 1
                    else:
                        self.stdout.write(
                            self.style.SUCCESS('   ▶️ تشغيل النسخة الاحتياطية...')
                        )
                        
                        # تشغيل النسخة الاحتياطية
                        backup = create_backup_job(schedule.id)
                        
                        if backup:
                            self.stdout.write(
                                self.style.SUCCESS(f'   ✅ تم إنشاء النسخة الاحتياطية: {backup.name}')
                            )
                            executed_count += 1
                        else:
                            self.stdout.write(
                                self.style.ERROR('   ❌ فشل إنشاء النسخة الاحتياطية')
                            )
                            error_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING('   ⏭️ لا تحتاج للتشغيل الآن')
                    )
                    skipped_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ خطأ في الجدولة {schedule.id}: {str(e)}')
                )
                error_count += 1
                logger.error(f'خطأ في تشغيل الجدولة {schedule.id}: {str(e)}')
        
        # عرض النتائج النهائية
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'📊 ملخص العملية:')
        )
        self.stdout.write(f'   إجمالي الجدولات: {len(schedules)}')
        self.stdout.write(f'   تم التشغيل: {executed_count}')
        self.stdout.write(f'   تم التجاهل: {skipped_count}')
        self.stdout.write(f'   الأخطاء: {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 هذه كانت معاينة فقط. لتشغيل النسخ الاحتياطية، قم بإزالة --dry-run')
            )
        else:
            if executed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'\n✅ تم تشغيل {executed_count} نسخة احتياطية بنجاح!')
                )
            
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f'\n❌ فشل تشغيل {error_count} نسخة احتياطية')
                )

    def _should_run_now(self, schedule, now):
        """التحقق من استحقاق الجدولة للتشغيل"""
        # إذا لم يتم تحديد موعد التشغيل القادم، احسبه
        if not schedule.next_run:
            schedule.calculate_next_run()
            schedule.save(update_fields=['next_run'])
        
        # إذا لم يتم التشغيل من قبل، شغله الآن
        if not schedule.last_run:
            return True
        
        # إذا حان موعد التشغيل القادم
        if schedule.next_run and now >= schedule.next_run:
            return True
        
        # إذا تأخر التشغيل كثيراً (أكثر من ضعف المدة المحددة)
        if schedule.last_run:
            time_since_last = now - schedule.last_run
            
            if schedule.frequency == 'hourly' and time_since_last > timedelta(hours=2):
                return True
            elif schedule.frequency == 'daily' and time_since_last > timedelta(days=2):
                return True
            elif schedule.frequency == 'weekly' and time_since_last > timedelta(weeks=2):
                return True
            elif schedule.frequency == 'monthly' and time_since_last > timedelta(days=60):
                return True
        
        return False
