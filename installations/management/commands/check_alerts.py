"""
أمر إدارة لفحص الإنذارات
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from installations.services.alert_system import AlertSystem

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'فحص وإنشاء إنذارات التركيبات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='التاريخ المراد فحصه (YYYY-MM-DD). افتراضياً: اليوم الحالي'
        )
        
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=7,
            help='عدد الأيام القادمة للفحص (افتراضياً: 7 أيام)'
        )
        
        parser.add_argument(
            '--alert-type',
            type=str,
            choices=[
                'capacity', 'technician', 'overdue', 
                'payment', 'quality', 'scheduling'
            ],
            help='نوع الإنذار المراد فحصه (افتراضياً: جميع الأنواع)'
        )
        
        parser.add_argument(
            '--send-notifications',
            action='store_true',
            help='إرسال إشعارات للإنذارات الحرجة'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل مفصلة'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        
        # تحديد التاريخ
        if options['date']:
            try:
                check_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('تنسيق التاريخ غير صحيح. استخدم YYYY-MM-DD')
                )
                return
        else:
            check_date = timezone.now().date()
        
        self.stdout.write(f"بدء فحص الإنذارات للتاريخ: {check_date}")
        
        total_alerts = 0
        critical_alerts = 0
        
        # فحص الأيام القادمة
        for day_offset in range(options['days_ahead']):
            current_date = check_date + timedelta(days=day_offset)
            
            if options['verbose']:
                self.stdout.write(f"\nفحص التاريخ: {current_date}")
            
            # فحص الإنذارات حسب النوع
            if options['alert_type']:
                alerts = self._check_specific_alert_type(
                    options['alert_type'], current_date
                )
            else:
                alerts = AlertSystem.check_all_alerts(current_date)
            
            # عرض النتائج
            if alerts:
                total_alerts += len(alerts)
                
                for alert in alerts:
                    severity_style = self._get_severity_style(alert['severity'])
                    
                    self.stdout.write(
                        severity_style(
                            f"  [{alert['severity'].upper()}] {alert['title']}"
                        )
                    )
                    
                    if options['verbose']:
                        self.stdout.write(f"    {alert['message']}")
                        
                        if 'suggested_actions' in alert:
                            self.stdout.write("    الإجراءات المقترحة:")
                            for action in alert['suggested_actions']:
                                self.stdout.write(f"      - {action}")
                    
                    if alert['severity'] == 'critical':
                        critical_alerts += 1
            
            elif options['verbose']:
                self.stdout.write("  لا توجد إنذارات")
        
        # ملخص النتائج
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("ملخص فحص الإنذارات:")
        self.stdout.write(f"  إجمالي الإنذارات: {total_alerts}")
        self.stdout.write(f"  الإنذارات الحرجة: {critical_alerts}")
        self.stdout.write(f"  مدة الفحص: {duration:.2f} ثانية")
        
        if critical_alerts > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"تحذير: يوجد {critical_alerts} إنذار حرج يتطلب اهتماماً فورياً!"
                )
            )
        elif total_alerts > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"يوجد {total_alerts} إنذار يتطلب المراجعة"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("لا توجد إنذارات - النظام يعمل بشكل طبيعي")
            )
        
        # إحصائيات إضافية
        if options['verbose']:
            self._show_detailed_statistics()

    def _check_specific_alert_type(self, alert_type: str, date):
        """فحص نوع محدد من الإنذارات"""
        
        if alert_type == 'capacity':
            return AlertSystem.check_daily_capacity_alerts(date)
        elif alert_type == 'technician':
            return AlertSystem.check_technician_capacity_alerts(date)
        elif alert_type == 'overdue':
            return AlertSystem.check_overdue_alerts(date)
        elif alert_type == 'payment':
            return AlertSystem.check_payment_alerts()
        elif alert_type == 'quality':
            return AlertSystem.check_quality_alerts()
        elif alert_type == 'scheduling':
            return AlertSystem.check_scheduling_conflicts(date)
        else:
            return []

    def _get_severity_style(self, severity: str):
        """الحصول على نمط العرض حسب خطورة الإنذار"""
        
        if severity == 'critical':
            return self.style.ERROR
        elif severity == 'high':
            return self.style.WARNING
        elif severity == 'medium':
            return self.style.NOTICE
        else:
            return self.style.SUCCESS

    def _show_detailed_statistics(self):
        """عرض إحصائيات مفصلة"""
        
        from installations.models_new import InstallationNew, InstallationAlert
        
        self.stdout.write("\nإحصائيات مفصلة:")
        
        # إحصائيات التركيبات
        today = timezone.now().date()
        
        total_installations = InstallationNew.objects.count()
        today_installations = InstallationNew.objects.filter(
            scheduled_date=today
        ).count()
        
        pending_installations = InstallationNew.objects.filter(
            status='pending'
        ).count()
        
        overdue_installations = InstallationNew.objects.filter(
            scheduled_date__lt=today,
            status__in=['pending', 'scheduled']
        ).count()
        
        self.stdout.write(f"  إجمالي التركيبات: {total_installations}")
        self.stdout.write(f"  تركيبات اليوم: {today_installations}")
        self.stdout.write(f"  تركيبات معلقة: {pending_installations}")
        self.stdout.write(f"  تركيبات متأخرة: {overdue_installations}")
        
        # إحصائيات الإنذارات
        active_alerts = InstallationAlert.objects.filter(
            is_resolved=False
        ).count()
        
        critical_active_alerts = InstallationAlert.objects.filter(
            is_resolved=False,
            severity='critical'
        ).count()
        
        self.stdout.write(f"  إنذارات نشطة: {active_alerts}")
        self.stdout.write(f"  إنذارات حرجة نشطة: {critical_active_alerts}")


# مهمة مجدولة لتشغيل فحص الإنذارات تلقائياً
class AlertScheduler:
    """مجدول الإنذارات التلقائي"""
    
    @staticmethod
    def run_hourly_check():
        """فحص كل ساعة للإنذارات الحرجة"""
        
        try:
            today = timezone.now().date()
            alerts = AlertSystem.check_all_alerts(today)
            
            critical_alerts = [
                alert for alert in alerts 
                if alert['severity'] == 'critical'
            ]
            
            if critical_alerts:
                logger.warning(
                    f"تم اكتشاف {len(critical_alerts)} إنذار حرج"
                )
                
                # إرسال إشعارات فورية
                for alert in critical_alerts:
                    AlertSystem.send_critical_alert_notification(alert)
            
            logger.info(f"تم فحص الإنذارات: {len(alerts)} إنذار إجمالي")
            
        except Exception as e:
            logger.error(f"خطأ في فحص الإنذارات التلقائي: {str(e)}")
    
    @staticmethod
    def run_daily_check():
        """فحص يومي شامل"""
        
        try:
            today = timezone.now().date()
            
            # فحص الأسبوع القادم
            all_alerts = []
            for day_offset in range(7):
                check_date = today + timedelta(days=day_offset)
                daily_alerts = AlertSystem.check_all_alerts(check_date)
                all_alerts.extend(daily_alerts)
            
            # تجميع الإحصائيات
            alert_summary = {
                'total': len(all_alerts),
                'critical': len([a for a in all_alerts if a['severity'] == 'critical']),
                'high': len([a for a in all_alerts if a['severity'] == 'high']),
                'medium': len([a for a in all_alerts if a['severity'] == 'medium']),
                'low': len([a for a in all_alerts if a['severity'] == 'low']),
            }
            
            logger.info(
                f"فحص يومي شامل: {alert_summary['total']} إنذار "
                f"({alert_summary['critical']} حرج، {alert_summary['high']} عالي)"
            )
            
            # إرسال تقرير يومي للإدارة
            if alert_summary['total'] > 0:
                AlertScheduler._send_daily_report(alert_summary, all_alerts)
            
        except Exception as e:
            logger.error(f"خطأ في الفحص اليومي الشامل: {str(e)}")
    
    @staticmethod
    def _send_daily_report(summary: dict, alerts: list):
        """إرسال تقرير يومي"""
        
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
                return
            
            subject = f"تقرير إنذارات التركيبات اليومي - {timezone.now().date()}"
            
            message = f"""
            تقرير إنذارات التركيبات اليومي
            التاريخ: {timezone.now().strftime('%Y-%m-%d %H:%M')}
            
            ملخص الإنذارات:
            - إجمالي الإنذارات: {summary['total']}
            - إنذارات حرجة: {summary['critical']}
            - إنذارات عالية: {summary['high']}
            - إنذارات متوسطة: {summary['medium']}
            - إنذارات منخفضة: {summary['low']}
            
            الإنذارات الحرجة:
            """
            
            critical_alerts = [a for a in alerts if a['severity'] == 'critical']
            for alert in critical_alerts[:5]:  # أول 5 إنذارات حرجة
                message += f"\n- {alert['title']}: {alert['message']}"
            
            if len(critical_alerts) > 5:
                message += f"\n... و {len(critical_alerts) - 5} إنذار حرج آخر"
            
            message += "\n\nيرجى مراجعة نظام التركيبات لاتخاذ الإجراءات اللازمة."
            
            recipient_list = [user.email for user in managers]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=True
            )
            
            logger.info("تم إرسال التقرير اليومي للإنذارات")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال التقرير اليومي: {str(e)}")
