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
        'user_warehouses': [],
        'is_warehouse_manager': False,
    }
    
    if request.user.is_authenticated:
        # التحقق من صلاحيات المستخدم
        # يمكن تحسين هذا بناءً على نظام الصلاحيات الخاص بك
        is_warehouse_manager = (
            request.user.is_staff or 
            request.user.groups.filter(name__in=['مسؤول مخازن', 'Warehouse Manager']).exists()
        )
        
        context['is_warehouse_manager'] = is_warehouse_manager
        
        if is_warehouse_manager:
            # الحصول على المستودعات التي يديرها المستخدم
            # يمكن تحسين هذا بإضافة حقل manager في نموذج Warehouse
            user_warehouses = Warehouse.objects.filter(is_active=True)
            context['user_warehouses'] = user_warehouses
            
            # التحويلات المعلقة للمستودعات التي يديرها
            pending_transfers = StockTransfer.objects.filter(
                to_warehouse__in=user_warehouses,
                status__in=['approved', 'in_transit']
            ).select_related('from_warehouse', 'to_warehouse').order_by('-created_at')[:10]
            
            context['pending_transfers_count'] = pending_transfers.count()
            context['pending_transfers_list'] = pending_transfers
    
    return context

