"""
Context processors للمخزون
"""
from django.db.models import Q
from .models import StockTransfer, Warehouse


def pending_transfers(request):
    """
    إضافة التحويلات المعلقة للمستخدم الحالي
    """
    context = {
        'pending_transfers_count': 0,
        'pending_transfers_list': [],
        'incoming_transfers_count': 0,
        'incoming_transfers_list': [],
        'user_warehouses': [],
        'is_warehouse_manager': False,
        'user_managed_warehouses': [],
    }

    if request.user.is_authenticated:
        # التحقق من صلاحيات المستخدم
        # 1. إذا كان مدير مستودع (له مستودعات مخصصة)
        # 2. إذا كان في مجموعة مسؤول مخازن
        # 3. إذا كان staff

        # المستودعات التي يديرها المستخدم
        user_managed_warehouses = Warehouse.objects.filter(
            manager=request.user,
            is_active=True
        ).distinct()

        # جميع المستودعات النشطة
        all_warehouses = Warehouse.objects.filter(is_active=True)

        # مسؤول المخازن فقط (وليس مدير النظام)
        is_warehouse_manager = (
            user_managed_warehouses.exists() or
            request.user.groups.filter(name__in=['مسؤول مخازن', 'Warehouse Manager', 'مسؤول مستودع']).exists()
        )

        context['is_warehouse_manager'] = is_warehouse_manager
        context['user_warehouses'] = all_warehouses
        context['user_managed_warehouses'] = user_managed_warehouses

        if is_warehouse_manager:
            # التحويلات المعلقة (لجميع مسؤولي المخازن - للإنشاء)
            all_pending_transfers = StockTransfer.objects.filter(
                status__in=['approved', 'in_transit']
            ).select_related('from_warehouse', 'to_warehouse').order_by('-created_at')

            context['pending_transfers_count'] = all_pending_transfers.count()
            context['pending_transfers_list'] = list(all_pending_transfers[:10])

        # التحويلات الواردة للمستخدم (المستودعات التي يديرها)
        if user_managed_warehouses.exists():
            incoming_transfers = StockTransfer.objects.filter(
                to_warehouse__in=user_managed_warehouses,
                status__in=['approved', 'in_transit']
            ).select_related('from_warehouse', 'to_warehouse').order_by('-created_at')

            context['incoming_transfers_count'] = incoming_transfers.count()
            context['incoming_transfers_list'] = list(incoming_transfers[:10])

    return context

