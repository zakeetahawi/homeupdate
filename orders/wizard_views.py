"""
Views للويزارد متعدد الخطوات لإنشاء الطلبات
Multi-Step Order Creation Wizard Views
⚡ Performance Optimized - December 2024
"""
import json
import logging
from decimal import Decimal
from django.db import transaction, models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.core.cache import cache

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
from accounts.models import SystemSettings
from django.contrib.auth import get_user_model

User = get_user_model()

# ⚡ استيراد تحسينات الأداء
from .performance_optimizations import (
    get_user_drafts_optimized,
    get_draft_with_relations,
    get_curtains_with_details,
    get_cached_system_settings,
    invalidate_draft_cache,
)

logger = logging.getLogger(__name__)


def get_currency_context():
    """
    ⚡ الحصول على سياق العملة من إعدادات النظام (cached)
    """
    settings = get_cached_system_settings()
    return {
        'currency_code': settings.get('currency', 'EGP'),
        'currency_symbol': settings.get('currency_symbol', 'ج.م'),
    }


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
    ⚡ بداية الويزارد - عرض المسودات المحفوظة أو إنشاء مسودة جديدة
    مع التحقق من الحد الأقصى للمسودات (OPTIMIZED)
    """
    # ⚡ الحصول على إعدادات النظام من Cache
    settings = get_cached_system_settings()
    max_drafts = settings.get('max_draft_orders_per_user', 5)
    
    # ⚡ البحث عن المسودات غير المكتملة للمستخدم - محسّن
    user_drafts = get_user_drafts_optimized(request.user, is_completed=False, limit=max_drafts)
    
    # التحقق من وجود درافت للعميل المحدد (إن وجد)
    customer_id = request.GET.get('customer_id')
    if customer_id:
        customer_draft = user_drafts.filter(customer_id=customer_id).first()
        if customer_draft:
            # إذا وجد درافت لهذا العميل، توجيه مباشر لإكماله
            request.session['wizard_draft_id'] = customer_draft.id
            messages.info(request, f'لديك مسودة طلب غير مكتملة لهذا العميل. سيتم إكمالها.')
            return redirect('orders:wizard_step', step=customer_draft.current_step)
    
    # إذا كان هناك مسودات، توجيه إلى قائمة المسودات
    if user_drafts.exists():
        return redirect('orders:wizard_drafts_list')
    else:
        # البحث عن العميل إذا تم تمريره - محسّن
        from customers.models import Customer
        customer = None
        customer_id = request.GET.get('customer_id')
        customer_code = request.GET.get('customer')
        
        if customer_id:
            customer = Customer.objects.select_related('branch').filter(pk=customer_id).first()
        elif customer_code:
            customer = Customer.objects.select_related('branch').filter(code=customer_code).first()
        
        # تحديد الفرع تلقائياً بناءً على المستخدم
        user_branch = None
        if hasattr(request.user, 'branch') and request.user.branch:
            user_branch = request.user.branch
        
        # إنشاء مسودة جديدة مباشرة مع العميل والفرع
        draft = DraftOrder.objects.create(
            created_by=request.user,
            current_step=1,
            customer=customer,
            branch=user_branch
        )
        request.session['wizard_draft_id'] = draft.id
        return redirect('orders:wizard_step', step=1)


@login_required
def wizard_start_new(request):
    """
    إنشاء مسودة جديدة مباشرة (تجاوز المسودات الموجودة)
    يمكن تمرير معرف العميل أو كود العميل كمعامل
    مع التحقق من الحد الأقصى للمسودات
    """
    from customers.models import Customer
    # ⚡ الحصول على إعدادات النظام من Cache
    settings = get_cached_system_settings()
    max_drafts = settings.get('max_draft_orders_per_user', 5)
    
    # التحقق من وجود مسودات غير مكتملة للمستخدم - محسّن
    existing_drafts = DraftOrder.objects.filter(
        created_by=request.user,
        is_completed=False
    ).select_related('customer', 'branch').only(
        'id', 'current_step', 'customer__id', 'customer__name', 'branch__id'
    )
    
    customer = None
    customer_code = request.GET.get('customer')
    customer_id = request.GET.get('customer_id')
    
    # البحث عن العميل بالكود أو المعرف - محسّن
    if customer_code:
        customer = Customer.objects.select_related('branch').filter(code=customer_code).first()
    elif customer_id:
        customer = Customer.objects.select_related('branch').filter(pk=customer_id).first()
    
    # التحقق من وجود درافت لنفس العميل
    if customer:
        customer_draft = existing_drafts.filter(customer=customer).first()
        if customer_draft:
            # إذا وجد درافت لهذا العميل، توجيه مباشر لإكماله
            request.session['wizard_draft_id'] = customer_draft.id
            messages.info(request, f'لديك مسودة طلب غير مكتملة للعميل "{customer.name}". سيتم إكمالها.')
            return redirect('orders:wizard_step', step=customer_draft.current_step)
    
    # التحقق من عدد المسودات الحالية
    current_drafts_count = existing_drafts.count()
    
    if current_drafts_count >= max_drafts:
        messages.error(request, f'لقد وصلت للحد الأقصى المسموح من المسودات ({max_drafts}). يرجى إكمال أو حذف بعض المسودات أولاً.')
        return redirect('orders:wizard_drafts_list')
    
    # إذا كان هناك مسودات وطلب التأكيد غير موجود
    if existing_drafts.exists() and not request.GET.get('confirm_new'):
        # تخزين معاملات الطلب الأصلية في الجلسة
        request.session['pending_new_order_params'] = {
            'customer': request.GET.get('customer'),
            'customer_id': request.GET.get('customer_id')
        }
        return redirect('orders:wizard_confirm_new')
    
    # تحديد الفرع تلقائياً بناءً على المستخدم
    user_branch = None
    if hasattr(request.user, 'branch') and request.user.branch:
        user_branch = request.user.branch
    
    # إنشاء المسودة مع العميل والفرع إذا وُجدا
    draft = DraftOrder.objects.create(
        created_by=request.user,
        current_step=1,
        customer=customer,
        branch=user_branch
    )
    
    # تخزين معرف المسودة في الجلسة
    request.session['wizard_draft_id'] = draft.id
    
    return redirect('orders:wizard_step', step=1)


@login_required
def wizard_confirm_new(request):
    """
    صفحة تأكيد إنشاء مسودة جديدة عند وجود مسودات غير مكتملة
    """
    # ⚡ الحصول على إعدادات النظام من Cache
    settings = get_cached_system_settings()
    max_drafts = settings.get('max_draft_orders_per_user', 5)
    
    existing_drafts = DraftOrder.objects.filter(
        created_by=request.user,
        is_completed=False
    ).select_related('customer', 'branch').order_by('-updated_at')
    
    current_drafts_count = existing_drafts.count()
    can_create_new = current_drafts_count < max_drafts
    
    context = {
        'existing_drafts': existing_drafts,
        'pending_params': request.session.get('pending_new_order_params', {}),
        'max_drafts': max_drafts,
        'current_drafts_count': current_drafts_count,
        'can_create_new': can_create_new,
        'remaining_drafts': max_drafts - current_drafts_count
    }
    
    return render(request, 'orders/wizard/confirm_new.html', context)


@login_required
def wizard_delete_and_create_new(request):
    """
    حذف جميع المسودات غير المكتملة وإنشاء مسودة جديدة
    """
    # حذف المسودات غير المكتملة
    DraftOrder.objects.filter(
        created_by=request.user,
        is_completed=False
    ).delete()
    
    # استرجاع معاملات الطلب الأصلية
    pending_params = request.session.pop('pending_new_order_params', {})
    
    # إعادة التوجيه لإنشاء مسودة جديدة مع التأكيد
    url = reverse('orders:wizard_start_new') + '?confirm_new=1'
    if pending_params.get('customer'):
        url += f"&customer={pending_params['customer']}"
    elif pending_params.get('customer_id'):
        url += f"&customer_id={pending_params['customer_id']}"
    
    return redirect(url)


@login_required
def wizard_drafts_list(request):
    """
    عرض قائمة المسودات المحفوظة بناءً على صلاحيات المستخدم
    مع عرض معلومات الحد الأقصى للمسودات
    """
    # ⚡ الحصول على إعدادات النظام من Cache
    settings = get_cached_system_settings()
    max_drafts = settings.get('max_draft_orders_per_user', 5)
    
    # تحديد الاستعلام بناءً على صلاحيات المستخدم
    if request.user.is_superuser or request.user.groups.filter(name='مدير نظام').exists():
        # مدير النظام - عرض جميع المسودات
        drafts = DraftOrder.objects.filter(is_completed=False).select_related('created_by', 'customer', 'branch')
    elif request.user.groups.filter(name='مدير عام').exists() or (hasattr(request.user, 'is_sales_manager') and request.user.is_sales_manager):
        # مدير عام - عرض جميع المسودات
        drafts = DraftOrder.objects.filter(is_completed=False).select_related('created_by', 'customer', 'branch')
    elif request.user.groups.filter(name='مدير منطقة').exists() or (hasattr(request.user, 'is_region_manager') and request.user.is_region_manager):
        # مدير منطقة - عرض مسودات الفروع المُدارة
        managed_branches = request.user.managed_branches.all() if hasattr(request.user, 'managed_branches') else []
        if managed_branches:
            # عرض المسودات من الفروع المُدارة + المسودات التي أنشأها المستخدمون المُدارون
            from django.db.models import Q
            # الحصول على المستخدمين الذين يمكن إدارتهم
            manageable_users = []
            for branch in managed_branches:
                # إضافة جميع المستخدمين في الفرع
                branch_users = User.objects.filter(branch=branch)
                manageable_users.extend(list(branch_users))
            
            # إضافة مسودات المستخدم الحالي أيضاً
            drafts = DraftOrder.objects.filter(
                Q(branch__in=managed_branches) | 
                Q(created_by__in=manageable_users) |
                Q(created_by=request.user),
                is_completed=False
            ).select_related('created_by', 'customer', 'branch').distinct()
        else:
            # إذا لم يكن له فروع مُدارة، عرض مسوداته فقط
            drafts = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).select_related('customer', 'branch')
    elif hasattr(request.user, 'is_branch_manager') and request.user.is_branch_manager:
        # مدير فرع - عرض مسودات فرعه + المستخدمين في فرعه
        if hasattr(request.user, 'branch') and request.user.branch:
            from django.db.models import Q
            branch_users = User.objects.filter(branch=request.user.branch)
            drafts = DraftOrder.objects.filter(
                Q(branch=request.user.branch) | 
                Q(created_by__in=branch_users) |
                Q(created_by=request.user),
                is_completed=False
            ).select_related('created_by', 'customer', 'branch').distinct()
        else:
            # إذا لم يكن له فرع، عرض مسوداته فقط
            drafts = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).select_related('customer', 'branch')
    else:
        # المستخدم العادي - عرض مسوداته فقط
        drafts = DraftOrder.objects.filter(
            created_by=request.user,
            is_completed=False
        ).select_related('customer', 'branch')
    
    drafts = drafts.order_by('-updated_at')
    
    # حساب عدد مسودات المستخدم الحالي للتحقق من الحد الأقصى
    user_drafts_count = DraftOrder.objects.filter(
        created_by=request.user,
        is_completed=False
    ).count()
    
    can_create_new = user_drafts_count < max_drafts
    remaining_drafts = max_drafts - user_drafts_count
    
    context = {
        'drafts': drafts,
        'title': 'قائمة المسودات المحفوظة',
        'max_drafts': max_drafts,
        'current_drafts_count': user_drafts_count,
        'can_create_new': can_create_new,
        'remaining_drafts': remaining_drafts
    }
    
    return render(request, 'orders/wizard/drafts_list.html', context)


@login_required
@ensure_csrf_cookie
def wizard_step(request, step):
    """
    عرض خطوة معينة من الويزارد
    ensure_csrf_cookie يضمن إرسال CSRF cookie مع الاستجابة
    
    ملاحظة مهمة: يجب أن يكون هناك draft_id في الجلسة للوصول للخطوات
    المسودة تُنشأ فقط عند البدء الفعلي من wizard_start
    """
    # التحقق من وجود معرف المسودة في الجلسة
    draft_id = request.session.get('wizard_draft_id')
    
    if not draft_id:
        # لا يوجد draft_id - توجيه للصفحة الرئيسية
        messages.warning(request, 'يرجى البدء بإنشاء طلب جديد أو اختيار مسودة موجودة')
        return redirect('orders:wizard_start')
    
    # الحصول على المسودة
    try:
        draft = DraftOrder.objects.select_related(
            'created_by',
            'last_modified_by',
            'customer',
            'branch'
        ).get(pk=draft_id)
        
        # التحقق من الصلاحيات
        if draft.created_by != request.user:
            # التحقق من أن المستخدم لديه صلاحيات أعلى
            if not request.user.can_manage_user(draft.created_by):
                messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه المسودة')
                del request.session['wizard_draft_id']
                if 'editing_order_id' in request.session:
                    del request.session['editing_order_id']
                return redirect('orders:wizard_start')
            # المستخدم لديه صلاحيات أعلى - السماح بالمتابعة بدون تغيير created_by
            messages.info(request, f'تقوم بمتابعة مسودة {draft.created_by.get_full_name() or draft.created_by.username}')
            
    except DraftOrder.DoesNotExist:
        # المسودة غير موجودة، حذف من الجلسة
        del request.session['wizard_draft_id']
        if 'editing_order_id' in request.session:
            del request.session['editing_order_id']
        messages.error(request, 'المسودة غير موجودة')
        return redirect('orders:wizard_start')
    
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
        # حفظ القيم القديمة للمقارنة
        old_customer = draft.customer
        old_branch = draft.branch
        old_salesperson = draft.salesperson
        
        form = Step1BasicInfoForm(request.POST, instance=draft, user=request.user)
        if form.is_valid():
            draft = form.save(commit=False)
            
            # تسجيل التعديلات إذا كان المستخدم مختلف عن المنشئ
            if draft.created_by != request.user:
                changes = []
                if old_customer != draft.customer:
                    changes.append(f'تغيير العميل من {old_customer.name if old_customer else "غير محدد"} إلى {draft.customer.name if draft.customer else "غير محدد"}')
                if old_branch != draft.branch:
                    changes.append(f'تغيير الفرع من {old_branch.name if old_branch else "غير محدد"} إلى {draft.branch.name if draft.branch else "غير محدد"}')
                if old_salesperson != draft.salesperson:
                    changes.append(f'تغيير البائع')
                
                if changes:
                    draft.log_edit(
                        user=request.user,
                        action='update_basic_info',
                        details='تعديل البيانات الأساسية: ' + '، '.join(changes)
                    )
            
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
    
    # الحصول على العميل المحدد لاستخدامه في Select2
    selected_customer = None
    if draft.customer:
        selected_customer = {
            'id': draft.customer.id,
            'name': draft.customer.name,
            'phone': draft.customer.phone or '',
        }
    
    context = {
        'draft': draft,
        'form': form,
        'current_step': 1,
        'total_steps': total_steps,
        'step_title': 'البيانات الأساسية',
        'progress_percentage': round((1 / total_steps) * 100, 2),
        'editing_mode': editing_mode,
        'editing_order': editing_order,
        'selected_customer': selected_customer,
    }
    
    return render(request, 'orders/wizard/step1_basic_info.html', context)


def wizard_step_2_order_type(request, draft):
    """
    الخطوة 2: نوع الطلب
    """
    if request.method == 'POST':
        old_selected_type = draft.selected_type
        
        form = Step2OrderTypeForm(request.POST, instance=draft, customer=draft.customer)
        if form.is_valid():
            draft = form.save()
            
            # تسجيل التعديلات
            if draft.created_by != request.user and old_selected_type != draft.selected_type:
                type_names = {
                    'accessory': 'إكسسوار',
                    'installation': 'تركيب',
                    'inspection': 'معاينة',
                    'tailoring': 'تسليم',
                    'products': 'منتجات'
                }
                old_name = type_names.get(old_selected_type, old_selected_type) if old_selected_type else 'غير محدد'
                new_name = type_names.get(draft.selected_type, draft.selected_type) if draft.selected_type else 'غير محدد'
                
                draft.log_edit(
                    user=request.user,
                    action='update_order_type',
                    details=f'تغيير نوع الطلب من {old_name} إلى {new_name}'
                )
            
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
    ⚡ الخطوة 3: عناصر الطلب (OPTIMIZED)
    """
    # ⚡ استخدام select_related لتجنب N+1 queries - مع حقول التتبع
    items = draft.items.select_related(
        'product', 
        'product__category',
        'added_by',
        'modified_by'
    ).all()
    
    total_steps = get_total_steps(draft)
    currency = get_currency_context()
    
    # ⚡ Cache التفاصيل المحسوبة
    cache_key = f'draft_totals_{draft.id}'
    totals = cache.get(cache_key)
    if totals is None:
        totals = draft.calculate_totals()
        cache.set(cache_key, totals, 300)  # 5 دقائق
    
    context = {
        'draft': draft,
        'items': items,
        'current_step': 3,
        'total_steps': total_steps,
        'step_title': 'عناصر الطلب',
        'progress_percentage': round((3 / total_steps) * 100, 2),
        'totals': totals,
        'currency_symbol': currency['currency_symbol'],
        'currency_code': currency['currency_code'],
    }
    
    return render(request, 'orders/wizard/step3_order_items.html', context)


def ajax_login_required(view_func):
    """
    Decorator للتحقق من تسجيل الدخول لطلبات AJAX
    يُرجع JSON بدلاً من إعادة توجيه لصفحة تسجيل الدخول
    """
    from functools import wraps
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'يجب تسجيل الدخول أولاً',
                'redirect': '/accounts/login/'
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@ajax_login_required
@require_http_methods(["POST"])
def wizard_add_item(request):
    """
    إضافة عنصر لمسودة الطلب (AJAX)
    """
    try:
        data = json.loads(request.body)
        
        logger.info(f"wizard_add_item: Received data: {data}")
        logger.info(f"wizard_add_item: User: {request.user}")
        logger.info(f"wizard_add_item: Session key: {request.session.session_key if hasattr(request, 'session') else 'No session'}")
        
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id') if hasattr(request, 'session') else None
        logger.info(f"wizard_add_item: Draft ID from session: {draft_id}")
        
        if draft_id:
            # البحث عن المسودة بدون فحص created_by (للسماح للمديرين بالتعديل)
            draft = DraftOrder.objects.filter(pk=draft_id).first()
            logger.info(f"wizard_add_item: Draft from session ID: {draft}")
        else:
            draft = DraftOrder.objects.filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
            logger.info(f"wizard_add_item: Draft from query: {draft}")
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # الحصول على المنتج
        product_id = data.get('product_id')
        if not product_id:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم تحديد المنتج'
            }, status=400)
        
        product = get_object_or_404(Product, pk=product_id)
        
        # التحقق من السعر
        unit_price = data.get('unit_price')
        if unit_price is None or unit_price == '':
            unit_price = product.price if product.price else Decimal('0.00')
        else:
            unit_price = Decimal(str(unit_price))
        
        # التحقق من الكمية
        quantity = data.get('quantity', 1)
        if quantity is None or quantity == '':
            quantity = Decimal('1')
        else:
            quantity = Decimal(str(quantity))
        
        # التحقق من نسبة الخصم
        discount_percentage = data.get('discount_percentage', 0)
        if discount_percentage is None or discount_percentage == '':
            discount_percentage = Decimal('0.00')
        else:
            discount_percentage = Decimal(str(discount_percentage))
        
        # حساب مبلغ الخصم
        total_price = quantity * unit_price
        discount_amount = total_price * (discount_percentage / Decimal('100.0'))
        
        # إنشاء العنصر
        item = DraftOrderItem.objects.create(
            draft_order=draft,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            discount_percentage=discount_percentage,
            discount_amount=discount_amount,  # إضافة مبلغ الخصم المحسوب
            item_type=data.get('item_type', 'product') or 'product',
            notes=data.get('notes', '') or '',
            added_by=request.user  # تسجيل من أضاف العنصر
        )
        
        logger.info(f"wizard_add_item: Item created successfully: {item.id}")
        
        # تسجيل التعديل في سجل المسودة
        if draft.created_by != request.user:
            draft.log_edit(
                user=request.user,
                action='add_item',
                details=f'أضاف عنصر: {product.name} (الكمية: {quantity})'
            )
        
        # ⚡ إبطال الذاكرة المؤقتة للمجاميع
        invalidate_draft_cache(draft.id)
        cache.delete(f'draft_totals_{draft.id}')
        
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
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in wizard_add_item: {e}")
        return JsonResponse({
            'success': False,
            'message': 'بيانات غير صالحة'
        }, status=400)
    
    except Exception as e:
        import traceback
        logger.error(f"Error adding item to draft: {e}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@ajax_login_required
@require_http_methods(["POST"])
def wizard_remove_item(request, item_id):
    """
    حذف عنصر من مسودة الطلب (AJAX)
    """
    try:
        # التحقق من وجود مسودة محددة في الجلسة (للتعديل)
        draft_id = request.session.get('wizard_draft_id') if hasattr(request, 'session') else None
        
        if draft_id:
            # البحث عن المسودة بدون فحص created_by (للسماح للمديرين بالتعديل)
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
        product_name = item.product.name
        
        # تسجيل التعديل في سجل المسودة
        if draft.created_by != request.user:
            draft.log_edit(
                user=request.user,
                action='remove_item',
                details=f'حذف عنصر: {product_name}'
            )
        
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
        old_invoice_number = draft.invoice_number
        old_paid_amount = draft.paid_amount
        old_payment_method = draft.payment_method
        
        form = Step4InvoicePaymentForm(
            request.POST,
            request.FILES,
            instance=draft,
            draft_order=draft,
            request=request  # تمرير request للتحقق من وضع التعديل
        )
        if form.is_valid():
            draft = form.save()
            
            # تسجيل التعديلات
            if draft.created_by != request.user:
                changes = []
                if old_invoice_number != draft.invoice_number:
                    changes.append(f'تغيير رقم الفاتورة من {old_invoice_number or "غير محدد"} إلى {draft.invoice_number or "غير محدد"}')
                if old_paid_amount != draft.paid_amount:
                    changes.append(f'تغيير المبلغ المدفوع من {old_paid_amount} إلى {draft.paid_amount}')
                if old_payment_method != draft.payment_method:
                    changes.append(f'تغيير طريقة الدفع')
                
                if changes:
                    draft.log_edit(
                        user=request.user,
                        action='update_payment_invoice',
                        details='تعديل الدفع والفاتورة: ' + '، '.join(changes)
                    )
            
            # معالجة الصور الإضافية
            from .wizard_models import DraftOrderInvoiceImage
            for key in request.FILES:
                if key.startswith('additional_invoice_image_'):
                    image = request.FILES[key]
                    DraftOrderInvoiceImage.objects.create(
                        draft_order=draft,
                        image=image
                    )
                    
                    # تسجيل إضافة صورة
                    if draft.created_by != request.user:
                        draft.log_edit(
                            user=request.user,
                            action='add_invoice_image',
                            details='إضافة صورة فاتورة'
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
        form = Step4InvoicePaymentForm(instance=draft, draft_order=draft, request=request)
    
    # حساب المجاميع
    totals = draft.calculate_totals()
    
    # إضافة الحد الأدنى للدفع (50%)
    from decimal import Decimal
    final_total = totals.get('final_total', Decimal('0'))
    if isinstance(final_total, float):
        final_total = Decimal(str(final_total))
    totals['minimum_payment'] = (final_total * Decimal('0.5')).quantize(Decimal('0.01'))
    
    total_steps = get_total_steps(draft)
    currency = get_currency_context()
    
    # التحقق من وجود صور محفوظة
    has_saved_images = bool(draft.invoice_image) or draft.invoice_images_new.exists()
    
    context = {
        'draft': draft,
        'form': form,
        'current_step': 4,
        'total_steps': total_steps,
        'step_title': 'تفاصيل المرجع والدفع',
        'progress_percentage': round((4 / total_steps) * 100, 2),
        'totals': totals,
        'currency_symbol': currency['currency_symbol'],
        'currency_code': currency['currency_code'],
        'has_saved_images': has_saved_images,
        'is_editing': bool(request.session.get('editing_order_id')),
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


@login_required
@require_http_methods(["POST"])
def delete_main_draft_invoice_image(request):
    """حذف صورة الفاتورة الرئيسية من المسودة"""
    try:
        draft_id = request.session.get('wizard_draft_id')
        if not draft_id:
            return JsonResponse({'success': False, 'error': 'لا توجد مسودة نشطة'}, status=404)
        
        draft = DraftOrder.objects.get(pk=draft_id)
        
        # التحقق من الصلاحيات
        if draft.created_by != request.user:
            return JsonResponse({'success': False, 'error': 'غير مصرح لك بحذف هذه الصورة'}, status=403)
        
        # حذف الصورة
        if draft.invoice_image:
            draft.invoice_image.delete()
            draft.invoice_image = None
            draft.save(update_fields=['invoice_image'])
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'لا توجد صورة رئيسية لحذفها'}, status=404)
            
    except DraftOrder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'المسودة غير موجودة'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def wizard_step_5_contract(request, draft):
    """
    ⚡ الخطوة 5: العقد الإلكتروني أو PDF (OPTIMIZED)
    """
    # معالجة POST - تحديد الخطوة كمكتملة
    if request.method == 'POST':
        # تحديد الخطوة كمكتملة
        draft.mark_step_complete(5)
        draft.current_step = 6
        draft.save()
        
        # ⚡ إبطال الذاكرة المؤقتة
        invalidate_draft_cache(draft.id)
        
        # الرد برسالة نجاح
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'تم حفظ بيانات العقد'
            })
        else:
            # إعادة توجيه إلى الخطوة التالية
            return redirect('orders:wizard_step', step=6)
    
    # ⚡ الحصول على الستائر المرتبطة بالمسودة - استخدام الدالة المحسّنة
    curtains = get_curtains_with_details(draft=draft)
    
    # ⚡ الحصول على عناصر الفاتورة (الأقمشة فقط) - محسّن
    order_items = draft.items.filter(
        item_type__in=['fabric', 'product']
    ).select_related('product')
    
    # حساب الكميات المتاحة لكل عنصر - محسّن: استعلام واحد بدلاً من N+1
    # جلب مجاميع الأقمشة والإكسسوارات دفعة واحدة
    fabric_usage = dict(CurtainFabric.objects.filter(
        curtain__draft_order=draft,
        draft_order_item__isnull=False
    ).values('draft_order_item_id').annotate(
        total=models.Sum('meters')
    ).values_list('draft_order_item_id', 'total'))
    
    accessory_usage = dict(CurtainAccessory.objects.filter(
        curtain__draft_order=draft,
        draft_order_item__isnull=False
    ).values('draft_order_item_id').annotate(
        total=models.Sum('quantity')
    ).values_list('draft_order_item_id', 'total'))
    
    items_with_usage = []
    for item in order_items:
        used_fabrics = fabric_usage.get(item.id, Decimal('0')) or Decimal('0')
        used_accessories = accessory_usage.get(item.id, Decimal('0')) or Decimal('0')
        used = used_fabrics + used_accessories
        
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
    currency = get_currency_context()
    
    # تحديد ما إذا كان نوع الطلب إكسسوار فقط (يتخطى قسم الأقمشة)
    is_accessory_only = draft.selected_type == 'accessory'
    
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
        'currency_symbol': currency['currency_symbol'],
        'currency_code': currency['currency_code'],
        'is_accessory_only': is_accessory_only,
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
    currency = get_currency_context()
    
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
        'currency_symbol': currency['currency_symbol'],
        'currency_code': currency['currency_code'],
    }
    
    return render(request, 'orders/wizard/step6_review.html', context)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def wizard_finalize(request):
    """
    ⚡ تحويل المسودة إلى طلب نهائي - محسّن للسرعة القصوى
    """
    try:
        # ⚡ استعلام واحد محسّن مع جميع العلاقات
        draft_id = request.session.get('wizard_draft_id')
        
        if draft_id:
            draft = DraftOrder.objects.select_related(
                'customer', 'salesperson', 'branch', 'related_inspection'
            ).prefetch_related('items__product', 'invoice_images_new').filter(pk=draft_id).first()
        else:
            draft = DraftOrder.objects.select_related(
                'customer', 'salesperson', 'branch', 'related_inspection'
            ).prefetch_related('items__product', 'invoice_images_new').filter(
                created_by=request.user,
                is_completed=False
            ).order_by('-updated_at').first()
        
        if not draft:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم العثور على مسودة نشطة'
            }, status=404)
        
        # ⚡ تحقق سريع من الخطوات (بدون حلقة)
        required_steps = {1, 2, 3, 4}
        completed = set(draft.completed_steps) if draft.completed_steps else set()
        if not required_steps.issubset(completed):
            missing = required_steps - completed
            return JsonResponse({
                'success': False,
                'message': f'يجب إكمال الخطوات: {", ".join(map(str, sorted(missing)))}'
            }, status=400)
        
        # ⚡ التحقق السريع من وجود عناصر (استعلام محسّن)
        draft_items_list = list(draft.items.all())  # تم تحميلها مسبقاً من prefetch_related
        if not draft_items_list:
            return JsonResponse({
                'success': False,
                'message': 'يجب إضافة عنصر واحد على الأقل'
            }, status=400)
        
        # التحقق من وضع التعديل
        editing_order_id = request.session.get('editing_order_id')
        
        if editing_order_id:
            # وضع التعديل - تحديث الطلب الموجود
            try:
                order = Order.objects.get(pk=editing_order_id)
                
                # ⚡ تحديث الحقول مباشرة
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
                order.financial_addition = Decimal('0.00')
                order.used_customer_balance = Decimal('0.00')
                
                # تحديث الملفات إذا لزم الأمر
                if draft.contract_file:
                    order.contract_file = draft.contract_file
                if draft.invoice_image:
                    order.invoice_image = draft.invoice_image
                
                # حفظ بدون update_fields لإطلاق signals
                order.save()
                
                # ⚡ حذف مجمّع
                from .models import OrderInvoiceImage
                OrderInvoiceImage.objects.filter(order=order).delete()
                order.items.all().delete()
                order.contract_curtains.all().delete()
                order.payments.all().delete()
                
                # نقل الصور الجديدة
                if draft.invoice_images_new.exists():
                    new_images = [
                        OrderInvoiceImage(order=order, image=img.image)
                        for img in draft.invoice_images_new.all()
                    ]
                    OrderInvoiceImage.objects.bulk_create(new_images, batch_size=50)
                
            except Order.DoesNotExist:
                editing_order_id = None  # إنشاء طلب جديد
        
        if not editing_order_id:
            # ⚡ وضع الإنشاء - إنشاء طلب جديد بأقل عمليات ممكنة
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
                financial_addition=Decimal('0.00'),
                used_customer_balance=Decimal('0.00'),
                contract_file=draft.contract_file,
                invoice_image=draft.invoice_image,
                created_by=request.user,
                creation_method='wizard',
                source_draft_id=draft.id,
            )
            
            # ⚡ نقل الصور مجمّعاً
            from .models import OrderInvoiceImage
            if draft.invoice_images_new.exists():
                new_images = [
                    OrderInvoiceImage(order=order, image=img.image)
                    for img in draft.invoice_images_new.all()
                ]
                OrderInvoiceImage.objects.bulk_create(new_images, batch_size=50)
        
        # ⚡ نقل الستائر - bulk_update محسّن
        curtains = list(ContractCurtain.objects.filter(draft_order=draft))
        if curtains:
            for c in curtains:
                c.order = order
                c.draft_order = None
            ContractCurtain.objects.bulk_update(curtains, ['order', 'draft_order'], batch_size=200)
        
        # ⚡ نقل العناصر - bulk_create محسّن (استخدام القائمة المحملة مسبقاً)
        order_items_to_create = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percentage=item.discount_percentage,
                discount_amount=item.discount_amount if item.discount_amount else Decimal('0.00'),
                item_type=item.item_type,
                notes=item.notes,
            )
            for item in draft_items_list
        ]
        OrderItem.objects.bulk_create(order_items_to_create, batch_size=200)
        
        # ⚡ إنشاء الدفعة
        if draft.paid_amount > 0:
            Payment.objects.create(
                order=order,
                amount=draft.paid_amount,
                payment_method=draft.payment_method,
                reference_number=draft.invoice_number or '',
                notes=draft.payment_notes,
                created_by=request.user,
            )
        
        # ⚡ تحديث المسودة - update بدلاً من save
        DraftOrder.objects.filter(pk=draft.pk).update(
            is_completed=True,
            completed_at=timezone.now(),
            final_order=order
        )
        
        # مسح الجلسة
        request.session.pop('editing_order_id', None)
        request.session.pop('wizard_draft_id', None)
        
        # ⚡ توليد العقد في الخلفية - بعد اكتمال الـ transaction
        selected_type = draft.selected_type
        should_generate_contract = selected_type not in ['products', 'inspection']
        
        if should_generate_contract and not draft.contract_file:
            # استخدام on_commit لضمان اكتمال حفظ الطلب قبل توليد العقد
            order_pk = order.pk
            user_pk = request.user.pk
            
            def trigger_contract_generation():
                try:
                    from .tasks import generate_contract_pdf_async
                    task = generate_contract_pdf_async.delay(order_pk, user_pk)
                    logger.info(f"⚡ Contract generation started (task: {task.id}) after commit")
                except Exception as e:
                    logger.warning(f"⚠️ Contract task failed: {e}")
            
            transaction.on_commit(trigger_contract_generation)
        
        return JsonResponse({
            'success': True,
            'message': 'تم إنشاء الطلب بنجاح' if not editing_order_id else 'تم حفظ الطلب بنجاح',
            'order_id': order.pk,
            'order_number': order.order_number,
            'redirect_url': f'/orders/order/{order.order_number}/'
        })
    
    except Exception as e:
        logger.error(f"Error finalizing draft order: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@login_required
def wizard_continue_draft(request, draft_id):
    """
    متابعة مسودة معينة - مع دعم المستخدمين ذوي الصلاحيات الأعلى
    """
    try:
        draft = get_object_or_404(DraftOrder, id=draft_id, is_completed=False)
        
        # التحقق من الصلاحيات
        if draft.created_by != request.user:
            # التحقق من أن المستخدم لديه صلاحيات أعلى
            if not request.user.can_manage_user(draft.created_by):
                messages.error(request, 'ليس لديك صلاحية للوصول إلى هذه المسودة')
                return redirect('orders:wizard_drafts_list')
            # المستخدم لديه صلاحيات أعلى - السماح بالمتابعة
            messages.info(request, f'تقوم بمتابعة مسودة {draft.created_by.get_full_name() or draft.created_by.username}')
        
        # تخزين معرف المسودة في الجلسة
        request.session['wizard_draft_id'] = draft.id
        
        # التوجيه للخطوة الحالية
        return redirect('orders:wizard_step', step=draft.current_step)
        
    except Exception as e:
        logger.error(f"Error continuing draft: {e}")
        messages.error(request, f'حدث خطأ أثناء متابعة المسودة: {str(e)}')
        return redirect('orders:wizard_drafts_list')


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
    إلغاء الويزارد - حذف المسودة فقط إذا كانت ملك المستخدم الحالي
    إذا كانت المسودة تابعة لمستخدم آخر، يتم الخروج فقط دون حذف
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
            # التحقق من صاحب المسودة
            if draft.created_by == request.user:
                # المسودة تابعة للمستخدم الحالي - يمكن حذفها
                draft.delete()
                messages.success(request, 'تم إلغاء عملية إنشاء الطلب وحذف المسودة')
            else:
                # المسودة تابعة لمستخدم آخر - الخروج فقط دون حذف
                messages.info(request, f'تم الخروج من المسودة (المسودة تابعة لـ {draft.created_by.get_full_name()})')
            
            # مسح معرف المسودة من الجلسة
            if 'wizard_draft_id' in request.session:
                del request.session['wizard_draft_id']
            
            return redirect('orders:order_list')
        else:
            # GET request - show confirmation page
            is_owner = draft.created_by == request.user
            context = {
                'draft': draft,
                'is_owner': is_owner,
                'title': 'تأكيد إلغاء الطلب' if is_owner else 'تأكيد الخروج من المسودة'
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
            curtain_box_width=Decimal(str(round(float(curtain_box_width), 3))) if curtain_box_width else None,
            curtain_box_depth=Decimal(str(round(float(curtain_box_depth), 3))) if curtain_box_depth else None,
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
                    meters=Decimal(str(round(float(fabric_data.get('meters', 0)), 3))),  # تقريب لتجنب مشاكل دقة الفاصلة العائمة
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
                # size قد يكون None للمنتجات بالقطعة
                size_val = accessory_data.get('size')
                if size_val and size_val != '' and size_val != 'null' and size_val != 'None':
                    try:
                        # تقريب القيمة إلى 3 منازل عشرية لتجنب مشاكل دقة الفاصلة العائمة
                        size = Decimal(str(round(float(size_val), 3)))
                    except:
                        size = Decimal('0')
                else:
                    size = Decimal('0')  # بالقطعة
                
                # quantity = count فقط للمنتجات بالقطعة، أو count * size للمتر
                quantity_val = accessory_data.get('quantity')
                if quantity_val and quantity_val != '' and quantity_val != 'null' and quantity_val != 'None':
                    try:
                        # تقريب القيمة إلى 3 منازل عشرية لتجنب مشاكل دقة الفاصلة العائمة
                        quantity = Decimal(str(round(float(quantity_val), 3)))
                    except:
                        quantity = Decimal(str(count))
                else:
                    if size > 0:
                        quantity = Decimal(str(count)) * size
                    else:
                        quantity = Decimal(str(count))
                
                accessory = CurtainAccessory(
                    curtain=curtain,
                    draft_order_item=draft_order_item,
                    accessory_name=accessory_data.get('name', ''),
                    accessory_type=accessory_data.get('display_type', ''),
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
                # محاولة الحصول على item_id من draft_order_item أو البحث بالاسم
                item_id = None
                if fabric.draft_order_item_id:
                    item_id = str(fabric.draft_order_item_id)
                elif fabric.fabric_name:
                    # البحث عن العنصر بالاسم في المسودة
                    matching_item = draft.items.filter(product__name=fabric.fabric_name).first()
                    if matching_item:
                        item_id = str(matching_item.id)
                        # تحديث الربط في قاعدة البيانات
                        fabric.draft_order_item = matching_item
                        fabric.save(update_fields=['draft_order_item'])
                
                # تحديد إذا كان حزام
                is_belt = 'حزام' in fabric.fabric_name if fabric.fabric_name else False
                
                fabrics_data.append({
                    'type': fabric.fabric_type,
                    'type_display': fabric.get_fabric_type_display(),
                    'name': fabric.fabric_name,
                    'item_id': item_id,
                    'meters': float(fabric.meters),
                    'pieces': fabric.pieces,
                    'tailoring': fabric.tailoring_type or '',
                    'tailoring_display': fabric.get_tailoring_type_display() if fabric.tailoring_type else '-',
                    'source': 'belt' if is_belt else ('invoice' if item_id else 'external'),
                    'unit': 'piece' if is_belt else 'meter'
                })
            
            accessories_data = []
            for accessory in curtain.accessories.all():
                # محاولة الحصول على item_id من draft_order_item أو البحث بالاسم
                item_id = None
                source = 'external'
                if accessory.draft_order_item_id:
                    item_id = str(accessory.draft_order_item_id)
                    source = 'invoice'
                elif accessory.accessory_name:
                    # البحث عن العنصر بالاسم في المسودة
                    matching_item = draft.items.filter(product__name=accessory.accessory_name).first()
                    if matching_item:
                        item_id = str(matching_item.id)
                        source = 'invoice'
                        # تحديث الربط في قاعدة البيانات
                        accessory.draft_order_item = matching_item
                        accessory.save(update_fields=['draft_order_item'])
                
                accessories_data.append({
                    'name': accessory.accessory_name,
                    'display_type': accessory.accessory_type or '',  # نوع الإكسسوار الشائع
                    'quantity': float(accessory.quantity),
                    'count': accessory.count,
                    'size': float(accessory.size) if accessory.size else 0,
                    'color': accessory.color or '',
                    'item_id': item_id,
                    'source': source
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
                width = Decimal(str(round(float(width), 3)))  # تقريب لتجنب مشاكل دقة الفاصلة العائمة
                height = Decimal(str(round(float(height), 3)))  # تقريب لتجنب مشاكل دقة الفاصلة العائمة
                
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
            curtain.curtain_box_width = Decimal(str(round(float(curtain_box_width), 3))) if curtain_box_width else None
            curtain.curtain_box_depth = Decimal(str(round(float(curtain_box_depth), 3))) if curtain_box_depth else None
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
                        meters=Decimal(str(round(float(fabric_data.get('meters', 0)), 3))),  # تقريب لتجنب مشاكل دقة الفاصلة العائمة
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
                    count_val = accessory_data.get('count', 1)
                    size_val = accessory_data.get('size')
                    quantity_val = accessory_data.get('quantity')
                    
                    # تحويل القيم بشكل آمن
                    count = int(count_val) if count_val else 1
                    
                    # size قد يكون None أو 0 للمنتجات بالقطعة
                    if size_val and size_val != '' and size_val != 'null' and size_val != 'None':
                        try:
                            # تقريب القيمة إلى 3 منازل عشرية لتجنب مشاكل دقة الفاصلة العائمة
                            size = Decimal(str(round(float(size_val), 3)))
                        except:
                            size = Decimal('0')
                    else:
                        size = Decimal('0')  # بالقطعة
                    
                    # quantity = count فقط للمنتجات بالقطعة، أو count * size للمتر
                    if quantity_val and quantity_val != '' and quantity_val != 'null' and quantity_val != 'None':
                        try:
                            # تقريب القيمة إلى 3 منازل عشرية لتجنب مشاكل دقة الفاصلة العائمة
                            quantity = Decimal(str(round(float(quantity_val), 3)))
                        except:
                            quantity = Decimal(str(count))
                    else:
                        if size > 0:
                            quantity = Decimal(str(count)) * size
                        else:
                            quantity = Decimal(str(count))
                    
                    accessory = CurtainAccessory(
                        curtain=curtain,
                        draft_order_item=draft_order_item,
                        accessory_name=accessory_data.get('name', ''),
                        accessory_type=accessory_data.get('display_type', ''),  # نوع الإكسسوار الشائع
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
    
    # منع البائع من تعديل الطلبات
    if request.user.is_salesperson and not request.user.is_superuser:
        messages.error(request, '❌ عذراً، البائع لا يمكنه تعديل الطلبات بعد إنشائها')
        return redirect('orders:order_detail', pk=order_pk)
    
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
        invoice_image=order.invoice_image,  # نسخ صورة الفاتورة
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
    
    # منع البائع من تعديل الطلبات
    if request.user.is_salesperson and not request.user.is_superuser:
        messages.error(request, '❌ عذراً، البائع لا يمكنه تعديل الطلبات بعد إنشائها')
        return redirect('orders:order_detail', pk=order_pk)
    
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
    
    # ⚡ الحصول على سياق العملة من Cache
    currency_context = get_currency_context()
    
    context = {
        'order': order,
        'has_contract': has_contract,
        **currency_context,
    }
    
    return render(request, 'orders/wizard/edit_options.html', context)


@login_required
def wizard_edit_type(request, order_pk):
    """
    تعديل نوع الطلب والخدمة - يستخدم أنواع الخدمات من نظام التخصيص
    Edit order type and service - uses service types from customization system
    """
    order = get_object_or_404(Order, pk=order_pk)
    
    # منع البائع من تعديل الطلبات
    if request.user.is_salesperson and not request.user.is_superuser:
        messages.error(request, '❌ عذراً، البائع لا يمكنه تعديل الطلبات بعد إنشائها')
        return redirect('orders:order_detail', pk=order_pk)
    
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
    
    # منع البائع من تعديل الطلبات
    if request.user.is_salesperson and not request.user.is_superuser:
        messages.error(request, '❌ عذراً، البائع لا يمكنه تعديل الطلبات بعد إنشائها')
        return redirect('orders:order_detail', pk=order_pk)
    
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
    
    # منع البائع من تعديل الطلبات
    if request.user.is_salesperson and not request.user.is_superuser:
        messages.error(request, '❌ عذراً، البائع لا يمكنه تعديل الطلبات بعد إنشائها')
        return redirect('orders:order_detail', pk=order_pk)
    
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
