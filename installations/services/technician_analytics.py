"""
خدمة تحليل أداء الفنيين وحساب الشبابيك
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F, Case, When, IntegerField
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import calendar

from ..models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationTechnician
)
from accounts.models import User


class TechnicianAnalyticsService:
    """خدمة تحليل أداء الفنيين"""

    @classmethod
    def get_summary_statistics(cls) -> Dict:
        """الحصول على إحصائيات ملخصة للفنيين"""
        try:
            # إجمالي الفنيين
            total_technicians = InstallationTechnician.objects.filter(is_active=True).count()

            # الفنيين النشطين اليوم
            today = timezone.now().date()
            active_today = InstallationNew.objects.filter(
                scheduled_date=today,
                team__technicians__is_active=True
            ).values('team__technicians').distinct().count()

            # متوسط الشبابيك لكل فني
            avg_windows = InstallationNew.objects.filter(
                scheduled_date=today
            ).aggregate(
                avg_windows=Avg('windows_count')
            )['avg_windows'] or 0

            # أفضل فني (أكثر تركيبات مكتملة)
            best_technician = InstallationTechnician.objects.annotate(
                completed_count=Count(
                    'user__installationteamnew__installations',
                    filter=Q(user__installationteamnew__installations__status='completed')
                )
            ).order_by('-completed_count').first()

            return {
                'total_technicians': total_technicians,
                'active_today': active_today,
                'avg_windows_per_technician': round(avg_windows, 1),
                'best_technician': {
                    'name': best_technician.user.get_full_name() if best_technician else 'غير محدد',
                    'completed_count': best_technician.completed_count if best_technician else 0
                } if best_technician else None,
                'efficiency_rate': round((active_today / total_technicians * 100), 1) if total_technicians > 0 else 0
            }
        except Exception as e:
            return {
                'total_technicians': 0,
                'active_today': 0,
                'avg_windows_per_technician': 0,
                'best_technician': None,
                'efficiency_rate': 0,
                'error': str(e)
            }

    @classmethod
    def get_technician_daily_stats(cls, technician_id: int,
                                 target_date: date = None) -> Dict:
        """إحصائيات فني في يوم محدد"""
        
        if not target_date:
            target_date = timezone.now().date()
        
        try:
            technician = InstallationTechnician.objects.get(id=technician_id)
        except InstallationTechnician.DoesNotExist:
            return {'error': 'الفني غير موجود'}
        
        # التركيبات المجدولة للفني في هذا اليوم
        daily_installations = InstallationNew.objects.filter(
            team__members=technician.user,
            scheduled_date=target_date
        ).select_related('team', 'order')
        
        # حساب الإحصائيات
        total_installations = daily_installations.count()
        total_windows = sum(inst.windows_count for inst in daily_installations)
        
        # تجميع حسب الحالة
        status_breakdown = {}
        for status, _ in InstallationNew.STATUS_CHOICES:
            status_breakdown[status] = daily_installations.filter(status=status).count()
        
        # تجميع حسب الأولوية
        priority_breakdown = {}
        for priority, _ in InstallationNew.PRIORITY_CHOICES:
            priority_breakdown[priority] = daily_installations.filter(priority=priority).count()
        
        # حساب الوقت المقدر
        estimated_hours = total_installations * 2  # افتراض ساعتين لكل تركيب
        
        # التحقق من الحمولة
        capacity_status = 'normal'
        if total_windows >= technician.max_windows_per_day:
            capacity_status = 'overloaded'
        elif total_windows >= technician.max_windows_per_day * 0.9:
            capacity_status = 'near_capacity'
        
        return {
            'technician': {
                'id': technician.id,
                'name': technician.user.get_full_name(),
                'employee_id': technician.employee_id,
                'max_windows_per_day': technician.max_windows_per_day,
                'experience_years': technician.experience_years,
                'branch': technician.branch.name,
            },
            'date': target_date,
            'statistics': {
                'total_installations': total_installations,
                'total_windows': total_windows,
                'estimated_hours': estimated_hours,
                'capacity_utilization': (total_windows / technician.max_windows_per_day) * 100,
                'capacity_status': capacity_status,
                'remaining_capacity': max(0, technician.max_windows_per_day - total_windows),
            },
            'breakdown': {
                'status': status_breakdown,
                'priority': priority_breakdown,
            },
            'installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'windows_count': inst.windows_count,
                    'status': inst.status,
                    'priority': inst.priority,
                    'scheduled_time_start': inst.scheduled_time_start,
                    'scheduled_time_end': inst.scheduled_time_end,
                    'location_type': inst.get_location_type_display(),
                }
                for inst in daily_installations
            ]
        }
    
    @classmethod
    def get_technician_weekly_stats(cls, technician_id: int, 
                                  start_date: date = None) -> Dict:
        """إحصائيات فني لأسبوع"""
        
        if not start_date:
            start_date = timezone.now().date()
            # البدء من يوم السبت (بداية الأسبوع)
            start_date = start_date - timedelta(days=start_date.weekday() + 1)
        
        end_date = start_date + timedelta(days=6)
        
        try:
            technician = InstallationTechnician.objects.get(id=technician_id)
        except InstallationTechnician.DoesNotExist:
            return {'error': 'الفني غير موجود'}
        
        # التركيبات الأسبوعية
        weekly_installations = InstallationNew.objects.filter(
            team__members=technician.user,
            scheduled_date__range=[start_date, end_date]
        ).select_related('team')
        
        # إحصائيات يومية
        daily_stats = {}
        total_windows_week = 0
        total_installations_week = 0
        
        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            day_installations = weekly_installations.filter(scheduled_date=current_date)
            day_windows = sum(inst.windows_count for inst in day_installations)
            
            daily_stats[current_date.strftime('%Y-%m-%d')] = {
                'date': current_date,
                'day_name': calendar.day_name[current_date.weekday()],
                'installations_count': day_installations.count(),
                'windows_count': day_windows,
                'capacity_utilization': (day_windows / technician.max_windows_per_day) * 100,
                'is_overloaded': day_windows > technician.max_windows_per_day,
            }
            
            total_windows_week += day_windows
            total_installations_week += day_installations.count()
        
        # أكثر الأيام ازدحاماً
        busiest_day = max(daily_stats.values(), key=lambda x: x['windows_count'])
        
        return {
            'technician': {
                'id': technician.id,
                'name': technician.user.get_full_name(),
                'employee_id': technician.employee_id,
            },
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'week_number': start_date.isocalendar()[1],
            },
            'summary': {
                'total_installations': total_installations_week,
                'total_windows': total_windows_week,
                'average_daily_windows': total_windows_week / 7,
                'weekly_capacity_utilization': (total_windows_week / (technician.max_windows_per_day * 7)) * 100,
                'busiest_day': busiest_day,
                'overloaded_days': sum(1 for day in daily_stats.values() if day['is_overloaded']),
            },
            'daily_stats': daily_stats,
        }
    
    @classmethod
    def get_technician_monthly_stats(cls, technician_id: int, 
                                   year: int = None, month: int = None) -> Dict:
        """إحصائيات فني لشهر"""
        
        if not year:
            year = timezone.now().year
        if not month:
            month = timezone.now().month
        
        try:
            technician = InstallationTechnician.objects.get(id=technician_id)
        except InstallationTechnician.DoesNotExist:
            return {'error': 'الفني غير موجود'}
        
        # تحديد بداية ونهاية الشهر
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # التركيبات الشهرية
        monthly_installations = InstallationNew.objects.filter(
            team__members=technician.user,
            scheduled_date__range=[start_date, end_date]
        )
        
        # الإحصائيات العامة
        total_installations = monthly_installations.count()
        total_windows = sum(inst.windows_count for inst in monthly_installations)
        
        # تجميع حسب الحالة
        status_stats = {}
        for status, display in InstallationNew.STATUS_CHOICES:
            count = monthly_installations.filter(status=status).count()
            status_stats[status] = {
                'count': count,
                'percentage': (count / total_installations * 100) if total_installations > 0 else 0
            }
        
        # تجميع حسب الأسبوع
        weekly_stats = {}
        current_date = start_date
        week_number = 1
        
        while current_date <= end_date:
            week_start = current_date
            week_end = min(current_date + timedelta(days=6), end_date)
            
            week_installations = monthly_installations.filter(
                scheduled_date__range=[week_start, week_end]
            )
            week_windows = sum(inst.windows_count for inst in week_installations)
            
            weekly_stats[f'week_{week_number}'] = {
                'start_date': week_start,
                'end_date': week_end,
                'installations_count': week_installations.count(),
                'windows_count': week_windows,
            }
            
            current_date += timedelta(days=7)
            week_number += 1
        
        # حساب متوسط الأداء
        working_days = sum(1 for day in range((end_date - start_date).days + 1)
                          if (start_date + timedelta(days=day)).weekday() < 5)  # السبت-الأربعاء
        
        avg_daily_windows = total_windows / working_days if working_days > 0 else 0
        
        # تقييم الأداء
        performance_rating = cls._calculate_performance_rating(
            technician, total_windows, total_installations, working_days
        )
        
        return {
            'technician': {
                'id': technician.id,
                'name': technician.user.get_full_name(),
                'employee_id': technician.employee_id,
                'experience_years': technician.experience_years,
            },
            'period': {
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'start_date': start_date,
                'end_date': end_date,
                'working_days': working_days,
            },
            'summary': {
                'total_installations': total_installations,
                'total_windows': total_windows,
                'avg_daily_windows': avg_daily_windows,
                'monthly_capacity_utilization': (total_windows / (technician.max_windows_per_day * working_days)) * 100 if working_days > 0 else 0,
                'performance_rating': performance_rating,
            },
            'breakdown': {
                'status': status_stats,
                'weekly': weekly_stats,
            },
        }
    
    @classmethod
    def get_all_technicians_comparison(cls, date_range: Tuple[date, date] = None) -> Dict:
        """مقارنة أداء جميع الفنيين"""
        
        if not date_range:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)  # آخر 30 يوم
        else:
            start_date, end_date = date_range
        
        technicians = InstallationTechnician.objects.filter(is_active=True)
        comparison_data = []
        
        for technician in technicians:
            # حساب إحصائيات الفني
            technician_installations = InstallationNew.objects.filter(
                team__members=technician.user,
                scheduled_date__range=[start_date, end_date]
            )
            
            total_installations = technician_installations.count()
            total_windows = sum(inst.windows_count for inst in technician_installations)
            completed_installations = technician_installations.filter(status='completed').count()
            
            # حساب متوسط الجودة
            quality_ratings = [
                inst.quality_rating for inst in technician_installations 
                if inst.quality_rating and inst.status == 'completed'
            ]
            avg_quality = sum(quality_ratings) / len(quality_ratings) if quality_ratings else 0
            
            # حساب الأيام العاملة
            working_days = sum(1 for day in range((end_date - start_date).days + 1)
                              if (start_date + timedelta(days=day)).weekday() < 5)
            
            comparison_data.append({
                'technician': {
                    'id': technician.id,
                    'name': technician.user.get_full_name(),
                    'employee_id': technician.employee_id,
                    'experience_years': technician.experience_years,
                    'branch': technician.branch.name,
                },
                'performance': {
                    'total_installations': total_installations,
                    'total_windows': total_windows,
                    'completed_installations': completed_installations,
                    'completion_rate': (completed_installations / total_installations * 100) if total_installations > 0 else 0,
                    'avg_daily_windows': total_windows / working_days if working_days > 0 else 0,
                    'avg_quality_rating': avg_quality,
                    'capacity_utilization': (total_windows / (technician.max_windows_per_day * working_days)) * 100 if working_days > 0 else 0,
                }
            })
        
        # ترتيب حسب الأداء
        comparison_data.sort(key=lambda x: x['performance']['total_windows'], reverse=True)
        
        # إحصائيات عامة
        total_all_windows = sum(tech['performance']['total_windows'] for tech in comparison_data)
        total_all_installations = sum(tech['performance']['total_installations'] for tech in comparison_data)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'working_days': working_days,
            },
            'summary': {
                'total_technicians': len(comparison_data),
                'total_windows': total_all_windows,
                'total_installations': total_all_installations,
                'avg_windows_per_technician': total_all_windows / len(comparison_data) if comparison_data else 0,
            },
            'technicians': comparison_data,
            'top_performers': comparison_data[:5],  # أفضل 5 فنيين
        }
    
    @classmethod
    def get_team_windows_distribution(cls, team_id: int, 
                                    target_date: date = None) -> Dict:
        """توزيع الشبابيك على أعضاء الفريق"""
        
        if not target_date:
            target_date = timezone.now().date()
        
        try:
            team = InstallationTeamNew.objects.get(id=team_id)
        except InstallationTeamNew.DoesNotExist:
            return {'error': 'الفريق غير موجود'}
        
        # التركيبات المجدولة للفريق
        team_installations = InstallationNew.objects.filter(
            team=team,
            scheduled_date=target_date
        )
        
        # توزيع الشبابيك على الأعضاء
        members_distribution = []
        total_team_windows = 0
        
        for member in team.members.all():
            try:
                technician = member.technician_profile
                member_windows = technician.get_daily_windows_count(target_date)
                
                members_distribution.append({
                    'technician': {
                        'id': technician.id,
                        'name': member.get_full_name(),
                        'employee_id': technician.employee_id,
                        'max_windows_per_day': technician.max_windows_per_day,
                    },
                    'windows_count': member_windows,
                    'capacity_utilization': (member_windows / technician.max_windows_per_day) * 100,
                    'remaining_capacity': max(0, technician.max_windows_per_day - member_windows),
                    'is_overloaded': member_windows > technician.max_windows_per_day,
                })
                
                total_team_windows += member_windows
                
            except:
                # العضو ليس فني مسجل
                members_distribution.append({
                    'technician': {
                        'id': None,
                        'name': member.get_full_name(),
                        'employee_id': 'غير مسجل',
                        'max_windows_per_day': 0,
                    },
                    'windows_count': 0,
                    'capacity_utilization': 0,
                    'remaining_capacity': 0,
                    'is_overloaded': False,
                })
        
        # حساب التوزيع المثالي
        total_capacity = sum(
            member['technician']['max_windows_per_day'] 
            for member in members_distribution
        )
        
        return {
            'team': {
                'id': team.id,
                'name': team.name,
                'leader': team.leader.get_full_name() if team.leader else None,
                'branch': team.branch.name,
            },
            'date': target_date,
            'summary': {
                'total_members': len(members_distribution),
                'total_windows': total_team_windows,
                'total_capacity': total_capacity,
                'team_utilization': (total_team_windows / total_capacity * 100) if total_capacity > 0 else 0,
                'remaining_capacity': max(0, total_capacity - total_team_windows),
                'overloaded_members': sum(1 for member in members_distribution if member['is_overloaded']),
            },
            'members_distribution': members_distribution,
            'installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'windows_count': inst.windows_count,
                    'status': inst.status,
                }
                for inst in team_installations
            ]
        }
    
    @classmethod
    def _calculate_performance_rating(cls, technician: InstallationTechnician,
                                    total_windows: int, total_installations: int,
                                    working_days: int) -> Dict:
        """حساب تقييم الأداء"""
        
        # معايير التقييم
        target_daily_windows = technician.max_windows_per_day * 0.8  # 80% من السعة
        actual_daily_avg = total_windows / working_days if working_days > 0 else 0
        
        # نقاط الأداء
        productivity_score = min(100, (actual_daily_avg / target_daily_windows) * 100) if target_daily_windows > 0 else 0
        
        # تحديد التقييم
        if productivity_score >= 90:
            rating = 'ممتاز'
            color = 'success'
        elif productivity_score >= 75:
            rating = 'جيد جداً'
            color = 'info'
        elif productivity_score >= 60:
            rating = 'جيد'
            color = 'warning'
        else:
            rating = 'يحتاج تحسين'
            color = 'danger'
        
        return {
            'score': round(productivity_score, 1),
            'rating': rating,
            'color': color,
            'target_daily_windows': target_daily_windows,
            'actual_daily_avg': round(actual_daily_avg, 1),
        }
