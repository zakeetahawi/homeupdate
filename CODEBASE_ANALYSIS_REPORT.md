# Codebase Analysis Report

## Summary

- Total Files Analyzed: 432
- Files with Issues: 359
- Total Unused Imports: 516
- Total Unused Functions: 2336
- Total Unused Classes: 557
- Total Query Optimization Issues: 1423

## Detailed Findings

### inventory/views_optimized.py

#### Unused Imports (15)

- Line 1: `render` (from `django.shortcuts.render`)
- Line 1: `redirect` (from `django.shortcuts.redirect`)
- Line 1: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)
- Line 2: `login_required` (from `django.contrib.auth.decorators.login_required`)
- Line 3: `messages` (from `django.contrib.messages`)
- Line 6: `Paginator` (from `django.core.paginator.Paginator`)
- Line 7: `Q` (from `django.db.models.Q`)
- Line 7: `Case` (from `django.db.models.Case`)
- Line 7: `When` (from `django.db.models.When`)
- Line 9: `datetime` (from `datetime.datetime`)
- Line 11: `ProductForm` (from `forms.ProductForm`)
- Line 12: `get_cached_stock_level` (from `inventory_utils.get_cached_stock_level`)
- Line 12: `get_cached_product_list` (from `inventory_utils.get_cached_product_list`)
- Line 12: `invalidate_product_cache` (from `inventory_utils.invalidate_product_cache`)
- Line 18: `SystemSettings` (from `accounts.models.SystemSettings`)

#### Unused Functions (1)

- Line 23: `get_context_data()`

#### Unused Classes (1)

- Line 20: `InventoryDashboardView`

#### Query Optimization Opportunities (3)

- Line 71: missing_select_related
  ```python
  ).filter(product_count__gt=0)[:10]
  ```
- Line 54: potential_n_plus_one
  ```python
  for p in low_stock_products
  ```
- Line 78: potential_n_plus_one
  ```python
  for cat in category_stats
  ```

### manufacturing/views.py

#### Unused Imports (14)

- Line 11: `render` (from `django.shortcuts.render`)
- Line 13: `HttpResponseForbidden` (from `django.http.HttpResponseForbidden`)
- Line 13: `HttpResponseBadRequest` (from `django.http.HttpResponseBadRequest`)
- Line 14: `UpdateView` (from `django.views.generic.UpdateView`)
- Line 18: `F` (from `django.db.models.F`)
- Line 18: `Case` (from `django.db.models.Case`)
- Line 18: `When` (from `django.db.models.When`)
- Line 18: `Value` (from `django.db.models.Value`)
- Line 18: `IntegerField` (from `django.db.models.IntegerField`)
- Line 24: `Paginator` (from `django.core.paginator.Paginator`)
- Line 25: `TruncDay` (from `django.db.models.functions.TruncDay`)
- Line 25: `TruncMonth` (from `django.db.models.functions.TruncMonth`)
- Line 43: `Department` (from `accounts.models.Department`)
- Line 1219: `io` (from `io`)

#### Unused Functions (42)

- Line 58: `paginate_queryset()`
- Line 84: `get_paginate_by()`
- Line 2980: `get_queryset()`
- Line 1072: `get_sort_field()`
- Line 273: `apply_display_settings_filter()`
- Line 303: `has_manual_filters()`
- Line 3473: `get_context_data()`
- Line 485: `_get_available_statuses()`
- Line 872: `get_success_url()`
- Line 876: `form_valid()`
- Line 886: `post()`
- Line 957: `get_production_lines_api()`
- Line 1208: `setup()`
- Line 1268: `get()`
- Line 1281: `generate_pdf()`
- Line 1318: `delete()`
- Line 1381: `update_order_status()`
- Line 1621: `update_exit_permit()`
- Line 1646: `create_from_order()`
- Line 1688: `print_manufacturing_order()`
- Line 1801: `dashboard_data()`
- Line 1843: `update_approval_status()`
- Line 1978: `get_order_details()`
- Line 2032: `send_reply()`
- Line 2152: `re_approve_after_reply()`
- Line 2245: `manufacturing_order_detail_by_code()`
- Line 2265: `manufacturing_order_detail_redirect()`
- Line 2381: `receive_fabric_item()`
- Line 2450: `get_bag_number_data()`
- Line 2469: `bulk_receive_fabric()`
- Line 2516: `fabric_receipt_status_api()`
- Line 2629: `receive_cutting_order_for_manufacturing()`
- Line 2705: `get_cutting_order_data()`
- Line 2748: `receive_all_fabric_items()`
- Line 2802: `recent_fabric_receipts()`
- Line 2835: `receive_cutting_order()`
- Line 2952: `get_object()`
- Line 3128: `cleanup_products_manufacturing_orders()`
- Line 3156: `fix_manufacturing_order_items()`
- Line 3198: `create_manufacturing_receipt()`
- Line 3267: `get_cutting_data()`
- Line 3398: `create_product_receipt()`

#### Unused Classes (14)

- Line 49: `ManufacturingOrderListView`
- Line 573: `VIPOrdersListView`
- Line 864: `ManufacturingOrderCreateView`
- Line 882: `ChangeProductionLineView`
- Line 1205: `ProductionLinePDFView`
- Line 1312: `ManufacturingOrderDeleteView`
- Line 1714: `DashboardView`
- Line 2271: `OverdueOrdersListView`
- Line 2563: `FabricReceiptView`
- Line 2946: `FabricReceiptDetailView`
- Line 2974: `FabricReceiptListView`
- Line 3302: `ProductReceiptView`
- Line 3357: `ProductReceiptsListView`
- Line 3462: `ManufacturingItemStatusReportView`

#### Query Optimization Opportunities (65)

- Line 121: missing_select_related
  ```python
  queryset = queryset.filter(status__in=status_filters)
  ```
- Line 143: missing_select_related
  ```python
  queryset = queryset.filter(order_type__in=order_type_filters)
  ```
- Line 225: missing_select_related
  ```python
  queryset = queryset.filter(order_date__gte=date_from)
  ```
- Line 234: missing_select_related
  ```python
  queryset = queryset.filter(order_date__lt=end_date)
  ```
- Line 291: missing_select_related
  ```python
  queryset = queryset.filter(status__in=display_settings.allowed_statuses)
  ```
- Line 295: missing_select_related
  ```python
  queryset = queryset.filter(order_type__in=display_settings.allowed_order_types)
  ```
- Line 626: missing_select_related
  ```python
  queryset = queryset.filter(status__in=display_setting.allowed_statuses)
  ```
- Line 630: missing_select_related
  ```python
  queryset = queryset.filter(order_type__in=display_setting.allowed_order_types)
  ```
- Line 1025: missing_select_related
  ```python
  queryset = queryset.filter(status__in=status_filters)
  ```
- Line 1043: missing_select_related
  ```python
  queryset = queryset.filter(order_type__in=order_type_filters)
  ```
- Line 1058: missing_select_related
  ```python
  queryset = queryset.filter(order_date__gte=date_from)
  ```
- Line 1066: missing_select_related
  ```python
  queryset = queryset.filter(order_date__lt=end_date)
  ```
- Line 1792: missing_select_related
  ```python
  'completed_orders': orders.filter(status__in=['ready_install', 'completed']).cou
  ```
- Line 1828: missing_select_related
  ```python
  'completed_orders': orders.filter(status__in=['ready_install', 'completed']).cou
  ```
- Line 2304: missing_select_related
  ```python
  queryset = queryset.filter(order__branch__id=branch)
  ```
- Line 3010: missing_select_related
  ```python
  queryset = queryset.filter(fabric_received_date__date__gte=date_from)
  ```
- Line 3015: missing_select_related
  ```python
  queryset = queryset.filter(fabric_received_date__date__lte=date_to)
  ```
- Line 3020: missing_select_related
  ```python
  queryset = queryset.filter(manufacturing_order__order__customer_id=customer_id)
  ```
- Line 3025: missing_select_related
  ```python
  queryset = queryset.filter(manufacturing_order__order__customer__name__icontains
  ```
- Line 3030: missing_select_related
  ```python
  queryset = queryset.filter(product_name__icontains=product_name)
  ```
- Line 3040: missing_select_related
  ```python
  queryset = queryset.filter(permit_number__icontains=permit_number)
  ```
- Line 3045: missing_select_related
  ```python
  queryset = queryset.filter(receiver_name__icontains=receiver_name)
  ```
- Line 3057: missing_select_related
  ```python
  queryset = queryset.filter(manufacturing_order__order__order_number__icontains=s
  ```
- Line 3095: missing_select_related
  ```python
  id__in=ManufacturingOrderItem.objects.filter(
  ```
- Line 3160: missing_select_related
  ```python
  orders_without_items = ManufacturingOrder.objects.filter(items__isnull=True).dis
  ```
- Line 3331: missing_select_related
  ```python
  print(f"DEBUG: أوامر التقطيع المكتملة للمنتجات: {CuttingOrder.objects.filter(sta
  ```
- Line 3385: missing_select_related
  ```python
  today_receipts = receipts.filter(receipt_date__date=timezone.now().date()).count
  ```
- Line 118: potential_n_plus_one
  ```python
  status_filters = [f for f in status_filters if f and f.strip()]
  ```
- Line 129: potential_n_plus_one
  ```python
  for branch_id in branch_filters:
  ```
- Line 140: potential_n_plus_one
  ```python
  order_type_filters = [f for f in order_type_filters if f and f.strip()]
  ```
- Line 214: potential_n_plus_one
  ```python
  for col in search_columns:
  ```
- Line 321: potential_n_plus_one
  ```python
  for param in filter_params:
  ```
- Line 426: potential_n_plus_one
  ```python
  branch_map = {str(b.id): b.name for b in context.get('branches', [])}
  ```
- Line 442: potential_n_plus_one
  ```python
  context['status_filters_display'] = [status_choices_map.get(s, s) for s in conte
  ```
- Line 443: potential_n_plus_one
  ```python
  context['branch_filters_display'] = [branch_map.get(bid, bid) for bid in context
  ```
- Line 444: potential_n_plus_one
  ```python
  context['order_type_filters_display'] = [order_types_map.get(code, code) for cod
  ```
- Line 445: potential_n_plus_one
  ```python
  context['search_columns_display'] = [column_labels.get(col, col) for col in cont
  ```
- Line 645: potential_n_plus_one
  ```python
  for status_code, status_display in ManufacturingOrder.STATUS_CHOICES:
  ```
- Line 655: potential_n_plus_one
  ```python
  for type_code, type_display in ManufacturingOrder.ORDER_TYPE_CHOICES:
  ```
- Line 719: potential_n_plus_one
  ```python
  for order_item in order_items:
  ```
- Line 769: potential_n_plus_one
  ```python
  for cutting_item in cutting_items:
  ```
- Line 965: potential_n_plus_one
  ```python
  for line in lines:
  ```
- Line 1031: potential_n_plus_one
  ```python
  for branch_id in branch_filters:
  ```
- Line 1122: potential_n_plus_one
  ```python
  for order_type in self.production_line.supported_order_types:
  ```
- Line 1123: potential_n_plus_one
  ```python
  for choice_code, choice_name in ManufacturingOrder.ORDER_TYPE_CHOICES:
  ```
- Line 1672: potential_n_plus_one
  ```python
  for item in order.items.all():
  ```
- Line 1744: potential_n_plus_one
  ```python
  for status in status_counts:
  ```
- Line 1770: potential_n_plus_one
  ```python
  for item in monthly_orders:
  ```
- Line 1831: potential_n_plus_one
  ```python
  'status_data': {item['status']: item['count'] for item in status_counts},
  ```
- Line 2111: potential_n_plus_one
  ```python
  for user in approval_users:
  ```
- Line 2309: potential_n_plus_one
  ```python
  for order_type in order_types:
  ```
- Line 2333: potential_n_plus_one
  ```python
  status_data = {item['status']: item['count'] for item in status_counts}
  ```
- Line 2339: potential_n_plus_one
  ```python
  for order in overdue_orders:
  ```
- Line 2493: potential_n_plus_one
  ```python
  for item in items_to_receive:
  ```
- Line 2522: potential_n_plus_one
  ```python
  for item in manufacturing_order.items.all():
  ```
- Line 2611: potential_n_plus_one
  ```python
  for item in cutting_items:
  ```
- Line 2677: potential_n_plus_one
  ```python
  for item in ready_items:
  ```
- Line 2768: potential_n_plus_one
  ```python
  for item in ready_items:
  ```
- Line 2812: potential_n_plus_one
  ```python
  for item in recent_items:
  ```
- Line 2891: potential_n_plus_one
  ```python
  for cutting_item in cutting_order.items.all():
  ```
- Line 3163: potential_n_plus_one
  ```python
  for manufacturing_order in orders_without_items:
  ```
- Line 3171: potential_n_plus_one
  ```python
  for cutting_item in cutting_order.items.all():
  ```
- Line 3377: potential_n_plus_one
  ```python
  for receipt in receipts:
  ```
- Line 3495: potential_n_plus_one
  ```python
  for order in manufacturing_orders:
  ```
- Line 3510: potential_n_plus_one
  ```python
  for item in order.items.all():
  ```

### reports/views.py

#### Unused Imports (14)

- Line 7: `JsonResponse` (from `django.http.JsonResponse`)
- Line 536: `F` (from `django.db.models.F`)
- Line 8: `Window` (from `django.db.models.Window`)
- Line 9: `date` (from `datetime.date`)
- Line 13: `OrderItem` (from `orders.models.OrderItem`)
- Line 125: `Q` (from `django.db.models.Q`)
- Line 536: `Case` (from `django.db.models.Case`)
- Line 536: `When` (from `django.db.models.When`)
- Line 468: `IntegerField` (from `django.db.models.IntegerField`)
- Line 536: `StdDev` (from `django.db.models.StdDev`)
- Line 536: `FloatField` (from `django.db.models.FloatField`)
- Line 603: `TruncMonth` (from `django.db.models.functions.TruncMonth`)
- Line 537: `ExtractHour` (from `django.db.models.functions.ExtractHour`)
- Line 537: `ExtractWeekDay` (from `django.db.models.functions.ExtractWeekDay`)

#### Unused Functions (25)

- Line 26: `seller_customer_activity_view()`
- Line 53: `seller_customer_activity_export_csv()`
- Line 85: `seller_customer_activity_index()`
- Line 723: `get_context_data()`
- Line 165: `dispatch()`
- Line 740: `get_queryset()`
- Line 729: `form_valid()`
- Line 743: `delete()`
- Line 261: `get_template_names()`
- Line 314: `get_initial_report_data()`
- Line 333: `generate_seller_customer_activity_report()`
- Line 406: `generate_inspection_report()`
- Line 420: `generate_sales_report()`
- Line 443: `generate_production_report()`
- Line 462: `generate_inventory_report()`
- Line 510: `generate_financial_report()`
- Line 534: `generate_analytics_report()`
- Line 591: `calculate_fulfillment_rate()`
- Line 596: `calculate_inventory_turnover()`
- Line 601: `calculate_customer_retention()`
- Line 621: `calculate_avg_fulfillment_time()`
- Line 626: `calculate_profit_margin()`
- Line 631: `analyze_customer_segments()`
- Line 669: `save_report_result()`
- Line 747: `get_success_url()`

#### Unused Classes (8)

- Line 91: `ReportDashboardView`
- Line 159: `ReportListView`
- Line 176: `ReportCreateView`
- Line 204: `ReportUpdateView`
- Line 235: `ReportDeleteView`
- Line 695: `ReportScheduleCreateView`
- Line 715: `ReportScheduleUpdateView`
- Line 736: `ReportScheduleDeleteView`

#### Query Optimization Opportunities (26)

- Line 88: missing_select_related
  ```python
  reports_qs = Report.objects.filter(report_type__in=['seller_activity', 'seller_c
  ```
- Line 350: missing_select_related
  ```python
  users_qs = users_qs.filter(groups__name__icontains='seller')
  ```
- Line 366: missing_select_related
  ```python
  cust_qs = Customer.objects.filter(created_at__date__gte=start_date)
  ```
- Line 376: missing_select_related
  ```python
  ord_qs = Order.objects.filter(created_at__date__gte=start_date)
  ```
- Line 387: missing_select_related
  ```python
  ins_qs = Inspection.objects.filter(created_at__date__gte=start_date)
  ```
- Line 411: missing_select_related
  ```python
  inspections = Inspection.objects.filter(request_date__gte=start_date)
  ```
- Line 516: missing_select_related
  ```python
  payments = Payment.objects.filter(payment_date__gte=start_date)
  ```
- Line 517: missing_select_related
  ```python
  orders = Order.objects.filter(order_date__gte=start_date)
  ```
- Line 543: missing_select_related
  ```python
  orders = Order.objects.filter(created_at__gte=start_date)
  ```
- Line 34: potential_n_plus_one
  ```python
  for uid, data in raw_results.items():
  ```
- Line 35: potential_n_plus_one
  ```python
  daily_list = [data['daily'].get(d, 0) for d in date_list]
  ```
- Line 64: potential_n_plus_one
  ```python
  header = ['User'] + [d.strftime('%Y-%m-%d') for d in date_list] + ['Total']
  ```
- Line 67: potential_n_plus_one
  ```python
  for uid, data in results.items():
  ```
- Line 71: potential_n_plus_one
  ```python
  for d in date_list:
  ```
- Line 116: potential_n_plus_one
  ```python
  for report_type, label in report_types.items():
  ```
- Line 191: potential_n_plus_one
  ```python
  params['seller_roles'] = [int(r.pk) for r in roles]
  ```
- Line 224: potential_n_plus_one
  ```python
  params['seller_roles'] = [int(r.pk) for r in roles]
  ```
- Line 334: potential_n_plus_one
  ```python
  """Generate report: for sellers, how many customers they created per day in the 
  ```
- Line 353: potential_n_plus_one
  ```python
  date_list = [start_date + timedelta(days=i) for i in range(days)]
  ```
- Line 357: potential_n_plus_one
  ```python
  for u in users_qs.order_by('first_name', 'last_name'):
  ```
- Line 360: potential_n_plus_one
  ```python
  'daily': {d: 0 for d in date_list},
  ```
- Line 368: potential_n_plus_one
  ```python
  for row in cust_agg:
  ```
- Line 378: potential_n_plus_one
  ```python
  for row in ord_agg:
  ```
- Line 389: potential_n_plus_one
  ```python
  for row in ins_agg:
  ```
- Line 640: potential_n_plus_one
  ```python
  data = np.array([[c['total_spent'], c['order_count']] for c in customer_analysis
  ```
- Line 651: potential_n_plus_one
  ```python
  for i, customer in enumerate(customer_analysis):
  ```

### crm/dashboard_utils.py

#### Unused Imports (12)

- Line 6: `F` (from `django.db.models.F`)
- Line 6: `Max` (from `django.db.models.Max`)
- Line 7: `datetime` (from `datetime.datetime`)
- Line 14: `Branch` (from `accounts.models.Branch`)
- Line 14: `DashboardYearSettings` (from `accounts.models.DashboardYearSettings`)
- Line 15: `ComplaintType` (from `complaints.models.ComplaintType`)
- Line 17: `Avg` (from `django.db.models.Avg`)
- Line 17: `Case` (from `django.db.models.Case`)
- Line 17: `When` (from `django.db.models.When`)
- Line 17: `IntegerField` (from `django.db.models.IntegerField`)
- Line 17: `DurationField` (from `django.db.models.DurationField`)
- Line 18: `Extract` (from `django.db.models.functions.Extract`)

#### Unused Functions (16)

- Line 21: `get_customers_statistics()`
- Line 69: `get_orders_statistics()`
- Line 119: `get_manufacturing_statistics()`
- Line 161: `get_inspections_statistics()`
- Line 198: `get_installation_orders_statistics()`
- Line 230: `get_installations_statistics()`
- Line 270: `get_inventory_statistics()`
- Line 305: `get_enhanced_chart_data()`
- Line 315: `get_single_year_chart_data()`
- Line 362: `get_multi_year_chart_data()`
- Line 429: `get_dashboard_summary()`
- Line 453: `get_complaints_statistics()`
- Line 517: `calculate_resolution_rate()`
- Line 889: `get_user_performance_analytics()`
- Line 940: `get_user_activity_analytics()`
- Line 1024: `get_installation_order_scheduling_analytics()`

#### Query Optimization Opportunities (44)

- Line 29: missing_select_related
  ```python
  customers = customers.filter(created_at__range=(start_date, end_date))
  ```
- Line 48: missing_select_related
  ```python
  new_this_month = customers.filter(created_at__gte=current_month_start).count()
  ```
- Line 75: missing_select_related
  ```python
  orders = orders.filter(order_date__range=(start_date, end_date))
  ```
- Line 169: missing_select_related
  ```python
  inspections = inspections.filter(created_at__range=(start_date, end_date))
  ```
- Line 209: missing_select_related
  ```python
  orders = orders.filter(order_date__range=(start_date, end_date))
  ```
- Line 245: missing_select_related
  ```python
  installations = installations.filter(order__branch_id=branch_filter)
  ```
- Line 318: missing_select_related
  ```python
  orders_monthly = Order.objects.filter(order_date__year=year)
  ```
- Line 330: missing_select_related
  ```python
  customers_monthly = Customer.objects.filter(created_at__year=year)
  ```
- Line 342: missing_select_related
  ```python
  inspections_monthly = Inspection.objects.filter(created_at__year=year)
  ```
- Line 416: missing_select_related
  ```python
  current_count = queryset.filter(**{f"{date_field}__gte": current_month}).count()
  ```
- Line 461: missing_select_related
  ```python
  complaints = complaints.filter(created_at__range=(start_date, end_date))
  ```
- Line 484: missing_select_related
  ```python
  new_this_month = complaints.filter(created_at__gte=current_month_start).count()
  ```
- Line 503: missing_select_related
  ```python
  week_count = complaints.filter(created_at__range=(week_start, week_end)).count()
  ```
- Line 521: missing_select_related
  ```python
  resolved = complaints.filter(status__in=["resolved", "closed"]).count()
  ```
- Line 651: missing_select_related
  ```python
  inspections = inspections.filter(created_at__range=(start_date, end_date))
  ```
- Line 755: missing_select_related
  ```python
  "pending_scheduling": inspections.filter(scheduled_date__isnull=True).count(),
  ```
- Line 768: missing_select_related
  ```python
  inspections = inspections.filter(created_at__range=(start_date, end_date))
  ```
- Line 877: missing_select_related
  ```python
  "pending_scheduling": inspections.filter(scheduled_date__isnull=True).count(),
  ```
- Line 286: potential_n_plus_one
  ```python
  for product in Product.objects.filter(**products_filter)[:100]:  # عينة من 100 م
  ```
- Line 500: potential_n_plus_one
  ```python
  for i in range(4):
  ```
- Line 557: potential_n_plus_one
  ```python
  for order in completed_orders:
  ```
- Line 593: potential_n_plus_one
  ```python
  quick_approvals = len([t for t in approval_times if t <= 24])  # أقل من 24 ساعة
  ```
- Line 594: potential_n_plus_one
  ```python
  medium_approvals = len([t for t in approval_times if 24 < t <= 72])  # 1-3 أيام
  ```
- Line 595: potential_n_plus_one
  ```python
  slow_approvals = len([t for t in approval_times if t > 72])  # أكثر من 3 أيام
  ```
- Line 599: potential_n_plus_one
  ```python
  for order in completed_orders:
  ```
- Line 619: potential_n_plus_one
  ```python
  for user_data in approval_by_user.values():
  ```
- Line 662: potential_n_plus_one
  ```python
  for inspection in scheduled_inspections:
  ```
- Line 708: potential_n_plus_one
  ```python
  quick_scheduling = len([t for t in scheduling_times if t <= 24])  # أقل من 24 سا
  ```
- Line 709: potential_n_plus_one
  ```python
  medium_scheduling = len([t for t in scheduling_times if 24 < t <= 72])  # 1-3 أي
  ```
- Line 710: potential_n_plus_one
  ```python
  slow_scheduling = len([t for t in scheduling_times if t > 72])  # أكثر من 3 أيام
  ```
- Line 714: potential_n_plus_one
  ```python
  for inspection in scheduled_inspections:
  ```
- Line 745: potential_n_plus_one
  ```python
  for user_data in scheduling_by_user.values():
  ```
- Line 779: potential_n_plus_one
  ```python
  for inspection in scheduled_inspections:
  ```
- Line 827: potential_n_plus_one
  ```python
  quick_scheduling = len([t for t in scheduling_times if t <= 24])  # أقل من 24 سا
  ```
- Line 828: potential_n_plus_one
  ```python
  medium_scheduling = len([t for t in scheduling_times if 24 < t <= 72])  # 1-3 أي
  ```
- Line 829: potential_n_plus_one
  ```python
  slow_scheduling = len([t for t in scheduling_times if t > 72])  # أكثر من 3 أيام
  ```
- Line 833: potential_n_plus_one
  ```python
  for inspection in scheduled_inspections:
  ```
- Line 867: potential_n_plus_one
  ```python
  for user_data in scheduling_by_user.values():
  ```
- Line 908: potential_n_plus_one
  ```python
  for user_name in all_users:
  ```
- Line 961: potential_n_plus_one
  ```python
  for user in all_users:
  ```
- Line 1049: potential_n_plus_one
  ```python
  for order in installation_orders:
  ```
- Line 1107: potential_n_plus_one
  ```python
  quick_scheduling = len([t for t in scheduling_times if t <= 24])  # أقل من 24 سا
  ```
- Line 1108: potential_n_plus_one
  ```python
  medium_scheduling = len([t for t in scheduling_times if 24 < t <= 168])  # 1-7 أ
  ```
- Line 1109: potential_n_plus_one
  ```python
  slow_scheduling = len([t for t in scheduling_times if t > 168])  # أكثر من أسبوع
  ```

### crm/views_backup.py

#### Unused Imports (12)

- Line 6: `Count` (from `django.db.models.Count`)
- Line 6: `Sum` (from `django.db.models.Sum`)
- Line 6: `Q` (from `django.db.models.Q`)
- Line 9: `LoginRequiredMixin` (from `django.contrib.auth.mixins.LoginRequiredMixin`)
- Line 9: `UserPassesTestMixin` (from `django.contrib.auth.mixins.UserPassesTestMixin`)
- Line 10: `TemplateView` (from `django.views.generic.TemplateView`)
- Line 18: `ContactFormSettings` (from `accounts.models.ContactFormSettings`)
- Line 18: `FooterSettings` (from `accounts.models.FooterSettings`)
- Line 19: `ManufacturingOrderItem` (from `manufacturing.models.ManufacturingOrderItem`)
- Line 20: `InstallationSchedule` (from `installations.models.InstallationSchedule`)
- Line 23: `JsonResponse` (from `django.http.JsonResponse`)
- Line 25: `HttpResponse` (from `django.http.HttpResponse`)

#### Unused Functions (14)

- Line 31: `is_admin_user()`
- Line 193: `admin_dashboard()`
- Line 289: `get_date_range()`
- Line 308: `get_comprehensive_statistics()`
- Line 327: `get_comparison_data()`
- Line 358: `get_or_create_company_info()`
- Line 371: `get_filter_data()`
- Line 413: `get_performance_metrics()`
- Line 443: `home()`
- Line 496: `about()`
- Line 520: `contact()`
- Line 552: `serve_media_file()`
- Line 589: `data_management_redirect()`
- Line 597: `dashboard_api()`

#### Query Optimization Opportunities (6)

- Line 615: missing_select_related
  ```python
  'low_stock': Product.objects.filter(current_stock__lte=F('minimum_stock')).count
  ```
- Line 619: missing_select_related
  ```python
  'completed_today': ManufacturingOrder.objects.filter(completed_at__date=today).c
  ```
- Line 391: potential_n_plus_one
  ```python
  all_years.update([date.year for date in order_years])
  ```
- Line 394: potential_n_plus_one
  ```python
  all_years.update([date.year for date in customer_years])
  ```
- Line 397: potential_n_plus_one
  ```python
  all_years.update([date.year for date in inspection_years])
  ```
- Line 467: potential_n_plus_one
  ```python
  product for product in Product.objects.all()
  ```

### crm/views.py

#### Unused Imports (11)

- Line 8: `Count` (from `django.db.models.Count`)
- Line 8: `Sum` (from `django.db.models.Sum`)
- Line 8: `Q` (from `django.db.models.Q`)
- Line 11: `LoginRequiredMixin` (from `django.contrib.auth.mixins.LoginRequiredMixin`)
- Line 11: `UserPassesTestMixin` (from `django.contrib.auth.mixins.UserPassesTestMixin`)
- Line 13: `TemplateView` (from `django.views.generic.TemplateView`)
- Line 21: `ContactFormSettings` (from `accounts.models.ContactFormSettings`)
- Line 21: `FooterSettings` (from `accounts.models.FooterSettings`)
- Line 28: `ManufacturingOrderItem` (from `manufacturing.models.ManufacturingOrderItem`)
- Line 29: `InstallationSchedule` (from `installations.models.InstallationSchedule`)
- Line 32: `JsonResponse` (from `django.http.JsonResponse`)

#### Unused Functions (18)

- Line 41: `is_admin_user()`
- Line 48: `admin_dashboard()`
- Line 269: `get_date_range()`
- Line 292: `get_comprehensive_statistics()`
- Line 331: `get_comparison_data()`
- Line 385: `get_or_create_company_info()`
- Line 398: `get_filter_data()`
- Line 447: `get_performance_metrics()`
- Line 484: `home()`
- Line 553: `about()`
- Line 578: `contact()`
- Line 612: `serve_media_file()`
- Line 650: `data_management_redirect()`
- Line 659: `dashboard_api()`
- Line 698: `monitoring_dashboard()`
- Line 708: `chat_gone_view()`
- Line 731: `test_minimal_view()`
- Line 754: `clear_cache_view()`

#### Query Optimization Opportunities (4)

- Line 522: missing_select_related
  ```python
  .filter(current_stock_level__gt=0, current_stock_level__lte=F("minimum_stock"))
  ```
- Line 425: potential_n_plus_one
  ```python
  all_years.update([date.year for date in order_years])
  ```
- Line 428: potential_n_plus_one
  ```python
  all_years.update([date.year for date in customer_years])
  ```
- Line 431: potential_n_plus_one
  ```python
  all_years.update([date.year for date in inspection_years])
  ```

### odoo_db_manager/advanced_sync_service_backup.py

#### Unused Imports (10)

- Line 7: `json` (from `json`)
- Line 8: `os` (from `os`)
- Line 9: `sys` (from `sys`)
- Line 12: `Tuple` (from `typing.Tuple`)
- Line 14: `transaction` (from `django.db.transaction`)
- Line 15: `ValidationError` (from `django.core.exceptions.ValidationError`)
- Line 16: `settings` (from `django.conf.settings`)
- Line 22: `CustomerCategory` (from `customers.models.CustomerCategory`)
- Line 24: `ExtendedOrder` (from `orders.extended_models.ExtendedOrder`)
- Line 27: `Branch` (from `accounts.models.Branch`)

#### Unused Functions (17)

- Line 35: `__init__()`
- Line 53: `sync_from_sheets()`
- Line 209: `sync_to_sheets()`
- Line 237: `_get_sheet_data()`
- Line 245: `_get_headers()`
- Line 256: `_map_row_data()`
- Line 276: `_process_customer()`
- Line 304: `_create_customer()`
- Line 329: `_update_customer()`
- Line 346: `_process_order()`
- Line 371: `_create_order()`
- Line 426: `_update_order()`
- Line 464: `_process_inspection()`
- Line 508: `_process_installation()`
- Line 540: `_create_conflict()`
- Line 555: `_get_system_data()`
- Line 558: `_update_sheets_data()`

#### Unused Classes (1)

- Line 562: `SyncScheduler`

#### Query Optimization Opportunities (4)

- Line 414: missing_select_related
  ```python
  salesperson = Salesperson.objects.filter(name__icontains=salesperson_name).first
  ```
- Line 92: potential_n_plus_one
  ```python
  for i, row_data in enumerate(data_rows):
  ```
- Line 263: potential_n_plus_one
  ```python
  for col_index, value in enumerate(row_data):
  ```
- Line 573: potential_n_plus_one
  ```python
  for schedule in due_schedules:
  ```

### odoo_db_manager/google_sync_views.py

#### Unused Imports (10)

- Line 9: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)
- Line 12: `HttpResponse` (from `django.http.HttpResponse`)
- Line 18: `ContentFile` (from `django.core.files.base.ContentFile`)
- Line 20: `sync_databases` (from `google_sync.sync_databases`)
- Line 20: `sync_users` (from `google_sync.sync_users`)
- Line 20: `sync_customers` (from `google_sync.sync_customers`)
- Line 20: `sync_orders` (from `google_sync.sync_orders`)
- Line 20: `sync_products` (from `google_sync.sync_products`)
- Line 20: `sync_inspections` (from `google_sync.sync_inspections`)
- Line 20: `sync_settings` (from `google_sync.sync_settings`)

#### Unused Functions (11)

- Line 34: `google_sync()`
- Line 79: `google_sync_config()`
- Line 108: `google_sync_config_save()`
- Line 145: `google_sync_delete_credentials()`
- Line 162: `google_sync_options()`
- Line 185: `google_sync_now()`
- Line 237: `google_sync_test()`
- Line 261: `google_sync_reset()`
- Line 281: `google_sync_advanced_settings()`
- Line 335: `reverse_sync_view()`
- Line 404: `google_sync_logs_api()`

#### Query Optimization Opportunities (3)

- Line 324: missing_select_related
  ```python
  GoogleSyncLog.objects.filter(created_at__lt=delete_date).delete()
  ```
- Line 214: potential_n_plus_one
  ```python
  for key, value in result.get('results', {}).items():
  ```
- Line 407: potential_n_plus_one
  ```python
  for log in logs:
  ```

### installations/admin.py

#### Unused Imports (8)

- Line 4: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)
- Line 6: `mark_safe` (from `django.utils.safestring.mark_safe`)
- Line 7: `_` (from `django.utils.translation.gettext_lazy`)
- Line 8: `Sum` (from `django.db.models.Sum`)
- Line 8: `Count` (from `django.db.models.Count`)
- Line 8: `Q` (from `django.db.models.Q`)
- Line 13: `InstallationManufacturingOrder` (from `models.ManufacturingOrder`)
- Line 442: `render` (from `django.shortcuts.render`)

#### Unused Functions (71)

- Line 91: `lookups()`
- Line 103: `queryset()`
- Line 1265: `get_queryset()`
- Line 501: `has_delete_permission()`
- Line 175: `get_deleted_objects()`
- Line 1206: `customer_name()`
- Line 1193: `order_number()`
- Line 215: `branch_name()`
- Line 221: `salesperson_name()`
- Line 229: `debt_amount_formatted()`
- Line 235: `payment_status()`
- Line 256: `days_overdue()`
- Line 267: `payment_receiver()`
- Line 1434: `save_model()`
- Line 313: `mark_as_paid()`
- Line 352: `delete_selected_debts()`
- Line 363: `export_to_excel()`
- Line 440: `print_debts_report()`
- Line 477: `get_readonly_fields()`
- Line 484: `get_fieldsets()`
- Line 187: `format_callback()`
- Line 544: `technicians_count()`
- Line 599: `status_display()`
- Line 626: `get_urls()`
- Line 638: `installation_by_code_view()`
- Line 662: `installation_code()`
- Line 687: `mark_status_scheduled()`
- Line 693: `mark_status_in_installation()`
- Line 699: `mark_status_completed()`
- Line 705: `mark_status_cancelled()`
- Line 711: `mark_status_modification_required()`
- Line 733: `estimated_cost_formatted()`
- Line 746: `image_preview()`
- Line 870: `changelist_view()`
- Line 927: `order_type_display()`
- Line 1214: `status()`
- Line 964: `installation_status_display()`
- Line 1241: `mark_as_pending()`
- Line 1247: `mark_as_in_progress()`
- Line 1002: `mark_as_ready_install()`
- Line 1253: `mark_as_completed()`
- Line 1259: `mark_as_delivered()`
- Line 1029: `_update_installation_status()`
- Line 1074: `mark_installation_needs_scheduling()`
- Line 1079: `mark_installation_scheduled()`
- Line 1084: `mark_installation_in_progress()`
- Line 1089: `mark_installation_completed()`
- Line 1094: `mark_installation_cancelled()`
- Line 1099: `mark_installation_modification_required()`
- Line 1105: `mark_manufacturing_pending_approval()`
- Line 1111: `mark_manufacturing_pending()`
- Line 1117: `mark_manufacturing_in_progress()`
- Line 1123: `mark_manufacturing_ready_install()`
- Line 1129: `mark_manufacturing_completed()`
- Line 1135: `mark_manufacturing_delivered()`
- Line 1141: `mark_manufacturing_rejected()`
- Line 1147: `mark_manufacturing_cancelled()`
- Line 1232: `estimated_completion()`
- Line 1291: `receipt_image_preview()`
- Line 1300: `amount_received_formatted()`
- Line 1313: `amount_formatted()`
- Line 1327: `archive_notes_short()`
- Line 1334: `archived_by_display()`
- Line 1357: `old_status_display()`
- Line 1363: `new_status_display()`
- Line 1369: `changed_by_display()`
- Line 1381: `reason_short()`
- Line 1399: `event_type_display()`
- Line 1405: `user_display()`
- Line 1417: `description_short()`
- Line 1447: `cost_impact_formatted()`

#### Unused Classes (18)

- Line 121: `CustomerDebtAdmin`
- Line 507: `Media`
- Line 515: `TechnicianAdmin`
- Line 525: `DriverAdmin`
- Line 535: `InstallationTeamAdmin`
- Line 550: `InstallationScheduleAdmin`
- Line 725: `ModificationRequestAdmin`
- Line 739: `ModificationImageAdmin`
- Line 1156: `ModificationManufacturingOrderAdmin`
- Line 1275: `ModificationReportAdmin`
- Line 1284: `ReceiptMemoAdmin`
- Line 1306: `InstallationPaymentAdmin`
- Line 1319: `InstallationArchiveAdmin`
- Line 1348: `InstallationStatusLogAdmin`
- Line 1390: `InstallationEventLogAdmin`
- Line 1426: `InstallationAnalyticsAdmin`
- Line 1440: `ModificationErrorAnalysisAdmin`
- Line 1453: `ModificationErrorTypeAdmin`

#### Query Optimization Opportunities (21)

- Line 57: missing_select_related
  ```python
  return queryset.filter(order__selected_types__icontains='installation')
  ```
- Line 59: missing_select_related
  ```python
  return queryset.filter(order__selected_types__icontains='custom')
  ```
- Line 61: missing_select_related
  ```python
  return queryset.filter(order__selected_types__icontains='accessory')
  ```
- Line 82: missing_select_related
  ```python
  return queryset.filter(order__installation_status=self.value())
  ```
- Line 785: missing_select_related
  ```python
  'count': self.get_queryset(request).filter(order__installation_status='needs_sch
  ```
- Line 790: missing_select_related
  ```python
  'count': self.get_queryset(request).filter(order__installation_status='scheduled
  ```
- Line 795: missing_select_related
  ```python
  'count': self.get_queryset(request).filter(order__installation_status='in_instal
  ```
- Line 800: missing_select_related
  ```python
  'count': self.get_queryset(request).filter(order__installation_status='completed
  ```
- Line 805: missing_select_related
  ```python
  'count': self.get_queryset(request).filter(order__installation_status='cancelled
  ```
- Line 810: missing_select_related
  ```python
  'count': self.get_queryset(request).filter(order__installation_status='modificat
  ```
- Line 1042: missing_select_related
  ```python
  Order.objects.filter(id__in=order_ids).update(installation_status=new_status)
  ```
- Line 1045: missing_select_related
  ```python
  existing_installations = InstallationSchedule.objects.filter(order_id__in=order_
  ```
- Line 318: potential_n_plus_one
  ```python
  for debt in queryset.filter(is_paid=False):
  ```
- Line 383: potential_n_plus_one
  ```python
  for col, header in enumerate(headers, 1):
  ```
- Line 390: potential_n_plus_one
  ```python
  for row, debt in enumerate(queryset.select_related('customer', 'order', 'order__
  ```
- Line 417: potential_n_plus_one
  ```python
  for column in ws.columns:
  ```
- Line 420: potential_n_plus_one
  ```python
  for cell in column:
  ```
- Line 449: potential_n_plus_one
  ```python
  total_amount = sum(debt.debt_amount for debt in queryset)
  ```
- Line 1036: potential_n_plus_one
  ```python
  orders = [order.order for order in queryset if order.order]
  ```
- Line 1037: potential_n_plus_one
  ```python
  order_ids = [order.id for order in orders]
  ```
- Line 1050: potential_n_plus_one
  ```python
  for order in orders:
  ```

### notifications/views.py

#### Unused Imports (8)

- Line 6: `Paginator` (from `django.core.paginator.Paginator`)
- Line 7: `Count` (from `django.db.models.Count`)
- Line 8: `method_decorator` (from `django.utils.decorators.method_decorator`)
- Line 9: `require_POST` (from `django.views.decorators.http.require_POST`)
- Line 14: `status` (from `rest_framework.status`)
- Line 22: `NotificationVisibility` (from `models.NotificationVisibility`)
- Line 22: `NotificationSettings` (from `models.NotificationSettings`)
- Line 23: `NotificationVisibilitySerializer` (from `serializers.NotificationVisibilitySerializer`)

#### Unused Functions (11)

- Line 314: `get_queryset()`
- Line 97: `get_context_data()`
- Line 131: `get_object()`
- Line 142: `mark_notification_read()`
- Line 189: `mark_all_notifications_read()`
- Line 251: `notification_count_ajax()`
- Line 262: `recent_notifications_ajax()`
- Line 321: `unread()`
- Line 332: `count()`
- Line 341: `mark_read()`
- Line 352: `mark_all_read()`

#### Unused Classes (3)

- Line 27: `NotificationListView`
- Line 121: `NotificationDetailView`
- Line 308: `NotificationViewSet`

#### Query Optimization Opportunities (5)

- Line 67: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date__gte=date_from)
  ```
- Line 71: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date__lte=date_to)
  ```
- Line 92: potential_n_plus_one
  ```python
  for notification in notifications:
  ```
- Line 273: potential_n_plus_one
  ```python
  for notification in notifications:
  ```
- Line 275: potential_n_plus_one
  ```python
  visibility_records = [v for v in notification.visibility_records.all() if v.user
  ```

### accounts/admin.py

#### Unused Imports (7)

- Line 8: `format_html` (from `django.utils.html.format_html`)
- Line 12: `ActivityLog` (from `models.ActivityLog`)
- Line 12: `Employee` (from `models.Employee`)
- Line 12: `FormField` (from `models.FormField`)
- Line 12: `ContactFormSettings` (from `models.ContactFormSettings`)
- Line 12: `FooterSettings` (from `models.FooterSettings`)
- Line 12: `AboutPageSettings` (from `models.AboutPageSettings`)

#### Unused Functions (27)

- Line 31: `lookups()`
- Line 39: `queryset()`
- Line 53: `add_manufacturing_approval_permission()`
- Line 84: `remove_manufacturing_approval_permission()`
- Line 125: `formfield_for_foreignkey()`
- Line 494: `get_queryset()`
- Line 609: `get_form()`
- Line 209: `get_roles()`
- Line 217: `has_manufacturing_approval()`
- Line 230: `get_inline_instances()`
- Line 322: `change_view()`
- Line 475: `get_model_perms()`
- Line 565: `has_add_permission()`
- Line 751: `has_delete_permission()`
- Line 314: `changelist_view()`
- Line 376: `has_change_permission()`
- Line 380: `has_view_permission()`
- Line 384: `delete_model()`
- Line 396: `delete_queryset()`
- Line 505: `get_users_count()`
- Line 626: `color_preview()`
- Line 660: `icon_preview()`
- Line 704: `get_section_display()`
- Line 709: `save_model()`
- Line 727: `activate_years()`
- Line 733: `deactivate_years()`
- Line 739: `set_as_default()`

#### Unused Classes (11)

- Line 132: `CustomUserAdmin`
- Line 248: `CompanyInfoAdmin`
- Line 331: `BranchAdmin`
- Line 341: `DepartmentAdmin`
- Line 439: `SalespersonAdmin`
- Line 515: `PermissionAdmin`
- Line 538: `SystemSettingsAdmin`
- Line 577: `BranchMessageAdmin`
- Line 677: `Media`
- Line 686: `YearFilterExemptionAdmin`
- Line 720: `DashboardYearSettingsAdmin`

#### Query Optimization Opportunities (10)

- Line 42: missing_select_related
  ```python
  return queryset.filter(departments__id=self.value())
  ```
- Line 44: missing_select_related
  ```python
  return queryset.filter(department__id=self.value())
  ```
- Line 49: missing_select_related
  ```python
  return queryset.filter(user__departments__id=self.value())
  ```
- Line 362: missing_select_related
  ```python
  return qs.filter(id__in=department_ids)
  ```
- Line 37: potential_n_plus_one
  ```python
  return [(dept.id, dept.name) for dept in departments]
  ```
- Line 68: potential_n_plus_one
  ```python
  for user in queryset:
  ```
- Line 101: potential_n_plus_one
  ```python
  for user in queryset:
  ```
- Line 214: potential_n_plus_one
  ```python
  return ", ".join([role.role.name for role in roles])
  ```
- Line 356: potential_n_plus_one
  ```python
  for dept in user_departments:
  ```
- Line 360: potential_n_plus_one
  ```python
  for child in children:
  ```

### backup_system/services.py

#### Unused Imports (7)

- Line 12: `Optional` (from `typing.Optional`)
- Line 12: `Callable` (from `typing.Callable`)
- Line 16: `call_command` (from `django.core.management.call_command`)
- Line 17: `models` (from `django.db.models`)
- Line 19: `timezone` (from `django.utils.timezone`)
- Line 20: `ContentType` (from `django.contrib.contenttypes.models.ContentType`)
- Line 21: `ValidationError` (from `django.core.exceptions.ValidationError`)

#### Unused Functions (21)

- Line 507: `__init__()`
- Line 33: `create_backup()`
- Line 55: `_run_backup()`
- Line 113: `_get_default_apps()`
- Line 129: `_get_app_data()`
- Line 154: `_should_skip_model()`
- Line 169: `_write_compressed_backup()`
- Line 195: `restore_from_file()`
- Line 226: `_run_restore()`
- Line 310: `_read_backup_file()`
- Line 328: `_sort_data_by_dependencies()`
- Line 383: `_clear_existing_data()`
- Line 429: `_should_skip_clearing()`
- Line 449: `_restore_item()`
- Line 488: `_should_skip_restoring()`
- Line 511: `create_full_backup()`
- Line 520: `create_partial_backup()`
- Line 531: `restore_backup()`
- Line 542: `get_backup_status()`
- Line 563: `get_restore_status()`
- Line 585: `cleanup_old_backups()`

#### Query Optimization Opportunities (12)

- Line 71: potential_n_plus_one
  ```python
  for i, app_name in enumerate(apps_to_include):
  ```
- Line 135: potential_n_plus_one
  ```python
  for model in app_config.get_models():
  ```
- Line 265: potential_n_plus_one
  ```python
  for i, item in enumerate(sorted_data):
  ```
- Line 367: potential_n_plus_one
  ```python
  for model_name in priority_order:
  ```
- Line 368: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 375: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 388: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 410: potential_n_plus_one
  ```python
  for model_name in clear_order:
  ```
- Line 464: potential_n_plus_one
  ```python
  for obj in serializers.deserialize('python', [item]):
  ```
- Line 474: potential_n_plus_one
  ```python
  for field_name, field_value in item['fields'].items():
  ```
- Line 501: potential_n_plus_one
  ```python
  return model_name.lower() in [m.lower() for m in skip_models]
  ```
- Line 595: potential_n_plus_one
  ```python
  for backup in backups_to_delete:
  ```

### manufacturing/admin.py

#### Unused Imports (7)

- Line 4: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)
- Line 5: `JsonResponse` (from `django.http.JsonResponse`)
- Line 7: `Q` (from `django.db.models.Q`)
- Line 7: `Count` (from `django.db.models.Count`)
- Line 8: `mark_safe` (from `django.utils.safestring.mark_safe`)
- Line 9: `require_http_methods` (from `django.views.decorators.http.require_http_methods`)
- Line 10: `staff_member_required` (from `django.contrib.admin.views.decorators.staff_member_required`)

#### Unused Functions (44)

- Line 723: `__init__()`
- Line 39: `save()`
- Line 55: `get_formset()`
- Line 579: `get_queryset()`
- Line 100: `get_sortable_by()`
- Line 192: `bulk_update_status()`
- Line 261: `mark_pending_approval()`
- Line 267: `mark_pending()`
- Line 273: `mark_in_progress()`
- Line 279: `mark_ready_install()`
- Line 285: `mark_completed()`
- Line 291: `mark_delivered()`
- Line 297: `mark_rejected()`
- Line 303: `mark_cancelled()`
- Line 905: `customer_name()`
- Line 375: `production_line_display()`
- Line 389: `contract_number()`
- Line 397: `exit_permit_display()`
- Line 403: `order_type_display()`
- Line 431: `order_date()`
- Line 439: `expected_delivery_date()`
- Line 447: `status_display()`
- Line 471: `delivery_info()`
- Line 491: `rejection_reply_status()`
- Line 511: `created_at()`
- Line 518: `get_urls()`
- Line 530: `manufacturing_order_by_code_view()`
- Line 554: `manufacturing_code()`
- Line 832: `has_change_permission()`
- Line 840: `save_model()`
- Line 695: `get_branches_display()`
- Line 700: `get_supported_order_types_display()`
- Line 747: `clean()`
- Line 820: `has_module_permission()`
- Line 824: `has_view_permission()`
- Line 946: `has_add_permission()`
- Line 950: `has_delete_permission()`
- Line 846: `get_allowed_statuses_display()`
- Line 851: `get_allowed_order_types_display()`
- Line 856: `get_target_users_display()`
- Line 861: `orders_count()`
- Line 866: `active_orders_count()`
- Line 909: `order_number()`
- Line 954: `changelist_view()`

#### Unused Classes (9)

- Line 709: `Meta`
- Line 69: `ManufacturingOrderAdmin`
- Line 624: `ManufacturingOrderItemAdmin`
- Line 634: `ProductionLineAdmin`
- Line 769: `ManufacturingDisplaySettingsAdmin`
- Line 881: `FabricReceiptAdmin`
- Line 915: `FabricReceiptItemAdmin`
- Line 924: `ManufacturingSettingsAdmin`
- Line 959: `Media`

#### Query Optimization Opportunities (3)

- Line 212: potential_n_plus_one
  ```python
  for order in queryset.select_related('order'):
  ```
- Line 223: potential_n_plus_one
  ```python
  for key in cache_keys_to_clear:
  ```
- Line 425: potential_n_plus_one
  ```python
  type_names = [type_map.get(t, t) for t in selected_types]
  ```

### odoo_db_manager/advanced_sync_service.py

#### Unused Imports (7)

- Line 8: `time` (from `time`)
- Line 10: `Tuple` (from `typing.Tuple`)
- Line 13: `ValidationError` (from `django.core.exceptions.ValidationError`)
- Line 14: `settings` (from `django.conf.settings`)
- Line 16: `GoogleSyncConflict` (from `google_sync_advanced.GoogleSyncConflict`)
- Line 20: `CustomerCategory` (from `customers.models.CustomerCategory`)
- Line 25: `Branch` (from `accounts.models.Branch`)

#### Unused Functions (22)

- Line 31: `_create_manufacturing_order()`
- Line 72: `_map_order_type()`
- Line 90: `_create_inspection()`
- Line 1007: `__init__()`
- Line 161: `sync_from_sheets()`
- Line 224: `_process_sheet_data()`
- Line 383: `_print_detailed_report()`
- Line 481: `_get_sheet_data()`
- Line 489: `_map_row_data()`
- Line 502: `_process_customer()`
- Line 545: `_parse_date()`
- Line 575: `_is_valid_inspection_date()`
- Line 605: `_create_customer()`
- Line 643: `_update_customer()`
- Line 669: `_create_order()`
- Line 762: `_find_existing_order()`
- Line 786: `_find_or_create_inspection_order()`
- Line 818: `_update_order()`
- Line 860: `_process_inspection()`
- Line 912: `_update_inspection()`
- Line 969: `_process_installation()`
- Line 1010: `run_scheduled_syncs()`

#### Unused Classes (1)

- Line 1004: `SyncScheduler`

#### Query Optimization Opportunities (16)

- Line 524: missing_select_related
  ```python
  customer = Customer.objects.filter(name__iexact=customer_name).first()
  ```
- Line 736: missing_select_related
  ```python
  salesperson = Salesperson.objects.filter(name__icontains=salesperson_name).first
  ```
- Line 247: potential_n_plus_one
  ```python
  for batch_start in range(0, total_rows, batch_size):
  ```
- Line 255: potential_n_plus_one
  ```python
  for i, row in enumerate(batch_rows):
  ```
- Line 431: potential_n_plus_one
  ```python
  for error in self.stats['detailed_errors']:
  ```
- Line 432: potential_n_plus_one
  ```python
  for action in error.get('actions', []):
  ```
- Line 447: potential_n_plus_one
  ```python
  for example in sorted(unknown_type_examples):
  ```
- Line 454: potential_n_plus_one
  ```python
  for i, error in enumerate(self.stats['errors'][:5]):  # أول 5 أخطاء
  ```
- Line 465: potential_n_plus_one
  ```python
  for i, row_detail in enumerate(self.stats['detailed_errors'][:10]):
  ```
- Line 471: potential_n_plus_one
  ```python
  for action in row_detail.get('actions', []):
  ```
- Line 494: potential_n_plus_one
  ```python
  for i, header in enumerate(headers):
  ```
- Line 560: potential_n_plus_one
  ```python
  for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
  ```
- Line 590: potential_n_plus_one
  ```python
  for phrase in rejected_phrases:
  ```
- Line 595: potential_n_plus_one
  ```python
  if any('\u0600' <= char <= '\u06FF' for char in value_str):
  ```
- Line 656: potential_n_plus_one
  ```python
  for customer_field, mapping_field in zip(fields_to_update, mapping_fields):
  ```
- Line 1017: potential_n_plus_one
  ```python
  for schedule in due_schedules:
  ```

### orders/views.py

#### Unused Imports (7)

- Line 12: `ValidationError` (from `django.core.exceptions.ValidationError`)
- Line 16: `Department` (from `accounts.models.Department`)
- Line 18: `Product` (from `inventory.models.Product`)
- Line 20: `datetime` (from `datetime.datetime`)
- Line 20: `timedelta` (from `datetime.timedelta`)
- Line 23: `_` (from `django.utils.translation.gettext_lazy`)
- Line 57: `get_available_years` (from `core.monthly_filter_utils.get_available_years`)

#### Unused Functions (27)

- Line 26: `get_context_data()`
- Line 52: `order_list()`
- Line 210: `order_success()`
- Line 232: `order_detail()`
- Line 308: `order_create()`
- Line 558: `order_update()`
- Line 793: `order_delete()`
- Line 832: `payment_create()`
- Line 880: `payment_delete()`
- Line 904: `salesperson_list()`
- Line 943: `update_order_status()`
- Line 982: `get_order_details_api()`
- Line 1052: `get_customer_inspections()`
- Line 1105: `order_detail_by_number()`
- Line 1152: `order_detail_by_code()`
- Line 1195: `order_success_by_number()`
- Line 1207: `order_update_by_number()`
- Line 1436: `order_delete_by_number()`
- Line 1461: `order_detail_redirect()`
- Line 1467: `order_success_redirect()`
- Line 1473: `order_update_redirect()`
- Line 1479: `order_delete_redirect()`
- Line 1490: `invoice_print()`
- Line 1847: `invoice_print_redirect()`
- Line 1856: `ajax_upload_contract_to_google_drive()`
- Line 1920: `check_contract_upload_status()`
- Line 1938: `order_status_history()`

#### Unused Classes (1)

- Line 24: `OrdersDashboardView`

#### Query Optimization Opportunities (36)

- Line 42: missing_select_related
  ```python
  context['completed_orders'] = orders.filter(order_status__in=['completed', 'deli
  ```
- Line 46: missing_select_related
  ```python
  context['total_sales'] = orders.filter(order_status='completed').aggregate(Sum('
  ```
- Line 47: missing_select_related
  ```python
  context['monthly_sales'] = orders.filter(order_status='completed', created_at__m
  ```
- Line 127: missing_select_related
  ```python
  orders = orders.filter(selected_types__icontains=order_type_filter)
  ```
- Line 134: missing_select_related
  ```python
  orders = orders.filter(order_date__gte=date_from)
  ```
- Line 137: missing_select_related
  ```python
  orders = orders.filter(order_date__lte=date_to)
  ```
- Line 1969: missing_select_related
  ```python
  status_logs = status_logs.filter(changed_by__id=user_filter)
  ```
- Line 153: potential_n_plus_one
  ```python
  available_years = [year.year for year in available_years]
  ```
- Line 287: potential_n_plus_one
  ```python
  for it in order_items:
  ```
- Line 609: potential_n_plus_one
  ```python
  for field_name in order_fields_to_track:
  ```
- Line 654: potential_n_plus_one
  ```python
  for form_item in formset:
  ```
- Line 660: potential_n_plus_one
  ```python
  for field_name in item_fields_to_track:
  ```
- Line 687: potential_n_plus_one
  ```python
  for form_item in formset.deleted_forms:
  ```
- Line 700: potential_n_plus_one
  ```python
  for form_item in formset:
  ```
- Line 742: potential_n_plus_one
  ```python
  #     for field_name, values in modified_fields.items():
  ```
- Line 1020: potential_n_plus_one
  ```python
  for item in order_items:
  ```
- Line 1078: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 1221: potential_n_plus_one
  ```python
  for field, errors in form.errors.items():
  ```
- Line 1225: potential_n_plus_one
  ```python
  for i, form_errors in enumerate(formset.errors):
  ```
- Line 1227: potential_n_plus_one
  ```python
  for field, errors in form_errors.items():
  ```
- Line 1233: potential_n_plus_one
  ```python
  for form_item in formset:
  ```
- Line 1246: potential_n_plus_one
  ```python
  for field in form.changed_data:
  ```
- Line 1279: potential_n_plus_one
  ```python
  for form_item in formset:
  ```
- Line 1302: potential_n_plus_one
  ```python
  for field in form_item.changed_data:
  ```
- Line 1353: potential_n_plus_one
  ```python
  for form_item in formset:
  ```
- Line 1380: potential_n_plus_one
  ```python
  for change in changes:
  ```
- Line 1386: potential_n_plus_one
  ```python
  for item in added_items:
  ```
- Line 1392: potential_n_plus_one
  ```python
  for item in modified_items:
  ```
- Line 1398: potential_n_plus_one
  ```python
  for item in deleted_items:
  ```
- Line 1528: potential_n_plus_one
  ```python
  for item in order.items.all():
  ```
- Line 1580: potential_n_plus_one
  ```python
  for placeholder, value in basic_replacements.items():
  ```
- Line 1661: potential_n_plus_one
  ```python
  for typ in ['معاينة', 'تركيب', 'تسليم', 'إكسسوار', 'منتج', 'خدمة']:
  ```
- Line 1992: potential_n_plus_one
  ```python
  inspection_choices = [(f"inspection_{choice[0]}", f"معاينة: {choice[1]}") for ch
  ```
- Line 2000: potential_n_plus_one
  ```python
  installation_choices = [(f"installation_{choice[0]}", f"تركيب: {choice[1]}") for
  ```
- Line 2008: potential_n_plus_one
  ```python
  manufacturing_choices = [(f"manufacturing_{choice[0]}", f"تصنيع: {choice[1]}") f
  ```
- Line 2016: potential_n_plus_one
  ```python
  cutting_choices = [(f"cutting_{choice[0]}", f"تقطيع: {choice[1]}") for choice in
  ```

### crm/monitoring.py

#### Unused Imports (6)

- Line 6: `time` (from `time`)
- Line 13: `connection` (from `django.db.connection`)
- Line 15: `datetime` (from `datetime.datetime`)
- Line 15: `timedelta` (from `datetime.timedelta`)
- Line 16: `json` (from `json`)
- Line 17: `os` (from `os`)

#### Unused Functions (11)

- Line 244: `__init__()`
- Line 46: `get_connection_stats()`
- Line 98: `check_alerts()`
- Line 128: `cleanup_connections()`
- Line 189: `get_system_stats()`
- Line 314: `start_monitoring()`
- Line 265: `stop_monitoring_service()`
- Line 272: `_monitoring_loop()`
- Line 296: `get_current_status()`
- Line 319: `stop_monitoring()`
- Line 324: `get_monitoring_status()`

### orders/admin.py

#### Unused Imports (6)

- Line 5: `Q` (from `django.db.models.Q`)
- Line 7: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)
- Line 7: `redirect` (from `django.shortcuts.redirect`)
- Line 9: `datetime` (from `datetime.datetime`)
- Line 10: `ManufacturingDeletionLog` (from `models.ManufacturingDeletionLog`)
- Line 659: `invoice_admin` (from `invoice_admin`)

#### Unused Functions (30)

- Line 24: `lookups()`
- Line 31: `queryset()`
- Line 679: `old_status_display()`
- Line 686: `new_status_display()`
- Line 64: `has_add_permission()`
- Line 67: `has_change_permission()`
- Line 614: `has_delete_permission()`
- Line 153: `get_formset()`
- Line 121: `__init__()`
- Line 143: `clean_selected_types()`
- Line 611: `get_queryset()`
- Line 201: `get_sortable_by()`
- Line 264: `mark_as_paid()`
- Line 279: `create_manufacturing_order()`
- Line 302: `export_orders()`
- Line 365: `order_type_display()`
- Line 380: `status_display()`
- Line 395: `order_status_display()`
- Line 414: `payment_status()`
- Line 423: `order_year()`
- Line 445: `get_form()`
- Line 462: `get_urls()`
- Line 473: `order_by_code_view()`
- Line 483: `order_number_display()`
- Line 693: `notes_truncated()`
- Line 539: `quantity_display()`
- Line 570: `get_setting_display()`
- Line 581: `get_default_days_display()`
- Line 618: `save_model()`
- Line 671: `order_link()`

#### Unused Classes (5)

- Line 117: `Meta`
- Line 161: `OrderAdmin`
- Line 547: `DeliveryTimeSettingsAdmin`
- Line 638: `PaymentAdmin`
- Line 662: `OrderStatusLogAdmin`

#### Query Optimization Opportunities (8)

- Line 37: missing_select_related
  ```python
  return queryset.filter(order_date__year=year)
  ```
- Line 27: potential_n_plus_one
  ```python
  for year in years:
  ```
- Line 137: potential_n_plus_one
  ```python
  val = [v.strip() for v in val.split(',') if v.strip()]
  ```
- Line 266: potential_n_plus_one
  ```python
  for order in queryset:
  ```
- Line 282: potential_n_plus_one
  ```python
  for order in queryset:
  ```
- Line 285: potential_n_plus_one
  ```python
  if any(t in ['installation', 'tailoring', 'accessory'] for t in order_types):
  ```
- Line 314: potential_n_plus_one
  ```python
  for order in queryset:
  ```
- Line 374: potential_n_plus_one
  ```python
  type_names = [type_map.get(t, t) for t in selected_types]
  ```

### cutting/views.py

#### Unused Imports (6)

- Line 1: `redirect` (from `django.shortcuts.redirect`)
- Line 5: `HttpResponse` (from `django.http.HttpResponse`)
- Line 6: `messages` (from `django.contrib.messages`)
- Line 9: `Paginator` (from `django.core.paginator.Paginator`)
- Line 10: `render_to_string` (from `django.template.loader.render_to_string`)
- Line 11: `timedelta` (from `datetime.timedelta`)

#### Unused Functions (21)

- Line 834: `get_context_data()`
- Line 482: `get_user_warehouses()`
- Line 66: `get_user_warehouses_with_stats()`
- Line 660: `get_queryset()`
- Line 242: `cutting_order_detail_by_code()`
- Line 260: `update_cutting_item()`
- Line 301: `complete_cutting_item()`
- Line 343: `reject_cutting_item()`
- Line 375: `bulk_update_items()`
- Line 420: `bulk_complete_items()`
- Line 490: `generate_cutting_report()`
- Line 543: `daily_cutting_report()`
- Line 580: `print_daily_delivery_report()`
- Line 606: `warehouse_cutting_stats()`
- Line 637: `get_item_status()`
- Line 712: `receive_cutting_order_ajax()`
- Line 787: `cutting_notifications_api()`
- Line 844: `print_cutting_report()`
- Line 928: `create_cutting_order_from_order()`
- Line 981: `start_cutting_order()`
- Line 1013: `quick_stats_api()`

#### Unused Classes (8)

- Line 21: `CuttingDashboardView`
- Line 95: `CuttingOrderListView`
- Line 160: `CompletedCuttingOrdersView`
- Line 226: `CuttingOrderDetailView`
- Line 463: `CuttingReportsView`
- Line 654: `CuttingReceiptView`
- Line 820: `WarehouseSettingsView`
- Line 830: `UserPermissionsView`

#### Query Optimization Opportunities (15)

- Line 33: missing_select_related
  ```python
  'total_orders': CuttingOrder.objects.filter(warehouse__in=[w['warehouse'] for w 
  ```
- Line 114: missing_select_related
  ```python
  queryset = queryset.filter(warehouse__in=user_warehouses)
  ```
- Line 174: missing_select_related
  ```python
  queryset = queryset.filter(warehouse__in=user_warehouses)
  ```
- Line 33: potential_n_plus_one
  ```python
  'total_orders': CuttingOrder.objects.filter(warehouse__in=[w['warehouse'] for w 
  ```
- Line 35: potential_n_plus_one
  ```python
  warehouse__in=[w['warehouse'] for w in user_warehouses], status='pending'
  ```
- Line 38: potential_n_plus_one
  ```python
  warehouse__in=[w['warehouse'] for w in user_warehouses], status='in_progress'
  ```
- Line 41: potential_n_plus_one
  ```python
  warehouse__in=[w['warehouse'] for w in user_warehouses], status='completed'
  ```
- Line 45: potential_n_plus_one
  ```python
  warehouse__in=[w['warehouse'] for w in user_warehouses]
  ```
- Line 71: potential_n_plus_one
  ```python
  for warehouse in warehouses:
  ```
- Line 396: potential_n_plus_one
  ```python
  for item in cutting_order.items.filter(status='pending'):
  ```
- Line 440: potential_n_plus_one
  ```python
  for item in cutting_order.items.filter(status='pending'):
  ```
- Line 563: potential_n_plus_one
  ```python
  for item in cutting_items:
  ```
- Line 759: potential_n_plus_one
  ```python
  for item in ready_items:
  ```
- Line 799: potential_n_plus_one
  ```python
  for notification in notifications:
  ```
- Line 959: potential_n_plus_one
  ```python
  for order_item in order.items.all():
  ```

### odoo_db_manager/services/scheduled_backup_service.py

#### Unused Imports (6)

- Line 7: `datetime` (from `datetime.datetime`)
- Line 7: `timedelta` (from `datetime.timedelta`)
- Line 9: `settings` (from `django.conf.settings`)
- Line 10: `Q` (from `django.db.models.Q`)
- Line 13: `DjangoJobExecution` (from `django_apscheduler.models.DjangoJobExecution`)
- Line 15: `Database` (from `odoo_db_manager.models.Database`)

#### Unused Functions (8)

- Line 77: `cleanup_old_backups()`
- Line 110: `__init__()`
- Line 115: `start()`
- Line 131: `stop()`
- Line 141: `_schedule_all_backups()`
- Line 159: `_schedule_backup()`
- Line 211: `remove_job()`
- Line 223: `run_job_now()`

#### Query Optimization Opportunities (2)

- Line 95: potential_n_plus_one
  ```python
  for backup in to_delete:
  ```
- Line 156: potential_n_plus_one
  ```python
  for schedule in schedules:
  ```

### accounts/management/commands/check_security.py

#### Unused Imports (6)

- Line 3: `Error` (from `django.core.checks.Error`)
- Line 3: `Warning` (from `django.core.checks.Warning`)
- Line 4: `SECRET_KEY_MIN_LENGTH` (from `django.core.checks.security.base.SECRET_KEY_MIN_LENGTH`)
- Line 5: `requests` (from `requests`)
- Line 6: `socket` (from `socket`)
- Line 7: `ssl` (from `ssl`)

#### Unused Functions (1)

- Line 12: `handle()`

#### Unused Classes (1)

- Line 9: `Command`

### backup_system/views.py

#### Unused Imports (5)

- Line 5: `json` (from `json`)
- Line 10: `staff_member_required` (from `django.contrib.admin.views.decorators.staff_member_required`)
- Line 14: `require_http_methods` (from `django.views.decorators.http.require_http_methods`)
- Line 16: `timezone` (from `django.utils.timezone`)
- Line 19: `BackupSchedule` (from `models.BackupSchedule`)

#### Unused Functions (14)

- Line 24: `is_staff_or_superuser()`
- Line 31: `dashboard()`
- Line 67: `backup_list()`
- Line 98: `backup_create()`
- Line 144: `backup_detail()`
- Line 158: `backup_download()`
- Line 179: `backup_delete()`
- Line 209: `restore_list()`
- Line 234: `restore_upload()`
- Line 301: `restore_from_backup()`
- Line 352: `restore_detail()`
- Line 369: `backup_status_api()`
- Line 381: `restore_status_api()`
- Line 392: `_format_file_size()`

#### Query Optimization Opportunities (3)

- Line 47: potential_n_plus_one
  ```python
  backup.compressed_size for backup in
  ```
- Line 256: potential_n_plus_one
  ```python
  for chunk in uploaded_file.chunks():
  ```
- Line 397: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
  ```

### complaints/admin.py

#### Unused Imports (5)

- Line 3: `reverse` (from `django.urls.reverse`)
- Line 4: `mark_safe` (from `django.utils.safestring.mark_safe`)
- Line 5: `Count` (from `django.db.models.Count`)
- Line 5: `Q` (from `django.db.models.Q`)
- Line 8: `Department` (from `accounts.models.Department`)

#### Unused Functions (27)

- Line 101: `permissions_summary()`
- Line 129: `current_assigned_count()`
- Line 687: `get_queryset()`
- Line 158: `enable_assignment()`
- Line 164: `disable_assignment()`
- Line 170: `enable_escalation()`
- Line 176: `disable_escalation()`
- Line 182: `enable_escalate_permission()`
- Line 188: `disable_escalate_permission()`
- Line 194: `enable_all_permissions()`
- Line 210: `disable_all_permissions()`
- Line 226: `make_supervisor()`
- Line 253: `make_staff_member()`
- Line 542: `has_delete_permission()`
- Line 661: `file_size_display()`
- Line 404: `customer_name()`
- Line 408: `status_display()`
- Line 416: `priority_display()`
- Line 424: `is_overdue_display()`
- Line 434: `time_remaining_display()`
- Line 450: `resolution_time_display()`
- Line 500: `has_change_permission()`
- Line 563: `mark_as_resolved()`
- Line 576: `escalate_complaints()`
- Line 584: `export_as_csv()`
- Line 590: `export_as_excel()`
- Line 637: `status_change_display()`

#### Unused Classes (9)

- Line 19: `ComplaintTypeAdmin`
- Line 50: `ComplaintUserPermissionsAdmin`
- Line 335: `ComplaintAdmin`
- Line 598: `ComplaintUpdateAdmin`
- Line 651: `ComplaintAttachmentAdmin`
- Line 677: `ComplaintEscalationAdmin`
- Line 694: `ComplaintSLAAdmin`
- Line 709: `ResolutionMethodAdmin`
- Line 730: `ComplaintTemplateAdmin`

#### Query Optimization Opportunities (6)

- Line 276: missing_select_related
  ```python
  *Group.objects.filter(name__in=['Complaints_Supervisors', 'Managers', 'Complaint
  ```
- Line 482: missing_select_related
  ```python
  if user.groups.filter(name__in=admin_groups).exists():
  ```
- Line 513: missing_select_related
  ```python
  if user.groups.filter(name__in=admin_groups).exists():
  ```
- Line 529: missing_select_related
  ```python
  if user.groups.filter(name__in=['Complaints_Managers', 'Complaints_Supervisors',
  ```
- Line 245: potential_n_plus_one
  ```python
  for permission in queryset:
  ```
- Line 273: potential_n_plus_one
  ```python
  for permission in queryset:
  ```

### inspections/views.py

#### Unused Imports (5)

- Line 1: `TemplateView` (from `django.views.generic.TemplateView`)
- Line 8: `Count` (from `django.db.models.Count`)
- Line 8: `F` (from `django.db.models.F`)
- Line 9: `HttpResponse` (from `django.http.HttpResponse`)
- Line 18: `require_GET` (from `django.views.decorators.http.require_GET`)

#### Unused Functions (21)

- Line 600: `get_queryset()`
- Line 82: `get_paginate_by()`
- Line 573: `get_context_data()`
- Line 542: `get_form_kwargs()`
- Line 610: `form_valid()`
- Line 526: `test_func()`
- Line 461: `check_upload_status()`
- Line 534: `handle_no_permission()`
- Line 617: `get_success_url()`
- Line 620: `mark_notification_read()`
- Line 630: `iterate_inspection()`
- Line 676: `ajax_duplicate_inspection()`
- Line 755: `ajax_upload_to_google_drive()`
- Line 817: `inspection_detail_by_code()`
- Line 839: `inspection_update_by_code()`
- Line 857: `inspection_delete_by_code()`
- Line 873: `inspection_detail_redirect()`
- Line 879: `inspection_update_redirect()`
- Line 885: `inspection_delete_redirect()`
- Line 892: `inspection_schedule_view()`
- Line 950: `print_daily_schedule()`

#### Unused Classes (9)

- Line 21: `CompletedInspectionsDetailView`
- Line 39: `CancelledInspectionsDetailView`
- Line 57: `PendingInspectionsDetailView`
- Line 75: `InspectionListView`
- Line 178: `InspectionCreateView`
- Line 538: `EvaluationCreateView`
- Line 578: `InspectionReportCreateView`
- Line 593: `NotificationListView`
- Line 605: `NotificationCreateView`

#### Query Optimization Opportunities (10)

- Line 108: missing_select_related
  ```python
  queryset = queryset.filter(order__customer__branch_id=branch_id)
  ```
- Line 114: missing_select_related
  ```python
  queryset = queryset.filter(notes__contains='تكرار من المعاينة رقم:')
  ```
- Line 157: missing_select_related
  ```python
  dashboard_qs = dashboard_qs.filter(order__customer__branch_id=branch_id)
  ```
- Line 163: missing_select_related
  ```python
  dashboard_qs = dashboard_qs.filter(notes__contains='تكرار من المعاينة رقم:')
  ```
- Line 173: missing_select_related
  ```python
  'duplicated_inspections': dashboard_qs.filter(notes__contains='تكرار من المعاينة
  ```
- Line 845: missing_select_related
  ```python
  inspection = Inspection.objects.filter(order__order_number=order_number).first()
  ```
- Line 862: missing_select_related
  ```python
  inspection = Inspection.objects.filter(order__order_number=order_number).first()
  ```
- Line 371: potential_n_plus_one
  ```python
  for installation in installation_schedules:
  ```
- Line 553: potential_n_plus_one
  ```python
  for criteria in ['location', 'condition', 'suitability', 'safety', 'accessibilit
  ```
- Line 978: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```

### installations/models.py

#### Unused Imports (5)

- Line 3: `MinValueValidator` (from `django.core.validators.MinValueValidator`)
- Line 3: `MaxValueValidator` (from `django.core.validators.MaxValueValidator`)
- Line 7: `os` (from `os`)
- Line 210: `time` (from `datetime.time`)
- Line 304: `User` (from `django.contrib.auth.models.User`)

#### Unused Functions (15)

- Line 10: `installation_receipt_path()`
- Line 15: `modification_report_path()`
- Line 20: `modification_images_path()`
- Line 824: `__str__()`
- Line 190: `save()`
- Line 180: `get_absolute_url()`
- Line 185: `clean()`
- Line 328: `can_change_status_to()`
- Line 339: `get_next_possible_statuses()`
- Line 344: `get_installation_date()`
- Line 363: `get_installation_date_label()`
- Line 374: `get_expected_installation_date()`
- Line 385: `requires_scheduling_settings()`
- Line 572: `calculate_rates()`
- Line 742: `populate_from_order()`

#### Unused Classes (12)

- Line 25: `CustomerDebt`
- Line 819: `Meta`
- Line 418: `ModificationImage`
- Line 470: `ModificationReport`
- Line 489: `ReceiptMemo`
- Line 506: `InstallationPayment`
- Line 531: `InstallationArchive`
- Line 547: `InstallationAnalytics`
- Line 597: `ModificationErrorAnalysis`
- Line 628: `InstallationStatusLog`
- Line 675: `InstallationSchedulingSettings`
- Line 777: `InstallationEventLog`

#### Query Optimization Opportunities (3)

- Line 336: potential_n_plus_one
  ```python
  valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
  ```
- Line 342: potential_n_plus_one
  ```python
  return [(choice[0], choice[1]) for choice in self.STATUS_CHOICES]
  ```
- Line 768: potential_n_plus_one
  ```python
  self.technician_name = ', '.join([tech.name for tech in technicians])
  ```

### inventory/views_bulk.py

#### Unused Imports (5)

- Line 1: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)
- Line 9: `openpyxl` (from `openpyxl`)
- Line 10: `Font` (from `openpyxl.styles.Font`)
- Line 10: `PatternFill` (from `openpyxl.styles.PatternFill`)
- Line 641: `BytesIO` (from `io.BytesIO`)

#### Unused Functions (5)

- Line 228: `product_bulk_upload()`
- Line 273: `bulk_stock_update()`
- Line 308: `process_excel_upload()`
- Line 515: `process_stock_update()`
- Line 605: `download_excel_template()`

#### Query Optimization Opportunities (10)

- Line 32: missing_select_related
  ```python
  warehouse = Warehouse.objects.filter(name__iexact=warehouse_name).first()
  ```
- Line 126: potential_n_plus_one
  ```python
  for row_idx in range(sheet.nrows):
  ```
- Line 128: potential_n_plus_one
  ```python
  for col_idx in range(sheet.ncols):
  ```
- Line 175: potential_n_plus_one
  ```python
  for row in sheet.iter_rows(values_only=True):
  ```
- Line 177: potential_n_plus_one
  ```python
  for cell in row:
  ```
- Line 182: potential_n_plus_one
  ```python
  if any(cell.strip() for cell in row_data):
  ```
- Line 256: potential_n_plus_one
  ```python
  for error in result['errors'][:5]:
  ```
- Line 294: potential_n_plus_one
  ```python
  for error in result['errors'][:5]:
  ```
- Line 336: potential_n_plus_one
  ```python
  for index, row in df.iterrows():
  ```
- Line 530: potential_n_plus_one
  ```python
  for index, row in df.iterrows():
  ```

### inventory/views_warehouse_locations.py

#### Unused Imports (5)

- Line 5: `Sum` (from `django.db.models.Sum`)
- Line 5: `Count` (from `django.db.models.Count`)
- Line 5: `F` (from `django.db.models.F`)
- Line 6: `timezone` (from `django.utils.timezone`)
- Line 8: `timedelta` (from `datetime.timedelta`)

#### Unused Functions (5)

- Line 12: `warehouse_location_list()`
- Line 103: `warehouse_location_create()`
- Line 166: `warehouse_location_update()`
- Line 210: `warehouse_location_delete()`
- Line 229: `warehouse_location_detail()`

#### Query Optimization Opportunities (1)

- Line 42: potential_n_plus_one
  ```python
  for location in locations:
  ```

### odoo_db_manager/fast_sync_service.py

#### Unused Imports (5)

- Line 9: `date` (from `datetime.date`)
- Line 12: `IntegrityError` (from `django.db.IntegrityError`)
- Line 13: `ValidationError` (from `django.core.exceptions.ValidationError`)
- Line 20: `Branch` (from `accounts.models.Branch`)
- Line 20: `Salesperson` (from `accounts.models.Salesperson`)

#### Unused Functions (14)

- Line 28: `__init__()`
- Line 47: `sync_from_sheets()`
- Line 100: `_process_sheet_data_fast()`
- Line 168: `_find_or_create_customer_fast()`
- Line 244: `_process_orders_fast()`
- Line 279: `_map_order_type_fast()`
- Line 295: `_is_valid_inspection_date_fast()`
- Line 309: `_parse_date_fast()`
- Line 324: `_create_order_fast()`
- Line 371: `_create_manufacturing_order_fast()`
- Line 400: `_create_inspection_fast()`
- Line 429: `_get_sheet_data()`
- Line 437: `_map_row_data()`
- Line 450: `_print_fast_summary()`

#### Unused Classes (1)

- Line 25: `FastSyncService`

#### Query Optimization Opportunities (7)

- Line 116: potential_n_plus_one
  ```python
  for c in Customer.objects.select_related('branch').all():
  ```
- Line 126: potential_n_plus_one
  ```python
  for batch_start in range(0, total_rows, batch_size):
  ```
- Line 137: potential_n_plus_one
  ```python
  for i, row in enumerate(batch_rows):
  ```
- Line 216: potential_n_plus_one
  ```python
  for key in ['customer_created_at', 'customer_date', 'customer_registration_date'
  ```
- Line 303: potential_n_plus_one
  ```python
  if any(word in value_str for word in ['عميل', 'لاحق', 'غير', 'بدون', 'فارغ']):
  ```
- Line 315: potential_n_plus_one
  ```python
  for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
  ```
- Line 442: potential_n_plus_one
  ```python
  for i, header in enumerate(headers):
  ```

### orders/dashboard_views.py

#### Unused Imports (5)

- Line 8: `timezone` (from `django.utils.timezone`)
- Line 9: `datetime` (from `datetime.datetime`)
- Line 42: `Case` (from `django.db.models.Case`)
- Line 42: `When` (from `django.db.models.When`)
- Line 42: `IntegerField` (from `django.db.models.IntegerField`)

#### Unused Functions (5)

- Line 27: `orders_dashboard()`
- Line 129: `inspection_orders()`
- Line 196: `installation_orders()`
- Line 263: `accessory_orders()`
- Line 330: `tailoring_orders()`

#### Query Optimization Opportunities (10)

- Line 75: missing_select_related
  ```python
  orders_with_pending_inspections = orders.filter(inspections__status='pending').d
  ```
- Line 135: missing_select_related
  ```python
  orders = orders.filter(selected_types__icontains='inspection')
  ```
- Line 173: missing_select_related
  ```python
  pending_count = orders.filter(inspection_status__in=['not_scheduled', 'pending']
  ```
- Line 202: missing_select_related
  ```python
  orders = orders.filter(selected_types__icontains='installation')
  ```
- Line 269: missing_select_related
  ```python
  orders = orders.filter(selected_types__icontains='accessory')
  ```
- Line 307: missing_select_related
  ```python
  pending_count = orders.filter(tracking_status__in=['pending', 'processing']).cou
  ```
- Line 336: missing_select_related
  ```python
  orders = orders.filter(selected_types__icontains='tailoring')
  ```
- Line 362: missing_select_related
  ```python
  orders = orders.filter(contract_number__icontains=contract_filter)
  ```
- Line 382: missing_select_related
  ```python
  in_progress_count = orders.filter(tracking_status__in=['warehouse', 'factory', '
  ```
- Line 23: potential_n_plus_one
  ```python
  return [year.year for year in years]
  ```

### user_activity/admin.py

#### Unused Imports (5)

- Line 8: `mark_safe` (from `django.utils.safestring.mark_safe`)
- Line 9: `Count` (from `django.db.models.Count`)
- Line 9: `Q` (from `django.db.models.Q`)
- Line 10: `timezone` (from `django.utils.timezone`)
- Line 11: `timedelta` (from `datetime.timedelta`)

#### Unused Functions (8)

- Line 32: `online_duration_display()`
- Line 178: `has_add_permission()`
- Line 181: `has_change_permission()`
- Line 69: `action_type_display()`
- Line 80: `description_short()`
- Line 110: `duration_display()`
- Line 158: `user_display()`
- Line 172: `session_duration_display()`

#### Unused Classes (4)

- Line 17: `OnlineUserAdmin`
- Line 46: `UserActivityLogAdmin`
- Line 94: `UserSessionAdmin`
- Line 133: `UserLoginHistoryAdmin`

### cutting/models.py

#### Unused Imports (5)

- Line 3: `FileExtensionValidator` (from `django.core.validators.FileExtensionValidator`)
- Line 487: `post_save` (from `django.db.models.signals.post_save`)
- Line 488: `receiver` (from `django.dispatch.receiver`)
- Line 6: `Branch` (from `accounts.models.Branch`)
- Line 489: `Order` (from `orders.models.Order`)

#### Unused Functions (7)

- Line 352: `__str__()`
- Line 148: `save()`
- Line 360: `mark_as_completed()`
- Line 398: `mark_as_rejected()`
- Line 415: `reset_to_pending()`
- Line 460: `get_inventory_status_color()`
- Line 471: `update_products_order_status()`

#### Unused Classes (4)

- Line 11: `Section`
- Line 529: `Meta`
- Line 198: `CuttingOrderItem`
- Line 495: `CuttingReport`

### crm/dashboard_utils_backup.py

#### Unused Imports (4)

- Line 5: `F` (from `django.db.models.F`)
- Line 6: `datetime` (from `datetime.datetime`)
- Line 13: `Branch` (from `accounts.models.Branch`)
- Line 13: `DashboardYearSettings` (from `accounts.models.DashboardYearSettings`)

#### Unused Functions (12)

- Line 16: `get_customers_statistics()`
- Line 54: `get_orders_statistics()`
- Line 98: `get_manufacturing_statistics()`
- Line 130: `get_inspections_statistics()`
- Line 165: `get_installation_orders_statistics()`
- Line 197: `get_installations_statistics()`
- Line 233: `get_inventory_statistics()`
- Line 272: `get_enhanced_chart_data()`
- Line 282: `get_single_year_chart_data()`
- Line 323: `get_multi_year_chart_data()`
- Line 363: `calculate_growth_rate()`
- Line 382: `get_dashboard_summary()`

#### Query Optimization Opportunities (14)

- Line 22: missing_select_related
  ```python
  customers = customers.filter(created_at__range=(start_date, end_date))
  ```
- Line 39: missing_select_related
  ```python
  new_this_month = customers.filter(created_at__gte=current_month_start).count()
  ```
- Line 60: missing_select_related
  ```python
  orders = orders.filter(order_date__range=(start_date, end_date))
  ```
- Line 104: missing_select_related
  ```python
  manufacturing_orders = manufacturing_orders.filter(order__order_date__range=(sta
  ```
- Line 108: missing_select_related
  ```python
  manufacturing_orders = manufacturing_orders.filter(order__branch_id=branch_filte
  ```
- Line 136: missing_select_related
  ```python
  inspections = inspections.filter(created_at__range=(start_date, end_date))
  ```
- Line 176: missing_select_related
  ```python
  orders = orders.filter(order_date__range=(start_date, end_date))
  ```
- Line 204: missing_select_related
  ```python
  installations = installations.filter(created_at__range=(start_date, end_date))
  ```
- Line 208: missing_select_related
  ```python
  installations = installations.filter(order__branch_id=branch_filter)
  ```
- Line 285: missing_select_related
  ```python
  orders_monthly = Order.objects.filter(order_date__year=year)
  ```
- Line 297: missing_select_related
  ```python
  customers_monthly = Customer.objects.filter(created_at__year=year)
  ```
- Line 306: missing_select_related
  ```python
  inspections_monthly = Inspection.objects.filter(created_at__year=year)
  ```
- Line 369: missing_select_related
  ```python
  current_count = queryset.filter(**{f'{date_field}__gte': current_month}).count()
  ```
- Line 247: potential_n_plus_one
  ```python
  for product in products:
  ```

### crm/admin.py

#### Unused Imports (4)

- Line 6: `AdminSite` (from `django.contrib.admin.AdminSite`)
- Line 7: `_` (from `django.utils.translation.gettext_lazy`)
- Line 9: `format_html` (from `django.utils.html.format_html`)
- Line 18: `json` (from `json`)

#### Unused Functions (3)

- Line 99: `debt_management_view()`
- Line 169: `mark_debt_paid_view()`
- Line 222: `admin_dashboard_view()`

#### Unused Classes (1)

- Line 232: `JazzminAdminConfig`

#### Query Optimization Opportunities (2)

- Line 116: missing_select_related
  ```python
  debts = debts.filter(is_paid=False, created_at__lt=thirty_days_ago)
  ```
- Line 127: missing_select_related
  ```python
  debts = debts.filter(debt_amount__gte=min_amount_val)
  ```

### installations/views.py

#### Unused Imports (4)

- Line 13: `timedelta` (from `datetime.timedelta`)
- Line 3165: `ManufacturingOrder` (from `manufacturing.models.ManufacturingOrder`)
- Line 349: `apply_default_year_filter` (from `accounts.utils.apply_default_year_filter`)
- Line 2387: `Avg` (from `django.db.models.Avg`)

#### Unused Functions (59)

- Line 32: `currency_format()`
- Line 123: `dashboard()`
- Line 236: `change_installation_status()`
- Line 345: `installation_list()`
- Line 515: `sort_key()`
- Line 654: `schedule_installation()`
- Line 734: `update_status()`
- Line 879: `update_status_by_code()`
- Line 1027: `receive_completed_order()`
- Line 1037: `orders_modal()`
- Line 1145: `schedule_from_needs_scheduling()`
- Line 1198: `create_modification_request()`
- Line 1256: `modification_detail()`
- Line 1271: `upload_modification_images()`
- Line 1296: `create_manufacturing_order()`
- Line 1327: `manufacturing_order_detail()`
- Line 1340: `complete_manufacturing_order()`
- Line 1378: `modification_requests_list()`
- Line 1407: `manufacturing_orders_list()`
- Line 1434: `check_debt_before_schedule()`
- Line 1460: `quick_schedule_installation()`
- Line 3078: `daily_schedule()`
- Line 3161: `print_daily_schedule()`
- Line 1712: `add_payment()`
- Line 1736: `add_modification_report()`
- Line 1760: `add_receipt_memo()`
- Line 1784: `complete_installation()`
- Line 1826: `team_management()`
- Line 1859: `add_team()`
- Line 1878: `add_technician()`
- Line 1905: `add_driver()`
- Line 1929: `archive_list()`
- Line 1949: `installation_stats_api()`
- Line 2116: `manage_customer_debt()`
- Line 2147: `pay_debt()`
- Line 2173: `debt_list()`
- Line 2200: `schedule_manufacturing_order()`
- Line 2258: `edit_schedule()`
- Line 2303: `modification_error_analysis()`
- Line 2358: `add_error_analysis()`
- Line 2385: `installation_analytics()`
- Line 2486: `installation_event_logs()`
- Line 2548: `installation_in_progress_list()`
- Line 2588: `print_installation_schedule()`
- Line 2619: `view_scheduling_details()`
- Line 2646: `edit_scheduling_settings()`
- Line 2702: `get_installation_date_info()`
- Line 2725: `update_installation_date_from_scheduled()`
- Line 2776: `delete_installation()`
- Line 2788: `debt_orders_list()`
- Line 2892: `team_detail()`
- Line 2917: `edit_team()`
- Line 2939: `delete_team()`
- Line 2957: `edit_technician()`
- Line 2979: `delete_technician()`
- Line 3008: `edit_driver()`
- Line 3030: `delete_driver()`
- Line 3049: `installation_detail_by_code()`
- Line 3069: `installation_detail_redirect()`

#### Query Optimization Opportunities (39)

- Line 393: missing_select_related
  ```python
  scheduled_query = scheduled_query.filter(order__branch_id=branch_filter)
  ```
- Line 397: missing_select_related
  ```python
  scheduled_query = scheduled_query.filter(scheduled_date__gte=date_from_obj)
  ```
- Line 403: missing_select_related
  ```python
  scheduled_query = scheduled_query.filter(scheduled_date__lte=date_to_obj)
  ```
- Line 462: missing_select_related
  ```python
  ready_manufacturing_query = ready_manufacturing_query.filter(order__branch_id=br
  ```
- Line 1387: missing_select_related
  ```python
  modifications = modifications.filter(installation__status=status_filter)
  ```
- Line 1616: missing_select_related
  ```python
  installations = installations.filter(order__salesperson=salesperson)
  ```
- Line 1620: missing_select_related
  ```python
  installations = installations.filter(order__branch=branch)
  ```
- Line 1680: missing_select_related
  ```python
  installations = installations.filter(order__salesperson_id=salesperson_id)
  ```
- Line 1684: missing_select_related
  ```python
  installations = installations.filter(order__branch_id=branch_id)
  ```
- Line 1977: missing_select_related
  ```python
  total_orders = Order.objects.filter(selected_types__icontains='installation').co
  ```
- Line 2415: missing_select_related
  ```python
  team_stats = monthly_installations.filter(team__isnull=False).values(
  ```
- Line 2514: missing_select_related
  ```python
  event_logs = event_logs.filter(created_at__date__gte=date_from)
  ```
- Line 2516: missing_select_related
  ```python
  event_logs = event_logs.filter(created_at__date__lte=date_to)
  ```
- Line 2824: missing_select_related
  ```python
  debt_orders_query = debt_orders_query.filter(created_at__year=year_filter)
  ```
- Line 2828: missing_select_related
  ```python
  debt_orders_query = debt_orders_query.filter(created_at__month=month_filter)
  ```
- Line 3118: missing_select_related
  ```python
  installations_query = installations_query.filter(order__salesperson_id=salespers
  ```
- Line 3122: missing_select_related
  ```python
  installations_query = installations_query.filter(order__branch_id=branch_filter)
  ```
- Line 3202: missing_select_related
  ```python
  installations_query = installations_query.filter(order__salesperson_id=salespers
  ```
- Line 3206: missing_select_related
  ```python
  installations_query = installations_query.filter(order__branch_id=branch_filter)
  ```
- Line 198: potential_n_plus_one
  ```python
  for mfg_order in orders_needing_scheduling_queryset[:10]:
  ```
- Line 418: potential_n_plus_one
  ```python
  for installation in scheduled_query:
  ```
- Line 465: potential_n_plus_one
  ```python
  for mfg_order in ready_manufacturing_query:
  ```
- Line 500: potential_n_plus_one
  ```python
  for mfg_order in under_manufacturing_query:
  ```
- Line 541: potential_n_plus_one
  ```python
  scheduled_count = sum(1 for item in installation_items if item['status'] in ['sc
  ```
- Line 542: potential_n_plus_one
  ```python
  completed_count = sum(1 for item in installation_items if item['status'] == 'com
  ```
- Line 1057: potential_n_plus_one
  ```python
  for mfg_order in manufacturing_orders:
  ```
- Line 1068: potential_n_plus_one
  ```python
  for mfg in manufacturing_orders:
  ```
- Line 1076: potential_n_plus_one
  ```python
  orders = [schedule.order for schedule in schedules]
  ```
- Line 1094: potential_n_plus_one
  ```python
  orders = [mod.installation.order for mod in modifications]
  ```
- Line 1100: potential_n_plus_one
  ```python
  orders = [schedule.order for schedule in schedules]
  ```
- Line 1106: potential_n_plus_one
  ```python
  orders = [schedule.order for schedule in schedules]
  ```
- Line 1112: potential_n_plus_one
  ```python
  orders = [schedule.order for schedule in schedules]
  ```
- Line 1122: potential_n_plus_one
  ```python
  for mfg_order in manufacturing_orders:
  ```
- Line 1530: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 1832: potential_n_plus_one
  ```python
  for team in teams:
  ```
- Line 1840: potential_n_plus_one
  ```python
  technicians_in_team_ids = [tech.id for tech in technicians_in_teams]
  ```
- Line 2423: potential_n_plus_one
  ```python
  for day in range(1, calendar.monthrange(year, month)[1] + 1):
  ```
- Line 2452: potential_n_plus_one
  ```python
  for installation in completed_installations:
  ```
- Line 2989: potential_n_plus_one
  ```python
  teams_names = ', '.join([team.name for team in installation_teams])
  ```

### inventory/views.py

#### Unused Imports (4)

- Line 693: `Count` (from `django.db.models.Count`)
- Line 7: `Case` (from `django.db.models.Case`)
- Line 7: `When` (from `django.db.models.When`)
- Line 394: `Max` (from `django.db.models.Max`)

#### Unused Functions (12)

- Line 24: `get_context_data()`
- Line 137: `product_list()`
- Line 238: `product_create()`
- Line 281: `product_update()`
- Line 306: `product_delete()`
- Line 321: `product_detail()`
- Line 436: `transaction_create()`
- Line 587: `product_api_detail()`
- Line 607: `product_api_list()`
- Line 634: `product_api_autocomplete()`
- Line 701: `dashboard_view()`
- Line 729: `product_search_api()`

#### Unused Classes (1)

- Line 21: `InventoryDashboardView`

#### Query Optimization Opportunities (12)

- Line 74: missing_select_related
  ```python
  ).filter(product_count__gt=0)[:10]
  ```
- Line 55: potential_n_plus_one
  ```python
  for p in low_stock_products
  ```
- Line 81: potential_n_plus_one
  ```python
  for cat in category_stats
  ```
- Line 361: potential_n_plus_one
  ```python
  for warehouse in warehouses:
  ```
- Line 399: potential_n_plus_one
  ```python
  for warehouse in warehouses:
  ```
- Line 461: potential_n_plus_one
  ```python
  for warehouse in Warehouse.objects.filter(is_active=True):
  ```
- Line 616: potential_n_plus_one
  ```python
  products = [p for p in products if p.category.name == 'أقمشة']
  ```
- Line 618: potential_n_plus_one
  ```python
  products = [p for p in products if p.category.name == 'اكسسوارات']
  ```
- Line 630: potential_n_plus_one
  ```python
  } for p in products]
  ```
- Line 661: potential_n_plus_one
  ```python
  for p in products:
  ```
- Line 676: potential_n_plus_one
  ```python
  for p in products:
  ```
- Line 755: potential_n_plus_one
  ```python
  for product in products:
  ```

### inventory/views_extended.py

#### Unused Imports (4)

- Line 420: `Count` (from `django.db.models.Count`)
- Line 5: `F` (from `django.db.models.F`)
- Line 10: `WarehouseLocation` (from `models.WarehouseLocation`)
- Line 10: `PurchaseOrderItem` (from `models.PurchaseOrderItem`)

#### Unused Functions (17)

- Line 18: `category_list()`
- Line 44: `category_create()`
- Line 93: `category_update()`
- Line 137: `category_delete()`
- Line 164: `warehouse_list()`
- Line 214: `warehouse_create()`
- Line 307: `warehouse_update()`
- Line 366: `warehouse_delete()`
- Line 415: `warehouse_detail()`
- Line 502: `supplier_list()`
- Line 570: `supplier_create()`
- Line 622: `purchase_order_list()`
- Line 720: `purchase_order_create()`
- Line 775: `alert_list()`
- Line 847: `alert_resolve()`
- Line 864: `alert_ignore()`
- Line 882: `alert_resolve_multiple()`

#### Query Optimization Opportunities (15)

- Line 655: missing_select_related
  ```python
  purchase_orders = purchase_orders.filter(order_date__gte=start_of_week)
  ```
- Line 657: missing_select_related
  ```python
  purchase_orders = purchase_orders.filter(order_date__year=today.year, order_date
  ```
- Line 662: missing_select_related
  ```python
  purchase_orders = purchase_orders.filter(order_date__gte=quarter_start_date)
  ```
- Line 664: missing_select_related
  ```python
  purchase_orders = purchase_orders.filter(order_date__year=today.year)
  ```
- Line 668: missing_select_related
  ```python
  pending_orders = purchase_orders.filter(status__in=['draft', 'pending']).count()
  ```
- Line 801: missing_select_related
  ```python
  alerts = alerts.filter(created_at__date=today)
  ```
- Line 804: missing_select_related
  ```python
  alerts = alerts.filter(created_at__date__gte=start_of_week)
  ```
- Line 806: missing_select_related
  ```python
  alerts = alerts.filter(created_at__date__year=today.year, created_at__date__mont
  ```
- Line 891: missing_select_related
  ```python
  alerts = StockAlert.objects.filter(id__in=alert_id_list, status='active')
  ```
- Line 116: potential_n_plus_one
  ```python
  if category.id in [c.id for c in parent.get_ancestors(include_self=True)]:
  ```
- Line 169: potential_n_plus_one
  ```python
  for warehouse in warehouses:
  ```
- Line 451: potential_n_plus_one
  ```python
  for item in product_values:
  ```
- Line 465: potential_n_plus_one
  ```python
  for product_data in products_data:
  ```
- Line 890: potential_n_plus_one
  ```python
  alert_id_list = [int(id) for id in alert_ids.split(',')]
  ```
- Line 893: potential_n_plus_one
  ```python
  for alert in alerts:
  ```

### inventory/views_stock_analysis.py

#### Unused Imports (4)

- Line 6: `Q` (from `django.db.models.Q`)
- Line 6: `F` (from `django.db.models.F`)
- Line 6: `Avg` (from `django.db.models.Avg`)
- Line 9: `JsonResponse` (from `django.http.JsonResponse`)

#### Unused Functions (4)

- Line 18: `product_stock_movement()`
- Line 88: `warehouse_stock_analysis()`
- Line 157: `stock_movement_summary()`
- Line 222: `stock_discrepancy_report()`

#### Query Optimization Opportunities (3)

- Line 50: potential_n_plus_one
  ```python
  for warehouse in Warehouse.objects.filter(is_active=True):
  ```
- Line 116: potential_n_plus_one
  ```python
  for product in Product.objects.all():
  ```
- Line 226: potential_n_plus_one
  ```python
  for product in Product.objects.all():
  ```

### manufacturing/dashboard_view.py

#### Unused Imports (4)

- Line 5: `Sum` (from `django.db.models.Sum`)
- Line 10: `apply_default_year_filter` (from `accounts.utils.apply_default_year_filter`)
- Line 11: `DashboardYearSettings` (from `accounts.models.DashboardYearSettings`)
- Line 158: `Cast` (from `django.db.models.functions.Cast`)

#### Unused Functions (1)

- Line 18: `get_context_data()`

#### Unused Classes (1)

- Line 14: `ImprovedDashboardView`

#### Query Optimization Opportunities (2)

- Line 79: potential_n_plus_one
  ```python
  for status_code, status_display in ManufacturingOrder.STATUS_CHOICES:
  ```
- Line 108: potential_n_plus_one
  ```python
  for item in monthly_orders:
  ```

### notifications/admin.py

#### Unused Imports (4)

- Line 5: `Count` (from `django.db.models.Count`)
- Line 5: `Q` (from `django.db.models.Q`)
- Line 6: `timezone` (from `django.utils.timezone`)
- Line 7: `timedelta` (from `datetime.timedelta`)

#### Unused Functions (13)

- Line 183: `get_queryset()`
- Line 74: `notification_type_display()`
- Line 84: `priority_display()`
- Line 99: `created_by_display()`
- Line 106: `recipients_count()`
- Line 115: `unread_count()`
- Line 216: `created_at_display()`
- Line 131: `related_object_link()`
- Line 156: `has_add_permission()`
- Line 188: `notification_title()`
- Line 241: `user_display()`
- Line 198: `is_read_display()`
- Line 209: `read_at_display()`

#### Unused Classes (3)

- Line 24: `NotificationAdmin`
- Line 162: `NotificationVisibilityAdmin`
- Line 223: `NotificationSettingsAdmin`

### odoo_db_manager/google_sync.py

#### Unused Imports (4)

- Line 8: `datetime` (from `datetime`)
- Line 9: `Path` (from `pathlib.Path`)
- Line 12: `settings` (from `django.conf.settings`)
- Line 14: `connection` (from `django.db.connection`)

#### Unused Functions (26)

- Line 159: `__str__()`
- Line 66: `get_credentials()`
- Line 121: `is_sync_due()`
- Line 133: `update_last_sync()`
- Line 163: `sync_with_google_sheets()`
- Line 370: `sync_branches()`
- Line 415: `create_sheets_service()`
- Line 490: `sync_databases()`
- Line 535: `sync_users()`
- Line 580: `sync_customers()`
- Line 628: `sync_inspections()`
- Line 673: `sync_orders()`
- Line 792: `sync_products()`
- Line 852: `sync_settings()`
- Line 894: `sync_manufacturing_orders()`
- Line 958: `sync_technicians()`
- Line 997: `sync_installation_teams()`
- Line 1038: `sync_suppliers()`
- Line 1074: `sync_salespersons()`
- Line 1254: `sync_comprehensive_customers()`
- Line 1336: `sync_comprehensive_users()`
- Line 1386: `sync_comprehensive_inventory()`
- Line 1445: `sync_comprehensive_system_settings()`
- Line 1527: `sync_complete_orders_lifecycle()`
- Line 1737: `reverse_sync_from_google_sheets()`
- Line 1881: `process_reverse_sync_row()`

#### Unused Classes (1)

- Line 154: `Meta`

#### Query Optimization Opportunities (45)

- Line 1282: missing_select_related
  ```python
  manufacturing_orders_count = customer.customer_orders.filter(manufacturing_order
  ```
- Line 106: potential_n_plus_one
  ```python
  missing_fields = [field for field in required_fields if field not in credentials
  ```
- Line 377: potential_n_plus_one
  ```python
  fields = [f.name for f in Branch._meta.get_fields() if not f.many_to_many and no
  ```
- Line 379: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 388: potential_n_plus_one
  ```python
  for branch in branches:
  ```
- Line 390: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 440: potential_n_plus_one
  ```python
  missing_fields = [field for field in required_fields if field not in credentials
  ```
- Line 497: potential_n_plus_one
  ```python
  fields = [f.name for f in Database._meta.get_fields() if not f.many_to_many and 
  ```
- Line 499: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 508: potential_n_plus_one
  ```python
  for db in databases:
  ```
- Line 510: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 542: potential_n_plus_one
  ```python
  fields = [f.name for f in User._meta.get_fields() if not f.many_to_many and not 
  ```
- Line 544: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 553: potential_n_plus_one
  ```python
  for user in users:
  ```
- Line 555: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 588: potential_n_plus_one
  ```python
  fields = [f.name for f in Customer._meta.get_fields() if not f.many_to_many and 
  ```
- Line 591: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 600: potential_n_plus_one
  ```python
  for customer in customers:
  ```
- Line 602: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 640: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 694: potential_n_plus_one
  ```python
  for order in orders:
  ```
- Line 730: potential_n_plus_one
  ```python
  for type_code in types_list:
  ```
- Line 812: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 823: potential_n_plus_one
  ```python
  for product in products:
  ```
- Line 825: potential_n_plus_one
  ```python
  for f in fields:
  ```
- Line 911: potential_n_plus_one
  ```python
  for manufacturing_order in manufacturing_orders:
  ```
- Line 972: potential_n_plus_one
  ```python
  for technician in technicians:
  ```
- Line 1011: potential_n_plus_one
  ```python
  for team in teams:
  ```
- Line 1013: potential_n_plus_one
  ```python
  technician_names = ', '.join([tech.name for tech in team.technicians.all()])
  ```
- Line 1015: potential_n_plus_one
  ```python
  driver_names = ', '.join([driver.name for driver in team.drivers.all()])
  ```
- Line 1052: potential_n_plus_one
  ```python
  for supplier in suppliers:
  ```
- Line 1088: potential_n_plus_one
  ```python
  for salesperson in salespersons:
  ```
- Line 1134: potential_n_plus_one
  ```python
  for sheet in sheets:
  ```
- Line 1278: potential_n_plus_one
  ```python
  for customer in customers:
  ```
- Line 1285: potential_n_plus_one
  ```python
  total_orders_value = sum([order.total_amount or 0 for order in customer.customer
  ```
- Line 1296: potential_n_plus_one
  ```python
  invoice_numbers = [num for num in [last_order.invoice_number, last_order.invoice
  ```
- Line 1300: potential_n_plus_one
  ```python
  contract_numbers = [num for num in [last_order.contract_number, last_order.contr
  ```
- Line 1355: potential_n_plus_one
  ```python
  for user in users:
  ```
- Line 1405: potential_n_plus_one
  ```python
  for product in products:
  ```
- Line 1411: potential_n_plus_one
  ```python
  for trans in stock_transactions
  ```
- Line 1578: potential_n_plus_one
  ```python
  for order in orders:
  ```
- Line 1607: potential_n_plus_one
  ```python
  for type_code in types_list:
  ```
- Line 1757: potential_n_plus_one
  ```python
  for user in admin_users:
  ```
- Line 1766: potential_n_plus_one
  ```python
  admin_usernames = [user.username for user in admin_users]
  ```
- Line 1786: potential_n_plus_one
  ```python
  for sheet in sheets:
  ```

### odoo_db_manager/google_sync_advanced.py

#### Unused Imports (4)

- Line 8: `_` (from `django.utils.translation.gettext_lazy`)
- Line 12: `os` (from `os`)
- Line 13: `sys` (from `sys`)
- Line 564: `datetime` (from `datetime.datetime`)

#### Unused Functions (31)

- Line 553: `__str__()`
- Line 146: `get_column_mappings()`
- Line 156: `get_reverse_sync_fields()`
- Line 160: `set_column_mappings()`
- Line 167: `clean()`
- Line 178: `has_valid_mappings()`
- Line 186: `get_mapped_columns()`
- Line 195: `get_customer_related_fields()`
- Line 208: `get_order_related_fields()`
- Line 223: `get_manufacturing_related_fields()`
- Line 241: `should_create_customers()`
- Line 245: `should_create_orders()`
- Line 249: `get_clean_column_mappings()`
- Line 258: `validate_mappings()`
- Line 349: `get_duration()`
- Line 357: `get_success_rate()`
- Line 363: `is_running()`
- Line 367: `is_completed()`
- Line 371: `start_execution()`
- Line 377: `complete_execution()`
- Line 390: `update_progress()`
- Line 397: `start_task()`
- Line 401: `mark_completed()`
- Line 405: `mark_failed()`
- Line 468: `get_conflict_description()`
- Line 479: `is_pending()`
- Line 483: `resolve()`
- Line 494: `ignore()`
- Line 556: `is_due()`
- Line 562: `calculate_next_run()`
- Line 579: `record_execution()`

#### Unused Classes (3)

- Line 547: `Meta`
- Line 410: `GoogleSyncConflict`
- Line 502: `GoogleSyncSchedule`

#### Query Optimization Opportunities (7)

- Line 183: potential_n_plus_one
  ```python
  for field_type in mappings.values()
  ```
- Line 191: potential_n_plus_one
  ```python
  for col, field_type in mappings.items()
  ```
- Line 204: potential_n_plus_one
  ```python
  for col, field_type in mappings.items()
  ```
- Line 220: potential_n_plus_one
  ```python
  for col, field_type in mappings.items()
  ```
- Line 237: potential_n_plus_one
  ```python
  for col, field_type in mappings.items()
  ```
- Line 254: potential_n_plus_one
  ```python
  for col, field_type in mappings.items()
  ```
- Line 280: potential_n_plus_one
  ```python
  valid_mappings = [v for v in mappings.values() if v != 'ignore']
  ```

### odoo_db_manager/signals.py

#### Unused Imports (4)

- Line 5: `os` (from `os`)
- Line 9: `timezone` (from `django.utils.timezone`)
- Line 10: `settings` (from `django.conf.settings`)
- Line 11: `apps` (from `django.apps.apps`)

#### Unused Functions (2)

- Line 23: `handle_database_save()`
- Line 40: `handle_database_delete()`

### orders/invoice_admin.py

#### Unused Imports (4)

- Line 6: `path` (from `django.urls.path`)
- Line 7: `mark_safe` (from `django.utils.safestring.mark_safe`)
- Line 8: `redirect` (from `django.shortcuts.redirect`)
- Line 9: `HttpResponseRedirect` (from `django.http.HttpResponseRedirect`)

#### Unused Functions (7)

- Line 103: `save_model()`
- Line 109: `is_default_display()`
- Line 120: `preview_link()`
- Line 170: `has_add_permission()`
- Line 174: `has_change_permission()`
- Line 178: `order_link()`
- Line 190: `template_name()`

#### Unused Classes (3)

- Line 14: `InvoiceTemplateAdmin`
- Line 131: `Media`
- Line 139: `InvoicePrintLogAdmin`

### tests/test_notification_system.py

#### Unused Imports (4)

- Line 15: `TestCase` (from `django.test.TestCase`)
- Line 16: `reverse` (from `django.urls.reverse`)
- Line 21: `Order` (from `orders.models.Order`)
- Line 208: `CustomerCategory` (from `customers.models.CustomerCategory`)

#### Unused Functions (5)

- Line 25: `test_notification_creation()`
- Line 63: `test_notification_permissions()`
- Line 101: `test_notification_read_status()`
- Line 145: `test_notification_api()`
- Line 194: `test_notification_signals()`

### orders/services/google_drive_service.py

#### Unused Imports (4)

- Line 6: `json` (from `json`)
- Line 7: `settings` (from `django.conf.settings`)
- Line 9: `default_storage` (from `django.core.files.storage.default_storage`)
- Line 10: `ContentFile` (from `django.core.files.base.ContentFile`)

#### Unused Functions (8)

- Line 28: `__init__()`
- Line 33: `_initialize()`
- Line 64: `upload_contract_file()`
- Line 109: `_get_or_create_contracts_folder()`
- Line 155: `_generate_contract_filename()`
- Line 182: `_clean_filename()`
- Line 194: `_generate_file_description()`
- Line 238: `test_contract_file_upload_to_folder()`

### accounts/models.py

#### Unused Imports (3)

- Line 6: `ContentType` (from `django.contrib.contenttypes.models.ContentType`)
- Line 7: `GenericForeignKey` (from `django.contrib.contenttypes.fields.GenericForeignKey`)
- Line 8: `timesince` (from `django.utils.timesince.timesince`)

#### Unused Functions (13)

- Line 681: `__str__()`
- Line 42: `get_default_theme()`
- Line 575: `clean()`
- Line 634: `save()`
- Line 76: `get_user_role()`
- Line 99: `get_user_role_display()`
- Line 172: `get_full_path()`
- Line 196: `delete()`
- Line 330: `get_display_name()`
- Line 428: `assign_to_user()`
- Line 435: `remove_from_user()`
- Line 602: `get_icon_size_class()`
- Line 611: `get_display_duration_ms()`

#### Unused Classes (10)

- Line 10: `User`
- Line 676: `Meta`
- Line 208: `CompanyInfo`
- Line 250: `FormField`
- Line 290: `Employee`
- Line 444: `UserRole`
- Line 455: `ActivityLog`
- Line 472: `SystemSettings`
- Line 525: `BranchMessage`
- Line 656: `YearFilterExemption`

#### Query Optimization Opportunities (3)

- Line 442: missing_select_related
  ```python
  if not UserRole.objects.filter(user=user, role__permissions=permission).exists()
  ```
- Line 433: potential_n_plus_one
  ```python
  for permission in self.permissions.all():
  ```
- Line 441: potential_n_plus_one
  ```python
  for permission in self.permissions.all():
  ```

### inventory/dashboard_view_append.py

#### Unused Imports (3)

- Line 24: `Count` (from `django.db.models.Count`)
- Line 24: `Value` (from `django.db.models.Value`)
- Line 25: `Category` (from `models.Category`)

#### Unused Functions (4)

- Line 8: `get_context_data()`
- Line 29: `optimized_product_detail()`
- Line 61: `low_stock_report()`
- Line 101: `stock_movement_report()`

#### Unused Classes (1)

- Line 5: `InventoryDashboardView`

#### Query Optimization Opportunities (2)

- Line 11: potential_n_plus_one
  ```python
  context['low_stock_count'] = sum(1 for p in Product.objects.all() if p.current_s
  ```
- Line 13: potential_n_plus_one
  ```python
  context['inventory_value'] = sum(p.current_stock * p.price for p in Product.obje
  ```

### manufacturing/signals.py

#### Unused Imports (3)

- Line 1: `pre_save` (from `django.db.models.signals.pre_save`)
- Line 3: `timezone` (from `django.utils.timezone`)
- Line 5: `transaction` (from `django.db.transaction`)

#### Unused Functions (3)

- Line 52: `update_manufacturing_order_status()`
- Line 87: `delete_related_installation()`
- Line 132: `sync_order_to_manufacturing()`

#### Query Optimization Opportunities (5)

- Line 38: potential_n_plus_one
  ```python
  #             for item in instance.items.all():
  ```
- Line 67: potential_n_plus_one
  ```python
  if all(item.status == 'completed' for item in items):
  ```
- Line 70: potential_n_plus_one
  ```python
  elif any(item.status == 'in_progress' for item in items):
  ```
- Line 73: potential_n_plus_one
  ```python
  elif all(item.status == 'pending' for item in items):
  ```
- Line 162: potential_n_plus_one
  ```python
  **{field: getattr(manufacturing_order, field) for field in update_fields}
  ```

### odoo_db_manager/models.py

#### Unused Imports (3)

- Line 8: `datetime` (from `datetime.datetime`)
- Line 127: `load_dotenv` (from `dotenv.load_dotenv`)
- Line 318: `importlib` (from `importlib`)

#### Unused Functions (10)

- Line 686: `__str__()`
- Line 122: `update_env_file()`
- Line 233: `update_settings_file()`
- Line 263: `create_default_user()`
- Line 286: `activate()`
- Line 472: `calculate_next_run()`
- Line 576: `save()`
- Line 689: `update_progress()`
- Line 731: `set_completed()`
- Line 740: `set_failed()`

#### Unused Classes (4)

- Line 17: `ImportLog`
- Line 681: `Meta`
- Line 383: `BackupSchedule`
- Line 582: `RestoreProgress`

#### Query Optimization Opportunities (4)

- Line 116: potential_n_plus_one
  ```python
  total_size = sum(backup.size for backup in self.backups.all())
  ```
- Line 117: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB']:
  ```
- Line 160: potential_n_plus_one
  ```python
  for line in lines:
  ```
- Line 212: potential_n_plus_one
  ```python
  for line in lines:
  ```

### odoo_db_manager/views.py

#### Unused Imports (3)

- Line 9: `FileResponse` (from `django.http.FileResponse`)
- Line 14: `shutil` (from `shutil`)
- Line 935: `ContentType` (from `django.contrib.contenttypes.models.ContentType`)

#### Unused Functions (31)

- Line 31: `is_staff_or_superuser()`
- Line 37: `dashboard()`
- Line 167: `database_list()`
- Line 187: `database_discover()`
- Line 239: `database_detail()`
- Line 267: `database_create()`
- Line 395: `database_activate()`
- Line 475: `database_delete()`
- Line 519: `schedule_list()`
- Line 534: `schedule_detail()`
- Line 553: `schedule_create()`
- Line 594: `schedule_update()`
- Line 628: `schedule_delete()`
- Line 664: `schedule_toggle()`
- Line 688: `schedule_run_now()`
- Line 708: `scheduler_status()`
- Line 764: `_restore_json_simple()`
- Line 924: `_restore_json_simple_with_progress()`
- Line 1367: `google_drive_settings()`
- Line 1397: `google_drive_test_connection()`
- Line 1438: `google_drive_create_test_folder()`
- Line 1476: `google_drive_test_file_upload()`
- Line 1518: `google_drive_test_contract_upload()`
- Line 1559: `database_register()`
- Line 1609: `database_refresh_status()`
- Line 1647: `_create_default_user()`
- Line 1726: `_apply_migrations_to_database()`
- Line 1771: `restore_progress_stream()`
- Line 1827: `restore_progress_status()`
- Line 1868: `generate_temp_token()`
- Line 1901: `refresh_session()`

#### Query Optimization Opportunities (29)

- Line 44: potential_n_plus_one
  ```python
  for db in databases:
  ```
- Line 88: potential_n_plus_one
  ```python
  for db in databases:
  ```
- Line 213: potential_n_plus_one
  ```python
  for db_info in discovered_dbs:
  ```
- Line 380: potential_n_plus_one
  ```python
  for field, errors in form.errors.items():
  ```
- Line 381: potential_n_plus_one
  ```python
  for error in errors:
  ```
- Line 823: potential_n_plus_one
  ```python
  for app_label, model_name in required_content_types:
  ```
- Line 856: potential_n_plus_one
  ```python
  for model_name in priority_order:
  ```
- Line 857: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 860: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 864: potential_n_plus_one
  ```python
  for item in final_data:
  ```
- Line 872: potential_n_plus_one
  ```python
  for field in old_fields:
  ```
- Line 878: potential_n_plus_one
  ```python
  for item in final_data:
  ```
- Line 882: potential_n_plus_one
  ```python
  for model_name in reversed(priority_order):
  ```
- Line 895: potential_n_plus_one
  ```python
  for i, item in enumerate(final_data):
  ```
- Line 898: potential_n_plus_one
  ```python
  for obj in serializers.deserialize('json', json.dumps([item])):
  ```
- Line 906: potential_n_plus_one
  ```python
  for original_index, item, original_error in failed_items:
  ```
- Line 911: potential_n_plus_one
  ```python
  for obj in serializers.deserialize('json', json.dumps([item_copy])):
  ```
- Line 1024: potential_n_plus_one
  ```python
  for j, item in enumerate(batch):
  ```
- Line 1027: potential_n_plus_one
  ```python
  for obj in serializers.deserialize('json', json.dumps([item])):
  ```
- Line 1065: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 1112: potential_n_plus_one
  ```python
  for item in final_data:
  ```
- Line 1122: potential_n_plus_one
  ```python
  for model_name in deletion_order:
  ```
- Line 1142: potential_n_plus_one
  ```python
  for model_name in models_to_clear:
  ```
- Line 1208: potential_n_plus_one
  ```python
  for idx, item in enumerate(final_data):
  ```
- Line 1232: potential_n_plus_one
  ```python
  for field in old_fields:
  ```
- Line 1239: potential_n_plus_one
  ```python
  for field_name, field_value in fields.items():
  ```
- Line 1269: potential_n_plus_one
  ```python
  for deserialized_obj in serializers.deserialize('json', item_json):
  ```
- Line 1327: potential_n_plus_one
  ```python
  for i, error in enumerate(failed_items[:10], 1):
  ```
- Line 1617: potential_n_plus_one
  ```python
  for db in databases:
  ```

### reports/api_views.py

#### Unused Imports (3)

- Line 4: `Window` (from `django.db.models.Window`)
- Line 5: `ExtractHour` (from `django.db.models.functions.ExtractHour`)
- Line 13: `Report` (from `models.Report`)

#### Unused Functions (6)

- Line 51: `get_analytics_data()`
- Line 122: `get_kpi_details()`
- Line 227: `get_latest_analytics()`
- Line 243: `analyze_customer_segments()`
- Line 294: `calculate_growth()`
- Line 300: `calculate_average_growth()`

#### Query Optimization Opportunities (12)

- Line 61: missing_select_related
  ```python
  orders = Order.objects.filter(created_at__gte=start_date)
  ```
- Line 231: missing_select_related
  ```python
  recent_orders = Order.objects.filter(created_at__gte=last_hour)
  ```
- Line 232: missing_select_related
  ```python
  recent_customers = Customer.objects.filter(created_at__gte=last_hour)
  ```
- Line 70: potential_n_plus_one
  ```python
  historical_sales = [item['total_sales'] for item in sales_data]
  ```
- Line 97: potential_n_plus_one
  ```python
  for i, val in enumerate(sales_predictions)
  ```
- Line 140: potential_n_plus_one
  ```python
  'total_growth': calculate_growth([d['total_sales'] for d in data]),
  ```
- Line 141: potential_n_plus_one
  ```python
  'avg_monthly_growth': calculate_average_growth([d['total_sales'] for d in data])
  ```
- Line 147: potential_n_plus_one
  ```python
  for i in range(12):
  ```
- Line 174: potential_n_plus_one
  ```python
  'avg_rate': sum(m['rate'] for m in monthly_retention) / len(monthly_retention) i
  ```
- Line 195: potential_n_plus_one
  ```python
  'best_time': min(d['avg_time'].total_seconds()/3600 for d in data) if data else 
  ```
- Line 269: potential_n_plus_one
  ```python
  for customer in customers:
  ```
- Line 306: potential_n_plus_one
  ```python
  for i in range(1, len(values)):
  ```

### tests/test_manufacturing_integration.py

#### Unused Imports (3)

- Line 5: `override_settings` (from `django.test.override_settings`)
- Line 8: `SimpleUploadedFile` (from `django.core.files.uploadedfile.SimpleUploadedFile`)
- Line 9: `File` (from `django.core.files.File`)

#### Unused Functions (5)

- Line 28: `setUp()`
- Line 77: `test_manufacturing_order_creation()`
- Line 116: `test_order_status_update_when_manufacturing_completed()`
- Line 154: `test_manufacturing_order_ui()`
- Line 179: `test_manufacturing_order_status_update_api()`

#### Unused Classes (1)

- Line 23: `ManufacturingIntegrationTest`

### tests/test_notifications.py

#### Unused Imports (3)

- Line 16: `Customer` (from `customers.models.Customer`)
- Line 17: `Order` (from `orders.models.Order`)
- Line 86: `NotificationVisibility` (from `notifications.models.NotificationVisibility`)

### user_activity/models.py

#### Unused Imports (3)

- Line 8: `ValidationError` (from `django.core.exceptions.ValidationError`)
- Line 9: `format_html` (from `django.utils.html.format_html`)
- Line 11: `json` (from `json`)

#### Unused Functions (6)

- Line 651: `__str__()`
- Line 675: `end_session()`
- Line 263: `get_icon()`
- Line 291: `get_color_class()`
- Line 322: `get_entity_details()`
- Line 463: `update_activity()`

#### Unused Classes (3)

- Line 640: `Meta`
- Line 114: `UserActivityLog`
- Line 550: `UserLoginHistory`

#### Query Optimization Opportunities (1)

- Line 494: missing_select_related
  ```python
  cls.objects.filter(last_seen__lt=offline_threshold).delete()
  ```

### user_activity/signals.py

#### Unused Imports (3)

- Line 5: `post_delete` (from `django.db.models.signals.post_delete`)
- Line 9: `timezone` (from `django.utils.timezone`)
- Line 11: `UserSession` (from `models.UserSession`)

#### Unused Functions (4)

- Line 17: `handle_user_login()`
- Line 43: `handle_user_logout()`
- Line 82: `handle_user_update()`
- Line 101: `handle_user_deletion()`

### cutting/inventory_integration.py

#### Unused Imports (3)

- Line 8: `User` (from `django.contrib.auth.models.User`)
- Line 12: `Product` (from `inventory.models.Product`)
- Line 14: `CuttingOrderItem` (from `models.CuttingOrderItem`)

#### Unused Functions (3)

- Line 303: `deduct_inventory_for_cutting()`
- Line 308: `reverse_inventory_deduction()`
- Line 313: `check_cutting_stock_availability()`

#### Query Optimization Opportunities (2)

- Line 152: potential_n_plus_one
  ```python
  for item in cutting_order.items.all():
  ```
- Line 252: potential_n_plus_one
  ```python
  for trans in subsequent_transactions:
  ```

### odoo_db_manager/services/backup_service.py

#### Unused Imports (3)

- Line 15: `default_storage` (from `django.core.files.storage.default_storage`)
- Line 16: `ContentFile` (from `django.core.files.base.ContentFile`)
- Line 17: `connection` (from `django.db.connection`)

#### Unused Functions (15)

- Line 32: `create_backup()`
- Line 109: `_create_django_backup()`
- Line 296: `_create_postgresql_backup()`
- Line 403: `_get_postgresql_database_size()`
- Line 431: `_create_sqlite_backup()`
- Line 443: `restore_backup()`
- Line 702: `_restore_from_json()`
- Line 741: `_check_file_type()`
- Line 815: `_validate_json_file()`
- Line 830: `_convert_binary_pg_dump_to_sql()`
- Line 907: `_check_command_exists()`
- Line 916: `_restore_postgresql_backup()`
- Line 1006: `restore_from_file()`
- Line 1227: `delete_backup()`
- Line 235: `json_serial()`

#### Unused Classes (1)

- Line 21: `BackupService`

#### Query Optimization Opportunities (5)

- Line 203: potential_n_plus_one
  ```python
  for app_config in apps.get_app_configs():
  ```
- Line 204: potential_n_plus_one
  ```python
  for model in app_config.get_models():
  ```
- Line 212: potential_n_plus_one
  ```python
  for model in all_models:
  ```
- Line 224: potential_n_plus_one
  ```python
  for model_name in include_models:
  ```
- Line 1038: potential_n_plus_one
  ```python
  for chunk in uploaded_file.chunks():
  ```

### inspections/services/google_drive_service.py

#### Unused Imports (3)

- Line 7: `settings` (from `django.conf.settings`)
- Line 9: `default_storage` (from `django.core.files.storage.default_storage`)
- Line 10: `ContentFile` (from `django.core.files.base.ContentFile`)

#### Unused Functions (9)

- Line 28: `__init__()`
- Line 33: `_initialize()`
- Line 69: `upload_inspection_file()`
- Line 114: `_generate_file_description()`
- Line 129: `get_file_view_url()`
- Line 133: `test_connection()`
- Line 333: `create_test_folder()`
- Line 373: `test_file_upload_to_folder()`
- Line 424: `get_service_account_email()`

#### Query Optimization Opportunities (2)

- Line 225: potential_n_plus_one
  ```python
  for f in folders_found[:10]
  ```
- Line 238: potential_n_plus_one
  ```python
  for f in files_found[:5]
  ```

### accounts/middleware/log_terminal_activity.py

#### Unused Imports (3)

- Line 2: `json` (from `json`)
- Line 4: `timezone` (from `django.utils.timezone.timezone`)
- Line 6: `Session` (from `django.contrib.sessions.models.Session`)

#### Unused Functions (17)

- Line 23: `__init__()`
- Line 27: `process_request()`
- Line 42: `process_response()`
- Line 51: `_update_online_status()`
- Line 124: `_log_activity()`
- Line 188: `_get_or_create_session()`
- Line 215: `_determine_action_type()`
- Line 242: `_determine_entity_type()`
- Line 265: `_extract_entity_details()`
- Line 334: `_create_description()`
- Line 375: `_get_page_title()`
- Line 398: `_get_client_ip()`
- Line 407: `_get_device_info()`
- Line 421: `_get_device_type()`
- Line 435: `_get_browser_info()`
- Line 441: `_get_os_info()`
- Line 447: `_print_terminal_log()`

#### Unused Classes (1)

- Line 494: `TerminalActivityLoggerMiddleware`

#### Query Optimization Opportunities (5)

- Line 281: potential_n_plus_one
  ```python
  for pattern in id_patterns:
  ```
- Line 293: potential_n_plus_one
  ```python
  for field in name_fields:
  ```
- Line 301: potential_n_plus_one
  ```python
  for field in order_fields:
  ```
- Line 310: potential_n_plus_one
  ```python
  for field in search_fields:
  ```
- Line 392: potential_n_plus_one
  ```python
  for pattern, title in page_titles.items():
  ```

### accounts/management/commands/runserver.py

#### Unused Imports (3)

- Line 1: `os` (from `os`)
- Line 4: `sys` (from `sys`)
- Line 5: `threading` (from `threading`)

#### Unused Functions (1)

- Line 13: `handle()`

#### Unused Classes (1)

- Line 10: `Command`

### analyze_codebase.py

#### Unused Imports (2)

- Line 13: `os` (from `os`)
- Line 15: `defaultdict` (from `collections.defaultdict`)

#### Unused Functions (8)

- Line 22: `__init__()`
- Line 32: `visit_Import()`
- Line 43: `visit_ImportFrom()`
- Line 55: `visit_FunctionDef()`
- Line 65: `visit_ClassDef()`
- Line 87: `visit_Name()`
- Line 96: `visit_Call()`
- Line 115: `visit_For()`

#### Query Optimization Opportunities (21)

- Line 34: potential_n_plus_one
  ```python
  for alias in node.names:
  ```
- Line 45: potential_n_plus_one
  ```python
  for alias in node.names:
  ```
- Line 61: potential_n_plus_one
  ```python
  'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorat
  ```
- Line 74: potential_n_plus_one
  ```python
  for item in node.body:
  ```
- Line 81: potential_n_plus_one
  ```python
  'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in item.decorat
  ```
- Line 117: potential_n_plus_one
  ```python
  # Look for foreign key access in loops
  ```
- Line 118: potential_n_plus_one
  ```python
  for child in ast.walk(node):
  ```
- Line 120: potential_n_plus_one
  ```python
  # Pattern: for item in items: item.foreign_key.attribute
  ```
- Line 141: potential_n_plus_one
  ```python
  'unused_imports': {k: v for k, v in analyzer.imports.items() if not v['used']},
  ```
- Line 142: potential_n_plus_one
  ```python
  'unused_functions': {k: v for k, v in analyzer.functions.items()
  ```
- Line 145: potential_n_plus_one
  ```python
  for d in v['decorators'])},
  ```
- Line 146: potential_n_plus_one
  ```python
  'unused_classes': {k: v for k, v in analyzer.classes.items() if not v['used']},
  ```
- Line 182: potential_n_plus_one
  ```python
  for i, line in enumerate(content.split('\n'), 1):
  ```
- Line 193: potential_n_plus_one
  ```python
  for i, line in enumerate(lines):
  ```
- Line 194: potential_n_plus_one
  ```python
  if 'for ' in line and ' in ' in line:
  ```
- Line 196: potential_n_plus_one
  ```python
  for j in range(i+1, min(i+10, len(lines))):
  ```
- Line 270: potential_n_plus_one
  ```python
  for file_data in sorted(results['files'], key=lambda x: len(x['unused_imports'])
  ```
- Line 280: potential_n_plus_one
  ```python
  for name, info in file_data['unused_imports'].items():
  ```
- Line 286: potential_n_plus_one
  ```python
  for name, info in file_data['unused_functions'].items():
  ```
- Line 292: potential_n_plus_one
  ```python
  for name, info in file_data['unused_classes'].items():
  ```
- Line 298: potential_n_plus_one
  ```python
  for issue in file_data['query_optimizations']:
  ```

### accounts/activity_views.py

#### Unused Imports (2)

- Line 6: `user_passes_test` (from `django.contrib.auth.decorators.user_passes_test`)
- Line 17: `UserSession` (from `user_activity.models.UserSession`)

#### Unused Functions (8)

- Line 22: `online_users_api()`
- Line 202: `_parse_login_key()`
- Line 232: `user_activity_dashboard()`
- Line 277: `user_activity_detail()`
- Line 352: `activity_logs_list()`
- Line 417: `login_history_list()`
- Line 463: `update_current_page()`
- Line 496: `user_activities_api()`

#### Query Optimization Opportunities (14)

- Line 43: missing_select_related
  ```python
  request.user.groups.filter(name__in=['مدير النظام', 'Admin', 'Administrators']).
  ```
- Line 383: missing_select_related
  ```python
  activities = activities.filter(timestamp__date=timezone.now().date())
  ```
- Line 386: missing_select_related
  ```python
  activities = activities.filter(timestamp__gte=week_ago)
  ```
- Line 389: missing_select_related
  ```python
  activities = activities.filter(timestamp__gte=month_ago)
  ```
- Line 398: missing_select_related
  ```python
  users = User.objects.filter(activity_logs__isnull=False).distinct()
  ```
- Line 432: missing_select_related
  ```python
  logins = logins.filter(login_time__date=timezone.now().date())
  ```
- Line 435: missing_select_related
  ```python
  logins = logins.filter(login_time__gte=week_ago)
  ```
- Line 438: missing_select_related
  ```python
  logins = logins.filter(login_time__gte=month_ago)
  ```
- Line 447: missing_select_related
  ```python
  users = User.objects.filter(login_history__isnull=False).distinct()
  ```
- Line 51: potential_n_plus_one
  ```python
  for online_user in online_users:
  ```
- Line 126: potential_n_plus_one
  ```python
  for login_history in recent_login_users:
  ```
- Line 135: potential_n_plus_one
  ```python
  for login_history in unique_recent_users:
  ```
- Line 199: potential_n_plus_one
  ```python
  online_list = [u for u in users_data if u.get('is_online')]
  ```
- Line 200: potential_n_plus_one
  ```python
  offline_list = [u for u in users_data if not u.get('is_online')]
  ```

### accounts/signals.py

#### Unused Imports (2)

- Line 6: `UserRole` (from `models.UserRole`)
- Line 6: `Role` (from `models.Role`)

#### Unused Functions (4)

- Line 11: `assign_default_departments()`
- Line 19: `assign_departments()`
- Line 38: `log_user_login()`
- Line 90: `log_user_logout()`

#### Query Optimization Opportunities (1)

- Line 27: potential_n_plus_one
  ```python
  for dept in default_departments:
  ```

### backup_system/admin.py

#### Unused Imports (2)

- Line 6: `reverse` (from `django.urls.reverse`)
- Line 7: `timezone` (from `django.utils.timezone`)

#### Unused Functions (8)

- Line 161: `status_badge()`
- Line 177: `progress_bar()`
- Line 205: `file_size_display()`
- Line 100: `compressed_size_display()`
- Line 219: `has_add_permission()`
- Line 192: `success_rate_display()`
- Line 252: `is_active_badge()`
- Line 260: `save_model()`

#### Unused Classes (3)

- Line 12: `BackupJobAdmin`
- Line 120: `RestoreJobAdmin`
- Line 225: `BackupScheduleAdmin`

### backup_system/models.py

#### Unused Imports (2)

- Line 4: `os` (from `os`)
- Line 9: `settings` (from `django.conf.settings`)

#### Unused Functions (5)

- Line 319: `__str__()`
- Line 240: `update_progress()`
- Line 256: `mark_as_started()`
- Line 262: `mark_as_completed()`
- Line 270: `mark_as_failed()`

#### Unused Classes (3)

- Line 313: `Meta`
- Line 158: `RestoreJob`
- Line 279: `BackupSchedule`

#### Query Optimization Opportunities (4)

- Line 77: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
  ```
- Line 90: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
  ```
- Line 105: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
  ```
- Line 218: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
  ```

### complaints/admin_performance.py

#### Unused Imports (2)

- Line 4: `admin` (from `django.contrib.admin`)
- Line 5: `models` (from `django.db.models`)

#### Unused Functions (13)

- Line 11: `cache_admin_method()`
- Line 13: `decorator()`
- Line 15: `wrapper()`
- Line 83: `get_queryset()`
- Line 50: `get_list_display()`
- Line 67: `get_list_filter()`
- Line 100: `optimize_complaint_admin()`
- Line 124: `get_cached_customer_name()`
- Line 136: `get_cached_status_display()`
- Line 152: `get_cached_priority_display()`
- Line 177: `clear_complaint_cache()`
- Line 192: `get_user_complaint_permissions()`
- Line 227: `is_user_admin()`

#### Query Optimization Opportunities (4)

- Line 57: missing_select_related
  ```python
  user.groups.filter(name__in=['Complaints_Managers', 'Complaints_Supervisors']).e
  ```
- Line 73: missing_select_related
  ```python
  user.groups.filter(name__in=['Complaints_Managers', 'Complaints_Supervisors']).e
  ```
- Line 235: missing_select_related
  ```python
  user.groups.filter(name__in=[
  ```
- Line 60: potential_n_plus_one
  ```python
  for field in list_display:
  ```

### complaints/api_views.py

#### Unused Imports (2)

- Line 6: `csrf_exempt` (from `django.views.decorators.csrf.csrf_exempt`)
- Line 18: `notification_service` (from `services.notification_service.notification_service`)

#### Unused Functions (13)

- Line 807: `post()`
- Line 860: `has_permission()`
- Line 569: `mark_complaint_notification_read()`
- Line 602: `complaints_notifications_api()`
- Line 656: `clear_complaints_notifications()`
- Line 688: `assigned_complaints_api()`
- Line 730: `escalated_complaints_api()`
- Line 882: `complaint_search_api()`
- Line 958: `complaint_stats_api()`
- Line 1011: `user_notifications_api()`
- Line 1243: `get()`
- Line 1098: `mark_assignment_notification_read()`
- Line 1292: `get_complaint_type_responsible_staff()`

#### Unused Classes (10)

- Line 23: `ComplaintStatusUpdateView`
- Line 190: `ComplaintEscalationView`
- Line 342: `ComplaintAssignmentView`
- Line 485: `ComplaintNoteView`
- Line 802: `ComplaintAssignmentUpdateView`
- Line 1049: `AssignmentNotificationsView`
- Line 1123: `ResolutionMethodsView`
- Line 1150: `UsersForEscalationView`
- Line 1194: `UsersForAssignmentView`
- Line 1238: `UnresolvedComplaintsStatsView`

#### Query Optimization Opportunities (18)

- Line 156: missing_select_related
  ```python
  if user.groups.filter(name__in=['Complaints_Supervisors', 'Managers']).exists():
  ```
- Line 303: missing_select_related
  ```python
  if user.groups.filter(name__in=[
  ```
- Line 972: missing_select_related
  ```python
  complaints = Complaint.objects.filter(created_at__gte=start_date)
  ```
- Line 1253: missing_select_related
  ```python
  overdue_count = unresolved_complaints.filter(deadline__lt=timezone.now()).count(
  ```
- Line 1255: missing_select_related
  ```python
  unassigned_count = unresolved_complaints.filter(assigned_to__isnull=True).count(
  ```
- Line 1262: missing_select_related
  ```python
  request.user.groups.filter(name__in=[
  ```
- Line 1278: missing_select_related
  ```python
  request.user.groups.filter(name__in=[
  ```
- Line 620: potential_n_plus_one
  ```python
  for notification in notifications_queryset:
  ```
- Line 702: potential_n_plus_one
  ```python
  for complaint in assigned_complaints:
  ```
- Line 748: potential_n_plus_one
  ```python
  for escalation_info in latest_escalations:
  ```
- Line 763: potential_n_plus_one
  ```python
  for complaint in escalated_complaints:
  ```
- Line 922: potential_n_plus_one
  ```python
  for complaint in page_obj:
  ```
- Line 1024: potential_n_plus_one
  ```python
  for notification in notifications:
  ```
- Line 1069: potential_n_plus_one
  ```python
  for notification in assignment_notifications:
  ```
- Line 1133: potential_n_plus_one
  ```python
  for method in methods:
  ```
- Line 1167: potential_n_plus_one
  ```python
  for user in escalation_users:
  ```
- Line 1209: potential_n_plus_one
  ```python
  for user in assignment_users:
  ```
- Line 1321: potential_n_plus_one
  ```python
  for staff in responsible_staff.order_by('first_name', 'last_name'):
  ```

### complaints/tasks.py

#### Unused Imports (2)

- Line 8: `timezone` (from `django.utils.timezone`)
- Line 9: `timedelta` (from `datetime.timedelta`)

#### Unused Functions (2)

- Line 60: `cleanup_expired_cache()`
- Line 187: `system_health_check()`

#### Query Optimization Opportunities (2)

- Line 25: potential_n_plus_one
  ```python
  for alias in connections:
  ```
- Line 155: potential_n_plus_one
  ```python
  for worker, worker_stats in stats.items():
  ```

### complaints/urls.py

#### Unused Imports (2)

- Line 4: `clear_complaints_notifications` (from `api_views.clear_complaints_notifications`)
- Line 4: `assigned_complaints_api` (from `api_views.assigned_complaints_api`)

### crm/__init__.py

#### Unused Imports (2)

- Line 6: `celery_app` (from `celery.app`)
- Line 12: `signals` (from `signals`)

### crm/admin_enhancements.py

#### Unused Imports (2)

- Line 6: `ModelAdmin` (from `django.contrib.admin.ModelAdmin`)
- Line 7: `settings` (from `django.conf.settings`)

#### Unused Functions (9)

- Line 10: `enhance_admin_site()`
- Line 17: `auto_add_sortable_fields()`
- Line 70: `__init__()`
- Line 75: `enhance_all_admins()`
- Line 84: `enhance_admin_class()`
- Line 105: `__call__()`
- Line 99: `get_sortable_by()`
- Line 110: `add_admin_css()`
- Line 185: `add_admin_js()`

#### Unused Classes (1)

- Line 67: `AdminSortingMiddleware`

#### Query Optimization Opportunities (3)

- Line 20: potential_n_plus_one
  ```python
  for field_name in admin_class.list_display:
  ```
- Line 60: potential_n_plus_one
  ```python
  for field_name in admin_class.list_display:
  ```
- Line 80: potential_n_plus_one
  ```python
  for model, admin_class in admin.site._registry.items():
  ```

### crm/wsgi.py

#### Unused Imports (2)

- Line 6: `sys` (from `sys`)
- Line 8: `logging` (from `logging`)

### crm/settings.py

#### Unused Imports (2)

- Line 83: `connection` (from `django.db.connection`)
- Line 104: `ImproperlyConfigured` (from `django.core.exceptions.ImproperlyConfigured`)

#### Unused Functions (4)

- Line 87: `process_view()`
- Line 90: `process_response()`
- Line 576: `__init__()`
- Line 579: `__call__()`

#### Unused Classes (2)

- Line 86: `QueryPerformanceLoggingMiddleware`
- Line 575: `DisableCSRFMiddleware`

#### Query Optimization Opportunities (1)

- Line 572: potential_n_plus_one
  ```python
  # Disable CSRF for /api/ endpoints in development
  ```

### customers/services.py

#### Unused Imports (2)

- Line 6: `List` (from `typing.List`)
- Line 7: `F` (from `django.db.models.F`)

#### Unused Classes (2)

- Line 15: `CustomerService`
- Line 179: `CustomerCategoryService`

### customers/views_backup.py

#### Unused Imports (2)

- Line 15: `Order` (from `orders.models.Order`)
- Line 18: `get_user_customer_permissions` (from `permissions.get_user_customer_permissions`)

#### Unused Functions (17)

- Line 32: `customer_list()`
- Line 121: `customer_detail()`
- Line 200: `customer_create()`
- Line 258: `customer_update()`
- Line 301: `customer_delete()`
- Line 383: `add_customer_note()`
- Line 418: `delete_customer_note()`
- Line 432: `customer_category_list()`
- Line 443: `add_customer_category()`
- Line 468: `delete_customer_category()`
- Line 485: `get_customer_notes()`
- Line 508: `get_customer_details()`
- Line 539: `get_context_data()`
- Line 569: `test_customer_form()`
- Line 575: `find_customer_by_phone()`
- Line 597: `check_customer_phone()`
- Line 621: `update_customer_address()`

#### Unused Classes (1)

- Line 536: `CustomerDashboardView`

#### Query Optimization Opportunities (6)

- Line 101: potential_n_plus_one
  ```python
  for customer in page_obj:
  ```
- Line 161: potential_n_plus_one
  ```python
  for order in customer_orders:
  ```
- Line 324: potential_n_plus_one
  ```python
  for rel, label in relations.items():
  ```
- Line 336: potential_n_plus_one
  ```python
  for label, count in related_counts.items()
  ```
- Line 360: potential_n_plus_one
  ```python
  for model_name, rel_name in relations_found.items()
  ```
- Line 362: potential_n_plus_one
  ```python
  for obj in protected_objects)
  ```

### customers/views_temp.py

#### Unused Imports (2)

- Line 15: `Order` (from `orders.models.Order`)
- Line 18: `get_user_customer_permissions` (from `permissions.get_user_customer_permissions`)

#### Unused Functions (17)

- Line 32: `customer_list()`
- Line 124: `customer_detail()`
- Line 203: `customer_create()`
- Line 261: `customer_update()`
- Line 304: `customer_delete()`
- Line 386: `add_customer_note()`
- Line 421: `delete_customer_note()`
- Line 435: `customer_category_list()`
- Line 446: `add_customer_category()`
- Line 471: `delete_customer_category()`
- Line 488: `get_customer_notes()`
- Line 511: `get_customer_details()`
- Line 542: `get_context_data()`
- Line 572: `test_customer_form()`
- Line 578: `find_customer_by_phone()`
- Line 623: `check_customer_phone()`
- Line 647: `update_customer_address()`

#### Unused Classes (1)

- Line 539: `CustomerDashboardView`

#### Query Optimization Opportunities (7)

- Line 101: potential_n_plus_one
  ```python
  for customer in page_obj:
  ```
- Line 164: potential_n_plus_one
  ```python
  for order in customer_orders:
  ```
- Line 327: potential_n_plus_one
  ```python
  for rel, label in relations.items():
  ```
- Line 339: potential_n_plus_one
  ```python
  for label, count in related_counts.items()
  ```
- Line 363: potential_n_plus_one
  ```python
  for model_name, rel_name in relations_found.items()
  ```
- Line 365: potential_n_plus_one
  ```python
  for obj in protected_objects)
  ```
- Line 597: potential_n_plus_one
  ```python
  for customer in customers:
  ```

### important_script/fix_year_2025_to_2024.py

#### Unused Imports (2)

- Line 10: `datetime` (from `datetime.datetime`)
- Line 10: `timedelta` (from `datetime.timedelta`)

#### Query Optimization Opportunities (9)

- Line 63: missing_select_related
  ```python
  target_orders = Order.objects.filter(order_number__in=target_order_numbers)
  ```
- Line 120: missing_select_related
  ```python
  inspections = Inspection.objects.filter(order__in=target_orders)
  ```
- Line 162: missing_select_related
  ```python
  manufacturing_orders = ManufacturingOrder.objects.filter(order__in=target_orders
  ```
- Line 204: missing_select_related
  ```python
  installations = InstallationSchedule.objects.filter(order__in=target_orders)
  ```
- Line 90: potential_n_plus_one
  ```python
  for order in target_orders:
  ```
- Line 123: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 165: potential_n_plus_one
  ```python
  for manu_order in manufacturing_orders:
  ```
- Line 207: potential_n_plus_one
  ```python
  for installation in installations:
  ```
- Line 246: potential_n_plus_one
  ```python
  for order in target_orders:
  ```

### installations/tests.py

#### Unused Imports (2)

- Line 310: `ModificationReportForm` (from `forms.ModificationReportForm`)
- Line 310: `ReceiptMemoForm` (from `forms.ReceiptMemoForm`)

#### Unused Functions (27)

- Line 16: `setUp()`
- Line 76: `test_dashboard_view()`
- Line 82: `test_installation_list_view()`
- Line 88: `test_installation_detail_view()`
- Line 96: `test_schedule_installation_view()`
- Line 104: `test_update_status_view()`
- Line 116: `test_daily_schedule_view()`
- Line 122: `test_team_management_view()`
- Line 128: `test_add_payment_view()`
- Line 136: `test_add_modification_report_view()`
- Line 144: `test_add_receipt_memo_view()`
- Line 152: `test_archive_list_view()`
- Line 158: `test_installation_stats_api()`
- Line 167: `test_complete_installation_view()`
- Line 182: `test_technician_model()`
- Line 193: `test_driver_model()`
- Line 205: `test_installation_team_model()`
- Line 218: `test_installation_schedule_model()`
- Line 234: `test_installation_payment_model()`
- Line 250: `test_modification_report_model()`
- Line 260: `test_receipt_memo_model()`
- Line 273: `test_installation_archive_model()`
- Line 289: `test_installation_service()`
- Line 308: `test_forms()`
- Line 336: `test_permissions()`
- Line 343: `test_file_upload_validation()`
- Line 363: `tearDown()`

#### Unused Classes (1)

- Line 13: `InstallationsTestCase`

### installations/signals.py

#### Unused Imports (2)

- Line 3: `get_user_model` (from `django.contrib.auth.get_user_model`)
- Line 4: `F` (from `django.db.models.F`)

#### Unused Functions (4)

- Line 15: `installation_status_changed()`
- Line 50: `manage_customer_debt_on_order_save()`
- Line 101: `update_debt_payment_date()`
- Line 122: `installation_deleted()`

### inventory/views_backup.py

#### Unused Imports (2)

- Line 7: `F` (from `django.db.models.F`)
- Line 613: `Count` (from `django.db.models.Count`)

#### Unused Functions (12)

- Line 23: `get_context_data()`
- Line 136: `product_list()`
- Line 212: `product_create()`
- Line 255: `product_update()`
- Line 280: `product_delete()`
- Line 295: `product_detail()`
- Line 399: `transaction_create()`
- Line 507: `product_api_detail()`
- Line 527: `product_api_list()`
- Line 554: `product_api_autocomplete()`
- Line 621: `dashboard_view()`
- Line 649: `product_search_api()`

#### Unused Classes (1)

- Line 20: `InventoryDashboardView`

#### Query Optimization Opportunities (14)

- Line 331: missing_select_related
  ```python
  opening_transactions = all_transactions.filter(transaction_date__date__lt=start_
  ```
- Line 41: potential_n_plus_one
  ```python
  for p in products
  ```
- Line 67: potential_n_plus_one
  ```python
  for product in products_with_categories:
  ```
- Line 75: potential_n_plus_one
  ```python
  for category_name, products in category_products.items():
  ```
- Line 76: potential_n_plus_one
  ```python
  total_stock = sum(get_cached_stock_level(product.id) for product in products)
  ```
- Line 325: potential_n_plus_one
  ```python
  # Calculate the running balance for each day in the range
  ```
- Line 332: potential_n_plus_one
  ```python
  for trans in opening_transactions:
  ```
- Line 347: potential_n_plus_one
  ```python
  for trans in day_transactions:
  ```
- Line 536: potential_n_plus_one
  ```python
  products = [p for p in products if p.category.name == 'أقمشة']
  ```
- Line 538: potential_n_plus_one
  ```python
  products = [p for p in products if p.category.name == 'اكسسوارات']
  ```
- Line 550: potential_n_plus_one
  ```python
  } for p in products]
  ```
- Line 581: potential_n_plus_one
  ```python
  for p in products:
  ```
- Line 596: potential_n_plus_one
  ```python
  for p in products:
  ```
- Line 675: potential_n_plus_one
  ```python
  for product in products:
  ```

### inventory/views_reports.py

#### Unused Imports (2)

- Line 3: `Count` (from `django.db.models.Count`)
- Line 7: `get_cached_stock_level` (from `inventory_utils.get_cached_stock_level`)

#### Unused Functions (3)

- Line 10: `report_list()`
- Line 43: `low_stock_report()`
- Line 113: `stock_movement_report()`

#### Query Optimization Opportunities (10)

- Line 146: missing_select_related
  ```python
  transactions = transactions.filter(date__date=today)
  ```
- Line 149: missing_select_related
  ```python
  transactions = transactions.filter(date__date__gte=start_of_week)
  ```
- Line 151: missing_select_related
  ```python
  transactions = transactions.filter(date__date__year=today.year, date__date__mont
  ```
- Line 156: missing_select_related
  ```python
  transactions = transactions.filter(date__date__gte=quarter_start_date)
  ```
- Line 158: missing_select_related
  ```python
  transactions = transactions.filter(date__date__year=today.year)
  ```
- Line 14: potential_n_plus_one
  ```python
  low_stock_products = [p for p in products if 0 < p.current_stock_calc <= p.minim
  ```
- Line 57: potential_n_plus_one
  ```python
  low_stock_products = [p for p in products if 0 < p.current_stock_calc <= p.minim
  ```
- Line 58: potential_n_plus_one
  ```python
  out_of_stock_products = [p for p in products if p.current_stock_calc <= 0]
  ```
- Line 62: potential_n_plus_one
  ```python
  low_stock_products = [p for p in low_stock_products if
  ```
- Line 66: potential_n_plus_one
  ```python
  out_of_stock_products = [p for p in out_of_stock_products if
  ```

### inventory/forms.py

#### Unused Imports (2)

- Line 5: `openpyxl` (from `openpyxl`)
- Line 7: `UploadedFile` (from `django.core.files.uploadedfile.UploadedFile`)

#### Unused Functions (4)

- Line 161: `clean_excel_file()`
- Line 430: `__init__()`
- Line 344: `clean()`
- Line 408: `clean_quantity()`

#### Unused Classes (6)

- Line 11: `ProductExcelUploadForm`
- Line 119: `BulkStockUpdateForm`
- Line 239: `ProductForm`
- Line 372: `Meta`
- Line 301: `StockTransferForm`
- Line 427: `StockTransferReceiveForm`

#### Query Optimization Opportunities (7)

- Line 74: potential_n_plus_one
  ```python
  for row in sheet.iter_rows(values_only=True):
  ```
- Line 75: potential_n_plus_one
  ```python
  if any(cell is not None for cell in row):
  ```
- Line 93: potential_n_plus_one
  ```python
  for col in required_columns:
  ```
- Line 194: potential_n_plus_one
  ```python
  for row in sheet.iter_rows(values_only=True):
  ```
- Line 195: potential_n_plus_one
  ```python
  if any(cell is not None for cell in row):
  ```
- Line 213: potential_n_plus_one
  ```python
  for col in required_columns:
  ```
- Line 435: potential_n_plus_one
  ```python
  for item in transfer.items.all():
  ```

### inventory/views_stock_transfer.py

#### Unused Imports (2)

- Line 8: `Sum` (from `django.db.models.Sum`)
- Line 8: `Count` (from `django.db.models.Count`)

#### Unused Functions (14)

- Line 25: `stock_transfer_list()`
- Line 138: `stock_transfer_bulk()`
- Line 152: `stock_transfer_bulk_create()`
- Line 228: `stock_transfer_detail()`
- Line 252: `stock_transfer_edit()`
- Line 291: `stock_transfer_submit()`
- Line 312: `stock_transfer_approve()`
- Line 328: `stock_transfer_receive()`
- Line 396: `stock_transfer_cancel()`
- Line 414: `stock_transfer_delete()`
- Line 432: `get_warehouse_products()`
- Line 510: `get_product_stock()`
- Line 545: `get_similar_products()`
- Line 575: `get_pending_transfers_for_warehouse()`

#### Query Optimization Opportunities (5)

- Line 41: missing_select_related
  ```python
  request.user.groups.filter(name__in=['مسؤول مخازن', 'Warehouse Manager', 'مسؤول 
  ```
- Line 69: missing_select_related
  ```python
  transfers = transfers.filter(status__in=status_list)
  ```
- Line 198: potential_n_plus_one
  ```python
  for product_data in products:
  ```
- Line 355: potential_n_plus_one
  ```python
  for item in transfer.items.all():
  ```
- Line 453: potential_n_plus_one
  ```python
  for trans in latest_transactions:
  ```

### manufacturing/admin_backup.py

#### Unused Imports (2)

- Line 4: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)
- Line 149: `redirect` (from `django.shortcuts.redirect`)

#### Unused Functions (33)

- Line 515: `__init__()`
- Line 33: `save()`
- Line 67: `get_sortable_by()`
- Line 147: `bulk_update_status()`
- Line 180: `customer_name()`
- Line 194: `production_line_display()`
- Line 208: `contract_number()`
- Line 216: `exit_permit_display()`
- Line 222: `order_type_display()`
- Line 250: `order_date()`
- Line 258: `expected_delivery_date()`
- Line 266: `status_display()`
- Line 288: `delivery_info()`
- Line 308: `rejection_reply_status()`
- Line 328: `created_at()`
- Line 335: `get_urls()`
- Line 347: `manufacturing_order_by_code_view()`
- Line 371: `manufacturing_code()`
- Line 396: `get_queryset()`
- Line 624: `has_change_permission()`
- Line 632: `save_model()`
- Line 487: `get_branches_display()`
- Line 492: `get_supported_order_types_display()`
- Line 539: `clean()`
- Line 612: `has_module_permission()`
- Line 616: `has_view_permission()`
- Line 620: `has_add_permission()`
- Line 628: `has_delete_permission()`
- Line 638: `get_allowed_statuses_display()`
- Line 643: `get_allowed_order_types_display()`
- Line 648: `get_target_users_display()`
- Line 653: `orders_count()`
- Line 658: `active_orders_count()`

#### Unused Classes (6)

- Line 501: `Meta`
- Line 43: `ManufacturingOrderItemInline`
- Line 51: `ManufacturingOrderAdmin`
- Line 416: `ManufacturingOrderItemAdmin`
- Line 426: `ProductionLineAdmin`
- Line 561: `ManufacturingDisplaySettingsAdmin`

#### Query Optimization Opportunities (1)

- Line 244: potential_n_plus_one
  ```python
  type_names = [type_map.get(t, t) for t in selected_types]
  ```

### orders/cache_utils.py

#### Unused Imports (2)

- Line 148: `Inspection` (from `inspections.models.Inspection`)
- Line 147: `Salesperson` (from `accounts.models.Salesperson`)

#### Unused Functions (9)

- Line 51: `clear_customer_cache()`
- Line 62: `clear_inspection_cache()`
- Line 70: `clear_salesperson_cache()`
- Line 77: `clear_user_cache()`
- Line 109: `get_cached_user_customers()`
- Line 115: `get_cached_customer_inspections()`
- Line 144: `warm_up_cache()`
- Line 164: `clear_all_form_cache()`
- Line 184: `get_cache_stats()`

#### Query Optimization Opportunities (6)

- Line 18: potential_n_plus_one
  ```python
  for key in cache_keys:
  ```
- Line 32: potential_n_plus_one
  ```python
  for key in cache_keys:
  ```
- Line 44: potential_n_plus_one
  ```python
  for key in cache_keys:
  ```
- Line 135: potential_n_plus_one
  ```python
  for insp in inspections
  ```
- Line 152: potential_n_plus_one
  ```python
  for customer in active_customers:
  ```
- Line 157: potential_n_plus_one
  ```python
  for user in active_users:
  ```

### orders/permissions.py

#### Unused Imports (2)

- Line 4: `Permission` (from `django.contrib.auth.models.Permission`)
- Line 5: `ContentType` (from `django.contrib.contenttypes.models.ContentType`)

#### Unused Functions (6)

- Line 65: `can_user_view_order()`
- Line 126: `can_user_edit_order()`
- Line 171: `can_user_delete_order()`
- Line 205: `can_user_create_order_type()`
- Line 245: `apply_order_permissions()`
- Line 281: `get_user_role_permissions()`

#### Query Optimization Opportunities (9)

- Line 25: missing_select_related
  ```python
  return Order.objects.filter(selected_types__icontains='inspection')
  ```
- Line 29: missing_select_related
  ```python
  return Order.objects.filter(selected_types__icontains='installation')
  ```
- Line 35: missing_select_related
  ```python
  return Order.objects.filter(branch__in=managed_branches)
  ```
- Line 54: missing_select_related
  ```python
  return Order.objects.filter(selected_types__icontains='inspection')
  ```
- Line 258: missing_select_related
  ```python
  return orders_queryset.filter(branch__in=managed_branches)
  ```
- Line 275: missing_select_related
  ```python
  return orders_queryset.filter(selected_types__icontains='inspection')
  ```
- Line 295: potential_n_plus_one
  ```python
  return {key: True for key in permissions.keys()}
  ```
- Line 299: potential_n_plus_one
  ```python
  return {key: True for key in permissions.keys()}
  ```
- Line 303: potential_n_plus_one
  ```python
  return {key: True for key in permissions.keys()}
  ```

### orders/serializers.py

#### Unused Imports (2)

- Line 1: `serializers` (from `rest_framework.serializers`)
- Line 2: `Order` (from `models.Order`)

### orders/services.py

#### Unused Imports (2)

- Line 6: `List` (from `typing.List`)
- Line 13: `OrderItem` (from `models.OrderItem`)

#### Unused Classes (1)

- Line 15: `OrderService`

#### Query Optimization Opportunities (2)

- Line 66: missing_select_related
  ```python
  queryset = queryset.filter(created_at__gte=start_date)
  ```
- Line 69: missing_select_related
  ```python
  queryset = queryset.filter(created_at__lte=end_date)
  ```

### orders/cache.py

#### Unused Imports (2)

- Line 6: `settings` (from `django.conf.settings`)
- Line 158: `datetime` (from `datetime.datetime`)

#### Unused Functions (4)

- Line 308: `get_cached_delivery_settings()`
- Line 313: `get_cached_customer()`
- Line 318: `search_products_cached()`
- Line 323: `get_cached_order_stats()`

#### Query Optimization Opportunities (4)

- Line 49: potential_n_plus_one
  ```python
  for setting in delivery_settings:
  ```
- Line 128: potential_n_plus_one
  ```python
  for product in products:
  ```
- Line 279: potential_n_plus_one
  ```python
  for date_range in ['week', 'month', 'year']:
  ```
- Line 289: potential_n_plus_one
  ```python
  for key_pattern in CACHE_KEYS.values():
  ```

### orders/models.py

#### Unused Imports (2)

- Line 2564: `InvoiceTemplate` (from `invoice_models.InvoiceTemplate`)
- Line 2564: `InvoicePrintLog` (from `invoice_models.InvoicePrintLog`)

#### Unused Functions (50)

- Line 19: `validate_pdf_file()`
- Line 378: `calculate_final_price()`
- Line 2242: `save()`
- Line 567: `delete()`
- Line 597: `notify_status_change()`
- Line 609: `calculate_expected_delivery_date()`
- Line 659: `generate_unique_order_number()`
- Line 705: `upload_contract_to_google_drive()`
- Line 2695: `__str__()`
- Line 746: `get_absolute_url()`
- Line 751: `get_selected_types_list()`
- Line 790: `get_selected_type_display()`
- Line 808: `get_selected_types_display()`
- Line 861: `calculate_total()`
- Line 872: `get_smart_delivery_date()`
- Line 915: `get_installation_date()`
- Line 927: `get_installation_date_label()`
- Line 938: `get_expected_installation_date()`
- Line 951: `update_installation_status()`
- Line 982: `update_inspection_status()`
- Line 997: `update_completion_status()`
- Line 1023: `update_all_statuses()`
- Line 1035: `get_delivery_date_label()`
- Line 1070: `get_display_status()`
- Line 1174: `get_display_status_badge_class()`
- Line 1235: `get_display_status_icon()`
- Line 1295: `get_display_status_text()`
- Line 1367: `get_display_inspection_status()`
- Line 1483: `get_cutting_orders()`
- Line 1492: `order_post_save()`
- Line 1501: `update_order_installation_status()`
- Line 1571: `order_item_saved()`
- Line 1584: `order_item_deleted()`
- Line 1728: `get_clean_quantity_display()`
- Line 1759: `get_clean_discount_display()`
- Line 1777: `mark_cutting_completed()`
- Line 1790: `mark_cutting_rejected()`
- Line 1796: `get_cutting_status_display_color()`
- Line 1983: `get_icon()`
- Line 1997: `get_color_class()`
- Line 2061: `_status_label()`
- Line 2156: `_get_order_type_name()`
- Line 2192: `get_detailed_description()`
- Line 2544: `get_scheduling_date()`
- Line 2555: `get_scheduling_date_display()`
- Line 2589: `get_field_display_name()`
- Line 2599: `get_clean_old_value()`
- Line 2629: `get_clean_new_value()`
- Line 2698: `get_clean_old_total()`
- Line 2704: `get_clean_new_total()`

#### Unused Classes (7)

- Line 2686: `Meta`
- Line 1949: `OrderNote`
- Line 2012: `OrderStatusLog`
- Line 2380: `ManufacturingDeletionLog`
- Line 2423: `DeliveryTimeSettings`
- Line 2567: `OrderItemModificationLog`
- Line 2660: `OrderModificationLog`

#### Query Optimization Opportunities (14)

- Line 1083: missing_select_related
  ```python
  cutting_items = self.items.filter(cutting_status__in=['pending', 'in_progress'])
  ```
- Line 1558: missing_select_related
  ```python
  if order.items.filter(cutting_status__in=['pending', 'in_progress']).exists():
  ```
- Line 393: potential_n_plus_one
  ```python
  for item in self.items.select_related('product').all():
  ```
- Line 413: potential_n_plus_one
  ```python
  for item in self.items.all():
  ```
- Line 468: potential_n_plus_one
  ```python
  st.strip() for st in selected_types.split(',') if st.strip()
  ```
- Line 484: potential_n_plus_one
  ```python
  has_products = any(t in ['fabric', 'accessory'] for t in selected_types)
  ```
- Line 487: potential_n_plus_one
  ```python
  for t in selected_types
  ```
- Line 494: potential_n_plus_one
  ```python
  t for t in selected_types if t in [
  ```
- Line 623: potential_n_plus_one
  ```python
  for service in service_priority:
  ```
- Line 686: potential_n_plus_one
  ```python
  for attempt in range(max_attempts):
  ```
- Line 786: potential_n_plus_one
  ```python
  result = [match[0] or match[1] for match in matches]
  ```
- Line 824: potential_n_plus_one
  ```python
  arabic_types = [type_map.get(t, t) for t in types_list]
  ```
- Line 864: potential_n_plus_one
  ```python
  for item in self.items.all():
  ```
- Line 1536: potential_n_plus_one
  ```python
  # Signals for OrderItem to keep order totals in sync and update cutting status
  ```

### orders/signals.py

#### Unused Imports (2)

- Line 8: `get_user_model` (from `django.contrib.auth.get_user_model`)
- Line 9: `ObjectDoesNotExist` (from `django.core.exceptions.ObjectDoesNotExist`)

#### Unused Functions (32)

- Line 38: `track_order_changes()`
- Line 432: `track_price_changes()`
- Line 454: `create_manufacturing_order_on_order_creation()`
- Line 524: `sync_order_from_manufacturing()`
- Line 588: `create_inspection_on_order_creation()`
- Line 655: `set_default_delivery_option()`
- Line 672: `find_available_team()`
- Line 678: `calculate_windows_count()`
- Line 684: `create_production_order()`
- Line 691: `order_post_save()`
- Line 792: `order_item_post_save()`
- Line 981: `payment_post_save()`
- Line 1008: `update_order_manufacturing_status()`
- Line 1041: `log_manufacturing_order_deletion()`
- Line 1099: `track_order_item_changes()`
- Line 1114: `log_order_item_changes()`
- Line 1159: `log_order_item_creation()`
- Line 1178: `log_order_item_deletion()`
- Line 1210: `invalidate_order_cache_on_save()`
- Line 1229: `invalidate_order_cache_on_delete()`
- Line 1244: `invalidate_delivery_settings_cache_on_save()`
- Line 1256: `invalidate_customer_cache_on_save()`
- Line 1268: `invalidate_product_cache_on_save()`
- Line 1280: `invalidate_product_cache_on_delete()`
- Line 1294: `track_inspection_status_changes()`
- Line 1344: `track_inspection_changes_pre_save()`
- Line 1359: `track_cutting_status_changes()`
- Line 1397: `track_cutting_changes_pre_save()`
- Line 1412: `track_installation_changes_pre_save()`
- Line 1423: `track_installation_status_changes()`
- Line 1459: `track_manufacturing_changes_pre_save()`
- Line 1470: `track_manufacturing_status_changes()`

#### Query Optimization Opportunities (7)

- Line 1378: missing_select_related
  ```python
  changed_by = User.objects.filter(username__icontains=instance.cutter_name).first
  ```
- Line 31: potential_n_plus_one
  ```python
  for order_type in order_types:
  ```
- Line 166: potential_n_plus_one
  ```python
  for field_name, field_display in contract_fields:
  ```
- Line 237: potential_n_plus_one
  ```python
  for field_name, field_display in invoice_fields:
  ```
- Line 259: potential_n_plus_one
  ```python
  for field_name, field_display in address_fields:
  ```
- Line 562: potential_n_plus_one
  ```python
  Order.objects.filter(pk=order.pk).update(**{f: getattr(order, f) for f in update
  ```
- Line 757: potential_n_plus_one
  ```python
  for field_name in order_fields_to_track:
  ```

### templatetags/pagination_tags.py

#### Unused Imports (2)

- Line 7: `mark_safe` (from `django.utils.safestring.mark_safe`)
- Line 126: `Context` (from `django.template.Context`)

#### Unused Functions (13)

- Line 12: `pagination_url()`
- Line 53: `pagination_url_with_filters()`
- Line 104: `preserve_filters()`
- Line 121: `render_pagination()`
- Line 139: `add_page_param()`
- Line 149: `current_url_with_page()`
- Line 182: `build_filter_url()`
- Line 222: `get_filter_value()`
- Line 230: `is_filter_active()`
- Line 239: `clear_filter_url()`
- Line 255: `clear_all_filters_url()`
- Line 273: `get_page_range()`
- Line 291: `page_info()`

#### Query Optimization Opportunities (6)

- Line 39: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 90: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 114: potential_n_plus_one
  ```python
  for param in exclude_params:
  ```
- Line 168: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 208: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 266: potential_n_plus_one
  ```python
  for param in keep_params:
  ```

### tests/test_inspection_final.py

#### Unused Imports (2)

- Line 14: `Order` (from `orders.models.Order`)
- Line 18: `json` (from `json`)

#### Query Optimization Opportunities (1)

- Line 64: potential_n_plus_one
  ```python
  for key, value in form_data.items():
  ```

### tests/test_inspection_simple.py

#### Unused Imports (2)

- Line 14: `Order` (from `orders.models.Order`)
- Line 18: `json` (from `json`)

#### Query Optimization Opportunities (2)

- Line 63: potential_n_plus_one
  ```python
  for key, value in form_data.items():
  ```
- Line 153: potential_n_plus_one
  ```python
  for key, value in form_data.items():
  ```

### tests/test_user_file.py

#### Unused Imports (2)

- Line 6: `sys` (from `sys`)
- Line 10: `BytesIO` (from `io.BytesIO`)

#### Query Optimization Opportunities (7)

- Line 42: potential_n_plus_one
  ```python
  for sheet_name in wb.sheetnames:
  ```
- Line 49: potential_n_plus_one
  ```python
  for col in range(1, min(6, ws.max_column + 1)):
  ```
- Line 55: potential_n_plus_one
  ```python
  for row in range(2, min(6, ws.max_row + 1)):
  ```
- Line 57: potential_n_plus_one
  ```python
  for col in range(1, min(6, ws.max_column + 1)):
  ```
- Line 80: potential_n_plus_one
  ```python
  for col in df.columns:
  ```
- Line 113: potential_n_plus_one
  ```python
  for index, row in df.iterrows():
  ```
- Line 185: potential_n_plus_one
  ```python
  for file_name in file_list:
  ```

### manufacturing/templatetags/manufacturing_pagination.py

#### Unused Imports (2)

- Line 6: `urlencode` (from `django.utils.http.urlencode`)
- Line 7: `mark_safe` (from `django.utils.safestring.mark_safe`)

#### Unused Functions (3)

- Line 12: `manufacturing_pagination_url()`
- Line 58: `render_manufacturing_pagination()`
- Line 69: `get_manufacturing_page_range()`

#### Query Optimization Opportunities (2)

- Line 39: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 43: potential_n_plus_one
  ```python
  for v in value:
  ```

### manufacturing/tests/create_test_data.py

#### Unused Imports (2)

- Line 6: `datetime` (from `datetime.datetime`)
- Line 8: `DjangoValidationError` (from `django.core.exceptions.ValidationError`)

#### Query Optimization Opportunities (7)

- Line 62: potential_n_plus_one
  ```python
  for i in range(1, 6):
  ```
- Line 78: potential_n_plus_one
  ```python
  for cat_name in ['أبواب', 'نوافذ', 'مطابخ', 'ديكورات', 'إكسسوارات']:
  ```
- Line 86: potential_n_plus_one
  ```python
  for i in range(1, 11):
  ```
- Line 102: potential_n_plus_one
  ```python
  for i in range(5):
  ```
- Line 129: potential_n_plus_one
  ```python
  for j in range(random.randint(1, 3)):  # 1-3 عناصر لكل طلب
  ```
- Line 175: potential_n_plus_one
  ```python
  for item in order.items.all():
  ```
- Line 194: potential_n_plus_one
  ```python
  for order in Order.objects.all():
  ```

### installations/services/installation_service.py

#### Unused Imports (2)

- Line 3: `datetime` (from `datetime.datetime`)
- Line 3: `timedelta` (from `datetime.timedelta`)

#### Unused Classes (1)

- Line 7: `InstallationService`

#### Query Optimization Opportunities (2)

- Line 130: missing_select_related
  ```python
  installations = installations.filter(scheduled_date__gte=filters['date_from'])
  ```
- Line 132: missing_select_related
  ```python
  installations = installations.filter(scheduled_date__lte=filters['date_to'])
  ```

### crm/management/commands/fix_all_sequences.py

#### Unused Imports (2)

- Line 8: `transaction` (from `django.db.transaction`)
- Line 10: `settings` (from `django.conf.settings`)

#### Unused Functions (9)

- Line 19: `add_arguments()`
- Line 41: `handle()`
- Line 63: `fix_all_sequences()`
- Line 98: `fix_app_sequences()`
- Line 134: `fix_single_table()`
- Line 152: `fix_table_sequence()`
- Line 208: `extract_sequence_name()`
- Line 217: `fix_sequence()`
- Line 279: `get_all_sequences_info()`

#### Unused Classes (1)

- Line 16: `Command`

#### Query Optimization Opportunities (3)

- Line 79: potential_n_plus_one
  ```python
  for app_name in local_apps:
  ```
- Line 114: potential_n_plus_one
  ```python
  for model in models:
  ```
- Line 190: potential_n_plus_one
  ```python
  for column_name, column_default, is_identity in auto_columns:
  ```

### complaints/services/notification_service.py

#### Unused Imports (2)

- Line 11: `async_to_sync` (from `asgiref.sync.async_to_sync`)
- Line 186: `ComplaintUserPermissions` (from `complaints.models.ComplaintUserPermissions`)

#### Unused Functions (16)

- Line 25: `__init__()`
- Line 28: `notify_new_complaint()`
- Line 73: `notify_status_change()`
- Line 129: `notify_assignment_change()`
- Line 163: `notify_deadline_approaching()`
- Line 181: `notify_overdue_to_escalation_users()`
- Line 233: `notify_overdue_complaints_daily()`
- Line 277: `notify_overdue()`
- Line 307: `notify_escalation()`
- Line 337: `_send_notification()`
- Line 361: `_send_websocket_notification()`
- Line 369: `_send_email_notification()`
- Line 400: `_hide_old_assignment_notifications()`
- Line 432: `_cleanup_mismatched_assignment_notifications()`
- Line 461: `_hide_old_notifications_for_resolved_complaint()`
- Line 482: `cleanup_old_notifications()`

#### Query Optimization Opportunities (9)

- Line 490: missing_select_related
  ```python
  resolved_complaints = Complaint.objects.filter(status__in=['resolved', 'closed']
  ```
- Line 504: missing_select_related
  ```python
  active_complaints = Complaint.objects.filter(status__in=['new', 'in_progress', '
  ```
- Line 60: potential_n_plus_one
  ```python
  for supervisor in supervisors:
  ```
- Line 209: potential_n_plus_one
  ```python
  for group in admin_groups:
  ```
- Line 218: potential_n_plus_one
  ```python
  for user in escalation_users:
  ```
- Line 252: potential_n_plus_one
  ```python
  for complaint in overdue_complaints:
  ```
- Line 447: potential_n_plus_one
  ```python
  for notification in assignment_notifications:
  ```
- Line 493: potential_n_plus_one
  ```python
  for complaint in resolved_complaints:
  ```
- Line 506: potential_n_plus_one
  ```python
  for complaint in active_complaints:
  ```

### complaints/management/commands/test_overdue_system.py

#### Unused Imports (2)

- Line 8: `ComplaintUserPermissions` (from `complaints.models.ComplaintUserPermissions`)
- Line 9: `Department` (from `accounts.models.Department`)

#### Unused Functions (5)

- Line 20: `add_arguments()`
- Line 32: `handle()`
- Line 53: `create_test_data()`
- Line 119: `test_notification_system()`
- Line 156: `check_current_overdue_complaints()`

#### Unused Classes (1)

- Line 17: `Command`

#### Query Optimization Opportunities (3)

- Line 176: potential_n_plus_one
  ```python
  for complaint in overdue_complaints:
  ```
- Line 197: potential_n_plus_one
  ```python
  for user in escalation_users:
  ```
- Line 209: potential_n_plus_one
  ```python
  for group in admin_groups:
  ```

### monitor_indexes.py

#### Unused Imports (1)

- Line 16: `Tuple` (from `typing.Tuple`)

#### Unused Functions (11)

- Line 34: `__init__()`
- Line 40: `connect_to_database()`
- Line 58: `get_index_usage_stats()`
- Line 97: `get_unused_indexes()`
- Line 134: `get_table_sizes()`
- Line 173: `get_slow_queries()`
- Line 218: `generate_recommendations()`
- Line 255: `_format_bytes()`
- Line 263: `generate_monitoring_report()`
- Line 319: `_print_summary()`
- Line 344: `disconnect_from_database()`

#### Query Optimization Opportunities (11)

- Line 79: potential_n_plus_one
  ```python
  for row in self.cursor.fetchall():
  ```
- Line 118: potential_n_plus_one
  ```python
  for row in self.cursor.fetchall():
  ```
- Line 155: potential_n_plus_one
  ```python
  for row in self.cursor.fetchall():
  ```
- Line 203: potential_n_plus_one
  ```python
  for row in self.cursor.fetchall():
  ```
- Line 225: potential_n_plus_one
  ```python
  total_unused_size = sum(idx['size_bytes'] for idx in unused_indexes)
  ```
- Line 233: potential_n_plus_one
  ```python
  for idx in largest_unused:
  ```
- Line 239: potential_n_plus_one
  ```python
  high_usage = [idx for idx in index_stats if idx['scans'] > 10000]
  ```
- Line 257: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
  ```
- Line 280: potential_n_plus_one
  ```python
  total_index_size = sum(idx['size_bytes'] for idx in index_stats)
  ```
- Line 281: potential_n_plus_one
  ```python
  total_unused_size = sum(idx['size_bytes'] for idx in unused_indexes)
  ```
- Line 339: potential_n_plus_one
  ```python
  for rec in report['recommendations'][:5]:
  ```

### accounts/apps.py

#### Unused Imports (1)

- Line 10: `signals` (from `signals`)

#### Unused Functions (1)

- Line 8: `ready()`

#### Unused Classes (1)

- Line 4: `AccountsConfig`

### accounts/core_departments.py

#### Unused Imports (1)

- Line 4: `_` (from `django.utils.translation.gettext_lazy`)

#### Unused Functions (1)

- Line 109: `create_core_departments()`

#### Query Optimization Opportunities (10)

- Line 167: missing_select_related
  ```python
  Department.objects.filter(code__in=core_dept_codes).update(is_core=True)
  ```
- Line 168: missing_select_related
  ```python
  Department.objects.filter(code__in=core_child_codes).update(is_core=True)
  ```
- Line 116: potential_n_plus_one
  ```python
  core_dept_codes = [dept['code'] for dept in CORE_DEPARTMENTS]
  ```
- Line 119: potential_n_plus_one
  ```python
  for dept in CORE_DEPARTMENTS:
  ```
- Line 120: potential_n_plus_one
  ```python
  for child in dept.get('children', []):
  ```
- Line 124: potential_n_plus_one
  ```python
  for dept_data in CORE_DEPARTMENTS:
  ```
- Line 126: potential_n_plus_one
  ```python
  dept_data_clean = {k: v for k, v in dept_data.items() if k != 'children'}
  ```
- Line 138: potential_n_plus_one
  ```python
  for key, value in dept_data_copy.items():
  ```
- Line 148: potential_n_plus_one
  ```python
  for child_data in children:
  ```
- Line 157: potential_n_plus_one
  ```python
  for key, value in child_data.items():
  ```

### accounts/middleware.py

#### Unused Imports (1)

- Line 1: `Permission` (from `django.contrib.auth.models.Permission`)

#### Unused Functions (1)

- Line 13: `process_request()`

#### Unused Classes (1)

- Line 7: `RoleBasedPermissionsMiddleware`

#### Query Optimization Opportunities (1)

- Line 32: potential_n_plus_one
  ```python
  for user_role in user.user_roles.select_related('role').all():
  ```

### accounts/mixins.py

#### Unused Imports (1)

- Line 2: `PermissionDenied` (from `django.core.exceptions.PermissionDenied`)

#### Unused Functions (2)

- Line 88: `test_func()`
- Line 91: `handle_no_permission()`

#### Unused Classes (4)

- Line 9: `DepartmentRequiredMixin`
- Line 33: `PermissionRequiredMixin`
- Line 56: `BranchAccessMixin`
- Line 82: `StaffRequiredMixin`

### backup_system/forms.py

#### Unused Imports (1)

- Line 5: `RestoreJob` (from `models.RestoreJob`)

#### Unused Functions (1)

- Line 112: `clean_backup_file()`

#### Unused Classes (4)

- Line 8: `BackupForm`
- Line 40: `RestoreForm`
- Line 72: `UploadBackupForm`
- Line 140: `BackupScheduleForm`

#### Query Optimization Opportunities (1)

- Line 120: potential_n_plus_one
  ```python
  for ext in allowed_extensions:
  ```

### complaints/apps.py

#### Unused Imports (1)

- Line 10: `complaints` (from `complaints.signals`)

#### Unused Functions (1)

- Line 9: `ready()`

#### Unused Classes (1)

- Line 4: `ComplaintsConfig`

### complaints/forms.py

#### Unused Imports (1)

- Line 9: `Customer` (from `customers.models.Customer`)

#### Unused Functions (5)

- Line 539: `__init__()`
- Line 136: `update_related_order_queryset()`
- Line 681: `clean()`
- Line 262: `clean_related_order()`
- Line 525: `save()`

#### Unused Classes (11)

- Line 16: `ComplaintForm`
- Line 552: `Meta`
- Line 328: `ComplaintUpdateForm`
- Line 360: `ComplaintStatusUpdateForm`
- Line 394: `ComplaintAssignmentForm`
- Line 429: `ComplaintEscalationForm`
- Line 466: `ComplaintAttachmentForm`
- Line 490: `ComplaintResolutionForm`
- Line 536: `ComplaintCustomerRatingForm`
- Line 561: `ComplaintFilterForm`
- Line 644: `ComplaintBulkActionForm`

#### Query Optimization Opportunities (8)

- Line 127: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 350: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 380: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 413: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 449: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 473: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 512: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 543: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```

### complaints/forms_backup.py

#### Unused Imports (1)

- Line 8: `Customer` (from `customers.models.Customer`)

#### Unused Functions (3)

- Line 319: `__init__()`
- Line 306: `save()`
- Line 413: `clean()`

#### Unused Classes (11)

- Line 15: `ComplaintForm`
- Line 332: `Meta`
- Line 135: `ComplaintUpdateForm`
- Line 163: `ComplaintStatusUpdateForm`
- Line 191: `ComplaintAssignmentForm`
- Line 225: `ComplaintEscalationForm`
- Line 255: `ComplaintAttachmentForm`
- Line 279: `ComplaintResolutionForm`
- Line 316: `ComplaintCustomerRatingForm`
- Line 341: `ComplaintFilterForm`
- Line 376: `ComplaintBulkActionForm`

#### Query Optimization Opportunities (8)

- Line 95: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 142: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 177: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 211: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 238: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 262: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 293: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```
- Line 323: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```

### complaints/models.py

#### Unused Imports (1)

- Line 6: `_` (from `django.utils.translation.gettext_lazy`)

#### Unused Functions (15)

- Line 1391: `__str__()`
- Line 719: `save()`
- Line 369: `calculate_business_hours_deadline()`
- Line 397: `generate_complaint_number()`
- Line 447: `get_absolute_url()`
- Line 472: `can_be_closed_by_user()`
- Line 504: `get_status_badge_class()`
- Line 516: `get_priority_badge_class()`
- Line 701: `clean()`
- Line 877: `check_breach_level()`
- Line 894: `get_performance_metrics()`
- Line 1019: `mark_as_read()`
- Line 1120: `generate_title()`
- Line 1128: `generate_description()`
- Line 1401: `can_accept_new_complaint()`

#### Unused Classes (10)

- Line 1386: `Meta`
- Line 527: `ComplaintUpdate`
- Line 655: `ComplaintAttachment`
- Line 730: `ComplaintEscalation`
- Line 799: `ComplaintSLA`
- Line 951: `ComplaintNotification`
- Line 1067: `ComplaintTemplate`
- Line 1138: `ComplaintEvaluation`
- Line 1254: `ResolutionMethod`
- Line 1291: `ComplaintUserPermissions`

#### Query Optimization Opportunities (7)

- Line 479: missing_select_related
  ```python
  if user.is_superuser or user.groups.filter(name__in=['Managers', 'Complaints_Sup
  ```
- Line 899: missing_select_related
  ```python
  complaints = complaints.filter(created_at__gte=start_date)
  ```
- Line 901: missing_select_related
  ```python
  complaints = complaints.filter(created_at__lte=end_date)
  ```
- Line 915: missing_select_related
  ```python
  satisfied = complaints.filter(customer_rating__gte=4).count()
  ```
- Line 318: potential_n_plus_one
  ```python
  [int(d) for d in self.complaint_type.working_days.split(',')]
  ```
- Line 422: potential_n_plus_one
  ```python
  for attempt in range(max_attempts):
  ```
- Line 923: potential_n_plus_one
  ```python
  for complaint in complaints:
  ```

### complaints/signals.py

#### Unused Imports (1)

- Line 4: `reverse` (from `django.urls.reverse`)

#### Unused Functions (6)

- Line 10: `handle_complaint_notifications()`
- Line 17: `handle_status_change_notifications()`
- Line 39: `handle_post_save_notifications()`
- Line 71: `handle_update_notifications()`
- Line 93: `handle_escalation_notifications()`
- Line 118: `check_complaint_deadlines()`

#### Query Optimization Opportunities (5)

- Line 82: potential_n_plus_one
  ```python
  for recipient in recipients:
  ```
- Line 127: potential_n_plus_one
  ```python
  for complaint in deadline_approaching:
  ```
- Line 147: potential_n_plus_one
  ```python
  for complaint in overdue:
  ```
- Line 156: potential_n_plus_one
  ```python
  for complaint in overdue:
  ```
- Line 163: potential_n_plus_one
  ```python
  for recipient in recipients:
  ```

### complaints/views.py

#### Unused Imports (1)

- Line 439: `datetime` (from `datetime.datetime`)

#### Unused Functions (37)

- Line 1687: `get_context_data()`
- Line 172: `calculate_avg_resolution_time()`
- Line 512: `get_queryset()`
- Line 275: `apply_complaint_permissions()`
- Line 1677: `dispatch()`
- Line 502: `get_object()`
- Line 785: `get_form_kwargs()`
- Line 2189: `form_valid()`
- Line 724: `form_invalid()`
- Line 760: `get_success_url()`
- Line 805: `complaint_status_update()`
- Line 883: `start_working_on_complaint()`
- Line 919: `complaint_assignment()`
- Line 955: `complaint_add_update()`
- Line 974: `complaint_escalate()`
- Line 1066: `complaint_resolve()`
- Line 1106: `mark_complaint_as_resolved()`
- Line 1137: `complaint_add_attachment()`
- Line 1156: `customer_rating()`
- Line 1183: `start_action_on_escalated_complaint()`
- Line 1219: `close_complaint()`
- Line 1257: `customer_complaints()`
- Line 1282: `complaints_statistics()`
- Line 1323: `bulk_action()`
- Line 1359: `complaints_analysis()`
- Line 1475: `notifications_list()`
- Line 1571: `mark_notification_as_read()`
- Line 1583: `mark_all_notifications_as_read()`
- Line 1594: `delete_notification()`
- Line 1603: `notification_bulk_action()`
- Line 1631: `ajax_complaint_stats()`
- Line 1750: `create_evaluation()`
- Line 1807: `search_customers()`
- Line 1857: `get_customer_info()`
- Line 1879: `get_customer_orders()`
- Line 1978: `get_complaint_type_fields()`
- Line 2090: `get_department_staff()`

#### Unused Classes (9)

- Line 34: `ComplaintDashboardView`
- Line 196: `ComplaintListView`
- Line 326: `AdminComplaintListView`
- Line 412: `ComplaintReportsView`
- Line 496: `ComplaintDetailView`
- Line 596: `ComplaintCreateView`
- Line 764: `ComplaintUpdateView`
- Line 1673: `ComplaintEvaluationReportView`
- Line 2183: `ExportComplaintsView`

#### Query Optimization Opportunities (46)

- Line 255: missing_select_related
  ```python
  queryset = queryset.filter(customer__name__icontains=customer_name)
  ```
- Line 259: missing_select_related
  ```python
  queryset = queryset.filter(id__icontains=complaint_id)
  ```
- Line 269: missing_select_related
  ```python
  queryset = queryset.filter(status='closed', evaluation__isnull=False)
  ```
- Line 271: missing_select_related
  ```python
  queryset = queryset.filter(status='closed', evaluation__isnull=True)
  ```
- Line 298: missing_select_related
  ```python
  return queryset.filter(assigned_department__in=managed_departments)
  ```
- Line 318: missing_select_related
  ```python
  self.request.user.groups.filter(name__in=[
  ```
- Line 337: missing_select_related
  ```python
  request.user.groups.filter(name__in=[
  ```
- Line 402: missing_select_related
  ```python
  'overdue_count': all_unresolved.filter(deadline__lt=timezone.now()).count(),
  ```
- Line 404: missing_select_related
  ```python
  'unassigned_count': all_unresolved.filter(assigned_to__isnull=True).count(),
  ```
- Line 419: missing_select_related
  ```python
  request.user.groups.filter(name__in=[
  ```
- Line 444: missing_select_related
  ```python
  context['this_week'] = all_complaints.filter(created_at__date__gte=week_ago).cou
  ```
- Line 445: missing_select_related
  ```python
  context['this_month'] = all_complaints.filter(created_at__date__gte=month_ago).c
  ```
- Line 490: missing_select_related
  ```python
  ).filter(resolved_count__gt=0).order_by('-resolved_count')[:5]
  ```
- Line 987: missing_select_related
  ```python
  elif user.groups.filter(name__in=[
  ```
- Line 1029: missing_select_related
  ```python
  escalated_to.groups.filter(name__in=['Complaints_Managers', 'Complaints_Supervis
  ```
- Line 1333: missing_select_related
  ```python
  complaints = Complaint.objects.filter(id__in=complaint_ids)
  ```
- Line 1438: missing_select_related
  ```python
  ).filter(count__gte=3).order_by('-avg_rating')  # فقط الطرق التي استخدمت 3 مرات 
  ```
- Line 1448: missing_select_related
  ```python
  ).filter(count__gte=3).order_by('avg_time')[:5]
  ```
- Line 1502: missing_select_related
  ```python
  today_notifications = base_queryset.filter(created_at__date=timezone.now().date(
  ```
- Line 1541: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date=today)
  ```
- Line 1544: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date__gte=start_of_week)
  ```
- Line 1546: missing_select_related
  ```python
  queryset = queryset.filter(created_at__month=today.month, created_at__year=today
  ```
- Line 1651: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date__gte=date_from)
  ```
- Line 1653: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date__lte=date_to)
  ```
- Line 1680: missing_select_related
  ```python
  request.user.groups.filter(name__in=[
  ```
- Line 2194: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date__gte=form.cleaned_data['date_from'])
  ```
- Line 2197: missing_select_related
  ```python
  queryset = queryset.filter(created_at__date__lte=form.cleaned_data['date_to'])
  ```
- Line 2200: missing_select_related
  ```python
  queryset = queryset.filter(status__in=form.cleaned_data['status'])
  ```
- Line 2203: missing_select_related
  ```python
  queryset = queryset.filter(complaint_type__in=form.cleaned_data['complaint_type'
  ```
- Line 2206: missing_select_related
  ```python
  queryset = queryset.filter(priority__in=form.cleaned_data['priority'])
  ```
- Line 479: potential_n_plus_one
  ```python
  for complaint in resolved_complaints
  ```
- Line 623: potential_n_plus_one
  ```python
  for field_name, field_value in form.cleaned_data.items():
  ```
- Line 731: potential_n_plus_one
  ```python
  for field, errors in form.errors.items():
  ```
- Line 737: potential_n_plus_one
  ```python
  for error in form.non_field_errors():
  ```
- Line 742: potential_n_plus_one
  ```python
  for key, value in self.request.POST.items():
  ```
- Line 1340: potential_n_plus_one
  ```python
  for complaint in complaints:
  ```
- Line 1406: potential_n_plus_one
  ```python
  for method in resolution_methods_stats:
  ```
- Line 1451: potential_n_plus_one
  ```python
  for method in fastest_methods:
  ```
- Line 1556: potential_n_plus_one
  ```python
  for notification in page_obj:
  ```
- Line 1830: potential_n_plus_one
  ```python
  for customer in customers:
  ```
- Line 1896: potential_n_plus_one
  ```python
  for order in orders:
  ```
- Line 1994: potential_n_plus_one
  ```python
  for user in responsible_staff:
  ```
- Line 2013: potential_n_plus_one
  ```python
  for user in dept_staff:
  ```
- Line 2038: potential_n_plus_one
  ```python
  for user in all_qualified_staff:
  ```
- Line 2052: potential_n_plus_one
  ```python
  for dept in all_departments:
  ```
- Line 2104: potential_n_plus_one
  ```python
  for user in staff_users:
  ```

### core/decorators.py

#### Unused Imports (1)

- Line 7: `login_required` (from `django.contrib.auth.decorators.login_required`)

#### Unused Functions (3)

- Line 11: `ajax_login_required()`
- Line 42: `wrapper()`
- Line 36: `api_login_required()`

### crm/admin_performance.py

#### Unused Imports (1)

- Line 5: `models` (from `django.db.models`)

#### Unused Functions (6)

- Line 11: `cache_queryset()`
- Line 13: `decorator()`
- Line 15: `wrapper()`
- Line 32: `get_queryset()`
- Line 50: `changelist_view()`
- Line 76: `optimize_admin_performance()`

#### Unused Classes (1)

- Line 29: `PerformanceMixin`

#### Query Optimization Opportunities (1)

- Line 85: potential_n_plus_one
  ```python
  for model_admin in [admin.site._registry.get(Order),
  ```

### crm/apps.py

#### Unused Imports (1)

- Line 16: `crm` (from `crm.signals`)

#### Unused Functions (1)

- Line 14: `ready()`

#### Unused Classes (1)

- Line 8: `CrmConfig`

### crm/db_pool.py

#### Unused Imports (1)

- Line 7: `time` (from `time`)

#### Unused Functions (12)

- Line 25: `__new__()`
- Line 239: `__init__()`
- Line 48: `_create_pool()`
- Line 181: `get_connection()`
- Line 135: `get_stats()`
- Line 145: `close_all_connections()`
- Line 156: `health_check()`
- Line 223: `reset_fallback()`
- Line 243: `__call__()`
- Line 266: `get_pool_statistics()`
- Line 272: `cleanup_pool()`
- Line 290: `execute_query()`

#### Unused Classes (1)

- Line 234: `ConnectionPoolMiddleware`

#### Query Optimization Opportunities (1)

- Line 141: potential_n_plus_one
  ```python
  'available_connections': len([c for c in self._pool._pool if c]),
  ```

### crm/health.py

#### Unused Imports (1)

- Line 5: `os` (from `os`)

#### Unused Functions (1)

- Line 7: `health_check()`

### crm/middleware.py

#### Unused Imports (1)

- Line 14: `AccessToken` (from `rest_framework_simplejwt.tokens.AccessToken`)

#### Unused Functions (7)

- Line 95: `process_request()`
- Line 280: `process_response()`
- Line 389: `__init__()`
- Line 392: `__call__()`
- Line 150: `process_exception()`
- Line 355: `add_lazy_loading()`
- Line 375: `_get_user()`

#### Unused Classes (10)

- Line 22: `BlockWebSocketMiddleware`
- Line 92: `QueryAnalysisMiddleware`
- Line 141: `DebugMiddleware`
- Line 192: `QueryPerformanceMiddleware`
- Line 245: `PerformanceCookiesMiddleware`
- Line 276: `CustomGZipMiddleware`
- Line 298: `PerformanceMiddleware`
- Line 330: `LazyLoadMiddleware`
- Line 367: `JWTAuthenticationMiddleware`
- Line 388: `JWTAuthMiddleware`

#### Query Optimization Opportunities (6)

- Line 45: potential_n_plus_one
  ```python
  for blocked_path in blocked_paths:
  ```
- Line 119: potential_n_plus_one
  ```python
  for query in connection.queries[-total_queries:]:
  ```
- Line 130: potential_n_plus_one
  ```python
  "\n".join([f"  - {q['time']:.3f}s: {q['sql']}" for q in slow_queries])
  ```
- Line 165: potential_n_plus_one
  ```python
  for key, value in request.POST.items():
  ```
- Line 221: potential_n_plus_one
  ```python
  for query in connection.queries[start_queries:end_queries]:
  ```
- Line 233: potential_n_plus_one
  ```python
  "\n".join([f"Time: {q['time']:.4f}s: {q['sql']}" for q in slow_queries])
  ```

### crm/resource_tracker.py

#### Unused Imports (1)

- Line 5: `settings` (from `django.conf.settings`)

#### Unused Functions (7)

- Line 16: `__init__()`
- Line 20: `_start_monitoring()`
- Line 29: `_monitor_resources()`
- Line 64: `stop_monitoring()`
- Line 72: `track_resource_usage()`
- Line 77: `wrapper()`
- Line 101: `cleanup_resources()`

### crm/settings_backup.py

#### Unused Imports (1)

- Line 5: `dj_database_url` (from `dj_database_url`)

#### Unused Functions (2)

- Line 430: `__init__()`
- Line 433: `__call__()`

#### Unused Classes (1)

- Line 429: `DisableCSRFMiddleware`

#### Query Optimization Opportunities (2)

- Line 31: potential_n_plus_one
  ```python
  ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',')]
  ```
- Line 426: potential_n_plus_one
  ```python
  # Disable CSRF for /api/ endpoints in development
  ```

### customers/apps.py

#### Unused Imports (1)

- Line 10: `customers` (from `customers.signals`)

#### Unused Functions (1)

- Line 9: `ready()`

#### Unused Classes (1)

- Line 4: `CustomersConfig`

### customers/forms.py

#### Unused Imports (1)

- Line 5: `DiscountType` (from `models.DiscountType`)

#### Unused Functions (6)

- Line 251: `__init__()`
- Line 96: `clean_image()`
- Line 295: `clean_phone()`
- Line 144: `clean_phone2()`
- Line 207: `clean_note()`
- Line 213: `save()`

#### Unused Classes (4)

- Line 8: `CustomerForm`
- Line 265: `Meta`
- Line 184: `CustomerNoteForm`
- Line 221: `CustomerSearchForm`

#### Query Optimization Opportunities (1)

- Line 91: potential_n_plus_one
  ```python
  for t in CustomerType.objects.filter(is_active=True).order_by('name')]
  ```

### customers/signals.py

#### Unused Imports (1)

- Line 4: `get_customer_types` (from `models.get_customer_types`)

#### Unused Functions (1)

- Line 7: `update_customer_type_choices()`

#### Query Optimization Opportunities (1)

- Line 15: potential_n_plus_one
  ```python
  types = [(t.code, t.name) for t in CustomerType.objects.filter(is_active=True).o
  ```

### customers/admin.py

#### Unused Imports (1)

- Line 5: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)

#### Unused Functions (18)

- Line 24: `__init__()`
- Line 34: `clean_customer_type()`
- Line 67: `note_preview()`
- Line 384: `save_model()`
- Line 95: `get_formset()`
- Line 100: `clean()`
- Line 170: `customer_type_display()`
- Line 182: `customer_image()`
- Line 192: `birth_date_display()`
- Line 201: `get_queryset()`
- Line 219: `get_urls()`
- Line 231: `customer_by_code_view()`
- Line 242: `customer_code_display()`
- Line 269: `has_change_permission()`
- Line 275: `has_delete_permission()`
- Line 281: `delete_model()`
- Line 308: `delete_queryset()`
- Line 371: `customers_count()`

#### Unused Classes (8)

- Line 46: `Meta`
- Line 52: `CustomerCategoryAdmin`
- Line 60: `CustomerNoteAdmin`
- Line 78: `CustomerTypeAdmin`
- Line 120: `CustomerAdmin`
- Line 343: `Media`
- Line 350: `DiscountTypeAdmin`
- Line 395: `CustomerResponsibleAdmin`

#### Query Optimization Opportunities (2)

- Line 37: potential_n_plus_one
  ```python
  valid_choices = [choice[0] for choice in get_customer_types()]
  ```
- Line 106: potential_n_plus_one
  ```python
  for form in self.forms:
  ```

### customers/views.py

#### Unused Imports (1)

- Line 15: `Order` (from `orders.models.Order`)

#### Unused Functions (22)

- Line 51: `customer_list()`
- Line 212: `customer_detail()`
- Line 314: `customer_create()`
- Line 377: `customer_update()`
- Line 428: `customer_delete()`
- Line 510: `add_customer_note()`
- Line 561: `add_customer_note_by_code()`
- Line 646: `delete_customer_note()`
- Line 660: `customer_category_list()`
- Line 671: `add_customer_category()`
- Line 696: `delete_customer_category()`
- Line 713: `get_customer_notes()`
- Line 736: `get_customer_details()`
- Line 773: `get_context_data()`
- Line 818: `test_customer_form()`
- Line 824: `find_customer_by_phone()`
- Line 869: `check_customer_phone()`
- Line 933: `update_customer_address()`
- Line 988: `customer_api()`
- Line 1043: `customer_detail_by_code()`
- Line 1179: `customer_detail_redirect()`
- Line 1192: `save_customer_responsibles()`

#### Unused Classes (1)

- Line 770: `CustomerDashboardView`

#### Query Optimization Opportunities (17)

- Line 150: potential_n_plus_one
  ```python
  customer_ids = [customer.pk for customer in page_obj]
  ```
- Line 251: potential_n_plus_one
  ```python
  for order in customer_orders:
  ```
- Line 451: potential_n_plus_one
  ```python
  for rel, label in relations.items():
  ```
- Line 463: potential_n_plus_one
  ```python
  for label, count in related_counts.items()
  ```
- Line 487: potential_n_plus_one
  ```python
  for model_name, rel_name in relations_found.items()
  ```
- Line 489: potential_n_plus_one
  ```python
  for obj in protected_objects)
  ```
- Line 545: potential_n_plus_one
  ```python
  for field, errors in form.errors.items():
  ```
- Line 546: potential_n_plus_one
  ```python
  for error in errors:
  ```
- Line 597: potential_n_plus_one
  ```python
  for recent_note in recent_notes:
  ```
- Line 626: potential_n_plus_one
  ```python
  for field, errors in form.errors.items():
  ```
- Line 627: potential_n_plus_one
  ```python
  for error in errors:
  ```
- Line 843: potential_n_plus_one
  ```python
  for customer in customers:
  ```
- Line 1025: potential_n_plus_one
  ```python
  for customer in page_obj:
  ```
- Line 1133: potential_n_plus_one
  ```python
  for order in customer_orders:
  ```
- Line 1203: potential_n_plus_one
  ```python
  for key, value in request.POST.items():
  ```
- Line 1237: potential_n_plus_one
  ```python
  for r in responsibles_data:
  ```
- Line 1244: potential_n_plus_one
  ```python
  for i, responsible_data in enumerate(responsibles_data, 1):
  ```

### important_script/check_inspection_dates.py

#### Unused Imports (1)

- Line 8: `timezone` (from `django.utils.timezone`)

#### Query Optimization Opportunities (3)

- Line 45: missing_select_related
  ```python
  orders = Order.objects.filter(order_number__in=suspicious_order_numbers)
  ```
- Line 64: potential_n_plus_one
  ```python
  for order in orders.order_by('order_number'):
  ```
- Line 78: potential_n_plus_one
  ```python
  for i, inspection in enumerate(inspections, 1):
  ```

### important_script/fix_inspection_dates_complete.py

#### Unused Imports (1)

- Line 10: `datetime` (from `datetime.datetime`)

#### Query Optimization Opportunities (6)

- Line 47: missing_select_related
  ```python
  target_orders = Order.objects.filter(order_number__in=target_order_numbers)
  ```
- Line 71: potential_n_plus_one
  ```python
  for order in target_orders.order_by('order_number'):
  ```
- Line 84: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 118: potential_n_plus_one
  ```python
  for field_name, old_value in inspection_date_fields:
  ```
- Line 155: potential_n_plus_one
  ```python
  for order in target_orders[:5]:  # عرض أول 5 طلبات للتحقق
  ```
- Line 160: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```

### important_script/fix_salesperson_names_in_sheets.py

#### Unused Imports (1)

- Line 1: `json` (from `json`)

#### Query Optimization Opportunities (4)

- Line 65: potential_n_plus_one
  ```python
  sheet_titles = [s['properties']['title'] for s in sheet_metadata['sheets']]
  ```
- Line 81: potential_n_plus_one
  ```python
  for sheet_title in sheet_titles:
  ```
- Line 91: potential_n_plus_one
  ```python
  for row in values:
  ```
- Line 116: potential_n_plus_one
  ```python
  for names in unmatched_report.values():
  ```

### important_script/fix_specific_inspections_dates.py

#### Unused Imports (1)

- Line 10: `datetime` (from `datetime.datetime`)

#### Query Optimization Opportunities (5)

- Line 47: missing_select_related
  ```python
  target_orders = Order.objects.filter(order_number__in=target_order_numbers)
  ```
- Line 71: potential_n_plus_one
  ```python
  for order in target_orders.order_by('order_number'):
  ```
- Line 84: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 124: potential_n_plus_one
  ```python
  for order in target_orders[:5]:  # عرض أول 5 طلبات للتحقق
  ```
- Line 129: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```

### important_script/reset_orders_to_initial_state.py

#### Unused Imports (1)

- Line 11: `datetime` (from `datetime.datetime`)

#### Query Optimization Opportunities (7)

- Line 54: missing_select_related
  ```python
  inspections_to_reset = Inspection.objects.filter(order__in=target_orders)
  ```
- Line 71: missing_select_related
  ```python
  manufacturing_orders_to_reset = ManufacturingOrder.objects.filter(order__in=targ
  ```
- Line 95: missing_select_related
  ```python
  installations_to_reset = InstallationSchedule.objects.filter(order__in=target_or
  ```
- Line 57: potential_n_plus_one
  ```python
  for inspection in inspections_to_reset:
  ```
- Line 74: potential_n_plus_one
  ```python
  for manu_order in manufacturing_orders_to_reset:
  ```
- Line 99: potential_n_plus_one
  ```python
  for installation in installations_to_reset:
  ```
- Line 120: potential_n_plus_one
  ```python
  for order in target_orders:
  ```

### important_script/reset_specific_orders.py

#### Unused Imports (1)

- Line 8: `timezone` (from `django.utils.timezone`)

#### Query Optimization Opportunities (8)

- Line 39: missing_select_related
  ```python
  target_orders = Order.objects.filter(order_number__in=target_order_numbers)
  ```
- Line 60: missing_select_related
  ```python
  inspections_to_reset = Inspection.objects.filter(order__in=target_orders)
  ```
- Line 78: missing_select_related
  ```python
  manufacturing_orders_to_reset = ManufacturingOrder.objects.filter(order__in=targ
  ```
- Line 103: missing_select_related
  ```python
  installations_to_reset = InstallationSchedule.objects.filter(order__in=target_or
  ```
- Line 63: potential_n_plus_one
  ```python
  for inspection in inspections_to_reset:
  ```
- Line 81: potential_n_plus_one
  ```python
  for manu_order in manufacturing_orders_to_reset:
  ```
- Line 107: potential_n_plus_one
  ```python
  for installation in installations_to_reset:
  ```
- Line 131: potential_n_plus_one
  ```python
  for order in target_orders:
  ```

### important_script/sync_inspection_with_order_dates.py

#### Unused Imports (1)

- Line 10: `datetime` (from `datetime.datetime`)

#### Query Optimization Opportunities (5)

- Line 47: missing_select_related
  ```python
  target_orders = Order.objects.filter(order_number__in=target_order_numbers)
  ```
- Line 72: potential_n_plus_one
  ```python
  for order in target_orders.order_by('order_number'):
  ```
- Line 86: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 187: potential_n_plus_one
  ```python
  for order in target_orders[:3]:  # عرض أول 3 طلبات للتحقق
  ```
- Line 192: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```

### important_script/update_existing_status_logs.py

#### Unused Imports (1)

- Line 16: `transaction` (from `django.db.transaction`)

#### Query Optimization Opportunities (2)

- Line 31: potential_n_plus_one
  ```python
  for log in logs_to_update:
  ```
- Line 95: potential_n_plus_one
  ```python
  for order in orders:
  ```

### inspections/admin.py

#### Unused Imports (1)

- Line 5: `get_object_or_404` (from `django.shortcuts.get_object_or_404`)

#### Unused Functions (14)

- Line 84: `inspector_display()`
- Line 91: `status_display()`
- Line 108: `result_display()`
- Line 126: `mark_as_completed()`
- Line 136: `mark_as_passed()`
- Line 146: `mark_as_failed()`
- Line 156: `export_inspections()`
- Line 190: `get_urls()`
- Line 202: `inspection_by_code_view()`
- Line 226: `inspection_code()`
- Line 250: `get_queryset()`
- Line 257: `get_form()`
- Line 353: `save_model()`
- Line 379: `mark_as_read()`

#### Unused Classes (4)

- Line 15: `InspectionAdmin`
- Line 291: `InspectionEvaluationAdmin`
- Line 314: `InspectionReportAdmin`
- Line 360: `InspectionNotificationAdmin`

#### Query Optimization Opportunities (2)

- Line 128: missing_select_related
  ```python
  updated = queryset.filter(status__in=['pending', 'scheduled']).update(status='co
  ```
- Line 172: potential_n_plus_one
  ```python
  for inspection in queryset:
  ```

### inspections/apps.py

#### Unused Imports (1)

- Line 10: `inspections` (from `inspections.signals`)

#### Unused Functions (1)

- Line 9: `ready()`

#### Unused Classes (1)

- Line 4: `InspectionsConfig`

### inspections/forms.py

#### Unused Imports (1)

- Line 6: `InspectionEvaluation` (from `models.InspectionEvaluation`)

#### Unused Functions (3)

- Line 173: `__init__()`
- Line 271: `clean()`
- Line 89: `clean_scheduled_for()`

#### Unused Classes (7)

- Line 13: `InspectionEvaluationForm`
- Line 43: `InspectionReportForm`
- Line 146: `Meta`
- Line 70: `InspectionNotificationForm`
- Line 95: `InspectionFilterForm`
- Line 126: `InspectionForm`
- Line 291: `InspectionSearchForm`

#### Query Optimization Opportunities (3)

- Line 39: potential_n_plus_one
  ```python
  for field in self.fields:
  ```
- Line 55: potential_n_plus_one
  ```python
  for field in self.fields:
  ```
- Line 84: potential_n_plus_one
  ```python
  for field in self.fields:
  ```

### installations/apps.py

#### Unused Imports (1)

- Line 11: `installations` (from `installations.signals`)

#### Unused Functions (1)

- Line 10: `ready()`

#### Unused Classes (1)

- Line 5: `InstallationsConfig`

### installations/deployment.py

#### Unused Imports (1)

- Line 4: `Path` (from `pathlib.Path`)

#### Unused Functions (1)

- Line 248: `apply_settings()`

#### Query Optimization Opportunities (4)

- Line 259: potential_n_plus_one
  ```python
  for key, value in settings['EMAIL'].items():
  ```
- Line 263: potential_n_plus_one
  ```python
  for key, value in settings['SECURITY'].items():
  ```
- Line 267: potential_n_plus_one
  ```python
  for key, value in settings['APP'].items():
  ```
- Line 271: potential_n_plus_one
  ```python
  for key, value in settings['MEDIA'].items():
  ```

### inventory/apps.py

#### Unused Imports (1)

- Line 11: `inventory` (from `inventory.signals`)

#### Unused Functions (1)

- Line 9: `ready()`

#### Unused Classes (1)

- Line 4: `InventoryConfig`

### inventory/cache_utils.py

#### Unused Imports (1)

- Line 5: `Count` (from `django.db.models.Count`)

#### Unused Functions (12)

- Line 18: `get_cached_dashboard_stats()`
- Line 115: `invalidate_product_stock_cache()`
- Line 125: `invalidate_product_cache()`
- Line 145: `get_cached_product_list()`
- Line 183: `get_cached_category_list()`
- Line 199: `invalidate_category_cache()`
- Line 209: `get_cached_supplier_list()`
- Line 225: `invalidate_supplier_cache()`
- Line 231: `get_cached_warehouse_list()`
- Line 247: `invalidate_warehouse_cache()`
- Line 253: `get_cached_alert_count()`
- Line 269: `invalidate_alert_cache()`

#### Query Optimization Opportunities (6)

- Line 69: missing_select_related
  ```python
  ).filter(total_out__gt=0).order_by('-total_out')[:5]
  ```
- Line 35: potential_n_plus_one
  ```python
  for product in products:
  ```
- Line 42: potential_n_plus_one
  ```python
  for product in products:
  ```
- Line 136: potential_n_plus_one
  ```python
  for key in cache_keys:
  ```
- Line 166: potential_n_plus_one
  ```python
  for product in products:
  ```
- Line 206: potential_n_plus_one
  ```python
  for key in cache.keys('product_list_*'):
  ```

### inventory/signals.py

#### Unused Imports (1)

- Line 28: `Order` (from `orders.models.Order`)

#### Unused Functions (5)

- Line 8: `update_currency_on_settings_change()`
- Line 10: `update_products()`
- Line 18: `protect_paid_orders_from_price_changes()`
- Line 54: `update_running_balance()`
- Line 57: `update_balances()`

#### Query Optimization Opportunities (2)

- Line 39: potential_n_plus_one
  ```python
  affected_orders = [item.order.order_number for item in paid_orders_with_product]
  ```
- Line 83: potential_n_plus_one
  ```python
  for trans in subsequent_transactions:
  ```

### inventory/admin.py

#### Unused Imports (1)

- Line 3: `Sum` (from `django.db.models.Sum`)

#### Unused Functions (4)

- Line 63: `get_queryset()`
- Line 49: `get_current_stock()`
- Line 54: `get_stock_status()`
- Line 237: `save_model()`

#### Unused Classes (13)

- Line 12: `CategoryAdmin`
- Line 19: `ProductAdmin`
- Line 74: `StockTransactionAdmin`
- Line 100: `SupplierAdmin`
- Line 106: `PurchaseOrderAdmin`
- Line 138: `PurchaseOrderItemAdmin`
- Line 145: `WarehouseAdmin`
- Line 152: `WarehouseLocationAdmin`
- Line 159: `ProductBatchAdmin`
- Line 167: `InventoryAdjustmentAdmin`
- Line 175: `StockAlertAdmin`
- Line 192: `StockTransferAdmin`
- Line 244: `StockTransferItemAdmin`

### inventory/context_processors.py

#### Unused Imports (1)

- Line 4: `Q` (from `django.db.models.Q`)

#### Unused Functions (1)

- Line 8: `pending_transfers()`

#### Query Optimization Opportunities (1)

- Line 40: missing_select_related
  ```python
  request.user.groups.filter(name__in=['مسؤول مخازن', 'Warehouse Manager', 'مسؤول 
  ```

### inventory/models.py

#### Unused Imports (1)

- Line 144: `Max` (from `django.db.models.Max`)

#### Unused Functions (8)

- Line 899: `__str__()`
- Line 32: `get_ancestors()`
- Line 43: `get_total_products_count()`
- Line 162: `get_unit_display()`
- Line 732: `save()`
- Line 778: `approve()`
- Line 812: `complete()`
- Line 849: `cancel()`

#### Unused Classes (6)

- Line 9: `Category`
- Line 889: `Meta`
- Line 493: `PurchaseOrderItem`
- Line 519: `InventoryAdjustment`
- Line 567: `StockAlert`
- Line 860: `StockTransferItem`

#### Query Optimization Opportunities (7)

- Line 48: potential_n_plus_one
  ```python
  for child in self.children.all():
  ```
- Line 116: potential_n_plus_one
  ```python
  for warehouse in warehouses:
  ```
- Line 150: potential_n_plus_one
  ```python
  for warehouse in Warehouse.objects.filter(is_active=True):
  ```
- Line 426: potential_n_plus_one
  ```python
  for trans in next_transactions:
  ```
- Line 495: potential_n_plus_one
  ```python
  Model for items in a purchase order
  ```
- Line 789: potential_n_plus_one
  ```python
  for item in self.items.all():
  ```
- Line 824: potential_n_plus_one
  ```python
  for item in self.items.all():
  ```

### manufacturing/tests.py

#### Unused Imports (1)

- Line 1: `TestCase` (from `django.test.TestCase`)

### manufacturing/apps.py

#### Unused Imports (1)

- Line 10: `signals` (from `signals`)

#### Unused Functions (1)

- Line 8: `ready()`

#### Unused Classes (1)

- Line 4: `ManufacturingConfig`

### manufacturing/models.py

#### Unused Imports (1)

- Line 743: `Q` (from `django.db.models.Q`)

#### Unused Functions (21)

- Line 1475: `__str__()`
- Line 1303: `save()`
- Line 73: `with_items_count()`
- Line 293: `get_absolute_url()`
- Line 298: `get_delete_url()`
- Line 381: `update_order_status()`
- Line 471: `assign_production_line()`
- Line 540: `get_items_status_display()`
- Line 549: `get_items_status_color()`
- Line 686: `get_clean_quantity_display()`
- Line 698: `mark_fabric_received()`
- Line 791: `get_fabric_status_display()`
- Line 800: `get_fabric_status_color()`
- Line 809: `get_cutting_status_color()`
- Line 936: `get_branches_display()`
- Line 945: `get_supported_order_types_display()`
- Line 959: `supports_order_type()`
- Line 1104: `get_allowed_statuses_display()`
- Line 1118: `get_allowed_order_types_display()`
- Line 1132: `get_target_users_display()`
- Line 1175: `update_related_models()`

#### Unused Classes (5)

- Line 1470: `Meta`
- Line 827: `ProductionLine`
- Line 985: `ManufacturingDisplaySettings`
- Line 1330: `ProductReceipt`
- Line 1417: `FabricReceiptItem`

#### Query Optimization Opportunities (12)

- Line 465: potential_n_plus_one
  ```python
  for installation in installations:
  ```
- Line 726: potential_n_plus_one
  ```python
  for bag in active_bags:
  ```
- Line 751: potential_n_plus_one
  ```python
  for order in completed_orders:
  ```
- Line 752: potential_n_plus_one
  ```python
  for item in order.items.filter(fabric_received=True).exclude(bag_number=''):
  ```
- Line 942: potential_n_plus_one
  ```python
  return ', '.join([branch.name for branch in branches[:3]]) + \
  ```
- Line 951: potential_n_plus_one
  ```python
  for order_type in self.supported_order_types:
  ```
- Line 952: potential_n_plus_one
  ```python
  for choice_value, choice_display in self.ORDER_TYPE_CHOICES:
  ```
- Line 1110: potential_n_plus_one
  ```python
  for status in self.allowed_statuses:
  ```
- Line 1111: potential_n_plus_one
  ```python
  for choice_value, choice_display in ManufacturingOrder.STATUS_CHOICES:
  ```
- Line 1124: potential_n_plus_one
  ```python
  for order_type in self.allowed_order_types:
  ```
- Line 1125: potential_n_plus_one
  ```python
  for choice_value, choice_display in ManufacturingOrder.ORDER_TYPE_CHOICES:
  ```
- Line 1141: potential_n_plus_one
  ```python
  return ', '.join([user.get_full_name() or user.username for user in users[:3]]) 
  ```

### notifications/tests.py

#### Unused Imports (1)

- Line 1: `TestCase` (from `django.test.TestCase`)

### notifications/apps.py

#### Unused Imports (1)

- Line 12: `notifications` (from `notifications.signals`)

#### Unused Functions (1)

- Line 10: `ready()`

#### Unused Classes (1)

- Line 5: `NotificationsConfig`

### notifications/signals.py

#### Unused Imports (1)

- Line 5: `_` (from `django.utils.translation.gettext_lazy`)

#### Unused Functions (8)

- Line 114: `customer_created_notification()`
- Line 140: `order_created_notification()`
- Line 187: `inspection_created_notification()`
- Line 223: `inspection_status_changed_notification()`
- Line 285: `installation_scheduled_notification()`
- Line 313: `installation_completed_notification()`
- Line 348: `manufacturing_order_status_changed_notification()`
- Line 437: `complaint_created_notification()`

#### Query Optimization Opportunities (2)

- Line 96: potential_n_plus_one
  ```python
  for user in recipients:
  ```
- Line 144: potential_n_plus_one
  ```python
  order_types_str = ', '.join([dict(instance.ORDER_TYPES).get(t, t) for t in order
  ```

### odoo_db_manager/apps.py

#### Unused Imports (1)

- Line 33: `odoo_db_manager` (from `odoo_db_manager.signals`)

#### Unused Functions (3)

- Line 23: `ready()`
- Line 43: `_setup_backup_service()`
- Line 51: `check_scheduled_backup_service()`

#### Unused Classes (1)

- Line 13: `OdooDbManagerConfig`

### odoo_db_manager/tasks.py

#### Unused Imports (1)

- Line 12: `GoogleSyncSchedule` (from `google_sync_advanced.GoogleSyncSchedule`)

#### Unused Functions (7)

- Line 19: `sync_google_sheet_task()`
- Line 81: `reverse_sync_task()`
- Line 116: `run_scheduled_syncs()`
- Line 135: `cleanup_old_tasks()`
- Line 160: `sync_all_active_mappings()`
- Line 199: `validate_all_mappings()`
- Line 235: `send_sync_notification()`

#### Query Optimization Opportunities (2)

- Line 168: potential_n_plus_one
  ```python
  for mapping in active_mappings:
  ```
- Line 207: potential_n_plus_one
  ```python
  for mapping in mappings:
  ```

### odoo_db_manager/views_advanced_sync.py

#### Unused Imports (1)

- Line 17: `settings` (from `django.conf.settings`)

#### Unused Functions (18)

- Line 160: `advanced_sync_dashboard()`
- Line 198: `mapping_list()`
- Line 236: `mapping_create()`
- Line 331: `mapping_detail()`
- Line 388: `mapping_edit()`
- Line 518: `mapping_delete()`
- Line 540: `api_run_sync()`
- Line 627: `api_run_sync_all()`
- Line 713: `get_sheets_by_id()`
- Line 759: `mapping_update_columns()`
- Line 806: `start_sync()`
- Line 951: `task_detail()`
- Line 974: `conflict_list()`
- Line 1012: `resolve_conflict()`
- Line 1036: `schedule_sync()`
- Line 1087: `get_sheet_columns()`
- Line 1140: `preview_sheet_data()`
- Line 1194: `get_task_status()`

#### Query Optimization Opportunities (9)

- Line 206: missing_select_related
  ```python
  mappings = mappings.filter(name__icontains=search_query)
  ```
- Line 55: potential_n_plus_one
  ```python
  for field in required_fields:
  ```
- Line 265: potential_n_plus_one
  ```python
  for key, value in request.POST.items():
  ```
- Line 414: potential_n_plus_one
  ```python
  for key, value in request.POST.items():
  ```
- Line 452: potential_n_plus_one
  ```python
  for key, value in request.POST.items():
  ```
- Line 645: potential_n_plus_one
  ```python
  for mapping in mappings:
  ```
- Line 698: potential_n_plus_one
  ```python
  overall_success = all(r['success'] for r in results)
  ```
- Line 776: potential_n_plus_one
  ```python
  for key, value in request.POST.items():
  ```
- Line 1114: potential_n_plus_one
  ```python
  for header in headers:
  ```

### orders/invoice_models.py

#### Unused Imports (1)

- Line 6: `_` (from `django.utils.translation.gettext_lazy`)

#### Unused Functions (9)

- Line 305: `__str__()`
- Line 171: `save()`
- Line 183: `increment_usage()`
- Line 190: `get_color_palette()`
- Line 198: `get_font_settings()`
- Line 205: `get_page_settings()`
- Line 212: `render_html_content()`
- Line 220: `generate_default_html()`
- Line 233: `clone_template()`

#### Unused Classes (2)

- Line 300: `Meta`
- Line 266: `InvoicePrintLog`

### orders/apps.py

#### Unused Imports (1)

- Line 13: `orders` (from `orders.tracking`)

#### Unused Functions (1)

- Line 10: `ready()`

#### Unused Classes (1)

- Line 5: `OrdersConfig`

### orders/forms.py

#### Unused Imports (1)

- Line 3: `_` (from `django.utils.translation.gettext_lazy`)

#### Unused Functions (7)

- Line 14: `create_option()`
- Line 668: `__init__()`
- Line 75: `clean_quantity()`
- Line 462: `save()`
- Line 372: `clean_customer()`
- Line 394: `clean_related_inspection()`
- Line 652: `clean()`

#### Unused Classes (5)

- Line 11: `ProductSelectWidget`
- Line 553: `Meta`
- Line 104: `PaymentForm`
- Line 127: `OrderForm`
- Line 550: `OrderEditForm`

#### Query Optimization Opportunities (4)

- Line 325: potential_n_plus_one
  ```python
  for inspection_data in cached_inspections:
  ```
- Line 339: potential_n_plus_one
  ```python
  for field_name in self.fields:
  ```
- Line 421: potential_n_plus_one
  ```python
  for field in required_fields:
  ```
- Line 646: potential_n_plus_one
  ```python
  for t in types_list:
  ```

### reports/admin.py

#### Unused Imports (1)

- Line 3: `_` (from `django.utils.translation.gettext_lazy`)

#### Unused Functions (1)

- Line 41: `save_model()`

#### Unused Classes (3)

- Line 7: `ReportAdmin`
- Line 20: `SavedReportAdmin`
- Line 33: `ReportScheduleAdmin`

### tests/test_arabic_fix.py

#### Unused Imports (1)

- Line 7: `sys` (from `sys`)

#### Query Optimization Opportunities (2)

- Line 27: potential_n_plus_one
  ```python
  for i, sheet in enumerate(sheets, 1):
  ```
- Line 46: potential_n_plus_one
  ```python
  for sheet in sheets:
  ```

### tests/test_fixes.py

#### Unused Imports (1)

- Line 154: `inspection_detail_by_code` (from `inspections.views.inspection_detail_by_code`)

#### Unused Functions (3)

- Line 22: `test_manufacturing_order_notification()`
- Line 69: `test_notification_read_functionality()`
- Line 130: `test_inspection_duplicate_issue()`

#### Query Optimization Opportunities (1)

- Line 140: missing_select_related
  ```python
  ).filter(inspection_count__gt=1)
  ```

### tests/test_form_submission.py

#### Unused Imports (1)

- Line 18: `json` (from `json`)

#### Query Optimization Opportunities (1)

- Line 67: potential_n_plus_one
  ```python
  for key, value in form_data.items():
  ```

### tests/test_inspection_notifications.py

#### Unused Imports (1)

- Line 81: `inspection_status_changed_notification` (from `notifications.signals.inspection_status_changed_notification`)

#### Query Optimization Opportunities (3)

- Line 62: potential_n_plus_one
  ```python
  for notif in new_notifications:
  ```
- Line 84: potential_n_plus_one
  ```python
  signal_found = any('inspection_status_changed_notification' in str(receiver) for
  ```
- Line 93: potential_n_plus_one
  ```python
  print(f"     المستخدمون: {[u.username for u in recipients[:5]]}")
  ```

### tests/test_javascript_fixes.py

#### Unused Imports (1)

- Line 7: `Path` (from `pathlib.Path`)

#### Unused Functions (4)

- Line 9: `check_select2_i18n_files()`
- Line 47: `check_javascript_errors()`
- Line 87: `check_notification_elements()`
- Line 126: `check_payment_status_template()`

#### Query Optimization Opportunities (11)

- Line 24: potential_n_plus_one
  ```python
  for template_dir in template_dirs:
  ```
- Line 26: potential_n_plus_one
  ```python
  for root, dirs, files in os.walk(template_dir):
  ```
- Line 27: potential_n_plus_one
  ```python
  for file in files:
  ```
- Line 40: potential_n_plus_one
  ```python
  for file_path in found_files:
  ```
- Line 59: potential_n_plus_one
  ```python
  for root, dirs, files in os.walk('.'):
  ```
- Line 60: potential_n_plus_one
  ```python
  for file in files:
  ```
- Line 66: potential_n_plus_one
  ```python
  for file_path in template_files:
  ```
- Line 71: potential_n_plus_one
  ```python
  for pattern in error_patterns:
  ```
- Line 80: potential_n_plus_one
  ```python
  for issue in issues_found:
  ```
- Line 109: potential_n_plus_one
  ```python
  for element in required_elements:
  ```
- Line 115: potential_n_plus_one
  ```python
  for element in missing_elements:
  ```

### tests/test_payment_status_fix.py

#### Unused Imports (1)

- Line 15: `Order` (from `orders.models.Order`)

#### Unused Functions (3)

- Line 17: `test_payment_status_logic()`
- Line 55: `test_form_fields()`
- Line 72: `test_template_display()`

### tests/test_status_sync.py

#### Unused Imports (1)

- Line 15: `ManufacturingOrder` (from `manufacturing.models.ManufacturingOrder`)

#### Query Optimization Opportunities (1)

- Line 79: potential_n_plus_one
  ```python
  for notif in new_notifications:
  ```

### tests/test_sweetalert2_migration.py

#### Unused Imports (1)

- Line 7: `os` (from `os`)

#### Query Optimization Opportunities (6)

- Line 35: potential_n_plus_one
  ```python
  for pattern in modal_patterns:
  ```
- Line 62: potential_n_plus_one
  ```python
  for pattern in swal_patterns:
  ```
- Line 105: potential_n_plus_one
  ```python
  for file_name in updated_files:
  ```
- Line 115: potential_n_plus_one
  ```python
  for issue in issues:
  ```
- Line 135: potential_n_plus_one
  ```python
  for file_name in new_files:
  ```
- Line 162: potential_n_plus_one
  ```python
  for positive in all_positives:
  ```

### user_activity/tests.py

#### Unused Imports (1)

- Line 1: `TestCase` (from `django.test.TestCase`)

### user_activity/views.py

#### Unused Imports (1)

- Line 1: `render` (from `django.shortcuts.render`)

### user_activity/apps.py

#### Unused Imports (1)

- Line 11: `user_activity` (from `user_activity.signals`)

#### Unused Functions (1)

- Line 9: `ready()`

#### Unused Classes (1)

- Line 4: `UserActivityConfig`

### cutting/admin.py

#### Unused Imports (1)

- Line 4: `mark_safe` (from `django.utils.safestring.mark_safe`)

#### Unused Functions (11)

- Line 18: `get_readonly_fields()`
- Line 59: `order_link()`
- Line 67: `customer_name()`
- Line 178: `status_badge()`
- Line 88: `completion_progress()`
- Line 198: `get_queryset()`
- Line 154: `cutting_order_code()`
- Line 159: `product_name()`
- Line 164: `quantity_display()`
- Line 224: `save_model()`
- Line 219: `date_range()`

#### Unused Classes (3)

- Line 25: `CuttingOrderAdmin`
- Line 116: `CuttingOrderItemAdmin`
- Line 205: `CuttingReportAdmin`

### cutting/apps.py

#### Unused Imports (1)

- Line 10: `cutting` (from `cutting.signals`)

#### Unused Functions (1)

- Line 9: `ready()`

#### Unused Classes (1)

- Line 4: `CuttingConfig`

### reports/templatetags/report_math_filters.py

#### Unused Imports (1)

- Line 10: `RequestContext` (from `django.template.RequestContext`)

#### Unused Functions (23)

- Line 8: `currency()`
- Line 28: `growth_class()`
- Line 42: `retention_class()`
- Line 56: `margin_class()`
- Line 70: `map()`
- Line 78: `percentage()`
- Line 86: `trend_icon()`
- Line 100: `format_frequency()`
- Line 112: `status_class()`
- Line 124: `chart_color()`
- Line 139: `format_time()`
- Line 156: `format_number()`
- Line 170: `div()`
- Line 178: `divide()`
- Line 186: `mul()`
- Line 194: `multiply()`
- Line 202: `sub()`
- Line 210: `subtract()`
- Line 218: `add()`
- Line 226: `sum_attr()`
- Line 240: `avg_attr()`
- Line 261: `max_attr()`
- Line 279: `min_attr()`

#### Query Optimization Opportunities (5)

- Line 73: potential_n_plus_one
  ```python
  return mark_safe(json.dumps([item[attr] for item in value]))
  ```
- Line 230: potential_n_plus_one
  ```python
  for item in items:
  ```
- Line 247: potential_n_plus_one
  ```python
  for item in items:
  ```
- Line 267: potential_n_plus_one
  ```python
  for item in items:
  ```
- Line 285: potential_n_plus_one
  ```python
  for item in items:
  ```

### orders/templatetags/unified_status_tags.py

#### Unused Imports (1)

- Line 3: `format_html` (from `django.utils.html.format_html`)

#### Unused Functions (8)

- Line 8: `get_status_badge()`
- Line 129: `get_order_type_badge()`
- Line 180: `get_order_type_text()`
- Line 207: `get_status_indicator()`
- Line 264: `get_completion_indicator()`
- Line 287: `get_vip_badge()`
- Line 299: `get_normal_badge()`
- Line 311: `get_urgent_badge()`

### orders/management/commands/warm_cache.py

#### Unused Imports (1)

- Line 6: `cache` (from `django.core.cache.cache`)

#### Unused Functions (3)

- Line 13: `add_arguments()`
- Line 30: `handle()`
- Line 71: `show_cache_stats()`

#### Unused Classes (1)

- Line 10: `Command`

### odoo_db_manager/services/__init__.py

#### Unused Imports (1)

- Line 5: `DatabaseService` (from `database_service.DatabaseService`)

### odoo_db_manager/management/commands/create_default_user.py

#### Unused Imports (1)

- Line 8: `settings` (from `django.conf.settings`)

#### Unused Functions (2)

- Line 13: `add_arguments()`
- Line 38: `handle()`

#### Unused Classes (1)

- Line 10: `Command`

### odoo_db_manager/management/commands/sync_google_sheets.py

#### Unused Imports (1)

- Line 8: `timezone` (from `django.utils.timezone`)

#### Unused Functions (8)

- Line 19: `add_arguments()`
- Line 62: `handle()`
- Line 84: `validate_mappings()`
- Line 120: `run_scheduled_syncs()`
- Line 130: `sync_all_mappings()`
- Line 176: `sync_mapping_by_id()`
- Line 207: `sync_mapping_by_name()`
- Line 238: `sync_single_mapping()`

#### Unused Classes (1)

- Line 16: `Command`

#### Query Optimization Opportunities (2)

- Line 97: potential_n_plus_one
  ```python
  for mapping in mappings:
  ```
- Line 150: potential_n_plus_one
  ```python
  for mapping in mappings:
  ```

### manufacturing/management/commands/sync_production_lines.py

#### Unused Imports (1)

- Line 11: `Counter` (from `collections.Counter`)

#### Unused Functions (21)

- Line 18: `get_distribution_rules()`
- Line 63: `add_arguments()`
- Line 85: `handle()`
- Line 117: `create_backup()`
- Line 155: `create_missing_production_lines()`
- Line 192: `get_default_priority()`
- Line 202: `display_distribution_rules()`
- Line 220: `analyze_orders_by_branches_and_types()`
- Line 253: `get_order_branch()`
- Line 264: `display_detailed_analysis()`
- Line 287: `apply_new_synchronization()`
- Line 339: `get_matching_orders()`
- Line 374: `get_hani_ramsis_orders()`
- Line 404: `preview_new_synchronization()`
- Line 433: `read_current_settings()`
- Line 450: `display_current_settings()`
- Line 463: `analyze_manufacturing_orders()`
- Line 505: `display_orders_analysis()`
- Line 533: `preview_synchronization()`
- Line 556: `calculate_proposed_distribution()`
- Line 610: `apply_synchronization()`

#### Unused Classes (1)

- Line 15: `Command`

#### Query Optimization Opportunities (31)

- Line 139: missing_select_related
  ```python
  for order in ManufacturingOrder.objects.filter(production_line__isnull=False):
  ```
- Line 336: missing_select_related
  ```python
  unassigned_count = ManufacturingOrder.objects.filter(production_line__isnull=Tru
  ```
- Line 651: missing_select_related
  ```python
  unassigned_orders = ManufacturingOrder.objects.filter(production_line__isnull=Tr
  ```
- Line 127: potential_n_plus_one
  ```python
  for line in ProductionLine.objects.all():
  ```
- Line 139: potential_n_plus_one
  ```python
  for order in ManufacturingOrder.objects.filter(production_line__isnull=False):
  ```
- Line 160: potential_n_plus_one
  ```python
  for line_name, config in rules.items():
  ```
- Line 176: potential_n_plus_one
  ```python
  for branch_name in config['branches']:
  ```
- Line 207: potential_n_plus_one
  ```python
  for line_name, config in rules.items():
  ```
- Line 215: potential_n_plus_one
  ```python
  for branch in config['branches']:
  ```
- Line 234: potential_n_plus_one
  ```python
  for order in all_orders:
  ```
- Line 274: potential_n_plus_one
  ```python
  for order_type, count in analysis['by_type'].items():
  ```
- Line 279: potential_n_plus_one
  ```python
  for branch_name, count in sorted_branches[:10]:
  ```
- Line 284: potential_n_plus_one
  ```python
  type_details = ', '.join([f'{otype}({count})' for otype, count in branch_types.i
  ```
- Line 301: potential_n_plus_one
  ```python
  for line_name, config in rules.items():
  ```
- Line 357: potential_n_plus_one
  ```python
  for branch_name in config['branches']:
  ```
- Line 379: potential_n_plus_one
  ```python
  for branch_name in config['branches']:
  ```
- Line 411: potential_n_plus_one
  ```python
  for line_name, config in rules.items():
  ```
- Line 424: potential_n_plus_one
  ```python
  for order in sample_orders:
  ```
- Line 437: potential_n_plus_one
  ```python
  for line in ProductionLine.objects.filter(is_active=True).order_by('-priority'):
  ```
- Line 455: potential_n_plus_one
  ```python
  for line_id, config in settings.items():
  ```
- Line 477: potential_n_plus_one
  ```python
  for order in all_orders:
  ```
- Line 515: potential_n_plus_one
  ```python
  for order_type, count in analysis['orders_by_type'].items():
  ```
- Line 519: potential_n_plus_one
  ```python
  for status, count in analysis['orders_by_status'].items():
  ```
- Line 525: potential_n_plus_one
  ```python
  for mismatch in analysis['mismatched_assignments'][:5]:  # عرض أول 5 فقط
  ```
- Line 541: potential_n_plus_one
  ```python
  for line_id, config in settings.items():
  ```
- Line 553: potential_n_plus_one
  ```python
  for order_type, count in type_breakdown.items():
  ```
- Line 565: potential_n_plus_one
  ```python
  for line_id, config in sorted_lines:
  ```
- Line 568: potential_n_plus_one
  ```python
  for order_type in supported_types:
  ```
- Line 603: potential_n_plus_one
  ```python
  for order_type in unassigned_types:
  ```
- Line 624: potential_n_plus_one
  ```python
  for line_id, config in sorted_lines:
  ```
- Line 632: potential_n_plus_one
  ```python
  for order_type in supported_types:
  ```

### installations/management/commands/create_debt_records.py

#### Unused Imports (1)

- Line 7: `models` (from `django.db.models`)

#### Unused Functions (2)

- Line 16: `add_arguments()`
- Line 29: `handle()`

#### Unused Classes (1)

- Line 13: `Command`

#### Query Optimization Opportunities (2)

- Line 47: potential_n_plus_one
  ```python
  for order in debt_orders:
  ```
- Line 109: potential_n_plus_one
  ```python
  for debt in paid_orders:
  ```

### installations/management/commands/sync_debts.py

#### Unused Imports (1)

- Line 7: `models` (from `django.db.models`)

#### Unused Functions (7)

- Line 19: `add_arguments()`
- Line 31: `handle()`
- Line 58: `get_debt_stats()`
- Line 68: `sync_new_debts()`
- Line 99: `update_existing_debts()`
- Line 126: `mark_paid_debts()`
- Line 149: `display_results()`

#### Unused Classes (1)

- Line 16: `Command`

#### Query Optimization Opportunities (3)

- Line 80: potential_n_plus_one
  ```python
  for order in debt_orders:
  ```
- Line 106: potential_n_plus_one
  ```python
  for debt in existing_debts:
  ```
- Line 135: potential_n_plus_one
  ```python
  for debt in paid_orders_debts:
  ```

### inspections/management/commands/copy_order_notes.py

#### Unused Imports (1)

- Line 2: `F` (from `django.db.models.F`)

#### Unused Functions (1)

- Line 9: `handle()`

#### Unused Classes (1)

- Line 6: `Command`

#### Query Optimization Opportunities (1)

- Line 18: potential_n_plus_one
  ```python
  for inspection in inspections_with_orders:
  ```

### inspections/management/commands/fix_inspection_order_numbers.py

#### Unused Imports (1)

- Line 3: `Order` (from `orders.models.Order`)

#### Unused Functions (1)

- Line 9: `handle()`

#### Unused Classes (1)

- Line 6: `Command`

#### Query Optimization Opportunities (2)

- Line 12: missing_select_related
  ```python
  inspections = Inspection.objects.filter(order__isnull=False, is_from_orders=True
  ```
- Line 13: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```

### inspections/management/commands/fix_upload_status.py

#### Unused Imports (1)

- Line 6: `timezone` (from `django.utils.timezone`)

#### Unused Functions (2)

- Line 15: `add_arguments()`
- Line 27: `handle()`

#### Unused Classes (1)

- Line 12: `Command`

#### Query Optimization Opportunities (1)

- Line 70: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```

### inspections/management/commands/update_google_drive_fields.py

#### Unused Imports (1)

- Line 6: `timezone` (from `django.utils.timezone`)

#### Unused Functions (3)

- Line 14: `add_arguments()`
- Line 26: `handle()`
- Line 137: `_format_filename()`

#### Unused Classes (1)

- Line 11: `Command`

#### Query Optimization Opportunities (1)

- Line 65: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```

### crm/middleware/__init__.py

#### Unused Imports (1)

- Line 2: `EmergencyConnectionMiddleware` (from `emergency_connection.EmergencyConnectionMiddleware`)

### crm/middleware/connection_manager.py

#### Unused Imports (1)

- Line 9: `settings` (from `django.conf.settings`)

#### Unused Functions (9)

- Line 157: `__init__()`
- Line 161: `__call__()`
- Line 42: `cleanup_connections()`
- Line 70: `process_request()`
- Line 81: `process_response()`
- Line 115: `check_connection_count()`
- Line 134: `cleanup_idle_connections()`
- Line 175: `is_emergency_state()`
- Line 190: `emergency_cleanup()`

#### Unused Classes (4)

- Line 15: `DatabaseConnectionMiddleware`
- Line 61: `ConnectionMonitoringMiddleware`
- Line 95: `ConnectionPoolMiddleware`
- Line 152: `EmergencyConnectionMiddleware`

#### Query Optimization Opportunities (1)

- Line 48: potential_n_plus_one
  ```python
  for alias in connections:
  ```

### crm/middleware/emergency_connection.py

#### Unused Imports (1)

- Line 8: `transaction` (from `django.db.transaction`)

#### Unused Functions (5)

- Line 19: `__init__()`
- Line 24: `__call__()`
- Line 44: `check_connection_health()`
- Line 88: `cleanup_connections()`
- Line 104: `process_exception()`

#### Unused Classes (1)

- Line 14: `EmergencyConnectionMiddleware`

#### Query Optimization Opportunities (1)

- Line 94: potential_n_plus_one
  ```python
  for alias in connections:
  ```

### crm/middleware/performance.py

#### Unused Imports (1)

- Line 8: `HttpResponse` (from `django.http.HttpResponse`)

#### Unused Functions (2)

- Line 106: `__init__()`
- Line 109: `__call__()`

#### Unused Classes (5)

- Line 13: `PerformanceMiddleware`
- Line 37: `LazyLoadMiddleware`
- Line 53: `QueryPerformanceMiddleware`
- Line 81: `PerformanceCookiesMiddleware`
- Line 103: `CustomGZipMiddleware`

### crm/services/__init__.py

#### Unused Imports (1)

- Line 6: `BaseService` (from `base_service.BaseService`)

### crm/services/base_service.py

#### Unused Imports (1)

- Line 10: `ValidationError` (from `django.core.exceptions.ValidationError`)

#### Unused Classes (2)

- Line 15: `StatusSyncService`
- Line 98: `BaseService`

#### Query Optimization Opportunities (2)

- Line 169: potential_n_plus_one
  ```python
  for key, value in data.items():
  ```
- Line 204: potential_n_plus_one
  ```python
  instances = [cls.model_class(**data) for data in data_list]
  ```

### crm/management/commands/analyze_queries.py

#### Unused Imports (1)

- Line 3: `settings` (from `django.conf.settings`)

#### Unused Functions (7)

- Line 10: `add_arguments()`
- Line 23: `handle()`
- Line 47: `analyze_indexes()`
- Line 75: `analyze_slow_queries()`
- Line 113: `analyze_manufacturing_admin()`
- Line 165: `analyze_orders_admin()`
- Line 189: `analyze_customers_admin()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (2)

- Line 64: potential_n_plus_one
  ```python
  for row in results:
  ```
- Line 100: potential_n_plus_one
  ```python
  for query, calls, total_time, mean_time, rows in results:
  ```

### crm/management/commands/monitor_sequences.py

#### Unused Imports (1)

- Line 15: `timedelta` (from `datetime.timedelta`)

#### Unused Functions (10)

- Line 23: `add_arguments()`
- Line 51: `handle()`
- Line 63: `run_single_check()`
- Line 79: `run_daemon()`
- Line 109: `check_all_sequences()`
- Line 176: `extract_sequence_name()`
- Line 184: `check_table_sequence_status()`
- Line 271: `process_report()`
- Line 318: `save_report()`
- Line 337: `send_email_alert()`

#### Unused Classes (1)

- Line 20: `Command`

#### Query Optimization Opportunities (3)

- Line 144: potential_n_plus_one
  ```python
  for table_name, column_name, column_default, is_identity in tables_with_sequence
  ```
- Line 282: potential_n_plus_one
  ```python
  for problem in problems:
  ```
- Line 365: potential_n_plus_one
  ```python
  for warning in warnings:
  ```

### crm/management/commands/optimize_db.py

#### Unused Imports (1)

- Line 6: `connection` (from `django.db.connection`)

#### Unused Functions (8)

- Line 15: `add_arguments()`
- Line 46: `handle()`
- Line 62: `_get_db_connection()`
- Line 79: `_show_database_stats()`
- Line 151: `_analyze_tables()`
- Line 186: `_vacuum_database()`
- Line 221: `_reindex_database()`
- Line 256: `_run_all_optimizations()`

#### Unused Classes (1)

- Line 12: `Command`

#### Query Optimization Opportunities (5)

- Line 108: potential_n_plus_one
  ```python
  for row in cursor.fetchall():
  ```
- Line 143: potential_n_plus_one
  ```python
  for row in cursor.fetchall():
  ```
- Line 170: potential_n_plus_one
  ```python
  for table in tables:
  ```
- Line 205: potential_n_plus_one
  ```python
  for table in tables:
  ```
- Line 240: potential_n_plus_one
  ```python
  for index in indexes:
  ```

### core/templatetags/pagination_tags.py

#### Unused Imports (1)

- Line 7: `mark_safe` (from `django.utils.safestring.mark_safe`)

#### Unused Functions (12)

- Line 12: `pagination_url()`
- Line 53: `preserve_filters()`
- Line 90: `render_pagination()`
- Line 101: `add_page_param()`
- Line 111: `current_url_with_page()`
- Line 152: `build_filter_url()`
- Line 181: `get_filter_value()`
- Line 192: `is_filter_active()`
- Line 203: `clear_filter_url()`
- Line 228: `clear_all_filters_url()`
- Line 249: `get_page_range()`
- Line 262: `page_info()`

#### Query Optimization Opportunities (6)

- Line 39: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 76: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 138: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 171: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 218: potential_n_plus_one
  ```python
  for key, value in params.items():
  ```
- Line 239: potential_n_plus_one
  ```python
  for param in keep_params:
  ```

### complaints/templatetags/complaints_tags.py

#### Unused Imports (1)

- Line 8: `ComplaintType` (from `models.ComplaintType`)

#### Unused Functions (11)

- Line 14: `customer_complaints_widget()`
- Line 42: `order_complaints_widget()`
- Line 60: `user_complaints_widget()`
- Line 85: `department_complaints_widget()`
- Line 113: `complaint_status_badge()`
- Line 138: `complaint_priority_badge()`
- Line 160: `get_complaint_stats_for_period()`
- Line 179: `time_until_deadline()`
- Line 204: `quick_complaint_create_url()`
- Line 225: `complaint_quick_stats()`
- Line 248: `complaint_type_color()`

#### Query Optimization Opportunities (1)

- Line 233: missing_select_related
  ```python
  'today': Complaint.objects.filter(created_at__date=today).count(),
  ```

### complaints/templatetags/complaints_permissions.py

#### Unused Imports (1)

- Line 5: `Group` (from `django.contrib.auth.models.Group`)

#### Unused Functions (3)

- Line 11: `has_complaints_permissions()`
- Line 31: `has_assignment_permissions()`
- Line 51: `user_complaints_role()`

### complaints/management/commands/update_complaint_numbers.py

#### Unused Imports (1)

- Line 7: `Customer` (from `customers.models.Customer`)

#### Unused Functions (2)

- Line 13: `add_arguments()`
- Line 25: `handle()`

#### Unused Classes (1)

- Line 10: `Command`

#### Query Optimization Opportunities (3)

- Line 60: potential_n_plus_one
  ```python
  for complaint in complaints_to_update:
  ```
- Line 68: potential_n_plus_one
  ```python
  for customer_id, complaints in customer_complaints.items():
  ```
- Line 79: potential_n_plus_one
  ```python
  for index, complaint in enumerate(complaints, 1):
  ```

### accounts/middleware/__init__.py

#### Unused Imports (1)

- Line 10: `RoleBasedPermissionsMiddleware` (from `middleware.RoleBasedPermissionsMiddleware`)

#### Unused Functions (1)

- Line 17: `process_request()`

#### Unused Classes (1)

- Line 15: `RoleBasedPermissionsMiddleware`

### accounts/services/__init__.py

#### Unused Imports (1)

- Line 5: `DashboardService` (from `dashboard_service.DashboardService`)

### accounts/signals/__init__.py

#### Unused Imports (1)

- Line 4: `create_core_departments_after_migrate` (from `accounts.signals.post_migrate.create_core_departments_after_migrate`)

### accounts/signals/post_migrate.py

#### Unused Imports (1)

- Line 6: `apps` (from `django.apps.apps`)

#### Unused Functions (1)

- Line 9: `create_core_departments_after_migrate()`

### accounts/management/commands/create_departments.py

#### Unused Imports (1)

- Line 2: `User` (from `accounts.models.User`)

#### Unused Functions (1)

- Line 8: `handle()`

#### Unused Classes (1)

- Line 5: `Command`

#### Query Optimization Opportunities (3)

- Line 55: potential_n_plus_one
  ```python
  for code, data in main_departments.items():
  ```
- Line 216: potential_n_plus_one
  ```python
  for code, data in departments_data.items():
  ```
- Line 337: potential_n_plus_one
  ```python
  for code, data in units_data.items():
  ```

### accounts/management/commands/grant_full_permissions.py

#### Unused Imports (1)

- Line 7: `ContentType` (from `django.contrib.contenttypes.models.ContentType`)

#### Unused Functions (4)

- Line 14: `add_arguments()`
- Line 31: `handle()`
- Line 57: `create_superuser_group()`
- Line 76: `grant_full_permissions()`

#### Unused Classes (1)

- Line 11: `Command`

#### Query Optimization Opportunities (1)

- Line 86: potential_n_plus_one
  ```python
  for user in users:
  ```

### accounts/management/commands/runserver_with_celery.py

#### Unused Imports (1)

- Line 1: `os` (from `os`)

#### Unused Functions (2)

- Line 12: `add_arguments()`
- Line 34: `handle()`

#### Unused Classes (1)

- Line 9: `Command`

### accounts/management/commands/setup_departments.py

#### Unused Imports (1)

- Line 2: `_` (from `django.utils.translation.gettext_lazy`)

#### Unused Functions (1)

- Line 8: `handle()`

#### Unused Classes (1)

- Line 5: `Command`

#### Query Optimization Opportunities (1)

- Line 81: potential_n_plus_one
  ```python
  for dept_data in departments:
  ```

### manage.py

#### Query Optimization Opportunities (1)

- Line 127: potential_n_plus_one
  ```python
  for pid_file in ['/tmp/celery_worker_dev.pid', '/tmp/celery_beat_dev.pid']:
  ```

### apply_ultimate_indexes.py

#### Unused Functions (9)

- Line 35: `__init__()`
- Line 55: `connect_to_database()`
- Line 79: `disconnect_from_database()`
- Line 90: `check_existing_indexes()`
- Line 112: `parse_sql_file()`
- Line 151: `extract_index_name()`
- Line 168: `apply_index()`
- Line 228: `apply_all_indexes()`
- Line 289: `generate_report()`

#### Query Optimization Opportunities (5)

- Line 103: potential_n_plus_one
  ```python
  existing_indexes = {row[0]: True for row in self.cursor.fetchall()}
  ```
- Line 125: potential_n_plus_one
  ```python
  for line in lines:
  ```
- Line 156: potential_n_plus_one
  ```python
  for i, part in enumerate(parts):
  ```
- Line 248: potential_n_plus_one
  ```python
  for i, statement in enumerate(statements, 1):
  ```
- Line 343: potential_n_plus_one
  ```python
  for key in default_config.keys():
  ```

### test_delete_order.py

#### Query Optimization Opportunities (1)

- Line 12: missing_select_related
  ```python
  test_order = Order.objects.filter(order_number__startswith='1-0001').first()
  ```

### test_order_delete_simple.py

#### Query Optimization Opportunities (1)

- Line 24: missing_select_related
  ```python
  test_order = Order.objects.filter(order_number__startswith='1-0001').first()
  ```

### accounts/admin_config.py

#### Unused Functions (4)

- Line 178: `changelist_view()`
- Line 185: `change_view()`
- Line 191: `add_view()`
- Line 198: `get_activity_summary_html()`

#### Unused Classes (1)

- Line 175: `UserActivityAdminMixin`

#### Query Optimization Opportunities (2)

- Line 208: missing_select_related
  ```python
  today_logins = UserLoginHistory.objects.filter(login_time__date=today).count()
  ```
- Line 209: missing_select_related
  ```python
  today_activities = UserActivityLog.objects.filter(timestamp__date=today).count()
  ```

### accounts/api_views.py

#### Unused Functions (14)

- Line 18: `current_user()`
- Line 29: `user_info()`
- Line 55: `login_api()`
- Line 84: `role_list_api()`
- Line 106: `role_create_api()`
- Line 127: `role_detail_api()`
- Line 179: `user_roles_api()`
- Line 193: `add_user_role_api()`
- Line 226: `remove_user_role_api()`
- Line 256: `get_user_permissions()`
- Line 275: `dashboard_stats()`
- Line 283: `dashboard_activities()`
- Line 294: `dashboard_orders()`
- Line 305: `dashboard_trends()`

#### Query Optimization Opportunities (9)

- Line 98: missing_select_related
  ```python
  roles = roles.filter(name__icontains=search)
  ```
- Line 116: missing_select_related
  ```python
  permissions = Permission.objects.filter(id__in=permissions_ids)
  ```
- Line 150: missing_select_related
  ```python
  permissions = Permission.objects.filter(id__in=permissions_ids)
  ```
- Line 248: missing_select_related
  ```python
  if not UserRole.objects.filter(user=user, role__permissions=permission).exists()
  ```
- Line 154: potential_n_plus_one
  ```python
  for user_role in UserRole.objects.filter(role=updated_role):
  ```
- Line 160: potential_n_plus_one
  ```python
  for ur in user_roles:
  ```
- Line 161: potential_n_plus_one
  ```python
  for permission in ur.role.permissions.all():
  ```
- Line 217: potential_n_plus_one
  ```python
  for permission in role.permissions.all():
  ```
- Line 247: potential_n_plus_one
  ```python
  for permission in role.permissions.all():
  ```

### accounts/auth_compat.py

#### Unused Functions (1)

- Line 13: `auth_compat_view()`

### accounts/backends.py

#### Unused Functions (1)

- Line 9: `authenticate()`

#### Unused Classes (1)

- Line 8: `CustomModelBackend`

### accounts/context_processors.py

#### Unused Functions (8)

- Line 7: `departments()`
- Line 60: `company_info()`
- Line 98: `footer_settings()`
- Line 123: `system_settings()`
- Line 152: `user_context()`
- Line 161: `branch_messages()`
- Line 192: `notifications_context()`
- Line 209: `admin_notifications_context()`

#### Query Optimization Opportunities (2)

- Line 16: missing_select_related
  ```python
  parent_departments = all_departments.filter(parent__isnull=True)
  ```
- Line 35: potential_n_plus_one
  ```python
  for dept in user_departments:
  ```

### accounts/forms.py

#### Unused Functions (1)

- Line 259: `__init__()`

#### Unused Classes (10)

- Line 15: `CustomAuthenticationForm`
- Line 28: `UserRegistrationForm`
- Line 234: `Meta`
- Line 49: `UserUpdateForm`
- Line 72: `CustomPasswordChangeForm`
- Line 89: `BranchForm`
- Line 106: `DepartmentForm`
- Line 123: `CompanyInfoForm`
- Line 152: `FormFieldForm`
- Line 177: `SalespersonForm`

#### Query Optimization Opportunities (3)

- Line 266: missing_select_related
  ```python
  self.fields['users'].queryset = User.objects.exclude(id__in=assigned_users).filt
  ```
- Line 217: potential_n_plus_one
  ```python
  for ct in content_types:
  ```
- Line 224: potential_n_plus_one
  ```python
  group_permissions = [(p.id, p.name) for p in permissions]
  ```

### accounts/serializers.py

#### Unused Functions (4)

- Line 19: `get_full_name()`
- Line 31: `get_content_type_name()`
- Line 44: `get_permissions_count()`
- Line 60: `get_users_count()`

#### Unused Classes (4)

- Line 8: `UserSerializer`
- Line 69: `Meta`
- Line 51: `RoleDetailSerializer`
- Line 64: `UserRoleSerializer`

### accounts/utils.py

#### Unused Functions (7)

- Line 9: `apply_default_year_filter()`
- Line 60: `apply_year_filter_for_customers()`
- Line 101: `get_dashboard_year_context()`
- Line 126: `get_active_dashboard_years()`
- Line 136: `set_default_dashboard_year()`
- Line 166: `ensure_current_year_exists()`
- Line 191: `get_year_filter_display()`

#### Query Optimization Opportunities (5)

- Line 49: missing_select_related
  ```python
  queryset = queryset.filter(**{f'{date_field}__year': year})
  ```
- Line 55: missing_select_related
  ```python
  queryset = queryset.filter(**{f'{date_field}__year': default_year})
  ```
- Line 93: missing_select_related
  ```python
  queryset = queryset.filter(**{f'{date_field}__year': year})
  ```
- Line 36: potential_n_plus_one
  ```python
  for year_str in selected_years:
  ```
- Line 80: potential_n_plus_one
  ```python
  for year_str in selected_years:
  ```

### accounts/views.py

#### Unused Functions (27)

- Line 19: `login_view()`
- Line 95: `logout_view()`
- Line 103: `admin_logout_view()`
- Line 112: `profile_view()`
- Line 124: `company_info_view()`
- Line 166: `form_field_list()`
- Line 193: `form_field_create()`
- Line 216: `form_field_update()`
- Line 240: `form_field_delete()`
- Line 259: `toggle_form_field()`
- Line 279: `department_list()`
- Line 328: `department_create()`
- Line 349: `department_update()`
- Line 373: `department_delete()`
- Line 397: `toggle_department()`
- Line 417: `salesperson_list()`
- Line 473: `salesperson_create()`
- Line 494: `salesperson_update()`
- Line 518: `salesperson_delete()`
- Line 540: `toggle_salesperson()`
- Line 560: `role_list()`
- Line 596: `role_create()`
- Line 617: `role_update()`
- Line 658: `role_delete()`
- Line 689: `role_assign()`
- Line 722: `role_management()`
- Line 753: `set_default_theme()`

#### Query Optimization Opportunities (7)

- Line 313: missing_select_related
  ```python
  parent_departments = list(Department.objects.filter(parent__isnull=True))
  ```
- Line 569: missing_select_related
  ```python
  roles = roles.filter(name__icontains=search_query)
  ```
- Line 634: potential_n_plus_one
  ```python
  for user_role in UserRole.objects.filter(role=updated_role):
  ```
- Line 640: potential_n_plus_one
  ```python
  for ur in user_roles:
  ```
- Line 641: potential_n_plus_one
  ```python
  for permission in ur.role.permissions.all():
  ```
- Line 700: potential_n_plus_one
  ```python
  for user in users:
  ```
- Line 704: potential_n_plus_one
  ```python
  for permission in role.permissions.all():
  ```

### accounts/widgets.py

#### Unused Functions (2)

- Line 287: `__init__()`
- Line 293: `render()`

#### Unused Classes (3)

- Line 8: `DurationRangeWidget`
- Line 162: `ColorPickerWidget`
- Line 284: `IconPickerWidget`

#### Query Optimization Opportunities (1)

- Line 335: potential_n_plus_one
  ```python
  for icon_class, icon_name in predefined_icons:
  ```

### backup_system/apps.py

#### Unused Functions (1)

- Line 12: `ready()`

#### Unused Classes (1)

- Line 7: `BackupSystemConfig`

### core/apps.py

#### Unused Classes (1)

- Line 4: `CoreConfig`

### core/mixins.py

#### Unused Functions (1)

- Line 11: `dispatch()`

#### Unused Classes (1)

- Line 5: `PaginationFixMixin`

#### Query Optimization Opportunities (1)

- Line 23: potential_n_plus_one
  ```python
  for key, value in request.GET.items():
  ```

### core/monthly_filter_utils.py

#### Unused Functions (7)

- Line 12: `get_available_years()`
- Line 31: `apply_monthly_filter()`
- Line 104: `get_monthly_analytics()`
- Line 150: `get_date_range_for_month()`
- Line 192: `apply_quarter_filter()`
- Line 221: `get_monthly_comparison()`
- Line 260: `format_filter_summary()`

#### Query Optimization Opportunities (5)

- Line 25: potential_n_plus_one
  ```python
  return [year.year for year in years]
  ```
- Line 125: potential_n_plus_one
  ```python
  for month in range(1, 13):
  ```
- Line 212: potential_n_plus_one
  ```python
  # Create Q objects for each month in the quarter
  ```
- Line 214: potential_n_plus_one
  ```python
  for month in months:
  ```
- Line 236: potential_n_plus_one
  ```python
  for i in range(months_back):
  ```

### crm/admin_base.py

#### Unused Functions (13)

- Line 24: `get_search_fields()`
- Line 30: `get_list_filter()`
- Line 36: `get_queryset()`
- Line 59: `get_sortable_by()`
- Line 104: `get_list_display_links()`
- Line 111: `__init__()`
- Line 129: `apply_sortable_to_admin_method()`
- Line 131: `decorator()`
- Line 138: `create_foreign_key_display()`
- Line 186: `display_method()`
- Line 156: `create_choice_display()`
- Line 170: `create_date_display()`
- Line 184: `create_boolean_display()`

#### Unused Classes (2)

- Line 48: `Media`
- Line 56: `BaseSortableModelAdmin`

#### Query Optimization Opportunities (4)

- Line 64: potential_n_plus_one
  ```python
  for field_name in self.list_display:
  ```
- Line 86: potential_n_plus_one
  ```python
  for field in self.model._meta.fields:
  ```
- Line 91: potential_n_plus_one
  ```python
  for field in self.model._meta.fields:
  ```
- Line 116: potential_n_plus_one
  ```python
  for field_name in self.list_display:
  ```

### crm/api_monitoring.py

#### Unused Functions (7)

- Line 22: `monitoring_status()`
- Line 48: `database_stats()`
- Line 103: `system_stats()`
- Line 131: `pool_stats()`
- Line 161: `post()`
- Line 239: `health_check()`
- Line 293: `alerts()`

#### Unused Classes (1)

- Line 156: `DatabaseActionsView`

#### Query Optimization Opportunities (1)

- Line 303: potential_n_plus_one
  ```python
  for alert_type, alert_info in alerts_data.items():
  ```

### crm/auth.py

#### Unused Functions (3)

- Line 8: `authenticate()`
- Line 32: `_enforce_csrf()`
- Line 36: `dummy_get_response()`

#### Unused Classes (1)

- Line 7: `CustomJWTAuthentication`

### crm/context_processors.py

#### Unused Functions (2)

- Line 5: `admin_stats()`
- Line 48: `jazzmin_extras()`

### crm/csrf_views.py

#### Unused Functions (4)

- Line 14: `csrf_failure()`
- Line 50: `get_csrf_token_view()`
- Line 66: `csrf_debug_view()`
- Line 109: `test_csrf_view()`

### crm/views_health.py

#### Unused Functions (1)

- Line 9: `health_check()`

### crm/celery.py

#### Unused Functions (5)

- Line 147: `debug_task()`
- Line 154: `test_celery_connection()`
- Line 180: `get_celery_stats()`
- Line 243: `restart_celery_workers()`
- Line 264: `cleanup_expired_tasks()`

#### Query Optimization Opportunities (2)

- Line 206: potential_n_plus_one
  ```python
  total_active_tasks = sum(len(tasks) for tasks in active_tasks.values())
  ```
- Line 216: potential_n_plus_one
  ```python
  total_scheduled_tasks = sum(len(tasks) for tasks in scheduled_tasks.values())
  ```

### crm/signals.py

#### Unused Functions (2)

- Line 16: `run_sequence_check()`
- Line 27: `auto_fix_sequences_after_migrate()`

### customers/permissions.py

#### Unused Functions (11)

- Line 8: `get_user_customers_queryset()`
- Line 69: `get_user_base_customers_queryset()`
- Line 108: `can_user_view_customer()`
- Line 144: `can_user_edit_customer()`
- Line 175: `can_user_delete_customer()`
- Line 197: `can_user_create_customer()`
- Line 226: `can_user_create_order_for_customer()`
- Line 257: `can_user_access_cross_branch_customer()`
- Line 276: `apply_customer_permissions()`
- Line 327: `get_user_customer_permissions()`
- Line 394: `is_customer_cross_branch()`

#### Query Optimization Opportunities (4)

- Line 23: missing_select_related
  ```python
  return Customer.objects.filter(branch__in=managed_branches)
  ```
- Line 289: missing_select_related
  ```python
  return customers_queryset.filter(branch__in=managed_branches)
  ```
- Line 341: potential_n_plus_one
  ```python
  return {key: True for key in permissions.keys()}
  ```
- Line 345: potential_n_plus_one
  ```python
  return {key: True for key in permissions.keys()}
  ```

### customers/models.py

#### Unused Functions (13)

- Line 466: `__str__()`
- Line 52: `get_default_customer_category_id()`
- Line 469: `clean()`
- Line 483: `save()`
- Line 488: `generate_unique_code()`
- Line 544: `get_customer_type_display()`
- Line 552: `get_absolute_url()`
- Line 557: `requires_responsibles()`
- Line 561: `get_primary_responsible()`
- Line 565: `get_all_responsibles()`
- Line 569: `get_discount_percentage()`
- Line 575: `has_discount()`
- Line 579: `delete()`

#### Unused Classes (5)

- Line 413: `Meta`
- Line 74: `CustomerNote`
- Line 111: `CustomerAccessLog`
- Line 209: `CustomerType`
- Line 229: `DiscountType`

#### Query Optimization Opportunities (2)

- Line 21: potential_n_plus_one
  ```python
  types = [(t.code, t.name) for t in CustomerType.objects.filter(
  ```
- Line 511: potential_n_plus_one
  ```python
  for attempt in range(max_attempts):
  ```

### factory/apps.py

#### Unused Classes (1)

- Line 4: `FactoryConfig`

### important_script/create_advanced_sync_mappings.py

#### Query Optimization Opportunities (1)

- Line 15: potential_n_plus_one
  ```python
  for i in range(1, 15):
  ```

### important_script/complete_all_inspections_orders_manufacturing.py

#### Query Optimization Opportunities (6)

- Line 50: missing_select_related
  ```python
  completed_without_result = Inspection.objects.filter(status='completed', result_
  ```
- Line 41: potential_n_plus_one
  ```python
  for inspection in inspections_to_update:
  ```
- Line 61: potential_n_plus_one
  ```python
  for manu_order in manufacturing_orders_to_update.select_related('order'):
  ```
- Line 93: potential_n_plus_one
  ```python
  for order in installation_orders:
  ```
- Line 109: potential_n_plus_one
  ```python
  for inst in installations_to_update:
  ```
- Line 133: potential_n_plus_one
  ```python
  for order in all_orders:
  ```

### important_script/complete_pending_inspections.py

#### Query Optimization Opportunities (3)

- Line 41: potential_n_plus_one
  ```python
  for inspection in pending_inspections:
  ```
- Line 74: potential_n_plus_one
  ```python
  for inspection in completed_inspections:
  ```
- Line 102: potential_n_plus_one
  ```python
  for order in orders_with_inspections:
  ```

### important_script/fix_phone.py

#### Query Optimization Opportunities (1)

- Line 21: potential_n_plus_one
  ```python
  for customer in Customer.objects.all():
  ```

### important_script/sync_inspection_order_date_field.py

#### Query Optimization Opportunities (8)

- Line 47: missing_select_related
  ```python
  target_orders = Order.objects.filter(order_number__in=target_order_numbers)
  ```
- Line 72: potential_n_plus_one
  ```python
  for order in target_orders.order_by('order_number'):
  ```
- Line 86: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 98: potential_n_plus_one
  ```python
  for field_name in possible_order_date_fields:
  ```
- Line 122: potential_n_plus_one
  ```python
  for field_name in possible_order_date_fields:
  ```
- Line 211: potential_n_plus_one
  ```python
  for order in target_orders[:3]:  # عرض أول 3 طلبات للتحقق
  ```
- Line 216: potential_n_plus_one
  ```python
  for inspection in inspections:
  ```
- Line 229: potential_n_plus_one
  ```python
  for field_name in possible_order_date_fields:
  ```

### inspections/signals.py

#### Unused Functions (1)

- Line 7: `update_order_status_on_inspection_change()`

### inspections/models.py

#### Unused Functions (15)

- Line 12: `validate_inspection_pdf_file()`
- Line 293: `__str__()`
- Line 126: `calculate_statistics()`
- Line 304: `get_absolute_url()`
- Line 309: `clean()`
- Line 322: `save()`
- Line 379: `get_status_color()`
- Line 389: `get_status_badge_class()`
- Line 402: `get_status_icon()`
- Line 430: `generate_drive_filename()`
- Line 451: `_clean_filename()`
- Line 459: `calculate_expected_delivery_date()`
- Line 482: `recalculate_expected_delivery_date()`
- Line 487: `upload_to_google_drive_async()`
- Line 535: `schedule_upload_to_google_drive()`

#### Unused Classes (4)

- Line 23: `InspectionEvaluation`
- Line 277: `Meta`
- Line 59: `InspectionNotification`
- Line 89: `InspectionReport`

### installations/admin_filters.py

#### Unused Functions (2)

- Line 204: `lookups()`
- Line 213: `queryset()`

#### Unused Classes (8)

- Line 11: `DebtAmountRangeFilter`
- Line 42: `OverdueFilter`
- Line 82: `BranchFilter`
- Line 98: `SalespersonFilter`
- Line 121: `PaymentMethodFilter`
- Line 154: `CustomerTypeFilter`
- Line 173: `OrderTypeFilter`
- Line 199: `DebtAgeFilter`

#### Query Optimization Opportunities (18)

- Line 28: missing_select_related
  ```python
  return queryset.filter(debt_amount__lt=100)
  ```
- Line 30: missing_select_related
  ```python
  return queryset.filter(debt_amount__gte=100, debt_amount__lt=500)
  ```
- Line 32: missing_select_related
  ```python
  return queryset.filter(debt_amount__gte=500, debt_amount__lt=1000)
  ```
- Line 34: missing_select_related
  ```python
  return queryset.filter(debt_amount__gte=1000, debt_amount__lt=5000)
  ```
- Line 36: missing_select_related
  ```python
  return queryset.filter(debt_amount__gte=5000, debt_amount__lt=10000)
  ```
- Line 38: missing_select_related
  ```python
  return queryset.filter(debt_amount__gte=10000)
  ```
- Line 94: missing_select_related
  ```python
  return queryset.filter(order__customer__branch__id=self.value())
  ```
- Line 117: missing_select_related
  ```python
  return queryset.filter(order__salesperson__id=self.value())
  ```
- Line 142: missing_select_related
  ```python
  return queryset.filter(is_paid=True, payment_date__date=today)
  ```
- Line 144: missing_select_related
  ```python
  return queryset.filter(is_paid=True, payment_date__gte=week_ago)
  ```
- Line 146: missing_select_related
  ```python
  return queryset.filter(is_paid=True, payment_date__gte=month_ago)
  ```
- Line 148: missing_select_related
  ```python
  return queryset.filter(is_paid=False, created_at__gte=month_ago)
  ```
- Line 150: missing_select_related
  ```python
  return queryset.filter(is_paid=False, created_at__lt=month_ago)
  ```
- Line 169: missing_select_related
  ```python
  return queryset.filter(customer__customer_type=self.value())
  ```
- Line 216: missing_select_related
  ```python
  return queryset.filter(created_at__gte=now - timezone.timedelta(days=7))
  ```
- Line 233: missing_select_related
  ```python
  return queryset.filter(created_at__lt=now - timezone.timedelta(days=180))
  ```
- Line 90: potential_n_plus_one
  ```python
  return [(branch.id, branch.name) for branch in branches]
  ```
- Line 112: potential_n_plus_one
  ```python
  for salesperson in salespersons
  ```

### installations/forms.py

#### Unused Functions (6)

- Line 924: `__init__()`
- Line 973: `clean()`
- Line 241: `clean_payment_receipt_number()`
- Line 247: `clean_payment_receiver_name()`
- Line 595: `clean_report_file()`
- Line 623: `clean_receipt_image()`

#### Unused Classes (23)

- Line 14: `InstallationStatusForm`
- Line 949: `Meta`
- Line 92: `ModificationRequestForm`
- Line 121: `ModificationImageForm`
- Line 138: `ManufacturingOrderForm`
- Line 583: `ModificationReportForm`
- Line 193: `CustomerDebtForm`
- Line 223: `CustomerDebtPaymentForm`
- Line 254: `InstallationScheduleForm`
- Line 345: `QuickScheduleForm`
- Line 477: `InstallationTeamForm`
- Line 512: `TechnicianForm`
- Line 534: `TechnicianEditForm`
- Line 557: `DriverForm`
- Line 610: `ReceiptMemoForm`
- Line 638: `InstallationPaymentForm`
- Line 654: `InstallationFilterForm`
- Line 995: `DailyScheduleForm`
- Line 825: `ModificationReportForm_new`
- Line 836: `InstallationAnalyticsForm`
- Line 856: `ModificationErrorAnalysisForm`
- Line 874: `InstallationSchedulingSettingsForm`
- Line 936: `ScheduleEditForm`

#### Query Optimization Opportunities (1)

- Line 758: potential_n_plus_one
  ```python
  for field_name, field in self.fields.items():
  ```

### installations/tasks.py

#### Unused Functions (4)

- Line 17: `sync_customer_debts_task()`
- Line 54: `create_debt_records_task()`
- Line 101: `update_overdue_debts_task()`
- Line 141: `generate_debt_report_task()`

#### Query Optimization Opportunities (1)

- Line 72: potential_n_plus_one
  ```python
  for order in debt_orders:
  ```

### inventory/inventory_utils.py

#### Unused Functions (4)

- Line 9: `get_cached_stock_level()`
- Line 42: `invalidate_product_cache()`
- Line 61: `get_cached_product_list()`
- Line 99: `get_cached_dashboard_stats()`

#### Query Optimization Opportunities (1)

- Line 132: missing_select_related
  ```python
  'out_of_stock_count': products.filter(current_stock_calc__lte=0).count(),
  ```

### inventory/managers.py

#### Unused Functions (8)

- Line 61: `with_stock_level()`
- Line 64: `low_stock()`
- Line 67: `out_of_stock()`
- Line 70: `in_stock()`
- Line 73: `with_related()`
- Line 58: `get_queryset()`
- Line 76: `get_cached()`
- Line 89: `get_category_stats()`

#### Unused Classes (1)

- Line 57: `ProductManager`

#### Query Optimization Opportunities (2)

- Line 41: missing_select_related
  ```python
  return self.with_stock_level().filter(current_stock_calc__lte=0)
  ```
- Line 47: missing_select_related
  ```python
  return self.with_stock_level().filter(current_stock_calc__gt=0)
  ```

### manufacturing/context_processors.py

#### Unused Functions (1)

- Line 3: `manufacturing_nav_links()`

### notifications/context_processors.py

#### Unused Functions (1)

- Line 5: `notifications_context()`

### notifications/forms.py

#### Unused Functions (2)

- Line 163: `__init__()`
- Line 107: `get_field_groups()`

#### Unused Classes (4)

- Line 6: `NotificationSettingsForm`
- Line 9: `Meta`
- Line 143: `BulkNotificationSettingsForm`
- Line 171: `NotificationFilterForm`

### notifications/models.py

#### Unused Functions (11)

- Line 15: `for_user()`
- Line 19: `unread_for_user()`
- Line 23: `recent_for_user()`
- Line 419: `__str__()`
- Line 151: `get_absolute_url()`
- Line 181: `get_icon_and_color()`
- Line 232: `get_icon_class()`
- Line 248: `get_color_class()`
- Line 258: `get_visibility_for_user()`
- Line 262: `get_related_info()`
- Line 352: `mark_as_read()`

#### Unused Classes (3)

- Line 415: `Meta`
- Line 307: `NotificationVisibility`
- Line 360: `NotificationSettings`

#### Query Optimization Opportunities (1)

- Line 21: missing_select_related
  ```python
  return self.filter(visible_to=user, read_by__user=user, read_by__is_read=False).
  ```

### notifications/serializers.py

#### Unused Functions (5)

- Line 16: `get_full_name()`
- Line 50: `get_is_read()`
- Line 64: `get_read_at()`
- Line 78: `get_related_object_info()`
- Line 169: `validate()`

#### Unused Classes (7)

- Line 103: `Meta`
- Line 20: `NotificationVisibilitySerializer`
- Line 98: `NotificationSettingsSerializer`
- Line 114: `NotificationCreateSerializer`
- Line 134: `NotificationSummarySerializer`
- Line 143: `NotificationBulkActionSerializer`
- Line 152: `NotificationFilterSerializer`

### notifications/utils.py

#### Unused Functions (9)

- Line 7: `get_notification_recipients()`
- Line 54: `get_customer_notification_recipients()`
- Line 82: `get_order_notification_recipients()`
- Line 150: `get_inspection_notification_recipients()`
- Line 203: `get_installation_notification_recipients()`
- Line 236: `get_complaint_notification_recipients()`
- Line 269: `get_user_notification_count()`
- Line 279: `mark_notification_as_read()`
- Line 306: `mark_all_notifications_as_read()`

#### Query Optimization Opportunities (2)

- Line 51: missing_select_related
  ```python
  return User.objects.filter(id__in=recipient_ids)
  ```
- Line 105: potential_n_plus_one
  ```python
  if any(t in order_types for t in ['installation', 'tailoring']):
  ```

### odoo_db_manager/admin.py

#### Unused Functions (7)

- Line 145: `get_duration()`
- Line 217: `get_success_rate()`
- Line 229: `save_model()`
- Line 181: `get_conflict_description()`
- Line 185: `mark_as_resolved()`
- Line 190: `mark_as_ignored()`
- Line 223: `run_now()`

#### Unused Classes (8)

- Line 15: `DatabaseAdmin`
- Line 38: `GoogleDriveConfigAdmin`
- Line 75: `GoogleSyncConfigAdmin`
- Line 96: `GoogleSheetMappingAdmin`
- Line 120: `GoogleSyncTaskAdmin`
- Line 161: `GoogleSyncConflictAdmin`
- Line 196: `GoogleSyncScheduleAdmin`
- Line 237: `GoogleSyncLogAdmin`

#### Query Optimization Opportunities (1)

- Line 224: potential_n_plus_one
  ```python
  for schedule in queryset:
  ```

### odoo_db_manager/advanced_sync_settings.py

#### Unused Functions (11)

- Line 239: `is_advanced_sync_enabled()`
- Line 243: `get_max_concurrent_syncs()`
- Line 247: `get_sync_timeout()`
- Line 251: `should_send_notifications()`
- Line 255: `get_batch_size()`
- Line 259: `get_cache_timeout()`
- Line 263: `get_conflict_resolution_strategy()`
- Line 267: `is_reverse_sync_enabled()`
- Line 271: `get_date_formats()`
- Line 277: `should_validate_data()`
- Line 281: `get_google_api_rate_limit()`

### odoo_db_manager/db_settings.py

#### Unused Functions (3)

- Line 35: `get_current_time()`
- Line 47: `get_active_database_settings()`
- Line 102: `_create_default_settings()`

### odoo_db_manager/forms.py

#### Unused Functions (5)

- Line 174: `__init__()`
- Line 65: `save()`
- Line 249: `clean()`
- Line 190: `clean_inspections_folder_id()`
- Line 200: `clean_credentials_file()`

#### Unused Classes (5)

- Line 10: `DatabaseForm`
- Line 138: `Meta`
- Line 86: `BackupScheduleForm`
- Line 135: `GoogleDriveConfigForm`
- Line 214: `ImportSelectionForm`

### odoo_db_manager/google_sheets_import.py

#### Unused Functions (8)

- Line 14: `__init__()`
- Line 18: `initialize()`
- Line 87: `_test_connection()`
- Line 114: `get_available_sheets()`
- Line 131: `get_sheet_data()`
- Line 164: `preview_data()`
- Line 184: `import_data_by_type()`
- Line 343: `update_sheet_data()`

#### Unused Classes (1)

- Line 13: `GoogleSheetsImporter`

#### Query Optimization Opportunities (12)

- Line 64: potential_n_plus_one
  ```python
  field for field in required_fields
  ```
- Line 122: potential_n_plus_one
  ```python
  for sheet in spreadsheet.get('sheets', []):
  ```
- Line 230: potential_n_plus_one
  ```python
  model_fields = {f.name: f for f in Model._meta.get_fields() if not f.auto_create
  ```
- Line 239: potential_n_plus_one
  ```python
  for row_index, row in enumerate(rows, start=2):
  ```
- Line 243: potential_n_plus_one
  ```python
  for i, value in enumerate(row):
  ```
- Line 248: potential_n_plus_one
  ```python
  for mf in model_fields:
  ```
- Line 272: potential_n_plus_one
  ```python
  for rel_field in RelatedModel._meta.fields:
  ```
- Line 305: potential_n_plus_one
  ```python
  unique_fields = [f.name for f in Model._meta.fields if f.unique and f.name in ob
  ```
- Line 307: potential_n_plus_one
  ```python
  for uf in unique_fields:
  ```
- Line 315: potential_n_plus_one
  ```python
  for k, v in obj_data.items():
  ```
- Line 320: potential_n_plus_one
  ```python
  for k, v in date_fields_to_set.items():
  ```
- Line 328: potential_n_plus_one
  ```python
  for k, v in date_fields_to_set.items():
  ```

### odoo_db_manager/google_sheets_utils.py

#### Unused Functions (4)

- Line 13: `encode_sheet_name()`
- Line 90: `get_sheet_data_safe()`
- Line 201: `get_available_sheets()`
- Line 243: `safe_sheet_operation()`

#### Query Optimization Opportunities (3)

- Line 38: potential_n_plus_one
  ```python
  any(char in clean_sheet_name for char in ['!', "'", '"', '-', '(', ')', '[', ']'
  ```
- Line 71: potential_n_plus_one
  ```python
  for sheet in spreadsheet.get('sheets', []):
  ```
- Line 177: potential_n_plus_one
  ```python
  for sheet in spreadsheet.get('sheets', [])
  ```

### odoo_db_manager/import_forms.py

#### Unused Functions (2)

- Line 85: `__init__()`
- Line 160: `clean()`

#### Unused Classes (2)

- Line 8: `GoogleSheetsImportForm`
- Line 135: `SheetSelectionForm`

#### Query Optimization Opportunities (1)

- Line 92: potential_n_plus_one
  ```python
  for sheet in available_sheets:
  ```

### odoo_db_manager/smart_restore_service.py

#### Unused Functions (10)

- Line 20: `__init__()`
- Line 93: `create_missing_dependencies()`
- Line 108: `ensure_content_types()`
- Line 130: `preprocess_data()`
- Line 165: `sort_data_by_dependencies()`
- Line 183: `restore_item_with_retry()`
- Line 203: `fix_foreign_key_issues()`
- Line 227: `restore_from_file()`
- Line 332: `read_backup_file()`
- Line 358: `clear_existing_data()`

#### Unused Classes (1)

- Line 17: `SmartRestoreService`

#### Query Optimization Opportunities (12)

- Line 121: potential_n_plus_one
  ```python
  for app_label, model_name in required_content_types:
  ```
- Line 134: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 155: potential_n_plus_one
  ```python
  for key, value in fields.items():
  ```
- Line 171: potential_n_plus_one
  ```python
  for model_name in self.dependency_order:
  ```
- Line 172: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 177: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 185: potential_n_plus_one
  ```python
  for attempt in range(max_retries):
  ```
- Line 188: potential_n_plus_one
  ```python
  for obj in serializers.deserialize('json', json.dumps([item])):
  ```
- Line 271: potential_n_plus_one
  ```python
  for i, item in enumerate(sorted_data):
  ```
- Line 295: potential_n_plus_one
  ```python
  for i, (original_index, item, original_error) in enumerate(failed_items):
  ```
- Line 361: potential_n_plus_one
  ```python
  for item in data:
  ```
- Line 367: potential_n_plus_one
  ```python
  for model_name in reversed(self.dependency_order):
  ```

### odoo_db_manager/views_google_import.py

#### Unused Functions (10)

- Line 18: `is_staff_or_superuser()`
- Line 25: `google_sheets_import_dashboard()`
- Line 44: `google_sheets_import_form()`
- Line 94: `handle_import_form_submission()`
- Line 142: `google_sheets_import_preview()`
- Line 187: `google_sheets_import_execute()`
- Line 273: `google_sheets_import_result()`
- Line 301: `import_logs()`
- Line 322: `get_sheets_ajax()`
- Line 365: `google_import_all()`

#### Query Optimization Opportunities (4)

- Line 60: potential_n_plus_one
  ```python
  if available_sheets and not all(isinstance(s, str) for s in available_sheets):
  ```
- Line 64: potential_n_plus_one
  ```python
  for s in available_sheets
  ```
- Line 378: potential_n_plus_one
  ```python
  for sheet in all_sheets:
  ```
- Line 379: potential_n_plus_one
  ```python
  if any(key in sheet.lower() for key in supported_keys):
  ```

### orders/invoice_views.py

#### Unused Functions (13)

- Line 24: `invoice_editor()`
- Line 30: `invoice_builder()`
- Line 140: `template_list()`
- Line 180: `save_template()`
- Line 275: `load_template()`
- Line 343: `clone_template()`
- Line 376: `delete_template()`
- Line 409: `set_default_template()`
- Line 438: `preview_invoice()`
- Line 452: `print_invoice_with_template()`
- Line 465: `template_analytics()`
- Line 504: `export_template()`
- Line 571: `import_template()`

#### Query Optimization Opportunities (5)

- Line 147: missing_select_related
  ```python
  templates = templates.filter(name__icontains=search_query)
  ```
- Line 475: missing_select_related
  ```python
  most_used = templates.filter(usage_count__gt=0)[:5]
  ```
- Line 472: potential_n_plus_one
  ```python
  total_usage = sum(template.usage_count for template in templates)
  ```
- Line 479: potential_n_plus_one
  ```python
  for template_type, name in InvoiceTemplate.TEMPLATE_TYPES:
  ```
- Line 481: potential_n_plus_one
  ```python
  usage = sum(t.usage_count for t in templates.filter(template_type=template_type)
  ```

### orders/tasks.py

#### Unused Functions (6)

- Line 14: `upload_contract_to_drive_async()`
- Line 60: `upload_inspection_to_drive_async()`
- Line 104: `cleanup_failed_uploads()`
- Line 164: `update_order_status_async()`
- Line 202: `calculate_order_totals_async()`
- Line 230: `clear_expired_cache()`

#### Query Optimization Opportunities (2)

- Line 120: potential_n_plus_one
  ```python
  for order in failed_orders:
  ```
- Line 139: potential_n_plus_one
  ```python
  for inspection in failed_inspections:
  ```

### orders/middleware.py

#### Unused Functions (4)

- Line 16: `__init__()`
- Line 19: `__call__()`
- Line 31: `get_current_user()`
- Line 40: `set_current_user()`

#### Unused Classes (1)

- Line 10: `CurrentUserMiddleware`

### orders/tracking.py

#### Unused Functions (5)

- Line 38: `unified_order_tracking_pre_save()`
- Line 57: `unified_order_tracking_post_save()`
- Line 199: `track_order_change()`
- Line 244: `orderitem_tracking_pre_save()`
- Line 261: `orderitem_tracking_post_save()`

### orders/utils.py

#### Unused Functions (15)

- Line 31: `update_inspection_status_with_user()`
- Line 46: `track_installation_status_change()`
- Line 60: `track_manufacturing_status_change()`
- Line 74: `track_cutting_status_change()`
- Line 89: `update_order_status()`
- Line 143: `can_user_modify_order()`
- Line 169: `log_multiple_changes()`
- Line 198: `update_order_contract_invoice()`
- Line 227: `cleanup_old_status_logs()`
- Line 248: `example_view_usage()`
- Line 290: `update_order_with_tracking()`
- Line 321: `update_order_items_with_tracking()`
- Line 399: `update_contract_invoice_numbers()`
- Line 435: `quick_update_order()`
- Line 476: `simple_order_update()`

#### Query Optimization Opportunities (6)

- Line 182: potential_n_plus_one
  ```python
  for field_name, change_data in changes_dict.items():
  ```
- Line 213: potential_n_plus_one
  ```python
  for field_name, new_value in kwargs.items():
  ```
- Line 308: potential_n_plus_one
  ```python
  for field_name, new_value in field_updates.items():
  ```
- Line 345: potential_n_plus_one
  ```python
  for item_data in items_data:
  ```
- Line 355: potential_n_plus_one
  ```python
  for field in ['quantity', 'unit_price', 'discount_percentage']:
  ```
- Line 422: potential_n_plus_one
  ```python
  for field_name, new_value in updates.items():
  ```

### reports/apps.py

#### Unused Classes (1)

- Line 4: `ReportsConfig`

### reports/forms.py

#### Unused Functions (2)

- Line 42: `__init__()`
- Line 94: `clean_parameters()`

#### Unused Classes (3)

- Line 9: `ReportForm`
- Line 86: `Meta`
- Line 85: `ReportScheduleForm`

### reports/models.py

#### Unused Functions (1)

- Line 101: `__str__()`

#### Unused Classes (3)

- Line 97: `Meta`
- Line 36: `SavedReport`
- Line 63: `ReportSchedule`

### tests/test_comprehensive_sync.py

#### Query Optimization Opportunities (1)

- Line 71: potential_n_plus_one
  ```python
  for name, func in test_functions:
  ```

### tests/test_notification_icons.py

#### Query Optimization Opportunities (1)

- Line 31: potential_n_plus_one
  ```python
  for notification in notifications:
  ```

### tests/test_views.py

#### Unused Functions (1)

- Line 6: `test_inspections_view()`

### cutting/forms.py

#### Unused Functions (2)

- Line 193: `__init__()`
- Line 197: `clean()`

#### Unused Classes (7)

- Line 8: `CuttingOrderForm`
- Line 172: `Meta`
- Line 47: `CuttingItemForm`
- Line 116: `BulkUpdateForm`
- Line 169: `CuttingReportForm`
- Line 209: `CuttingFilterForm`
- Line 260: `QuickCompleteForm`

### cutting/signals.py

#### Unused Functions (8)

- Line 174: `handle_order_item_creation()`
- Line 236: `update_cutting_order_status()`
- Line 263: `create_manufacturing_item_on_cutting_completion()`
- Line 311: `send_completion_notification()`
- Line 333: `send_stock_shortage_notification()`
- Line 354: `create_missing_cutting_orders()`
- Line 382: `update_cutting_order_status_on_item_completion()`
- Line 421: `update_order_status_based_on_cutting_orders()`

#### Query Optimization Opportunities (11)

- Line 152: missing_select_related
  ```python
  fabric_warehouse = warehouses.filter(name__icontains='بافلي').first()
  ```
- Line 158: missing_select_related
  ```python
  accessory_warehouse = warehouses.filter(name__icontains='اكسسوار').first()
  ```
- Line 44: potential_n_plus_one
  ```python
  for item in order_items:
  ```
- Line 57: potential_n_plus_one
  ```python
  for warehouse_data in warehouse_items.values():
  ```
- Line 75: potential_n_plus_one
  ```python
  ) for item in items
  ```
- Line 98: potential_n_plus_one
  ```python
  for warehouse in warehouses:
  ```
- Line 139: potential_n_plus_one
  ```python
  for category_key, warehouse_names in category_warehouse_mapping.items():
  ```
- Line 141: potential_n_plus_one
  ```python
  for warehouse_name in warehouse_names:
  ```
- Line 151: potential_n_plus_one
  ```python
  if any(keyword in product_name for keyword in ['قماش', 'fabric', 'textile', 'خيط
  ```
- Line 157: potential_n_plus_one
  ```python
  elif any(keyword in product_name for keyword in ['اكسسوار', 'accessory', 'زر', '
  ```
- Line 366: potential_n_plus_one
  ```python
  for order in orders_without_cutting:
  ```

### tools/fix_changed_by.py

#### Query Optimization Opportunities (1)

- Line 13: potential_n_plus_one
  ```python
  for l in logs:
  ```

### cutting/management/commands/create_missing_cutting_orders.py

#### Unused Functions (1)

- Line 8: `handle()`

#### Unused Classes (1)

- Line 5: `Command`

### reports/templatetags/report_extras.py

#### Unused Functions (1)

- Line 6: `multiply()`

### reports/management/commands/create_sample_reports.py

#### Unused Functions (1)

- Line 8: `handle()`

#### Unused Classes (1)

- Line 5: `Command`

#### Query Optimization Opportunities (1)

- Line 47: potential_n_plus_one
  ```python
  for data in reports_data:
  ```

### orders/templatetags/decimal_filters.py

#### Unused Functions (2)

- Line 48: `clean_decimal_with_unit()`
- Line 63: `clean_decimal_currency()`

### orders/templatetags/order_extras.py

#### Unused Functions (14)

- Line 9: `parse_selected_types()`
- Line 34: `get_type_display()`
- Line 45: `get_type_badge_class()`
- Line 56: `get_type_icon()`
- Line 67: `get_order_type_badge()`
- Line 128: `get_vip_badge()`
- Line 140: `get_status_badge()`
- Line 232: `get_status_display()`
- Line 257: `currency_format()`
- Line 269: `paid_percentage()`
- Line 287: `remaining_amount()`
- Line 300: `get_selected_type_display()`
- Line 310: `timesince_days()`
- Line 326: `days_until()`

#### Query Optimization Opportunities (1)

- Line 29: potential_n_plus_one
  ```python
  result = [match[0] or match[1] for match in matches]
  ```

### orders/management/commands/clear_cache.py

#### Unused Functions (5)

- Line 15: `add_arguments()`
- Line 42: `handle()`
- Line 111: `show_cache_stats()`
- Line 147: `clear_cache_programmatically()`
- Line 248: `generate_cache_report()`

#### Unused Classes (1)

- Line 12: `Command`

#### Query Optimization Opportunities (3)

- Line 229: potential_n_plus_one
  ```python
  for i in range(100):
  ```
- Line 232: potential_n_plus_one
  ```python
  for i in range(100):
  ```
- Line 235: potential_n_plus_one
  ```python
  for i in range(100):
  ```

### orders/management/commands/create_test_inspection_order.py

#### Unused Functions (1)

- Line 13: `handle()`

#### Unused Classes (1)

- Line 10: `Command`

### orders/management/commands/create_test_order.py

#### Unused Functions (1)

- Line 14: `handle()`

#### Unused Classes (1)

- Line 11: `Command`

#### Query Optimization Opportunities (2)

- Line 54: potential_n_plus_one
  ```python
  for product in products:
  ```
- Line 69: potential_n_plus_one
  ```python
  total_amount = sum(item.quantity * item.unit_price for item in order.items.all()
  ```

### orders/management/commands/recalculate_orders_total.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

#### Query Optimization Opportunities (1)

- Line 9: potential_n_plus_one
  ```python
  for order in Order.objects.all():
  ```

### orders/management/commands/recompute_order_totals.py

#### Unused Functions (2)

- Line 12: `add_arguments()`
- Line 17: `handle()`

#### Unused Classes (1)

- Line 6: `Command`

#### Query Optimization Opportunities (1)

- Line 32: potential_n_plus_one
  ```python
  for order in qs.iterator(chunk_size=batch):
  ```

### orders/management/commands/setup_delivery_settings.py

#### Unused Functions (1)

- Line 8: `handle()`

#### Unused Classes (1)

- Line 5: `Command`

#### Query Optimization Opportunities (1)

- Line 31: potential_n_plus_one
  ```python
  for setting_data in default_settings:
  ```

### orders/management/commands/setup_orders_permissions.py

#### Unused Functions (1)

- Line 13: `handle()`

#### Unused Classes (1)

- Line 10: `Command`

#### Query Optimization Opportunities (3)

- Line 28: potential_n_plus_one
  ```python
  for codename, name in permissions_to_create:
  ```
- Line 46: potential_n_plus_one
  ```python
  for group_name, permission_codenames in groups_to_create:
  ```
- Line 53: potential_n_plus_one
  ```python
  for codename in permission_codenames:
  ```

### orders/management/commands/setup_user_roles.py

#### Unused Functions (3)

- Line 13: `add_arguments()`
- Line 37: `handle()`
- Line 121: `_assign_permissions()`

#### Unused Classes (1)

- Line 10: `Command`

#### Query Optimization Opportunities (2)

- Line 94: missing_select_related
  ```python
  branches = Branch.objects.filter(id__in=managed_branches)
  ```
- Line 165: potential_n_plus_one
  ```python
  for perm_codename in permissions:
  ```

### orders/management/commands/sync_order_statuses.py

#### Unused Functions (1)

- Line 13: `handle()`

#### Unused Classes (1)

- Line 10: `Command`

#### Query Optimization Opportunities (8)

- Line 47: missing_select_related
  ```python
  orders = list(Order.objects.filter(pk__in=order_ids))
  ```
- Line 95: missing_select_related
  ```python
  qs = Order.objects.filter(pk__in=batch_ids).exclude(order_status='completed')
  ```
- Line 121: missing_select_related
  ```python
  remaining_qs = Order.objects.filter(manufacturing_order__isnull=True).exclude(or
  ```
- Line 43: potential_n_plus_one
  ```python
  for start in range(0, total_pairs, chunk):
  ```
- Line 45: potential_n_plus_one
  ```python
  order_ids = [p[0] for p in batch_pairs]
  ```
- Line 48: potential_n_plus_one
  ```python
  order_map = {o.pk: o for o in orders}
  ```
- Line 52: potential_n_plus_one
  ```python
  for oid, new_status in batch_pairs:
  ```
- Line 92: potential_n_plus_one
  ```python
  for start in range(0, total_inst_orders, chunk):
  ```

### orders/management/commands/update_orders_total_amount.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

#### Query Optimization Opportunities (1)

- Line 9: potential_n_plus_one
  ```python
  for order in Order.objects.all():
  ```

### odoo_db_manager/middleware/default_user.py

#### Unused Functions (4)

- Line 20: `__init__()`
- Line 23: `__call__()`
- Line 39: `_check_and_create_default_user()`
- Line 72: `_is_database_ready()`

### odoo_db_manager/services/database_service.py

#### Unused Functions (20)

- Line 213: `activate_database()`
- Line 39: `create_database()`
- Line 111: `_check_postgresql_db_exists()`
- Line 149: `_create_sqlite_database()`
- Line 165: `_create_postgresql_database()`
- Line 197: `_check_command_exists()`
- Line 228: `_update_settings_file()`
- Line 259: `discover_postgresql_databases()`
- Line 356: `sync_discovered_databases()`
- Line 393: `sync_databases_from_settings()`
- Line 460: `delete_database()`
- Line 490: `_delete_sqlite_database()`
- Line 501: `_delete_postgresql_database()`
- Line 533: `test_connection()`
- Line 555: `_test_postgresql_connection()`
- Line 576: `_test_sqlite_connection()`
- Line 603: `create_physical_database()`
- Line 654: `_format_size()`
- Line 665: `check_django_tables()`
- Line 718: `run_migrations()`

#### Unused Classes (1)

- Line 13: `DatabaseService`

#### Query Optimization Opportunities (6)

- Line 140: potential_n_plus_one
  ```python
  for line in result.stdout.splitlines():
  ```
- Line 301: potential_n_plus_one
  ```python
  for row in cursor.fetchall():
  ```
- Line 364: potential_n_plus_one
  ```python
  for db_info in discovered_dbs:
  ```
- Line 413: potential_n_plus_one
  ```python
  for db_id, db_info in db_settings.get('databases', {}).items():
  ```
- Line 433: potential_n_plus_one
  ```python
  connection_info = {k: v for k, v in db_info.items() if k != 'ENGINE'}
  ```
- Line 659: potential_n_plus_one
  ```python
  for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
  ```

### odoo_db_manager/templatetags/arabic_filters.py

#### Unused Functions (5)

- Line 42: `safe_arabic_text()`
- Line 65: `is_arabic_text()`
- Line 108: `format_field_type()`
- Line 145: `truncate_arabic()`
- Line 168: `debug_encoding()`

#### Query Optimization Opportunities (4)

- Line 33: potential_n_plus_one
  ```python
  value = ''.join(char for char in value if unicodedata.category(char) != 'Cf')
  ```
- Line 75: potential_n_plus_one
  ```python
  return any(ord(char) in arabic_range for char in str(value))
  ```
- Line 98: potential_n_plus_one
  ```python
  for char in unwanted_chars:
  ```
- Line 184: potential_n_plus_one
  ```python
  for i, char in enumerate(str(value)[:10]):
  ```

### odoo_db_manager/templatetags/mapping_tags.py

#### Unused Functions (2)

- Line 6: `get_mapping_value()`
- Line 13: `is_column_mapped()`

### odoo_db_manager/templatetags/odoo_filters.py

#### Unused Functions (1)

- Line 12: `pprint()`

### odoo_db_manager/management/commands/diagnose_sync.py

#### Unused Functions (4)

- Line 12: `add_arguments()`
- Line 15: `handle()`
- Line 23: `diagnose_mapping()`
- Line 121: `diagnose_all_mappings()`

#### Unused Classes (1)

- Line 9: `Command`

#### Query Optimization Opportunities (3)

- Line 36: potential_n_plus_one
  ```python
  for col, field in column_mappings.items():
  ```
- Line 53: potential_n_plus_one
  ```python
  for error in errors:
  ```
- Line 131: potential_n_plus_one
  ```python
  for mapping in mappings:
  ```

### odoo_db_manager/management/commands/fix_sequence.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

### odoo_db_manager/management/commands/list_mappings.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

#### Query Optimization Opportunities (2)

- Line 19: potential_n_plus_one
  ```python
  for id, name in mappings:
  ```
- Line 23: potential_n_plus_one
  ```python
  max_id = max(mapping[0] for mapping in mappings)
  ```

### odoo_db_manager/management/commands/migrate_google_unified.py

#### Unused Functions (5)

- Line 22: `add_arguments()`
- Line 34: `handle()`
- Line 91: `migrate_config_to_mapping()`
- Line 177: `migrate_logs_to_tasks()`
- Line 265: `cleanup_old_system()`

#### Unused Classes (1)

- Line 19: `Command`

#### Query Optimization Opportunities (3)

- Line 147: potential_n_plus_one
  ```python
  for key, value in mapping_data.items():
  ```
- Line 208: potential_n_plus_one
  ```python
  for old_log in old_logs:
  ```
- Line 244: potential_n_plus_one
  ```python
  for key, value in task_data.items():
  ```

### odoo_db_manager/management/commands/reset_sequence.py

#### Unused Functions (2)

- Line 7: `add_arguments()`
- Line 11: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

### odoo_db_manager/management/commands/reset_sequence_high.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

### odoo_db_manager/management/commands/run_scheduled_backups.py

#### Unused Functions (3)

- Line 19: `add_arguments()`
- Line 36: `handle()`
- Line 143: `_should_run_now()`

#### Unused Classes (1)

- Line 16: `Command`

#### Query Optimization Opportunities (1)

- Line 70: potential_n_plus_one
  ```python
  for schedule in schedules:
  ```

### notifications/templatetags/notification_tags.py

#### Unused Functions (5)

- Line 9: `getattribute()`
- Line 91: `notification_badge()`
- Line 104: `notification_settings_summary()`
- Line 130: `is_notification_enabled()`
- Line 144: `notifications_enabled_for_user()`

### manufacturing/management/commands/fix_manufacturing_order_types.py

#### Unused Functions (5)

- Line 14: `add_arguments()`
- Line 26: `handle()`
- Line 152: `determine_order_type()`
- Line 166: `get_statistics()`
- Line 178: `display_statistics()`

#### Unused Classes (1)

- Line 11: `Command`

#### Query Optimization Opportunities (4)

- Line 37: missing_select_related
  ```python
  queryset = queryset.filter(order_date__year=year)
  ```
- Line 51: potential_n_plus_one
  ```python
  for mfg in empty_orders:
  ```
- Line 90: potential_n_plus_one
  ```python
  for mfg in queryset.exclude(order_type=''):
  ```
- Line 107: potential_n_plus_one
  ```python
  for mfg, correct_type in mismatched_orders:
  ```

### manufacturing/management/commands/setup_approval_permissions.py

#### Unused Functions (2)

- Line 12: `add_arguments()`
- Line 24: `handle()`

#### Unused Classes (1)

- Line 9: `Command`

#### Query Optimization Opportunities (2)

- Line 61: potential_n_plus_one
  ```python
  for user in staff_users:
  ```
- Line 83: potential_n_plus_one
  ```python
  for user in users_with_permission:
  ```

### manufacturing/management/commands/sync_order_statuses.py

#### Unused Functions (2)

- Line 10: `add_arguments()`
- Line 22: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (1)

- Line 36: potential_n_plus_one
  ```python
  for mfg_order in manufacturing_orders:
  ```

### inventory/templatetags/inventory_math_filters.py

#### Unused Functions (2)

- Line 6: `multiply()`
- Line 14: `divide()`

### inventory/management/commands/add_test_stock.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

#### Query Optimization Opportunities (1)

- Line 16: potential_n_plus_one
  ```python
  for product in products:
  ```

### inventory/management/commands/create_test_products.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

#### Query Optimization Opportunities (2)

- Line 37: potential_n_plus_one
  ```python
  for product_data in fabric_products:
  ```
- Line 81: potential_n_plus_one
  ```python
  for product_data in accessory_products:
  ```

### inventory/management/commands/fix_product_imports.py

#### Unused Functions (2)

- Line 8: `add_arguments()`
- Line 21: `handle()`

#### Unused Classes (1)

- Line 5: `Command`

#### Query Optimization Opportunities (1)

- Line 45: missing_select_related
  ```python
  products_with_null_category = Product.objects.filter(category__isnull=True)
  ```

### installations/templatetags/custom_filters.py

#### Unused Functions (3)

- Line 7: `split()`
- Line 15: `get_month_name()`
- Line 37: `currency_format()`

### crm/middleware/cloudflare_hosts.py

#### Unused Functions (4)

- Line 83: `__init__()`
- Line 86: `__call__()`
- Line 59: `_extract_host_from_error()`
- Line 70: `_is_auto_allowed_host()`

#### Unused Classes (2)

- Line 11: `CloudflareHostsMiddleware`
- Line 78: `DynamicAllowedHostsMiddleware`

#### Query Optimization Opportunities (1)

- Line 72: potential_n_plus_one
  ```python
  for pattern in self.auto_allowed_patterns:
  ```

### crm/middleware/permission_handler.py

#### Unused Functions (3)

- Line 11: `__init__()`
- Line 14: `__call__()`
- Line 17: `process_exception()`

#### Unused Classes (1)

- Line 10: `PermissionDeniedMiddleware`

### crm/middleware/websocket_blocker.py

#### Unused Functions (1)

- Line 17: `process_request()`

#### Unused Classes (1)

- Line 12: `BlockWebSocketMiddleware`

#### Query Optimization Opportunities (1)

- Line 35: potential_n_plus_one
  ```python
  for blocked_path in blocked_paths:
  ```

### crm/management/commands/check_sequences.py

#### Unused Functions (12)

- Line 43: `add_arguments()`
- Line 70: `handle()`
- Line 119: `check_all_sequences()`
- Line 148: `check_app_sequences()`
- Line 193: `check_single_table()`
- Line 224: `check_table_sequence()`
- Line 280: `extract_sequence_name()`
- Line 288: `check_sequence_health()`
- Line 428: `display_table_result()`
- Line 462: `display_app_summary()`
- Line 479: `display_summary()`
- Line 537: `export_results()`

#### Unused Classes (1)

- Line 40: `Command`

#### Query Optimization Opportunities (10)

- Line 134: potential_n_plus_one
  ```python
  for app_name in local_apps:
  ```
- Line 140: potential_n_plus_one
  ```python
  for key in all_results:
  ```
- Line 171: potential_n_plus_one
  ```python
  for model in models:
  ```
- Line 257: potential_n_plus_one
  ```python
  for column_name, column_default, is_identity in auto_columns:
  ```
- Line 490: potential_n_plus_one
  ```python
  critical = [p for p in problems if p.get('severity') == 'critical']
  ```
- Line 491: potential_n_plus_one
  ```python
  warnings = [p for p in problems if p.get('severity') == 'warning']
  ```
- Line 497: potential_n_plus_one
  ```python
  for problem in critical:
  ```
- Line 505: potential_n_plus_one
  ```python
  for warning in warnings:
  ```
- Line 522: potential_n_plus_one
  ```python
  for error in errors:
  ```
- Line 528: potential_n_plus_one
  ```python
  critical_count = len([p for p in problems if p.get('severity') == 'critical'])
  ```

### crm/management/commands/monitor_db.py

#### Unused Functions (8)

- Line 16: `__init__()`
- Line 20: `add_arguments()`
- Line 52: `handle()`
- Line 72: `_signal_handler()`
- Line 81: `_show_status()`
- Line 144: `_cleanup_connections()`
- Line 162: `_single_check()`
- Line 183: `_start_monitoring()`

#### Unused Classes (1)

- Line 13: `Command`

#### Query Optimization Opportunities (2)

- Line 127: potential_n_plus_one
  ```python
  active_alerts = [k for k, v in alerts.items() if v]
  ```
- Line 131: potential_n_plus_one
  ```python
  for alert_type in active_alerts:
  ```

### crm/management/commands/sequence_manager.py

#### Unused Functions (11)

- Line 18: `add_arguments()`
- Line 57: `handle()`
- Line 84: `handle_check()`
- Line 103: `handle_fix()`
- Line 122: `handle_monitor()`
- Line 141: `handle_auto()`
- Line 156: `handle_info()`
- Line 228: `handle_reset()`
- Line 284: `find_table_for_sequence()`
- Line 291: `get_max_id_for_table()`
- Line 301: `print_help()`

#### Unused Classes (1)

- Line 15: `Command`

#### Query Optimization Opportunities (1)

- Line 192: potential_n_plus_one
  ```python
  for seq in sequences:
  ```

### crm/management/commands/auto_fix_sequences.py

#### Unused Functions (6)

- Line 18: `add_arguments()`
- Line 30: `handle()`
- Line 58: `detect_sequence_problems()`
- Line 115: `extract_sequence_name()`
- Line 126: `check_sequence_problem()`
- Line 173: `fix_sequences()`

#### Unused Classes (1)

- Line 14: `Command`

#### Query Optimization Opportunities (2)

- Line 84: potential_n_plus_one
  ```python
  for row in tables_with_sequences:
  ```
- Line 197: potential_n_plus_one
  ```python
  for row in tables_with_sequences:
  ```

### complaints/templatetags/file_tags.py

#### Unused Functions (1)

- Line 7: `filesize_format()`

### complaints/tests/test_integration.py

#### Unused Functions (15)

- Line 26: `setUp()`
- Line 94: `test_dashboard_performance_optimization()`
- Line 111: `test_notification_service_integration()`
- Line 127: `test_status_update_api()`
- Line 155: `test_assignment_update_api()`
- Line 176: `test_search_api()`
- Line 189: `test_stats_api()`
- Line 202: `test_notifications_api()`
- Line 224: `test_cross_module_integration()`
- Line 237: `test_template_tags_functionality()`
- Line 259: `test_database_optimization_command()`
- Line 271: `test_form_validation_enhancements()`
- Line 299: `test_ui_enhancements()`
- Line 314: `test_permission_system()`
- Line 331: `tearDown()`

#### Unused Classes (1)

- Line 21: `ComplaintsSystemIntegrationTest`

### complaints/utils/export.py

#### Unused Functions (2)

- Line 9: `export_complaints_to_csv()`
- Line 67: `export_complaints_to_excel()`

#### Query Optimization Opportunities (6)

- Line 12: missing_select_related
  ```python
  queryset = Complaint.objects.filter(id__in=selected_ids)
  ```
- Line 70: missing_select_related
  ```python
  queryset = Complaint.objects.filter(id__in=selected_ids)
  ```
- Line 42: potential_n_plus_one
  ```python
  for complaint in queryset.select_related(
  ```
- Line 127: potential_n_plus_one
  ```python
  for col, header in enumerate(headers):
  ```
- Line 144: potential_n_plus_one
  ```python
  for row, complaint in enumerate(queryset.select_related(
  ```
- Line 173: potential_n_plus_one
  ```python
  for col, value in enumerate(data):
  ```

### complaints/management/commands/check_overdue_complaints.py

#### Unused Functions (2)

- Line 17: `add_arguments()`
- Line 30: `handle()`

#### Unused Classes (1)

- Line 14: `Command`

#### Query Optimization Opportunities (6)

- Line 64: potential_n_plus_one
  ```python
  for complaint in overdue_complaints:
  ```
- Line 90: potential_n_plus_one
  ```python
  for complaint in overdue_complaints:
  ```
- Line 138: potential_n_plus_one
  ```python
  for complaint in overdue_complaints:
  ```
- Line 142: potential_n_plus_one
  ```python
  for dept, count in departments.items():
  ```
- Line 147: potential_n_plus_one
  ```python
  for complaint in overdue_complaints:
  ```
- Line 152: potential_n_plus_one
  ```python
  for assignee, count in assignees.items():
  ```

### complaints/management/commands/cleanup_notifications.py

#### Unused Functions (2)

- Line 8: `add_arguments()`
- Line 15: `handle()`

#### Unused Classes (1)

- Line 5: `Command`

### complaints/management/commands/diagnose_complaints.py

#### Unused Functions (9)

- Line 15: `add_arguments()`
- Line 27: `handle()`
- Line 45: `check_database_status()`
- Line 61: `check_groups()`
- Line 82: `check_user_permissions()`
- Line 109: `check_complaints_status()`
- Line 136: `check_specific_user()`
- Line 176: `check_specific_complaint()`
- Line 206: `performance_test()`

#### Unused Classes (1)

- Line 12: `Command`

#### Query Optimization Opportunities (4)

- Line 72: potential_n_plus_one
  ```python
  for group_name in required_groups:
  ```
- Line 97: potential_n_plus_one
  ```python
  for user in users_without_permissions[:5]:
  ```
- Line 119: potential_n_plus_one
  ```python
  for stat in status_stats:
  ```
- Line 144: potential_n_plus_one
  ```python
  groups = [group.name for group in user.groups.all()]
  ```

### complaints/management/commands/fix_complaints_performance.py

#### Unused Functions (5)

- Line 14: `add_arguments()`
- Line 36: `handle()`
- Line 55: `create_required_groups()`
- Line 73: `fix_user_permissions()`
- Line 120: `create_database_indexes()`

#### Unused Classes (1)

- Line 11: `Command`

#### Query Optimization Opportunities (4)

- Line 66: potential_n_plus_one
  ```python
  for group_name in groups:
  ```
- Line 82: potential_n_plus_one
  ```python
  for user in users_without_permissions:
  ```
- Line 105: potential_n_plus_one
  ```python
  for perm in existing_permissions:
  ```
- Line 173: potential_n_plus_one
  ```python
  for index_sql in indexes:
  ```

### complaints/management/commands/fix_dashboard_stats.py

#### Unused Functions (6)

- Line 16: `add_arguments()`
- Line 33: `handle()`
- Line 56: `show_current_stats()`
- Line 84: `fix_overdue_complaints()`
- Line 137: `send_overdue_notifications()`
- Line 168: `validate_stats_consistency()`

#### Unused Classes (1)

- Line 13: `Command`

#### Query Optimization Opportunities (4)

- Line 65: potential_n_plus_one
  ```python
  for status, label in Complaint.STATUS_CHOICES:
  ```
- Line 107: potential_n_plus_one
  ```python
  for complaint in overdue_complaints[:10]:  # أول 10 فقط للعرض
  ```
- Line 144: potential_n_plus_one
  ```python
  for complaint in complaints:
  ```
- Line 208: potential_n_plus_one
  ```python
  for issue in issues:
  ```

### complaints/management/commands/optimize_complaints_db.py

#### Unused Functions (2)

- Line 11: `add_arguments()`
- Line 18: `handle()`

#### Unused Classes (1)

- Line 8: `Command`

#### Query Optimization Opportunities (2)

- Line 112: potential_n_plus_one
  ```python
  for cmd in optimization_commands:
  ```
- Line 118: potential_n_plus_one
  ```python
  for cmd in optimization_commands:
  ```

### complaints/management/commands/setup_complaint_types.py

#### Unused Functions (1)

- Line 9: `handle()`

#### Unused Classes (1)

- Line 6: `Command`

#### Query Optimization Opportunities (2)

- Line 57: potential_n_plus_one
  ```python
  for complaint_type_data in complaint_types:
  ```
- Line 70: potential_n_plus_one
  ```python
  for key, value in complaint_type_data.items():
  ```

### complaints/management/commands/setup_complaints_permissions.py

#### Unused Functions (7)

- Line 14: `add_arguments()`
- Line 36: `handle()`
- Line 55: `create_groups()`
- Line 73: `setup_permissions()`
- Line 104: `assign_permissions_to_groups()`
- Line 133: `assign_users()`
- Line 187: `show_statistics()`

#### Unused Classes (1)

- Line 11: `Command`

#### Query Optimization Opportunities (7)

- Line 66: potential_n_plus_one
  ```python
  for group_name, description in groups_to_create:
  ```
- Line 92: potential_n_plus_one
  ```python
  for codename, name in permissions_to_create:
  ```
- Line 125: potential_n_plus_one
  ```python
  for group_name, permissions in groups_permissions.items():
  ```
- Line 153: potential_n_plus_one
  ```python
  for user in admin_users:
  ```
- Line 174: potential_n_plus_one
  ```python
  for user in staff_users:
  ```
- Line 180: potential_n_plus_one
  ```python
  for user in superusers:
  ```
- Line 192: potential_n_plus_one
  ```python
  for group_name in groups:
  ```

### complaints/management/commands/test_complaint_edit_restrictions.py

#### Unused Functions (4)

- Line 19: `add_arguments()`
- Line 31: `handle()`
- Line 42: `create_test_data()`
- Line 93: `test_edit_restrictions()`

#### Unused Classes (1)

- Line 16: `Command`

#### Query Optimization Opportunities (3)

- Line 97: missing_select_related
  ```python
  complaints = Complaint.objects.filter(title__startswith='شكوى اختبار')
  ```
- Line 77: potential_n_plus_one
  ```python
  for status in statuses:
  ```
- Line 99: potential_n_plus_one
  ```python
  for complaint in complaints:
  ```

### complaints/management/commands/test_filters.py

#### Unused Functions (6)

- Line 17: `add_arguments()`
- Line 39: `handle()`
- Line 60: `create_test_data()`
- Line 68: `test_filter_form()`
- Line 98: `test_filter_queries()`
- Line 128: `test_complete_filtering()`

#### Unused Classes (1)

- Line 14: `Command`

#### Query Optimization Opportunities (4)

- Line 84: potential_n_plus_one
  ```python
  for field, value in form.cleaned_data.items():
  ```
- Line 89: potential_n_plus_one
  ```python
  for field, errors in form.errors.items():
  ```
- Line 169: potential_n_plus_one
  ```python
  for status_code, status_name in Complaint.STATUS_CHOICES:
  ```
- Line 176: potential_n_plus_one
  ```python
  for priority_code, priority_name in Complaint.PRIORITY_CHOICES:
  ```

### accounts/middleware/current_user.py

#### Unused Functions (5)

- Line 12: `get_current_user()`
- Line 17: `get_current_request()`
- Line 28: `process_request()`
- Line 33: `process_response()`
- Line 41: `process_exception()`

#### Unused Classes (1)

- Line 22: `CurrentUserMiddleware`

### accounts/services/dashboard_service.py

#### Unused Classes (1)

- Line 11: `DashboardService`

#### Query Optimization Opportunities (6)

- Line 30: missing_select_related
  ```python
  new_customers_last_month = customers.filter(created_at__gte=last_month).count()
  ```
- Line 39: missing_select_related
  ```python
  orders_last_month = orders.filter(created_at__gte=last_month)
  ```
- Line 47: potential_n_plus_one
  ```python
  for p in products
  ```
- Line 91: potential_n_plus_one
  ```python
  for order in orders:
  ```
- Line 103: potential_n_plus_one
  ```python
  for trans in transactions:
  ```
- Line 128: potential_n_plus_one
  ```python
  for order in orders[:limit]:
  ```

### accounts/templatetags/dict_utils.py

#### Unused Functions (2)

- Line 7: `to_json()`
- Line 15: `get_item()`

### accounts/templatetags/url_filters.py

#### Unused Functions (1)

- Line 6: `fix_url()`

### accounts/management/commands/assign_departments.py

#### Unused Functions (2)

- Line 13: `add_arguments()`
- Line 41: `handle()`

#### Unused Classes (1)

- Line 10: `Command`

#### Query Optimization Opportunities (5)

- Line 57: potential_n_plus_one
  ```python
  for dept in departments:
  ```
- Line 66: potential_n_plus_one
  ```python
  for dept in current_departments:
  ```
- Line 82: potential_n_plus_one
  ```python
  dept_codes = [code.strip() for code in options['departments'].split(',')]
  ```
- Line 91: potential_n_plus_one
  ```python
  missing_codes = [code for code in dept_codes if code not in found_codes]
  ```
- Line 110: potential_n_plus_one
  ```python
  for dept in existing_departments:
  ```

### accounts/management/commands/check_user_sequence.py

#### Unused Functions (1)

- Line 10: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

### accounts/management/commands/cleanup_activity_logs.py

#### Unused Functions (7)

- Line 17: `add_arguments()`
- Line 61: `handle()`
- Line 115: `cleanup_online_users()`
- Line 135: `cleanup_expired_sessions()`
- Line 154: `cleanup_activity_logs()`
- Line 188: `cleanup_login_history()`
- Line 207: `cleanup_excessive_logs_per_user()`

#### Unused Classes (1)

- Line 14: `Command`

#### Query Optimization Opportunities (4)

- Line 120: missing_select_related
  ```python
  offline_users = OnlineUser.objects.filter(last_seen__lt=timeout_date)
  ```
- Line 216: missing_select_related
  ```python
  ).filter(log_count__gt=max_logs)
  ```
- Line 174: potential_n_plus_one
  ```python
  id__in=[log.id for log in batch]
  ```
- Line 220: potential_n_plus_one
  ```python
  for user in users_with_excess_logs:
  ```

### accounts/management/commands/cleanup_departments.py

#### Unused Functions (2)

- Line 10: `add_arguments()`
- Line 22: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (6)

- Line 116: missing_select_related
  ```python
  remaining_departments = Department.objects.filter(code__in=real_departments)
  ```
- Line 50: potential_n_plus_one
  ```python
  for dept in all_departments:
  ```
- Line 64: potential_n_plus_one
  ```python
  for dept in real_deps:
  ```
- Line 69: potential_n_plus_one
  ```python
  for dept in fake_deps:
  ```
- Line 93: potential_n_plus_one
  ```python
  for dept in fake_deps:
  ```
- Line 118: potential_n_plus_one
  ```python
  for dept in remaining_departments.order_by('order'):
  ```

### accounts/management/commands/cleanup_fake_departments.py

#### Unused Functions (2)

- Line 10: `add_arguments()`
- Line 22: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (3)

- Line 34: missing_select_related
  ```python
  departments_to_delete = Department.objects.filter(code__in=fake_departments)
  ```
- Line 44: potential_n_plus_one
  ```python
  for dept in departments_to_delete:
  ```
- Line 62: potential_n_plus_one
  ```python
  for dept in departments_to_delete:
  ```

### accounts/management/commands/create_admin_user.py

#### Unused Functions (2)

- Line 10: `add_arguments()`
- Line 16: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

### accounts/management/commands/create_core_departments.py

#### Unused Functions (1)

- Line 10: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

### accounts/management/commands/create_sample_activity.py

#### Unused Functions (7)

- Line 19: `add_arguments()`
- Line 41: `handle()`
- Line 189: `get_random_ip()`
- Line 193: `get_random_user_agent()`
- Line 204: `get_activity_description()`
- Line 218: `get_random_url_path()`
- Line 233: `get_page_title()`

#### Unused Classes (1)

- Line 16: `Command`

#### Query Optimization Opportunities (4)

- Line 68: potential_n_plus_one
  ```python
  for day in range(days):
  ```
- Line 71: potential_n_plus_one
  ```python
  for user in users:
  ```
- Line 119: potential_n_plus_one
  ```python
  for activity_num in range(random.randint(activities_per_day // 2, activities_per
  ```
- Line 155: potential_n_plus_one
  ```python
  for i in range(online_users_count):
  ```

### accounts/management/commands/ensure_departments.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

#### Query Optimization Opportunities (2)

- Line 22: potential_n_plus_one
  ```python
  for dept in default_departments:
  ```
- Line 38: potential_n_plus_one
  ```python
  for field in ['url', 'icon', 'order']:
  ```

### accounts/management/commands/fix_duplicate_users.py

#### Unused Functions (3)

- Line 11: `add_arguments()`
- Line 23: `handle()`
- Line 31: `fix_sessions()`

#### Unused Classes (1)

- Line 8: `Command`

#### Query Optimization Opportunities (9)

- Line 79: missing_select_related
  ```python
  expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
  ```
- Line 97: missing_select_related
  ```python
  ).filter(count__gt=1).order_by('username')
  ```
- Line 44: potential_n_plus_one
  ```python
  for key in session_keys:
  ```
- Line 57: potential_n_plus_one
  ```python
  for key in duplicate_keys:
  ```
- Line 100: potential_n_plus_one
  ```python
  duplicate_usernames = [item['username'] for item in duplicate_users]
  ```
- Line 109: potential_n_plus_one
  ```python
  for username in duplicate_usernames:
  ```
- Line 117: potential_n_plus_one
  ```python
  for i, user in enumerate(users):
  ```
- Line 129: potential_n_plus_one
  ```python
  for dup_user in duplicate_users:
  ```
- Line 132: potential_n_plus_one
  ```python
  for role in UserRole.objects.filter(user=dup_user):
  ```

### accounts/management/commands/fix_inventory_department_code.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

### accounts/management/commands/fix_inventory_url.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

### accounts/management/commands/fix_user_model_references.py

#### Unused Functions (4)

- Line 11: `handle()`
- Line 25: `fix_content_types()`
- Line 55: `fix_permissions()`
- Line 74: `fix_foreign_keys()`

#### Unused Classes (1)

- Line 8: `Command`

### accounts/management/commands/grant_department_permissions.py

#### Unused Functions (2)

- Line 15: `add_arguments()`
- Line 27: `handle()`

#### Unused Classes (1)

- Line 12: `Command`

#### Query Optimization Opportunities (2)

- Line 35: potential_n_plus_one
  ```python
  for perm in permissions:
  ```
- Line 57: potential_n_plus_one
  ```python
  for user in users:
  ```

### accounts/management/commands/list_departments.py

#### Unused Functions (1)

- Line 10: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (7)

- Line 21: potential_n_plus_one
  ```python
  for dept in departments:
  ```
- Line 30: potential_n_plus_one
  ```python
  for dept_type, dept_list in by_type.items():
  ```
- Line 32: potential_n_plus_one
  ```python
  for dept in dept_list:
  ```
- Line 58: potential_n_plus_one
  ```python
  for code in real_departments:
  ```
- Line 62: potential_n_plus_one
  ```python
  for dept in departments:
  ```
- Line 68: potential_n_plus_one
  ```python
  for code in missing:
  ```
- Line 73: potential_n_plus_one
  ```python
  for dept in extra:
  ```

### accounts/management/commands/reset_activity_data.py

#### Unused Functions (2)

- Line 15: `add_arguments()`
- Line 28: `handle()`

#### Unused Classes (1)

- Line 12: `Command`

### accounts/management/commands/reset_sequence.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

### accounts/management/commands/restore_deleted_departments.py

#### Unused Functions (2)

- Line 10: `add_arguments()`
- Line 17: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (4)

- Line 115: potential_n_plus_one
  ```python
  for dept_data in departments_to_restore:
  ```
- Line 123: potential_n_plus_one
  ```python
  for name in existing_departments:
  ```
- Line 133: potential_n_plus_one
  ```python
  for dept_data in missing_departments:
  ```
- Line 145: potential_n_plus_one
  ```python
  for dept_data in missing_departments:
  ```

### accounts/management/commands/setup_branch.py

#### Unused Functions (1)

- Line 9: `handle()`

#### Unused Classes (1)

- Line 6: `Command`

#### Query Optimization Opportunities (1)

- Line 23: missing_select_related
  ```python
  customers_updated = Customer.objects.filter(branch__isnull=True).update(branch=b
  ```

### accounts/management/commands/setup_dashboard_years.py

#### Unused Functions (2)

- Line 12: `add_arguments()`
- Line 30: `handle()`

#### Unused Classes (1)

- Line 9: `Command`

#### Query Optimization Opportunities (2)

- Line 46: potential_n_plus_one
  ```python
  for year in years_to_add:
  ```
- Line 90: potential_n_plus_one
  ```python
  for year_setting in DashboardYearSettings.objects.all().order_by('-year'):
  ```

### accounts/management/commands/setup_inventory_permissions.py

#### Unused Functions (1)

- Line 10: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (8)

- Line 41: potential_n_plus_one
  ```python
  for action in ['add', 'change', 'delete', 'view']:
  ```
- Line 54: potential_n_plus_one
  ```python
  for action in ['add', 'change', 'delete', 'view']:
  ```
- Line 67: potential_n_plus_one
  ```python
  for action in ['add', 'change', 'delete', 'view']:
  ```
- Line 80: potential_n_plus_one
  ```python
  for action in ['add', 'change', 'delete', 'view']:
  ```
- Line 93: potential_n_plus_one
  ```python
  for action in ['add', 'change', 'delete', 'view']:
  ```
- Line 106: potential_n_plus_one
  ```python
  for action in ['add', 'change', 'delete', 'view']:
  ```
- Line 122: potential_n_plus_one
  ```python
  for user in inventory_users:
  ```
- Line 123: potential_n_plus_one
  ```python
  for perm in permissions:
  ```

### accounts/management/commands/setup_roles.py

#### Unused Functions (1)

- Line 10: `handle()`

#### Unused Classes (1)

- Line 7: `Command`

#### Query Optimization Opportunities (1)

- Line 172: potential_n_plus_one
  ```python
  for user in superusers:
  ```

### accounts/management/commands/update_inventory_url.py

#### Unused Functions (1)

- Line 7: `handle()`

#### Unused Classes (1)

- Line 4: `Command`

### accounts/management/commands/update_requirements.py

#### Unused Functions (7)

- Line 16: `add_arguments()`
- Line 23: `handle()`
- Line 60: `get_installed_packages()`
- Line 70: `parse_requirements_file()`
- Line 88: `normalize_package_name()`
- Line 92: `find_new_packages()`
- Line 111: `add_packages_to_requirements()`

#### Unused Classes (1)

- Line 13: `Command`

#### Query Optimization Opportunities (4)

- Line 46: potential_n_plus_one
  ```python
  for package in new_packages:
  ```
- Line 79: potential_n_plus_one
  ```python
  for line in lines:
  ```
- Line 96: potential_n_plus_one
  ```python
  for package_line in installed_packages:
  ```
- Line 115: potential_n_plus_one
  ```python
  for package in new_packages:
  ```

### accounts/management/commands/update_role_permissions.py

#### Unused Functions (4)

- Line 12: `add_arguments()`
- Line 16: `handle()`
- Line 49: `update_user_permissions_for_role()`
- Line 55: `update_permissions_for_user()`

#### Unused Classes (1)

- Line 9: `Command`

#### Query Optimization Opportunities (4)

- Line 43: potential_n_plus_one
  ```python
  for user in users:
  ```
- Line 51: potential_n_plus_one
  ```python
  for user_role in user_roles:
  ```
- Line 63: potential_n_plus_one
  ```python
  for user_role in user_roles:
  ```
- Line 65: potential_n_plus_one
  ```python
  for permission in role.permissions.all():
  ```

