"""
Management command to generate a comprehensive PDF with all QR codes
Uses Arabic font support and matches 3x3cm layout request
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from inventory.models import Product, BaseProduct, ProductVariant
from io import BytesIO
import os
import base64

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# Arabic text support
import arabic_reshaper
from bidi.algorithm import get_display


class Command(BaseCommand):
    help = 'Generate comprehensive PDF with all product QR codes (BaseProduct + Orphans)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=int,
            help='Generate PDF for specific category ID only',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='media/qr_codes/all_products_qr.pdf',
            help='Output file path',
        )

    def handle(self, *args, **options):
        category_id = options.get('category')
        output_path = options.get('output')
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.stdout.write(self.style.NOTICE('Starting PDF generation (3x3cm Layout)...'))
        
        # Register Arabic font
        self.register_fonts()
        
        # 1. Fetch BaseProducts (Active)
        base_products = BaseProduct.objects.filter(is_active=True).order_by('name')
        
        # 2. Fetch Orphan Products (Active, have code, NOT linked to any variant)
        # We need to find products that are NOT in ProductVariant.legacy_product
        linked_ids = ProductVariant.objects.filter(legacy_product__isnull=False).values_list('legacy_product_id', flat=True)
        orphan_products = Product.objects.filter(code__isnull=False).exclude(code='').exclude(id__in=linked_ids).order_by('name')
        
        if category_id:
            base_products = base_products.filter(category_id=category_id)
            orphan_products = orphan_products.filter(category_id=category_id)
            self.stdout.write(f'Filtering by category ID: {category_id}')
        
        # Combine lists
        all_items = list(base_products) + list(orphan_products)
        total_count = len(all_items)
        
        self.stdout.write(f'Found {total_count} items (Base: {base_products.count()}, Orphans: {orphan_products.count()})')
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No products found!'))
            return
        
        # Generate PDF
        self.generate_pdf(all_items, output_path, total_count)
        
        self.stdout.write(self.style.SUCCESS(f'PDF generated successfully: {output_path}'))
        
        # Get file size
        file_size = os.path.getsize(output_path)
        self.stdout.write(f'File size: {file_size / 1024 / 1024:.2f} MB')

    def register_fonts(self):
        try:
            # Prefer DejaVu Sans which supports BOTH Arabic and English well
            font_paths = [
                '/usr/share/fonts/TTF/DejaVuSans.ttf',
                '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/noto/NotoSansArabic-Regular.ttf',
                '/usr/share/fonts/noto/NotoSansArabic-Bold.ttf',
                'static/fonts/NotoSansArabic-Regular.ttf',
                'static/fonts/NotoSansArabic-Bold.ttf',
            ]
            
            registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font_name = 'Arabic'
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        self.stdout.write(self.style.SUCCESS(f'Registered font: {font_path}'))
                        registered = True
                        break
                    except Exception as e:
                        pass
            
            if not registered:
                self.stdout.write(self.style.WARNING('No Arabic font found! Text may appear as squares.'))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not register Arabic font: {e}'))

    def reshape_arabic(self, text):
        """Reshape Arabic text for proper display in PDF"""
        if not text:
            return ""
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except:
            return str(text)

    def generate_pdf(self, items, output_path, total_count):
        """Generate the PDF with QR codes in 3x3cm grid"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.5*cm, # Minimized margins for max space
            leftMargin=0.5*cm,
            topMargin=1.0*cm,
            bottomMargin=1.0*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Define styles
        try:
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Heading1'],
                fontName='Arabic',
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=15,
                leading=22
            )
            arabic_normal = ParagraphStyle(
                'ArabicNormal',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=10,
                alignment=TA_CENTER,
                leading=12
            )
            # Compact Product Name Style
            product_name_style = ParagraphStyle(
                'ProductName',
                parent=styles['Normal'],
                fontName='Arabic',
                fontSize=9, # Smaller font
                alignment=TA_CENTER,
                leading=10,
                spaceBefore=1
            )
        except:
            title_style = styles['Heading1']
            arabic_normal = styles['Normal']
            product_name_style = styles['Normal']
        
        # Header
        title_text = self.reshape_arabic('رموز QR للمنتجات - الخواجة')
        elements.append(Paragraph(title_text, title_style))
        
        count_text = self.reshape_arabic(f'إجمالي المنتجات: {total_count}')
        elements.append(Paragraph(count_text, arabic_normal))
        elements.append(Spacer(1, 15))
        
        # Grid Setup
        # 3cm QR + Text space ~= 3.5cm width per item? 
        # User asked for 3cm x 3cm QR.
        # A4 Width = 21cm. -1cm margin = 20cm usable.
        # If column width is ~3.8cm, we fit 5 columns (19cm).
        
        ITEMS_PER_ROW = 5
        COL_WIDTH = 3.8 * cm
        
        table_data = []
        current_row = []
        processed = 0
        
        for item in items:
            processed += 1
            
            # Generate/Get QR
            if not item.qr_code_base64:
                item.generate_qr()
                try:
                    # Save silently to avoid overhead if possible, or just generate in memory
                    # But we need to save it to model eventually
                   if hasattr(item, 'save'):
                       item.save(update_fields=['qr_code_base64'])
                except:
                    pass
            
            qr_base64 = item.qr_code_base64
            
            if qr_base64:
                try:
                    qr_data = base64.b64decode(qr_base64)
                    qr_buffer = BytesIO(qr_data)
                    # REQUEST: 3cm x 3cm QR
                    qr_img = Image(qr_buffer, width=3*cm, height=3*cm)
                    
                    # Name Truncation
                    raw_name = item.name
                    if len(raw_name) > 25:
                        raw_name = raw_name[:25] + '..'
                    name_text = self.reshape_arabic(raw_name)
                    
                    # Inner Cell Content: QR Image + Name Text
                    cell_content = [
                        [qr_img],
                        [Paragraph(f"<b>{name_text}</b>", product_name_style)]
                    ]
                    
                    # Inner Table for alignment
                    inner_table = Table(cell_content, colWidths=[3.2*cm])
                    inner_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 1),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ]))
                    
                    current_row.append(inner_table)
                    
                except Exception as e:
                    self.stdout.write(f"Error processing item {item.code}: {e}")
                    current_row.append('') # Empty placeholder on error
            else:
                 current_row.append('')
            
            # Row Management
            if len(current_row) == ITEMS_PER_ROW:
                table_data.append(current_row)
                current_row = []
            
            if processed % 100 == 0:
                self.stdout.write(f'Processed {processed}/{total_count}...')

        # Fill last row
        if current_row:
            while len(current_row) < ITEMS_PER_ROW:
                current_row.append('')
            table_data.append(current_row)
        
        # Build Main Grid Table
        if table_data:
            main_table = Table(table_data, colWidths=[COL_WIDTH] * ITEMS_PER_ROW)
            main_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                # Optional: Dotted lines for cutting?
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]))
            elements.append(main_table)
            
        self.stdout.write('Building PDF document...')
        doc.build(elements)
