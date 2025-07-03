"""
إشارات نظام التركيبات الجديد
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
import logging

from .models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationTechnician,
    InstallationAlert,
    DailyInstallationReport
)
from .services.alert_system import AlertSystem
from .services.calendar_service import CalendarService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=InstallationNew)
def installation_created_or_updated(sender, instance, created, **kwargs):
    """معالجة إنشاء أو تحديث التركيب"""
    
    try:
        if created:
            logger.info(f"تم إنشاء تركيب جديد: {instance.id} للعميل {instance.customer_name}")
            
            # فحص إنذارات السعة اليومية
            if instance.scheduled_date:
                AlertSystem.check_daily_capacity_alerts(instance.scheduled_date)
            
            # فحص إنذارات الفنيين
            if instance.team:
                AlertSystem.check_technician_capacity_alerts(instance.team, instance.scheduled_date)
            
            # إنشاء إنذار للتركيبات العاجلة
            if instance.priority == 'urgent':
                InstallationAlert.objects.create(
                    installation=instance,
                    alert_type='urgent_installation',
                    severity='high',
                    title=f'تركيب عاجل جديد #{instance.id}',
                    message=f'تم إنشاء تركيب عاجل للعميل {instance.customer_name}. يتطلب اهتماماً فورياً.'
                )
        
        else:
            logger.info(f"تم تحديث التركيب: {instance.id}")
            
            # فحص تغيير الحالة
            if hasattr(instance, '_original_status'):
                old_status = instance._original_status
                new_status = instance.status
                
                if old_status != new_status:
                    handle_status_change(instance, old_status, new_status)
            
            # فحص تغيير التاريخ
            if hasattr(instance, '_original_date'):
                old_date = instance._original_date
                new_date = instance.scheduled_date
                
                if old_date != new_date:
                    handle_date_change(instance, old_date, new_date)
        
        # تنظيف ذاكرة التخزين المؤقت
        clear_related_cache(instance)
        
    except Exception as e:
        logger.error(f"خطأ في معالجة إشارة التركيب {instance.id}: {e}")


@receiver(pre_save, sender=InstallationNew)
def installation_pre_save(sender, instance, **kwargs):
    """معالجة ما قبل حفظ التركيب"""
    
    try:
        # حفظ القيم الأصلية للمقارنة
        if instance.pk:
            try:
                original = InstallationNew.objects.get(pk=instance.pk)
                instance._original_status = original.status
                instance._original_date = original.scheduled_date
                instance._original_team = original.team
            except InstallationNew.DoesNotExist:
                pass
        
        # تحديث تاريخ التعديل
        instance.updated_at = timezone.now()
        
        # حساب مدة التركيب إذا كانت متاحة
        if instance.actual_start_date and instance.actual_end_date:
            duration = instance.actual_end_date - instance.actual_start_date
            instance.duration_hours = duration.total_seconds() / 3600
        
    except Exception as e:
        logger.error(f"خطأ في معالجة ما قبل حفظ التركيب: {e}")


@receiver(post_delete, sender=InstallationNew)
def installation_deleted(sender, instance, **kwargs):
    """معالجة حذف التركيب"""
    
    try:
        logger.info(f"تم حذف التركيب: {instance.id}")
        
        # حذف الإنذارات المرتبطة
        InstallationAlert.objects.filter(installation=instance).delete()
        
        # تنظيف ذاكرة التخزين المؤقت
        clear_related_cache(instance)
        
    except Exception as e:
        logger.error(f"خطأ في معالجة حذف التركيب {instance.id}: {e}")


@receiver(post_save, sender=InstallationTeamNew)
def team_updated(sender, instance, created, **kwargs):
    """معالجة تحديث الفريق"""
    
    try:
        if created:
            logger.info(f"تم إنشاء فريق جديد: {instance.name}")
        else:
            logger.info(f"تم تحديث الفريق: {instance.name}")
        
        # تنظيف ذاكرة التخزين المؤقت للفرق
        cache.delete('teams_list')
        cache.delete('active_teams')
        cache.delete_many([
            f'team_stats_{instance.id}',
            f'team_schedule_{instance.id}',
            f'team_capacity_{instance.id}'
        ])
        
    except Exception as e:
        logger.error(f"خطأ في معالجة تحديث الفريق {instance.id}: {e}")


@receiver(post_save, sender=InstallationTechnician)
def technician_updated(sender, instance, created, **kwargs):
    """معالجة تحديث الفني"""
    
    try:
        if created:
            logger.info(f"تم إنشاء فني جديد: {instance.user.get_full_name()}")
        else:
            logger.info(f"تم تحديث الفني: {instance.user.get_full_name()}")
        
        # تنظيف ذاكرة التخزين المؤقت للفنيين
        cache.delete('technicians_list')
        cache.delete('active_technicians')
        cache.delete_many([
            f'technician_stats_{instance.id}',
            f'technician_performance_{instance.id}',
            f'technician_schedule_{instance.id}'
        ])
        
    except Exception as e:
        logger.error(f"خطأ في معالجة تحديث الفني {instance.id}: {e}")


@receiver(post_save, sender=InstallationAlert)
def alert_created(sender, instance, created, **kwargs):
    """معالجة إنشاء إنذار جديد"""
    
    try:
        if created:
            logger.info(f"تم إنشاء إنذار جديد: {instance.title}")
            
            # إرسال إشعارات فورية للإنذارات الحرجة
            if instance.severity == 'critical':
                send_immediate_alert_notification(instance)
            
            # تنظيف ذاكرة التخزين المؤقت للإنذارات
            cache.delete('active_alerts')
            cache.delete('critical_alerts')
        
    except Exception as e:
        logger.error(f"خطأ في معالجة إنشاء الإنذار {instance.id}: {e}")


def handle_status_change(instance, old_status, new_status):
    """معالجة تغيير حالة التركيب"""
    
    try:
        logger.info(f"تغيير حالة التركيب {instance.id} من {old_status} إلى {new_status}")
        
        # إنشاء إنذارات حسب تغيير الحالة
        if new_status == 'completed':
            # إنذار إكمال التركيب
            InstallationAlert.objects.create(
                installation=instance,
                alert_type='installation_completed',
                severity='low',
                title=f'تم إكمال التركيب #{instance.id}',
                message=f'تم إكمال تركيب العميل {instance.customer_name} بنجاح.'
            )
            
            # تحديث إحصائيات الفريق
            if instance.team:
                update_team_statistics(instance.team)
        
        elif new_status == 'cancelled':
            # إنذار إلغاء التركيب
            InstallationAlert.objects.create(
                installation=instance,
                alert_type='installation_cancelled',
                severity='medium',
                title=f'تم إلغاء التركيب #{instance.id}',
                message=f'تم إلغاء تركيب العميل {instance.customer_name}.'
            )
        
        elif new_status == 'in_progress':
            # تحديث وقت البدء الفعلي
            if not instance.actual_start_date:
                instance.actual_start_date = timezone.now()
                instance.save(update_fields=['actual_start_date'])
        
    except Exception as e:
        logger.error(f"خطأ في معالجة تغيير الحالة: {e}")


def handle_date_change(instance, old_date, new_date):
    """معالجة تغيير تاريخ التركيب"""
    
    try:
        logger.info(f"تغيير تاريخ التركيب {instance.id} من {old_date} إلى {new_date}")
        
        # فحص إنذارات السعة للتاريخ الجديد
        if new_date:
            AlertSystem.check_daily_capacity_alerts(new_date)
        
        # إنشاء إنذار إعادة الجدولة
        InstallationAlert.objects.create(
            installation=instance,
            alert_type='installation_rescheduled',
            severity='medium',
            title=f'تم إعادة جدولة التركيب #{instance.id}',
            message=f'تم تغيير تاريخ تركيب العميل {instance.customer_name} من {old_date} إلى {new_date}.'
        )
        
    except Exception as e:
        logger.error(f"خطأ في معالجة تغيير التاريخ: {e}")


def send_immediate_alert_notification(alert):
    """إرسال إشعار فوري للإنذار الحرج"""
    
    try:
        # يمكن إضافة منطق إرسال SMS أو إشعارات فورية هنا
        logger.warning(f"إنذار حرج: {alert.title} - {alert.message}")
        
        # إرسال إشعار للمديرين عبر البريد الإلكتروني
        from django.core.mail import send_mail
        from django.conf import settings
        from accounts.models import User
        
        managers = User.objects.filter(
            is_staff=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        if managers.exists():
            recipient_list = [user.email for user in managers]
            
            send_mail(
                subject=f"إنذار حرج: {alert.title}",
                message=f"""
                تم إنشاء إنذار حرج في نظام التركيبات:
                
                العنوان: {alert.title}
                الرسالة: {alert.message}
                الوقت: {alert.created_at.strftime('%Y-%m-%d %H:%M')}
                
                يرجى مراجعة النظام فوراً.
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=True
            )
        
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار الإنذار الحرج: {e}")


def update_team_statistics(team):
    """تحديث إحصائيات الفريق"""
    
    try:
        # تنظيف ذاكرة التخزين المؤقت للفريق
        cache.delete_many([
            f'team_stats_{team.id}',
            f'team_performance_{team.id}',
            f'team_monthly_stats_{team.id}'
        ])
        
        logger.info(f"تم تحديث إحصائيات الفريق: {team.name}")
        
    except Exception as e:
        logger.error(f"خطأ في تحديث إحصائيات الفريق: {e}")


def clear_related_cache(instance):
    """تنظيف ذاكرة التخزين المؤقت المرتبطة"""
    
    try:
        # تنظيف ذاكرة التخزين المؤقت العامة
        cache.delete_many([
            'dashboard_analytics',
            'installations_list',
            'calendar_events',
            'daily_stats',
            'branch_comparison',
            'factory_stats'
        ])
        
        # تنظيف ذاكرة التخزين المؤقت للتاريخ المحدد
        if instance.scheduled_date:
            cache.delete(f'daily_schedule_{instance.scheduled_date}')
            cache.delete(f'daily_stats_{instance.scheduled_date}')
        
        # تنظيف ذاكرة التخزين المؤقت للفرع
        if instance.branch_name:
            cache.delete(f'branch_stats_{instance.branch_name}')
        
        # تنظيف ذاكرة التخزين المؤقت للفريق
        if instance.team:
            cache.delete(f'team_schedule_{instance.team.id}')
        
    except Exception as e:
        logger.error(f"خطأ في تنظيف ذاكرة التخزين المؤقت: {e}")


# إشارات إضافية للتحسين

@receiver(post_save, sender=DailyInstallationReport)
def daily_report_created(sender, instance, created, **kwargs):
    """معالجة إنشاء التقرير اليومي"""
    
    if created:
        logger.info(f"تم إنشاء التقرير اليومي لتاريخ {instance.report_date}")
        
        # تنظيف ذاكرة التخزين المؤقت للتقارير
        cache.delete('recent_reports')
        cache.delete(f'daily_report_{instance.report_date}')


# تسجيل الإشارات
def register_signals():
    """تسجيل جميع الإشارات"""
    
    logger.info("تم تسجيل إشارات نظام التركيبات الجديد")


# استدعاء تسجيل الإشارات عند استيراد الملف
register_signals()
