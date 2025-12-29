# ==================== Interactive Migration Views ====================

@login_required
def migrate_phase1(request):
    """المرحلة 1: ترحيل المنتجات فقط"""
    if request.method == 'POST':
        stats = VariantService.phase1_migrate_products()
        
        # حفظ IDs في session للمراحل التالية
        request.session['migration_base_product_ids'] = stats['base_product_ids']
        request.session['migration_phase1_stats'] = {
            'total': stats['total'],
            'migrated': stats['migrated'],
            'skipped': stats['skipped'],
            'errors': len(stats['errors'])
        }
        
        messages.success(
            request,
            f"✅ المرحلة 1 اكتملت: تم ترحيل {stats['migrated']} منتج"
        )
        
        return redirect('inventory:migrate_phase2_confirm')
    
    # GET request - show confirmation
    total_products = Product.objects.count()
    linked_products = ProductVariant.objects.filter(
        legacy_product__isnull=False
    ).count()
    pending = total_products - linked_products
    
    context = {
        'pending_count': pending,
        'title': _('المرحلة 1: ترحيل المنتجات'),
        'active_menu': 'variants',
    }
    
    return render(request, 'inventory/variants/migrate_phase1.html', context)


@login_required
def migrate_phase2_confirm(request):
    """صفحة تأكيد المرحلة 2"""
    phase1_stats = request.session.get('migration_phase1_stats')
    
    if not phase1_stats:
        messages.error(request, 'يجب تنفيذ المرحلة 1 أولاً')
        return redirect('inventory:migrate_phase1')
    
    context = {
        'phase1_stats': phase1_stats,
        'title': _('المرحلة 2: توليد QR'),
        'active_menu': 'variants',
    }
    
    return render(request, 'inventory/variants/migrate_phase2_confirm.html', context)


@login_required
def migrate_phase2(request):
    """المرحلة 2: توليد QR"""
    if request.method != 'POST':
        return redirect('inventory:migrate_phase2_confirm')
    
    base_product_ids = request.session.get('migration_base_product_ids', [])
    
    if not base_product_ids:
        messages.error(request, 'لا توجد منتجات لتوليد QR لها')
        return redirect('inventory:migrate_products')
    
    stats = VariantService.phase2_generate_qr(base_product_ids)
    
    request.session['migration_phase2_stats'] = {
        'total': stats['total'],
        'generated': stats['generated'],
        'failed': stats['failed']
    }
    
    messages.success(
        request,
        f"✅ المرحلة 2 اكتملت: تم توليد {stats['generated']} QR"
    )
    
    return redirect('inventory:migrate_phase3_confirm')


@login_required
def migrate_phase3_confirm(request):
    """صفحة تأكيد المرحلة 3"""
    phase1_stats = request.session.get('migration_phase1_stats')
    phase2_stats = request.session.get('migration_phase2_stats')
    
    if not phase1_stats or not phase2_stats:
        messages.error(request, 'يجب تنفيذ المراحل السابقة أولاً')
        return redirect('inventory:migrate_products')
    
    context = {
        'phase1_stats': phase1_stats,
        'phase2_stats': phase2_stats,
        'title': _('المرحلة 3: مزامنة Cloudflare'),
        'active_menu': 'variants',
    }
    
    return render(request, 'inventory/variants/migrate_phase3_confirm.html', context)


@login_required
def migrate_phase3(request):
    """المرحلة 3: مزامنة Cloudflare"""
    if request.method != 'POST':
        return redirect('inventory:migrate_phase3_confirm')
    
    base_product_ids = request.session.get('migration_base_product_ids', [])
    
    if not base_product_ids:
        messages.error(request, 'لا توجد منتجات للمزامنة')
        return redirect('inventory:migrate_products')
    
    stats = VariantService.phase3_sync_cloudflare(base_product_ids)
    
    request.session['migration_phase3_stats'] = {
        'total': stats['total'],
        'synced': stats['synced'],
        'failed': stats['failed'],
        'skipped': stats['skipped']
    }
    
    # جمع كل الإحصائيات
    all_stats = {
        'phase1': request.session.get('migration_phase1_stats'),
        'phase2': request.session.get('migration_phase2_stats'),
        'phase3': request.session['migration_phase3_stats'],
    }
    
    # تنظيف session
    for key in ['migration_base_product_ids', 'migration_phase1_stats', 
                'migration_phase2_stats', 'migration_phase3_stats']:
        request.session.pop(key, None)
    
    messages.success(
        request,
        f"🎉 اكتملت جميع المراحل! تم مزامنة {stats['synced']} منتج"
    )
    
    context = {
        'all_stats': all_stats,
        'title': _('نتائج الترحيل'),
        'active_menu': 'variants',
    }
    
    return render(request, 'inventory/variants/migrate_complete.html', context)
