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

        # ✅ تحسين: استخدام aggregate بدلاً من جلب جميع السجلات
        # يقلل استهلاك الذاكرة ويحسن الأداء بشكل كبير
        today = timezone.now().date()

        # حساب جميع الإحصائيات في استعلام واحد
        stats = ManufacturingOrder.objects.aggregate(
            total_orders=Count('id'),
            pending_approval=Count('id', filter=Q(status='pending_approval')),
            pending=Count('id', filter=Q(status='pending')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            ready_install=Count('id', filter=Q(status='ready_install')),
            completed=Count('id', filter=Q(status='completed')),
            delivered=Count('id', filter=Q(status='delivered')),
            rejected=Count('id', filter=Q(status='rejected')),
            cancelled=Count('id', filter=Q(status='cancelled')),

            # الطلبات المتأخرة
            overdue=Count('id', filter=Q(
                expected_delivery_date__lt=today,
                status__in=['pending_approval', 'pending', 'in_progress']
            )),
        )

        # Get date range for charts (last 6 months for better view)
        end_date = today
        start_date = end_date - timedelta(days=180)  # 6 months

        # ✅ تحسين: استخدام values + annotate بدلاً من جلب جميع السجلات
        all_status_data = {
            'pending_approval': stats['pending_approval'],
            'pending': stats['pending'],
            'in_progress': stats['in_progress'],
            'ready_install': stats['ready_install'],
            'completed': stats['completed'],
            'delivered': stats['delivered'],
            'rejected': stats['rejected'],
            'cancelled': stats['cancelled'],
        }
        
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
        
        # ✅ تحسين: استعلام مباشر للبيانات الشهرية
        monthly_orders = ManufacturingOrder.objects.filter(
            order_date__range=(start_date, end_date)
        ).annotate(
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
        
        # ✅ تحسين: جلب آخر 10 طلبات مع select_related فقط
        recent_orders = ManufacturingOrder.objects.select_related(
            'order',
            'order__customer',
            'production_line'
        ).only(
            'id', 'status', 'created_at', 'order_date', 'expected_delivery_date',
            'order__id', 'order__order_number',
            'order__customer__id', 'order__customer__name',
            'production_line__id', 'production_line__name'
        ).order_by('-created_at')[:10]

        # ✅ تحسين: استعلام مباشر لأنواع الطلبات
        orders_by_type = ManufacturingOrder.objects.values('order_type').annotate(
            count=Count('id')
        )

        # ✅ تحسين: حساب إحصائيات الشهر في استعلام واحد
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

        month_stats = ManufacturingOrder.objects.aggregate(
            this_month=Count('id', filter=Q(order_date__gte=this_month_start)),
            last_month=Count('id', filter=Q(
                order_date__gte=last_month_start,
                order_date__lt=this_month_start
            ))
        )

        this_month_orders = month_stats['this_month']
        last_month_orders = month_stats['last_month']

        # Calculate percentage change
        if last_month_orders > 0:
            month_change_percent = ((this_month_orders - last_month_orders) / last_month_orders) * 100
        else:
            month_change_percent = 100 if this_month_orders > 0 else 0

        # ✅ تحسين: استخدام البيانات من stats بدلاً من استعلام جديد
        pending_approval_count = stats['pending_approval']
        # ✅ تحسين: استخدام البيانات من stats بدلاً من استعلام جديد
        overdue_orders = stats['overdue']

        # ✅ تحسين: حساب متوسط وقت الإنجاز باستخدام aggregate
        from django.db.models import Avg, ExpressionWrapper, DurationField
        from django.db.models.functions import Cast

        # حساب متوسط الأيام باستخدام aggregate (أسرع بكثير)
        avg_stats = ManufacturingOrder.objects.filter(
            status__in=['ready_install', 'completed', 'delivered'],
            completion_date__isnull=False,
            order_date__isnull=False
        ).aggregate(
            avg_days=Avg(
                ExpressionWrapper(
                    F('completion_date') - F('order_date'),
                    output_field=DurationField()
                )
            )
        )

        avg_completion_days = 0
        if avg_stats['avg_days']:
            avg_completion_days = round(avg_stats['avg_days'].days, 1)

        # ✅ تحسين: إحصائيات طلبات VIP في استعلام واحد
        vip_stats = ManufacturingOrder.objects.aggregate(
            vip_total=Count('id', filter=Q(order__status='vip')),
            vip_pending=Count('id', filter=Q(
                order__status='vip',
                status__in=['pending_approval', 'pending', 'in_progress']
            )),
            vip_completed=Count('id', filter=Q(
                order__status='vip',
                status__in=['ready_install', 'completed', 'delivered']
            ))
        )

        vip_orders_count = vip_stats['vip_total']
        vip_pending_count = vip_stats['vip_pending']
        vip_completed_count = vip_stats['vip_completed']

        # ✅ تحسين: إحصائيات خطوط الإنتاج باستخدام annotate (استعلام واحد بدلاً من N استعلامات)
        from .models import ProductionLine

        production_lines_stats = ProductionLine.objects.filter(
            is_active=True
        ).annotate(
            total_orders=Count('manufacturing_orders'),
            active_orders=Count(
                'manufacturing_orders',
                filter=Q(manufacturing_orders__status__in=[
                    'pending_approval', 'pending', 'in_progress'
                ])
            ),
            completed_orders=Count(
                'manufacturing_orders',
                filter=Q(manufacturing_orders__status__in=[
                    'ready_install', 'completed', 'delivered'
                ])
            ),
            overdue_orders=Count(
                'manufacturing_orders',
                filter=Q(
                    manufacturing_orders__expected_delivery_date__lt=today,
                    manufacturing_orders__status__in=[
                        'pending_approval', 'pending', 'in_progress'
                    ]
                )
            )
        ).order_by('-priority', 'name')

        context.update({
            'status_data': json.dumps(status_data),
            'monthly_data': json.dumps(monthly_data),
            'recent_orders': recent_orders,
            'orders_by_type': orders_by_type,

            # ✅ تحسين: استخدام البيانات من stats بدلاً من استعلامات جديدة
            'total_orders': stats['total_orders'],
            'pending_approval_orders': stats['pending_approval'],
            'pending_orders': stats['pending'],
            'in_progress_orders': stats['in_progress'],
            'ready_install_orders': stats['ready_install'],
            'completed_orders': stats['completed'],
            'delivered_orders': stats['delivered'],
            'rejected_orders': stats['rejected'],
            'cancelled_orders': stats['cancelled'],

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

            # Date ranges
            'start_date': start_date,
            'end_date': end_date,
            'chart_period': '6 أشهر',
        })
        
        return context