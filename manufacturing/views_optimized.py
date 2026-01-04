from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from core.mixins import PaginationFixMixin, FilteredListViewMixin
from .models import ManufacturingOrder
from .filters import ManufacturingOrderFilter
from accounts.models import Branch
from core.monthly_filter_utils import apply_monthly_filter, get_available_years
import logging

logger = logging.getLogger(__name__)


class ManufacturingOrderListViewOptimized(
    FilteredListViewMixin,
    PaginationFixMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView
):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_list.html'
    context_object_name = 'manufacturing_orders'
    paginate_by = 25
    permission_required = 'manufacturing.view_manufacturingorder'
    allow_empty = True
    paginate_orphans = 0
    filterset_class = ManufacturingOrderFilter
    
    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty())
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(page)
        except ValueError:
            page_number = 1
        
        if page_number > paginator.num_pages and paginator.num_pages > 0:
            page_number = paginator.num_pages
        elif page_number < 1:
            page_number = 1
            
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list, page.has_other_pages())
        except Exception:
            page = paginator.page(1)
            return (paginator, page, page.object_list, page.has_other_pages())
    
    def get_paginate_by(self, queryset):
        try:
            page_size_str = self.request.GET.get('page_size', '25')
            if isinstance(page_size_str, list):
                page_size_str = page_size_str[0] if page_size_str else '25'
            page_size = int(page_size_str)
            if page_size > 100:
                page_size = 100
            elif page_size < 1:
                page_size = 25
            return page_size
        except Exception:
            return 25
    
    def get_queryset(self):
        queryset = ManufacturingOrder.objects.select_related(
            'order',
            'order__customer',
            'order__branch',
            'order__salesperson',
            'production_line'
        ).order_by('expected_delivery_date', 'order_date')
        
        queryset = queryset.exclude(order__selected_types__contains=['products'])
        
        queryset, self.monthly_filter_context = apply_monthly_filter(
            queryset, self.request, 'order_date'
        )
        
        queryset = self.apply_display_settings_filter(queryset)
        
        sort_column = self.request.GET.get('sort')
        sort_direction = self.request.GET.get('direction', 'asc')
        
        if sort_column and sort_direction != 'none':
            sort_field = self.get_sort_field(sort_column)
            if sort_field:
                if sort_direction == 'desc':
                    sort_field = f'-{sort_field}'
                queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_sort_field(self, sort_column):
        sort_fields = {
            'id': 'id',
            'order_number': 'order__order_number',
            'order_type': 'order_type',
            'contract_number': 'contract_number',
            'production_line': 'production_line__name',
            'invoice_number': 'invoice_number',
            'customer': 'order__customer__name',
            'salesperson': 'order__salesperson__name',
            'branch': 'order__branch__name',
            'order_date': 'order_date',
            'expected_delivery_date': 'expected_delivery_date',
            'status': 'status',
        }
        return sort_fields.get(sort_column)
    
    def apply_display_settings_filter(self, queryset):
        try:
            from .models import ManufacturingDisplaySettings

            manual_filters = self.has_manual_filters()

            if manual_filters:
                return queryset

            display_settings = ManufacturingDisplaySettings.get_user_settings(self.request.user)

            if display_settings:
                if display_settings.allowed_statuses:
                    queryset = queryset.filter(status__in=display_settings.allowed_statuses)

                if display_settings.allowed_order_types:
                    queryset = queryset.filter(order_type__in=display_settings.allowed_order_types)

            return queryset
        except Exception as e:
            logger.warning(f"خطأ في تطبيق إعدادات العرض: {e}")
            return queryset

    def has_manual_filters(self):
        filter_params = [
            'status', 'order_type', 'search', 'date_from', 'date_to',
            'customer', 'salesperson', 'branch', 'production_line',
            'contract_number', 'invoice_number',
        ]
        
        for param in filter_params:
            if self.request.GET.get(param):
                return True
        
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import ManufacturingDisplaySettings, ProductionLine
        
        filtered_orders = ManufacturingOrder.objects.select_related('order', 'order__customer')
        
        from accounts.utils import apply_default_year_filter
        filtered_orders = apply_default_year_filter(filtered_orders, self.request, 'order_date')
        
        context.update({
            'status_choices': dict(ManufacturingOrder.STATUS_CHOICES),
            'order_types': dict(ManufacturingOrder.ORDER_TYPE_CHOICES),
        })
        
        context.update({
            'status_filters': self.request.GET.getlist('status'),
            'branch_filters': self.request.GET.getlist('branch'),
            'order_type_filters': self.request.GET.getlist('order_type'),
            'production_line_filters': self.request.GET.getlist('production_line'),
            'overdue_filter': self.request.GET.get('overdue', ''),
            'search_query': self.request.GET.get('search', ''),
            'search_columns': self.request.GET.getlist('search_columns'),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'page_size': self.request.GET.get('page_size', 25),
        })
        
        context.update({
            'branches': Branch.objects.filter(is_active=True).order_by('name'),
            'production_lines': ProductionLine.objects.filter(is_active=True).order_by('name'),
            'order_types': ManufacturingOrder.ORDER_TYPE_CHOICES,
        })
        
        try:
            context['available_display_settings'] = ManufacturingDisplaySettings.objects.filter(
                is_active=True
            ).order_by('-priority', 'name')
        except Exception:
            context['available_display_settings'] = []
        
        context['production_lines'] = ProductionLine.objects.filter(is_active=True).order_by('-priority', 'name')
        
        context['order_types'] = [
            ('installation', 'تركيب'),
            ('custom', 'تفصيل'),
            ('accessory', 'إكسسوار'),
            ('delivery', 'تسليم'),
        ]
        
        context.update(self.monthly_filter_context)
        
        context['available_years'] = get_available_years(ManufacturingOrder, 'order_date')
        
        return context
