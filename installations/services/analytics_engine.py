"""
محرك التحليلات الشامل للتركيبات
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F, Case, When, IntegerField, FloatField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Extract
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import calendar

from ..models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationTechnician,
    DailyInstallationReport
)
from accounts.models import User, Branch


class AnalyticsEngine:
    """محرك التحليلات الشامل"""
    
    @classmethod
    def get_dashboard_analytics(cls, branch_name: str = None, 
                              date_range: Tuple[date, date] = None) -> Dict:
        """تحليلات لوحة التحكم الرئيسية"""
        
        if not date_range:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date, end_date = date_range
        
        # استعلام أساسي
        installations = InstallationNew.objects.all()
        if branch_name:
            installations = installations.filter(branch_name=branch_name)
        
        # إحصائيات عامة
        total_installations = installations.count()
        period_installations = installations.filter(
            scheduled_date__range=[start_date, end_date]
        )
        
        # إحصائيات الحالة
        status_stats = cls._get_status_statistics(period_installations)
        
        # إحصائيات الأولوية
        priority_stats = cls._get_priority_statistics(period_installations)
        
        # اتجاهات الأداء
        performance_trends = cls._get_performance_trends(installations, start_date, end_date)
        
        # إحصائيات الفرق
        team_stats = cls._get_team_statistics(period_installations)
        
        # إحصائيات الجودة
        quality_stats = cls._get_quality_statistics(period_installations)
        
        # مؤشرات الأداء الرئيسية (KPIs)
        kpis = cls._calculate_kpis(period_installations, start_date, end_date)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days_count': (end_date - start_date).days + 1,
            },
            'overview': {
                'total_installations': total_installations,
                'period_installations': period_installations.count(),
                'total_windows': sum(inst.windows_count for inst in period_installations),
                'active_teams': InstallationTeamNew.objects.filter(is_active=True).count(),
                'active_technicians': InstallationTechnician.objects.filter(is_active=True).count(),
            },
            'status_distribution': status_stats,
            'priority_distribution': priority_stats,
            'performance_trends': performance_trends,
            'team_performance': team_stats,
            'quality_metrics': quality_stats,
            'kpis': kpis,
        }
    
    @classmethod
    def _get_status_statistics(cls, installations) -> Dict:
        """إحصائيات الحالة"""
        
        status_counts = installations.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        total = installations.count()
        status_data = {}
        
        for item in status_counts:
            status = item['status']
            count = item['count']
            percentage = (count / total * 100) if total > 0 else 0
            
            status_data[status] = {
                'count': count,
                'percentage': round(percentage, 1)
            }
        
        # إضافة الحالات المفقودة بقيم صفر
        all_statuses = ['pending', 'ready', 'scheduled', 'in_progress', 'completed', 'cancelled']
        for status in all_statuses:
            if status not in status_data:
                status_data[status] = {'count': 0, 'percentage': 0}
        
        return status_data
    
    @classmethod
    def _get_priority_statistics(cls, installations) -> Dict:
        """إحصائيات الأولوية"""
        
        priority_counts = installations.values('priority').annotate(
            count=Count('id')
        ).order_by('priority')
        
        total = installations.count()
        priority_data = {}
        
        for item in priority_counts:
            priority = item['priority']
            count = item['count']
            percentage = (count / total * 100) if total > 0 else 0
            
            priority_data[priority] = {
                'count': count,
                'percentage': round(percentage, 1)
            }
        
        return priority_data
    
    @classmethod
    def _get_performance_trends(cls, installations, start_date: date, 
                              end_date: date) -> Dict:
        """اتجاهات الأداء"""
        
        # اتجاه يومي
        daily_trends = installations.filter(
            scheduled_date__range=[start_date, end_date]
        ).extra(
            select={'day': 'date(scheduled_date)'}
        ).values('day').annotate(
            installations_count=Count('id'),
            windows_count=Sum('windows_count'),
            completed_count=Count(Case(
                When(status='completed', then=1),
                output_field=IntegerField()
            ))
        ).order_by('day')
        
        # اتجاه أسبوعي
        weekly_trends = installations.filter(
            scheduled_date__range=[start_date, end_date]
        ).annotate(
            week=TruncWeek('scheduled_date')
        ).values('week').annotate(
            installations_count=Count('id'),
            windows_count=Sum('windows_count'),
            completed_count=Count(Case(
                When(status='completed', then=1),
                output_field=IntegerField()
            ))
        ).order_by('week')
        
        return {
            'daily': list(daily_trends),
            'weekly': list(weekly_trends),
        }
    
    @classmethod
    def _get_team_statistics(cls, installations) -> Dict:
        """إحصائيات الفرق"""
        
        team_stats = installations.filter(
            team__isnull=False
        ).values(
            'team__name', 'team__id'
        ).annotate(
            installations_count=Count('id'),
            windows_count=Sum('windows_count'),
            completed_count=Count(Case(
                When(status='completed', then=1),
                output_field=IntegerField()
            )),
            avg_quality=Avg('quality_rating'),
            avg_satisfaction=Avg('customer_satisfaction')
        ).order_by('-installations_count')
        
        # حساب معدل الإكمال لكل فريق
        for team in team_stats:
            total = team['installations_count']
            completed = team['completed_count']
            team['completion_rate'] = (completed / total * 100) if total > 0 else 0
        
        return list(team_stats)
    
    @classmethod
    def _get_quality_statistics(cls, installations) -> Dict:
        """إحصائيات الجودة"""
        
        completed_installations = installations.filter(status='completed')
        
        # متوسط تقييم الجودة
        quality_ratings = completed_installations.exclude(
            quality_rating__isnull=True
        ).aggregate(
            avg_quality=Avg('quality_rating'),
            count_quality=Count('quality_rating')
        )
        
        # متوسط رضا العملاء
        satisfaction_ratings = completed_installations.exclude(
            customer_satisfaction__isnull=True
        ).aggregate(
            avg_satisfaction=Avg('customer_satisfaction'),
            count_satisfaction=Count('customer_satisfaction')
        )
        
        # توزيع التقييمات
        quality_distribution = completed_installations.exclude(
            quality_rating__isnull=True
        ).values('quality_rating').annotate(
            count=Count('id')
        ).order_by('quality_rating')
        
        satisfaction_distribution = completed_installations.exclude(
            customer_satisfaction__isnull=True
        ).values('customer_satisfaction').annotate(
            count=Count('id')
        ).order_by('customer_satisfaction')
        
        return {
            'average_quality': round(quality_ratings['avg_quality'] or 0, 2),
            'average_satisfaction': round(satisfaction_ratings['avg_satisfaction'] or 0, 2),
            'quality_responses': quality_ratings['count_quality'],
            'satisfaction_responses': satisfaction_ratings['count_satisfaction'],
            'quality_distribution': list(quality_distribution),
            'satisfaction_distribution': list(satisfaction_distribution),
        }
    
    @classmethod
    def _calculate_kpis(cls, installations, start_date: date, end_date: date) -> Dict:
        """حساب مؤشرات الأداء الرئيسية"""
        
        total_installations = installations.count()
        completed_installations = installations.filter(status='completed').count()
        cancelled_installations = installations.filter(status='cancelled').count()
        overdue_installations = installations.filter(
            scheduled_date__lt=timezone.now().date(),
            status__in=['pending', 'scheduled']
        ).count()
        
        # معدل الإكمال
        completion_rate = (completed_installations / total_installations * 100) if total_installations > 0 else 0
        
        # معدل الإلغاء
        cancellation_rate = (cancelled_installations / total_installations * 100) if total_installations > 0 else 0
        
        # معدل التأخير
        overdue_rate = (overdue_installations / total_installations * 100) if total_installations > 0 else 0
        
        # متوسط الشبابيك لكل تركيب
        avg_windows = installations.aggregate(avg=Avg('windows_count'))['avg'] or 0
        
        # متوسط مدة التركيب
        completed_with_duration = installations.filter(
            status='completed',
            actual_start_date__isnull=False,
            actual_end_date__isnull=False
        )
        
        total_duration = 0
        duration_count = 0
        for installation in completed_with_duration:
            if installation.duration_hours:
                total_duration += installation.duration_hours
                duration_count += 1
        
        avg_duration = total_duration / duration_count if duration_count > 0 else 0
        
        # إنتاجية يومية
        days_count = (end_date - start_date).days + 1
        daily_productivity = total_installations / days_count if days_count > 0 else 0
        
        return {
            'completion_rate': round(completion_rate, 1),
            'cancellation_rate': round(cancellation_rate, 1),
            'overdue_rate': round(overdue_rate, 1),
            'average_windows_per_installation': round(avg_windows, 1),
            'average_installation_duration': round(avg_duration, 1),
            'daily_productivity': round(daily_productivity, 1),
            'total_windows': installations.aggregate(total=Sum('windows_count'))['total'] or 0,
        }
    
    @classmethod
    def get_branch_comparison(cls, date_range: Tuple[date, date] = None) -> Dict:
        """مقارنة أداء الفروع"""
        
        if not date_range:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date, end_date = date_range
        
        # إحصائيات الفروع
        branch_stats = InstallationNew.objects.filter(
            scheduled_date__range=[start_date, end_date]
        ).values('branch_name').annotate(
            installations_count=Count('id'),
            windows_count=Sum('windows_count'),
            completed_count=Count(Case(
                When(status='completed', then=1),
                output_field=IntegerField()
            )),
            cancelled_count=Count(Case(
                When(status='cancelled', then=1),
                output_field=IntegerField()
            )),
            avg_quality=Avg('quality_rating'),
            avg_satisfaction=Avg('customer_satisfaction')
        ).order_by('-installations_count')
        
        # حساب المعدلات
        for branch in branch_stats:
            total = branch['installations_count']
            completed = branch['completed_count']
            cancelled = branch['cancelled_count']
            
            branch['completion_rate'] = (completed / total * 100) if total > 0 else 0
            branch['cancellation_rate'] = (cancelled / total * 100) if total > 0 else 0
            branch['avg_quality'] = round(branch['avg_quality'] or 0, 2)
            branch['avg_satisfaction'] = round(branch['avg_satisfaction'] or 0, 2)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'branches': list(branch_stats),
            'summary': {
                'total_branches': len(branch_stats),
                'best_performing_branch': max(branch_stats, key=lambda x: x['completion_rate']) if branch_stats else None,
                'most_productive_branch': max(branch_stats, key=lambda x: x['installations_count']) if branch_stats else None,
            }
        }
    
    @classmethod
    def get_monthly_report(cls, year: int, month: int, 
                         branch_name: str = None) -> Dict:
        """التقرير الشهري الشامل"""
        
        # تحديد بداية ونهاية الشهر
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # استعلام التركيبات
        installations = InstallationNew.objects.filter(
            scheduled_date__range=[start_date, end_date]
        )
        
        if branch_name:
            installations = installations.filter(branch_name=branch_name)
        
        # الإحصائيات الأساسية
        basic_stats = {
            'total_installations': installations.count(),
            'total_windows': installations.aggregate(total=Sum('windows_count'))['total'] or 0,
            'completed_installations': installations.filter(status='completed').count(),
            'cancelled_installations': installations.filter(status='cancelled').count(),
            'pending_installations': installations.filter(status='pending').count(),
        }
        
        # التوزيع اليومي
        daily_distribution = installations.extra(
            select={'day': 'day(scheduled_date)'}
        ).values('day').annotate(
            count=Count('id'),
            windows=Sum('windows_count')
        ).order_by('day')
        
        # التوزيع الأسبوعي
        weekly_distribution = installations.annotate(
            week_number=Extract('scheduled_date', 'week')
        ).values('week_number').annotate(
            count=Count('id'),
            windows=Sum('windows_count')
        ).order_by('week_number')
        
        # أداء الفرق
        team_performance = installations.filter(
            team__isnull=False
        ).values('team__name').annotate(
            installations_count=Count('id'),
            windows_count=Sum('windows_count'),
            completion_rate=Avg(Case(
                When(status='completed', then=100),
                default=0,
                output_field=FloatField()
            ))
        ).order_by('-installations_count')
        
        # إحصائيات الجودة
        quality_stats = installations.filter(
            status='completed',
            quality_rating__isnull=False
        ).aggregate(
            avg_quality=Avg('quality_rating'),
            min_quality=Min('quality_rating'),
            max_quality=Max('quality_rating'),
            quality_count=Count('quality_rating')
        )
        
        return {
            'period': {
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'start_date': start_date,
                'end_date': end_date,
                'working_days': cls._count_working_days(start_date, end_date),
            },
            'basic_statistics': basic_stats,
            'daily_distribution': list(daily_distribution),
            'weekly_distribution': list(weekly_distribution),
            'team_performance': list(team_performance),
            'quality_statistics': quality_stats,
            'kpis': cls._calculate_kpis(installations, start_date, end_date),
        }
    
    @classmethod
    def _count_working_days(cls, start_date: date, end_date: date) -> int:
        """حساب أيام العمل (السبت-الأربعاء)"""
        
        working_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # أيام العمل: السبت (5) إلى الأربعاء (2)
            if current_date.weekday() in [5, 6, 0, 1, 2]:  # السبت-الأربعاء
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    @classmethod
    def get_predictive_analytics(cls, branch_name: str = None) -> Dict:
        """التحليلات التنبؤية"""
        
        # البيانات التاريخية (آخر 90 يوم)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        historical_data = InstallationNew.objects.filter(
            scheduled_date__range=[start_date, end_date]
        )
        
        if branch_name:
            historical_data = historical_data.filter(branch_name=branch_name)
        
        # حساب المتوسطات
        daily_avg = historical_data.count() / 90
        weekly_avg = daily_avg * 7
        monthly_avg = daily_avg * 30
        
        # توقعات الأسبوع القادم
        next_week_start = end_date + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)
        
        predicted_next_week = round(weekly_avg)
        
        # توقعات الشهر القادم
        predicted_next_month = round(monthly_avg)
        
        # تحليل الاتجاهات
        recent_trend = cls._analyze_trend(historical_data, days=30)
        
        return {
            'historical_period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': 90,
            },
            'averages': {
                'daily': round(daily_avg, 1),
                'weekly': round(weekly_avg, 1),
                'monthly': round(monthly_avg, 1),
            },
            'predictions': {
                'next_week': {
                    'period': f"{next_week_start} - {next_week_end}",
                    'predicted_installations': predicted_next_week,
                    'confidence': 'متوسط',
                },
                'next_month': {
                    'predicted_installations': predicted_next_month,
                    'confidence': 'منخفض',
                },
            },
            'trends': recent_trend,
        }
    
    @classmethod
    def _analyze_trend(cls, installations, days: int = 30) -> Dict:
        """تحليل الاتجاه"""
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # تقسيم الفترة إلى نصفين
        mid_date = start_date + timedelta(days=days//2)
        
        first_half = installations.filter(
            scheduled_date__range=[start_date, mid_date]
        ).count()
        
        second_half = installations.filter(
            scheduled_date__range=[mid_date + timedelta(days=1), end_date]
        ).count()
        
        # حساب الاتجاه
        if second_half > first_half * 1.1:
            trend = 'صاعد'
            trend_percentage = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
        elif second_half < first_half * 0.9:
            trend = 'هابط'
            trend_percentage = ((first_half - second_half) / first_half * 100) if first_half > 0 else 0
        else:
            trend = 'مستقر'
            trend_percentage = 0
        
        return {
            'direction': trend,
            'percentage': round(trend_percentage, 1),
            'first_half_count': first_half,
            'second_half_count': second_half,
        }
