from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import ExtractMonth, ExtractYear
import json

from .models import ManufacturingOrder
from accounts.utils import apply_default_year_filter
from accounts.models import DashboardYearSettings


class ImprovedDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'manufacturing/dashboard.html'
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all manufacturing orders and apply default year filter
        all_orders = ManufacturingOrder.objects.all().select_related('order', 'order__customer')
        all_orders = apply_default_year_filter(all_orders, self.request, 'order_date')

        # Get default year for display
        default_year = DashboardYearSettings.get_default_year()

        # Get date range for charts (last 6 months for better view)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=180)  # 6 months

        # Get orders for charts (last 6 months) - also apply year filter
        chart_orders = all_orders.filter(order_date__range=(start_date, end_date))
        
        # Calculate status counts for all orders
        all_status_counts = all_orders.values('status').annotate(count=Count('status'))
        all_status_data = {item['status']: item['count'] for item in all_status_counts}
        
        # Prepare status data for the chart
        status_data = {
            'labels': [],
            'data': [],
            'colors': [],
        }
        
        status_colors = {
            'pending_approval': '#007bff',  # Blue
            'pending': '#ffc107',           # Yellow
            'in_progress': '#17a2b8',       # Cyan
            'ready_install': '#6f42c1',     # Purple
            'completed': '#28a745',         # Green
            'delivered': '#20c997',         # Teal
            'rejected': '#dc3545',          # Red
            'cancelled': '#6c757d',         # Gray
        }
        
        # Add all statuses to chart, even if count is 0
        for status_code, status_display in ManufacturingOrder.STATUS_CHOICES:
            count = all_status_data.get(status_code, 0)
            if count > 0:  # Only show statuses that have orders
                status_data['labels'].append(status_display)
                status_data['data'].append(count)
                status_data['colors'].append(status_colors.get(status_code, '#6c757d'))
        
        # Get monthly order counts for the last 6 months
        monthly_orders = chart_orders.annotate(
            month=ExtractMonth('order_date'),
            year=ExtractYear('order_date')
        ).values('year', 'month').annotate(
            total=Count('id')
        ).order_by('year', 'month')
        
        # Prepare monthly data for the chart
        monthly_data = {
            'labels': [],
            'data': [],
        }
        
        # Get month names in Arabic
        month_names = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        for item in monthly_orders:
            month_name = f"{month_names[item['month']-1]} {item['year']}"
            monthly_data['labels'].append(month_name)
            monthly_data['data'].append(item['total'])
        
        # Get recent orders (last 10)
        recent_orders = all_orders.order_by('-created_at')[:10]
        
        # Get orders by type (all orders)
        orders_by_type = all_orders.values('order_type').annotate(
            count=Count('id')
        )
        
        # Calculate additional statistics
        today = timezone.now().date()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        # This month vs last month comparison
        this_month_orders = all_orders.filter(order_date__gte=this_month_start).count()
        last_month_orders = all_orders.filter(
            order_date__gte=last_month_start,
            order_date__lt=this_month_start
        ).count()
        
        # Calculate percentage change
        if last_month_orders > 0:
            month_change_percent = ((this_month_orders - last_month_orders) / last_month_orders) * 100
        else:
            month_change_percent = 100 if this_month_orders > 0 else 0
        
        # Orders needing attention (pending approval + overdue)
        pending_approval_count = all_orders.filter(status='pending_approval').count()
        overdue_orders = all_orders.filter(
            expected_delivery_date__lt=today,
            status__in=['pending_approval', 'pending', 'in_progress']  # فقط هذه الحالات تعتبر متأخرة
        ).count()
        
        # Average completion time (for completed orders)
        completed_orders_with_dates = all_orders.filter(
            status__in=['completed', 'delivered'],
            completion_date__isnull=False,
            order_date__isnull=False
        )
        
        avg_completion_days = 0
        if completed_orders_with_dates.exists():
            total_days = 0
            count = 0
            for order in completed_orders_with_dates:
                if order.completion_date and order.order_date:
                    days_diff = (order.completion_date.date() - order.order_date).days
                    if days_diff >= 0:  # Only positive values
                        total_days += days_diff
                        count += 1
            if count > 0:
                avg_completion_days = round(total_days / count, 1)

        # إحصائيات طلبات VIP
        vip_orders_count = all_orders.filter(order__status='vip').count()
        vip_pending_count = all_orders.filter(
            order__status='vip',
            status__in=['pending_approval', 'pending', 'in_progress']
        ).count()
        vip_completed_count = all_orders.filter(
            order__status='vip',
            status__in=['completed', 'delivered']
        ).count()

        # Production lines statistics
        from .models import ProductionLine
        production_lines = ProductionLine.objects.filter(is_active=True).order_by('-priority', 'name')
        production_lines_stats = []

        for line in production_lines:
            line_orders = all_orders.filter(production_line=line)
            line_stats = {
                'line': line,
                'total_orders': line_orders.count(),
                'active_orders': line_orders.filter(
                    status__in=['pending_approval', 'pending', 'in_progress', 'ready_install']
                ).count(),
                'completed_orders': line_orders.filter(
                    status__in=['completed', 'delivered']
                ).count(),
                'overdue_orders': line_orders.filter(
                    expected_delivery_date__lt=today,
                    status__in=['pending_approval', 'pending', 'in_progress', 'ready_install']
                ).count()
            }
            production_lines_stats.append(line_stats)

        context.update({
            'status_data': json.dumps(status_data),
            'monthly_data': json.dumps(monthly_data),
            'recent_orders': recent_orders,
            'orders_by_type': orders_by_type,

            # Main statistics (all orders)
            'total_orders': all_orders.count(),
            'pending_approval_orders': all_status_data.get('pending_approval', 0),
            'pending_orders': all_status_data.get('pending', 0),
            'in_progress_orders': all_status_data.get('in_progress', 0),
            'ready_install_orders': all_status_data.get('ready_install', 0),
            'completed_orders': all_status_data.get('completed', 0),
            'delivered_orders': all_status_data.get('delivered', 0),
            'rejected_orders': all_status_data.get('rejected', 0),
            'cancelled_orders': all_status_data.get('cancelled', 0),

            # Additional metrics
            'this_month_orders': this_month_orders,
            'last_month_orders': last_month_orders,
            'month_change_percent': round(month_change_percent, 1),
            'pending_approval_count': pending_approval_count,
            'overdue_orders': overdue_orders,
            'avg_completion_days': avg_completion_days,

            # VIP orders statistics
            'vip_orders_count': vip_orders_count,
            'vip_pending_count': vip_pending_count,
            'vip_completed_count': vip_completed_count,

            # Production lines statistics
            'production_lines_stats': production_lines_stats,

            # Year filter information
            'default_year': default_year,

            # Date ranges
            'start_date': start_date,
            'end_date': end_date,
            'chart_period': '6 أشهر',
        })
        
        return context