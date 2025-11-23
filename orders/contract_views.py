"""
صفحات إدارة العقود - نظام الويزارد فقط
تم حذف نظام القوالب القديم
"""
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Order
from .contract_models import ContractCurtain

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def contract_pdf_view(request, order_id):
    """
    عرض/تحميل العقد بصيغة PDF
    يستخدم الملف المحفوظ مسبقاً، أو يولد ملف جديد إذا لم يكن موجوداً
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # التحقق من وجود ستائر للعقد
        curtains = ContractCurtain.objects.filter(order=order).prefetch_related('fabrics', 'accessories')
        
        if not curtains.exists():
            logger.warning(f"No curtains found for order {order.order_number}")
            return HttpResponse(
                "لا توجد ستائر مرتبطة بهذا الطلب. يرجى إضافة ستائر من خلال نظام الويزارد.",
                status=404
            )
        
        # إذا كان الملف موجوداً ومحفوظاً، نعيد الملف المحفوظ
        if order.contract_file and order.contract_file.name:
            try:
                with order.contract_file.open('rb') as pdf:
                    response = HttpResponse(pdf.read(), content_type='application/pdf')
                    response['Content-Disposition'] = f'inline; filename="contract_{order.order_number}.pdf"'
                    logger.info(f"Serving saved contract PDF for order {order.order_number}")
                    return response
            except Exception as e:
                logger.warning(f"Could not read saved contract file: {e}. Generating new one.")
        
        # إذا لم يكن الملف موجوداً، نولد ملف جديد ونحفظه
        from .services.contract_generation_service import ContractGenerationService
        
        service = ContractGenerationService(order, template=None)
        
        # حفظ الملف في الطلب
        contract_saved = service.save_contract_to_order(user=request.user)
        
        if contract_saved and order.contract_file:
            # إعادة قراءة الملف المحفوظ
            order.refresh_from_db()
            with order.contract_file.open('rb') as pdf:
                response = HttpResponse(pdf.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="contract_{order.order_number}.pdf"'
                logger.info(f"Contract PDF generated and saved for order {order.order_number}")
                return response
        else:
            # إذا فشل الحفظ، نولد PDF مؤقت فقط
            pdf_file = service.generate_pdf()
            response = HttpResponse(pdf_file.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="contract_{order.order_number}.pdf"'
            logger.warning(f"Contract PDF generated temporarily (not saved) for order {order.order_number}")
            return response
        
    except Exception as e:
        logger.error(f"Error generating contract PDF: {e}", exc_info=True)
        return HttpResponse(f"خطأ في توليد العقد: {str(e)}", status=500)


@login_required
@require_http_methods(["POST"])
def regenerate_contract_pdf(request, order_id):
    """
    إعادة توليد ملف العقد PDF وحفظه
    يستخدم عند تعديل بيانات العقد
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # التحقق من وجود ستائر للعقد
        curtains = ContractCurtain.objects.filter(order=order).prefetch_related('fabrics', 'accessories')
        
        if not curtains.exists():
            return JsonResponse({
                'success': False,
                'message': 'لا توجد ستائر مرتبطة بهذا الطلب'
            }, status=400)
        
        # توليد العقد وحفظه
        from .services.contract_generation_service import ContractGenerationService
        
        service = ContractGenerationService(order, template=None)
        contract_saved = service.save_contract_to_order(user=request.user)
        
        if contract_saved:
            logger.info(f"Contract PDF regenerated for order {order.order_number} by {request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'تم إعادة توليد العقد بنجاح',
                'contract_url': f'/orders/order/{order_id}/contract/pdf/'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'فشل في حفظ ملف العقد'
            }, status=500)
        
    except Exception as e:
        logger.error(f"Error regenerating contract PDF: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'خطأ في إعادة توليد العقد: {str(e)}'
        }, status=500)
