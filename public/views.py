from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.http import JsonResponse, HttpResponse
from inventory.models import Product
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
from django.conf import settings


def get_base_url():
    """Get the base URL for QR codes"""
    return getattr(settings, 'SITE_URL', 'https://www.elkhawaga.uk')


def generate_qr_base64(url):
    """Generate QR code as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


@never_cache
def product_qr_view(request, product_code):
    """
    Public product page - accessible without login
    Shows product details in an elegant card
    Hides stock/meter quantities
    """
    product = get_object_or_404(Product, code=product_code)
    
    # Get category name
    category_name = product.category.name if product.category else 'غير محدد'
    
    # Get currency display
    currency_display = dict(Product.CURRENCY_CHOICES).get(product.currency, product.currency)
    
    # Get unit display
    unit_display = dict(Product.UNIT_CHOICES).get(product.unit, product.unit)
    
    # Generate QR code for sharing
    qr_url = f"{get_base_url()}/p/{product.code}/"
    qr_base64 = generate_qr_base64(qr_url)
    
    context = {
        'product': product,
        'category_name': category_name,
        'currency_display': currency_display,
        'unit_display': unit_display,
        'qr_code': qr_base64,
        'share_url': qr_url,
        'site_name': 'الخواجة',
        'site_url': get_base_url(),
    }
    
    return render(request, 'public/product_card.html', context)


def generate_product_qr(request, product_code):
    """
    Generate QR code image for a product
    Returns PNG image
    """
    product = get_object_or_404(Product, code=product_code)
    
    qr_url = f"{get_base_url()}/p/{product.code}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="qr_{product.code}.png"'
    return response


@never_cache
def qr_export_page(request):
    """
    QR Code export page for printing
    Shows all products QR codes in A4 layout (3 per row)
    Uses cached QR codes from database for fast loading
    """
    # Get filter parameters
    category_id = request.GET.get('category')
    search = request.GET.get('search', '').strip()
    page = request.GET.get('page', '1')
    
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    # Get products with cached QR codes
    products = Product.objects.select_related('category').only(
        'id', 'name', 'code', 'price', 'currency', 'qr_code_base64',
        'category__id', 'category__name'
    ).exclude(code__isnull=True).exclude(code='').order_by('name')
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if search:
        from django.db.models import Q
        products = products.filter(Q(name__icontains=search) | Q(code__icontains=search))
    
    # Pagination - 60 products per page (20 rows of 3)
    per_page = 60
    total_products = products.count()
    total_pages = (total_products + per_page - 1) // per_page
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    start = (page - 1) * per_page
    end = start + per_page
    
    # Build list with cached or fallback QR codes
    products_with_qr = []
    base_url = get_base_url()
    products_to_update = []
    
    for product in products[start:end]:
        qr_url = f"{base_url}/p/{product.code}/"
        
        # Use cached QR code or generate if missing
        if product.qr_code_base64:
            qr_base64 = product.qr_code_base64
        else:
            # Fallback: generate on the fly (slower but works)
            qr_base64 = generate_qr_base64(qr_url)
            # Mark for update
            products_to_update.append((product.pk, qr_base64))
        
        products_with_qr.append({
            'product': product,
            'qr_code': qr_base64,
            'url': qr_url,
        })
    
    # Bulk update products that needed QR generation
    if products_to_update:
        from django.db import transaction
        with transaction.atomic():
            for pk, qr_data in products_to_update:
                Product.objects.filter(pk=pk).update(qr_code_base64=qr_data)
    
    # Get categories for filter
    from inventory.models import Category
    categories = Category.objects.all().order_by('name')
    
    context = {
        'products_with_qr': products_with_qr,
        'categories': categories,
        'total_products': total_products,
        'page': page,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'site_name': 'الخواجة',
    }
    
    return render(request, 'public/qr_export.html', context)


@never_cache
def qr_pdf_download(request):
    """
    Serve the pre-generated PDF with all QR codes
    The PDF is generated by: python manage.py generate_qr_pdf
    """
    import os
    from django.http import FileResponse, Http404
    
    # Path to pre-generated PDF
    pdf_path = os.path.join(settings.BASE_DIR, 'media', 'qr_codes', 'all_products_qr.pdf')
    
    if not os.path.exists(pdf_path):
        # If PDF doesn't exist, generate it on first request
        from django.core.management import call_command
        try:
            call_command('generate_qr_pdf')
        except Exception as e:
            return HttpResponse(
                f'<h1>PDF غير متاح</h1><p>يرجى تشغيل الأمر: <code>python manage.py generate_qr_pdf</code></p><p>Error: {e}</p>',
                content_type='text/html; charset=utf-8',
                status=503
            )
    
    # Get file modification time for cache info
    file_mtime = os.path.getmtime(pdf_path)
    from datetime import datetime
    last_updated = datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M')
    
    # Serve the file
    response = FileResponse(
        open(pdf_path, 'rb'),
        content_type='application/pdf',
        as_attachment=True,
        filename='qr_codes_all_products.pdf'
    )
    
    # Add info header
    response['X-PDF-Last-Updated'] = last_updated
    
    return response

