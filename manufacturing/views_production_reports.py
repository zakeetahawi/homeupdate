"""
عروض تقارير الإنتاج للمصنع
Production Reports Views for Manufacturing
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Q, F, Avg, DecimalField
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging

from .models import (
    ManufacturingOrder, 
    ManufacturingStatusLog, 
    ProductionForecast,
    ProductionLine,
    ManufacturingOrderItem
)

logger = logging.getLogger(__name__)

# الحالات التي تعتبر "مكتمل الإنتاج"
COMPLETED_STATUSES = ['completed', 'ready_install', 'delivered']


def normalize_status(status):
    """
    تطبيع الحالة - تحويل الحالات المكتملة إلى حالة واحدة
    """
    if status in COMPLETED_STATUSES:
        return 'completed_production'
    return status


def get_latest_status_logs(queryset):
    """
    الحصول على آخر سجل حالة لكل أمر تصنيع
    مع تطبيق منطق عدم التكرار للحالات المكتملة
    """
    from django.db.models import OuterRef, Subquery

    # الحصول على آخر سجل لكل أمر تصنيع باستخدام Subquery (أكثر كفاءة)
    latest_logs_subquery = queryset.filter(
        manufacturing_order_id=OuterRef('manufacturing_order_id')
    ).order_by('-changed_at').values('id')[:1]

    # تصفية السجلات للحصول على آخر سجل فقط لكل أمر
    latest_logs = queryset.filter(
        id__in=Subquery(latest_logs_subquery)
    )

    # تطبيق منطق عدم التكرار للحالات المكتملة
    # إذا كانت الحالة الجديدة من ضمن الحالات المكتملة، نتحقق من عدم وجود سجل سابق بحالة مكتملة أخرى
    filtered_ids = []
    processed_orders = set()

    for log in latest_logs.order_by('-changed_at'):
        order_id = log.manufacturing_order_id

        # إذا تم معالجة هذا الطلب من قبل، نتخطاه
        if order_id in processed_orders:
            continue

        # إذا كانت الحالة الجديدة من الحالات المكتملة
        if log.new_status in COMPLETED_STATUSES:
            # نتحقق من عدم وجود سجل سابق بحالة مكتملة أخرى
            previous_completed = queryset.filter(
                manufacturing_order_id=order_id,
                new_status__in=COMPLETED_STATUSES,
                changed_at__lt=log.changed_at
            ).exists()

            # إذا كان هناك سجل سابق بحالة مكتملة، نتخطى هذا السجل
            if previous_completed:
                continue

        filtered_ids.append(log.id)
        processed_orders.add(order_id)

    return queryset.filter(id__in=filtered_ids)


class ProductionReportDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    لوحة تحكم تقارير الإنتاج
    Production Reports Dashboard
    """
    template_name = 'manufacturing/production_reports/dashboard.html'
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الحصول على معلمات الفلترة
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        from_statuses = self.request.GET.getlist('from_status')  # دعم الاختيار المتعدد
        to_statuses = self.request.GET.getlist('to_status')  # دعم الاختيار المتعدد
        production_line_ids = self.request.GET.getlist('production_line')  # دعم الاختيار المتعدد
        order_types = self.request.GET.getlist('order_type')  # دعم الاختيار المتعدد
        order_statuses = self.request.GET.getlist('order_status')  # فلتر جديد

        # تعيين التواريخ الافتراضية (آخر 30 يوم)
        if not date_to:
            date_to = timezone.now().date()
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        if not date_from:
            date_from = date_to - timedelta(days=30)
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

        # بناء الاستعلام الأساسي - جميع أوامر التصنيع في الفترة المحددة
        manufacturing_orders = ManufacturingOrder.objects.filter(
            order__order_date__date__gte=date_from,
            order__order_date__date__lte=date_to
        )

        # تطبيق الفلاتر على أوامر التصنيع
        if production_line_ids:
            manufacturing_orders = manufacturing_orders.filter(production_line_id__in=production_line_ids)
        if order_types:
            manufacturing_orders = manufacturing_orders.filter(order_type__in=order_types)
        if order_statuses:
            manufacturing_orders = manufacturing_orders.filter(order__status__in=order_statuses)

        # فلترة حسب الحالة الحالية (to_statuses) - هذا هو الأهم!
        if to_statuses:
            manufacturing_orders = manufacturing_orders.filter(status__in=to_statuses)

        # الحصول على سجلات التحولات لهذه الأوامر
        status_logs = ManufacturingStatusLog.objects.filter(
            manufacturing_order__in=manufacturing_orders
        )

        # فلترة حسب الحالة السابقة إذا تم تحديدها
        if from_statuses:
            status_logs = status_logs.filter(previous_status__in=from_statuses)

        # تطبيق منطق عدم التكرار - الحصول على آخر سجل لكل أمر تصنيع
        status_logs = get_latest_status_logs(status_logs)
        
        # إحصائيات عامة
        total_transitions = status_logs.count()
        unique_orders = status_logs.values('manufacturing_order').distinct().count()
        
        # حساب إجمالي الأمتار للطلبات في الفترة المحددة
        orders_in_period = ManufacturingOrder.objects.filter(
            id__in=status_logs.values_list('manufacturing_order_id', flat=True)
        )

        total_meters = 0
        for order in orders_in_period:
            # حساب الأمتار من عناصر الطلب الأصلي
            if order.order:
                items_meters = order.order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0
            else:
                items_meters = order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0
            total_meters += float(items_meters)
        
        # توزيع التحولات حسب الحالة (مع تطبيع الحالات المكتملة)
        status_dist_data = {}
        for log in status_logs:
            normalized_status = normalize_status(log.new_status)
            status_name = 'مكتمل الإنتاج' if normalized_status == 'completed_production' else log.get_new_status_display()
            status_dist_data[status_name] = status_dist_data.get(status_name, 0) + 1

        status_distribution = [
            {'new_status': name, 'count': count}
            for name, count in sorted(status_dist_data.items(), key=lambda x: x[1], reverse=True)
        ]

        # التحولات اليومية
        daily_transitions = status_logs.annotate(
            date=TruncDate('changed_at')
        ).values('date').annotate(
            count=Count('manufacturing_order', distinct=True)
        ).order_by('date')
        
        # المستخدمون الأكثر نشاطاً
        top_users = status_logs.filter(
            changed_by__isnull=False
        ).values(
            'changed_by__username',
            'changed_by__first_name',
            'changed_by__last_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # خطوط الإنتاج
        production_lines = ProductionLine.objects.all()
        
        # خيارات الحالات
        status_choices = ManufacturingOrder.STATUS_CHOICES
        order_type_choices = ManufacturingOrder.ORDER_TYPE_CHOICES
        
        # إضافة بيانات الجدول مع الأمتار
        table_data = []
        for log in status_logs.select_related(
            'manufacturing_order',
            'manufacturing_order__order',
            'manufacturing_order__order__customer',
            'manufacturing_order__production_line'
        ).order_by('-changed_at')[:100]:  # أول 100 سجل للعرض
            order = log.manufacturing_order
            # حساب الأمتار من الطلب الأصلي
            if order.order:
                meters = order.order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0
            else:
                meters = order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0

            table_data.append({
                'log': log,
                'order_number': order.order.order_number if order.order else '-',
                'customer_name': order.order.customer.name if order.order and order.order.customer else '-',
                'contract_number': order.contract_number or '-',
                'meters': float(meters),
                'order_date': order.order.order_date if order.order else None,
                'order_type': order.order_type,
                'order_type_display': order.get_order_type_display(),
            })

        # استيراد Order.ORDER_STATUS_CHOICES
        from orders.models import Order

        context.update({
            'date_from': date_from,
            'date_to': date_to,
            'from_statuses': from_statuses,
            'to_statuses': to_statuses,
            'production_line_ids': production_line_ids,
            'order_types': order_types,
            'order_statuses': order_statuses,
            'total_transitions': total_transitions,
            'unique_orders': unique_orders,
            'total_meters': round(total_meters, 2),
            'status_distribution': status_distribution,
            'daily_transitions': list(daily_transitions),
            'top_users': list(top_users),
            'production_lines': production_lines,
            'status_choices': status_choices,
            'order_type_choices': order_type_choices,
            'order_status_choices': Order.STATUS_CHOICES,  # عادي أو VIP
            'table_data': table_data,
        })
        
        return context


class ProductionReportDetailView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    عرض تفصيلي لتقرير الإنتاج
    Detailed Production Report View
    """
    model = ManufacturingStatusLog
    template_name = 'manufacturing/production_reports/detail.html'
    context_object_name = 'status_logs'
    permission_required = 'manufacturing.view_manufacturingorder'
    paginate_by = 50
    
    def get_queryset(self):
        # الحصول على معلمات الفلترة
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        from_statuses = self.request.GET.getlist('from_status')
        to_statuses = self.request.GET.getlist('to_status')
        production_line_ids = self.request.GET.getlist('production_line')
        order_types = self.request.GET.getlist('order_type')
        order_statuses = self.request.GET.getlist('order_status')

        # بناء الاستعلام الأساسي - جميع أوامر التصنيع
        manufacturing_orders = ManufacturingOrder.objects.all()

        # تطبيق فلاتر التاريخ
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            manufacturing_orders = manufacturing_orders.filter(order__order_date__date__gte=date_from_obj)

        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            manufacturing_orders = manufacturing_orders.filter(order__order_date__date__lte=date_to_obj)

        # تطبيق الفلاتر على أوامر التصنيع
        if production_line_ids:
            manufacturing_orders = manufacturing_orders.filter(production_line_id__in=production_line_ids)

        if order_types:
            manufacturing_orders = manufacturing_orders.filter(order_type__in=order_types)

        if order_statuses:
            manufacturing_orders = manufacturing_orders.filter(order__status__in=order_statuses)

        # فلترة حسب الحالة الحالية (to_statuses) - هذا هو الأهم!
        if to_statuses:
            manufacturing_orders = manufacturing_orders.filter(status__in=to_statuses)

        # الحصول على سجلات التحولات لهذه الأوامر
        queryset = ManufacturingStatusLog.objects.filter(
            manufacturing_order__in=manufacturing_orders
        )

        # فلترة حسب الحالة السابقة إذا تم تحديدها
        if from_statuses:
            queryset = queryset.filter(previous_status__in=from_statuses)

        # تطبيق منطق عدم التكرار
        queryset = get_latest_status_logs(queryset)

        return queryset.select_related(
            'manufacturing_order',
            'manufacturing_order__order',
            'manufacturing_order__order__customer',
            'manufacturing_order__production_line',
            'changed_by'
        ).order_by('-changed_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إضافة معلمات الفلترة للسياق
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['from_statuses'] = self.request.GET.getlist('from_status')
        context['to_statuses'] = self.request.GET.getlist('to_status')
        context['production_line_ids'] = self.request.GET.getlist('production_line')
        context['order_types'] = self.request.GET.getlist('order_type')
        context['order_statuses'] = self.request.GET.getlist('order_status')

        # خيارات الحالات
        from orders.models import Order
        context['status_choices'] = ManufacturingOrder.STATUS_CHOICES
        context['order_type_choices'] = ManufacturingOrder.ORDER_TYPE_CHOICES
        context['order_status_choices'] = Order.STATUS_CHOICES  # عادي أو VIP
        context['production_lines'] = ProductionLine.objects.all()

        # إضافة بيانات الأمتار لكل سجل
        table_data = []
        unique_order_ids = set()

        for log in context['status_logs']:
            order = log.manufacturing_order
            unique_order_ids.add(order.id)

            # حساب الأمتار من الطلب الأصلي
            if order.order:
                meters = order.order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0
            else:
                meters = order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0

            table_data.append({
                'log': log,
                'order_number': order.order.order_number if order.order else '-',
                'customer_name': order.order.customer.name if order.order and order.order.customer else '-',
                'contract_number': order.contract_number or '-',
                'meters': float(meters),
                'order_date': order.order.order_date if order.order else None,
                'order_type': order.order_type,
                'order_type_display': order.get_order_type_display(),
            })

        context['table_data'] = table_data
        context['total_orders'] = len(unique_order_ids)  # إضافة عدد الطلبات الفريدة

        return context


class DailyProductionTrackingView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    تتبع الإنتاج اليومي
    Daily Production Tracking
    """
    template_name = 'manufacturing/production_reports/daily_tracking.html'
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الحصول على التاريخ المحدد أو اليوم الحالي
        selected_date = self.request.GET.get('date')
        if selected_date:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            selected_date = timezone.now().date()
        
        # الحصول على جميع التحولات في هذا اليوم
        daily_logs = ManufacturingStatusLog.objects.filter(
            changed_at__date=selected_date
        ).select_related(
            'manufacturing_order',
            'manufacturing_order__order',
            'manufacturing_order__order__customer',
            'manufacturing_order__production_line',
            'changed_by'
        ).order_by('changed_at')

        # إحصائيات اليوم
        total_transitions = daily_logs.count()
        completed_today = daily_logs.filter(new_status='completed').count()
        in_progress_today = daily_logs.filter(new_status='in_progress').count()
        delivered_today = daily_logs.filter(new_status='delivered').count()

        # توزيع حسب خط الإنتاج
        by_production_line = daily_logs.values(
            'manufacturing_order__production_line__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        # توزيع حسب نوع الطلب
        by_order_type = daily_logs.values(
            'manufacturing_order__order_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        # إضافة عرض نوع الطلب
        for item in by_order_type:
            order_type_value = item['manufacturing_order__order_type']
            if order_type_value:
                item['order_type_display'] = dict(ManufacturingOrder.ORDER_TYPE_CHOICES).get(
                    order_type_value,
                    order_type_value
                )
            else:
                item['order_type_display'] = 'غير محدد'
        
        context.update({
            'selected_date': selected_date,
            'daily_logs': daily_logs,
            'total_transitions': total_transitions,
            'completed_today': completed_today,
            'in_progress_today': in_progress_today,
            'delivered_today': delivered_today,
            'by_production_line': list(by_production_line),
            'by_order_type': list(by_order_type),
        })

        return context


@login_required
@permission_required('manufacturing.view_manufacturingorder', raise_exception=True)
def export_production_report_excel(request):
    """
    تصدير تقرير الإنتاج إلى Excel
    Export Production Report to Excel
    """
    try:
        import xlsxwriter
        from io import BytesIO

        # الحصول على معلمات الفلترة
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        from_statuses = request.GET.getlist('from_status')  # دعم الاختيار المتعدد
        to_statuses = request.GET.getlist('to_status')  # دعم الاختيار المتعدد
        production_line_ids = request.GET.getlist('production_line')  # دعم الاختيار المتعدد
        order_types = request.GET.getlist('order_type')  # دعم الاختيار المتعدد
        order_statuses = request.GET.getlist('order_status')  # فلتر جديد

        # تعيين التواريخ الافتراضية
        if not date_to:
            date_to = timezone.now().date()
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        if not date_from:
            date_from = date_to - timedelta(days=30)
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()

        # بناء الاستعلام الأساسي - جميع أوامر التصنيع في الفترة المحددة
        manufacturing_orders = ManufacturingOrder.objects.filter(
            order__order_date__date__gte=date_from,
            order__order_date__date__lte=date_to
        )

        # تطبيق الفلاتر على أوامر التصنيع
        if production_line_ids:
            manufacturing_orders = manufacturing_orders.filter(production_line_id__in=production_line_ids)
        if order_types:
            manufacturing_orders = manufacturing_orders.filter(order_type__in=order_types)
        if order_statuses:
            manufacturing_orders = manufacturing_orders.filter(order__status__in=order_statuses)

        # فلترة حسب الحالة الحالية (to_statuses) - هذا هو الأهم!
        if to_statuses:
            manufacturing_orders = manufacturing_orders.filter(status__in=to_statuses)

        # الحصول على سجلات التحولات لهذه الأوامر
        status_logs = ManufacturingStatusLog.objects.filter(
            manufacturing_order__in=manufacturing_orders
        ).select_related(
            'manufacturing_order',
            'manufacturing_order__order',
            'manufacturing_order__order__customer',
            'manufacturing_order__order__branch',
            'manufacturing_order__production_line',
            'changed_by'
        ).order_by('-changed_at')

        # فلترة حسب الحالة السابقة إذا تم تحديدها
        if from_statuses:
            status_logs = status_logs.filter(previous_status__in=from_statuses)

        # تطبيق منطق عدم التكرار
        status_logs = get_latest_status_logs(status_logs)

        # إنشاء ملف Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('تقرير الإنتاج')

        # تنسيق العناوين
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4B0082',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        # تنسيق البيانات
        data_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })

        # تنسيق التاريخ
        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': 'yyyy-mm-dd hh:mm'
        })

        # تنسيق البطاقة الإحصائية
        summary_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 2,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14
        })

        # حساب إجمالي الأمتار
        total_meters_sum = 0
        for log in status_logs:
            order = log.manufacturing_order
            # حساب الأمتار من الطلب الأصلي
            if order.order:
                meters = order.order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0
            else:
                meters = order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0
            total_meters_sum += float(meters)

        # كتابة بطاقة إجمالي الأمتار في الأعلى
        worksheet.merge_range('A1:G1', f'إجمالي الأمتار في التقرير: {total_meters_sum:.2f} متر', summary_format)

        # العناوين الجديدة
        headers = [
            'رقم الطلب',
            'اسم العميل',
            'رقم العقد',
            'تاريخ الطلب',
            'الأمتار',
            'الحالة السابقة',
            'الحالة الحالية'
        ]

        # كتابة العناوين في الصف الثاني
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, header_format)

        # كتابة البيانات
        for row, log in enumerate(status_logs, start=3):
            order = log.manufacturing_order
            main_order = order.order if order else None
            customer = main_order.customer if main_order else None

            # حساب الأمتار من الطلب الأصلي
            if main_order:
                meters = main_order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0
            else:
                meters = order.items.aggregate(
                    total=Sum('quantity', output_field=DecimalField())
                )['total'] or 0

            data = [
                main_order.order_number if main_order else '-',
                customer.name if customer else '-',
                order.contract_number if order else '-',
                main_order.order_date.strftime('%Y-%m-%d') if main_order and main_order.order_date else '-',
                float(meters),
                log.get_previous_status_display(),
                log.get_new_status_display()
            ]

            for col, value in enumerate(data):
                worksheet.write(row, col, value, data_format)

        # تعديل عرض الأعمدة
        worksheet.set_column('A:A', 15)  # رقم الطلب
        worksheet.set_column('B:B', 25)  # اسم العميل
        worksheet.set_column('C:C', 15)  # رقم العقد
        worksheet.set_column('D:D', 12)  # الأمتار
        worksheet.set_column('E:E', 18)  # الحالة السابقة
        worksheet.set_column('F:F', 18)  # الحالة الحالية

        workbook.close()
        output.seek(0)

        # إنشاء الاستجابة
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'production_report_{date_from}_{date_to}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f'خطأ في تصدير Excel: {str(e)}')
        return JsonResponse({
            'error': 'حدث خطأ أثناء إنشاء ملف Excel',
            'details': str(e)
        }, status=500)

