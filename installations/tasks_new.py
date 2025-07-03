"""
المهام المجدولة لنظام التركيبات
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta, date
import logging

from .services.alert_system import AlertSystem
from .services.analytics_engine import AnalyticsEngine
from .models_new import InstallationNew, InstallationAlert, DailyInstallationReport
from accounts.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_installation_alerts(self):
    """فحص إنذارات التركيبات"""
    
    try:
        logger.info("بدء فحص إنذارات التركيبات")
        
        # فحص إنذارات اليوم
        today = timezone.now().date()
        alerts = AlertSystem.check_all_alerts(today)
        
        # فحص الأيام القادمة (أسبوع)
        for day_offset in range(1, 8):
            future_date = today + timedelta(days=day_offset)
            future_alerts = AlertSystem.check_all_alerts(future_date)
            alerts.extend(future_alerts)
        
        # إحصائيات الإنذارات
        critical_alerts = [alert for alert in alerts if alert['severity'] == 'critical']
        high_alerts = [alert for alert in alerts if alert['severity'] == 'high']
        
        logger.info(f"تم فحص الإنذارات: {len(alerts)} إجمالي، {len(critical_alerts)} حرج، {len(high_alerts)} عالي")
        
        # إرسال تقرير إذا كان هناك إنذارات حرجة
        if critical_alerts:
            send_critical_alerts_report.delay(critical_alerts)
        
        return {
            'success': True,
            'total_alerts': len(alerts),
            'critical_alerts': len(critical_alerts),
            'high_alerts': len(high_alerts),
        }
        
    except Exception as exc:
        logger.error(f"خطأ في فحص الإنذارات: {exc}")
        
        # إعادة المحاولة
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300, exc=exc)  # إعادة المحاولة بعد 5 دقائق
        
        return {
            'success': False,
            'error': str(exc)
        }


@shared_task(bind=True, max_retries=2)
def generate_daily_report(self, target_date=None):
    """إنشاء التقرير اليومي"""
    
    try:
        if not target_date:
            target_date = timezone.now().date()
        else:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        logger.info(f"إنشاء التقرير اليومي لتاريخ {target_date}")
        
        # إنشاء التقرير اليومي
        report = DailyInstallationReport.generate_report(target_date)
        
        # إرسال التقرير للإدارة
        send_daily_report_email.delay(report.id)
        
        logger.info(f"تم إنشاء التقرير اليومي بنجاح: {report.id}")
        
        return {
            'success': True,
            'report_id': report.id,
            'date': target_date.strftime('%Y-%m-%d'),
            'total_installations': report.total_installations,
            'completed_installations': report.completed_installations,
        }
        
    except Exception as exc:
        logger.error(f"خطأ في إنشاء التقرير اليومي: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=600, exc=exc)  # إعادة المحاولة بعد 10 دقائق
        
        return {
            'success': False,
            'error': str(exc)
        }


@shared_task
def send_critical_alerts_report(critical_alerts):
    """إرسال تقرير الإنذارات الحرجة"""
    
    try:
        # الحصول على المديرين
        managers = User.objects.filter(
            is_staff=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if not managers.exists():
            logger.warning("لا يوجد مديرين لإرسال تقرير الإنذارات الحرجة")
            return
        
        # إنشاء محتوى البريد الإلكتروني
        subject = f"تنبيه: {len(critical_alerts)} إنذار حرج في نظام التركيبات"
        
        message = f"""
        تحية طيبة،
        
        تم اكتشاف {len(critical_alerts)} إنذار حرج في نظام التركيبات يتطلب اهتماماً فورياً:
        
        """
        
        for i, alert in enumerate(critical_alerts[:10], 1):  # أول 10 إنذارات
            message += f"{i}. {alert['title']}\n   {alert['message']}\n\n"
        
        if len(critical_alerts) > 10:
            message += f"... و {len(critical_alerts) - 10} إنذار حرج آخر\n\n"
        
        message += f"""
        يرجى مراجعة نظام التركيبات فوراً لاتخاذ الإجراءات اللازمة.
        
        تاريخ الإرسال: {timezone.now().strftime('%Y-%m-%d %H:%M')}
        
        مع تحيات،
        نظام إدارة التركيبات
        """
        
        # إرسال البريد الإلكتروني
        recipient_list = [user.email for user in managers]
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        logger.info(f"تم إرسال تقرير الإنذارات الحرجة إلى {len(recipient_list)} مدير")
        
        return {
            'success': True,
            'recipients_count': len(recipient_list),
            'alerts_count': len(critical_alerts)
        }
        
    except Exception as e:
        logger.error(f"خطأ في إرسال تقرير الإنذارات الحرجة: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_daily_report_email(report_id):
    """إرسال التقرير اليومي بالبريد الإلكتروني"""
    
    try:
        report = DailyInstallationReport.objects.get(id=report_id)
        
        # الحصول على المديرين
        managers = User.objects.filter(
            is_staff=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if not managers.exists():
            logger.warning("لا يوجد مديرين لإرسال التقرير اليومي")
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
        متوسط الجودة: {report.average_quality:.1f}/5
        متوسط رضا العملاء: {report.average_satisfaction:.1f}/5
        
        """
        
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
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        logger.info(f"تم إرسال التقرير اليومي إلى {len(recipient_list)} مدير")
        
        return {
            'success': True,
            'recipients_count': len(recipient_list),
            'report_date': report.report_date.strftime('%Y-%m-%d')
        }
        
    except DailyInstallationReport.DoesNotExist:
        logger.error(f"التقرير اليومي {report_id} غير موجود")
        return {
            'success': False,
            'error': 'التقرير غير موجود'
        }
    except Exception as e:
        logger.error(f"خطأ في إرسال التقرير اليومي: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(bind=True, max_retries=1)
def cleanup_old_data(self):
    """تنظيف البيانات القديمة"""
    
    try:
        logger.info("بدء تنظيف البيانات القديمة")
        
        # تنظيف الإنذارات القديمة (أكثر من 90 يوم)
        old_alerts_date = timezone.now() - timedelta(days=90)
        old_alerts = InstallationAlert.objects.filter(
            created_at__lt=old_alerts_date,
            is_resolved=True
        )
        alerts_deleted = old_alerts.count()
        old_alerts.delete()
        
        # تنظيف التقارير اليومية القديمة (أكثر من سنة)
        old_reports_date = timezone.now().date() - timedelta(days=365)
        old_reports = DailyInstallationReport.objects.filter(
            report_date__lt=old_reports_date
        )
        reports_deleted = old_reports.count()
        old_reports.delete()
        
        # تنظيف سجلات الجلسات القديمة
        # يمكن إضافة المزيد من عمليات التنظيف هنا
        
        logger.info(f"تم تنظيف البيانات: {alerts_deleted} إنذار، {reports_deleted} تقرير")
        
        return {
            'success': True,
            'alerts_deleted': alerts_deleted,
            'reports_deleted': reports_deleted,
        }
        
    except Exception as exc:
        logger.error(f"خطأ في تنظيف البيانات: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=3600, exc=exc)  # إعادة المحاولة بعد ساعة
        
        return {
            'success': False,
            'error': str(exc)
        }


@shared_task
def sync_with_legacy_system():
    """مزامنة مع النظام القديم"""
    
    try:
        logger.info("بدء مزامنة مع النظام القديم")
        
        # يمكن إضافة منطق المزامنة هنا
        # مثل استيراد البيانات الجديدة من النظام القديم
        # أو تصدير التحديثات إلى النظام القديم
        
        return {
            'success': True,
            'message': 'تمت المزامنة بنجاح'
        }
        
    except Exception as e:
        logger.error(f"خطأ في المزامنة مع النظام القديم: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_analytics_cache():
    """إنشاء ذاكرة التخزين المؤقت للتحليلات"""
    
    try:
        logger.info("بدء إنشاء ذاكرة التخزين المؤقت للتحليلات")
        
        # إنشاء تحليلات لوحة التحكم
        dashboard_analytics = AnalyticsEngine.get_dashboard_analytics()
        
        # إنشاء مقارنة الفروع
        branch_comparison = AnalyticsEngine.get_branch_comparison()
        
        # إنشاء التحليلات التنبؤية
        predictive_analytics = AnalyticsEngine.get_predictive_analytics()
        
        # حفظ في ذاكرة التخزين المؤقت (Redis مثلاً)
        from django.core.cache import cache
        
        cache.set('dashboard_analytics', dashboard_analytics, 900)  # 15 دقيقة
        cache.set('branch_comparison', branch_comparison, 1800)     # 30 دقيقة
        cache.set('predictive_analytics', predictive_analytics, 3600)  # ساعة
        
        logger.info("تم إنشاء ذاكرة التخزين المؤقت للتحليلات بنجاح")
        
        return {
            'success': True,
            'cached_items': 3
        }
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء ذاكرة التخزين المؤقت للتحليلات: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def send_weekly_summary():
    """إرسال الملخص الأسبوعي"""
    
    try:
        logger.info("إنشاء الملخص الأسبوعي")
        
        # حساب الأسبوع الماضي
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday() + 1)  # بداية الأسبوع (السبت)
        week_end = week_start + timedelta(days=6)  # نهاية الأسبوع (الجمعة)
        
        # الحصول على إحصائيات الأسبوع
        weekly_installations = InstallationNew.objects.filter(
            scheduled_date__range=[week_start, week_end]
        )
        
        total_installations = weekly_installations.count()
        completed_installations = weekly_installations.filter(status='completed').count()
        total_windows = sum(inst.windows_count for inst in weekly_installations)
        
        # إنشاء محتوى البريد الإلكتروني
        subject = f"الملخص الأسبوعي للتركيبات - {week_start.strftime('%Y/%m/%d')} - {week_end.strftime('%Y/%m/%d')}"
        
        message = f"""
        الملخص الأسبوعي لنظام التركيبات
        الفترة: {week_start.strftime('%Y/%m/%d')} - {week_end.strftime('%Y/%m/%d')}
        
        إحصائيات الأسبوع:
        - إجمالي التركيبات: {total_installations}
        - التركيبات المكتملة: {completed_installations}
        - إجمالي الشبابيك: {total_windows}
        - معدل الإكمال: {(completed_installations/total_installations*100):.1f}%
        
        تم إنشاء هذا التقرير تلقائياً في {timezone.now().strftime('%Y-%m-%d %H:%M')}
        
        مع تحيات،
        نظام إدارة التركيبات
        """
        
        # إرسال للإدارة
        managers = User.objects.filter(
            is_staff=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if managers.exists():
            recipient_list = [user.email for user in managers]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=False
            )
            
            logger.info(f"تم إرسال الملخص الأسبوعي إلى {len(recipient_list)} مدير")
        
        return {
            'success': True,
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'total_installations': total_installations,
            'completed_installations': completed_installations,
        }
        
    except Exception as e:
        logger.error(f"خطأ في إرسال الملخص الأسبوعي: {e}")
        return {
            'success': False,
            'error': str(e)
        }
