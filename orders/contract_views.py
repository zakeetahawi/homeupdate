"""
صفحات إدارة العقود - نظام جديد
تم حذف النظام القديم بالكامل
النظام الجديد يعتمد على الويزارد 100%
"""
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from .models import Order
from .contract_models import ContractTemplate, ContractPrintLog
from .services.contract_generation_service import ContractGenerationService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def contract_pdf_view(request, order_id):
    """
    عرض/تحميل العقد بصيغة PDF
    يستخدم القالب الجديد المحسّن من Google Sheets
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # التحقق من وجود ستائر للعقد
        from .contract_models import ContractCurtain
        curtains = ContractCurtain.objects.filter(order=order).prefetch_related('fabrics', 'accessories')
        
        if not curtains.exists():
            logger.warning(f"No curtains found for order {order.order_number}")
            return HttpResponse(
                "لا توجد ستائر مرتبطة بهذا الطلب. يرجى إضافة ستائر من خلال نظام الويزارد.",
                status=404
            )
        
        # الحصول على القالب (افتراضي أو مخصص)
        template = ContractTemplate.get_default_template()
        
        # توليد PDF
        service = ContractGenerationService(order, template)
        pdf_file = service.generate_pdf()
        
        # تسجيل الطباعة
        ContractPrintLog.objects.create(
            order=order,
            template=template,
            printed_by=request.user
        )
        
        # إرجاع PDF
        response = HttpResponse(pdf_file.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="contract_{order.order_number}.pdf"'
        
        logger.info(f"Contract PDF generated for order {order.order_number} by {request.user.username}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating contract PDF: {e}", exc_info=True)
        return HttpResponse(f"خطأ في توليد العقد: {str(e)}", status=500)
