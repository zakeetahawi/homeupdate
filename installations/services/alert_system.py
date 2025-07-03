"""
نظام الإنذارات للتركيبات
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import logging

from ..models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationAlert,
    InstallationTechnician
)
from accounts.models import User

logger = logging.getLogger(__name__)


class AlertSystem:
    """نظام الإنذارات الذكي للتركيبات"""
    
    # حدود الإنذارات
    MAX_DAILY_INSTALLATIONS = 13
    WARNING_DAILY_INSTALLATIONS = 11
    MAX_TECHNICIAN_WINDOWS = 20
    WARNING_TECHNICIAN_WINDOWS = 18
    OVERDUE_DAYS_THRESHOLD = 1
    PAYMENT_OVERDUE_DAYS = 30
    
    @classmethod
    def check_all_alerts(cls, date: date = None) -> List[Dict]:
        """فحص جميع أنواع الإنذارات"""
        
        if not date:
            date = timezone.now().date()
        
        alerts = []
        
        # فحص إنذارات السعة اليومية
        alerts.extend(cls.check_daily_capacity_alerts(date))
        
        # فحص إنذارات الفنيين
        alerts.extend(cls.check_technician_capacity_alerts(date))
        
        # فحص إنذارات التأخير
        alerts.extend(cls.check_overdue_alerts(date))
        
        # فحص إنذارات السداد
        alerts.extend(cls.check_payment_alerts())
        
        # فحص إنذارات الجودة
        alerts.extend(cls.check_quality_alerts())
        
        # فحص إنذارات تعارض الجدولة
        alerts.extend(cls.check_scheduling_conflicts(date))
        
        # حفظ الإنذارات في قاعدة البيانات
        cls.save_alerts(alerts)
        
        return alerts
    
    @classmethod
    def check_daily_capacity_alerts(cls, date: date) -> List[Dict]:
        """فحص إنذارات السعة اليومية"""
        
        alerts = []
        
        # عدد التركيبات المجدولة في اليوم
        daily_installations = InstallationNew.objects.filter(
            scheduled_date=date,
            status__in=['scheduled', 'in_progress']
        )
        
        total_count = daily_installations.count()
        
        if total_count >= cls.MAX_DAILY_INSTALLATIONS:
            # إنذار حرج - تجاوز الحد الأقصى
            alerts.append({
                'type': 'capacity_exceeded',
                'severity': 'critical',
                'title': f'تجاوز الحد الأقصى للتركيبات اليومية',
                'message': f'تم جدولة {total_count} تركيب في {date} (الحد الأقصى {cls.MAX_DAILY_INSTALLATIONS})',
                'date': date,
                'count': total_count,
                'installations': list(daily_installations.values('id', 'customer_name', 'team__name')),
                'action_required': True,
                'suggested_actions': [
                    'إعادة جدولة بعض التركيبات لأيام أخرى',
                    'تخصيص فرق إضافية',
                    'تأجيل التركيبات غير العاجلة'
                ]
            })
            
        elif total_count >= cls.WARNING_DAILY_INSTALLATIONS:
            # تحذير - اقتراب من الحد الأقصى
            alerts.append({
                'type': 'capacity_warning',
                'severity': 'high',
                'title': f'اقتراب من الحد الأقصى للتركيبات اليومية',
                'message': f'تم جدولة {total_count} تركيب في {date} (الحد الأقصى {cls.MAX_DAILY_INSTALLATIONS})',
                'date': date,
                'count': total_count,
                'remaining_capacity': cls.MAX_DAILY_INSTALLATIONS - total_count,
                'action_required': False,
                'suggested_actions': [
                    'مراجعة إمكانية إعادة توزيع التركيبات',
                    'التأكد من جاهزية الفرق'
                ]
            })
        
        # فحص حسب الفرع
        branches = daily_installations.values('branch_name').annotate(
            count=Count('id')
        ).filter(count__gte=cls.WARNING_DAILY_INSTALLATIONS)
        
        for branch in branches:
            if branch['count'] >= cls.MAX_DAILY_INSTALLATIONS:
                alerts.append({
                    'type': 'branch_capacity_exceeded',
                    'severity': 'critical',
                    'title': f'تجاوز السعة في فرع {branch["branch_name"]}',
                    'message': f'فرع {branch["branch_name"]} لديه {branch["count"]} تركيب مجدول في {date}',
                    'date': date,
                    'branch': branch['branch_name'],
                    'count': branch['count'],
                    'action_required': True
                })
        
        return alerts
    
    @classmethod
    def check_technician_capacity_alerts(cls, date: date) -> List[Dict]:
        """فحص إنذارات سعة الفنيين"""
        
        alerts = []
        
        # الحصول على جميع الفنيين النشطين
        technicians = InstallationTechnician.objects.filter(is_active=True)
        
        for technician in technicians:
            daily_windows = technician.get_daily_windows_count(date)
            
            if daily_windows >= cls.MAX_TECHNICIAN_WINDOWS:
                alerts.append({
                    'type': 'technician_overload',
                    'severity': 'critical',
                    'title': f'تحميل زائد على الفني {technician.user.get_full_name()}',
                    'message': f'الفني مكلف بـ {daily_windows} شباك في {date} (الحد الأقصى {cls.MAX_TECHNICIAN_WINDOWS})',
                    'date': date,
                    'technician_id': technician.id,
                    'technician_name': technician.user.get_full_name(),
                    'windows_count': daily_windows,
                    'action_required': True,
                    'suggested_actions': [
                        'إعادة توزيع بعض التركيبات على فنيين آخرين',
                        'تأجيل بعض التركيبات'
                    ]
                })
                
            elif daily_windows >= cls.WARNING_TECHNICIAN_WINDOWS:
                alerts.append({
                    'type': 'technician_warning',
                    'severity': 'medium',
                    'title': f'اقتراب من الحد الأقصى للفني {technician.user.get_full_name()}',
                    'message': f'الفني مكلف بـ {daily_windows} شباك في {date}',
                    'date': date,
                    'technician_id': technician.id,
                    'technician_name': technician.user.get_full_name(),
                    'windows_count': daily_windows,
                    'remaining_capacity': cls.MAX_TECHNICIAN_WINDOWS - daily_windows,
                    'action_required': False
                })
        
        return alerts
    
    @classmethod
    def check_overdue_alerts(cls, current_date: date = None) -> List[Dict]:
        """فحص إنذارات التأخير"""
        
        if not current_date:
            current_date = timezone.now().date()
        
        alerts = []
        
        # التركيبات المتأخرة
        overdue_installations = InstallationNew.objects.filter(
            scheduled_date__lt=current_date - timedelta(days=cls.OVERDUE_DAYS_THRESHOLD),
            status__in=['pending', 'scheduled']
        )
        
        if overdue_installations.exists():
            overdue_count = overdue_installations.count()
            
            alerts.append({
                'type': 'overdue_installations',
                'severity': 'high',
                'title': f'{overdue_count} تركيب متأخر',
                'message': f'يوجد {overdue_count} تركيب متأخر عن موعده المحدد',
                'count': overdue_count,
                'installations': list(overdue_installations.values(
                    'id', 'customer_name', 'scheduled_date', 'priority'
                )),
                'action_required': True,
                'suggested_actions': [
                    'إعادة جدولة التركيبات المتأخرة',
                    'التواصل مع العملاء لتحديد مواعيد جديدة',
                    'مراجعة أسباب التأخير'
                ]
            })
            
            # إنذارات خاصة للتركيبات العاجلة المتأخرة
            urgent_overdue = overdue_installations.filter(priority='urgent')
            if urgent_overdue.exists():
                alerts.append({
                    'type': 'urgent_overdue',
                    'severity': 'critical',
                    'title': f'{urgent_overdue.count()} تركيب عاجل متأخر',
                    'message': f'يوجد {urgent_overdue.count()} تركيب عاجل متأخر يتطلب اهتماماً فورياً',
                    'count': urgent_overdue.count(),
                    'installations': list(urgent_overdue.values(
                        'id', 'customer_name', 'scheduled_date', 'customer_phone'
                    )),
                    'action_required': True,
                    'priority': 'urgent'
                })
        
        return alerts
    
    @classmethod
    def check_payment_alerts(cls) -> List[Dict]:
        """فحص إنذارات السداد"""
        
        alerts = []
        current_date = timezone.now().date()
        
        # الطلبات المتأخرة السداد
        overdue_payments = InstallationNew.objects.filter(
            payment_status='pending',
            order_date__lt=current_date - timedelta(days=cls.PAYMENT_OVERDUE_DAYS)
        )
        
        if overdue_payments.exists():
            total_debt = sum(
                getattr(inst.order, 'remaining_amount', 0) 
                for inst in overdue_payments
            )
            
            alerts.append({
                'type': 'payment_overdue',
                'severity': 'high',
                'title': f'{overdue_payments.count()} طلب متأخر السداد',
                'message': f'يوجد {overdue_payments.count()} طلب متأخر السداد بإجمالي {total_debt:.2f}',
                'count': overdue_payments.count(),
                'total_debt': total_debt,
                'installations': list(overdue_payments.values(
                    'id', 'customer_name', 'customer_phone', 'order_date'
                )),
                'action_required': True,
                'suggested_actions': [
                    'التواصل مع العملاء لتحصيل المستحقات',
                    'مراجعة شروط السداد',
                    'تعليق التركيبات حتى السداد'
                ]
            })
        
        return alerts
    
    @classmethod
    def check_quality_alerts(cls) -> List[Dict]:
        """فحص إنذارات الجودة"""
        
        alerts = []
        
        # التركيبات ذات التقييم المنخفض
        low_quality_installations = InstallationNew.objects.filter(
            status='completed',
            quality_rating__lte=2,
            actual_end_date__gte=timezone.now() - timedelta(days=7)
        )
        
        if low_quality_installations.exists():
            alerts.append({
                'type': 'low_quality',
                'severity': 'medium',
                'title': f'{low_quality_installations.count()} تركيب بجودة منخفضة',
                'message': f'يوجد {low_quality_installations.count()} تركيب مكتمل بتقييم جودة منخفض خلال الأسبوع الماضي',
                'count': low_quality_installations.count(),
                'installations': list(low_quality_installations.values(
                    'id', 'customer_name', 'quality_rating', 'team__name'
                )),
                'action_required': True,
                'suggested_actions': [
                    'مراجعة أداء الفرق',
                    'تدريب إضافي للفنيين',
                    'تحسين إجراءات مراقبة الجودة'
                ]
            })
        
        return alerts
    
    @classmethod
    def check_scheduling_conflicts(cls, date: date) -> List[Dict]:
        """فحص تعارضات الجدولة"""
        
        alerts = []
        
        # البحث عن تعارضات في أوقات الفرق
        teams_with_conflicts = []
        
        teams = InstallationTeamNew.objects.filter(is_active=True)
        for team in teams:
            team_installations = InstallationNew.objects.filter(
                team=team,
                scheduled_date=date,
                status__in=['scheduled', 'in_progress'],
                scheduled_time_start__isnull=False,
                scheduled_time_end__isnull=False
            ).order_by('scheduled_time_start')
            
            # فحص التداخل في الأوقات
            for i in range(len(team_installations) - 1):
                current = team_installations[i]
                next_inst = team_installations[i + 1]
                
                if current.scheduled_time_end > next_inst.scheduled_time_start:
                    teams_with_conflicts.append({
                        'team': team.name,
                        'conflict_installations': [
                            {
                                'id': current.id,
                                'customer': current.customer_name,
                                'time': f"{current.scheduled_time_start} - {current.scheduled_time_end}"
                            },
                            {
                                'id': next_inst.id,
                                'customer': next_inst.customer_name,
                                'time': f"{next_inst.scheduled_time_start} - {next_inst.scheduled_time_end}"
                            }
                        ]
                    })
        
        if teams_with_conflicts:
            alerts.append({
                'type': 'scheduling_conflict',
                'severity': 'high',
                'title': f'تعارض في جدولة {len(teams_with_conflicts)} فريق',
                'message': f'يوجد تعارض في أوقات الجدولة لـ {len(teams_with_conflicts)} فريق في {date}',
                'date': date,
                'conflicts': teams_with_conflicts,
                'action_required': True,
                'suggested_actions': [
                    'إعادة ترتيب أوقات التركيبات',
                    'تخصيص فرق إضافية',
                    'تعديل المدة المقدرة للتركيبات'
                ]
            })
        
        return alerts
    
    @classmethod
    def save_alerts(cls, alerts: List[Dict]) -> None:
        """حفظ الإنذارات في قاعدة البيانات"""
        
        for alert_data in alerts:
            # البحث عن إنذار مشابه موجود
            existing_alert = InstallationAlert.objects.filter(
                alert_type=alert_data['type'],
                is_resolved=False,
                created_at__date=timezone.now().date()
            ).first()
            
            if not existing_alert:
                # إنشاء إنذار جديد
                InstallationAlert.objects.create(
                    installation=None,  # إنذار عام
                    alert_type=alert_data['type'],
                    severity=alert_data['severity'],
                    title=alert_data['title'],
                    message=alert_data['message']
                )
                
                # إرسال إشعار إذا كان الإنذار حرجاً
                if alert_data['severity'] == 'critical':
                    cls.send_critical_alert_notification(alert_data)
    
    @classmethod
    def send_critical_alert_notification(cls, alert_data: Dict) -> None:
        """إرسال إشعار للإنذارات الحرجة"""
        
        try:
            # الحصول على المستخدمين المخولين
            admin_users = User.objects.filter(
                is_staff=True,
                is_active=True,
                email__isnull=False
            ).exclude(email='')
            
            if admin_users.exists():
                subject = f"إنذار حرج: {alert_data['title']}"
                message = f"""
                تم اكتشاف إنذار حرج في نظام التركيبات:
                
                العنوان: {alert_data['title']}
                الرسالة: {alert_data['message']}
                الوقت: {timezone.now().strftime('%Y-%m-%d %H:%M')}
                
                يرجى اتخاذ الإجراء المناسب فوراً.
                """
                
                recipient_list = [user.email for user in admin_users]
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_list,
                    fail_silently=True
                )
                
                logger.info(f"تم إرسال إشعار إنذار حرج: {alert_data['title']}")
                
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار الإنذار: {str(e)}")
    
    @classmethod
    def get_active_alerts(cls, severity: str = None) -> List[Dict]:
        """الحصول على الإنذارات النشطة"""
        
        query = InstallationAlert.objects.filter(is_resolved=False)
        
        if severity:
            query = query.filter(severity=severity)
        
        return list(query.order_by('-created_at').values(
            'id', 'alert_type', 'severity', 'title', 'message', 'created_at'
        ))
    
    @classmethod
    def resolve_alert(cls, alert_id: int, resolved_by: User) -> bool:
        """حل إنذار"""
        
        try:
            alert = InstallationAlert.objects.get(id=alert_id, is_resolved=False)
            alert.is_resolved = True
            alert.resolved_by = resolved_by
            alert.resolved_at = timezone.now()
            alert.save()
            
            logger.info(f"تم حل الإنذار {alert_id} بواسطة {resolved_by.username}")
            return True
            
        except InstallationAlert.DoesNotExist:
            logger.warning(f"الإنذار {alert_id} غير موجود أو تم حله مسبقاً")
            return False
