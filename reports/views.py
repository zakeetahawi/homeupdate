from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, F, Window, Max
from datetime import datetime, timedelta, date
from django.utils import timezone

from .models import Report, SavedReport, ReportSchedule
from orders.models import Order, Payment, OrderItem
from inventory.models import Product
from customers.models import Customer

from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.db.models.functions import TruncDate
from django.http import HttpResponse
import csv
from .forms import ReportForm


@permission_required('reports.view_report', raise_exception=True)
def seller_customer_activity_view(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    report_data = ReportDetailView().get_initial_report_data(report)
    date_list = report_data.get('date_list', [])
    raw_results = report_data.get('results', {})

    # build presentation results: daily_list aligned with date_list for easy templating
    view_results = {}
    for uid, data in raw_results.items():
        daily_list = [data['daily'].get(d, 0) for d in date_list]
        view_results[uid] = {
            'user': data['user'],
            'daily_list': daily_list,
            'total': data['total']
        }

    return render(request, 'reports/seller_customer_activity.html', {
        'report': report,
        'date_list': date_list,
        'results': view_results,
        'zero_users': report_data.get('zero_users', []),
        'days': report_data.get('days', 7),
        'activity': report_data.get('activity', 'customers')
    })


@permission_required('reports.view_report', raise_exception=True)
def seller_customer_activity_export_csv(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    report_data = ReportDetailView().get_initial_report_data(report)
    date_list = report_data.get('date_list', [])
    results = report_data.get('results', {})

    # Build CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="seller_activity_{report_id}.csv"'
    writer = csv.writer(response)

    header = ['User'] + [d.strftime('%Y-%m-%d') for d in date_list] + ['Total']
    writer.writerow(header)

    for uid, data in results.items():
        row = [f"{data['user'].get_full_name() or data['user'].username}"]
        # data may be presentation-friendly or raw; prefer daily_list if present
        if isinstance(data.get('daily'), dict):
            for d in date_list:
                row.append(data['daily'].get(d, 0))
        elif isinstance(data.get('daily_list'), list):
            row.extend(data['daily_list'])
        else:
            # fallback: zeros
            row.extend([0] * len(date_list))
        row.append(data.get('total', 0))
        writer.writerow(row)

    return response


@permission_required('reports.view_report', raise_exception=True)
def seller_customer_activity_index(request):
    # list available reports of this type
    # support both legacy and new keys for compatibility
    reports_qs = Report.objects.filter(report_type__in=['seller_activity', 'seller_customer_activity'])
    return render(request, 'reports/seller_customer_activity_index.html', {'reports': reports_qs})

class ReportDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Get reports accessible by the user
        reports = Report.objects.all()

        # Basic statistics
        context['total_reports'] = reports.count()
        context['recent_reports'] = reports.order_by('-created_at')[:10]
        context['scheduled_reports'] = ReportSchedule.objects.filter(is_active=True).count()

        # Report statistics by type
        report_types = {
            'sales': _('تقارير المبيعات'),
            'inspection': _('تقارير المعاينات'),
            'production': _('تقارير الإنتاج'),
            'inventory': _('تقارير المخزون'),
            'financial': _('تقارير مالية'),
        }

        type_counts = {}
        for report_type, label in report_types.items():
            count = reports.filter(report_type=report_type).count()
            type_counts[label] = count

        context['report_type_counts'] = type_counts

        return context

class ReportListView(LoginRequiredMixin, ListView):
    model = Report
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'

    @method_decorator(permission_required('reports.view_report', raise_exception=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        # عرض جميع التقارير للجميع ممن لديهم الصلاحية
        return Report.objects.all()

class ReportCreateView(LoginRequiredMixin, CreateView):
    model = Report
    form_class = ReportForm
    template_name = 'reports/report_form.html'
    success_url = reverse_lazy('reports:report_list')

    def form_valid(self, form):
        # assemble parameters from helper fields when report_type is seller_activity
        params = {}
        if form.cleaned_data.get('report_type') in ('seller_activity', 'seller_customer_activity'):
            params['days'] = int(form.cleaned_data.get('days') or 7)
            params['activity'] = form.cleaned_data.get('activity') or 'customers'
            # save selected roles as list of ids
            roles = form.cleaned_data.get('seller_roles')
            if roles:
                params['seller_roles'] = [int(r.pk) for r in roles]
            else:
                params['seller_roles'] = []

        form.instance.parameters = params
        form.instance.created_by = self.request.user
        messages.success(self.request, _('تم إنشاء التقرير بنجاح'))
        response = super().form_valid(form)
        # if user clicked 'save and open'
        if self.request.POST.get('_open'):
            return redirect('reports:report_detail', pk=self.object.pk)
        return response

class ReportUpdateView(LoginRequiredMixin, UpdateView):
    model = Report
    form_class = ReportForm
    template_name = 'reports/report_form.html'
    success_url = reverse_lazy('reports:report_list')

    def get_queryset(self):
        # Allow staff users to view any report. Regular users only see reports they created.
        if getattr(self.request, 'user', None) and self.request.user.is_staff:
            return Report.objects.all()
        return Report.objects.filter(created_by=self.request.user)

    def form_valid(self, form):
        # update parameters if seller activity
        params = {}
        if form.cleaned_data.get('report_type') in ('seller_activity', 'seller_customer_activity'):
            params['days'] = int(form.cleaned_data.get('days') or 7)
            params['activity'] = form.cleaned_data.get('activity') or 'customers'
            roles = form.cleaned_data.get('seller_roles')
            if roles:
                params['seller_roles'] = [int(r.pk) for r in roles]
            else:
                params['seller_roles'] = []

        form.instance.parameters = params
        messages.success(self.request, _('تم تحديث التقرير بنجاح'))
        response = super().form_valid(form)
        if self.request.POST.get('_open'):
            return redirect('reports:report_detail', pk=self.object.pk)
        return response

class ReportDeleteView(LoginRequiredMixin, DeleteView):
    model = Report
    template_name = 'reports/report_confirm_delete.html'
    success_url = reverse_lazy('reports:report_list')

    def get_queryset(self):
        # Staff users can view any report, regular users see only their own
        if getattr(self.request, 'user', None) and self.request.user.is_staff:
            return Report.objects.all()
        return Report.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تم حذف التقرير بنجاح'))
        return super().delete(request, *args, **kwargs)

class ReportDetailView(LoginRequiredMixin, DetailView):
    model = Report
    template_name = 'reports/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        # allow staff to view any report
        if getattr(self.request, 'user', None) and self.request.user.is_staff:
            return Report.objects.all()
        return Report.objects.filter(created_by=self.request.user)

    def get_template_names(self):
        """تحديد قالب العرض بناءً على نوع التقرير"""
        report = self.get_object()
        if report.report_type == 'analytics':
            return ['reports/includes/analytics_report_enhanced.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_object()

        # Get saved results for this report
        context['saved_results'] = report.saved_results.all()

        # Get initial report data
        report_data = self.get_initial_report_data(report)
        context['report_data'] = report_data

        # If this is a seller activity report, populate friendly context keys used by the seller template
        if report.report_type in ('seller_customer_activity', 'seller_activity') and report_data:
            context.update({
                'date_list': report_data.get('date_list', []),
                'results': report_data.get('results', {}),
                'zero_users': report_data.get('zero_users', []),
                'days': report_data.get('days', 7),
                'activity': report_data.get('activity', 'customers'),
            })

        # Add additional context for enhanced analytics
        if report.report_type == 'analytics':
            context.update({
                'date_ranges': [
                    {'value': '7', 'label': 'آخر 7 أيام'},
                    {'value': '30', 'label': 'آخر 30 يوم'},
                    {'value': '90', 'label': 'آخر 3 شهور'},
                    {'value': '180', 'label': 'آخر 6 شهور'},
                    {'value': '365', 'label': 'آخر سنة'},
                ],
                'grouping_options': [
                    {'value': 'day', 'label': 'يومي'},
                    {'value': 'week', 'label': 'أسبوعي'},
                    {'value': 'month', 'label': 'شهري'},
                    {'value': 'quarter', 'label': 'ربع سنوي'},
                ],
                'analysis_types': [
                    {'value': 'trend', 'label': 'تحليل الاتجاه'},
                    {'value': 'comparison', 'label': 'تحليل مقارن'},
                    {'value': 'forecast', 'label': 'التنبؤ'},
                ]
            })

        return context

    def get_initial_report_data(self, report):
        """جلب البيانات الأولية للتقرير"""
        if report.report_type == 'sales':
            return self.generate_sales_report(report)
        elif report.report_type == 'inspection':
            return self.generate_inspection_report(report)
        elif report.report_type == 'production':
            return self.generate_production_report(report)
        elif report.report_type == 'inventory':
            return self.generate_inventory_report(report)
        elif report.report_type == 'financial':
            return self.generate_financial_report(report)
        elif report.report_type == 'analytics':
            return self.generate_analytics_report(report)
        elif report.report_type in ('seller_customer_activity', 'seller_activity'):
            return self.generate_seller_customer_activity_report(report)

        return None

    def generate_seller_customer_activity_report(self, report):
        """Generate report: for sellers, how many customers they created per day in the past N days.

        report.parameters expected keys:
          - days: int (default 7)
          - activity: 'customers' | 'orders' | 'inspections' | 'all'
          - seller_group: optional, if true restrict to users with role 'seller'
        """
        days = int(report.parameters.get('days', 7))
        activity = report.parameters.get('activity', 'customers')
        start_date = timezone.now().date() - timedelta(days=days-1)

        # base user queryset: sellers only if requested
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users_qs = User.objects.all()
        if report.parameters.get('seller_group'):
            users_qs = users_qs.filter(groups__name__icontains='seller')

        # Prepare an ordered list of dates
        date_list = [start_date + timedelta(days=i) for i in range(days)]

        # Initialize result structure
        results = {}
        for u in users_qs.order_by('first_name', 'last_name'):
            results[u.id] = {
                'user': u,
                'daily': {d: 0 for d in date_list},
                'total': 0
            }

        # Use DB aggregation (group by created_by and date) for performance
        if activity in ('customers', 'all'):
            cust_qs = Customer.objects.filter(created_at__date__gte=start_date)
            cust_agg = cust_qs.annotate(day=TruncDate('created_at')).values('created_by', 'day').annotate(cnt=Count('id'))
            for row in cust_agg:
                uid = row.get('created_by')
                d = row.get('day')
                if uid in results and d in results[uid]['daily']:
                    results[uid]['daily'][d] += row.get('cnt', 0)
                    results[uid]['total'] += row.get('cnt', 0)

        if activity in ('orders', 'all'):
            ord_qs = Order.objects.filter(created_at__date__gte=start_date)
            ord_agg = ord_qs.annotate(day=TruncDate('created_at')).values('created_by', 'day').annotate(cnt=Count('id'))
            for row in ord_agg:
                uid = row.get('created_by')
                d = row.get('day')
                if uid in results and d in results[uid]['daily']:
                    results[uid]['daily'][d] += row.get('cnt', 0)
                    results[uid]['total'] += row.get('cnt', 0)

        if activity in ('inspections', 'all'):
            from inspections.models import Inspection
            ins_qs = Inspection.objects.filter(created_at__date__gte=start_date)
            ins_agg = ins_qs.annotate(day=TruncDate('created_at')).values('created_by', 'day').annotate(cnt=Count('id'))
            for row in ins_agg:
                uid = row.get('created_by')
                d = row.get('day')
                if uid in results and d in results[uid]['daily']:
                    results[uid]['daily'][d] += row.get('cnt', 0)
                    results[uid]['total'] += row.get('cnt', 0)

        # users with zero activity
        zero_users = [v['user'] for v in results.values() if v['total'] == 0]

        return {
            'date_list': date_list,
            'results': results,
            'zero_users': zero_users,
            'days': days,
            'activity': activity,
        }
    def generate_inspection_report(self, report):
        """تقرير إحصائي للمعاينات"""
        from inspections.models import Inspection
        date_range = report.parameters.get('date_range', 30)
        start_date = datetime.now() - timedelta(days=date_range)
        inspections = Inspection.objects.filter(request_date__gte=start_date)
        data = {
            'total_inspections': inspections.count(),
            'successful_inspections': inspections.filter(result='passed').count(),
            'pending_inspections': inspections.filter(status='pending').count(),
            'cancelled_inspections': inspections.filter(status='cancelled').count(),
        }
        return data

    def generate_sales_report(self, report):
        """Generate sales report data"""
        # Get date range from parameters or default to last 30 days
        date_range = report.parameters.get('date_range', 30)
        start_date = datetime.now() - timedelta(days=date_range)

        orders = Order.objects.filter(
            order_date__gte=start_date
        ).select_related('customer')

        data = {
            'total_orders': orders.count(),
            'total_revenue': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'orders_by_status': orders.values('status').annotate(count=Count('id')).order_by('status'),
            'top_customers': Customer.objects.filter(
                customer_orders__in=orders
            ).annotate(
                total_orders=Count('customer_orders'),
                total_spent=Sum('customer_orders__total_amount')
            ).order_by('-total_spent')[:10]
        }
        return data

    def generate_production_report(self, report):
        """
        Generate production report data
        This will be reimplemented after rebuilding the factory system
        """
        return {
            'total_orders': 0,
            'completed_orders': 0,
            'completion_rate': 0,
            'status_stats': [],
            'line_stats': [],
            'avg_production_time': None,
            'recent_orders': [],
            'date_from': report.parameters.get('date_from') if report else None,
            'date_to': report.parameters.get('date_to') if report else None,
            'message': 'سيتم إعادة تنفيذ هذا التقرير بعد إعادة بناء نظام المصنع',
            'status': 'not_implemented'
        }

    def generate_inventory_report(self, report):
        """Generate inventory report data - محسن لتجنب N+1"""
        # استخدام select_related لتحسين الأداء
        products = Product.objects.select_related('category').all()

        # حساب الإحصائيات باستخدام استعلامات قاعدة البيانات بدلاً من Python loops
        from django.db.models import Sum, Count, Case, When, IntegerField
        
        # حساب الإحصائيات الأساسية أولاً
        basic_stats = products.aggregate(
            total_items=Count('id')
        )

        # حساب الإحصائيات بطريقة محسنة باستخدام Subquery
        from django.db.models import OuterRef, Subquery
        from inventory.models import StockTransaction
        
        # الحصول على آخر رصيد لكل منتج
        latest_balance = StockTransaction.objects.filter(
            product=OuterRef('pk')
        ).order_by('-transaction_date').values('running_balance')[:1]
        
        # إضافة الرصيد الحالي للمنتجات
        products_with_stock = products.annotate(
            current_stock_level=Subquery(latest_balance)
        )
        
        # جلب المنتجات منخفضة المخزون والمنتجات ال��افدة باستعلامات منفصلة
        low_stock_items = products_with_stock.filter(
            current_stock_level__lte=F('minimum_stock'),
            current_stock_level__gt=0
        )[:20]  # تحديد العدد لتحسين الأداء
        
        out_of_stock_items = products_with_stock.filter(
            current_stock_level=0
        )[:20]

        data = {
            'total_items': basic_stats.get('total_items', 0) or 0,
            'total_value': 0,
            'low_stock_items': list(low_stock_items),
            'out_of_stock_items': list(out_of_stock_items),
            'low_stock_count': low_stock_items.count(),
            'out_of_stock_count': out_of_stock_items.count(),
            'items': products[:50]  # تحديد العدد لتحسين الأداء
        }
        return data

    def generate_financial_report(self, report):
        """Generate financial report data"""
        # Get date range from parameters or default to last 30 days
        date_range = report.parameters.get('date_range', 30)
        start_date = datetime.now() - timedelta(days=date_range)

        payments = Payment.objects.filter(payment_date__gte=start_date)
        orders = Order.objects.filter(order_date__gte=start_date)

        data = {
            'total_revenue': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'total_payments': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
            'payments_by_method': payments.values('payment_method').annotate(
                count=Count('id'),
                total=Sum('amount')
            ),
            'outstanding_balance': (
                orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            ) - (
                payments.aggregate(Sum('amount'))['amount__sum'] or 0
            )
        }
        return data

    def generate_analytics_report(self, report):
        """توليد التقرير التحليلي المتقدم"""
        from django.db.models import Avg, StdDev, Count, Case, When, F, Sum, FloatField
        from django.db.models.functions import TruncMonth, ExtractHour, ExtractWeekDay

        date_range = report.parameters.get('date_range', 30)
        start_date = timezone.now() - timedelta(days=date_range)

        # تحليلات المبيعات المتقدمة
        orders = Order.objects.filter(created_at__gte=start_date)
        # تم تعطيل تحليل المبيعات الشهرية مؤقتًا بسبب مشكلة في TruncMonth
        monthly_sales = []

        # تم تعطيل تحليل نمط المبيعات اليومي مؤقتًا بسبب مشكلة في ExtractWeekDay
        daily_patterns = []

        # مؤشرات الأداء الرئيسية
        kpi_data = {
            # تم تعطيل حساب النمو مؤقتًا بسبب مشكلة في الحساب
            'sales_growth': 0,
            'customer_retention': self.calculate_customer_retention(start_date),
            'avg_fulfillment_time': self.calculate_avg_fulfillment_time(orders),
            'profit_margin': self.calculate_profit_margin(orders)
        }

        # تحليل سلوك العملاء
        customer_analysis = orders.values('customer').annotate(
            total_spent=Sum('total_amount'),
            order_count=Count('id'),
            avg_order_value=Avg('total_amount'),
            last_order_date=Max('created_at')
        ).order_by('-total_spent')

        # تم تعطيل تحليل التدفق النقدي مؤقتًا بسبب مشكلة في TruncMonth
        cash_flow = []

        return {
            'sales_analysis': {
                'monthly_trends': list(monthly_sales),
                'daily_patterns': list(daily_patterns),
                'total_orders': orders.count(),
                'total_revenue': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
                'avg_order_value': orders.aggregate(Avg('total_amount'))['total_amount__avg'] or 0
            },
            'kpi_metrics': kpi_data,
            'customer_insights': {
                'top_customers': list(customer_analysis[:10]),
                'customer_segments': self.analyze_customer_segments(customer_analysis),
                'retention_rate': kpi_data['customer_retention']
            },
            'financial_health': {
                'cash_flow': list(cash_flow),
                'profit_margin': kpi_data['profit_margin'],
                'revenue_growth': kpi_data['sales_growth']
            }
        }

    def calculate_fulfillment_rate(self, orders):
        """حساب معدل إكمال الطلبات"""
        # تم تعطيل حساب معدل إكمال الطلبات مؤقتًا بسبب مشكلة في حقل completion_date
        return 0

    def calculate_inventory_turnover(self):
        """حساب معدل دوران المخزون"""
        # تم تعطيل حساب معدل دوران المخزون مؤقتًا بسبب مشكلة في aggregate
        return 0

    def calculate_customer_retention(self, start_date):
        """حساب معدل الاحتفاظ بالعملاء"""
        from django.db.models.functions import TruncMonth

        # حساب العملاء النشطين في الشهر الحالي
        current_customers = Customer.objects.filter(
            customer_orders__created_at__gte=start_date
        ).distinct().count()

        # حساب العملاء النشطين في الشهر السابق
        previous_start = start_date - timedelta(days=30)
        previous_customers = Customer.objects.filter(
            customer_orders__created_at__range=[previous_start, start_date]
        ).distinct().count()

        if previous_customers == 0:
            return 0

        return (current_customers / previous_customers) * 100

    def calculate_avg_fulfillment_time(self, orders):
        """حساب متوسط وقت إتمام الطلبات"""
        # تم تعطيل حساب متوسط وقت إتمام الطلبات مؤقتًا بسبب مشكلة في annotate
        return 0

    def calculate_profit_margin(self, orders):
        """حساب هامش الربح"""
        # تم تعطيل حساب هامش الربح مؤقتًا بسبب مشكلة في annotate
        return 0

    def analyze_customer_segments(self, customer_analysis):
        """تحليل شرائح العملاء"""
        from sklearn.preprocessing import StandardScaler
        import numpy as np

        if not customer_analysis:
            return []

        # تحضير البيانات للتحليل
        data = np.array([[c['total_spent'], c['order_count']] for c in customer_analysis])
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)

        # تقسيم العملاء إلى شرائح
        segments = {
            'vip': [],
            'regular': [],
            'occasional': []
        }

        for i, customer in enumerate(customer_analysis):
            score = scaled_data[i].mean()
            if score > 0.5:
                segments['vip'].append(customer)
            elif score > -0.5:
                segments['regular'].append(customer)
            else:
                segments['occasional'].append(customer)

        return {
            'segments': segments,
            'summary': {
                'vip_count': len(segments['vip']),
                'regular_count': len(segments['regular']),
                'occasional_count': len(segments['occasional'])
            }
        }

def save_report_result(request, pk):
    """Save the current report result"""
    if request.method == 'POST':
        report = get_object_or_404(Report, pk=pk, created_by=request.user)
        name = request.POST.get('name')

        # Get the report data
        if report.report_type == 'sales':
            data = ReportDetailView.generate_sales_report(None, report)
        elif report.report_type == 'inspection':
            data = ReportDetailView.generate_inspection_report(None, report)

        # Save the result
        SavedReport.objects.create(
            report=report,
            name=name,
            data=data,
            parameters_used=report.parameters,
            created_by=request.user
        )

        messages.success(request, _('تم حفظ نتيجة التقرير بنجاح'))
        return redirect('reports:report_detail', pk=pk)

    return redirect('reports:report_list')

class ReportScheduleCreateView(LoginRequiredMixin, CreateView):
    model = ReportSchedule
    template_name = 'reports/report_schedule_form.html'
    fields = ['name', 'frequency', 'parameters', 'recipients']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = get_object_or_404(Report, pk=self.kwargs['pk'])
        context['debug'] = True  # Enable debug information for creation form too
        return context

    def form_valid(self, form):
        form.instance.report = get_object_or_404(Report, pk=self.kwargs['pk'])
        form.instance.created_by = self.request.user
        messages.success(self.request, _('تم إنشاء جدولة التقرير بنجاح'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('reports:report_detail', kwargs={'pk': self.kwargs['pk']})

class ReportScheduleUpdateView(LoginRequiredMixin, UpdateView):
    model = ReportSchedule
    template_name = 'reports/report_schedule_form.html'
    fields = ['name', 'frequency', 'parameters', 'recipients', 'is_active']

    def get_queryset(self):
        return ReportSchedule.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = self.object.report
        context['debug'] = True  # Enable debug information
        return context

    def form_valid(self, form):
        messages.success(self.request, _('تم تحديث جدولة التقرير بنجاح'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('reports:report_detail', kwargs={'pk': self.object.report.pk})

class ReportScheduleDeleteView(LoginRequiredMixin, DeleteView):
    model = ReportSchedule
    template_name = 'reports/report_schedule_confirm_delete.html'

    def get_queryset(self):
        return ReportSchedule.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تم حذف جدولة التقرير بنجاح'))
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('reports:report_detail', kwargs={'pk': self.object.report.pk})
