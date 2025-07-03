"""
نظام الجدولة الذكي للتركيبات
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
import logging

from ..models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationSchedule,
    InstallationTechnician,
    InstallationAlert
)

logger = logging.getLogger(__name__)


class SmartSchedulingService:
    """خدمة الجدولة الذكية للتركيبات"""
    
    # إعدادات الجدولة
    WORKING_HOURS_START = time(8, 0)  # 8:00 صباحاً
    WORKING_HOURS_END = time(17, 0)   # 5:00 مساءً
    LUNCH_BREAK_START = time(12, 0)   # 12:00 ظهراً
    LUNCH_BREAK_END = time(13, 0)     # 1:00 ظهراً
    MAX_INSTALLATIONS_PER_DAY = 13    # الحد الأقصى للتركيبات اليومية
    BUFFER_TIME_MINUTES = 30          # وقت إضافي بين التركيبات
    
    @classmethod
    def get_available_time_slots(cls, date: datetime.date, 
                                team: InstallationTeamNew = None) -> List[Dict]:
        """الحصول على الفترات الزمنية المتاحة في يوم معين"""
        
        # التحقق من أن التاريخ ليس في الماضي
        if date < timezone.now().date():
            return []
        
        # التحقق من أن التاريخ ليس يوم جمعة (عطلة)
        if date.weekday() == 4:  # الجمعة
            return []
        
        # الحصول على التركيبات المجدولة في هذا التاريخ
        scheduled_installations = InstallationNew.objects.filter(
            scheduled_date=date,
            status__in=['scheduled', 'in_progress']
        )
        
        if team:
            scheduled_installations = scheduled_installations.filter(team=team)
        
        # التحقق من عدم تجاوز الحد الأقصى
        if scheduled_installations.count() >= cls.MAX_INSTALLATIONS_PER_DAY:
            return []
        
        # إنشاء قائمة الفترات الزمنية المتاحة
        available_slots = []
        current_time = cls.WORKING_HOURS_START
        
        while current_time < cls.WORKING_HOURS_END:
            # تخطي فترة الغداء
            if cls.LUNCH_BREAK_START <= current_time < cls.LUNCH_BREAK_END:
                current_time = cls.LUNCH_BREAK_END
                continue
            
            # حساب نهاية الفترة الزمنية (ساعتين)
            end_time = (datetime.combine(date, current_time) + 
                       timedelta(hours=2)).time()
            
            # التأكد من عدم تجاوز ساعات العمل
            if end_time > cls.WORKING_HOURS_END:
                break
            
            # التحقق من عدم تعارض مع التركيبات الموجودة
            is_available = not scheduled_installations.filter(
                Q(scheduled_time_start__lt=end_time) & 
                Q(scheduled_time_end__gt=current_time)
            ).exists()
            
            if is_available:
                available_slots.append({
                    'start_time': current_time,
                    'end_time': end_time,
                    'duration_hours': 2,
                    'is_prime_time': cls._is_prime_time(current_time),
                })
            
            # الانتقال للفترة التالية
            current_time = (datetime.combine(date, current_time) + 
                           timedelta(hours=1)).time()
        
        return available_slots
    
    @classmethod
    def _is_prime_time(cls, time_slot: time) -> bool:
        """التحقق من كون الوقت في الفترة المفضلة (9-11 صباحاً أو 2-4 عصراً)"""
        return (time(9, 0) <= time_slot <= time(11, 0) or 
                time(14, 0) <= time_slot <= time(16, 0))
    
    @classmethod
    def suggest_optimal_schedule(cls, installation: InstallationNew, 
                               preferred_date: datetime.date = None,
                               max_days_ahead: int = 30) -> List[Dict]:
        """اقتراح أفضل مواعيد للتركيب"""
        
        suggestions = []
        start_date = preferred_date or timezone.now().date() + timedelta(days=1)
        
        for days_offset in range(max_days_ahead):
            check_date = start_date + timedelta(days=days_offset)
            
            # الحصول على الفرق المناسبة
            suitable_teams = cls._get_suitable_teams(installation, check_date)
            
            for team in suitable_teams:
                available_slots = cls.get_available_time_slots(check_date, team)
                
                for slot in available_slots:
                    # حساب نقاط الأولوية
                    priority_score = cls._calculate_priority_score(
                        installation, check_date, slot, team
                    )
                    
                    suggestions.append({
                        'date': check_date,
                        'team': team,
                        'time_slot': slot,
                        'priority_score': priority_score,
                        'estimated_windows_capacity': cls._get_team_windows_capacity(
                            team, check_date
                        ),
                    })
        
        # ترتيب الاقتراحات حسب الأولوية
        suggestions.sort(key=lambda x: x['priority_score'], reverse=True)
        return suggestions[:10]  # أفضل 10 اقتراحات
    
    @classmethod
    def _get_suitable_teams(cls, installation: InstallationNew, 
                          date: datetime.date) -> List[InstallationTeamNew]:
        """الحصول على الفرق المناسبة للتركيب"""
        
        # فلترة الفرق حسب الفرع
        teams = InstallationTeamNew.objects.filter(
            is_active=True,
            branch__name=installation.branch_name
        )
        
        suitable_teams = []
        for team in teams:
            # التحقق من السعة اليومية
            if team.can_schedule_installation(date):
                # التحقق من قدرة الفنيين على التعامل مع عدد الشبابيك
                if cls._team_can_handle_windows(team, installation.windows_count, date):
                    suitable_teams.append(team)
        
        return suitable_teams
    
    @classmethod
    def _team_can_handle_windows(cls, team: InstallationTeamNew, 
                               windows_count: int, date: datetime.date) -> bool:
        """التحقق من قدرة الفريق على التعامل مع عدد الشبابيك"""
        
        for member in team.members.all():
            try:
                technician = member.technician_profile
                if technician.can_handle_windows(windows_count, date):
                    return True
            except:
                continue
        return False
    
    @classmethod
    def _get_team_windows_capacity(cls, team: InstallationTeamNew, 
                                 date: datetime.date) -> int:
        """حساب السعة المتبقية للشبابيك للفريق في يوم معين"""
        
        total_capacity = 0
        for member in team.members.all():
            try:
                technician = member.technician_profile
                current_windows = technician.get_daily_windows_count(date)
                remaining_capacity = technician.max_windows_per_day - current_windows
                total_capacity += max(0, remaining_capacity)
            except:
                continue
        
        return total_capacity
    
    @classmethod
    def _calculate_priority_score(cls, installation: InstallationNew,
                                date: datetime.date, time_slot: Dict,
                                team: InstallationTeamNew) -> float:
        """حساب نقاط الأولوية للموعد المقترح"""
        
        score = 0.0
        
        # نقاط حسب أولوية التركيب
        priority_scores = {
            'urgent': 100,
            'high': 75,
            'normal': 50,
            'low': 25
        }
        score += priority_scores.get(installation.priority, 50)
        
        # نقاط حسب الوقت المفضل
        if time_slot['is_prime_time']:
            score += 20
        
        # نقاط حسب قرب التاريخ (كلما كان أقرب كان أفضل)
        days_from_now = (date - timezone.now().date()).days
        if days_from_now <= 3:
            score += 30
        elif days_from_now <= 7:
            score += 20
        elif days_from_now <= 14:
            score += 10
        
        # نقاط حسب خبرة الفريق
        if team.leader:
            try:
                leader_technician = team.leader.technician_profile
                score += leader_technician.experience_years * 2
            except:
                pass
        
        # نقاط حسب السعة المتبقية للفريق
        remaining_capacity = cls._get_team_windows_capacity(team, date)
        if remaining_capacity >= installation.windows_count * 2:
            score += 15
        elif remaining_capacity >= installation.windows_count:
            score += 10
        
        # خصم نقاط للأيام المزدحمة
        daily_installations = InstallationNew.objects.filter(
            scheduled_date=date,
            status__in=['scheduled', 'in_progress']
        ).count()
        
        if daily_installations >= 10:
            score -= 20
        elif daily_installations >= 8:
            score -= 10
        
        return score
    
    @classmethod
    def auto_schedule_installation(cls, installation: InstallationNew,
                                 preferred_date: datetime.date = None) -> bool:
        """جدولة تلقائية للتركيب"""
        
        suggestions = cls.suggest_optimal_schedule(installation, preferred_date)
        
        if not suggestions:
            # إنشاء تنبيه عدم توفر مواعيد
            InstallationAlert.objects.create(
                installation=installation,
                alert_type='schedule_conflict',
                severity='high',
                title='لا توجد مواعيد متاحة',
                message=f'لا يمكن جدولة التركيب للعميل {installation.customer_name}'
            )
            return False
        
        # اختيار أفضل اقتراح
        best_suggestion = suggestions[0]
        
        # تحديث التركيب
        installation.scheduled_date = best_suggestion['date']
        installation.scheduled_time_start = best_suggestion['time_slot']['start_time']
        installation.scheduled_time_end = best_suggestion['time_slot']['end_time']
        installation.team = best_suggestion['team']
        installation.status = 'scheduled'
        installation.save()
        
        # إنشاء جدولة
        InstallationSchedule.objects.create(
            installation=installation,
            date=best_suggestion['date'],
            time_slot_start=best_suggestion['time_slot']['start_time'],
            time_slot_end=best_suggestion['time_slot']['end_time'],
            estimated_duration=timedelta(hours=2),
            auto_scheduled=True,
            is_confirmed=True
        )
        
        logger.info(f"تم جدولة التركيب {installation.id} تلقائياً في {best_suggestion['date']}")
        return True
    
    @classmethod
    def check_daily_capacity_alerts(cls, date: datetime.date = None) -> List[Dict]:
        """فحص تنبيهات السعة اليومية"""
        
        if not date:
            date = timezone.now().date()
        
        alerts = []
        
        # عدد التركيبات المجدولة
        daily_count = InstallationNew.objects.filter(
            scheduled_date=date,
            status__in=['scheduled', 'in_progress']
        ).count()
        
        if daily_count >= cls.MAX_INSTALLATIONS_PER_DAY:
            alerts.append({
                'type': 'capacity_exceeded',
                'severity': 'critical',
                'message': f'تم تجاوز الحد الأقصى للتركيبات اليومية ({daily_count}/{cls.MAX_INSTALLATIONS_PER_DAY})',
                'date': date,
                'count': daily_count
            })
        elif daily_count >= cls.MAX_INSTALLATIONS_PER_DAY - 2:
            alerts.append({
                'type': 'capacity_warning',
                'severity': 'high',
                'message': f'اقتراب من الحد الأقصى للتركيبات اليومية ({daily_count}/{cls.MAX_INSTALLATIONS_PER_DAY})',
                'date': date,
                'count': daily_count
            })
        
        return alerts
