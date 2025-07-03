"""
خدمة التقويم والجدولة التفاعلية
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import calendar

from ..models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationSchedule,
    DailyInstallationReport
)


class CalendarService:
    """خدمة التقويم والجدولة التفاعلية"""

    @classmethod
    def get_month_calendar(cls, year: int, month: int) -> Dict:
        """الحصول على تقويم الشهر - دالة مبسطة"""
        return cls.get_monthly_calendar(year, month)

    @classmethod
    def get_monthly_calendar(cls, year: int, month: int,
                           branch_name: str = None) -> Dict:
        """الحصول على تقويم شهري مع بيانات التركيبات"""
        
        # إنشاء التقويم
        cal = calendar.monthcalendar(year, month)
        
        # الحصول على بيانات التركيبات للشهر
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        installations_query = InstallationNew.objects.filter(
            scheduled_date__range=[start_date, end_date]
        )
        
        if branch_name:
            installations_query = installations_query.filter(
                branch_name=branch_name
            )
        
        # تجميع البيانات حسب التاريخ
        daily_data = {}
        for installation in installations_query:
            day = installation.scheduled_date.day
            if day not in daily_data:
                daily_data[day] = {
                    'total_installations': 0,
                    'completed': 0,
                    'scheduled': 0,
                    'in_progress': 0,
                    'cancelled': 0,
                    'total_windows': 0,
                    'installations': [],
                    'is_overloaded': False,
                    'teams_count': set(),
                }
            
            daily_data[day]['total_installations'] += 1
            daily_data[day]['total_windows'] += installation.windows_count
            daily_data[day]['installations'].append({
                'id': installation.id,
                'customer_name': installation.customer_name,
                'status': installation.status,
                'windows_count': installation.windows_count,
                'team_name': installation.team.name if installation.team else None,
                'scheduled_time_start': installation.scheduled_time_start,
                'scheduled_time_end': installation.scheduled_time_end,
                'priority': installation.priority,
            })
            
            # عد الحالات
            daily_data[day][installation.status] += 1
            
            # عد الفرق
            if installation.team:
                daily_data[day]['teams_count'].add(installation.team.id)
            
            # التحقق من الحمولة الزائدة
            if daily_data[day]['total_installations'] > 13:
                daily_data[day]['is_overloaded'] = True
        
        # تحويل sets إلى counts
        for day_data in daily_data.values():
            day_data['teams_count'] = len(day_data['teams_count'])
        
        return {
            'calendar': cal,
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'daily_data': daily_data,
            'summary': cls._get_monthly_summary(daily_data),
        }
    
    @classmethod
    def _get_monthly_summary(cls, daily_data: Dict) -> Dict:
        """حساب ملخص الشهر"""
        total_installations = sum(day['total_installations'] for day in daily_data.values())
        total_windows = sum(day['total_windows'] for day in daily_data.values())
        total_completed = sum(day['completed'] for day in daily_data.values())
        total_cancelled = sum(day['cancelled'] for day in daily_data.values())
        overloaded_days = sum(1 for day in daily_data.values() if day['is_overloaded'])
        
        return {
            'total_installations': total_installations,
            'total_windows': total_windows,
            'total_completed': total_completed,
            'total_cancelled': total_cancelled,
            'completion_rate': (total_completed / total_installations * 100) if total_installations > 0 else 0,
            'cancellation_rate': (total_cancelled / total_installations * 100) if total_installations > 0 else 0,
            'overloaded_days': overloaded_days,
            'busiest_day': max(daily_data.items(), key=lambda x: x[1]['total_installations'])[0] if daily_data else None,
        }
    
    @classmethod
    def get_daily_schedule(cls, target_date: date, 
                          branch_name: str = None) -> Dict:
        """الحصول على جدول يوم محدد"""
        
        installations = InstallationNew.objects.filter(
            scheduled_date=target_date
        ).select_related('team', 'order').order_by('scheduled_time_start')
        
        if branch_name:
            installations = installations.filter(branch_name=branch_name)
        
        # تجميع البيانات حسب الفترات الزمنية
        time_slots = {}
        teams_schedule = {}
        
        for installation in installations:
            # تجميع حسب الوقت
            time_key = installation.scheduled_time_start.strftime('%H:%M') if installation.scheduled_time_start else 'غير محدد'
            if time_key not in time_slots:
                time_slots[time_key] = []
            
            time_slots[time_key].append({
                'id': installation.id,
                'customer_name': installation.customer_name,
                'customer_phone': installation.customer_phone,
                'customer_address': installation.customer_address,
                'windows_count': installation.windows_count,
                'status': installation.status,
                'priority': installation.priority,
                'team_name': installation.team.name if installation.team else 'غير محدد',
                'technicians': installation.technicians_names,
                'location_type': installation.get_location_type_display(),
                'scheduled_time_start': installation.scheduled_time_start,
                'scheduled_time_end': installation.scheduled_time_end,
                'notes': installation.notes,
                'special_instructions': installation.special_instructions,
                'access_instructions': installation.access_instructions,
            })
            
            # تجميع حسب الفريق
            team_name = installation.team.name if installation.team else 'غير محدد'
            if team_name not in teams_schedule:
                teams_schedule[team_name] = []
            
            teams_schedule[team_name].append(time_slots[time_key][-1])
        
        # إحصائيات اليوم
        total_installations = installations.count()
        total_windows = sum(inst.windows_count for inst in installations)
        status_counts = {}
        priority_counts = {}
        
        for installation in installations:
            status_counts[installation.status] = status_counts.get(installation.status, 0) + 1
            priority_counts[installation.priority] = priority_counts.get(installation.priority, 0) + 1
        
        return {
            'date': target_date,
            'day_name': calendar.day_name[target_date.weekday()],
            'time_slots': dict(sorted(time_slots.items())),
            'teams_schedule': teams_schedule,
            'statistics': {
                'total_installations': total_installations,
                'total_windows': total_windows,
                'status_counts': status_counts,
                'priority_counts': priority_counts,
                'is_overloaded': total_installations > 13,
                'teams_count': len(teams_schedule),
            },
            'installations_list': list(installations.values(
                'id', 'customer_name', 'customer_phone', 'windows_count',
                'status', 'priority', 'scheduled_time_start', 'scheduled_time_end'
            ))
        }
    
    @classmethod
    def get_weekly_view(cls, start_date: date, 
                       branch_name: str = None) -> Dict:
        """الحصول على عرض أسبوعي"""
        
        end_date = start_date + timedelta(days=6)
        
        weekly_data = {}
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            daily_schedule = cls.get_daily_schedule(current_date, branch_name)
            weekly_data[current_date.strftime('%Y-%m-%d')] = daily_schedule
        
        # إحصائيات الأسبوع
        total_installations = sum(day['statistics']['total_installations'] 
                                for day in weekly_data.values())
        total_windows = sum(day['statistics']['total_windows'] 
                          for day in weekly_data.values())
        overloaded_days = sum(1 for day in weekly_data.values() 
                            if day['statistics']['is_overloaded'])
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'weekly_data': weekly_data,
            'summary': {
                'total_installations': total_installations,
                'total_windows': total_windows,
                'overloaded_days': overloaded_days,
                'average_daily_installations': total_installations / 7,
                'average_daily_windows': total_windows / 7,
            }
        }
    
    @classmethod
    def get_team_schedule(cls, team_id: int, start_date: date, 
                         days: int = 7) -> Dict:
        """الحصول على جدول فريق محدد"""
        
        try:
            team = InstallationTeamNew.objects.get(id=team_id)
        except InstallationTeamNew.DoesNotExist:
            return {'error': 'الفريق غير موجود'}
        
        end_date = start_date + timedelta(days=days-1)
        
        installations = InstallationNew.objects.filter(
            team=team,
            scheduled_date__range=[start_date, end_date]
        ).order_by('scheduled_date', 'scheduled_time_start')
        
        # تجميع حسب التاريخ
        daily_schedule = {}
        for installation in installations:
            date_key = installation.scheduled_date.strftime('%Y-%m-%d')
            if date_key not in daily_schedule:
                daily_schedule[date_key] = []
            
            daily_schedule[date_key].append({
                'id': installation.id,
                'customer_name': installation.customer_name,
                'customer_phone': installation.customer_phone,
                'windows_count': installation.windows_count,
                'status': installation.status,
                'scheduled_time_start': installation.scheduled_time_start,
                'scheduled_time_end': installation.scheduled_time_end,
                'location_type': installation.get_location_type_display(),
                'customer_address': installation.customer_address,
            })
        
        # إحصائيات الفريق
        total_installations = installations.count()
        total_windows = sum(inst.windows_count for inst in installations)
        
        return {
            'team': {
                'id': team.id,
                'name': team.name,
                'leader': team.leader.get_full_name() if team.leader else None,
                'members_count': team.members_count,
                'branch': team.branch.name,
            },
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days,
            },
            'daily_schedule': daily_schedule,
            'statistics': {
                'total_installations': total_installations,
                'total_windows': total_windows,
                'average_daily_installations': total_installations / days,
                'average_daily_windows': total_windows / days,
                'busiest_day': max(daily_schedule.items(), 
                                 key=lambda x: len(x[1]))[0] if daily_schedule else None,
            }
        }
    
    @classmethod
    def generate_printable_schedule(cls, target_date: date, 
                                  branch_name: str = None) -> Dict:
        """إنشاء جدول قابل للطباعة"""
        
        daily_schedule = cls.get_daily_schedule(target_date, branch_name)
        
        # تنسيق البيانات للطباعة
        printable_data = {
            'header': {
                'title': f'جدول التركيبات اليومي - {target_date.strftime("%Y/%m/%d")}',
                'day_name': calendar.day_name[target_date.weekday()],
                'branch': branch_name or 'جميع الفروع',
                'generated_at': timezone.now().strftime('%Y/%m/%d %H:%M'),
            },
            'summary': daily_schedule['statistics'],
            'installations': [],
        }
        
        # ترتيب التركيبات حسب الوقت
        for time_slot, installations in daily_schedule['time_slots'].items():
            for installation in installations:
                printable_data['installations'].append({
                    'time': time_slot,
                    'customer_name': installation['customer_name'],
                    'phone': installation['customer_phone'],
                    'address': installation['customer_address'][:50] + '...' if len(installation['customer_address']) > 50 else installation['customer_address'],
                    'windows': installation['windows_count'],
                    'team': installation['team_name'],
                    'technicians': installation['technicians'],
                    'status': installation['status'],
                    'priority': installation['priority'],
                    'notes': installation['notes'][:30] + '...' if len(installation['notes']) > 30 else installation['notes'],
                })
        
        return printable_data
