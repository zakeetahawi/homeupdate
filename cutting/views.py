from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from datetime import datetime, timedelta
import json

from .models import CuttingOrder, CuttingOrderItem, CuttingReport
from inventory.models import Warehouse
from accounts.models import User
from orders.models import Order
from manufacturing.models import FabricReceipt, FabricReceiptItem


class CuttingDashboardView(LoginRequiredMixin, TemplateView):
    """لوحة تحكم نظام التقطيع"""
    template_name = 'cutting/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الحصول على المستودعات المتاحة للمستخدم مع إحصائيات مفصلة
        user_warehouses = self.get_user_warehouses_with_stats()

        # إحصائيات عامة
        context.update({
            'total_orders': CuttingOrder.objects.filter(warehouse__in=[w['warehouse'] for w in user_warehouses]).count(),
            'pending_orders': CuttingOrder.objects.filter(
                warehouse__in=[w['warehouse'] for w in user_warehouses], status='pending'
            ).count(),
            'in_progress_orders': CuttingOrder.objects.filter(
                warehouse__in=[w['warehouse'] for w in user_warehouses], status='in_progress'
            ).count(),
            'completed_orders': CuttingOrder.objects.filter(
                warehouse__in=[w['warehouse'] for w in user_warehouses], status='completed'
            ).count(),
            'user_warehouses': user_warehouses,
            'recent_orders': CuttingOrder.objects.filter(
                warehouse__in=[w['warehouse'] for w in user_warehouses]
            ).select_related('order', 'order__customer', 'warehouse').order_by('-created_at')[:10]
        })
        
        return context
    
    def get_user_warehouses(self):
        """الحصول على المستودعات المتاحة للمستخدم"""
        user = self.request.user

        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)

        # يمكن إضافة منطق صلاحيات المستودعات هنا
        # مؤقتاً نعرض جميع المستودعات النشطة
        return Warehouse.objects.filter(is_active=True)

    def get_user_warehouses_with_stats(self):
        """الحصول على المستودعات مع إحصائيات أوامر التقطيع"""
        warehouses = self.get_user_warehouses()
        warehouse_stats = []

        for warehouse in warehouses:
            total_orders = CuttingOrder.objects.filter(warehouse=warehouse).count()
            pending_orders = CuttingOrder.objects.filter(
                warehouse=warehouse,
                status__in=['pending', 'in_progress', 'partially_completed']
            ).count()
            completed_orders = CuttingOrder.objects.filter(
                warehouse=warehouse,
                status='completed'
            ).count()

            warehouse_stats.append({
                'warehouse': warehouse,
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'completed_orders': completed_orders,
                'name': warehouse.name,
                'description': warehouse.notes or warehouse.address,
                'id': warehouse.id
            })

        return warehouse_stats


class CuttingOrderListView(LoginRequiredMixin, ListView):
    """قائمة أوامر التقطيع"""
    model = CuttingOrder
    template_name = 'cutting/order_list.html'
    context_object_name = 'cutting_orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CuttingOrder.objects.select_related(
            'order', 'order__customer', 'warehouse', 'assigned_to'
        ).prefetch_related('items')
        
        # فلترة حسب المستودع إذا تم تحديده
        warehouse_id = self.kwargs.get('warehouse_id')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        else:
            # فلترة حسب مستودعات المستخدم
            user_warehouses = self.get_user_warehouses()
            queryset = queryset.filter(warehouse__in=user_warehouses)
        
        # البحث
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(cutting_code__icontains=search) |
                Q(order__contract_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search)
            )
        
        # فلترة حسب الحالة
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_user_warehouses(self):
        """الحصول على المستودعات المتاحة للمستخدم"""
        user = self.request.user
        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)
        return Warehouse.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'warehouses': self.get_user_warehouses(),
            'current_warehouse': self.kwargs.get('warehouse_id'),
            'status_choices': CuttingOrder.STATUS_CHOICES,
            'search_query': self.request.GET.get('search', ''),
            'current_status': self.request.GET.get('status', ''),
        })
        return context


class CuttingOrderDetailView(LoginRequiredMixin, DetailView):
    """تفاصيل أمر التقطيع"""
    model = CuttingOrder
    template_name = 'cutting/order_detail.html'
    context_object_name = 'cutting_order'
    
    def get_queryset(self):
        return CuttingOrder.objects.select_related(
            'order', 'order__customer', 'warehouse', 'assigned_to'
        ).prefetch_related(
            'items__order_item__product',
            'items__updated_by'
        )


@login_required
def cutting_order_detail_by_code(request, cutting_code):
    """عرض تفاصيل أمر التقطيع بالكود"""
    cutting_order = get_object_or_404(
        CuttingOrder.objects.select_related(
            'order', 'order__customer', 'warehouse', 'assigned_to'
        ).prefetch_related(
            'items__order_item__product',
            'items__updated_by'
        ),
        cutting_code=cutting_code
    )
    
    return render(request, 'cutting/order_detail.html', {
        'cutting_order': cutting_order
    })


@login_required
def update_cutting_item(request, pk):
    """تحديث عنصر التقطيع"""
    item = get_object_or_404(CuttingOrderItem, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # تحديث البيانات
            item.cutter_name = data.get('cutter_name', '')
            item.permit_number = data.get('permit_number', '')
            item.receiver_name = data.get('receiver_name', '')
            item.bag_number = data.get('bag_number', '')
            item.additional_quantity = float(data.get('additional_quantity', 0))
            item.notes = data.get('notes', '')
            item.updated_by = request.user
            
            # تحديث الحالة إذا تم ملء البيانات الأساسية
            if item.cutter_name and item.permit_number and item.receiver_name:
                item.status = 'completed'
                item.cutting_date = timezone.now()
                item.delivery_date = timezone.now()
            
            item.save()
            
            return JsonResponse({
                'success': True,
                'message': 'تم تحديث العنصر بنجاح',
                'status': item.get_status_display()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def complete_cutting_item(request, pk):
    """إكمال عنصر التقطيع"""
    item = get_object_or_404(CuttingOrderItem, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            cutter_name = data.get('cutter_name')
            permit_number = data.get('permit_number')
            receiver_name = data.get('receiver_name')
            notes = data.get('notes', '')
            
            if not all([cutter_name, permit_number, receiver_name]):
                return JsonResponse({
                    'success': False,
                    'message': 'يجب ملء جميع البيانات المطلوبة'
                })
            
            item.mark_as_completed(
                cutter_name=cutter_name,
                permit_number=permit_number,
                receiver_name=receiver_name,
                user=request.user,
                notes=notes
            )
            
            return JsonResponse({
                'success': True,
                'message': 'تم إكمال العنصر بنجاح'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def reject_cutting_item(request, pk):
    """رفض عنصر التقطيع"""
    item = get_object_or_404(CuttingOrderItem, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reason = data.get('reason')
            
            if not reason:
                return JsonResponse({
                    'success': False,
                    'message': 'يجب كتابة سبب الرفض'
                })
            
            item.mark_as_rejected(reason=reason, user=request.user)
            
            return JsonResponse({
                'success': True,
                'message': 'تم رفض العنصر'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def bulk_update_items(request, order_id):
    """تحديث مجمع لعناصر أمر التقطيع"""
    cutting_order = get_object_or_404(CuttingOrder, pk=order_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            cutter_name = data.get('cutter_name')
            permit_number = data.get('permit_number')
            receiver_name = data.get('receiver_name')
            bag_number = data.get('bag_number', '')
            
            if not all([cutter_name, permit_number, receiver_name]):
                return JsonResponse({
                    'success': False,
                    'message': 'يجب ملء جميع البيانات المطلوبة'
                })
            
            # تحديث جميع العناصر المعلقة
            updated_count = 0
            for item in cutting_order.items.filter(status='pending'):
                item.cutter_name = cutter_name
                item.permit_number = permit_number
                item.receiver_name = receiver_name
                item.bag_number = bag_number
                item.updated_by = request.user
                item.save()
                updated_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'تم تحديث {updated_count} عنصر'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def bulk_complete_items(request, order_id):
    """إكمال مجمع لعناصر أمر التقطيع"""
    cutting_order = get_object_or_404(CuttingOrder, pk=order_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            cutter_name = data.get('cutter_name')
            permit_number = data.get('permit_number')
            receiver_name = data.get('receiver_name')
            
            if not all([cutter_name, permit_number, receiver_name]):
                return JsonResponse({
                    'success': False,
                    'message': 'يجب ملء جميع البيانات المطلوبة'
                })
            
            # إكمال جميع العناصر المعلقة
            completed_count = 0
            for item in cutting_order.items.filter(status='pending'):
                item.mark_as_completed(
                    cutter_name=cutter_name,
                    permit_number=permit_number,
                    receiver_name=receiver_name,
                    user=request.user
                )
                completed_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'تم إكمال {completed_count} عنصر'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


class CuttingReportsView(LoginRequiredMixin, TemplateView):
    """صفحة التقارير"""
    template_name = 'cutting/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_warehouses = self.get_user_warehouses()

        context.update({
            'warehouses': user_warehouses,
            'report_types': CuttingReport.REPORT_TYPE_CHOICES,
            'recent_reports': CuttingReport.objects.filter(
                warehouse__in=user_warehouses
            ).order_by('-generated_at')[:10]
        })

        return context

    def get_user_warehouses(self):
        user = self.request.user
        if user.is_superuser:
            return Warehouse.objects.filter(is_active=True)
        return Warehouse.objects.filter(is_active=True)


@login_required
def generate_cutting_report(request):
    """إنشاء تقرير تقطيع"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            warehouse_id = data.get('warehouse_id')
            report_type = data.get('report_type')
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()

            warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

            # حساب الإحصائيات
            cutting_orders = CuttingOrder.objects.filter(
                warehouse=warehouse,
                created_at__date__range=[start_date, end_date]
            )

            cutting_items = CuttingOrderItem.objects.filter(
                cutting_order__warehouse=warehouse,
                cutting_order__created_at__date__range=[start_date, end_date]
            )

            # إنشاء التقرير
            report = CuttingReport.objects.create(
                report_type=report_type,
                warehouse=warehouse,
                start_date=start_date,
                end_date=end_date,
                total_orders=cutting_orders.count(),
                completed_items=cutting_items.filter(status='completed').count(),
                rejected_items=cutting_items.filter(status='rejected').count(),
                pending_items=cutting_items.filter(status='pending').count(),
                generated_by=request.user
            )

            return JsonResponse({
                'success': True,
                'message': 'تم إنشاء التقرير بنجاح',
                'report_id': report.id
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def daily_cutting_report(request, warehouse_id):
    """تقرير يومي للتقطيع"""
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
    date = request.GET.get('date', timezone.now().date())

    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d').date()

    # الحصول على عناصر التقطيع لليوم المحدد
    cutting_items = CuttingOrderItem.objects.filter(
        cutting_order__warehouse=warehouse,
        cutting_date__date=date,
        status='completed'
    ).select_related(
        'cutting_order__order__customer',
        'order_item__product'
    ).order_by('receiver_name', 'cutting_date')

    # تجميع حسب المستلم
    receivers_data = {}
    for item in cutting_items:
        receiver = item.receiver_name
        if receiver not in receivers_data:
            receivers_data[receiver] = []
        receivers_data[receiver].append(item)

    context = {
        'warehouse': warehouse,
        'date': date,
        'receivers_data': receivers_data,
        'total_items': cutting_items.count()
    }

    return render(request, 'cutting/daily_report.html', context)


@login_required
def print_daily_delivery_report(request, date, receiver):
    """طباعة تقرير التسليم اليومي لمستلم محدد"""
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()

    # الحصول على جميع العناصر المسلمة لهذا المستلم في هذا التاريخ
    cutting_items = CuttingOrderItem.objects.filter(
        receiver_name=receiver,
        delivery_date__date=date_obj,
        status='completed'
    ).select_related(
        'cutting_order__order__customer',
        'order_item__product',
        'cutting_order__warehouse'
    ).order_by('cutting_order__order__customer__name', 'delivery_date')

    context = {
        'receiver': receiver,
        'date': date_obj,
        'cutting_items': cutting_items,
        'total_items': cutting_items.count()
    }

    return render(request, 'cutting/print_daily_delivery.html', context)


@login_required
def warehouse_cutting_stats(request, warehouse_id):
    """إحصائيات المستودع API"""
    warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

    # إحصائيات أوامر التقطيع
    orders_stats = CuttingOrder.objects.filter(warehouse=warehouse).aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        completed=Count('id', filter=Q(status='completed')),
        partially_completed=Count('id', filter=Q(status='partially_completed'))
    )

    # إحصائيات العناصر
    items_stats = CuttingOrderItem.objects.filter(
        cutting_order__warehouse=warehouse
    ).aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        completed=Count('id', filter=Q(status='completed')),
        rejected=Count('id', filter=Q(status='rejected'))
    )

    return JsonResponse({
        'warehouse_name': warehouse.name,
        'orders': orders_stats,
        'items': items_stats
    })


@login_required
def get_item_status(request, item_id):
    """الحصول على حالة عنصر التقطيع API"""
    item = get_object_or_404(CuttingOrderItem, pk=item_id)

    return JsonResponse({
        'status': item.status,
        'status_display': item.get_status_display(),
        'cutter_name': item.cutter_name,
        'permit_number': item.permit_number,
        'receiver_name': item.receiver_name,
        'cutting_date': item.cutting_date.isoformat() if item.cutting_date else None,
        'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None,
        'notes': item.notes,
        'rejection_reason': item.rejection_reason
    })


class CuttingReceiptView(LoginRequiredMixin, ListView):
    """صفحة استلام أوامر التقطيع الجاهزة للاستلام"""
    template_name = 'cutting/cutting_receipt.html'
    context_object_name = 'cutting_orders'
    paginate_by = 20

    def get_queryset(self):
        """الحصول على أوامر التقطيع الجاهزة للاستلام"""
        from django.db.models import Q

        queryset = CuttingOrder.objects.select_related(
            'order', 'order__customer', 'warehouse'
        ).prefetch_related(
            'items'
        ).filter(
            # أوامر التقطيع التي تحتوي على عناصر مكتملة وجاهزة للاستلام
            items__status='completed',
            items__receiver_name__isnull=False,
            items__permit_number__isnull=False,
            # التأكد من عدم استلامها في المصنع بعد
            items__fabric_received=False
        ).filter(
            # تضمين جميع أنواع الطلبات: تركيب، تسليم، إكسسوار، تصنيع
            Q(order__selected_types__icontains='installation') |
            Q(order__selected_types__icontains='tailoring') |
            Q(order__selected_types__icontains='accessory') |
            Q(order__selected_types__icontains='manufacturing')
        ).distinct().order_by('-created_at')

        # البحث
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(cutting_code__icontains=search) |
                Q(order__contract_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات
        total_available_orders = self.get_queryset().count()
        context['total_available_orders'] = total_available_orders

        # معلومات الصفحات
        paginator = context.get('paginator')
        if paginator:
            context['total_pages'] = paginator.num_pages
            context['current_page'] = context['page_obj'].number

        return context


@login_required
def receive_cutting_order_ajax(request, cutting_order_id):
    """استلام أمر تقطيع عبر AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})

    try:
        cutting_order = get_object_or_404(CuttingOrder, pk=cutting_order_id)

        # التحقق من وجود عناصر جاهزة للاستلام
        ready_items = cutting_order.items.filter(
            status='completed',
            receiver_name__isnull=False,
            permit_number__isnull=False,
            fabric_received=False
        )

        if not ready_items.exists():
            return JsonResponse({
                'success': False,
                'message': 'لا توجد عناصر جاهزة للاستلام في هذا الأمر'
            })

        data = json.loads(request.body)
        bag_number = data.get('bag_number', '')
        received_by_name = data.get('received_by_name', '')
        notes = data.get('notes', '')

        if not received_by_name:
            return JsonResponse({
                'success': False,
                'message': 'يجب إدخال اسم المستلم'
            })

        # إنشاء استلام الأقمشة
        fabric_receipt = FabricReceipt.objects.create(
            order=cutting_order.order,
            cutting_order=cutting_order,
            receipt_type='cutting_order',
            permit_number=ready_items.first().permit_number,
            bag_number=bag_number,
            received_by_name=received_by_name,
            received_by=request.user,
            notes=notes
        )

        # إنشاء عناصر الاستلام وتحديث حالة العناصر
        items_count = 0
        for item in ready_items:
            FabricReceiptItem.objects.create(
                fabric_receipt=fabric_receipt,
                cutting_item=item,
                order_item=item.order_item,
                quantity_received=item.order_item.quantity + item.additional_quantity,
                item_notes=item.notes or ''
            )

            # تحديث حالة العنصر
            item.fabric_received = True
            item.save()
            items_count += 1

        return JsonResponse({
            'success': True,
            'message': f'تم استلام {items_count} عنصر بنجاح',
            'receipt_id': fabric_receipt.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@login_required
def cutting_notifications_api(request):
    """API للإشعارات المتعلقة بالتقطيع"""
    try:
        from notifications.models import Notification

        notifications = Notification.objects.filter(
            user=request.user,
            notification_type__in=['cutting_completed', 'stock_shortage'],
            is_read=False
        ).order_by('-created_at')[:10]

        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'created_at': notification.created_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'notifications': notifications_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


class WarehouseSettingsView(LoginRequiredMixin, TemplateView):
    """إعدادات المستودعات"""
    template_name = 'cutting/warehouse_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
        return context


class UserPermissionsView(LoginRequiredMixin, TemplateView):
    """إعدادات صلاحيات المستخدمين"""
    template_name = 'cutting/user_permissions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'users': User.objects.filter(is_active=True),
            'warehouses': Warehouse.objects.filter(is_active=True)
        })
        return context


@login_required
def print_cutting_report(request, report_id):
    """طباعة تقرير التقطيع المفصل"""
    from django.db.models import Sum, Count, Q

    report = get_object_or_404(CuttingReport, pk=report_id)

    # الحصول على جميع أوامر التقطيع في الفترة المحددة
    cutting_orders = CuttingOrder.objects.filter(
        warehouse=report.warehouse,
        created_at__date__range=[report.start_date, report.end_date]
    ).select_related(
        'order', 'order__customer', 'warehouse', 'assigned_to'
    ).prefetch_related(
        'items__order_item__product'
    ).order_by('created_at')

    # الحصول على جميع عناصر التقطيع في الفترة
    cutting_items = CuttingOrderItem.objects.filter(
        cutting_order__warehouse=report.warehouse,
        cutting_order__created_at__date__range=[report.start_date, report.end_date]
    ).select_related(
        'cutting_order__order__customer',
        'order_item__product'
    ).order_by('cutting_order__created_at', 'id')

    # إحصائيات تفصيلية
    items_stats = cutting_items.aggregate(
        total_quantity=Sum('order_item__quantity'),
        completed_count=Count('id', filter=Q(status='completed')),
        rejected_count=Count('id', filter=Q(status='rejected')),
        pending_count=Count('id', filter=Q(status='pending')),
        completed_quantity=Sum('order_item__quantity', filter=Q(status='completed')),
        rejected_quantity=Sum('order_item__quantity', filter=Q(status='rejected')),
        pending_quantity=Sum('order_item__quantity', filter=Q(status='pending'))
    )

    # تجميع حسب المنتج
    products_summary = cutting_items.values(
        'order_item__product__name'
    ).annotate(
        total_quantity=Sum('order_item__quantity'),
        completed_count=Count('id', filter=Q(status='completed')),
        rejected_count=Count('id', filter=Q(status='rejected')),
        pending_count=Count('id', filter=Q(status='pending'))
    ).order_by('-total_quantity')

    # تجميع حسب العميل
    customers_summary = cutting_orders.values(
        'order__customer__name',
        'order__contract_number',
        'order__invoice_number'
    ).annotate(
        total_items=Count('items'),
        completed_items=Count('items', filter=Q(items__status='completed')),
        total_quantity=Sum('items__order_item__quantity')
    ).order_by('order__customer__name')

    # تجميع حسب المستلم
    receivers_summary = cutting_items.exclude(
        receiver_name__isnull=True
    ).exclude(
        receiver_name=''
    ).values('receiver_name').annotate(
        total_items=Count('id'),
        completed_items=Count('id', filter=Q(status='completed')),
        total_quantity=Sum('order_item__quantity')
    ).order_by('-total_items')

    context = {
        'report': report,
        'cutting_orders': cutting_orders,
        'cutting_items': cutting_items,
        'items_stats': items_stats,
        'products_summary': products_summary,
        'customers_summary': customers_summary,
        'receivers_summary': receivers_summary,
        'total_orders_count': cutting_orders.count(),
        'total_items_count': cutting_items.count(),
    }

    return render(request, 'cutting/print_report.html', context)


@login_required
def create_cutting_order_from_order(request, order_id):
    """إنشاء أمر تقطيع من طلب موجود"""
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, pk=order_id)

            # التحقق من عدم وجود أمر تقطيع مسبق
            if CuttingOrder.objects.filter(order=order).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'يوجد أمر تقطيع مسبق لهذا الطلب'
                })

            # الحصول على أول مستودع متاح
            warehouse = Warehouse.objects.filter(is_active=True).first()

            if not warehouse:
                return JsonResponse({
                    'success': False,
                    'message': 'لا يوجد مستودع متاح'
                })

            # إنشاء أمر التقطيع
            cutting_order = CuttingOrder.objects.create(
                order=order,
                warehouse=warehouse,
                created_by=request.user,
                notes=f'أمر تقطيع يدوي للطلب {order.order_number}'
            )

            # إنشاء عناصر التقطيع من عناصر الطلب
            for order_item in order.items.all():
                CuttingOrderItem.objects.create(
                    cutting_order=cutting_order,
                    order_item=order_item,
                    status='pending'
                )

            return JsonResponse({
                'success': True,
                'message': f'تم إنشاء أمر التقطيع {cutting_order.cutting_code} بنجاح'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def start_cutting_order(request, order_id):
    """بدء أمر التقطيع"""
    if request.method == 'POST':
        try:
            cutting_order = get_object_or_404(CuttingOrder, pk=order_id)

            if cutting_order.status != 'pending':
                return JsonResponse({
                    'success': False,
                    'message': 'لا يمكن بدء هذا الأمر - الحالة الحالية: ' + cutting_order.get_status_display()
                })

            # تحديث حالة الأمر
            cutting_order.status = 'in_progress'
            cutting_order.assigned_to = request.user
            cutting_order.save()

            return JsonResponse({
                'success': True,
                'message': 'تم بدء أمر التقطيع بنجاح'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})
