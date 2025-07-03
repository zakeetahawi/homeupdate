"""
خدمة بطاقات العرض للوحة التحكم
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, Case, When, IntegerField
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

from ..models_new import InstallationNew, InstallationTeamNew
from orders.models import Order


class DashboardCardsService:
    """خدمة بطاقات العرض للوحة التحكم"""
    
    @classmethod
    def get_all_cards_data(cls, branch_name: str = None, 
                          user_branch: str = None) -> Dict:
        """الحصول على بيانات جميع البطاقات"""
        
        # تحديد الفرع للفلترة
        filter_branch = branch_name or user_branch
        
        return {
            'ready_orders': cls.get_ready_orders_card(filter_branch),
            'ready_scheduled': cls.get_ready_scheduled_card(filter_branch),
            'not_ready_orders': cls.get_not_ready_orders_card(filter_branch),
            'debt_orders': cls.get_debt_orders_card(filter_branch),
            'summary': cls.get_summary_stats(filter_branch),
            'alerts': cls.get_alerts_data(filter_branch),
        }
    
    @classmethod
    def get_ready_orders_card(cls, branch_name: str = None) -> Dict:
        """بطاقة الطلبات الجاهزة للتركيب"""
        
        # الطلبات الجاهزة من المصنع ولكن غير مجدولة
        query = InstallationNew.objects.filter(
            is_ready_for_installation=True,
            status__in=['pending', 'ready'],
            payment_status__in=['paid', 'partial']
        )
        
        if branch_name:
            query = query.filter(branch_name=branch_name)
        
        installations = query.select_related('order', 'team').order_by('-created_at')
        
        # إحصائيات
        total_count = installations.count()
        total_windows = sum(inst.windows_count for inst in installations)
        urgent_count = installations.filter(priority='urgent').count()
        high_priority_count = installations.filter(priority='high').count()
        
        # تجميع حسب الأولوية
        priority_breakdown = {
            'urgent': installations.filter(priority='urgent').count(),
            'high': installations.filter(priority='high').count(),
            'normal': installations.filter(priority='normal').count(),
            'low': installations.filter(priority='low').count(),
        }
        
        # أقدم الطلبات
        oldest_orders = installations.order_by('order_date')[:5]
        
        return {
            'title': 'طلبات جاهزة للتركيب',
            'count': total_count,
            'total_windows': total_windows,
            'urgent_count': urgent_count,
            'high_priority_count': high_priority_count,
            'priority_breakdown': priority_breakdown,
            'color': 'success',
            'icon': 'fas fa-check-circle',
            'installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'customer_phone': inst.customer_phone,
                    'windows_count': inst.windows_count,
                    'priority': inst.priority,
                    'order_date': inst.order_date,
                    'days_waiting': (timezone.now().date() - inst.order_date.date()).days,
                    'location_type': inst.get_location_type_display(),
                    'branch_name': inst.branch_name,
                }
                for inst in installations[:20]  # أول 20 طلب
            ],
            'oldest_orders': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'days_waiting': (timezone.now().date() - inst.order_date.date()).days,
                    'priority': inst.priority,
                }
                for inst in oldest_orders
            ],
            'needs_attention': urgent_count + high_priority_count > 0,
        }
    
    @classmethod
    def get_ready_scheduled_card(cls, branch_name: str = None) -> Dict:
        """بطاقة الطلبات الجاهزة والمجدولة"""
        
        query = InstallationNew.objects.filter(
            is_ready_for_installation=True,
            status='scheduled',
            scheduled_date__isnull=False
        )
        
        if branch_name:
            query = query.filter(branch_name=branch_name)
        
        installations = query.select_related('team').order_by('scheduled_date', 'scheduled_time_start')
        
        # إحصائيات
        total_count = installations.count()
        total_windows = sum(inst.windows_count for inst in installations)
        
        # تجميع حسب التاريخ
        today = timezone.now().date()
        today_count = installations.filter(scheduled_date=today).count()
        tomorrow_count = installations.filter(scheduled_date=today + timedelta(days=1)).count()
        this_week_count = installations.filter(
            scheduled_date__range=[today, today + timedelta(days=7)]
        ).count()
        
        # التركيبات القادمة (أسبوع)
        upcoming_installations = installations.filter(
            scheduled_date__range=[today, today + timedelta(days=7)]
        )[:10]
        
        # التركيبات اليوم
        today_installations = installations.filter(scheduled_date=today)
        
        return {
            'title': 'طلبات جاهزة ومجدولة',
            'count': total_count,
            'total_windows': total_windows,
            'today_count': today_count,
            'tomorrow_count': tomorrow_count,
            'this_week_count': this_week_count,
            'color': 'info',
            'icon': 'fas fa-calendar-check',
            'installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'customer_phone': inst.customer_phone,
                    'windows_count': inst.windows_count,
                    'scheduled_date': inst.scheduled_date,
                    'scheduled_time_start': inst.scheduled_time_start,
                    'team_name': inst.team.name if inst.team else 'غير محدد',
                    'days_until': (inst.scheduled_date - today).days,
                    'location_type': inst.get_location_type_display(),
                    'priority': inst.priority,
                }
                for inst in upcoming_installations
            ],
            'today_installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'scheduled_time_start': inst.scheduled_time_start,
                    'team_name': inst.team.name if inst.team else 'غير محدد',
                    'windows_count': inst.windows_count,
                }
                for inst in today_installations
            ],
            'needs_attention': today_count > 10,  # تنبيه إذا كان هناك أكثر من 10 تركيبات اليوم
        }
    
    @classmethod
    def get_not_ready_orders_card(cls, branch_name: str = None) -> Dict:
        """بطاقة الطلبات غير الجاهزة"""
        
        query = InstallationNew.objects.filter(
            is_ready_for_installation=False,
            status__in=['pending', 'ready'],
            payment_status__in=['paid', 'partial']
        )
        
        if branch_name:
            query = query.filter(branch_name=branch_name)
        
        installations = query.order_by('-created_at')
        
        # إحصائيات
        total_count = installations.count()
        total_windows = sum(inst.windows_count for inst in installations)
        
        # تجميع حسب مدة الانتظار
        today = timezone.now().date()
        waiting_breakdown = {
            'less_than_week': 0,
            'one_to_two_weeks': 0,
            'two_to_four_weeks': 0,
            'more_than_month': 0,
        }
        
        for inst in installations:
            days_waiting = (today - inst.order_date.date()).days
            if days_waiting < 7:
                waiting_breakdown['less_than_week'] += 1
            elif days_waiting < 14:
                waiting_breakdown['one_to_two_weeks'] += 1
            elif days_waiting < 30:
                waiting_breakdown['two_to_four_weeks'] += 1
            else:
                waiting_breakdown['more_than_month'] += 1
        
        # الطلبات المتأخرة (أكثر من شهر)
        overdue_installations = installations.filter(
            order_date__lt=today - timedelta(days=30)
        )
        
        return {
            'title': 'طلبات غير جاهزة',
            'count': total_count,
            'total_windows': total_windows,
            'waiting_breakdown': waiting_breakdown,
            'overdue_count': overdue_installations.count(),
            'color': 'warning',
            'icon': 'fas fa-clock',
            'installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'customer_phone': inst.customer_phone,
                    'windows_count': inst.windows_count,
                    'order_date': inst.order_date,
                    'days_waiting': (today - inst.order_date.date()).days,
                    'priority': inst.priority,
                    'branch_name': inst.branch_name,
                }
                for inst in installations[:20]
            ],
            'overdue_installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'days_waiting': (today - inst.order_date.date()).days,
                    'windows_count': inst.windows_count,
                }
                for inst in overdue_installations[:10]
            ],
            'needs_attention': overdue_installations.count() > 0,
        }
    
    @classmethod
    def get_debt_orders_card(cls, branch_name: str = None) -> Dict:
        """بطاقة الطلبات بمديونية"""
        
        query = InstallationNew.objects.filter(
            payment_status__in=['pending', 'overdue']
        )
        
        if branch_name:
            query = query.filter(branch_name=branch_name)
        
        installations = query.select_related('order').order_by('-order_date')
        
        # إحصائيات
        total_count = installations.count()
        total_windows = sum(inst.windows_count for inst in installations)
        
        # حساب المبالغ المستحقة
        total_debt = 0
        overdue_debt = 0
        
        for inst in installations:
            if hasattr(inst.order, 'remaining_amount'):
                debt_amount = inst.order.remaining_amount
                total_debt += debt_amount
                
                # إذا كان الطلب متأخر السداد (أكثر من 30 يوم)
                if (timezone.now().date() - inst.order_date.date()).days > 30:
                    overdue_debt += debt_amount
        
        # تجميع حسب حالة السداد
        payment_breakdown = {
            'pending': installations.filter(payment_status='pending').count(),
            'overdue': installations.filter(payment_status='overdue').count(),
        }
        
        # الطلبات المتأخرة السداد
        overdue_payments = installations.filter(payment_status='overdue')
        
        return {
            'title': 'طلبات بمديونية',
            'count': total_count,
            'total_windows': total_windows,
            'total_debt': total_debt,
            'overdue_debt': overdue_debt,
            'payment_breakdown': payment_breakdown,
            'color': 'danger',
            'icon': 'fas fa-exclamation-triangle',
            'installations': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'customer_phone': inst.customer_phone,
                    'windows_count': inst.windows_count,
                    'order_date': inst.order_date,
                    'payment_status': inst.payment_status,
                    'remaining_amount': getattr(inst.order, 'remaining_amount', 0),
                    'days_overdue': (timezone.now().date() - inst.order_date.date()).days,
                    'priority': inst.priority,
                }
                for inst in installations[:20]
            ],
            'overdue_payments': [
                {
                    'id': inst.id,
                    'customer_name': inst.customer_name,
                    'days_overdue': (timezone.now().date() - inst.order_date.date()).days,
                    'remaining_amount': getattr(inst.order, 'remaining_amount', 0),
                }
                for inst in overdue_payments[:10]
            ],
            'needs_attention': overdue_payments.count() > 0,
        }
    
    @classmethod
    def get_summary_stats(cls, branch_name: str = None) -> Dict:
        """إحصائيات ملخصة"""
        
        query = InstallationNew.objects.all()
        if branch_name:
            query = query.filter(branch_name=branch_name)
        
        today = timezone.now().date()
        
        return {
            'total_installations': query.count(),
            'total_windows': sum(inst.windows_count for inst in query),
            'completed_today': query.filter(
                status='completed',
                actual_end_date__date=today
            ).count(),
            'scheduled_today': query.filter(
                scheduled_date=today,
                status='scheduled'
            ).count(),
            'overdue_installations': query.filter(
                scheduled_date__lt=today,
                status__in=['pending', 'scheduled']
            ).count(),
            'active_teams': InstallationTeamNew.objects.filter(
                is_active=True,
                installations_new__scheduled_date=today
            ).distinct().count(),
        }
    
    @classmethod
    def get_alerts_data(cls, branch_name: str = None) -> List[Dict]:
        """بيانات التنبيهات"""
        
        alerts = []
        today = timezone.now().date()
        
        # تنبيه الطلبات المتأخرة
        overdue_query = InstallationNew.objects.filter(
            scheduled_date__lt=today,
            status__in=['pending', 'scheduled']
        )
        if branch_name:
            overdue_query = overdue_query.filter(branch_name=branch_name)
        
        overdue_count = overdue_query.count()
        if overdue_count > 0:
            alerts.append({
                'type': 'overdue',
                'severity': 'high',
                'title': f'{overdue_count} تركيب متأخر',
                'message': f'يوجد {overdue_count} تركيب متأخر عن موعده المحدد',
                'count': overdue_count,
            })
        
        # تنبيه السعة اليومية
        today_count = InstallationNew.objects.filter(
            scheduled_date=today,
            status__in=['scheduled', 'in_progress']
        )
        if branch_name:
            today_count = today_count.filter(branch_name=branch_name)
        
        today_count = today_count.count()
        if today_count >= 13:
            alerts.append({
                'type': 'capacity',
                'severity': 'critical',
                'title': 'تجاوز السعة اليومية',
                'message': f'تم جدولة {today_count} تركيب اليوم (الحد الأقصى 13)',
                'count': today_count,
            })
        elif today_count >= 11:
            alerts.append({
                'type': 'capacity_warning',
                'severity': 'medium',
                'title': 'اقتراب من السعة القصوى',
                'message': f'تم جدولة {today_count} تركيب اليوم',
                'count': today_count,
            })
        
        return alerts

    @classmethod
    def get_alerts_data(cls, branch_name: str = None) -> List[Dict]:
        """بيانات التنبيهات"""

        alerts = []
        today = timezone.now().date()

        # تنبيه الطلبات المتأخرة
        overdue_query = InstallationNew.objects.filter(
            scheduled_date__lt=today,
            status__in=['pending', 'scheduled']
        )
        if branch_name:
            overdue_query = overdue_query.filter(branch_name=branch_name)

        overdue_count = overdue_query.count()
        if overdue_count > 0:
            alerts.append({
                'type': 'overdue',
                'severity': 'high',
                'title': f'{overdue_count} تركيب متأخر',
                'message': f'يوجد {overdue_count} تركيب متأخر عن موعده المحدد',
                'count': overdue_count,
            })

        # تنبيه السعة اليومية
        today_count = InstallationNew.objects.filter(
            scheduled_date=today,
            status__in=['scheduled', 'in_progress']
        )
        if branch_name:
            today_count = today_count.filter(branch_name=branch_name)

        today_count = today_count.count()
        if today_count >= 13:
            alerts.append({
                'type': 'capacity',
                'severity': 'critical',
                'title': 'تجاوز السعة اليومية',
                'message': f'تم جدولة {today_count} تركيب اليوم (الحد الأقصى 13)',
                'count': today_count,
            })
        elif today_count >= 11:
            alerts.append({
                'type': 'capacity_warning',
                'severity': 'medium',
                'title': 'اقتراب من السعة القصوى',
                'message': f'تم جدولة {today_count} تركيب اليوم',
                'count': today_count,
            })

        return alerts
