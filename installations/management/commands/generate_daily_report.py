"""
أمر Django لإنشاء التقارير اليومية
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from installations.models_new import DailyInstallationReport, InstallationNew
from installations.services.analytics_engine import AnalyticsEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إنشاء التقارير اليومية للتركيبات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='التاريخ المحدد للتقرير (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--send-email',
            action='store_true',
            help='إرسال التقرير بالبريد الإلكتروني',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='إعادة إنشاء التقرير حتى لو كان موجوداً',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('بدء إنشاء التقرير اليومي...')
        )

        try:
            # تحديد التاريخ
            if options['date']:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            else:
                target_date = timezone.now().date() - timedelta(days=1)  # أمس

            self.stdout.write(f'إنشاء تقرير لتاريخ: {target_date}')

            # التحقق من وجود التقرير
            existing_report = DailyInstallationReport.objects.filter(
                report_date=target_date
            ).first()

            if existing_report and not options['force']:
                self.stdout.write(
                    self.style.WARNING(f'التقرير موجود مسبقاً لتاريخ {target_date}')
                )
                self.stdout.write('استخدم --force لإعادة الإنشاء')
                return

            # حذف التقرير الموجود إذا كان مطلوباً
            if existing_report and options['force']:
                existing_report.delete()
                self.stdout.write('تم حذف التقرير الموجود')

            # إنشاء التقرير
            report = DailyInstallationReport.generate_report(target_date)

            # عرض ملخص التقرير
            self.display_report_summary(report)

            # إرسال التقرير بالبريد الإلكتروني
            if options['send_email']:
                self.send_report_email(report)

            self.stdout.write(
                self.style.SUCCESS(f'تم إنشاء التقرير بنجاح: {report.id}')
            )

        except Exception as e:
            error_msg = f'خطأ في إنشاء التقرير اليومي: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise

    def display_report_summary(self, report):
        """عرض ملخص التقرير"""
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'تقرير يوم {report.report_date}')
        self.stdout.write('='*50)
        
        self.stdout.write(f'إجمالي التركيبات: {report.total_installations}')
        self.stdout.write(f'التركيبات المكتملة: {report.completed_installations}')
        self.stdout.write(f'التركيبات المجدولة: {report.scheduled_installations}')
        self.stdout.write(f'التركيبات الملغية: {report.cancelled_installations}')
        self.stdout.write(f'إجمالي الشبابيك: {report.total_windows}')
        self.stdout.write(f'معدل الإكمال: {report.completion_rate:.1f}%')
        self.stdout.write(f'الفرق النشطة: {report.active_teams}')
        
        if report.average_quality:
            self.stdout.write(f'متوسط الجودة: {report.average_quality:.1f}/5')
        
        if report.average_satisfaction:
            self.stdout.write(f'متوسط رضا العملاء: {report.average_satisfaction:.1f}/5')
        
        if report.notes:
            self.stdout.write(f'ملاحظات: {report.notes}')

    def send_report_email(self, report):
        """إرسال التقرير بالبريد الإلكتروني"""
        
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            from accounts.models import User
            
            # الحصول على المديرين
            managers = User.objects.filter(
                is_staff=True,
                is_active=True,
                email__isnull=False
            ).exclude(email='')
            
            if not managers.exists():
                self.stdout.write(
                    self.style.WARNING('لا يوجد مديرين لإرسال التقرير')
                )
                return
            
            # إنشاء محتوى البريد الإلكتروني
            subject = f"التقرير اليومي للتركيبات - {report.report_date.strftime('%Y/%m/%d')}"
            
            message = f"""
التقرير اليومي لنظام التركيبات
التاريخ: {report.report_date.strftime('%Y/%m/%d')}

ملخص اليوم:
- إجمالي التركيبات: {report.total_installations}
- التركيبات المكتملة: {report.completed_installations}
- التركيبات المجدولة: {report.scheduled_installations}
- التركيبات الملغية: {report.cancelled_installations}
- إجمالي الشبابيك: {report.total_windows}
- معدل الإكمال: {report.completion_rate:.1f}%

الفرق النشطة: {report.active_teams}
"""
            
            if report.average_quality:
                message += f"متوسط الجودة: {report.average_quality:.1f}/5\n"
            
            if report.average_satisfaction:
                message += f"متوسط رضا العملاء: {report.average_satisfaction:.1f}/5\n"
            
            if report.notes:
                message += f"\nملاحظات:\n{report.notes}\n"
            
            message += f"""

تم إنشاء هذا التقرير تلقائياً في {report.created_at.strftime('%Y-%m-%d %H:%M')}

مع تحيات،
نظام إدارة التركيبات
"""
            
            # إرسال البريد الإلكتروني
            recipient_list = [user.email for user in managers]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=recipient_list,
                fail_silently=False
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'تم إرسال التقرير إلى {len(recipient_list)} مدير')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إرسال التقرير: {str(e)}')
            )


class Command(BaseCommand):
    help = 'إنشاء تقرير شامل للتركيبات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['daily', 'weekly', 'monthly'],
            default='daily',
            help='نوع التقرير (daily/weekly/monthly)',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='التاريخ المرجعي (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--branch',
            type=str,
            help='فلترة حسب الفرع',
        )
        parser.add_argument(
            '--export',
            type=str,
            choices=['pdf', 'excel', 'csv'],
            help='تصدير التقرير بالتنسيق المحدد',
        )

    def handle(self, *args, **options):
        report_type = options['type']
        
        self.stdout.write(
            self.style.SUCCESS(f'إنشاء تقرير {report_type}...')
        )

        try:
            # تحديد التاريخ
            if options['date']:
                reference_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            else:
                reference_date = timezone.now().date()

            # إنشاء التقرير حسب النوع
            if report_type == 'daily':
                report_data = self.generate_daily_report(reference_date, options['branch'])
            elif report_type == 'weekly':
                report_data = self.generate_weekly_report(reference_date, options['branch'])
            elif report_type == 'monthly':
                report_data = self.generate_monthly_report(reference_date, options['branch'])

            # عرض التقرير
            self.display_report(report_data, report_type)

            # تصدير التقرير إذا كان مطلوباً
            if options['export']:
                self.export_report(report_data, options['export'], report_type)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إنشاء التقرير: {str(e)}')
            )

    def generate_daily_report(self, date, branch=None):
        """إنشاء تقرير يومي"""
        
        installations = InstallationNew.objects.filter(scheduled_date=date)
        
        if branch:
            installations = installations.filter(branch_name=branch)

        return {
            'type': 'daily',
            'date': date,
            'branch': branch,
            'total_installations': installations.count(),
            'completed': installations.filter(status='completed').count(),
            'scheduled': installations.filter(status='scheduled').count(),
            'pending': installations.filter(status='pending').count(),
            'cancelled': installations.filter(status='cancelled').count(),
            'total_windows': sum(inst.windows_count for inst in installations),
            'installations': list(installations.values(
                'id', 'customer_name', 'customer_phone', 'windows_count',
                'status', 'priority', 'team__name'
            ))
        }

    def generate_weekly_report(self, end_date, branch=None):
        """إنشاء تقرير أسبوعي"""
        
        start_date = end_date - timedelta(days=6)
        installations = InstallationNew.objects.filter(
            scheduled_date__range=[start_date, end_date]
        )
        
        if branch:
            installations = installations.filter(branch_name=branch)

        return {
            'type': 'weekly',
            'start_date': start_date,
            'end_date': end_date,
            'branch': branch,
            'total_installations': installations.count(),
            'completed': installations.filter(status='completed').count(),
            'total_windows': sum(inst.windows_count for inst in installations),
            'daily_breakdown': self._get_daily_breakdown(installations, start_date, end_date)
        }

    def generate_monthly_report(self, date, branch=None):
        """إنشاء تقرير شهري"""
        
        start_date = date.replace(day=1)
        if date.month == 12:
            end_date = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = date.replace(month=date.month + 1, day=1) - timedelta(days=1)

        return AnalyticsEngine.get_monthly_report(date.year, date.month, branch)

    def _get_daily_breakdown(self, installations, start_date, end_date):
        """تفصيل يومي للتركيبات"""
        
        breakdown = []
        current_date = start_date
        
        while current_date <= end_date:
            daily_installations = installations.filter(scheduled_date=current_date)
            breakdown.append({
                'date': current_date,
                'count': daily_installations.count(),
                'windows': sum(inst.windows_count for inst in daily_installations),
                'completed': daily_installations.filter(status='completed').count()
            })
            current_date += timedelta(days=1)
        
        return breakdown

    def display_report(self, report_data, report_type):
        """عرض التقرير"""
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'تقرير {report_type.upper()}')
        self.stdout.write('='*60)
        
        if report_type == 'daily':
            self.stdout.write(f"التاريخ: {report_data['date']}")
        elif report_type == 'weekly':
            self.stdout.write(f"الفترة: {report_data['start_date']} - {report_data['end_date']}")
        elif report_type == 'monthly':
            period = report_data.get('period', {})
            self.stdout.write(f"الشهر: {period.get('month_name', '')} {period.get('year', '')}")
        
        if report_data.get('branch'):
            self.stdout.write(f"الفرع: {report_data['branch']}")
        
        self.stdout.write(f"إجمالي التركيبات: {report_data['total_installations']}")
        self.stdout.write(f"التركيبات المكتملة: {report_data.get('completed', 0)}")
        self.stdout.write(f"إجمالي الشبابيك: {report_data['total_windows']}")
        
        if 'daily_breakdown' in report_data:
            self.stdout.write('\nالتفصيل اليومي:')
            for day in report_data['daily_breakdown']:
                self.stdout.write(
                    f"  {day['date']}: {day['count']} تركيب، {day['windows']} شباك"
                )

    def export_report(self, report_data, format_type, report_type):
        """تصدير التقرير"""
        
        filename = f"{report_type}_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format_type == 'pdf':
            self.stdout.write('تصدير PDF غير متاح حالياً')
        elif format_type == 'excel':
            self.stdout.write('تصدير Excel غير متاح حالياً')
        elif format_type == 'csv':
            self.export_csv(report_data, filename)

    def export_csv(self, report_data, filename):
        """تصدير CSV"""
        
        import csv
        
        filename = f"{filename}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # كتابة الرؤوس
            writer.writerow(['التاريخ', 'العدد', 'الشبابيك', 'المكتمل'])
            
            # كتابة البيانات
            if 'daily_breakdown' in report_data:
                for day in report_data['daily_breakdown']:
                    writer.writerow([
                        day['date'],
                        day['count'],
                        day['windows'],
                        day['completed']
                    ])
        
        self.stdout.write(f'تم تصدير التقرير: {filename}')
