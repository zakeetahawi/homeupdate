"""
Context Processors للمخزون - لعرض إشعارات التحويلات في جميع الصفحات
"""
from .models import StockTransfer, Warehouse


def pending_transfers(request):
    """
    إضافة عدد التحويلات المعلقة للمستخدم الحالي
    
    مسؤول المخزون: يرى فقط التحويلات الواردة لمخزنه
    مدير النظام: يرى جميع التحويلات
    """
    if not request.user.is_authenticated:
        return {
            'pending_transfers_count': 0,
            'pending_transfers': []
        }
    
    user = request.user
    
    # مدير النظام يرى جميع التحويلات المعلقة
    if user.is_superuser:
        pending_transfers = StockTransfer.objects.filter(
            status__in=['approved', 'in_transit']
        ).select_related('from_warehouse', 'to_warehouse', 'created_by').order_by('-transfer_date')[:10]
        
        pending_count = StockTransfer.objects.filter(
            status__in=['approved', 'in_transit']
        ).count()
    
    else:
        # مسؤول المخزون يرى فقط التحويلات الواردة لمستودعاته
        managed_warehouses = Warehouse.objects.filter(manager=user)
        
        # إذا كان في مجموعة مسؤول مخزون وليس لديه مستودعات محددة، يرى جميع التحويلات
        is_in_warehouse_group = user.groups.filter(
            name__in=['مسؤول مخزون', 'مسؤول مخازن', 'Warehouse Manager', 'مسؤول مستودع']
        ).exists()
        
        if managed_warehouses.exists():
            # لديه مستودعات محددة
            pending_transfers = StockTransfer.objects.filter(
                to_warehouse__in=managed_warehouses,
                status__in=['approved', 'in_transit']
            ).select_related('from_warehouse', 'to_warehouse', 'created_by').order_by('-transfer_date')[:10]
            
            pending_count = StockTransfer.objects.filter(
                to_warehouse__in=managed_warehouses,
                status__in=['approved', 'in_transit']
            ).count()
        elif is_in_warehouse_group:
            # في مجموعة مسؤول مخزون بدون مستودعات محددة - يرى جميع التحويلات
            pending_transfers = StockTransfer.objects.filter(
                status__in=['approved', 'in_transit']
            ).select_related('from_warehouse', 'to_warehouse', 'created_by').order_by('-transfer_date')[:10]
            
            pending_count = StockTransfer.objects.filter(
                status__in=['approved', 'in_transit']
            ).count()
        else:
            # ليس لديه صلاحيات
            pending_transfers = StockTransfer.objects.none()
            pending_count = 0
    
    # التحقق إذا كان المستخدم مسؤول مخزن
    is_warehouse_manager = False
    if not user.is_superuser:
        # التحقق من كونه مدير مستودع أو عضو في مجموعة مسؤول مخزون
        is_warehouse_manager = (
            Warehouse.objects.filter(manager=user).exists() or
            user.groups.filter(name__in=['مسؤول مخزون', 'مسؤول مخازن', 'Warehouse Manager', 'مسؤول مستودع']).exists()
        )
    
    return {
        'pending_transfers_count': pending_count,
        'pending_transfers': pending_transfers,
        'has_pending_transfers': pending_count > 0,
        'is_warehouse_manager': is_warehouse_manager or user.is_superuser
    }
