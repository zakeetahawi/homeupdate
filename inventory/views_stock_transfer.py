"""
Views للتحويل المخزني
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Max
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

    # التحقق من صلاحيات المستخدم
    user_managed_warehouses = Warehouse.objects.filter(
        manager=request.user,
        is_active=True
    )

    is_warehouse_manager = (
        user_managed_warehouses.exists() or
        request.user.groups.filter(name__in=['مسؤول مخازن', 'Warehouse Manager', 'مسؤول مستودع']).exists() or
        request.user.is_staff or
        request.user.is_superuser
    )

    # الاستعلام الأساسي
    transfers = StockTransfer.objects.select_related(
        'from_warehouse', 'to_warehouse', 'created_by',
        'approved_by', 'completed_by'
    ).prefetch_related('items__product')

    # تصفية حسب صلاحيات المستخدم
    if not request.user.is_superuser:
        if user_managed_warehouses.exists():
            # عرض التحويلات من أو إلى المستودعات التي يديرها المستخدم
            transfers = transfers.filter(
                Q(from_warehouse__in=user_managed_warehouses) |
                Q(to_warehouse__in=user_managed_warehouses)
            )
        elif not is_warehouse_manager:
            # إذا لم يكن مدير مستودع، لا يرى أي تحويلات
            transfers = transfers.none()

    # تطبيق الفلاتر
    if status:
        # دعم فلترة متعددة للحالات (مثل: status=approved,in_transit)
        if ',' in status:
            status_list = status.split(',')
            transfers = transfers.filter(status__in=status_list)
        else:
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

    # الإحصائيات (حسب صلاحيات المستخدم)
    base_query = StockTransfer.objects.all()
    if not request.user.is_superuser:
        if user_managed_warehouses.exists():
            base_query = base_query.filter(
                Q(from_warehouse__in=user_managed_warehouses) |
                Q(to_warehouse__in=user_managed_warehouses)
            )
        elif not is_warehouse_manager:
            base_query = base_query.none()

    stats = {
        'total': base_query.count(),
        'draft': base_query.filter(status='draft').count(),
        'pending': base_query.filter(status='pending').count(),
        'approved': base_query.filter(status='approved').count(),
        'in_transit': base_query.filter(status='in_transit').count(),
        'completed': base_query.filter(status='completed').count(),
        'cancelled': base_query.filter(status='cancelled').count(),
    }

    # المستودعات للفلاتر (فقط المستودعات التي يديرها المستخدم أو الكل للـ superuser)
    if request.user.is_superuser:
        warehouses = Warehouse.objects.filter(is_active=True)
    elif user_managed_warehouses.exists():
        warehouses = user_managed_warehouses
    else:
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
        'is_warehouse_manager': is_warehouse_manager,
        'user_managed_warehouses': user_managed_warehouses,
    }

    return render(request, 'inventory/stock_transfer_list.html', context)


@login_required
def stock_transfer_bulk(request):
    """صفحة التحويلات المخزنية"""
    user = request.user

    # تحديد المستودعات المتاحة حسب صلاحيات المستخدم
    if user.is_superuser:
        # المدير يرى جميع المستودعات
        warehouses = Warehouse.objects.filter(is_active=True).order_by('name')
    elif hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff:
        # موظف المستودع يرى مستودعه فقط كمصدر
        if user.assigned_warehouse:
            warehouses = Warehouse.objects.filter(is_active=True).order_by('name')
        else:
            warehouses = Warehouse.objects.none()
    else:
        # باقي المستخدمين يرون جميع المستودعات
        warehouses = Warehouse.objects.filter(is_active=True).order_by('name')

    context = {
        'warehouses': warehouses,
        'title': 'تحويلات مخزنية',
        'user_warehouse': user.assigned_warehouse if hasattr(user, 'assigned_warehouse') else None,
        'is_warehouse_staff': hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff,
    }

    return render(request, 'inventory/stock_transfer_bulk.html', context)


@login_required
@require_POST
def stock_transfer_bulk_create(request):
    """إنشاء تحويل جماعي"""
    import json

    try:
        data = json.loads(request.body)
        from_warehouse_id = data.get('from_warehouse')
        to_warehouse_id = data.get('to_warehouse')
        reason = data.get('reason', '')
        notes = data.get('notes', '')
        products = data.get('products', [])

        if not from_warehouse_id or not to_warehouse_id:
            return JsonResponse({
                'success': False,
                'error': 'يجب تحديد المستودع المصدر والمستهدف'
            }, status=400)

        if not products:
            return JsonResponse({
                'success': False,
                'error': 'يجب اختيار منتج واحد على الأقل'
            }, status=400)

        from_warehouse = Warehouse.objects.get(pk=from_warehouse_id)
        to_warehouse = Warehouse.objects.get(pk=to_warehouse_id)

        if from_warehouse == to_warehouse:
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن التحويل من وإلى نفس المستودع'
            }, status=400)

        # ✅ التحقق من صلاحيات موظف المستودع
        user = request.user
        if hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff:
            # موظف المستودع يمكنه فقط إنشاء تحويل من مستودعه المخصص
            if not user.assigned_warehouse:
                return JsonResponse({
                    'success': False,
                    'error': 'لا يوجد مستودع مخصص لك'
                }, status=403)

            if from_warehouse.id != user.assigned_warehouse.id:
                return JsonResponse({
                    'success': False,
                    'error': f'لا يمكنك إنشاء تحويل إلا من مستودعك المخصص ({user.assigned_warehouse.name})'
                }, status=403)

        with db_transaction.atomic():
            # إنشاء التحويل
            transfer = StockTransfer.objects.create(
                from_warehouse=from_warehouse,
                to_warehouse=to_warehouse,
                transfer_date=timezone.now(),
                reason=reason,
                notes=notes,
                created_by=request.user,
                status='pending'  # ✅ تغيير من draft إلى pending
            )

            # إضافة المنتجات
            for product_data in products:
                product = Product.objects.get(pk=product_data['id'])
                StockTransferItem.objects.create(
                    transfer=transfer,
                    product=product,
                    quantity=product_data['stock'],  # نقل الكل
                    notes=f"نقل كامل: {product_data['stock']} {product_data['unit']}"
                )

            # ✅ الموافقة التلقائية على التحويل
            transfer.approve(request.user)

            return JsonResponse({
                'success': True,
                'transfer_id': transfer.id,
                'transfer_number': transfer.transfer_number,
                'redirect_url': f"/inventory/stock-transfer/{transfer.id}/"
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# تم حذف stock_transfer_create القديم - الآن نستخدم stock_transfer_bulk


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

    # ✅ التحقق من صلاحيات الاستلام
    user = request.user
    can_receive = False

    if transfer.can_complete:
        # المدير يمكنه الاستلام دائماً
        if user.is_superuser:
            can_receive = True
        # منع منشئ التحويل من الاستلام
        elif transfer.created_by != user:
            # موظف المستودع يمكنه الاستلام فقط إذا كان التحويل إلى مستودعه
            if hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff:
                if user.assigned_warehouse and transfer.to_warehouse.id == user.assigned_warehouse.id:
                    can_receive = True
            else:
                # المستخدمون الآخرون يمكنهم الاستلام
                can_receive = True

    context = {
        'transfer': transfer,
        'stock_transactions': stock_transactions,
        'can_receive': can_receive,
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

    # ✅ التحقق من صلاحيات الاستلام
    user = request.user

    # 1. منع منشئ التحويل من استلامه
    if transfer.created_by == user:
        messages.error(request, 'لا يمكنك استلام تحويل قمت بإنشائه بنفسك')
        return redirect('inventory:stock_transfer_detail', pk=pk)

    # 2. موظف المستودع يمكنه فقط استلام تحويل إلى مستودعه المخصص
    if hasattr(user, 'is_warehouse_staff') and user.is_warehouse_staff and not user.is_superuser:
        if not user.assigned_warehouse:
            messages.error(request, 'لا يوجد مستودع مخصص لك')
            return redirect('inventory:stock_transfer_detail', pk=pk)

        if transfer.to_warehouse.id != user.assigned_warehouse.id:
            messages.error(
                request,
                f'لا يمكنك استلام هذا التحويل. يمكنك فقط استلام التحويلات الموجهة إلى مستودعك ({user.assigned_warehouse.name})'
            )
            return redirect('inventory:stock_transfer_detail', pk=pk)
    
    if request.method == 'POST':
        print(f"\n{'='*80}")
        print(f"📥 استلام POST request للتحويل {transfer.transfer_number}")
        print(f"{'='*80}")
        print(f"POST data: {request.POST}")

        form = StockTransferReceiveForm(request.POST, transfer=transfer)

        print(f"\n✅ Form created")
        print(f"Form is valid: {form.is_valid()}")

        if not form.is_valid():
            print(f"❌ Form errors: {form.errors}")

        if form.is_valid():
            print(f"✅ Form is valid, processing...")
            try:
                with db_transaction.atomic():
                    # تحديث الكميات المستلمة
                    for item in transfer.items.all():
                        field_name = f'item_{item.id}_received'
                        notes_field_name = f'item_{item.id}_notes'

                        received_qty = form.cleaned_data.get(field_name, item.quantity)
                        notes = form.cleaned_data.get(notes_field_name, '')

                        print(f"  - {item.product.name}: {received_qty} (ملاحظات: {notes})")

                        item.received_quantity = received_qty
                        if notes:
                            item.notes = f"{item.notes}\n{notes}" if item.notes else notes
                        item.save()

                    # إكمال التحويل
                    print(f"\n🔄 إكمال التحويل...")
                    transfer.complete(request.user)

                    print(f"✅ تم الاستلام بنجاح!")
                    messages.success(request, 'تم استلام التحويل بنجاح')
                    return redirect('inventory:stock_transfer_detail', pk=pk)
            except Exception as e:
                print(f"❌ خطأ: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'حدث خطأ: {str(e)}')
        else:
            print(f"❌ Form is not valid, showing errors to user")
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
def get_warehouse_products(request):
    """API للحصول على منتجات مستودع معين مع المخزون - مع دعم البحث"""
    warehouse_id = request.GET.get('warehouse_id')
    search_query = request.GET.get('search', '').strip()

    if not warehouse_id:
        return JsonResponse({'error': 'Missing warehouse_id'}, status=400)

    try:
        warehouse = Warehouse.objects.get(pk=warehouse_id)

        # الحصول على جميع المنتجات التي لها مخزون في هذا المستودع
        products_with_stock = []

        # الحصول على آخر حركة لكل منتج في المستودع
        latest_transactions = StockTransaction.objects.filter(
            warehouse=warehouse
        ).values('product').annotate(
            last_date=Max('transaction_date')
        ).order_by('product')

        for trans in latest_transactions:
            try:
                last_trans = StockTransaction.objects.filter(
                    warehouse=warehouse,
                    product_id=trans['product'],
                    transaction_date=trans['last_date']
                ).order_by('-id').first()

                if last_trans and last_trans.running_balance > 0:
                    product = last_trans.product

                    # تطبيق البحث إذا كان موجوداً
                    if search_query:
                        # البحث في الاسم أو الكود
                        if (search_query.lower() not in product.name.lower() and
                            (not product.code or search_query.lower() not in product.code.lower())):
                            continue

                    products_with_stock.append({
                        'id': product.id,
                        'name': product.name,
                        'code': product.code or '',
                        'stock': float(last_trans.running_balance),
                        'unit': product.unit,
                        'display': f"{product.name} - {last_trans.running_balance} {product.unit}"
                    })
            except Exception as e:
                # تجاهل الأخطاء في المنتجات الفردية
                print(f"خطأ في معالجة المنتج {trans.get('product')}: {e}")
                continue

        # ترتيب حسب الاسم
        products_with_stock.sort(key=lambda x: x['name'])

        # تحديد النتائج إلى 50 منتج فقط لتحسين الأداء
        if len(products_with_stock) > 50:
            products_with_stock = products_with_stock[:50]

        return JsonResponse({
            'success': True,
            'warehouse_id': warehouse.id,
            'warehouse_name': warehouse.name,
            'products': products_with_stock,
            'count': len(products_with_stock),
            'search_query': search_query
        })
    except Warehouse.DoesNotExist:
        return JsonResponse({'error': 'Warehouse not found'}, status=404)
    except Exception as e:
        import traceback
        print(f"خطأ في get_warehouse_products: {e}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)


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

