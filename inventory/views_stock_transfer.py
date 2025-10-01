"""
Views للتحويل المخزني
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction as db_transaction

from .models import (
    StockTransfer, StockTransferItem, Product, Warehouse,
    StockTransaction
)
from .forms import (
    StockTransferForm, StockTransferItemFormSet,
    StockTransferReceiveForm
)


@login_required
def stock_transfer_list(request):
    """قائمة التحويلات المخزنية"""
    # الفلاتر
    status = request.GET.get('status', '')
    from_warehouse = request.GET.get('from_warehouse', '')
    to_warehouse = request.GET.get('to_warehouse', '')
    search = request.GET.get('search', '')
    
    # الاستعلام الأساسي
    transfers = StockTransfer.objects.select_related(
        'from_warehouse', 'to_warehouse', 'created_by',
        'approved_by', 'completed_by'
    ).prefetch_related('items__product')
    
    # تطبيق الفلاتر
    if status:
        transfers = transfers.filter(status=status)
    if from_warehouse:
        transfers = transfers.filter(from_warehouse_id=from_warehouse)
    if to_warehouse:
        transfers = transfers.filter(to_warehouse_id=to_warehouse)
    if search:
        transfers = transfers.filter(
            Q(transfer_number__icontains=search) |
            Q(notes__icontains=search) |
            Q(reason__icontains=search)
        )
    
    # الترتيب
    transfers = transfers.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transfers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # الإحصائيات
    stats = {
        'total': StockTransfer.objects.count(),
        'draft': StockTransfer.objects.filter(status='draft').count(),
        'pending': StockTransfer.objects.filter(status='pending').count(),
        'approved': StockTransfer.objects.filter(status='approved').count(),
        'in_transit': StockTransfer.objects.filter(status='in_transit').count(),
        'completed': StockTransfer.objects.filter(status='completed').count(),
        'cancelled': StockTransfer.objects.filter(status='cancelled').count(),
    }
    
    # المستودعات للفلاتر
    warehouses = Warehouse.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'warehouses': warehouses,
        'status_choices': StockTransfer.STATUS_CHOICES,
        # الفلاتر الحالية
        'current_status': status,
        'current_from_warehouse': from_warehouse,
        'current_to_warehouse': to_warehouse,
        'current_search': search,
    }
    
    return render(request, 'inventory/stock_transfer_list.html', context)


@login_required
def stock_transfer_create(request):
    """إنشاء تحويل مخزني جديد"""
    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        formset = StockTransferItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with db_transaction.atomic():
                    # حفظ التحويل
                    transfer = form.save(commit=False)
                    transfer.created_by = request.user
                    transfer.status = 'draft'
                    transfer.save()
                    
                    # حفظ العناصر
                    formset.instance = transfer
                    formset.save()
                    
                    messages.success(
                        request,
                        f'تم إنشاء التحويل المخزني {transfer.transfer_number} بنجاح'
                    )
                    return redirect('inventory:stock_transfer_detail', pk=transfer.pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ: {str(e)}')
    else:
        form = StockTransferForm()
        formset = StockTransferItemFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'إنشاء تحويل مخزني جديد',
    }
    
    return render(request, 'inventory/stock_transfer_form.html', context)


@login_required
def stock_transfer_detail(request, pk):
    """تفاصيل التحويل المخزني"""
    transfer = get_object_or_404(
        StockTransfer.objects.select_related(
            'from_warehouse', 'to_warehouse', 'created_by',
            'approved_by', 'completed_by'
        ).prefetch_related('items__product'),
        pk=pk
    )
    
    # حركات المخزون المرتبطة
    stock_transactions = StockTransaction.objects.filter(
        reference=transfer.transfer_number
    ).select_related('product', 'warehouse', 'created_by')
    
    context = {
        'transfer': transfer,
        'stock_transactions': stock_transactions,
    }
    
    return render(request, 'inventory/stock_transfer_detail.html', context)


@login_required
def stock_transfer_edit(request, pk):
    """تعديل التحويل المخزني"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    # يمكن التعديل فقط إذا كان في حالة مسودة
    if transfer.status != 'draft':
        messages.error(request, 'لا يمكن تعديل التحويل بعد تقديمه')
        return redirect('inventory:stock_transfer_detail', pk=pk)
    
    if request.method == 'POST':
        form = StockTransferForm(request.POST, instance=transfer)
        formset = StockTransferItemFormSet(request.POST, instance=transfer)
        
        if form.is_valid() and formset.is_valid():
            try:
                with db_transaction.atomic():
                    form.save()
                    formset.save()
                    
                    messages.success(request, 'تم تحديث التحويل المخزني بنجاح')
                    return redirect('inventory:stock_transfer_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ: {str(e)}')
    else:
        form = StockTransferForm(instance=transfer)
        formset = StockTransferItemFormSet(instance=transfer)
    
    context = {
        'form': form,
        'formset': formset,
        'transfer': transfer,
        'title': f'تعديل التحويل {transfer.transfer_number}',
    }
    
    return render(request, 'inventory/stock_transfer_form.html', context)


@login_required
@require_POST
def stock_transfer_submit(request, pk):
    """تقديم التحويل للموافقة"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if transfer.status != 'draft':
        messages.error(request, 'التحويل تم تقديمه مسبقاً')
        return redirect('inventory:stock_transfer_detail', pk=pk)
    
    if not transfer.items.exists():
        messages.error(request, 'يجب إضافة عناصر للتحويل قبل التقديم')
        return redirect('inventory:stock_transfer_detail', pk=pk)
    
    transfer.status = 'pending'
    transfer.save()
    
    messages.success(request, 'تم تقديم التحويل للموافقة بنجاح')
    return redirect('inventory:stock_transfer_detail', pk=pk)


@login_required
@require_POST
def stock_transfer_approve(request, pk):
    """الموافقة على التحويل"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    try:
        transfer.approve(request.user)
        messages.success(request, 'تمت الموافقة على التحويل بنجاح')
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
    
    return redirect('inventory:stock_transfer_detail', pk=pk)


@login_required
def stock_transfer_receive(request, pk):
    """استلام التحويل"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    
    if not transfer.can_complete:
        messages.error(request, 'لا يمكن استلام هذا التحويل')
        return redirect('inventory:stock_transfer_detail', pk=pk)
    
    if request.method == 'POST':
        form = StockTransferReceiveForm(request.POST, transfer=transfer)
        
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    # تحديث الكميات المستلمة
                    for item in transfer.items.all():
                        field_name = f'item_{item.id}_received'
                        notes_field_name = f'item_{item.id}_notes'
                        
                        received_qty = form.cleaned_data.get(field_name, item.quantity)
                        notes = form.cleaned_data.get(notes_field_name, '')
                        
                        item.received_quantity = received_qty
                        if notes:
                            item.notes = f"{item.notes}\n{notes}" if item.notes else notes
                        item.save()
                    
                    # إكمال التحويل
                    transfer.complete(request.user)
                    
                    messages.success(request, 'تم استلام التحويل بنجاح')
                    return redirect('inventory:stock_transfer_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ: {str(e)}')
    else:
        form = StockTransferReceiveForm(transfer=transfer)
    
    context = {
        'transfer': transfer,
        'form': form,
    }
    
    return render(request, 'inventory/stock_transfer_receive.html', context)


@login_required
@require_POST
def stock_transfer_cancel(request, pk):
    """إلغاء التحويل"""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    reason = request.POST.get('reason', '')
    
    try:
        transfer.cancel(request.user, reason)
        messages.success(request, 'تم إلغاء التحويل بنجاح')
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
    
    return redirect('inventory:stock_transfer_detail', pk=pk)


@login_required
@require_POST
def stock_transfer_delete(request, pk):
    """حذف التحويل"""
    transfer = get_object_or_404(StockTransfer, pk=pk)

    # يمكن الحذف فقط إذا كان في حالة مسودة
    if transfer.status != 'draft':
        messages.error(request, 'لا يمكن حذف التحويل بعد تقديمه')
        return redirect('inventory:stock_transfer_detail', pk=pk)

    transfer_number = transfer.transfer_number
    transfer.delete()

    messages.success(request, f'تم حذف التحويل {transfer_number} بنجاح')
    return redirect('inventory:stock_transfer_list')


@login_required
@require_GET
def get_product_stock(request):
    """API للحصول على مخزون المنتج في مستودع معين"""
    product_id = request.GET.get('product_id')
    warehouse_id = request.GET.get('warehouse_id')

    if not product_id or not warehouse_id:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        product = Product.objects.get(pk=product_id)
        warehouse = Warehouse.objects.get(pk=warehouse_id)

        # الحصول على آخر حركة مخزون
        last_transaction = StockTransaction.objects.filter(
            product=product,
            warehouse=warehouse
        ).order_by('-transaction_date').first()

        current_stock = last_transaction.running_balance if last_transaction else 0

        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'product_name': product.name,
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
            'current_stock': float(current_stock),
            'unit': product.unit
        })
    except (Product.DoesNotExist, Warehouse.DoesNotExist):
        return JsonResponse({'error': 'Product or Warehouse not found'}, status=404)


@login_required
@require_GET
def get_similar_products(request):
    """API للحصول على الأصناف المشابهة لمنتج معين"""
    product_id = request.GET.get('product_id')

    if not product_id:
        return JsonResponse({'error': 'Missing product_id'}, status=400)

    try:
        product = Product.objects.get(pk=product_id)

        # البحث عن المنتجات المشابهة بالاسم (نفس الاسم الأساسي مع اختلاف اللون مثلاً)
        # نفترض أن الأسماء المشابهة تحتوي على نفس الكلمات الأساسية
        base_name = product.name.split('-')[0].strip() if '-' in product.name else product.name

        similar_products = Product.objects.filter(
            Q(name__icontains=base_name) | Q(category=product.category)
        ).exclude(id=product.id).values('id', 'name', 'code')[:10]

        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'product_name': product.name,
            'similar_products': list(similar_products)
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
@require_GET
def get_pending_transfers_for_warehouse(request):
    """API للحصول على التحويلات المعلقة لمستودع معين"""
    warehouse_id = request.GET.get('warehouse_id')

    if not warehouse_id:
        # إذا لم يتم تحديد مستودع، نحاول الحصول على مستودعات المستخدم
        # يمكن تحسين هذا لاحقاً بناءً على صلاحيات المستخدم
        return JsonResponse({'error': 'Missing warehouse_id'}, status=400)

    try:
        warehouse = Warehouse.objects.get(pk=warehouse_id)

        # التحويلات الواردة المعلقة
        pending_transfers = StockTransfer.objects.filter(
            to_warehouse=warehouse,
            status__in=['approved', 'in_transit']
        ).select_related('from_warehouse').values(
            'id', 'transfer_number', 'from_warehouse__name',
            'status', 'transfer_date', 'expected_arrival_date'
        ).order_by('-created_at')[:10]

        return JsonResponse({
            'success': True,
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
            'pending_count': pending_transfers.count(),
            'transfers': list(pending_transfers)
        })
    except Warehouse.DoesNotExist:
        return JsonResponse({'error': 'Warehouse not found'}, status=404)

