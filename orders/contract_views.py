"""
صفحات إدارة العقود والستائر
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.forms import formset_factory

from .models import Order, OrderItem
from .contract_models import ContractTemplate, ContractCurtain, ContractPrintLog
from .contract_forms import ContractCurtainForm, ContractTemplateForm
from .services.contract_generation_service import ContractGenerationService


@login_required
@require_http_methods(["GET", "POST"])
def contract_curtains_manage(request, order_id):
    """صفحة إدارة ستائر العقد"""
    order = get_object_or_404(Order, id=order_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.has_perm('orders.change_order'):
        messages.error(request, 'ليس لديك صلاحية لتعديل العقود')
        return redirect('orders:order_detail', order_id=order_id)
    
    # الحصول على الستائر الموجودة
    existing_curtains = ContractCurtain.objects.filter(order=order).order_by('sequence')
    
    if request.method == 'POST':
        # معالجة البيانات المرسلة
        try:
            # محاولة قراءة JSON من body
            data = json.loads(request.body)
            curtains_data = data.get('curtains', [])
        except:
            # إذا فشل، استخدم POST data
            action = request.POST.get('action')
            if action == 'save_curtains':
                curtains_data = json.loads(request.POST.get('curtains_data', '[]'))
            else:
                curtains_data = []

        if curtains_data:
            try:
                with transaction.atomic():
                    # حذف الستائر القديمة
                    ContractCurtain.objects.filter(order=order).delete()

                    # حفظ الستائر الجديدة
                    
                    for idx, curtain_data in enumerate(curtains_data, start=1):
                        curtain = ContractCurtain(
                            order=order,
                            sequence=idx,
                            room_name=curtain_data.get('room_name', ''),
                            width=curtain_data.get('width', 0),
                            height=curtain_data.get('height', 0),
                            notes=curtain_data.get('notes', '')
                        )
                        
                        # حفظ بيانات القماش الخفيف
                        if curtain_data.get('light_fabric') or curtain_data.get('light_fabric_id'):
                            curtain.light_fabric_id = curtain_data.get('light_fabric') or curtain_data.get('light_fabric_id')
                            curtain.light_fabric_meters = curtain_data.get('light_fabric_meters', 0)
                            curtain.light_fabric_tailoring = curtain_data.get('light_fabric_tailoring', '')
                            curtain.light_fabric_tailoring_size = curtain_data.get('light_fabric_tailoring_size', '')

                        # حفظ بيانات القماش الثقيل
                        if curtain_data.get('heavy_fabric') or curtain_data.get('heavy_fabric_id'):
                            curtain.heavy_fabric_id = curtain_data.get('heavy_fabric') or curtain_data.get('heavy_fabric_id')
                            curtain.heavy_fabric_meters = curtain_data.get('heavy_fabric_meters', 0)
                            curtain.heavy_fabric_tailoring = curtain_data.get('heavy_fabric_tailoring', '')
                            curtain.heavy_fabric_tailoring_size = curtain_data.get('heavy_fabric_tailoring_size', '')

                        # حفظ بيانات البلاك أوت
                        if curtain_data.get('blackout_fabric') or curtain_data.get('blackout_fabric_id'):
                            curtain.blackout_fabric_id = curtain_data.get('blackout_fabric') or curtain_data.get('blackout_fabric_id')
                            curtain.blackout_fabric_meters = curtain_data.get('blackout_fabric_meters', 0)
                            curtain.blackout_fabric_tailoring = curtain_data.get('blackout_fabric_tailoring', '')
                            curtain.blackout_fabric_tailoring_size = curtain_data.get('blackout_fabric_tailoring_size', '')

                        # حفظ بيانات الإكسسوارات
                        curtain.wood_quantity = curtain_data.get('wood_quantity', 0)
                        curtain.wood_type = curtain_data.get('wood_type', '')

                        if curtain_data.get('track_type') or curtain_data.get('track_type_id'):
                            curtain.track_type_id = curtain_data.get('track_type') or curtain_data.get('track_type_id')
                            curtain.track_quantity = curtain_data.get('track_quantity', 0)

                        if curtain_data.get('pipe') or curtain_data.get('pipe_id'):
                            curtain.pipe_id = curtain_data.get('pipe') or curtain_data.get('pipe_id')
                            curtain.pipe_quantity = curtain_data.get('pipe_quantity', 0)

                        if curtain_data.get('bracket') or curtain_data.get('bracket_id'):
                            curtain.bracket_id = curtain_data.get('bracket') or curtain_data.get('bracket_id')
                            curtain.bracket_quantity = curtain_data.get('bracket_quantity', 0)

                        if curtain_data.get('finial') or curtain_data.get('finial_id'):
                            curtain.finial_id = curtain_data.get('finial') or curtain_data.get('finial_id')
                            curtain.finial_quantity = curtain_data.get('finial_quantity', 0)

                        if curtain_data.get('ring') or curtain_data.get('ring_id'):
                            curtain.ring_id = curtain_data.get('ring') or curtain_data.get('ring_id')
                            curtain.ring_quantity = curtain_data.get('ring_quantity', 0)

                        if curtain_data.get('hanger') or curtain_data.get('hanger_id'):
                            curtain.hanger_id = curtain_data.get('hanger') or curtain_data.get('hanger_id')
                            curtain.hanger_quantity = curtain_data.get('hanger_quantity', 0)

                        if curtain_data.get('valance') or curtain_data.get('valance_id'):
                            curtain.valance_id = curtain_data.get('valance') or curtain_data.get('valance_id')
                            curtain.valance_quantity = curtain_data.get('valance_quantity', 0)

                        if curtain_data.get('tassel') or curtain_data.get('tassel_id'):
                            curtain.tassel_id = curtain_data.get('tassel') or curtain_data.get('tassel_id')
                            curtain.tassel_quantity = curtain_data.get('tassel_quantity', 0)

                        if curtain_data.get('tieback_fabric') or curtain_data.get('tieback_fabric_id'):
                            curtain.tieback_fabric_id = curtain_data.get('tieback_fabric') or curtain_data.get('tieback_fabric_id')
                            curtain.tieback_quantity = curtain_data.get('tieback_quantity', 0)

                        if curtain_data.get('belt') or curtain_data.get('belt_id'):
                            curtain.belt_id = curtain_data.get('belt') or curtain_data.get('belt_id')
                            curtain.belt_quantity = curtain_data.get('belt_quantity', 0)
                        
                        curtain.save()
                    
                    messages.success(request, 'تم حفظ بيانات الستائر بنجاح')
                    return JsonResponse({'success': True, 'message': 'تم الحفظ بنجاح'})
                    
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء الحفظ: {str(e)}')
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    # الحصول على عناصر الفاتورة
    order_items = OrderItem.objects.filter(order=order).select_related('product')

    # تحويل عناصر الطلب إلى JSON
    order_items_json = json.dumps([
        {
            'id': item.id,
            'product_name': item.product.name,
            'quantity': float(item.quantity)
        }
        for item in order_items
    ])

    context = {
        'order': order,
        'curtains': existing_curtains,
        'order_items': order_items,
        'order_items_json': order_items_json,
    }

    return render(request, 'orders/contract_curtains_manage.html', context)


@login_required
@require_http_methods(["GET"])
def contract_curtains_data(request, order_id):
    """
    الحصول على بيانات الستائر بصيغة JSON
    """
    order = get_object_or_404(Order, pk=order_id)
    curtains = ContractCurtain.objects.filter(order=order).order_by('sequence')

    curtains_data = []
    for curtain in curtains:
        curtains_data.append({
            'id': curtain.id,
            'sequence': curtain.sequence,
            'room_name': curtain.room_name,
            'width': float(curtain.width),
            'height': float(curtain.height),

            # القماش
            'light_fabric': curtain.light_fabric_id,
            'light_fabric_meters': float(curtain.light_fabric_meters) if curtain.light_fabric_meters else None,
            'light_fabric_tailoring': curtain.light_fabric_tailoring,
            'light_fabric_tailoring_size': curtain.light_fabric_tailoring_size,

            'heavy_fabric': curtain.heavy_fabric_id,
            'heavy_fabric_meters': float(curtain.heavy_fabric_meters) if curtain.heavy_fabric_meters else None,
            'heavy_fabric_tailoring': curtain.heavy_fabric_tailoring,
            'heavy_fabric_tailoring_size': curtain.heavy_fabric_tailoring_size,

            'blackout_fabric': curtain.blackout_fabric_id,
            'blackout_fabric_meters': float(curtain.blackout_fabric_meters) if curtain.blackout_fabric_meters else None,
            'blackout_fabric_tailoring': curtain.blackout_fabric_tailoring,
            'blackout_fabric_tailoring_size': curtain.blackout_fabric_tailoring_size,

            # الإكسسوارات
            'wood_quantity': curtain.wood_quantity,
            'wood_type': curtain.wood_type,
            'track_type': curtain.track_type_id,
            'track_quantity': curtain.track_quantity,
            'pipe': curtain.pipe_id,
            'pipe_quantity': curtain.pipe_quantity,
            'bracket': curtain.bracket_id,
            'bracket_quantity': curtain.bracket_quantity,
            'finial': curtain.finial_id,
            'finial_quantity': curtain.finial_quantity,
            'ring': curtain.ring_id,
            'ring_quantity': curtain.ring_quantity,
            'hanger': curtain.hanger_id,
            'hanger_quantity': curtain.hanger_quantity,
            'valance': curtain.valance_id,
            'valance_quantity': curtain.valance_quantity,
            'tassel': curtain.tassel_id,
            'tassel_quantity': curtain.tassel_quantity,
            'tieback_fabric': curtain.tieback_fabric_id,
            'tieback_quantity': curtain.tieback_quantity,
            'belt': curtain.belt_id,
            'belt_quantity': curtain.belt_quantity,

            'notes': curtain.notes or ''
        })

    return JsonResponse({
        'success': True,
        'curtains': curtains_data
    })


@login_required
@require_http_methods(["GET"])
def contract_pdf_view(request, order_id):
    """عرض PDF للعقد - توليد جديد في كل مرة"""
    order = get_object_or_404(Order, id=order_id)

    # الحصول على القالب الافتراضي
    try:
        template = ContractTemplate.objects.filter(is_active=True).first()
        if not template:
            template = ContractTemplate.objects.first()
    except:
        template = None

    # توليد PDF جديد
    service = ContractGenerationService(order, template)
    pdf_content = service.generate_pdf()

    if not pdf_content:
        return HttpResponse('خطأ في توليد العقد', status=500)

    # إرجاع PDF
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="contract_{order.order_number}.pdf"'

    return response
