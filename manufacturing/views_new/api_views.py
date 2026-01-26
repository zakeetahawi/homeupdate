"""
Manufacturing API Views - REST endpoints for manufacturing operations
عروض API للتصنيع - نقاط نهاية REST لعمليات التصنيع
"""

from typing import Any, Dict
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction

from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order


@login_required
@require_http_methods(["GET"])
def manufacturing_order_api(request: HttpRequest, pk: int) -> JsonResponse:
    """
    API للحصول على بيانات أمر تصنيع
    
    Args:
        request: طلب HTTP
        pk: معرف أمر التصنيع
        
    Returns:
        JsonResponse: بيانات الأمر بصيغة JSON
    """
    try:
        order = get_object_or_404(
            ManufacturingOrder.objects.select_related('order', 'order__customer'),
            pk=pk
        )
        
        data = {
            'id': order.id,
            'contract_number': order.contract_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'order': {
                'id': order.order.id,
                'order_number': order.order.order_number,
                'customer': order.order.customer.name,
            },
            'created_at': order.created_at.isoformat(),
            'expected_delivery_date': order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
            'notes': order.notes,
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def update_status_api(request: HttpRequest, pk: int) -> JsonResponse:
    """
    API لتحديث حالة أمر التصنيع
    
    Args:
        request: طلب HTTP
        pk: معرف أمر التصنيع
        
    Returns:
        JsonResponse: نتيجة التحديث
    """
    try:
        order = get_object_or_404(ManufacturingOrder, pk=pk)
        
        # الحصول على الحالة الجديدة
        new_status = request.POST.get('status')
        
        if not new_status:
            return JsonResponse({'error': 'الحالة مطلوبة'}, status=400)
        
        # التحقق من الحالة الصالحة
        valid_statuses = ['pending', 'in_progress', 'on_hold', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({'error': 'حالة غير صالحة'}, status=400)
        
        # تحديث الحالة
        with transaction.atomic():
            order.status = new_status
            order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'تم تحديث الحالة بنجاح',
            'new_status': new_status,
            'status_display': order.get_status_display()
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def manufacturing_statistics_api(request: HttpRequest) -> JsonResponse:
    """
    API للحصول على إحصائيات التصنيع
    
    Returns:
        JsonResponse: إحصائيات شاملة
    """
    try:
        stats = {
            'total_orders': ManufacturingOrder.objects.count(),
            'pending': ManufacturingOrder.objects.filter(status='pending').count(),
            'in_progress': ManufacturingOrder.objects.filter(status='in_progress').count(),
            'on_hold': ManufacturingOrder.objects.filter(status='on_hold').count(),
            'completed': ManufacturingOrder.objects.filter(status='completed').count(),
            'cancelled': ManufacturingOrder.objects.filter(status='cancelled').count(),
        }
        
        return JsonResponse(stats)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def order_items_api(request: HttpRequest, pk: int) -> JsonResponse:
    """
    API للحصول على عناصر أمر التصنيع
    
    Args:
        request: طلب HTTP
        pk: معرف أمر التصنيع
        
    Returns:
        JsonResponse: قائمة العناصر
    """
    try:
        order = get_object_or_404(ManufacturingOrder, pk=pk)
        items = order.items.select_related('product').all()
        
        data = {
            'order_id': order.id,
            'items': [
                {
                    'id': item.id,
                    'product': {
                        'id': item.product.id if item.product else None,
                        'name': item.product.name if item.product else item.product_name,
                    },
                    'quantity': float(item.quantity),
                    'notes': item.notes,
                }
                for item in items
            ]
        }
        
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def bulk_update_status_api(request: HttpRequest) -> JsonResponse:
    """
    API لتحديث حالة عدة أوامر دفعة واحدة
    
    Returns:
        JsonResponse: نتيجة التحديث الجماعي
    """
    try:
        import json
        
        # الحصول على البيانات
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])
        new_status = data.get('status')
        
        if not order_ids or not new_status:
            return JsonResponse({'error': 'معرفات الأوامر والحالة مطلوبة'}, status=400)
        
        # التحديث الجماعي
        with transaction.atomic():
            updated_count = ManufacturingOrder.objects.filter(
                id__in=order_ids
            ).update(status=new_status)
        
        return JsonResponse({
            'success': True,
            'message': f'تم تحديث {updated_count} أمر بنجاح',
            'updated_count': updated_count
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
