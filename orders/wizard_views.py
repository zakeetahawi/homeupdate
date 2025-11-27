"""
Views للويزارد متعدد الخطوات لإنشاء الطلبات
Multi-Step Order Creation Wizard Views
"""
import json
import logging
from decimal import Decimal
from django.db import transaction, models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError

from .wizard_models import (
    DraftOrder, DraftOrderItem
)
from .wizard_forms import (
    Step1BasicInfoForm, Step2OrderTypeForm, Step3OrderItemForm,
    Step4InvoicePaymentForm
)
from .models import Order, OrderItem, Payment
from .contract_models import ContractCurtain, CurtainFabric, CurtainAccessory
from inventory.models import Product
from customers.models import Customer

logger = logging.getLogger(__name__)


def get_total_steps(draft):
    """
    حساب عدد الخطوات الفعلي بناءً على نوع الطلب
    """
    if draft and draft.selected_type:
        # إذا كان النوع يحتاج عقد، 6 خطوات، وإلا 5 خطوات
        needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
        return 6 if needs_contract else 5
    return 6  # افتراضياً 6 خطوات


def get_step_number(draft, logical_step):
    """
    تحويل رقم الخطوة المنطقي إلى رقم الخطوة الفعلي
    عند تخطي خطوة العقد، الخطوة 6 تصبح 5
    """
    if logical_step <= 4:
        return logical_step
    
    needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
    
    if logical_step == 5 and needs_contract:
        return 5  # خطوة العقد
    elif logical_step == 6 and needs_contract:
        return 6  # خطوة المراجعة
    elif logical_step >= 5 and not needs_contract:
        return 5  # تخطي خطوة العقد، المراجعة تصبح الخطوة 5
    
    return logical_step


@login_required
def wizard_start(request):
    """
    بداية الويزارد - عرض المسودات المحفوظة أو إنشاء مسودة جديدة
    """
    # البحث عن المسودات غير المكتملة للمستخدم (بناءً على صلاحياته)
    from accounts.models import Department
    
    if request.user.is_superuser or request.user.groups.filter(name='مدير نظام').exists():
        # مدير النظام - عرض جميع المسودات
        user_drafts = DraftOrder.objects.filter(is_completed=False)
    elif request.user.groups.filter(name='مدير عام').exists():
        # مدير عام - عرض جميع المسودات  
        user_drafts = DraftOrder.objects.filter(is_completed=False)
    elif request.user.groups.filter(name='مدير منطقة').exists():
        # مدير منطقة - عرض مسودات الفروع المرتبطة به
        user_branches = request.user.branches.all()
        user_drafts = DraftOrder.objects.filter(
            is_completed=False,
            branch__in=user_branches
        )
    else:
        # المستخدم العادي - عرض مسوداته فقط
        user_drafts = DraftOrder.objects.filter(
            created_by=request.user,
            is_completed=False
        )
    
    # إذا كان هناك مسودات، توجيه إلى قائمة المسودات
    if user_drafts.exists():
        return redirect('orders:wizard_drafts_list')
    else:
        # إنشاء مسودة جديدة مباشرة
        draft = DraftOrder.objects.create(
            created_by=request.user,
            current_step=1
        )
        return redirect('orders:wizard_step', step=1)


@login_required
def wizard_start_new(request):
    """
    إنشاء مسودة جديدة مباشرة (تجاوز المسودات الموجودة)
    """
    draft = DraftOrder.objects.create(
        created_by=request.user,
        current_step=1
    )
    return redirect('orders:wizard_step', step=1)


@login_required
def wizard_drafts_list(request):
    """
    عرض قائمة المسودات المحفوظة بناءً على صلاحيات المستخدم
    """
    from accounts.models import Department
    
    # تحديد الاستعلام بناءً على صلاحيات المستخدم
    if request.user.is_superuser or request.user.groups.filter(name='مدير نظام').exists():
        # مدير النظام - عرض جميع المسودات
        drafts = DraftOrder.objects.filter(is_completed=False).select_related('created_by', 'customer', 'branch')
    elif request.user.groups.filter(name='مدير عام').exists():
        # مدير عام - عرض جميع المسودات
        drafts = DraftOrder.objects.filter(is_completed=False).select_related('created_by', 'customer', 'branch')
    elif request.user.groups.filter(name='مدير منطقة').exists():
        # مدير منطقة - عرض مسودات الفروع المرتبطة به
        user_branches = request.user.branches.all()
        drafts = DraftOrder.objects.filter(
            is_completed=False,
            branch__in=user_branches
        ).select_related('created_by', 'customer', 'branch')
    else:
        # المستخدم العادي - عرض مسوداته فقط
        drafts = DraftOrder.objects.filter(
            created_by=request.user,
            is_completed=False
        ).select_related('customer', 'branch')
    
    drafts = drafts.order_by('-updated_at')
    
    context = {
        'drafts': drafts,
        'title': 'قائمة المسودات المحفوظة'
    }
    
    return render(request, 'orders/wizard/drafts_list.html', context)


@login_required
def wizard_step(request, step):
    """
    عرض خطوة معينة من الويزارد
    """
    # التحقق من وجود معرف المسودة في الجلسة (وضع التعديل)
    draft_id = request.session.get('wizard_draft_id')
    
    if draft_id:
        # وضع التعديل - استخدام المسودة من الجلسة
        try:
            draft = DraftOrder.objects.get(pk=draft_id, created_by=request.user)
        except DraftOrder.DoesNotExist:
            # المسودة غير موجودة، حذف من الجلسة
            del request.session['wizard_draft_id']
            if 'editing_order_id' in request.session:
                del request.session['editing_order_id']
            messages.error(request, 'المسودة غير موجودة')
            return redirect('orders:wizard_start')
    else:
        # وضع الإنشاء العادي - البحث عن آخر مسودة نشطة
        draft = DraftOrder.objects.filter(
            created_by=request.user,
            is_completed=False
        ).order_by('-updated_at').first()
        
        if not draft:
            # إذا لم توجد مسودة، إنشاء واحدة جديدة
            draft = DraftOrder.objects.create(
                created_by=request.user,
                current_step=1
            )
            return redirect('orders:wizard_step', step=1)
    
    # التحقق من إمكانية الوصول للخطوة
    if not draft.can_access_step(step):
        messages.warning(request, 'يجب إكمال الخطوات السابقة أولاً')
        return redirect('orders:wizard_step', step=draft.current_step)
    
    # توجيه للدالة المناسبة حسب الخطوة
    if step == 1:
        return wizard_step_1_basic_info(request, draft)
    elif step == 2:
        return wizard_step_2_order_type(request, draft)
    elif step == 3:
        return wizard_step_3_order_items(request, draft)
    elif step == 4:
        return wizard_step_4_invoice_payment(request, draft)
    elif step == 5:
        # الخطوة 5 يمكن أن تكون العقد أو المراجعة حسب نوع الطلب
        needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
        if needs_contract:
            return wizard_step_5_contract(request, draft)
        else:
            return wizard_step_6_review(request, draft)  # المراجعة تصبح الخطوة 5
    elif step == 6:
        # الخطوة 6 موجودة فقط للأنواع التي تحتاج عقد
        needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
        if needs_contract:
            return wizard_step_6_review(request, draft)
        else:
            # تم تخطي خطوة العقد، توجيه للخطوة 5
            return redirect('orders:wizard_step', step=5)
    else:
        messages.error(request, 'خطوة غير صحيحة')
        return redirect('orders:wizard_step', step=1)


def wizard_step_1_basic_info(request, draft):
    """
    الخطوة 1: البيانات الأساسية
    """
    if request.method == 'POST':
        form = Step1BasicInfoForm(request.POST, instance=draft, user=request.user)
        if form.is_valid():
            form.save()
            draft.mark_step_complete(1)
            draft.current_step = 2
            draft.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'next_step': 2,
                    'message': 'تم حفظ البيانات الأساسية بنجاح'
                })
            
            messages.success(request, 'تم حفظ البيانات الأساسية بنجاح')
            return redirect('orders:wizard_step', step=2)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'يرجى تصحيح الأخطاء'
                }, status=400)
    else:
        form = Step1BasicInfoForm(instance=draft, user=request.user)
    
    total_steps = get_total_steps(draft)
    
    # التحقق من وضع التعديل
    editing_order_id = request.session.get('editing_order_id')
    editing_mode = editing_order_id is not None
    editing_order = None
    if editing_mode:
        try:
            editing_order = Order.objects.get(pk=editing_order_id)
        except Order.DoesNotExist:
            pass
    
    context = {
        'draft': draft,
        'form': form,
        'current_step': 1,
        'total_steps': total_steps,
        'step_title': 'البيانات الأساسية',
        'progress_percentage': round((1 / total_steps) * 100, 2),
        'editing_mode': editing_mode,
        'editing_order': editing_order,
    }
    
    return render(request, 'orders/wizard/step1_basic_info.html', context)


def wizard_step_2_order_type(request, draft):
    """
    الخطوة 2: نوع الطلب
    """
    if request.method == 'POST':
        form = Step2OrderTypeForm(request.POST, instance=draft, customer=draft.customer)
        if form.is_valid():
            form.save()
            draft.mark_step_complete(2)
            draft.current_step = 3
            draft.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'next_step': 3,
                    'message': 'تم حفظ نوع الطلب بنجاح'
                })
            
            messages.success(request, 'تم حفظ نوع الطلب بنجاح')
            return redirect('orders:wizard_step', step=3)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'يرجى تصحيح الأخطاء'
                }, status=400)
    else:
        form = Step2OrderTypeForm(instance=draft, customer=draft.customer)
    
    total_steps = get_total_steps(draft)
    
    context = {
        'draft': draft,
        'form': form,
        'current_step': 2,
        'total_steps': total_steps,
        'step_title': 'نوع الطلب',
        'progress_percentage': round((2 / total_steps) * 100, 2),
    }
    
    return render(request, 'orders/wizard/step2_order_type.html', context)


def wizard_step_3_order_items(request, draft):
    """
    الخطوة 3: عناصر الطلب
    """
    items = draft.items.all()
    
    total_steps = get_total_steps(draft)
    
    context = {
        'draft': draft,
        'items': items,
        'current_step': 3,
        'total_steps': total_steps,
        'step_title': 'عناصر الطلب',
        'progress_percentage': round((3 / total_steps) * 100, 2),
        'totals': draft.calculate_totals(),
    }
    
    return render(request, 'orders/wizard/step3_order_items.html', context)


@login_required
@require_http_methods(["POST"])
def wizard_add_item(request):
    """
    إضافة عنصر لمسودة الطلب (AJAX)
    """
    try:
        data = json.loads(request.body)
        
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # الحصول على المنتج
        product = get_object_or_404(Product, pk=data.get('product_id'))
        
        # إنشاء العنصر
        item = DraftOrderItem.objects.create(
            draft_order=draft,
            product=product,
            quantity=Decimal(str(data.get('quantity', 1))),
            unit_price=Decimal(str(data.get('unit_price', product.price))),
            discount_percentage=Decimal(str(data.get('discount_percentage', 0))),
            item_type=data.get('item_type', 'product'),
            notes=data.get('notes', '')
        )
        
        # إعادة حساب المجاميع
        totals = draft.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'message': 'تم إضافة العنصر بنجاح',
            'item': {
                'id': item.id,
                'product_name': product.name,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'discount_percentage': float(item.discount_percentage),
                'total_price': float(item.total_price),
                'discount_amount': float(item.discount_amount),
                'final_price': float(item.final_price),
            },
            'totals': {
                'subtotal': float(totals['subtotal']),
                'total_discount': float(totals['total_discount']),
                'final_total': float(totals['final_total']),
                'remaining': float(totals['remaining'])
            }
        })
    
    except Exception as e:
        logger.error(f"Error adding item to draft: {e}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=400)


@login_required
@require_http_methods(["POST"])
def wizard_remove_item(request, item_id):
    """
    حذف عنصر من مسودة الطلب (AJAX)
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # حذف العنصر
        item = get_object_or_404(DraftOrderItem, pk=item_id, draft_order=draft)
        item.delete()
        
        # إعادة حساب المجاميع
        totals = draft.calculate_totals()
        
        return JsonResponse({
            'success': True,
            'message': 'تم حذف العنصر بنجاح',
            'totals': {
                'subtotal': float(totals['subtotal']),
                'total_discount': float(totals['total_discount']),
                'final_total': float(totals['final_total']),
                'remaining': float(totals['remaining'])
            }
        })
    
    except Exception as e:
        logger.error(f"Error removing item from draft: {e}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=400)


@login_required
@require_http_methods(["POST"])
def wizard_complete_step_3(request):
    """
    إكمال الخطوة 3 (عناصر الطلب)
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # التحقق من وجود عناصر
        if not draft.items.exists():
            return JsonResponse({
                'success': False,
                'message': 'يجب إضافة عنصر واحد على الأقل'
            }, status=400)
        
        # تحديد الخطوة كمكتملة
        draft.mark_step_complete(3)
        draft.current_step = 4
        draft.save()
        
        return JsonResponse({
            'success': True,
            'next_step': 4,
            'message': 'تم حفظ العناصر بنجاح'
        })
    
    except Exception as e:
        logger.error(f"Error completing step 3: {e}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=400)


def wizard_step_4_invoice_payment(request, draft):
    """
    الخطوة 4: تفاصيل الفاتورة والدفع
    """
    if request.method == 'POST':
        form = Step4InvoicePaymentForm(
            request.POST,
            request.FILES,
            instance=draft,
            draft_order=draft
        )
        if form.is_valid():
            form.save()
            
            # معالجة الصور الإضافية
            from .wizard_models import DraftOrderInvoiceImage
            for key in request.FILES:
                if key.startswith('additional_invoice_image_'):
                    image = request.FILES[key]
                    DraftOrderInvoiceImage.objects.create(
                        draft_order=draft,
                        image=image
                    )
            
            draft.mark_step_complete(4)
            
            # تحديد الخطوة التالية بناءً على نوع الطلب
            # إذا كان النوع يحتاج عقد، انتقل للخطوة 5 (العقد)، وإلا للخطوة 5 (المراجعة)
            needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
            next_step = 5  # دائماً الخطوة 5 (العقد أو المراجعة)
            draft.current_step = next_step
            draft.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'next_step': next_step,
                    'message': 'تم حفظ تفاصيل الفاتورة والدفع بنجاح'
                })
            
            messages.success(request, 'تم حفظ تفاصيل الفاتورة والدفع بنجاح')
            return redirect('orders:wizard_step', step=next_step)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'يرجى تصحيح الأخطاء'
                }, status=400)
    else:
        form = Step4InvoicePaymentForm(instance=draft, draft_order=draft)
    
    # حساب المجاميع
    totals = draft.calculate_totals()
    
    # إضافة الحد الأدنى للدفع (50%)
    from decimal import Decimal
    final_total = totals.get('final_total', Decimal('0'))
    if isinstance(final_total, float):
        final_total = Decimal(str(final_total))
    totals['minimum_payment'] = (final_total * Decimal('0.5')).quantize(Decimal('0.01'))
    
    total_steps = get_total_steps(draft)
    
    context = {
        'draft': draft,
        'form': form,
        'current_step': 4,
        'total_steps': total_steps,
        'step_title': 'تفاصيل المرجع والدفع',
        'progress_percentage': round((4 / total_steps) * 100, 2),
        'totals': totals,
    }
    
    return render(request, 'orders/wizard/step4_invoice_payment.html', context)


@login_required
@require_http_methods(["POST"])
def delete_draft_invoice_image(request, image_id):
    """حذف صورة فاتورة من المسودة"""
    from .wizard_models import DraftOrderInvoiceImage
    try:
        image = DraftOrderInvoiceImage.objects.get(id=image_id)
        # التحقق من أن المستخدم هو من أنشأ المسودة
        if image.draft_order.created_by != request.user:
            return JsonResponse({'success': False, 'error': 'غير مصرح لك بحذف هذه الصورة'}, status=403)
        
        image.delete()
        return JsonResponse({'success': True})
    except DraftOrderInvoiceImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'الصورة غير موجودة'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def wizard_step_5_contract(request, draft):
    """
    الخطوة 5: العقد الإلكتروني أو PDF
    """
    # معالجة POST - تحديد الخطوة كمكتملة
    if request.method == 'POST':
        # تحديد الخطوة كمكتملة
        draft.mark_step_complete(5)
        draft.current_step = 6
        draft.save()
        
        # الرد برسالة نجاح
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'تم حفظ بيانات العقد'
            })
        else:
            # إعادة توجيه إلى الخطوة التالية
            return redirect('orders:wizard_step', step=6)
    
    # الحصول على الستائر المرتبطة بالمسودة
    curtains = ContractCurtain.objects.filter(draft_order=draft).order_by('sequence')
    
    # الحصول على عناصر الفاتورة (الأقمشة فقط)
    order_items = draft.items.filter(
        item_type__in=['fabric', 'product']
    ).select_related('product')
    
    # حساب الكميات المتاحة لكل عنصر
    items_with_usage = []
    for item in order_items:
        used = CurtainFabric.objects.filter(
            order_item__isnull=False,
            curtain__draft_order=draft,
            order_item__product=item.product
        ).aggregate(total=models.Sum('meters'))['total'] or 0
        
        items_with_usage.append({
            'id': item.id,
            'name': item.product.name,
            'total_quantity': float(item.quantity),
            'used_quantity': float(used),
            'available_quantity': float(item.quantity - used),
        })
    
    # الحصول على خيارات طرق التفصيل من نظام التخصيص
    from .wizard_customization_models import WizardFieldOption
    tailoring_options = WizardFieldOption.get_active_options('tailoring_type')
    installation_options = WizardFieldOption.get_active_options('installation_type')
    
    total_steps = get_total_steps(draft)
    
    context = {
        'draft': draft,
        'curtains': curtains,
        'order_items': items_with_usage,
        'tailoring_options': tailoring_options,
        'installation_options': installation_options,
        'current_step': 5,
        'total_steps': total_steps,
        'step_title': 'العقد',
        'progress_percentage': round((5 / total_steps) * 100, 2),
    }
    
    return render(request, 'orders/wizard/step5_contract.html', context)


def wizard_step_6_review(request, draft):
    """
    الخطوة 6 (أو 5 للأنواع بدون عقد): المراجعة والتأكيد
    """
    items = draft.items.all()
    totals = draft.calculate_totals()
    
    # الحصول على الستائر إن وجدت
    curtains = ContractCurtain.objects.filter(draft_order=draft).order_by('sequence')
    
    # الحصول على ملف العقد إذا كان موجوداً
    contract_file_url = None
    if draft.contract_file:
        contract_file_url = draft.contract_file.url
    
    # الحصول على المعاينة المرتبطة إن وُجدت
    inspection = None
    inspection_file_url = None
    if draft.related_inspection:
        inspection = draft.related_inspection
        # البحث عن ملف المعاينة
        if hasattr(inspection, 'inspection_file') and inspection.inspection_file:
            inspection_file_url = inspection.inspection_file.url
    
    # حساب رقم الخطوة الفعلي (5 أو 6)
    needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
    actual_step = 6 if needs_contract else 5
    total_steps = get_total_steps(draft)
    
    context = {
        'draft': draft,
        'items': items,
        'curtains': curtains,
        'totals': totals,
        'contract_file_url': contract_file_url,
        'inspection': inspection,
        'inspection_file_url': inspection_file_url,
        'current_step': actual_step,
        'total_steps': total_steps,
        'step_title': 'المراجعة والتأكيد',
        'progress_percentage': 100,
    }
    
    return render(request, 'orders/wizard/step6_review.html', context)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def wizard_finalize(request):
    """
    تحويل المسودة إلى طلب نهائي
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # التحقق من اكتمال جميع الخطوات المطلوبة (الخطوة 5 اختيارية)
        required_steps = [1, 2, 3, 4]
        for step in required_steps:
            if step not in draft.completed_steps:
                return JsonResponse({
                    'success': False,
                    'message': f'يجب إكمال الخطوة {step} أولاً'
                }, status=400)
        
        # التحقق من وجود عناصر
        if not draft.items.exists():
            return JsonResponse({
                'success': False,
                'message': 'يجب إضافة عنصر واحد على الأقل'
            }, status=400)
        
        # التحقق من وضع التعديل
        editing_order_id = request.session.get('editing_order_id')
        logger.info(f"Finalize - editing_order_id from session: {editing_order_id}")
        logger.info(f"Finalize - wizard_draft_id from session: {request.session.get('wizard_draft_id')}")
        
        if editing_order_id:
            # وضع التعديل - تحديث الطلب الموجود
            try:
                order = Order.objects.get(pk=editing_order_id)
                
                # تحديث بيانات الطلب
                order.customer = draft.customer
                order.salesperson = draft.salesperson
                order.branch = draft.branch
                order.status = draft.status
                order.notes = draft.notes
                order.selected_types = [draft.selected_type] if draft.selected_type else []
                order.related_inspection = draft.related_inspection
                order.related_inspection_type = draft.related_inspection_type
                order.invoice_number = draft.invoice_number
                order.invoice_number_2 = draft.invoice_number_2
                order.invoice_number_3 = draft.invoice_number_3
                order.contract_number = draft.contract_number
                order.contract_number_2 = draft.contract_number_2
                order.contract_number_3 = draft.contract_number_3
                order.total_amount = draft.subtotal
                order.final_price = draft.final_total
                order.paid_amount = draft.paid_amount
                
                # نقل ملف العقد إذا وجد
                if draft.contract_file:
                    order.contract_file = draft.contract_file
                
                # نقل صورة الفاتورة إذا وجدت
                if draft.invoice_image:
                    order.invoice_image = draft.invoice_image
                
                order.save()
                
                # نقل الصور الإضافية للفاتورة
                from .models import OrderInvoiceImage
                from .wizard_models import DraftOrderInvoiceImage
                
                # حذف الصور القديمة إذا وجدت
                order.invoice_images.all().delete()
                
                # نقل الصور الجديدة
                for draft_img in draft.invoice_images_new.all():
                    OrderInvoiceImage.objects.create(
                        order=order,
                        image=draft_img.image
                    )
                
                # حذف العناصر القديمة
                order.items.all().delete()
                
                # حذف الستائر القديمة
                order.contract_curtains.all().delete()
                
                logger.info(f"Updating existing order {order.order_number}")
                
            except Order.DoesNotExist:
                logger.error(f"Order {editing_order_id} not found, creating new order instead")
                editing_order_id = None  # إنشاء طلب جديد
        
        if not editing_order_id:
            # وضع الإنشاء - إنشاء طلب جديد
            order = Order.objects.create(
                customer=draft.customer,
                salesperson=draft.salesperson,
                branch=draft.branch,
                status=draft.status,
                notes=draft.notes,
                selected_types=[draft.selected_type] if draft.selected_type else [],
                related_inspection=draft.related_inspection,
                related_inspection_type=draft.related_inspection_type,
                invoice_number=draft.invoice_number,
                invoice_number_2=draft.invoice_number_2,
                invoice_number_3=draft.invoice_number_3,
                contract_number=draft.contract_number,
                contract_number_2=draft.contract_number_2,
                contract_number_3=draft.contract_number_3,
                total_amount=draft.subtotal,
                final_price=draft.final_total,
                paid_amount=draft.paid_amount,
                contract_file=draft.contract_file if draft.contract_file else None,  # نقل ملف العقد مباشرة
                invoice_image=draft.invoice_image if draft.invoice_image else None,  # نقل صورة الفاتورة
                created_by=request.user,
                creation_method='wizard',
                source_draft_id=draft.id,
            )
            
            # نقل الصور الإضافية للفاتورة
            from .models import OrderInvoiceImage
            from .wizard_models import DraftOrderInvoiceImage
            
            for draft_img in draft.invoice_images_new.all():
                OrderInvoiceImage.objects.create(
                    order=order,
                    image=draft_img.image
                )
            
            logger.info(f"Created new order {order.order_number}")
        
        # لا حاجة لنقل contract_file هنا - تم نقله في عملية الإنشاء/التحديث
        
        # نقل الستائر من المسودة إلى الطلب النهائي
        curtains = ContractCurtain.objects.filter(draft_order=draft)
        for curtain in curtains:
            curtain.order = order
            curtain.draft_order = None
            curtain.save(update_fields=['order', 'draft_order'])
        
        # نقل العناصر
        for draft_item in draft.items.all():
            OrderItem.objects.create(
                order=order,
                product=draft_item.product,
                quantity=draft_item.quantity,
                unit_price=draft_item.unit_price,
                discount_percentage=draft_item.discount_percentage,
                item_type=draft_item.item_type,
                notes=draft_item.notes,
            )
        
        # إنشاء الدفعة إذا وجد مبلغ مدفوع
        if draft.paid_amount > 0:
            # في وضع التعديل، نحدث الدفعة الموجودة أو ننشئ جديدة
            if editing_order_id:
                # حذف الدفعات القديمة
                order.payments.all().delete()
            
            Payment.objects.create(
                order=order,
                amount=draft.paid_amount,
                payment_method=draft.payment_method,
                reference_number=draft.invoice_number or '',
                notes=draft.payment_notes,
                created_by=request.user,
            )
        
        # تحديد المسودة كمكتملة
        draft.is_completed = True
        draft.completed_at = timezone.now()
        draft.final_order = order
        draft.save()
        
        # مسح معرفات الجلسة للتعديل
        if 'editing_order_id' in request.session:
            del request.session['editing_order_id']
        if 'wizard_draft_id' in request.session:
            del request.session['wizard_draft_id']
        
        # توليد ملف العقد تلقائياً وحفظه
        try:
            from .services.contract_generation_service import ContractGenerationService
            contract_service = ContractGenerationService(order)
            contract_saved = contract_service.save_contract_to_order(user=request.user)
            
            if contract_saved:
                logger.info(f"Contract PDF auto-generated for order {order.order_number}")
            else:
                logger.warning(f"Failed to auto-generate contract PDF for order {order.order_number}")
        except Exception as e:
            logger.error(f"Error auto-generating contract PDF: {e}", exc_info=True)
            # لا نفشل الطلب إذا فشل توليد العقد
        
        return JsonResponse({
            'success': True,
            'message': 'تم حفظ الطلب بنجاح' if editing_order_id else 'تم إنشاء الطلب بنجاح',
            'order_id': order.pk,
            'order_number': order.order_number,
            'redirect_url': f'/orders/order/{order.order_number}/'
        })
    
    except Exception as e:
        logger.error(f"Error finalizing draft order: {e}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def wizard_delete_draft(request, draft_id):
    """
    حذف مسودة معينة - يجب أن يكون المستخدم صاحب المسودة أو له صلاحيات إدارية
    """
    try:
        draft = get_object_or_404(DraftOrder, id=draft_id)
        
        # التحقق من الصلاحيات
        if not (request.user == draft.created_by or 
                request.user.is_superuser or 
                request.user.groups.filter(name__in=['مدير نظام', 'مدير عام']).exists()):
            messages.error(request, 'ليس لديك صلاحية لحذف هذه المسودة')
            return redirect('orders:wizard_drafts_list')
        
        draft.delete()
        messages.success(request, 'تم حذف المسودة بنجاح')
        
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        messages.error(request, f'حدث خطأ أثناء حذف المسودة: {str(e)}')
    
    return redirect('orders:wizard_drafts_list')


@login_required
@require_http_methods(["GET", "POST"])
def wizard_cancel(request):
    """
    إلغاء الويزارد وحذف المسودة
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            messages.info(request, 'لا توجد مسودة نشطة للإلغاء')
            return redirect('orders:order_list')
        
        if request.method == "POST":
            draft.delete()
            messages.success(request, 'تم إلغاء عملية إنشاء الطلب')
            return redirect('orders:order_list')
        else:
            # GET request - show confirmation page
            context = {
                'draft': draft,
                'title': 'تأكيد إلغاء الطلب'
            }
            return render(request, 'orders/wizard/cancel_confirm.html', context)
    
    except Exception as e:
        logger.error(f"Error canceling wizard: {e}")
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('orders:order_list')


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def wizard_add_curtain(request):
    """
    إضافة ستارة جديدة إلى العقد الإلكتروني مع الأقمشة والإكسسوارات
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # الحصول على البيانات
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in wizard_add_curtain: {e}")
            logger.error(f"Request body: {request.body[:500]}")
            return JsonResponse({
                'success': False,
                'message': f'خطأ في تنسيق البيانات: {str(e)}'
            }, status=400)
        
        room_name = data.get('room_name', '').strip()
        width = data.get('width')
        height = data.get('height')
        fabrics_data = data.get('fabrics', [])
        accessories_data = data.get('accessories', [])
        
        # Log received data for debugging
        logger.info(f"Adding curtain - Room: {room_name}, Width: {width}, Height: {height}")
        logger.info(f"Fabrics: {len(fabrics_data)}, Accessories: {len(accessories_data)}")
        logger.info(f"Full data: {json.dumps(data, ensure_ascii=False)[:500]}")
        
        # التحقق من البيانات الأساسية
        if not room_name:
            return JsonResponse({
                'success': False,
                'message': 'يرجى إدخال اسم الغرفة'
            }, status=400)
        
        if not width or not height:
            return JsonResponse({
                'success': False,
                'message': 'يرجى إدخال العرض والارتفاع'
            }, status=400)
        
        try:
            width = Decimal(str(width))
            height = Decimal(str(height))
            
            if width <= 0 or height <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'يجب أن تكون القيم أكبر من صفر'
                }, status=400)
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'message': 'قيم غير صحيحة للعرض أو الارتفاع'
            }, status=400)
        
        # الحصول على آخر sequence
        last_curtain = ContractCurtain.objects.filter(draft_order=draft).order_by('-sequence').first()
        next_sequence = (last_curtain.sequence + 1) if last_curtain else 1
        
        # الحصول على نوع التركيب وبيانات بيت الستارة
        installation_type = data.get('installation_type', '')
        curtain_box_width = data.get('curtain_box_width')
        curtain_box_depth = data.get('curtain_box_depth')
        notes = data.get('notes', '').strip()
        
        # إنشاء الستارة
        curtain = ContractCurtain.objects.create(
            draft_order=draft,
            sequence=next_sequence,
            room_name=room_name,
            width=width,
            height=height,
            installation_type=installation_type,
            curtain_box_width=Decimal(str(curtain_box_width)) if curtain_box_width else None,
            curtain_box_depth=Decimal(str(curtain_box_depth)) if curtain_box_depth else None,
            notes=notes
        )
        
        # إضافة الأقمشة
        for idx, fabric_data in enumerate(fabrics_data):
            try:
                # الحصول على draft_order_item إذا كان موجوداً
                draft_order_item = None
                item_id = fabric_data.get('item_id')
                if item_id:
                    try:
                        draft_order_item = draft.items.get(id=item_id)
                        logger.info(f"Found draft item: {draft_order_item.product.name}")
                    except Exception as e:
                        logger.warning(f"Could not find draft item {item_id}: {e}")
                
                fabric = CurtainFabric(
                    curtain=curtain,
                    draft_order_item=draft_order_item,  # استخدام draft_order_item بدلاً من order_item
                    fabric_type=fabric_data.get('type', 'light'),
                    fabric_name=fabric_data.get('name', ''),
                    pieces=int(fabric_data.get('pieces', 1)),
                    meters=Decimal(str(fabric_data.get('meters', 0))),
                    tailoring_type=fabric_data.get('tailoring', ''),
                    sequence=idx + 1
                )
                
                # التحقق من الصحة قبل الحفظ
                try:
                    fabric.full_clean()
                    fabric.save()
                    logger.info(f"Saved fabric: {fabric.fabric_name} - {fabric.meters}m")
                except ValidationError as ve:
                    # إرجاع رسالة خطأ واضحة للمستخدم
                    logger.error(f"Validation error for fabric: {ve}")
                    error_msgs = []
                    for field, errors in ve.message_dict.items():
                        error_msgs.append(f"{field}: {', '.join(errors)}")
                    return JsonResponse({
                        'success': False,
                        'message': 'خطأ في بيانات القماش: ' + ' | '.join(error_msgs)
                    }, status=400)
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Error adding fabric: {e}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'message': f'خطأ في إضافة القماش: {str(e)}'
                }, status=400)
        
        # إضافة الإكسسوارات
        for accessory_data in accessories_data:
            try:
                # الحصول على draft_order_item إذا كان موجوداً
                draft_order_item = None
                item_id = accessory_data.get('item_id')
                if item_id:
                    try:
                        draft_order_item = draft.items.get(id=item_id)
                        logger.info(f"Found draft item for accessory: {draft_order_item.product.name}")
                    except Exception as e:
                        logger.warning(f"Could not find draft item {item_id}: {e}")
                
                # Get count and size, calculate quantity
                count = int(accessory_data.get('count', 1))
                size = Decimal(str(accessory_data.get('size', 1)))
                quantity = Decimal(str(accessory_data.get('quantity', count * size)))
                
                accessory = CurtainAccessory(
                    curtain=curtain,
                    draft_order_item=draft_order_item,
                    accessory_name=accessory_data.get('name', ''),
                    count=count,
                    size=size,
                    quantity=quantity,
                    color=accessory_data.get('color', '')
                )
                
                # التحقق من الصحة قبل الحفظ
                try:
                    accessory.full_clean()
                    accessory.save()
                    logger.info(f"Saved accessory: {accessory.accessory_name} - count: {count} × size: {size} = quantity: {quantity}")
                except ValidationError as ve:
                    # إرجاع رسالة خطأ واضحة للمستخدم
                    logger.error(f"Validation error for accessory: {ve}")
                    error_msgs = []
                    for field, errors in ve.message_dict.items():
                        error_msgs.append(f"{field}: {', '.join(errors)}")
                    return JsonResponse({
                        'success': False,
                        'message': 'خطأ في بيانات الإكسسوار: ' + ' | '.join(error_msgs)
                    }, status=400)
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Error adding accessory: {e}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'message': f'خطأ في إضافة الإكسسوار: {str(e)}'
                }, status=400)
        
        # تحديث نوع العقد إلى إلكتروني
        draft.contract_type = 'electronic'
        draft.save(update_fields=['contract_type'])
        
        return JsonResponse({
            'success': True,
            'message': 'تم إضافة الستارة بنجاح',
            'curtain': {
                'id': curtain.id,
                'room_name': curtain.room_name,
                'width': float(curtain.width),
                'height': float(curtain.height),
                'fabrics_count': curtain.fabrics.count(),
                'accessories_count': curtain.accessories.count()
            }
        })
    
    except Exception as e:
        logger.error(f"Error adding curtain: {e}", exc_info=True)
        logger.error(f"Request data: {request.body[:500] if request.body else 'No body'}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء حفظ الستارة: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def wizard_edit_curtain(request, curtain_id):
    """
    تعديل ستارة موجودة في العقد الإلكتروني
    GET: جلب بيانات الستارة
    POST: حفظ التعديلات
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # الحصول على الستارة
        curtain = get_object_or_404(
            ContractCurtain,
            id=curtain_id,
            draft_order=draft
        )
        
        if request.method == 'GET':
            # إرجاع بيانات الستارة للتعديل
            fabrics_data = []
            for fabric in curtain.fabrics.all():
                fabrics_data.append({
                    'type': fabric.fabric_type,
                    'type_display': fabric.get_fabric_type_display(),
                    'name': fabric.fabric_name,
                    'item_id': str(fabric.draft_order_item_id) if fabric.draft_order_item_id else None,
                    'meters': float(fabric.meters),
                    'pieces': fabric.pieces,
                    'tailoring': fabric.tailoring_type or '',
                    'tailoring_display': fabric.get_tailoring_type_display() if fabric.tailoring_type else '-'
                })
            
            accessories_data = []
            for accessory in curtain.accessories.all():
                accessories_data.append({
                    'name': accessory.accessory_name,
                    'quantity': float(accessory.quantity),
                    'count': accessory.count,
                    'size': float(accessory.size),
                    'color': accessory.color or '',
                    'item_id': accessory.draft_order_item_id if accessory.draft_order_item else None,
                    'source': 'invoice' if accessory.draft_order_item else 'external'
                })
            
            return JsonResponse({
                'success': True,
                'curtain': {
                    'id': curtain.id,
                    'room_name': curtain.room_name,
                    'width': float(curtain.width),
                    'height': float(curtain.height),
                    'installation_type': curtain.installation_type or '',
                    'curtain_box_width': float(curtain.curtain_box_width) if curtain.curtain_box_width else None,
                    'curtain_box_depth': float(curtain.curtain_box_depth) if curtain.curtain_box_depth else None,
                    'notes': curtain.notes or '',
                    'fabrics': fabrics_data,
                    'accessories': accessories_data
                }
            })
        
        elif request.method == 'POST':
            # حفظ التعديلات
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in wizard_edit_curtain: {e}")
                return JsonResponse({
                    'success': False,
                    'message': f'خطأ في تنسيق البيانات: {str(e)}'
                }, status=400)
            
            room_name = data.get('room_name', '').strip()
            width = data.get('width')
            height = data.get('height')
            fabrics_data = data.get('fabrics', [])
            accessories_data = data.get('accessories', [])
            
            # التحقق من البيانات الأساسية
            if not room_name:
                return JsonResponse({
                    'success': False,
                    'message': 'يرجى إدخال اسم الغرفة'
                }, status=400)
            
            if not width or not height:
                return JsonResponse({
                    'success': False,
                    'message': 'يرجى إدخال العرض والارتفاع'
                }, status=400)
            
            try:
                width = Decimal(str(width))
                height = Decimal(str(height))
                
                if width <= 0 or height <= 0:
                    return JsonResponse({
                        'success': False,
                        'message': 'يجب أن تكون القيم أكبر من صفر'
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'message': 'قيم غير صحيحة للعرض أو الارتفاع'
                }, status=400)
            
            # تحديث بيانات الستارة
            curtain.room_name = room_name
            curtain.width = width
            curtain.height = height
            
            # تحديث نوع التركيب وبيانات بيت الستارة
            installation_type = data.get('installation_type', '')
            curtain_box_width = data.get('curtain_box_width')
            curtain_box_depth = data.get('curtain_box_depth')
            notes = data.get('notes', '').strip()
            
            curtain.installation_type = installation_type
            curtain.curtain_box_width = Decimal(str(curtain_box_width)) if curtain_box_width else None
            curtain.curtain_box_depth = Decimal(str(curtain_box_depth)) if curtain_box_depth else None
            curtain.notes = notes
            
            curtain.save()
            
            # حذف الأقمشة والإكسسوارات القديمة
            curtain.fabrics.all().delete()
            curtain.accessories.all().delete()
            
            # إضافة الأقمشة الجديدة
            for idx, fabric_data in enumerate(fabrics_data):
                try:
                    draft_order_item = None
                    item_id = fabric_data.get('item_id')
                    if item_id:
                        try:
                            draft_order_item = draft.items.get(id=item_id)
                        except Exception as e:
                            logger.warning(f"Could not find draft item {item_id}: {e}")
                    
                    fabric = CurtainFabric(
                        curtain=curtain,
                        draft_order_item=draft_order_item,
                        fabric_type=fabric_data.get('type', 'light'),
                        fabric_name=fabric_data.get('name', ''),
                        pieces=int(fabric_data.get('pieces', 1)),
                        meters=Decimal(str(fabric_data.get('meters', 0))),
                        tailoring_type=fabric_data.get('tailoring', ''),
                        sequence=idx + 1
                    )
                    
                    try:
                        fabric.full_clean()
                        fabric.save()
                    except ValidationError as ve:
                        error_msgs = []
                        for field, errors in ve.message_dict.items():
                            error_msgs.extend(errors)
                        return JsonResponse({
                            'success': False,
                            'message': 'خطأ في الكمية: ' + ', '.join(error_msgs)
                        }, status=400)
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error adding fabric: {e}")
                    return JsonResponse({
                        'success': False,
                        'message': f'خطأ في إضافة القماش: {str(e)}'
                    }, status=400)
            
            # إضافة الإكسسوارات الجديدة
            for accessory_data in accessories_data:
                try:
                    # الحصول على draft_order_item إذا كان موجوداً
                    draft_order_item = None
                    item_id = accessory_data.get('item_id')
                    if item_id:
                        try:
                            draft_order_item = draft.items.get(id=item_id)
                            logger.info(f"Found draft item for accessory: {draft_order_item.product.name}")
                        except Exception as e:
                            logger.warning(f"Could not find draft item {item_id}: {e}")
                    
                    # Get count and size, calculate quantity
                    count = int(accessory_data.get('count', 1))
                    size = Decimal(str(accessory_data.get('size', 1)))
                    quantity = Decimal(str(accessory_data.get('quantity', count * size)))
                    
                    accessory = CurtainAccessory(
                        curtain=curtain,
                        draft_order_item=draft_order_item,
                        accessory_name=accessory_data.get('name', ''),
                        count=count,
                        size=size,
                        quantity=quantity,
                        color=accessory_data.get('color', '')
                    )
                    
                    # التحقق من الصحة قبل الحفظ
                    try:
                        accessory.full_clean()
                        accessory.save()
                        logger.info(f"Saved accessory: {accessory.accessory_name} - count: {count} × size: {size} = quantity: {quantity}")
                    except ValidationError as ve:
                        # إرجاع رسالة خطأ واضحة للمستخدم
                        error_msgs = []
                        for field, errors in ve.message_dict.items():
                            error_msgs.extend(errors)
                        return JsonResponse({
                            'success': False,
                            'message': 'خطأ في كمية الإكسسوار: ' + ', '.join(error_msgs)
                        }, status=400)
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error adding accessory: {e}")
                    return JsonResponse({
                        'success': False,
                        'message': f'خطأ في إضافة الإكسسوار: {str(e)}'
                    }, status=400)
            
            return JsonResponse({
                'success': True,
                'message': 'تم تعديل الستارة بنجاح',
                'curtain': {
                    'id': curtain.id,
                    'room_name': curtain.room_name,
                    'width': float(curtain.width),
                    'height': float(curtain.height),
                    'fabrics_count': curtain.fabrics.count(),
                    'accessories_count': curtain.accessories.count()
                }
            })
    
    except Exception as e:
        logger.error(f"Error editing curtain: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء تعديل الستارة: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def wizard_remove_curtain(request, curtain_id):
    """
    حذف ستارة من العقد الإلكتروني
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # حذف الستارة
        curtain = get_object_or_404(
            ContractCurtain,
            id=curtain_id,
            draft_order=draft
        )
        curtain.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'تم حذف الستارة بنجاح'
        })
    
    except Exception as e:
        logger.error(f"Error removing curtain: {e}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء حذف الستارة: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def wizard_upload_contract(request):
    """
    رفع ملف PDF للعقد
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # التحقق من وجود الملف
        if 'contract_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم رفع أي ملف'
            }, status=400)
        
        contract_file = request.FILES['contract_file']
        
        # التحقق من نوع الملف
        if not contract_file.name.lower().endswith('.pdf'):
            return JsonResponse({
                'success': False,
                'message': 'يجب أن يكون الملف بصيغة PDF'
            }, status=400)
        
        # حفظ الملف
        draft.contract_file = contract_file
        draft.contract_type = 'pdf'
        draft.save(update_fields=['contract_file', 'contract_type'])
        
        return JsonResponse({
            'success': True,
            'message': 'تم رفع ملف العقد بنجاح',
            'file_name': contract_file.name,
            'file_url': draft.contract_file.url if draft.contract_file else None
        })
    
    except Exception as e:
        logger.error(f"Error uploading contract file: {e}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء رفع الملف: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def wizard_remove_contract_file(request):
    """
    حذف ملف العقد المرفوع
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # حذف الملف
        if draft.contract_file:
            draft.contract_file.delete()
        
        draft.contract_type = None
        draft.save(update_fields=['contract_type'])
        
        return JsonResponse({
            'success': True,
            'message': 'تم حذف ملف العقد بنجاح'
        })
    
    except Exception as e:
        logger.error(f"Error removing contract file: {e}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء حذف الملف: {str(e)}'
        }, status=500)


@login_required
def view_contract_template(request, order_id):
    """
    عرض العقد الإلكتروني بتنسيق HTML للطباعة أو التحويل إلى PDF
    View electronic contract in HTML format for printing or PDF conversion
    """
    # الحصول على الطلب
    order = get_object_or_404(Order, id=order_id)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('orders.view_order'):
        if order.created_by != request.user:
            messages.error(request, 'ليس لديك صلاحية لعرض هذا العقد')
            return redirect('orders:order_list')
    
    # الحصول على ستائر العقد
    curtains = ContractCurtain.objects.filter(order=order).prefetch_related(
        'fabrics', 'accessories'
    ).order_by('id')
    
    context = {
        'order': order,
        'curtains': curtains,
        'is_print_view': request.GET.get('print', False)
    }
    
    return render(request, 'orders/contract_template.html', context)


@login_required
def wizard_edit_order(request, order_pk):
    """
    تعديل طلب منشأ عبر الويزارد
    Edit an order created via wizard
    """
    # الحصول على الطلب
    order = get_object_or_404(Order, pk=order_pk)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('orders.change_order'):
        if order.created_by != request.user:
            messages.error(request, 'ليس لديك صلاحية لتعديل هذا الطلب')
            return redirect('orders:order_detail_by_number', order_number=order.order_number)
    
    # التحقق من أن الطلب منشأ عبر الويزارد
    if order.creation_method != 'wizard':
        messages.warning(request, 'هذا الطلب لم ينشأ عبر الويزارد. سيتم توجيهك للتعديل التقليدي.')
        return redirect('orders:order_update', pk=order.pk)
    
    try:
        # إنشاء مسودة جديدة من الطلب الحالي للتعديل
        # لا نستخدم المسودة القديمة لأنها قد تكون تم تعديلها أو حذف بياناتها
        draft = _create_draft_from_order(order, request.user)
        
        # حفظ معرف المسودة في الجلسة
        request.session['wizard_draft_id'] = draft.pk
        request.session['editing_order_id'] = order.pk
        request.session.modified = True  # التأكد من حفظ الجلسة
        
        logger.info(f"Edit mode activated - Order: {order.pk}, Draft: {draft.pk}")
        logger.info(f"Session keys after setting: {list(request.session.keys())}")
        
        # توجيه للخطوة الأولى
        messages.success(request, 'تم تحميل بيانات الطلب. يمكنك الآن تعديلها.')
        return redirect('orders:wizard_step', step=1)
    
    except Exception as e:
        logger.error(f"Error editing order via wizard: {e}")
        messages.error(request, f'حدث خطأ أثناء تحميل بيانات الطلب: {str(e)}')
        return redirect('orders:order_detail_by_number', order_number=order.order_number)


def _create_draft_from_order(order, user):
    """
    إنشاء مسودة من طلب موجود
    Create draft from existing order
    """
    from .contract_models import ContractCurtain, CurtainFabric, CurtainAccessory
    
    # إنشاء المسودة
    draft = DraftOrder.objects.create(
        created_by=user,
        customer=order.customer,
        branch=order.branch,
        salesperson=order.salesperson,
        status=order.status,
        selected_type=order.get_selected_types_list()[0] if order.get_selected_types_list() else None,
        notes=order.notes,
        invoice_number=order.invoice_number,
        invoice_number_2=order.invoice_number_2,
        invoice_number_3=order.invoice_number_3,
        contract_number=order.contract_number,
        contract_number_2=order.contract_number_2,
        contract_number_3=order.contract_number_3,
        contract_file=order.contract_file,
        payment_method='cash',  # افتراضي
        paid_amount=order.paid_amount,
        related_inspection=order.related_inspection,
        related_inspection_type=order.related_inspection_type,
        current_step=1,
        completed_steps=[1, 2, 3, 4]  # تم إكمال الخطوات الأساسية
    )
    
    # نسخ العناصر
    item_mapping = {}  # خريطة لربط العناصر القديمة بالجديدة
    for item in order.items.all():
        new_item = DraftOrderItem.objects.create(
            draft_order=draft,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_percentage=item.discount_percentage,
            item_type=item.item_type,
            notes=item.notes
        )
        item_mapping[item.id] = new_item
    
    # نسخ الستائر والأقمشة والإكسسوارات
    for curtain in order.contract_curtains.all():
        # إنشاء ستارة جديدة مرتبطة بالمسودة
        new_curtain = ContractCurtain.objects.create(
            draft_order=draft,
            order=None,  # مسودة فقط
            room_name=curtain.room_name,
            width=curtain.width,
            height=curtain.height,
            installation_type=curtain.installation_type,
            curtain_box_width=curtain.curtain_box_width,
            curtain_box_depth=curtain.curtain_box_depth,
            notes=curtain.notes,
            sequence=curtain.sequence
        )
        
        # نسخ الأقمشة
        for fabric in curtain.fabrics.all():
            CurtainFabric.objects.create(
                curtain=new_curtain,
                draft_order_item=item_mapping.get(fabric.draft_order_item_id) if fabric.draft_order_item_id else None,
                fabric_type=fabric.fabric_type,
                fabric_name=fabric.fabric_name,
                pieces=fabric.pieces,
                meters=fabric.meters,
                tailoring_type=fabric.tailoring_type,
                sequence=fabric.sequence
            )
        
        # نسخ الإكسسوارات
        for accessory in curtain.accessories.all():
            CurtainAccessory.objects.create(
                curtain=new_curtain,
                draft_order_item=item_mapping.get(accessory.draft_order_item_id) if accessory.draft_order_item_id else None,
                accessory_name=accessory.accessory_name,
                count=accessory.count,
                size=accessory.size,
                quantity=accessory.quantity,
                color=accessory.color
            )
    
    # حساب المجاميع
    draft.calculate_totals()
    
    # ربط المسودة بالطلب
    order.source_draft_id = draft.pk
    order.save(update_fields=['source_draft_id'])
    
    return draft


@login_required
def wizard_edit_options(request, order_pk):
    """
    صفحة خيارات التعديل - يختار المستخدم نوع التعديل المطلوب
    Edit options page - user chooses type of edit needed
    """
    order = get_object_or_404(Order, pk=order_pk)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('orders.change_order'):
        if order.created_by != request.user:
            messages.error(request, 'ليس لديك صلاحية لتعديل هذا الطلب')
            return redirect('orders:order_detail_by_number', order_number=order.order_number)
    
    # التحقق من أن الطلب منشأ عبر الويزارد
    if order.creation_method != 'wizard':
        messages.warning(request, 'هذا الطلب لم ينشأ عبر الويزارد. سيتم توجيهك للتعديل التقليدي.')
        return redirect('orders:order_update', pk=order.pk)
    
    # التحقق من وجود عقد
    has_contract = order.selected_types and any(
        t in ['installation', 'tailoring', 'accessory'] 
        for t in order.selected_types
    )
    
    context = {
        'order': order,
        'has_contract': has_contract,
    }
    
    return render(request, 'orders/wizard/edit_options.html', context)


@login_required
def wizard_edit_type(request, order_pk):
    """
    تعديل نوع الطلب والخدمة - يستخدم أنواع الخدمات من نظام التخصيص
    Edit order type and service - uses service types from customization system
    """
    order = get_object_or_404(Order, pk=order_pk)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('orders.change_order'):
        if order.created_by != request.user:
            messages.error(request, 'ليس لديك صلاحية لتعديل هذا الطلب')
            return redirect('orders:order_detail_by_number', order_number=order.order_number)
    
    # جلب أنواع الخدمات من نظام التخصيص
    from .wizard_customization_models import WizardFieldOption
    service_types = WizardFieldOption.get_active_options('service_type')
    
    if request.method == 'POST':
        old_type = order.selected_types[0] if order.selected_types else None
        new_type = request.POST.get('selected_type')
        
        if new_type and new_type != old_type:
            # الحصول على اسم النوع من نظام التخصيص
            old_option = WizardFieldOption.objects.filter(
                field_type='service_type',
                value=old_type,
                is_active=True
            ).first()
            
            new_option = WizardFieldOption.objects.filter(
                field_type='service_type',
                value=new_type,
                is_active=True
            ).first()
            
            old_display = old_option.display_name if old_option else old_type
            new_display = new_option.display_name if new_option else new_type
            
            # تحديث النوع والخدمة
            order.selected_types = [new_type]
            order.service_types = [new_type]  # تحديث نوع الخدمة أيضاً
            order.save(update_fields=['selected_types', 'service_types'])
            
            logger.info(f"Order type and service changed: {order.order_number} from {old_type} to {new_type}")
            messages.success(request, f'تم تغيير نوع الطلب والخدمة من "{old_display}" إلى "{new_display}" بنجاح')
            
            return redirect('orders:order_detail_by_number', order_number=order.order_number)
    
    context = {
        'order': order,
        'service_types': service_types,
    }
    
    return render(request, 'orders/wizard/edit_type.html', context)


@login_required
def wizard_edit_items(request, order_pk):
    """
    تعديل عناصر الطلب - فتح الويزارد في الخطوة 3
    Edit order items - open wizard at step 3
    """
    order = get_object_or_404(Order, pk=order_pk)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('orders.change_order'):
        if order.created_by != request.user:
            messages.error(request, 'ليس لديك صلاحية لتعديل هذا الطلب')
            return redirect('orders:order_detail_by_number', order_number=order.order_number)
    
    try:
        # إنشاء مسودة من الطلب
        draft = _create_draft_from_order(order, request.user)
        
        # تحديد أن المسودة وصلت للخطوة 3
        draft.mark_step_complete(1)
        draft.mark_step_complete(2)
        draft.current_step = 3
        draft.save()
        
        # حفظ معرفات الجلسة
        request.session['wizard_draft_id'] = draft.pk
        request.session['editing_order_id'] = order.pk
        request.session.modified = True
        
        logger.info(f"Edit items mode - Order: {order.pk}, Draft: {draft.pk}")
        
        # توجيه للخطوة 3
        messages.info(request, 'يمكنك الآن تعديل عناصر الطلب')
        return redirect('orders:wizard_step', step=3)
    
    except Exception as e:
        logger.error(f"Error editing items: {e}")
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('orders:order_detail_by_number', order_number=order.order_number)


@login_required
def wizard_edit_contract(request, order_pk):
    """
    تعديل العقد - فتح الويزارد في الخطوة 5
    Edit contract - open wizard at step 5
    """
    order = get_object_or_404(Order, pk=order_pk)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('orders.change_order'):
        if order.created_by != request.user:
            messages.error(request, 'ليس لديك صلاحية لتعديل هذا الطلب')
            return redirect('orders:order_detail_by_number', order_number=order.order_number)
    
    # التحقق من وجود عقد
    has_contract = order.selected_types and any(
        t in ['installation', 'tailoring', 'accessory'] 
        for t in order.selected_types
    )
    
    if not has_contract:
        messages.error(request, 'هذا الطلب لا يحتوي على عقد')
        return redirect('orders:order_detail_by_number', order_number=order.order_number)
    
    try:
        # إنشاء مسودة من الطلب
        draft = _create_draft_from_order(order, request.user)
        
        # تحديد أن المسودة وصلت للخطوة 5
        draft.mark_step_complete(1)
        draft.mark_step_complete(2)
        draft.mark_step_complete(3)
        draft.mark_step_complete(4)
        draft.current_step = 5
        draft.save()
        
        # حفظ معرفات الجلسة
        request.session['wizard_draft_id'] = draft.pk
        request.session['editing_order_id'] = order.pk
        request.session.modified = True
        
        logger.info(f"Edit contract mode - Order: {order.pk}, Draft: {draft.pk}")
        
        # توجيه للخطوة 5
        messages.info(request, 'يمكنك الآن تعديل تفاصيل العقد')
        return redirect('orders:wizard_step', step=5)
    
    except Exception as e:
        logger.error(f"Error editing contract: {e}")
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('orders:order_detail_by_number', order_number=order.order_number)
