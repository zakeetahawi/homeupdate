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
    يعرض الملف المحفوظ فقط - لا يعيد التوليد
    إذا لم يكن الملف موجوداً، يُرجع رسالة خطأ
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # التحقق من وجود الملف المحفوظ
        if order.contract_file and order.contract_file.name:
            try:
                with order.contract_file.open('rb') as pdf:
                    response = HttpResponse(pdf.read(), content_type='application/pdf')
                    response['Content-Disposition'] = f'inline; filename="contract_{order.order_number}.pdf"'
                    logger.info(f"Serving saved contract PDF for order {order.order_number}")
                    return response
            except Exception as e:
                logger.error(f"Could not read saved contract file: {e}")
                return HttpResponse(
                    "خطأ في قراءة ملف العقد. يرجى إعادة توليد العقد.",
                    status=500
                )
        else:
            # لا يوجد ملف محفوظ
            return HttpResponse(
                """
                <html dir="rtl">
                <head>
                    <meta charset="utf-8">
                    <title>ملف العقد غير موجود</title>
                    <style>
                        body { font-family: Arial; text-align: center; padding: 50px; }
                        .message { background: #fff3cd; padding: 20px; border-radius: 5px; max-width: 500px; margin: 0 auto; }
                        h2 { color: #856404; }
                    </style>
                </head>
                <body>
                    <div class="message">
                        <h2>⚠️ ملف العقد غير موجود</h2>
                        <p>لم يتم توليد ملف العقد بعد.</p>
                        <p>يرجى الاتصال بمدير النظام لتوليد العقد.</p>
                        <button onclick="window.close()">إغلاق</button>
                    </div>
                </body>
                </html>
                """,
                status=404
            )
        
    except Exception as e:
        logger.error(f"Error accessing contract PDF: {e}", exc_info=True)
        return HttpResponse(f"خطأ في الوصول للعقد: {str(e)}", status=500)


@login_required
@require_http_methods(["POST"])
def regenerate_contract_pdf(request, order_id):
    """
    إعادة توليد ملف العقد PDF وحفظه
    يستخدم عند تعديل بيانات العقد
    يقوم بأرشفة العقد القديم قبل توليد الجديد
    """
    try:
        # التحقق من صلاحية المستخدم
        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse({
                'success': False,
                'message': 'غير مصرح لك بإعادة توليد العقود'
            }, status=403)
        
        order = get_object_or_404(Order, id=order_id)
        
        # التحقق من وجود ستائر للعقد
        curtains = ContractCurtain.objects.filter(order=order).prefetch_related('fabrics', 'accessories')
        
        if not curtains.exists():
            return JsonResponse({
                'success': False,
                'message': 'لا توجد ستائر مرتبطة بهذا الطلب'
            }, status=400)
        
        # أرشفة العقد القديم إذا كان موجوداً
        if order.contract_file and order.contract_file.name:
            try:
                import os
                import shutil
                from django.conf import settings
                from datetime import datetime
                
                old_file_path = order.contract_file.path
                
                # إنشاء مجلد الأرشيف إن لم يكن موجوداً
                archive_dir = os.path.join(settings.MEDIA_ROOT, 'contracts', 'archive')
                os.makedirs(archive_dir, exist_ok=True)
                
                # اسم الملف المؤرشف مع التاريخ والوقت
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                old_filename = os.path.basename(old_file_path)
                name_without_ext = os.path.splitext(old_filename)[0]
                archived_filename = f"{name_without_ext}_archived_{timestamp}.pdf"
                archived_path = os.path.join(archive_dir, archived_filename)
                
                # نسخ الملف القديم للأرشيف
                shutil.copy2(old_file_path, archived_path)
                logger.info(f"Old contract archived: {archived_filename}")
                
            except Exception as e:
                logger.warning(f"Could not archive old contract: {e}")
                # نكمل حتى لو فشلت الأرشفة
        
        # توليد العقد وحفظه
        from .services.contract_generation_service import ContractGenerationService
        
        service = ContractGenerationService(order, template=None)
        contract_saved = service.save_contract_to_order(user=request.user)
        
        if contract_saved:
            logger.info(f"Contract PDF regenerated for order {order.order_number} by {request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'تم إعادة توليد العقد بنجاح وأرشفة العقد القديم',
                'contract_url': order.contract_file.url
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
