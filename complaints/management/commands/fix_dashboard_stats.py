"""
إصلاح إحصائيات داشبورد الشكاوى
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from complaints.models import Complaint
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إصلاح وتحديث إحصائيات داشبورد الشكاوى'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-overdue',
            action='store_true',
            help='إصلاح حالة الشكاوى المتأخرة',
        )
        parser.add_argument(
            '--show-stats',
            action='store_true',
            help='عرض الإحصائيات الحالية',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض التغييرات بدون تطبيقها',
        )

    def handle(self, *args, **options):
        fix_overdue = options['fix_overdue']
        show_stats = options['show_stats']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('🔧 بدء إصلاح إحصائيات داشبورد الشكاوى...')
        )
        
        if show_stats:
            self.show_current_stats()
        
        if fix_overdue:
            self.fix_overdue_complaints(dry_run)
        
        if show_stats:
            self.stdout.write('\n📊 الإحصائيات بعد الإصلاح:')
            self.show_current_stats()
        
        self.stdout.write(
            self.style.SUCCESS('✅ تم الانتهاء من إصلاح الإحصائيات')
        )

    def show_current_stats(self):
        """عرض الإحصائيات الحالية"""
        self.stdout.write('📊 الإحصائيات الحالية:')
        
        # إجمالي الشكاوى
        total = Complaint.objects.count()
        self.stdout.write(f'   📋 إجمالي الشكاوى: {total}')
        
        # إحصائيات حسب الحالة
        for status, label in Complaint.STATUS_CHOICES:
            count = Complaint.objects.filter(status=status).count()
            self.stdout.write(f'   📊 {label}: {count}')
        
        # الشكاوى المتأخرة فعلياً
        now = timezone.now()
        actually_overdue = Complaint.objects.filter(
            deadline__lt=now,
            status__in=['new', 'in_progress', 'overdue']
        ).count()
        self.stdout.write(f'   ⚠️  الشكاوى المتأخرة فعلياً: {actually_overdue}')
        
        # الشكاوى التي تحتاج تحديث حالة
        need_update = Complaint.objects.filter(
            deadline__lt=now,
            status__in=['new', 'in_progress']
        ).count()
        self.stdout.write(f'   🔄 تحتاج تحديث حالة: {need_update}')

    def fix_overdue_complaints(self, dry_run=False):
        """إصلاح حالة الشكاوى المتأخرة"""
        self.stdout.write('🔧 إصلاح حالة الشكاوى المتأخرة...')
        
        now = timezone.now()
        
        # البحث عن الشكاوى المتأخرة التي لم يتم تحديث حالتها
        overdue_complaints = Complaint.objects.filter(
            deadline__lt=now,
            status__in=['new', 'in_progress']
        )
        
        if not overdue_complaints.exists():
            self.stdout.write(
                self.style.SUCCESS('✅ جميع الشكاوى المتأخرة محدثة بالفعل')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'⚠️  تم العثور على {overdue_complaints.count()} شكوى تحتاج تحديث')
        )
        
        # عرض تفاصيل الشكاوى التي ستُحدث
        for complaint in overdue_complaints[:10]:  # أول 10 فقط للعرض
            days_late = (now - complaint.deadline).days
            self.stdout.write(
                f'   📋 {complaint.complaint_number} - متأخرة {days_late} يوم'
            )
        
        if overdue_complaints.count() > 10:
            self.stdout.write(f'   ... و {overdue_complaints.count() - 10} شكوى أخرى')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 تشغيل تجريبي - لن يتم تطبيق التغييرات')
            )
            return
        
        # تحديث حالة الشكاوى المتأخرة
        try:
            updated_count = overdue_complaints.update(status='overdue')
            self.stdout.write(
                self.style.SUCCESS(f'✅ تم تحديث {updated_count} شكوى إلى حالة متأخرة')
            )
            
            # إرسال تنبيهات للشكاوى المحدثة
            self.send_overdue_notifications(overdue_complaints)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في تحديث الشكاوى: {str(e)}')
            )

    def send_overdue_notifications(self, complaints):
        """إرسال تنبيهات للشكاوى المتأخرة"""
        try:
            from complaints.services.notification_service import ComplaintNotificationService
            
            notification_service = ComplaintNotificationService()
            
            for complaint in complaints:
                # إرسال تنبيه للمسؤول الحالي
                if complaint.assigned_to:
                    notification_service._send_notification(
                        complaint=complaint,
                        recipient=complaint.assigned_to,
                        notification_type='overdue_alert',
                        title=f'تنبيه: شكوى متأخرة {complaint.complaint_number}',
                        message=f'الشكوى تجاوزت الموعد النهائي وتحتاج إلى إجراء فوري',
                        send_email=True
                    )
                
                # إرسال تنبيهات للمستخدمين الذين يمكن التصعيد إليهم
                notification_service.notify_overdue_to_escalation_users(complaint)
            
            self.stdout.write(
                self.style.SUCCESS(f'📧 تم إرسال تنبيهات لـ {complaints.count()} شكوى متأخرة')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في إرسال التنبيهات: {str(e)}')
            )

    def validate_stats_consistency(self):
        """التحقق من تناسق الإحصائيات"""
        self.stdout.write('🔍 فحص تناسق الإحصائيات...')
        
        issues = []
        
        # فحص الشكاوى المتأخرة
        now = timezone.now()
        actually_overdue = Complaint.objects.filter(
            deadline__lt=now,
            status__in=['new', 'in_progress', 'overdue']
        ).count()
        
        status_overdue = Complaint.objects.filter(status='overdue').count()
        
        if actually_overdue != status_overdue:
            issues.append(f'تضارب في الشكاوى المتأخرة: فعلياً {actually_overdue} vs حالة {status_overdue}')
        
        # فحص الشكاوى المحلولة بدون تاريخ حل
        resolved_without_date = Complaint.objects.filter(
            status='resolved',
            resolved_at__isnull=True
        ).count()
        
        if resolved_without_date > 0:
            issues.append(f'{resolved_without_date} شكوى محلولة بدون تاريخ حل')
        
        # فحص الشكاوى المغلقة بدون تاريخ إغلاق
        closed_without_date = Complaint.objects.filter(
            status='closed',
            closed_at__isnull=True
        ).count()
        
        if closed_without_date > 0:
            issues.append(f'{closed_without_date} شكوى مغلقة بدون تاريخ إغلاق')
        
        if issues:
            self.stdout.write(
                self.style.WARNING('⚠️  تم العثور على مشاكل في الإحصائيات:')
            )
            for issue in issues:
                self.stdout.write(f'   ❌ {issue}')
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ الإحصائيات متناسقة')
            )
